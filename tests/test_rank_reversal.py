"""Tests for rank reversal metric."""

from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.rank_reversal import (
    RankReversal,
    RankReversalSummary,
    compute_rank_reversals,
)
from src.models.types import ModelResult
from src.parsing.schemas import StudentInfo


def _make_result(
    model_name: str,
    iwfs: list[float],
    names: list[str] | None = None,
) -> ModelResult:
    """Helper to build a ModelResult from a list of IWFs."""
    n = len(iwfs)
    if names is None:
        names = [f"Student_{i}" for i in range(n)]
    students = [
        StudentInfo(name=names[i], email=f"{names[i].lower()}@test.com", index=i)
        for i in range(n)
    ]
    return ModelResult(
        model_name=model_name,
        iwf_vector=np.array(iwfs, dtype=float),
        students=students,
    )


# --- Hand-computed cases ---


class TestHandComputed:
    """Verify against hand-calculated examples."""

    def test_clear_reversals(self):
        """3 students: baseline [12, 10, 8], advanced [9, 11, 10].

        Baseline ranking: A > B > C
        Advanced ranking: B > C > A

        Eligible pairs (δ=1.5):
          A–B: baseline diff 2.0 > 1.5 ✓ → advanced diff 9-11 = -2 → REVERSED
          A–C: baseline diff 4.0 > 1.5 ✓ → advanced diff 9-10 = -1 → REVERSED
          B–C: baseline diff 2.0 > 1.5 ✓ → advanced diff 11-10 = 1 → not reversed

        Expected: 2 reversals, 3 eligible pairs, rate = 2/3
        """
        baseline = _make_result("baseline", [12.0, 10.0, 8.0], ["A", "B", "C"])
        advanced = _make_result("peerrank", [9.0, 11.0, 10.0], ["A", "B", "C"])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.reversal_count == 2
        assert summary.eligible_pair_count == 3
        assert summary.all_pair_count == 3
        assert summary.reversal_rate == pytest.approx(2 / 3)
        assert summary.baseline_model == "baseline"
        assert summary.advanced_model == "peerrank"

        # Check specific reversals
        reversed_pairs = {(r.student_a, r.student_b) for r in summary.reversals}
        assert ("A", "B") in reversed_pairs
        assert ("A", "C") in reversed_pairs

    def test_no_reversals_same_ranking(self):
        """Models agree on ordering — no reversals."""
        baseline = _make_result("baseline", [12.0, 10.0, 8.0])
        advanced = _make_result("peerrank", [14.0, 10.0, 6.0])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.reversal_count == 0
        assert summary.eligible_pair_count == 3
        assert summary.reversal_rate == 0.0

    def test_single_reversal(self):
        """Only one pair reverses."""
        baseline = _make_result("baseline", [12.0, 10.0, 5.0], ["A", "B", "C"])
        advanced = _make_result("webpa", [9.5, 10.5, 10.0], ["A", "B", "C"])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        # A–B: baseline diff 2.0 > 1.5 ✓, advanced diff 9.5-10.5=-1.0 → REVERSED
        # A–C: baseline diff 7.0 > 1.5 ✓, advanced diff 9.5-10.0=-0.5 → REVERSED
        # B–C: baseline diff 5.0 > 1.5 ✓, advanced diff 10.5-10.0=0.5 → not reversed
        assert summary.reversal_count == 2
        assert summary.eligible_pair_count == 3


# --- Edge cases ---


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_all_tied(self):
        """All students at 10.0 — no pairs exceed δ."""
        baseline = _make_result("baseline", [10.0, 10.0, 10.0, 10.0])
        advanced = _make_result("peerrank", [10.1, 9.9, 10.2, 9.8])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.eligible_pair_count == 0
        assert summary.reversal_count == 0
        assert summary.reversal_rate == 0.0
        assert summary.all_pair_count == 6  # 4C2

    def test_two_students(self):
        """Minimum team size — one pair."""
        baseline = _make_result("baseline", [12.0, 8.0], ["A", "B"])
        advanced = _make_result("peerrank", [7.0, 13.0], ["A", "B"])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.all_pair_count == 1
        assert summary.eligible_pair_count == 1
        assert summary.reversal_count == 1

    def test_delta_filters_small_gaps(self):
        """Pair with baseline gap < δ is not eligible."""
        baseline = _make_result("baseline", [10.5, 10.0, 5.0], ["A", "B", "C"])
        advanced = _make_result("peerrank", [9.0, 11.0, 10.0], ["A", "B", "C"])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        # A–B: baseline diff 0.5 < 1.5 → NOT eligible
        # A–C: baseline diff 5.5 > 1.5 ✓ → advanced diff 9-10=-1 → REVERSED
        # B–C: baseline diff 5.0 > 1.5 ✓ → advanced diff 11-10=1 → not reversed
        assert summary.eligible_pair_count == 2
        assert summary.reversal_count == 1

    def test_magnitude_property(self):
        """RankReversal.magnitude = |baseline_diff| + |advanced_diff|."""
        baseline = _make_result("baseline", [15.0, 5.0])
        advanced = _make_result("peerrank", [4.0, 16.0])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert len(summary.reversals) == 1
        r = summary.reversals[0]
        assert r.baseline_diff == pytest.approx(10.0)
        assert r.advanced_diff == pytest.approx(-12.0)
        assert r.magnitude == pytest.approx(22.0)


# --- NaN handling ---


class TestNaNHandling:
    """Non-submitter (NaN) students should be excluded from pairs."""

    def test_nan_in_baseline_skips_pair(self):
        """Student with NaN baseline IWF is excluded from all pairs."""
        baseline = _make_result("baseline", [12.0, float("nan"), 8.0])
        advanced = _make_result("peerrank", [9.0, 11.0, 10.0])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        # Only pair 0–2 is eligible (student 1 has NaN baseline)
        assert summary.all_pair_count == 3
        assert summary.eligible_pair_count == 1  # Only A–C
        assert summary.reversal_count == 1  # A was 12, C was 8 → A ahead; advanced A=9 < C=10 → reversed

    def test_nan_in_advanced_skips_pair(self):
        """Student with NaN advanced IWF is excluded from all pairs."""
        baseline = _make_result("baseline", [12.0, 10.0, 8.0])
        advanced = _make_result("peerrank-exclude", [9.0, float("nan"), 10.0])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        # Student 1 has NaN in advanced → only pair 0–2 eligible
        assert summary.eligible_pair_count == 1
        assert summary.reversal_count == 1

    def test_all_nan_returns_zero(self):
        """All NaN → no eligible pairs."""
        baseline = _make_result("baseline", [float("nan")] * 3)
        advanced = _make_result("peerrank", [float("nan")] * 3)

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.eligible_pair_count == 0
        assert summary.reversal_count == 0
        assert summary.reversal_rate == 0.0


# --- Properties ---


class TestProperties:
    """Invariant checks."""

    def test_reversal_count_bounded(self):
        """Reversal count ≤ eligible pairs ≤ all pairs."""
        baseline = _make_result("baseline", [15.0, 12.0, 9.0, 6.0, 3.0])
        advanced = _make_result("peerrank", [3.0, 6.0, 9.0, 12.0, 15.0])

        summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)

        assert summary.reversal_count <= summary.eligible_pair_count
        assert summary.eligible_pair_count <= summary.all_pair_count
        assert summary.all_pair_count == 10  # 5C2

    def test_reversal_rate_between_0_and_1(self):
        """Rate is always in [0, 1]."""
        for iwfs in [[15, 12, 9, 6, 3], [10, 10, 10, 10, 10], [20, 5, 5, 5, 5]]:
            baseline = _make_result("baseline", [float(x) for x in iwfs])
            # Reverse the ordering
            advanced = _make_result("peerrank", [float(x) for x in reversed(iwfs)])
            summary = compute_rank_reversals(baseline, advanced, delta_iwf=1.5)
            assert 0.0 <= summary.reversal_rate <= 1.0

    def test_mismatched_student_count_raises(self):
        """Different student counts should raise ValueError."""
        baseline = _make_result("baseline", [10.0, 10.0, 10.0])
        advanced = _make_result("peerrank", [10.0, 10.0])

        with pytest.raises(ValueError, match="Student count mismatch"):
            compute_rank_reversals(baseline, advanced)
