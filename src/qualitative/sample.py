"""Batch sampler for the by-hand journal read (handoff-6, amended 2026-08-04).

Emits, per batch, a **text-free** spec JSON and a reviewable manifest CSV under
``output/qualitative/reader/``. ``reader.py`` turns a spec into the embedded-text
HTML; the spec and manifest themselves never carry journal text, so they stay
reviewable without exposing content.

Two batch kinds — both **team-based** (the team is the judgement unit):

* ``pilot`` — 3 teams from ``2024_s1``, one each from archetypes A0, A2, A1, every
  journalling member read in full. Blinded exactly like ``teams``; the
  ``team_NN`` → archetype mapping goes to ``pilot_key.csv`` (never loaded by the
  HTML). ``2024_s1`` is chosen because it contributes zero teams to the 40-card
  labelled anchor set, so the pilot spends none of the scarce overlap. Plus 3
  ``extract_suspect`` files as a trailing extract-check section.
* ``teams`` — one batch per analysable cohort, grouped by team; teams/members
  pseudonymised (``team_01``…, members ``A``–``F``). Key → ``team_key_<cohort>.csv``.

Data-collection instrumentation only — no sentiment analysis, no scoring.

Not to be merged with ``src/labelling/sample.py`` (different strand).

Run:
    python3 -m src.qualitative.sample pilot
    python3 -m src.qualitative.sample teams              # all analysable cohorts
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

from src.qualitative.audit import load_peer
from src.qualitative.ingest import CROSSWALK_CSV, ENTRIES_PARQUET

logger = logging.getLogger(__name__)

OUT_DIR = Path("output/qualitative/reader")
SEED = 42

# Pilot teams are hand-selected (handoff-6 amendment + Jos 2026-08-04): one per
# named archetype, chosen by mean-load argmax, zero anchor-set spend. The A0 team
# is from a *different cohort* than the other two — acceptable for a feasibility
# pilot (we test whether the judgement is makeable, not compare cohorts), but it
# must NOT carry into the main validation.
PILOT_TEAMS = (
    {"cohort": "2024_s1", "team": "Team 12 - Poké Rangers", "archetype": "A2"},
    {"cohort": "2024_s1", "team": "Team 5 - Pollination",   "archetype": "A1"},
    {"cohort": "2023_s2", "team": "Team 33 - DoWe?",         "archetype": "A0"},
)
SUSPECT_COHORT = "2024_s1"
SUSPECT_N = 3
ANALYSABLE = ("2023_s1", "2023_s2", "2024_s1")

DYN_ASSIGN = Path("output/dynamics/aa_k4_assignments.csv")
_COHORT_RE = re.compile(r"S(?P<sem>\d)-(?P<year>\d{4})")


def _entry_uid(row: pd.Series) -> str:
    return f"{row['anon_id']}_{row['submission_id']}"


# --------------------------------------------------------------------------- #
# archetype / load per team (from the persisted AA k=4 refit)
# --------------------------------------------------------------------------- #
_ARCHETYPES = ("A0", "A1", "A2", "A3")


def _team_meta() -> dict[tuple[str, str], dict]:
    """(cohort, team_name) -> team-level archetype record.

    Team archetype = **argmax of the mean load** across the team's
    question-matrices (Jos 2026-08-04). This is more stable than majority-vote of
    the per-matrix argmax labels: majority ties on 21 of 139 teams and is
    unanimous on only 41, whereas mean-load always resolves. The majority-vote
    label is retained alongside (`majority`) for comparison, with `is_tie` /
    `is_unanimous` so the tie rate can be reported.

    flag = 'Anomalous' if any of the team's matrices is flagged.
    """
    if not DYN_ASSIGN.exists():
        logger.warning("%s missing — archetype/load will be blank.", DYN_ASSIGN)
        return {}
    aa = pd.read_csv(DYN_ASSIGN)
    out: dict[tuple[str, str], dict] = {}
    for (csv_path, team), grp in aa.groupby(["csv_path", "team_name"]):
        m = _COHORT_RE.search(Path(csv_path).name)
        if not m:
            continue
        cohort = f"{m.group('year')}_s{m.group('sem')}"
        loads = {a: float(grp[f"load_{a}"].mean()) for a in _ARCHETYPES}
        archetype = max(loads, key=loads.get)          # mean-load argmax
        modes = grp["archetype"].mode()
        majority = modes.iloc[0] if len(modes) == 1 else "Mixed"
        out[(cohort, team)] = {
            "archetype": archetype, "load": loads[archetype], "loads": loads,
            "majority": majority, "is_tie": len(modes) > 1,
            "is_unanimous": grp["archetype"].nunique() == 1,
            "flag": ("Anomalous" if (grp["atypicality_flag"] == "Anomalous").any()
                     else "Typical"),
        }
    return out


def archetype_derivation_stats() -> dict:
    """Reportable comparison of mean-load vs majority-vote team archetypes."""
    meta = _team_meta()
    n = len(meta)
    return {
        "n_teams": n,
        "majority_ties": sum(m["is_tie"] for m in meta.values()),
        "majority_unanimous": sum(m["is_unanimous"] for m in meta.values()),
        "meanload_eq_majority": sum(m["archetype"] == m["majority"]
                                    for m in meta.values()),
    }


def _journal_pid_index(cohort: str, peer: dict, crosswalk: pd.DataFrame
                       ) -> dict[str, list[str]]:
    """peer person id -> list of journal normalised_names that match them."""
    key_index = peer[cohort]["key_index"]
    pid_to_names: dict[str, list[str]] = {}
    for nn in crosswalk.query("cohort == @cohort")["normalised_name"]:
        for pid in key_index.get(nn, ()):
            pid_to_names.setdefault(pid, []).append(nn)
    return pid_to_names


# --------------------------------------------------------------------------- #
# shared: assemble a team's blinded entries
# --------------------------------------------------------------------------- #
def _team_entries(team: str, journalling: list[str], team_label: str,
                  pid_to_names: dict[str, list[str]], name_to_anon: dict[str, str],
                  entries_by_anon: dict, rng: np.random.Generator) -> list[dict]:
    """Ordered, pseudonymised entry dicts for one team (members A–F)."""
    out: list[dict] = []
    member_order = rng.permutation(len(journalling))
    for m_i, m_orig in enumerate(member_order):
        pid = journalling[m_orig]
        member_label = chr(ord("A") + m_i)
        anon_ids = {name_to_anon[nn] for nn in pid_to_names[pid] if nn in name_to_anon}
        for anon in sorted(anon_ids):
            sub = entries_by_anon.get(anon)
            if sub is None:
                continue
            for _, row in sub.sort_values("journal_index").iterrows():
                if row["extract_status"] not in ("ok", "extract_suspect"):
                    continue
                out.append(_entry_dict(row, section="main",
                                       team_label=team_label,
                                       member_label=member_label))
    return out


def _suspect_section(df: pd.DataFrame, cohort: str, rng: np.random.Generator
                     ) -> list[dict]:
    """Up to SUSPECT_N extract_suspect files as a trailing extract-check group."""
    suspect = df[(df["cohort"] == cohort) & (df["extract_status"] == "extract_suspect")]
    if suspect.empty:
        return []
    take = min(SUSPECT_N, len(suspect))
    picks = suspect.iloc[rng.choice(len(suspect), size=take, replace=False)]
    return [_entry_dict(r, section="suspect", team_label="extract_check",
                        member_label="") for _, r in picks.iterrows()]


# --------------------------------------------------------------------------- #
# pilot
# --------------------------------------------------------------------------- #
def build_pilot(df: pd.DataFrame, crosswalk: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Assemble the 3 hand-selected pilot teams (cross-cohort), blinded."""
    rng = np.random.default_rng(SEED)
    peer = load_peer()
    meta = _team_meta()

    # gather each named team's journalling members (per its own cohort)
    selected = []
    for spec in PILOT_TEAMS:
        coh, team = spec["cohort"], spec["team"]
        pids = peer[coh]["teams"].get(team)
        if pids is None:
            raise ValueError(f"pilot team not found in peer data: {coh} / {team!r}")
        pid_to_names = _journal_pid_index(coh, peer, crosswalk)
        cw_c = crosswalk.query("cohort == @coh")
        journalling = [p for p in pids if p in pid_to_names]
        info = meta.get((coh, team), {})
        selected.append({
            "cohort": coh, "team": team, "intended": spec["archetype"],
            "journalling": journalling, "pid_to_names": pid_to_names,
            "name_to_anon": dict(zip(cw_c["normalised_name"], cw_c["anon_id"])),
            "entries_by_anon": {a: g for a, g in
                                df[df["cohort"] == coh].groupby("anon_id")},
            "info": info,
        })

    # blinded, seeded team order
    order = rng.permutation(len(selected))
    spec_entries, key_rows = [], []
    for new_i, orig_i in enumerate(order, start=1):
        s = selected[orig_i]
        team_label = f"team_{new_i:02d}"
        spec_entries += _team_entries(
            s["team"], s["journalling"], team_label, s["pid_to_names"],
            s["name_to_anon"], s["entries_by_anon"], rng)
        info = s["info"]
        key_rows.append({
            "team_label": team_label, "cohort": s["cohort"], "real_team": s["team"],
            "intended_archetype": s["intended"],
            "derived_archetype": info.get("archetype", ""),
            "archetype_load": round(info.get("load", float("nan")), 3),
            "majority_vote": info.get("majority", ""),
            "flag": info.get("flag", ""),
            "n_journalling_members": len(s["journalling"]),
        })

    spec_entries += _suspect_section(df, SUSPECT_COHORT, rng)
    spec = {"batch": "pilot", "mode": "teams", "seed": SEED,
            "cohort": "mixed (2024_s1, 2023_s2)", "entries": spec_entries}

    print("  pilot teams (blinded — archetype shown here only for the log):")
    for r in key_rows:
        print(f"    {r['team_label']}  intended={r['intended_archetype']}  "
              f"derived={r['derived_archetype']} (load {r['archetype_load']}, "
              f"majority {r['majority_vote']}, {r['flag']})  "
              f"members={r['n_journalling_members']}  cohort={r['cohort']}")
    return spec, pd.DataFrame(key_rows)


# --------------------------------------------------------------------------- #
# teams
# --------------------------------------------------------------------------- #
def build_teams(df: pd.DataFrame, crosswalk: pd.DataFrame, cohort: str
                ) -> tuple[dict, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    peer = load_peer()
    if cohort not in peer:
        raise ValueError(f"{cohort} has no peer data — cannot build a teams batch.")
    meta = _team_meta()
    pid_to_names = _journal_pid_index(cohort, peer, crosswalk)
    cw_c = crosswalk.query("cohort == @cohort")
    name_to_anon = dict(zip(cw_c["normalised_name"], cw_c["anon_id"]))
    entries_by_anon = {a: g for a, g in df[df["cohort"] == cohort].groupby("anon_id")}

    live = []
    for team, pids in peer[cohort]["teams"].items():
        journalling = [p for p in pids if p in pid_to_names]
        if journalling:
            live.append((team, journalling))

    order = rng.permutation(len(live))
    spec_entries, key_rows = [], []
    for new_i, orig_i in enumerate(order, start=1):
        team, journalling = live[orig_i]
        team_label = f"team_{new_i:02d}"
        spec_entries += _team_entries(team, journalling, team_label,
                                      pid_to_names, name_to_anon, entries_by_anon, rng)
        info = meta.get((cohort, team), {})
        key_rows.append({
            "team_label": team_label, "cohort": cohort, "real_team": team,
            "archetype": info.get("archetype", ""),
            "archetype_load": round(info.get("load", float("nan")), 3),
            "majority_vote": info.get("majority", ""),
            "flag": info.get("flag", ""),
            "n_journalling_members": len(journalling),
        })

    spec = {"batch": f"teams_{cohort}", "mode": "teams", "seed": SEED,
            "cohort": cohort, "entries": spec_entries}
    return spec, pd.DataFrame(key_rows)


# --------------------------------------------------------------------------- #
# main-run sample (handoff-7 Task 3)
# --------------------------------------------------------------------------- #
MAIN_RUN_CSV = Path("output/qualitative/main_run_sample.csv")


def _team_word_counts(df: pd.DataFrame, crosswalk: pd.DataFrame, peer: dict
                      ) -> pd.DataFrame:
    """One row per journalling team across the analysable cohorts, with its
    mean journal word count and mean-load archetype."""
    meta = _team_meta()
    rows = []
    for coh in ANALYSABLE:
        pid_to_names = _journal_pid_index(coh, peer, crosswalk)
        cw = crosswalk.query("cohort == @coh")
        name_to_anon = dict(zip(cw["normalised_name"], cw["anon_id"]))
        eba = {a: g for a, g in df[df["cohort"] == coh].groupby("anon_id")}
        for team, pids in peer[coh]["teams"].items():
            journalling = [p for p in pids if p in pid_to_names]
            if not journalling:
                continue
            wcs = []
            for p in journalling:
                for nn in pid_to_names[p]:
                    sub = eba.get(name_to_anon.get(nn))
                    if sub is not None:
                        wcs += sub[sub["extract_status"].isin(
                            ["ok", "extract_suspect"])]["word_count"].tolist()
            info = meta.get((coh, team), {})
            rows.append({
                "cohort": coh, "real_team": team,
                "archetype": info.get("archetype", ""),
                "archetype_load": round(info.get("load", float("nan")), 3),
                "majority_vote": info.get("majority", ""),
                "flag": info.get("flag", ""),
                "n_journalling_members": len(journalling),
                "n_entries": len(wcs),
                "mean_word_count": round(float(np.mean(wcs)), 1) if wcs else 0.0,
            })
    return pd.DataFrame(rows)


def build_main_run_sample(df: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """A0/A2 census, A1 by word-count tails (5 low + 5 high), A3 random = 32."""
    peer = load_peer()
    teams = _team_word_counts(df, crosswalk, peer)

    counts = teams["archetype"].value_counts().to_dict()
    print("  journalling teams by archetype (mean-load argmax):",
          {a: counts.get(a, 0) for a in ("A0", "A1", "A2", "A3")})
    if counts.get("A0") != 8 or counts.get("A2") != 10:
        print("  ⚠️  STOP-AND-REPORT: A0/A2 counts are not 8/10 — the census "
              "design assumes those numbers. Not sampling.")

    picks = []
    for arch in ("A0", "A2"):                       # census
        p = teams[teams["archetype"] == arch].copy()
        p["stratum"] = "census"
        picks.append(p)
    a1 = teams[teams["archetype"] == "A1"].sort_values("mean_word_count")
    low, high = a1.head(5).copy(), a1.tail(5).copy()
    low["stratum"], high["stratum"] = "A1_low_wordcount", "A1_high_wordcount"
    picks += [low, high]
    a3 = teams[teams["archetype"] == "A3"]
    a3pick = a3.sample(n=min(4, len(a3)), random_state=SEED).copy()
    a3pick["stratum"] = "A3_random"
    picks.append(a3pick)

    chosen = pd.concat(picks, ignore_index=True)
    chosen.insert(0, "sample_id", [f"team_{i+1:02d}" for i in range(len(chosen))])
    # flag census teams that were already in the v1 pilot (re-read under v2; the
    # pilot's v1 codes are not pooled, but Jos should know about the overlap).
    pilot_set = {(t["cohort"], t["team"]) for t in PILOT_TEAMS}
    chosen["in_pilot"] = [(c, t) in pilot_set for c, t
                          in zip(chosen["cohort"], chosen["real_team"])]
    MAIN_RUN_CSV.parent.mkdir(parents=True, exist_ok=True)
    chosen.to_csv(MAIN_RUN_CSV, index=False)

    # realised cell counts
    print(f"  main-run: {len(chosen)} teams -> {MAIN_RUN_CSV}")
    print("  archetype x cohort:")
    ct = chosen.pivot_table(index="archetype", columns="cohort",
                            values="sample_id", aggfunc="count", fill_value=0)
    for a in ct.index:
        print(f"    {a}: " + ", ".join(f"{c}={int(ct.loc[a, c])}" for c in ct.columns)
              + f"  (tot {int(ct.loc[a].sum())})")
    print(f"  A1 low-wordcount means : "
          f"{sorted(round(x,0) for x in low['mean_word_count'])}")
    print(f"  A1 high-wordcount means: "
          f"{sorted(round(x,0) for x in high['mean_word_count'])}")
    gap = high["mean_word_count"].min() - low["mean_word_count"].max()
    if gap <= 0:
        print("  ⚠️  A1 word-count tails overlap — the low/high split may not be "
              "meaningful; report before relying on it.")
    n_pilot = int(chosen["in_pilot"].sum())
    if n_pilot:
        print(f"  note: {n_pilot} census team(s) were in the v1 pilot "
              "(in_pilot=True) — re-read under v2, pilot v1 codes not pooled.")
    return chosen


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


def _write_batch(spec: dict, key_df: pd.DataFrame | None = None,
                 key_name: str | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    batch = spec["batch"]
    (OUT_DIR / f"batch_{batch}.json").write_text(
        json.dumps(spec, indent=2), encoding="utf-8")

    man = pd.DataFrame(spec["entries"])
    if "team_label" in man.columns:                 # mean journal word count/team
        man["team_mean_word_count"] = (
            man.groupby("team_label")["word_count"].transform("mean").round(1))
    man = man.drop(columns=["anon_id", "submission_id"], errors="ignore")
    man.to_csv(OUT_DIR / f"batch_manifest_{batch}.csv", index=False)

    if key_df is not None:
        key_df.to_csv(OUT_DIR / (key_name or f"team_key_{spec['cohort']}.csv"),
                      index=False)

    teams = [e for e in spec["entries"] if e.get("team_label")
             and e["section"] != "suspect"]
    n_teams = len({e["team_label"] for e in teams})
    n_suspect = sum(1 for e in spec["entries"] if e["section"] == "suspect")
    print(f"  {batch}: {len(spec['entries'])} entries, {n_teams} teams"
          + (f", {n_suspect} suspect" if n_suspect else "")
          + f" -> batch_{batch}.json + manifest"
          + (f" + {key_name or 'team_key_'+spec['cohort']+'.csv'}"
             if key_df is not None else ""))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.qualitative.sample",
        description="Sample journal batches for the by-hand reader.",
    )
    parser.add_argument("kind", choices=["pilot", "teams", "main"],
                        help="Which batch kind to build ('main' = main-run sample).")
    parser.add_argument("--cohort", default=None,
                        help="teams: restrict to one cohort (default: all analysable).")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # The peer-CSV parser logs non-submitter warnings that name students.
    logging.getLogger("src.parsing.parser").setLevel(logging.CRITICAL)

    df = pd.read_parquet(ENTRIES_PARQUET)
    crosswalk = pd.read_csv(CROSSWALK_CSV)

    print(f"Sampling '{args.kind}' (seed={SEED}):")
    if args.kind == "pilot":
        spec, key_df = build_pilot(df, crosswalk)
        _write_batch(spec, key_df, key_name="pilot_key.csv")
    elif args.kind == "main":
        build_main_run_sample(df, crosswalk)
    else:
        cohorts = [args.cohort] if args.cohort else list(ANALYSABLE)
        for c in cohorts:
            spec, key_df = build_teams(df, crosswalk, c)
            _write_batch(spec, key_df)


if __name__ == "__main__":
    main()
