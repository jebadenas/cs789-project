"""Regression tests for the model-implementation audit fixes (handoff-9).

Covers the two-sided Task 1 finding (the WebPA normalisation is implemented, and
is provably a no-op on the real fixed-budget data), the Task 2 baseline scaling
and its regression guard across all four models, and the PeerRank correctness
checks against Walsh's stated worked-example results.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.dynamics2.dataio import load_matrices
from src.models.baseline import baseline_average
from src.models.peerhits import peerhits
from src.models.peerrank import peerrank
from src.models.webpa import webpa
from src.parsing.schemas import ScoreMatrix, StudentInfo


def _mk(matrix: np.ndarray) -> ScoreMatrix:
    n = matrix.shape[0]
    return ScoreMatrix(
        matrix=matrix, team_name="T", question_label="q",
        year="2024", semester="S1", session_number=1,
        students=[StudentInfo(name=f"S{i}", email=f"s{i}@t.ac.nz", index=i)
                  for i in range(n)],
    )


def _webpa_unnormalised(m: np.ndarray) -> np.ndarray:
    """The previous webpa.py: received-sum ratio, no per-rater normalisation."""
    rec = np.nansum(m, axis=1)
    return rec / rec.mean() * 10.0


# --------------------------------------------------------------------------- #
# Task 1 — WebPA normalisation: implemented, and a no-op on real data
# --------------------------------------------------------------------------- #

class TestWebPANormalisation:

    def test_synthetic_unequal_totals_fractions_sum_to_one_and_differ(self):
        """With deliberately unequal rater totals the normalisation is NOT a no-op:
        each rater's fractional scores sum to 1, and the result differs from the
        un-normalised received-sum ratio."""
        # Rater column sums are 10, 20, 40 — deliberately unequal.
        matrix = np.array([
            [5.0,  4.0,  8.0],
            [3.0, 10.0, 20.0],
            [2.0,  6.0, 12.0],
        ])
        # Fractional scores per rater sum to 1.
        fractional = matrix / matrix.sum(axis=0)
        np.testing.assert_allclose(fractional.sum(axis=0), np.ones(3))

        got = webpa(_mk(matrix)).iwf_vector
        received = fractional.sum(axis=1)
        expected = received / received.mean() * 10.0
        np.testing.assert_allclose(got, expected)

        # And it genuinely differs from the un-normalised version.
        assert not np.allclose(got, _webpa_unnormalised(matrix))

    def test_real_data_normalisation_is_a_noop(self):
        """On all 417 real matrices (fixed budget including self), canonical WebPA
        is identical to the un-normalised implementation — the Task 1 finding."""
        worst = 0.0
        for rec in load_matrices():
            m = rec.sm.matrix.astype(float)
            got = webpa(rec.sm).iwf_vector
            ref = _webpa_unnormalised(m)
            mask = ~(np.isnan(got) | np.isnan(ref))
            worst = max(worst, float(np.max(np.abs(got[mask] - ref[mask]))))
        assert worst < 1e-9, f"WebPA normalisation is not a no-op on real data (max|Δ|={worst})"


# --------------------------------------------------------------------------- #
# Task 2 — scaling to team mean 10.0
# --------------------------------------------------------------------------- #

class TestTeamMeanScaling:

    def test_baseline_team_mean_is_ten_on_every_matrix(self):
        for rec in load_matrices():
            mean = float(np.nanmean(baseline_average(rec.sm).iwf_vector))
            assert mean == pytest.approx(10.0), f"{rec.team_name}: baseline mean {mean}"

    def test_all_models_team_mean_is_ten(self):
        """Regression guard for the Task 2 bug class: every model at mean 10.0."""
        for rec in load_matrices():
            for name, fn in (("baseline", baseline_average), ("webpa", webpa),
                             ("peerhits", peerhits)):
                mean = float(np.nanmean(fn(rec.sm).iwf_vector))
                assert mean == pytest.approx(10.0), f"{name} {rec.team_name}: mean {mean}"
            try:
                pr = peerrank(rec.sm)
            except ValueError:
                continue  # all-zero peer column — legitimately undefined
            assert float(np.nanmean(pr.iwf_vector)) == pytest.approx(10.0)


# --------------------------------------------------------------------------- #
# Task 9 — PeerRank against Walsh's stated worked-example results
# --------------------------------------------------------------------------- #

class TestPeerRankWalshExamples:

    def test_unanimous_grades_give_equal_iwf(self):
        """Walsh: a unanimous grade matrix converges to everyone equal. Under the
        mean-10 scaling here, 'everyone gets k' becomes 'everyone gets 10'."""
        result = peerrank(_mk(np.full((5, 5), 7.0)))
        np.testing.assert_allclose(result.iwf_vector, np.full(5, 10.0))

    def test_uniform_peer_allocation_gives_equal_iwf(self):
        """No discriminating signal (uniform off-diagonal) → uniform IWF — the
        self-excluded analogue of Walsh's identity → 1/m result."""
        result = peerrank(_mk(np.full((4, 4), 3.0)))
        np.testing.assert_allclose(result.iwf_vector, np.full(4, 10.0))

    def test_consensus_ranking_is_preserved_and_converges(self):
        """When all raters agree on a strict ranking, PeerRank preserves it."""
        base = np.array([12.0, 9.0, 6.0, 3.0])
        matrix = np.tile(base.reshape(-1, 1), (1, 4))  # every rater gives recipient i = base[i]
        result = peerrank(_mk(matrix))
        assert result.converged
        assert np.all(np.diff(result.iwf_vector) < 0)  # strictly decreasing

    def test_identity_is_degenerate_under_self_exclusion(self):
        """Walsh's identity → 1/m example does not map: this variant zeroes the
        diagonal (declared deviation), so an identity matrix has all-zero peer
        columns and is correctly rejected."""
        with pytest.raises(ValueError):
            peerrank(_mk(np.eye(4)))
