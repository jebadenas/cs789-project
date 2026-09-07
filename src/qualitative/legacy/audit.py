"""Linkage audit — is the journal ↔ peer-data join viable, and at what N?

Consumes the pseudonymised ingest artefacts plus the identity crosswalk and the
peer-feedback CSVs, and answers the questions that gate RQ4 (§5.4) and RQ3-EXT
Step 4 (external validation of the k=4 archetypes):

1. Cohort coverage & the analysable intersection.
2. Match rates (journal ↔ peer) via the normalised-name join key.
3. Name collisions within a cohort.
4. Attrition — entries per journal index and per-student submission counts.
5. Lateness rates.
6. Extraction health.
7. Team coverage — members per team with ≥1 journal entry (gates Step 4).
8. Date recoverability from document metadata.

Writes ``output/qualitative/linkage_audit.md`` (aggregate numbers only) plus
supporting CSVs. Identifiable unmatched-name lists go to CSVs, never the report.
Nothing here is committed — ``output/`` and ``data/`` are both git-ignored.

Run:  ``python3 -m src.qualitative.audit``  (run ingest first)
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import pandas as pd

from src.parsing.parser import parse_session
from src.qualitative import templates
from src.qualitative.ingest import (
    CROSSWALK_CSV,
    ENTRY_MANIFEST_CSV,
    normalise_name,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
OUT_DIR = Path("output/qualitative")
REPORT = OUT_DIR / "linkage_audit.md"

# Peer-feedback cohorts (from the CSVs in data/). Journals extend back to
# 2022_s2 but only from 2023_s1 onward do peer sessions exist.
_COHORT_RE = re.compile(r"S(?P<sem>\d)-(?P<year>\d{4})")

# Above this journal↔peer unmatched rate we stop and report rather than reach
# for fuzzy matching (a wrong join silently corrupts every downstream result).
UNMATCHED_ALERT = 0.10


# --------------------------------------------------------------------------- #
# Order-invariant EXACT matcher
# --------------------------------------------------------------------------- #
def candidate_keys(name: str) -> set[str]:
    """Deterministic order-invariant key set for a peer full name.

    Peer CSVs vary in name *order* between cohorts: most are ``"Last, First"``
    but ``2024_s1`` exports ``"First [Middle] Last"``. Journal filenames are the
    last-first concatenation with no delimiter, so the journal side cannot be
    tokenised — instead we enumerate the plausible orderings from the peer side
    (which HAS token boundaries) and match by exact string equality.

    This is order-invariant **exact** matching, not fuzzy matching: no edit
    distance, no approximate scoring. A journal name links only if it equals one
    of these concatenations character-for-character.
    """
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]
    if not tokens:
        return set()
    keys = {
        "".join(tokens),                    # as-is concat
        "".join(reversed(tokens)),          # fully reversed
        tokens[-1] + tokens[0],             # last + first
        tokens[0] + tokens[-1],             # first + last
        tokens[-1] + "".join(tokens[:-1]),  # last + first(+middle)
    }
    return {k for k in keys if k}


# --------------------------------------------------------------------------- #
# Load peer-side structure
# --------------------------------------------------------------------------- #
def load_peer() -> dict[str, dict]:
    """Parse every peer CSV in ``data/`` into a per-cohort matcher.

    Returns ``peer[cohort]`` with keys:
      ``persons``    pid(email) -> {"name", "team"}
      ``key_index``  candidate_key -> set(pid)      (order-invariant lookup)
      ``simple``     set of same-order normalised names (for method diagnostics)
      ``teams``      team -> set(pid)
    """
    peer: dict[str, dict] = {}
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        m = _COHORT_RE.search(csv_path.name)
        if not m:
            continue
        cohort = f"{m.group('year')}_s{m.group('sem')}"
        matrices = parse_session(csv_path)

        persons: dict[str, dict] = {}
        key_index: dict[str, set[str]] = {}
        simple: set[str] = set()
        teams: dict[str, set[str]] = {}

        for (team, _label), sm in matrices.items():
            for s in sm.students:
                pid = s.email.strip().lower() or normalise_name(s.name)
                if not pid:
                    continue
                persons.setdefault(pid, {"name": s.name, "team": team})
                teams.setdefault(team, set()).add(pid)
                simple.add(normalise_name(s.name))
                for k in candidate_keys(s.name):
                    key_index.setdefault(k, set()).add(pid)

        peer[cohort] = {"persons": persons, "key_index": key_index,
                        "simple": simple, "teams": teams}
    return peer


def match_journal_names(
    journal_names: set[str], key_index: dict[str, set[str]]
) -> tuple[dict[str, set[str]], set[str], set[str]]:
    """Match journal names against the peer key index.

    Returns (matched: name -> pids, ambiguous names (>1 pid), unmatched names).
    """
    matched: dict[str, set[str]] = {}
    ambiguous: set[str] = set()
    unmatched: set[str] = set()
    for nn in journal_names:
        pids = key_index.get(nn)
        if not pids:
            unmatched.add(nn)
            continue
        matched[nn] = pids
        if len(pids) > 1:
            ambiguous.add(nn)
    return matched, ambiguous, unmatched


# --------------------------------------------------------------------------- #
# Load journal side
# --------------------------------------------------------------------------- #
def load_journal_side() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the ingest manifest joined to the crosswalk (adds normalised_name)."""
    manifest = pd.read_csv(ENTRY_MANIFEST_CSV)
    crosswalk = pd.read_csv(CROSSWALK_CSV)
    merged = manifest.merge(
        crosswalk[["anon_id", "normalised_name", "id_collision"]],
        on="anon_id", how="left",
    )
    return merged, crosswalk


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _fmt_pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "—"


def build_report(
    entries: pd.DataFrame,
    crosswalk: pd.DataFrame,
    peer: dict[str, dict],
) -> tuple[str, dict[str, pd.DataFrame]]:
    """Assemble the markdown report and the supporting CSV tables."""
    csvs: dict[str, pd.DataFrame] = {}
    L: list[str] = []
    add = L.append

    journal_cohorts = sorted(entries["cohort"].unique())
    peer_cohorts = sorted(peer)
    analysable = sorted(set(journal_cohorts) & set(peer_cohorts))
    calibration_only = sorted(set(journal_cohorts) - set(peer_cohorts))
    peer_only_cohorts = sorted(set(peer_cohorts) - set(journal_cohorts))

    # Pre-compute the match per analysable cohort (reused by §2 and §7).
    match: dict[str, dict] = {}
    for c in analysable:
        j = set(crosswalk.query("cohort == @c")["normalised_name"])
        matched, ambiguous, unmatched = match_journal_names(
            j, peer[c]["key_index"])
        matched_pids = set().union(*matched.values()) if matched else set()
        match[c] = {
            "journal_names": j, "matched": matched, "ambiguous": ambiguous,
            "unmatched": unmatched, "matched_pids": matched_pids,
        }

    add("# Journal ↔ peer-data linkage audit\n")
    add(f"_Generated by `src.qualitative.audit`. {len(entries)} journal files, "
        f"{crosswalk.shape[0]} distinct students, {len(journal_cohorts)} journal "
        f"cohorts._\n")

    # -- 1. Cohort coverage ------------------------------------------------- #
    add("## 1. Cohort coverage\n")
    add(f"- **Journal cohorts:** {', '.join(journal_cohorts)}")
    add(f"- **Peer-data cohorts:** {', '.join(peer_cohorts)}")
    add(f"- **Analysable intersection (RQ4 / Step-4 set):** "
        f"**{', '.join(analysable)}**")
    add(f"- **`calibration_only`** (journals, no peer data): "
        f"{', '.join(calibration_only) or 'none'} — held-out set for tuning the "
        f"sentiment pipeline without spending analysis data.")
    add(f"- **Peer-only** (peer data, no journals): "
        f"{', '.join(peer_only_cohorts) or 'none'} — these contribute "
        f"**nothing** to RQ4.\n")
    if not {"2024_s2", "2025_s1"} <= set(journal_cohorts):
        add("> ⚠️ **Stop-and-report:** the journal export does **not** extend to "
            "`2024_s2` / `2025_s1`. Those are the two largest peer files "
            "(~250 students each) and contribute nothing to RQ4 — the joined set "
            "is three cohorts, not five.\n")

    cov_rows = []
    for c in sorted(set(journal_cohorts) | set(peer_cohorts)):
        cov_rows.append({
            "cohort": c,
            "journal_students": crosswalk.query("cohort == @c").shape[0],
            "peer_students": len(peer.get(c, {}).get("persons", {})),
            "role": ("analysable" if c in analysable else
                     "calibration_only" if c in calibration_only else "peer_only"),
        })
    csvs["coverage_by_cohort"] = pd.DataFrame(cov_rows)

    # -- 2. Match rates ----------------------------------------------------- #
    add("## 2. Match rates (order-invariant normalised-name join)\n")
    add("Join key is the normalised name (lowercased, non-alphanumerics "
        "stripped). Matching is **order-invariant exact** — see note below the "
        "table — so it links regardless of whether a cohort's peer export is "
        "`Last, First` or `First Last`.\n")
    add("| cohort | journal | peer | matched | via reorder | ambiguous | "
        "journal-only | peer-only | unmatched |")
    add("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    unmatched_journal_rows, unmatched_peer_rows = [], []
    alerts: list[str] = []
    reorder_note = False
    for c in analysable:
        mc = match[c]
        j = mc["journal_names"]
        persons = peer[c]["persons"]
        simple = peer[c]["simple"]
        matched = mc["matched"]
        # how many matched only because we allowed reordering
        via_reorder = sum(1 for nn in matched if nn not in simple)
        if via_reorder:
            reorder_note = True
        peer_only_pids = set(persons) - mc["matched_pids"]
        j_only = sorted(mc["unmatched"])
        rate_unmatched = len(j_only) / len(j) if j else 0.0
        add(f"| {c} | {len(j)} | {len(persons)} | {len(matched)} | {via_reorder} "
            f"| {len(mc['ambiguous'])} | {len(j_only)} | {len(peer_only_pids)} | "
            f"{_fmt_pct(len(j_only), len(j))} |")
        for nn in j_only:
            unmatched_journal_rows.append({"cohort": c, "normalised_name": nn})
        for pid in sorted(peer_only_pids):
            unmatched_peer_rows.append(
                {"cohort": c, "name": persons[pid]["name"], "pid": pid})
        if rate_unmatched > UNMATCHED_ALERT:
            alerts.append(
                f"`{c}`: {_fmt_pct(len(j_only), len(j))} of journalling students "
                f"({len(j_only)}/{len(j)}) have no peer-data match")
    add("")
    add("> **Join method.** For each peer student we enumerate the plausible "
        "orderings of their name tokens (`last+first`, `first+last`, full "
        "reversed, last+first+middle) and match the journal-filename "
        "concatenation by **exact string equality**. This is not fuzzy "
        "matching — no edit distance, no scoring. `via reorder` counts journal "
        "students who matched only under a non-`Last,First` ordering; "
        "`ambiguous` counts journal names that hit more than one peer student "
        "(none should be double-counted downstream).\n")
    if reorder_note:
        add("> ℹ️ `2024_s1`'s peer CSV stores names as `First [Middle] Last` "
            "(no comma), unlike the `Last, First` format in the other cohorts. "
            "The order-invariant join recovers it; without reordering this "
            "cohort matched 0/92 and would have looked unusable.\n")
    if alerts:
        add("> ⚠️ **Stop-and-report — unmatched rate above "
            f"{UNMATCHED_ALERT:.0%}:**")
        for a in alerts:
            add(f"> - {a}")
        add("> Residual unmatched are name-change / enrolment-drop cases for Jos "
            "to reconcile against the cohort rosters. Names are in "
            "`unmatched_journal_only.csv`, not this report. Do **not** apply "
            "fuzzy matching.\n")
    else:
        add(f"> All analysable cohorts are within the {UNMATCHED_ALERT:.0%} "
            "unmatched threshold after the order-invariant join.\n")
    csvs["unmatched_journal_only"] = pd.DataFrame(unmatched_journal_rows)
    csvs["unmatched_peer_only"] = pd.DataFrame(unmatched_peer_rows)

    # -- 3. Collisions ------------------------------------------------------ #
    add("## 3. Name collisions within a cohort\n")
    collisions = crosswalk[crosswalk["id_collision"]]
    if collisions.empty:
        add("No normalised name maps to more than one Canvas ID within a cohort. "
            "The journal-side join key is unique per cohort.\n")
    else:
        add(f"**{len(collisions)}** normalised name(s) map to multiple Canvas IDs "
            "within a cohort (same collapsed name, distinct students). Reported, "
            "not auto-resolved — see `collisions.csv`. Jos's call.\n")
    ambiguous_total = sum(len(match[c]["ambiguous"]) for c in analysable)
    add(f"Cross-dataset ambiguous matches (one journal name → >1 peer student): "
        f"**{ambiguous_total}**.\n")
    csvs["collisions"] = collisions[["cohort", "normalised_name",
                                     "canvas_user_ids"]]

    # -- 4. Attrition ------------------------------------------------------- #
    add("## 4. Attrition\n")
    add("Entries per journal index (distinct students submitting each index):\n")
    add("| cohort | " + " | ".join(f"J{i}" for i in range(1, 6)) + " |")
    add("|---|" + "--:|" * 5)
    sub = entries.dropna(subset=["journal_index"]).copy()
    sub["journal_index"] = sub["journal_index"].astype(int)
    for c in journal_cohorts:
        cc = sub[sub["cohort"] == c]
        cells = []
        for i in range(1, 6):
            n = cc[cc["journal_index"] == i]["anon_id"].nunique()
            cells.append(str(n) if n else "–")
        add(f"| {c} | " + " | ".join(cells) + " |")
    add("")

    per_student = (
        sub.groupby(["cohort", "anon_id"])["journal_index"]
        .nunique().reset_index(name="indices_submitted")
    )
    csvs["attrition_per_student"] = per_student
    add("Distribution of *how many distinct journal indices* each student "
        "submitted:\n")
    add("| cohort | " + " | ".join(f"{i}×" for i in range(1, 6)) + " | median |")
    add("|---|" + "--:|" * 5 + "--:|")
    for c in journal_cohorts:
        cc = per_student[per_student["cohort"] == c]["indices_submitted"]
        cells = [str(int((cc == i).sum())) for i in range(1, 6)]
        add(f"| {c} | " + " | ".join(cells) + f" | {cc.median():.0f} |")
    add("")

    # -- 5. Lateness -------------------------------------------------------- #
    add("## 5. Lateness\n")
    add("`is_late` rate per journal index (share of entries):\n")
    add("| cohort | " + " | ".join(f"J{i}" for i in range(1, 6)) + " | overall |")
    add("|---|" + "--:|" * 5 + "--:|")
    for c in journal_cohorts:
        cc = sub[sub["cohort"] == c]
        cells = []
        for i in range(1, 6):
            idx = cc[cc["journal_index"] == i]
            cells.append(_fmt_pct(int(idx["is_late"].sum()), len(idx)) if len(idx)
                         else "–")
        overall = _fmt_pct(int(cc["is_late"].sum()), len(cc))
        add(f"| {c} | " + " | ".join(cells) + f" | {overall} |")
    add("")

    # -- 6. Extraction health ---------------------------------------------- #
    add("## 6. Extraction health\n")
    status_counts = entries["extract_status"].value_counts()
    add("| status | count |")
    add("|---|--:|")
    for s, n in status_counts.items():
        add(f"| {s} | {n} |")
    ok = entries[entries["extract_status"].isin(["ok", "extract_suspect"])]
    wc = ok["word_count"]
    add("")
    add(f"- Extraction success (ok+suspect): "
        f"{_fmt_pct(len(ok), len(entries))} ({len(ok)}/{len(entries)})")
    if len(wc):
        add(f"- word_count over extracted files: min {int(wc.min())}, "
            f"median {int(wc.median())}, mean {wc.mean():.0f}, max {int(wc.max())}")
    add(f"- `extract_suspect` (<50 words — likely screenshot-only): "
        f"{int((entries['extract_status'] == 'extract_suspect').sum())} "
        "(reported, not OCR'd)")
    add(f"- `unsupported` (.doc/.pages/.rtf/img — flagged, not converted): "
        f"{int((entries['extract_status'] == 'unsupported').sum())}")
    add(f"- `error` (extractor raised — likely mis-named format): "
        f"{int((entries['extract_status'] == 'error').sum())}\n")

    # -- 7. Team coverage --------------------------------------------------- #
    add("## 7. Team coverage  *(gates RQ3-EXT Step 4)*\n")
    add("For each peer-data team: members with ≥1 journal entry. A team where "
        "one of five members journaled cannot support a dispersion measure.\n")
    team_rows = []
    for c in analysable:
        matched_pids = match[c]["matched_pids"]
        for team, members in peer[c]["teams"].items():
            n_with = len(members & matched_pids)
            team_rows.append({
                "cohort": c, "team": team, "n_members": len(members),
                "n_with_journal": n_with,
                "coverage": round(n_with / len(members), 3) if members else 0.0,
            })
    team_df = pd.DataFrame(team_rows)
    csvs["team_coverage"] = team_df
    add("| cohort | teams | median members w/ journal | teams ≥3 covered | "
        "teams ≤1 covered |")
    add("|---|--:|--:|--:|--:|")
    thin_flag = False
    for c in analysable:
        cc = team_df[team_df["cohort"] == c]
        if cc.empty:
            continue
        median_cov = cc["n_with_journal"].median()
        ge3 = int((cc["n_with_journal"] >= 3).sum())
        le1 = int((cc["n_with_journal"] <= 1).sum())
        add(f"| {c} | {len(cc)} | {median_cov:.0f} | {ge3} | {le1} |")
        if le1 > len(cc) / 2:
            thin_flag = True
    add("")
    if thin_flag:
        add("> ⚠️ **Design flag for Step 4:** in at least one cohort, most teams "
            "have ≤1 journalling member — too thin to aggregate an archetype "
            "dispersion measure. Not papered over with a heuristic; flagged for "
            "Jos.\n")
    else:
        add("> Team-level journal coverage is sufficient to attempt within-team "
            "aggregation in the analysable cohorts.\n")

    # -- 8. Dates ----------------------------------------------------------- #
    add("## 8. Date recoverability (from document metadata)\n")
    add("Folder mtimes are all the export date (useless). Dates below come from "
        "PDF `/CreationDate` `/ModDate` and DOCX core properties.\n")
    add("| cohort | doc_created recoverable | doc_modified recoverable |")
    add("|---|--:|--:|")
    for c in journal_cohorts:
        cc = entries[entries["cohort"] == c]
        cr = (cc["doc_created"].fillna("").astype(str) != "").sum()
        mo = (cc["doc_modified"].fillna("").astype(str) != "").sum()
        add(f"| {c} | {_fmt_pct(int(cr), len(cc))} | {_fmt_pct(int(mo), len(cc))} |")
    total_cr = (entries["doc_created"].fillna("").astype(str) != "").sum()
    add("")
    add(f"- Overall `doc_created` recoverable: "
        f"{_fmt_pct(int(total_cr), len(entries))}. Where absent, the "
        "pre/post peer-feedback contamination check must fall back to ordinal "
        "journal position plus the COMPSCI 399 timetable.\n")

    # -- 9. Reflection template & archetype derivation --------------------- #
    add("## 9. Reflection template by cohort  *(handoff-6 Task 3)*\n")
    add("Classified from template text that recurs across many students (shared "
        "prompts, not individual answers).\n")
    tmpl = templates.classify_templates()
    add("| cohort | entries | explicit team-dynamics prompt? | prompt text |")
    add("|---|--:|:--:|---|")
    for c in sorted(tmpl):
        info = tmpl[c]
        prompts = "; ".join(info["team_prompts"]) or "—"
        add(f"| {c} | {info['n']} | "
            f"{'**yes**' if info['has_team_prompt'] else 'no'} | {prompts[:60]} |")
    add("")
    have = [c for c in sorted(tmpl) if tmpl[c]["has_team_prompt"]]
    havent = [c for c in sorted(tmpl) if not tmpl[c]["has_team_prompt"]]
    add(f"**{', '.join(f'`{c}`' for c in have)}** prompt team dynamics "
        f"explicitly; **{', '.join(f'`{c}`' for c in havent)}** use "
        "individual-reflection templates (objective description / analysis / "
        "articulation of learning / planning). **Consequence:** the template is "
        "not constant across cohorts, so a higher rate of team-dynamics content "
        "in a prompting cohort may reflect the *template*, not the cohort — it "
        "must not be read as that cohort being more troubled, and this confound "
        "must not carry into the main validation.\n")

    dbi = templates.dynamics_by_index()
    if dbi:
        idxs = sorted(dbi)
        add("Is `2024_s1`'s *\"assessment of team's dynamic\"* section spread "
            "across the semester or introduced late? (share of entries "
            "containing it, per journal index)\n")
        add("| | " + " | ".join(f"J{i}" for i in idxs) + " |")
        add("|---|" + "--:|" * len(idxs))
        add("| entries | " + " | ".join(str(dbi[i][0]) for i in idxs) + " |")
        add("| has prompt | " + " | ".join(f"{dbi[i][1]:.0f}%" for i in idxs) + " |")
        add("")
        j1 = dbi.get(1, (0, 0.0))[1]
        later = [dbi[i][1] for i in idxs if i > 1]
        if j1 < 10 and later and min(later) > 40:
            add(f"The section is **absent at J1 ({j1:.0f}%)** and present from J2 "
                f"on (~{min(later):.0f}–{max(later):.0f}%): it was **introduced "
                "after the first journal**, not randomly skipped — so J1 entries "
                "carry unprompted team content while J2–J5 carry prompted "
                "content, within the same cohort.\n")

    st = templates.archetype_derivation_stats()
    if st:
        add("### Team-archetype derivation (mean-load argmax)\n")
        add(f"Team archetypes use the **argmax of mean load** across a team's "
            f"question-matrices, not majority-vote of the per-matrix labels. Over "
            f"{st['n_teams']} teams, majority-vote is unanimous on "
            f"**{st['majority_unanimous']}**, ties on **{st['majority_ties']}**, "
            f"and mean-load agrees with the resolvable majority on "
            f"{st['meanload_eq_majority']}. Mean-load always resolves, so it is "
            "the primary label; the majority-vote column is kept alongside in the "
            "team keys for comparison.\n")

    return "\n".join(L), csvs


def run_audit() -> Path:
    entries, crosswalk = load_journal_side()
    peer = load_peer()
    report, csvs = build_report(entries, crosswalk, peer)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    for name, df in csvs.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)

    print(f"Wrote {REPORT} and {len(csvs)} supporting CSVs to {OUT_DIR}/")
    return REPORT


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(
        prog="python3 -m src.qualitative.audit",
        description="Audit journal ↔ peer-data linkage viability.",
    ).parse_args(argv)
    logging.disable(logging.CRITICAL)  # silence peer-parser diagnostics
    run_audit()


if __name__ == "__main__":
    main()
