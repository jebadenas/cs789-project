"""Stratified team-level sampler for the hand-labelled anchor set (Task 1).

Selects ~40 of the 139 teams for blind hand-labelling, stratified so every AA
k=4 archetype and the Anomalous tail are represented — the rare cells are
oversampled, not sampled proportionally (rubric §4). The output CSV is *for the
record only* and is NEVER shown to raters (it carries the archetype/flag the
blinding exists to hide).

Design decisions (see docs/labelling-design.md):
  * Unit = team, keyed by (csv_path, team_name). Team *numbers* recur across
    cohorts ("Team 6" is three different teams), so the session file is part of
    the identity.
  * Per-matrix archetype comes from output/dynamics/aa_k4_assignments.csv
    (persisted AA k=4 refit — never re-fit here). The deprecated `dynamic_label`
    column in classifications.csv is NOT used.
  * Team-level archetype = majority across the team's 3 question-matrices; no
    majority -> "Mixed" (a real stratum, not force-fit). Team flag = Anomalous
    if ANY of its matrices is flagged.
  * Exemplars are *fill-don't-expand* calibration anchors: the quota is fixed
    first, and exemplar owner-teams are merely preferred when filling a cell's
    slots. Team 6 "Caffeine Overload" is force-included.

Run:
    python3 -m src.labelling.sample

Output: output/labelling/labelling_sample.csv (+ printed cell counts).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.dynamics.mixture import ensure_assignments
from src.labelling.constants import QUESTIONS

DYN = Path("output/dynamics")
OUT = Path("output/labelling")
SEED = 42

# ~40-team quota over {archetype} x {flag}. Rare cells oversampled, A1 (flat)
# capped, A2 taken as a full census, Mixed ~5. See docs/labelling-design.md.
QUOTA: dict[tuple[str, str], int] = {
    ("A0", "Anomalous"): 6, ("A0", "Typical"): 4,
    ("A1", "Anomalous"): 3, ("A1", "Typical"): 4,   # capped: flat is trivial
    ("A2", "Anomalous"): 5, ("A2", "Typical"): 2,   # full census of the tail
    ("A3", "Anomalous"): 5, ("A3", "Typical"): 6,
    ("Mixed", "Anomalous"): 3, ("Mixed", "Typical"): 2,
}

FORCE_TEAM = "Team 6 - Caffeine Overload"  # known high-Δ non-submitter case


def team_id(csv_path: str, team_name: str) -> str:
    return f"{csv_path} :: {team_name}"


def build_team_table() -> pd.DataFrame:
    """Aggregate the per-matrix AA assignments to one row per team."""
    asg = ensure_assignments()
    asg["team_id"] = [team_id(c, t) for c, t in
                      zip(asg["csv_path"], asg["team_name"])]

    rows = []
    for tid, g in asg.groupby("team_id", sort=False):
        g = g.set_index("question_label")
        # majority archetype across the (up to 3) matrices; tie -> Mixed
        vc = g["archetype"].value_counts()
        top = vc[vc == vc.max()].index.tolist()
        archetype = top[0] if len(top) == 1 else "Mixed"
        flag = "Anomalous" if (g["atypicality_flag"] == "Anomalous").any() \
            else "Typical"
        row = {
            "team_id": tid,
            "csv_path": g["csv_path"].iloc[0],
            "team_name": g["team_name"].iloc[0],
            "archetype": archetype,
            "flag": flag,
            "n_questions": len(g),
        }
        for q in QUESTIONS:
            row[f"arch_{_slug(q)}"] = g["archetype"].get(q, "")
        rows.append(row)
    return pd.DataFrame(rows)


def _slug(question: str) -> str:
    return question.replace(" ", "_")


def exemplar_owner_teams() -> set[str]:
    """Team ids that own at least one archetype exemplar matrix."""
    ex = pd.read_csv(DYN / "archetype_exemplars.csv")
    return {team_id(c, t) for c, t in zip(ex["csv_path"], ex["team_name"])}


def draw(teams: pd.DataFrame) -> pd.DataFrame:
    """Fill each (archetype, flag) cell to quota, preferring anchors.

    Order within a cell: forced team first, then exemplar owner-teams, then a
    seeded random fill of the remainder. Records shortfalls rather than silently
    shrinking the design.
    """
    rng = np.random.default_rng(SEED)
    anchors = exemplar_owner_teams()
    forced = set(teams.loc[teams["team_name"] == FORCE_TEAM, "team_id"])

    picked, report = [], []
    for (arch, flag), quota in QUOTA.items():
        cell = teams[(teams["archetype"] == arch) & (teams["flag"] == flag)]
        ids = list(cell["team_id"])
        pri = ([t for t in ids if t in forced]
               + [t for t in ids if t in anchors and t not in forced])
        rest = [t for t in ids if t not in forced and t not in anchors]
        rng.shuffle(rest)
        ordered = pri + rest
        take = ordered[:quota]
        picked.extend(take)
        report.append({
            "archetype": arch, "flag": flag, "quota": quota,
            "available": len(ids), "picked": len(take),
            "anchors_used": len([t for t in take if t in anchors or t in forced]),
            "shortfall": max(0, quota - len(ids)),
        })

    sample = teams[teams["team_id"].isin(picked)].copy()
    sample["is_anchor"] = sample["team_id"].isin(anchors | forced)
    sample["is_forced"] = sample["team_id"].isin(forced)
    return sample, pd.DataFrame(report)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    teams = build_team_table()
    print(f"Population: {len(teams)} teams")
    print(pd.crosstab(teams["archetype"], teams["flag"]).to_string())

    sample, report = draw(teams)
    cols = (["team_id", "csv_path", "team_name", "archetype", "flag",
             "n_questions"]
            + [f"arch_{_slug(q)}" for q in QUESTIONS]
            + ["is_anchor", "is_forced"])
    sample[cols].to_csv(OUT / "labelling_sample.csv", index=False)

    print(f"\nSampled {len(sample)} teams (target {sum(QUOTA.values())}) "
          f"-> output/labelling/labelling_sample.csv  [NEVER shown to raters]")
    print(report.to_string(index=False))
    if (report["shortfall"] > 0).any():
        print("\n*** STOP-AND-REPORT: a cell could not be filled — see shortfall "
              "column. Do not silently shrink the design; decide with Jos.")


if __name__ == "__main__":
    main()
