"""Batch sampler for the by-hand journal read (handoff-6).

Emits, per batch, a **text-free** spec JSON and a reviewable manifest CSV under
``output/qualitative/reader/``. ``reader.py`` turns a spec into the embedded-text
HTML; the spec and manifest themselves never carry journal text, so they stay
reviewable without exposing content.

Two batch kinds:

* ``recon`` — 25 entries from ``2022_s2`` (5 per journal index, spanning the
  word-count terciles), all `extract_status == ok`; plus 3 `extract_suspect`
  files as a small trailing section for Jos to eyeball.
* ``teams`` — one batch per analysable cohort, grouped by team. Teams and members
  are pseudonymised (``team_01``…, members ``A``–``F``). The un-blinding key
  (``team_NN`` → real team + archetype + flag) goes to a separate
  ``team_key_<cohort>.csv`` that the HTML **never** loads.

This is data-collection instrumentation only — no sentiment analysis, no scoring.

Not to be merged with ``src/labelling/sample.py`` (different strand).

Run:
    python3 -m src.qualitative.sample recon
    python3 -m src.qualitative.sample teams            # all analysable cohorts
    python3 -m src.qualitative.sample teams --cohort 2023_s1
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.qualitative.audit import candidate_keys, load_peer
from src.qualitative.ingest import CROSSWALK_CSV, ENTRIES_PARQUET

logger = logging.getLogger(__name__)

OUT_DIR = Path("output/qualitative/reader")
SEED = 42

RECON_COHORT = "2022_s2"
RECON_PER_INDEX = 5
RECON_SUSPECT_N = 3
ANALYSABLE = ("2023_s1", "2023_s2", "2024_s1")

DYN_ASSIGN = Path("output/dynamics/aa_k4_assignments.csv")
_COHORT_RE = re.compile(r"S(?P<sem>\d)-(?P<year>\d{4})")

# A journal file is uniquely identified downstream by this pair; we surface it as
# a single opaque id so nothing but the HTML needs the identifiable source path.
def _entry_uid(row: pd.Series) -> str:
    return f"{row['anon_id']}_{row['submission_id']}"


# --------------------------------------------------------------------------- #
# recon
# --------------------------------------------------------------------------- #
def _span_terciles(group: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Pick ``n`` rows spanning the word-count terciles of ``group``.

    Guarantees at least one short and one long entry rather than clustering at
    the median. Target split for n=5 is [2, 1, 2] across (low, mid, high).
    """
    g = group.sort_values("word_count").reset_index(drop=True)
    if len(g) <= n:
        return g
    # tercile boundaries by position
    thirds = np.array_split(g.index.to_numpy(), 3)
    targets = _tercile_targets(n)
    chosen: list[int] = []
    for bucket, t in zip(thirds, targets):
        take = min(t, len(bucket))
        if take:
            chosen.extend(rng.choice(bucket, size=take, replace=False).tolist())
    # top up if any bucket was too small
    remaining = [i for i in g.index.to_numpy() if i not in chosen]
    while len(chosen) < n and remaining:
        pick = int(rng.choice(remaining))
        chosen.append(pick)
        remaining.remove(pick)
    return g.loc[sorted(chosen)]


def _tercile_targets(n: int) -> list[int]:
    """Split n across (low, mid, high) favouring the tails. n=5 -> [2,1,2]."""
    base = n // 3
    targets = [base, base, base]
    for k, i in enumerate((0, 2, 1)):  # add extras to low, high, then mid
        if sum(targets) >= n:
            break
        targets[i] += 1
    return targets


def build_recon(df: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SEED)
    cohort = df[df["cohort"] == RECON_COHORT]

    ok = cohort[cohort["extract_status"] == "ok"]
    entries: list[dict] = []
    for idx in range(1, 6):
        g = ok[ok["journal_index"] == idx]
        if g.empty:
            logger.warning("recon: no 'ok' entries at journal index %d", idx)
            continue
        for _, row in _span_terciles(g, RECON_PER_INDEX, rng).iterrows():
            entries.append(_entry_dict(row, section="main"))

    # trailing suspect section (not part of the 25)
    suspect = cohort[cohort["extract_status"] == "extract_suspect"]
    if len(suspect):
        take = min(RECON_SUSPECT_N, len(suspect))
        picks = suspect.iloc[rng.choice(len(suspect), size=take, replace=False)]
        for _, row in picks.iterrows():
            entries.append(_entry_dict(row, section="suspect"))

    return {
        "batch": "recon", "mode": "recon", "seed": SEED,
        "cohort": RECON_COHORT, "entries": entries,
    }


# --------------------------------------------------------------------------- #
# teams
# --------------------------------------------------------------------------- #
def _team_archetypes() -> dict[tuple[str, str], dict]:
    """(cohort, team_name) -> {archetype, flag} from the persisted AA k=4 refit.

    Team archetype = majority across the team's question-matrices (no majority ->
    'Mixed'); flag = 'Anomalous' if ANY matrix is flagged. Mirrors the
    team-labelling derivation without importing across packages.
    """
    if not DYN_ASSIGN.exists():
        logger.warning("%s missing — team_key archetype/flag will be blank.",
                       DYN_ASSIGN)
        return {}
    aa = pd.read_csv(DYN_ASSIGN)
    out: dict[tuple[str, str], dict] = {}
    for (csv_path, team), grp in aa.groupby(["csv_path", "team_name"]):
        m = _COHORT_RE.search(Path(csv_path).name)
        if not m:
            continue
        cohort = f"{m.group('year')}_s{m.group('sem')}"
        modes = grp["archetype"].mode()
        archetype = modes.iloc[0] if len(modes) == 1 else "Mixed"
        flag = ("Anomalous" if (grp["atypicality_flag"] == "Anomalous").any()
                else "Typical")
        out[(cohort, team)] = {"archetype": archetype, "flag": flag}
    return out


def _journal_pid_index(cohort: str, peer: dict, crosswalk: pd.DataFrame
                       ) -> dict[str, list[str]]:
    """peer person id -> list of journal normalised_names that match them."""
    key_index = peer[cohort]["key_index"]
    pid_to_names: dict[str, list[str]] = {}
    for nn in crosswalk.query("cohort == @cohort")["normalised_name"]:
        for pid in key_index.get(nn, ()):  # candidate-key exact match
            pid_to_names.setdefault(pid, []).append(nn)
    return pid_to_names


def build_teams(df: pd.DataFrame, crosswalk: pd.DataFrame, cohort: str) -> tuple[dict, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    peer = load_peer()
    if cohort not in peer:
        raise ValueError(f"{cohort} has no peer data — cannot build a teams batch.")

    arche = _team_archetypes()
    pid_to_names = _journal_pid_index(cohort, peer, crosswalk)
    name_to_anon = dict(zip(
        crosswalk.query("cohort == @cohort")["normalised_name"],
        crosswalk.query("cohort == @cohort")["anon_id"]))
    entries_by_anon = {a: g for a, g in df[df["cohort"] == cohort].groupby("anon_id")}

    # teams that have ≥1 journalling member
    teams = peer[cohort]["teams"]
    live_teams = []
    for team, pids in teams.items():
        journalling = [p for p in pids if p in pid_to_names]
        if journalling:
            live_teams.append((team, journalling))

    # pseudonymise team order
    order = rng.permutation(len(live_teams))
    key_rows, spec_entries = [], []
    for new_i, orig_i in enumerate(order, start=1):
        team, journalling = live_teams[orig_i]
        team_label = f"team_{new_i:02d}"
        # pseudonymise members within team
        member_order = rng.permutation(len(journalling))
        for m_i, m_orig in enumerate(member_order):
            pid = journalling[m_orig]
            member_label = chr(ord("A") + m_i)
            # a peer person may map to >1 journal normalised name (rare); take all
            anon_ids = {name_to_anon[nn] for nn in pid_to_names[pid]
                        if nn in name_to_anon}
            for anon in sorted(anon_ids):
                sub = entries_by_anon.get(anon)
                if sub is None:
                    continue
                for _, row in sub.sort_values("journal_index").iterrows():
                    if row["extract_status"] not in ("ok", "extract_suspect"):
                        continue
                    spec_entries.append(_entry_dict(
                        row, section="main",
                        team_label=team_label, member_label=member_label))
        meta = arche.get((cohort, team), {"archetype": "", "flag": ""})
        key_rows.append({
            "team_label": team_label, "cohort": cohort, "real_team": team,
            "archetype": meta["archetype"], "flag": meta["flag"],
            "n_journalling_members": len(journalling),
        })

    spec = {
        "batch": f"teams_{cohort}", "mode": "teams", "seed": SEED,
        "cohort": cohort, "entries": spec_entries,
    }
    return spec, pd.DataFrame(key_rows)


# --------------------------------------------------------------------------- #
# shared
# --------------------------------------------------------------------------- #
def _entry_dict(row: pd.Series, section: str, team_label: str | None = None,
                member_label: str | None = None) -> dict:
    d = {
        "entry_uid": _entry_uid(row),
        "anon_id": row["anon_id"],
        "submission_id": str(row["submission_id"]),
        "cohort": row["cohort"],
        "journal_index": int(row["journal_index"]),
        "word_count": int(row["word_count"]),
        "extract_status": row["extract_status"],
        "section": section,
    }
    if team_label is not None:
        d["team_label"] = team_label
        d["member_label"] = member_label
    return d


def _write_batch(spec: dict, key_df: pd.DataFrame | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    batch = spec["batch"]
    (OUT_DIR / f"batch_{batch}.json").write_text(
        json.dumps(spec, indent=2), encoding="utf-8")

    # text-free manifest
    man = pd.DataFrame(spec["entries"]).drop(columns=["anon_id", "submission_id"],
                                             errors="ignore")
    man.to_csv(OUT_DIR / f"batch_manifest_{batch}.csv", index=False)

    if key_df is not None:
        cohort = spec["cohort"]
        key_df.to_csv(OUT_DIR / f"team_key_{cohort}.csv", index=False)

    n = len(spec["entries"])
    extra = ""
    if spec["mode"] == "teams":
        extra = f", {man['team_label'].nunique()} teams"
    print(f"  {batch}: {n} entries{extra} -> batch_{batch}.json + manifest"
          + (f" + team_key_{spec['cohort']}.csv" if key_df is not None else ""))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.qualitative.sample",
        description="Sample journal batches for the by-hand reader.",
    )
    parser.add_argument("kind", choices=["recon", "teams"],
                        help="Which batch kind to build.")
    parser.add_argument("--cohort", default=None,
                        help="teams: restrict to one cohort (default: all analysable).")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # The peer-CSV parser logs non-submitter warnings that name students —
    # keep those off the terminal.
    logging.getLogger("src.parsing.parser").setLevel(logging.CRITICAL)

    df = pd.read_parquet(ENTRIES_PARQUET)
    crosswalk = pd.read_csv(CROSSWALK_CSV)

    print(f"Sampling '{args.kind}' (seed={SEED}):")
    if args.kind == "recon":
        _write_batch(build_recon(df))
    else:
        cohorts = [args.cohort] if args.cohort else list(ANALYSABLE)
        for c in cohorts:
            spec, key_df = build_teams(df, crosswalk, c)
            _write_batch(spec, key_df)


if __name__ == "__main__":
    main()
