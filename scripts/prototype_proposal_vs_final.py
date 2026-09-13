"""Prototype — can the EARLY (proposal-stage) peer cascade foreshadow the final one?

Context (2026-09-08). We recovered the per-session peer-feedback exports
(data/peer_sessions/), hoping to compute a cascade state per sprint and build a
retrospective early-warning study. On inspection the validated cascade parser only
reads the **points-distribution** question, and points are collected in exactly two
sessions: Session 1 (the *project proposal*) and the final session (source code /
report / poster). Sessions 2-3 carry only contribution-% + Likert, which the parser
ignores. So the existing instrument gives two cascade snapshots, not a trajectory:
an EARLY one (proposal) and the FINAL one (already in team_states.csv).

This script computes the proposal-stage pooled state for the four LLM-study cohorts
and cross-tabs it against the final pooled state, to see (a) how many teams are even
*comparable* at proposal stage (the proposal has a single points question, so N=4
teams fall to Silent-incomparable by construction), and (b) whether the early state
carries any signal about the final one.

Read-only. Run from repo root:  python3 -m scripts.prototype_proposal_vs_final
"""

from __future__ import annotations

import contextlib
import io
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from src.cascade import ranks
from src.cascade.pooled import classify_team
from src.parsing.parser import parse_session_with_diagnostics

# Study cohorts -> their Session-1 (proposal) export in data/peer_sessions/.
PROPOSAL = {
    "2023_s2": "data/peer_sessions/COMPSCI399-S2-2023_Peer_Session1.csv",
    "2024_s1": "data/peer_sessions/COMPSCI399-S1-2024_Peer_Session1.csv",
    "2024_s2": "data/peer_sessions/COMPSCI399-S2-2024_Peer_Session1.csv",
    "2025_s1": "data/peer_sessions/COMPSCI399-S1-2025_Peer_Session1.csv",
}
# Cohort code as it appears in the final team_states.csv csv_path.
COHORT_CODE = {"2023_s2": "S2-2023", "2024_s1": "S1-2024",
               "2024_s2": "S2-2024", "2025_s1": "S1-2025"}
FINAL_STATES = Path("output/dynamics2/pooled/team_states.csv")


def proposal_states(path: str) -> dict[str, str]:
    """team_name -> proposal-stage pooled cascade state for one Session-1 file."""
    with contextlib.redirect_stderr(io.StringIO()):
        matrices, _ = parse_session_with_diagnostics(Path(path))
    by_team: dict[str, list] = defaultdict(list)
    for (team, _q), sm in matrices.items():
        emails = [s.email for s in sm.students]
        by_team[team].append((emails, ranks.prepare_matrix(sm)))
    out: dict[str, str] = {}
    for team, items in by_team.items():
        out[team] = classify_team(items, key=(path, team)).state
    return out


def final_states() -> dict[tuple[str, str], str]:
    """(cohort_code, team_name) -> final pooled_state."""
    df = pd.read_csv(FINAL_STATES)
    out: dict[tuple[str, str], str] = {}
    for _, r in df.iterrows():
        code = next((c for c in COHORT_CODE.values() if c in r["csv_path"]), None)
        if code:
            out[(code, r["team_name"])] = r["pooled_state"]
    return out


def main() -> None:
    finals = final_states()
    rows = []
    for cohort, ppath in PROPOSAL.items():
        code = COHORT_CODE[cohort]
        early = proposal_states(ppath)
        for team, estate in early.items():
            fstate = finals.get((code, team), "(no final)")
            rows.append((cohort, team, estate, fstate))

    df = pd.DataFrame(rows, columns=["cohort", "team", "proposal_state", "final_state"])
    n = len(df)
    incomp = df["proposal_state"].str.startswith("Silent").sum()
    print(f"teams scored at proposal stage: {n}")
    print(f"  comparable (non-Silent) at proposal: {n - incomp}  "
          f"| Silent/incomparable: {incomp}  ({100*incomp/n:.0f}%)")
    print("\nproposal_state distribution:")
    print(df["proposal_state"].value_counts().to_string())
    print("\ncross-tab  proposal_state (rows)  ×  final_state (cols):")
    ct = pd.crosstab(df["proposal_state"], df["final_state"])
    print(ct.to_string())

    # Coarse signal: does a proposal flag (anyone-detached / contested) line up with
    # a final flag? Collapse to {flag, calm, silent}.
    def bucket(s: str) -> str:
        if s.startswith("Silent"):
            return "silent"
        if s in ("No standout",):
            return "calm"
        return "flag"  # Contested / One at bottom|top / Both ends
    df["prop_b"] = df["proposal_state"].map(bucket)
    df["fin_b"] = df["final_state"].map(lambda s: bucket(s) if isinstance(s, str) and s != "(no final)" else "?")
    print("\ncoarse buckets  proposal (rows) × final (cols):")
    print(pd.crosstab(df["prop_b"], df["fin_b"]).to_string())


if __name__ == "__main__":
    main()
