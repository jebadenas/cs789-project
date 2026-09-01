"""Tests for the synthetic validation harness (handoff-10).

The cascade under test is not modified here; these guard the generator (CS399
form, reproducibility) and the harness bookkeeping.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.attacks.synthetic import generate_team
from src.dynamics2 import gates, validate as V


class TestGeneratorCS399Form:

    @pytest.mark.parametrize("n", [4, 5, 6])
    def test_budget_is_exactly_10N_including_self(self, n):
        for planter in V.PLANTERS.values():
            team = planter(n, 123)
            m = team.score_matrix.matrix
            colsums = np.nansum(m, axis=0)
            np.testing.assert_allclose(colsums, 10.0 * n, atol=1e-9)

    @pytest.mark.parametrize("n", [4, 5, 6])
    def test_diagonal_is_populated(self, n):
        team = V.plant_one_at_bottom(n, 1)
        assert np.all(np.isfinite(np.diag(team.score_matrix.matrix)))

    def test_default_generator_still_excludes_self(self):
        # Backward compatibility: the attack-suite default leaves the diagonal NaN.
        m = generate_team(5, 0).score_matrix.matrix
        assert np.all(np.isnan(np.diag(m)))
        assert np.nansum(m[:, 0]) == pytest.approx(40.0)  # pool = 10·(n−1)

    def test_non_differentiating_is_exactly_flat(self):
        team = V.plant_non_differentiating(6, 3)
        off = team.score_matrix.matrix[~np.eye(6, dtype=bool)]
        assert np.allclose(off, off[0])


class TestReproducibility:

    def test_same_seed_same_matrix(self):
        a = V.plant_one_at_bottom(6, 42, delta=6.0).score_matrix.matrix
        b = V.plant_one_at_bottom(6, 42, delta=6.0).score_matrix.matrix
        np.testing.assert_array_equal(np.nan_to_num(a), np.nan_to_num(b))

    def test_confusion_reproduces_bit_for_bit(self):
        c1 = V.run_confusion(replicates=2, n_perm=50, progress=False)
        c2 = V.run_confusion(replicates=2, n_perm=50, progress=False)
        assert list(c1["recovered"]) == list(c2["recovered"])


class TestRecoverySmoke:

    def test_large_gap_free_rider_recovered_at_n6(self):
        # An egregious free-rider on a 6-person team is caught and correctly named.
        hits = 0
        for rep in range(6):
            team = V.plant_one_at_bottom(6, 300 + rep, delta=9.0, target=rep % 6)
            r = V.classify_team(team, "One at bottom", n_perm=500)
            hits += (r.state == gates.ONE_AT_BOTTOM and r.bottom_member == rep % 6)
        assert hits >= 3  # majority recovered (N=6 power is moderate, not perfect)

    def test_non_differentiating_recovers_silent_flat(self):
        r = V.classify_team(V.plant_non_differentiating(6, 7), "Non-differentiating", n_perm=100)
        assert r.state == gates.SILENT_FLAT


class TestHarnessBookkeeping:

    def test_confusion_rows_sum_to_planted_counts(self):
        reps = 3
        conf = V.run_confusion(replicates=reps, n_perm=50, progress=False)
        counts = conf.groupby("planted").size()
        for planted in V.PLANTERS:
            assert counts[planted] == reps * len(V.SIZES)

    def test_wilson_interval_bounds(self):
        p, lo, hi = V.wilson(8, 10)
        assert 0 <= lo <= p <= hi <= 1
        assert V.wilson(0, 0)[0] != V.wilson(0, 0)[0]  # NaN for n=0
