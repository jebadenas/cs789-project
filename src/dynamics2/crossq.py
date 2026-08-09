"""Cross-question consistency — team level.

Each team was rated on **source code**, **group report** and **showcase poster**
— three near-independent measurements the current pipeline treats as unrelated
rows. If the same person sits at the bottom of all three, that is replication
the study is currently throwing away; if the bottom moves between tasks, the
low score is task-specific rather than a standing free-rider pattern.

Consensus vectors are keyed by **student email** (team numbers recur across
cohorts, so teams are keyed on ``(csv_path, team_name)`` and members on email).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

from src.dynamics2 import ranks
from src.dynamics2.dataio import MatrixRecord

MIN_QUALIFYING_RATERS = 2   # a question is "readable" iff ≥2 qualifying raters ordered it
MIN_COMMON_MEMBERS = 3      # ≥ this many shared members to compute a cross-question τ-b


@dataclass(frozen=True)
class CrossQRow:
    csv_path: str
    team_name: str
    n_readable_questions: int
    same_bottom_count: int
    distinct_bottoms: int
    cross_q_tau: float
    bottom_email: str
    verdict: str


def consensus_by_email(sm) -> dict[str, float]:
    """Per-question consensus vector keyed by student email (finite entries only)."""
    mat = ranks.prepare_matrix(sm)
    cons = ranks.consensus_vector(mat)
    emails = [s.email for s in sm.students]
    return {emails[i]: float(cons[i]) for i in range(len(emails)) if np.isfinite(cons[i])}


def analyse_team(records: list[MatrixRecord]) -> CrossQRow:
    """Cross-question verdict for one team's question-matrices."""
    csv_path = records[0].csv_path
    team_name = records[0].team_name

    # A question is "readable" iff ≥2 qualifying raters expressed an ordering, so
    # the consensus reflects genuine multi-rater agreement rather than one voice.
    readable: list[tuple[str, dict[str, float]]] = []
    for rec in records:
        mat = ranks.prepare_matrix(rec.sm)
        if int(ranks.qualifying_raters(mat).sum()) < MIN_QUALIFYING_RATERS:
            continue
        cons = consensus_by_email(rec.sm)
        if len(cons) >= 2:
            readable.append((rec.question_label, cons))

    if len(readable) < 2:
        return CrossQRow(csv_path, team_name, len(readable), 0, 0,
                        float("nan"), "", "insufficient")

    # Bottom (worst mean normalised rank = argmin) per readable question.
    bottoms = [min(cons, key=cons.get) for _, cons in readable]
    counts = Counter(bottoms)
    modal_email, same_bottom_count = counts.most_common(1)[0]
    distinct_bottoms = len(counts)

    # Cross-question agreement: mean pairwise τ-b between consensus vectors.
    taus: list[float] = []
    for a in range(len(readable)):
        for b in range(a + 1, len(readable)):
            ca, cb = readable[a][1], readable[b][1]
            common = sorted(set(ca) & set(cb))
            if len(common) < MIN_COMMON_MEMBERS:
                continue
            x = np.array([ca[e] for e in common])
            y = np.array([cb[e] for e in common])
            t = ranks.tau_b(x, y)
            if np.isfinite(t):
                taus.append(t)
    cross_q_tau = float(np.mean(taus)) if taus else float("nan")

    if distinct_bottoms == 1:
        verdict = "consistent"
    elif same_bottom_count >= 2:
        verdict = "mostly consistent"
    else:
        verdict = "task-specific"

    return CrossQRow(
        csv_path=csv_path, team_name=team_name,
        n_readable_questions=len(readable),
        same_bottom_count=same_bottom_count,
        distinct_bottoms=distinct_bottoms,
        cross_q_tau=cross_q_tau,
        bottom_email=modal_email,
        verdict=verdict,
    )


def group_by_team(records: list[MatrixRecord]) -> dict[tuple[str, str], list[MatrixRecord]]:
    """Group matrix records by ``(csv_path, team_name)``."""
    teams: dict[tuple[str, str], list[MatrixRecord]] = defaultdict(list)
    for rec in records:
        teams[(rec.csv_path, rec.team_name)].append(rec)
    return teams
