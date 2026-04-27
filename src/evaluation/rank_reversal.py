"""Rank reversal metrics for comparing IWF model outputs.

A rank reversal occurs when two models disagree on the relative ordering
of a pair of students.  Given a baseline model and an advanced model,
student A is "reversed" with student B when A ranks higher than B under
the baseline (by more than ``delta_iwf`` points) but lower under the
advanced model.

The ``delta_iwf`` threshold filters out trivially close pairs on the
**baseline** side only — if the baseline gap is meaningful and the
advanced model flips it, that counts regardless of the advanced gap size.

Units: ``delta_iwf`` is in **absolute IWF points** (scale ~0–60,
centred near 10 for typical teams).  Default 1.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from src.models.types import ModelResult


@dataclass(frozen=True)
class RankReversal:
    """A single reversed student pair between two models."""

    student_a: str
    """Student ranked higher under the baseline."""
    student_b: str
    """Student ranked lower under the baseline."""
    baseline_diff: float
    """A's baseline IWF minus B's baseline IWF (always > 0)."""
    advanced_diff: float
    """A's advanced IWF minus B's advanced IWF (negative = reversed)."""

    @property
    def magnitude(self) -> float:
        """Total swing: how far apart they were plus how far they crossed."""
        return abs(self.baseline_diff) + abs(self.advanced_diff)


@dataclass(frozen=True)
class RankReversalSummary:
    """Aggregate reversal statistics for one model pair on one team."""

    baseline_model: str
    advanced_model: str
    reversals: list[RankReversal] = field(default_factory=list)
    eligible_pair_count: int = 0
    """Pairs where both students have non-NaN IWFs in both models."""
    all_pair_count: int = 0
    """n*(n-1)/2 total possible pairs."""

    @property
    def reversal_count(self) -> int:
        return len(self.reversals)

    @property
    def reversal_rate(self) -> float:
        """Fraction of eligible pairs that are reversed."""
        if self.eligible_pair_count == 0:
            return 0.0
        return self.reversal_count / self.eligible_pair_count


def compute_rank_reversals(
    baseline: ModelResult,
    advanced: ModelResult,
    delta_iwf: float = 1.5,
) -> RankReversalSummary:
    """Compare two model results and find rank reversals.

    Parameters
    ----------
    baseline:
        The reference model result (typically Simple Average).
    advanced:
        The model result to compare against the baseline.
    delta_iwf:
        Minimum absolute IWF gap on the **baseline** side for a pair
        to be eligible.  Default 1.5 IWF points.

    Returns
    -------
    RankReversalSummary with all reversed pairs and aggregate rates.

    Raises
    ------
    ValueError
        If the two results have different student lists.
    """
    if len(baseline.students) != len(advanced.students):
        raise ValueError(
            f"Student count mismatch: baseline has {len(baseline.students)}, "
            f"advanced has {len(advanced.students)}"
        )

    n = len(baseline.students)
    all_pair_count = n * (n - 1) // 2

    b_iwf = baseline.iwf_vector
    a_iwf = advanced.iwf_vector

    reversals: list[RankReversal] = []
    eligible = 0

    for i, j in combinations(range(n), 2):
        b_i, b_j = float(b_iwf[i]), float(b_iwf[j])
        a_i, a_j = float(a_iwf[i]), float(a_iwf[j])

        # Skip pairs where either student has NaN in either model
        if np.isnan(b_i) or np.isnan(b_j) or np.isnan(a_i) or np.isnan(a_j):
            continue

        # Orient so student_a is the higher-ranked under baseline
        if b_i >= b_j:
            high_idx, low_idx = i, j
            baseline_diff = b_i - b_j
            advanced_diff = a_i - a_j
        else:
            high_idx, low_idx = j, i
            baseline_diff = b_j - b_i
            advanced_diff = a_j - a_i

        # Baseline gap must exceed δ for the pair to be eligible
        if baseline_diff < delta_iwf:
            continue

        eligible += 1

        # A reversal occurs when the advanced model flips the ordering
        if advanced_diff < 0:
            reversals.append(RankReversal(
                student_a=baseline.students[high_idx].name,
                student_b=baseline.students[low_idx].name,
                baseline_diff=round(baseline_diff, 4),
                advanced_diff=round(advanced_diff, 4),
            ))

    return RankReversalSummary(
        baseline_model=baseline.model_name,
        advanced_model=advanced.model_name,
        reversals=reversals,
        eligible_pair_count=eligible,
        all_pair_count=all_pair_count,
    )
