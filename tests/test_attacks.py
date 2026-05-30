"""Tests for the synthetic attack simulation (Phase 4, RQ1/RQ2).

Covers the Phase-4 acceptance criteria: generator determinism + budget
conservation, the four attack transforms' defining behaviours, Attack
Delta correctness, and the single-outlier Monte-Carlo harness.
"""

import numpy as np
import pytest

from src.attacks.delta import attack_delta, monte_carlo_single_outlier
from src.attacks.runner import run_attacks
from src.attacks.synthetic import generate_cohort, generate_team
from src.attacks.transforms import (
    single_outlier,
    targeted_downvote,
    uniform_inflation,
    zero_self,
)
from src.models.baseline import baseline_average
from src.models.peerrank_exclude import peerrank_exclude


def _baseline_iwf(sm):
    return baseline_average(sm).iwf_vector


class TestGenerator:
    def test_deterministic_for_seed(self):
        a = generate_team(5, seed=42)
        b = generate_team(5, seed=42)
        np.testing.assert_array_equal(a.score_matrix.matrix, b.score_matrix.matrix)
        np.testing.assert_array_equal(a.ground_truth, b.ground_truth)

    def test_different_seeds_differ(self):
        a = generate_team(5, seed=1)
        b = generate_team(5, seed=2)
        assert not np.allclose(a.score_matrix.matrix, b.score_matrix.matrix,
                               equal_nan=True)

    @pytest.mark.parametrize("n", [4, 5, 6])
    def test_sizes_and_shape(self, n):
        t = generate_team(n, seed=0)
        assert t.score_matrix.matrix.shape == (n, n)
        assert len(t.ground_truth) == n

    def test_diagonal_is_nan(self):
        m = generate_team(6, seed=3).score_matrix.matrix
        assert np.all(np.isnan(np.diag(m)))

    def test_budget_conserved_to_pool(self):
        n = 5
        t = generate_team(n, seed=7)
        pool = 10.0 * (n - 1)
        np.testing.assert_allclose(
            np.nansum(t.score_matrix.matrix, axis=0), pool
        )

    def test_reliable_panel_recovers_ground_truth(self):
        # On a clean reliable panel the baseline IWF should track truth.
        maes = []
        for s in range(30):
            t = generate_team(5, seed=s, profile="reliable")
            maes.append(np.mean(np.abs(_baseline_iwf(t.score_matrix)
                                       - t.ground_truth)))
        assert np.mean(maes) < 1.5

    def test_lazy_profile_degrades_recovery(self):
        def mae(profile):
            vals = []
            for s in range(20):
                t = generate_team(5, seed=s, profile=profile)
                vals.append(np.mean(np.abs(_baseline_iwf(t.score_matrix)
                                           - t.ground_truth)))
            return np.mean(vals)

        assert mae("lazy") > mae("reliable")

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError):
            generate_team(5, seed=0, profile="nope")


class TestUniformInflation:
    def test_baseline_iwf_collapses_to_ten(self):
        # Default pool = 10*(N-1) ⇒ per-recipient share = 10.
        t = generate_team(5, seed=11)
        atk = uniform_inflation(t.score_matrix)
        np.testing.assert_allclose(_baseline_iwf(atk), 10.0, atol=1e-9)

    def test_budget_conserved(self):
        sm = generate_team(6, seed=2).score_matrix
        before = np.nansum(sm.matrix, axis=0)
        after = np.nansum(uniform_inflation(sm).matrix, axis=0)
        np.testing.assert_allclose(after, before)

    def test_original_untouched(self):
        sm = generate_team(5, seed=1).score_matrix
        snapshot = sm.matrix.copy()
        uniform_inflation(sm)
        np.testing.assert_array_equal(
            np.nan_to_num(sm.matrix), np.nan_to_num(snapshot)
        )


class TestZeroSelf:
    def test_full_and_partial_distinct(self):
        sm = generate_team(5, seed=7).score_matrix
        full = zero_self(sm, full=True).matrix
        part = zero_self(sm, full=False).matrix
        assert not np.allclose(full, part, equal_nan=True)

    def test_full_is_uniform_uplift_preserving_rank(self):
        sm = generate_team(5, seed=7).score_matrix
        before = _baseline_iwf(sm)
        after = _baseline_iwf(zero_self(sm, full=True))
        assert np.all(after > before)  # surplus injected → grade uplift
        np.testing.assert_array_equal(np.argsort(after), np.argsort(before))

    def test_normalising_model_is_immune_to_full(self):
        # PeerRank normalises columns ⇒ uniform scaling cancels out.
        sm = generate_team(6, seed=4).score_matrix
        base = peerrank_exclude(sm)
        atk = peerrank_exclude(zero_self(sm, full=True))
        assert attack_delta(base, atk) == pytest.approx(0.0, abs=1e-6)

    def test_requires_two_colluders(self):
        sm = generate_team(4, seed=0).score_matrix
        with pytest.raises(ValueError):
            zero_self(sm, colluders=[0], full=False)


class TestTargetedDownvote:
    def test_victim_baseline_iwf_is_zero(self):
        sm = generate_team(5, seed=9).score_matrix
        atk = targeted_downvote(sm, victim=2)
        assert _baseline_iwf(atk)[2] == pytest.approx(0.0, abs=1e-9)

    def test_victim_column_unchanged(self):
        sm = generate_team(5, seed=9).score_matrix
        atk = targeted_downvote(sm, victim=2)
        np.testing.assert_allclose(
            atk.matrix[:, 2], sm.matrix[:, 2], equal_nan=True
        )

    def test_budget_conserved(self):
        sm = generate_team(6, seed=3).score_matrix
        before = np.nansum(sm.matrix, axis=0)
        after = np.nansum(targeted_downvote(sm, victim=1).matrix, axis=0)
        np.testing.assert_allclose(after, before)


class TestSingleOutlier:
    def test_seed_reproducible(self):
        sm = generate_team(5, seed=1).score_matrix
        a = single_outlier(sm, rng=np.random.default_rng(3)).matrix
        b = single_outlier(sm, rng=np.random.default_rng(3)).matrix
        np.testing.assert_array_equal(np.nan_to_num(a), np.nan_to_num(b))

    def test_budget_conserved_permutation(self):
        sm = generate_team(6, seed=2).score_matrix
        before = np.nansum(sm.matrix, axis=0)
        after = np.nansum(
            single_outlier(sm, rng=np.random.default_rng(0)).matrix, axis=0
        )
        np.testing.assert_allclose(after, before)

    def test_original_untouched(self):
        sm = generate_team(5, seed=1).score_matrix
        snap = sm.matrix.copy()
        single_outlier(sm, rng=np.random.default_rng(0))
        np.testing.assert_array_equal(
            np.nan_to_num(sm.matrix), np.nan_to_num(snap)
        )


class TestAttackDelta:
    def test_self_delta_is_zero(self):
        r = baseline_average(generate_team(5, seed=0).score_matrix)
        assert attack_delta(r, r) == 0.0

    def test_length_mismatch_raises(self):
        r4 = baseline_average(generate_team(4, seed=0).score_matrix)
        r5 = baseline_average(generate_team(5, seed=0).score_matrix)
        with pytest.raises(ValueError):
            attack_delta(r4, r5)


class TestMonteCarlo:
    def test_perm_count_and_reproducible(self):
        sm = generate_team(6, seed=1).score_matrix
        a = monte_carlo_single_outlier(sm, peerrank_exclude,
                                       n_perms=50, seed=5)
        b = monte_carlo_single_outlier(sm, peerrank_exclude,
                                       n_perms=50, seed=5)
        assert a.n_perms == 50
        np.testing.assert_array_equal(a.deltas, b.deltas)

    def test_stats_ordering(self):
        sm = generate_team(5, seed=2).score_matrix
        mc = monte_carlo_single_outlier(sm, baseline_average,
                                        n_perms=40, seed=0)
        assert mc.min <= mc.mean <= mc.max
        assert mc.std >= 0.0

    def test_iterative_convergence_tracked(self):
        sm = generate_team(6, seed=3).score_matrix
        mc = monte_carlo_single_outlier(sm, peerrank_exclude,
                                        n_perms=20, seed=0)
        assert mc.mean_iterations is not None
        base = monte_carlo_single_outlier(sm, baseline_average,
                                          n_perms=20, seed=0)
        assert base.mean_iterations is None  # non-iterative model


class TestRunner:
    def test_synthetic_run_all_attacks_present(self):
        cohort = generate_cohort(teams_per_size=3, base_seed=0)
        batch = run_attacks(synthetic=cohort, n_perms=10, seed=0,
                            progress=False)
        assert len(batch.records) > 0
        assert all(r.succeeded for r in batch.records)
        attacks = {k[0] for k in batch.aggregate()}
        assert {
            "uniform-inflation", "zero-self-full", "zero-self-partial",
            "targeted-downvote", "single-outlier",
        } <= attacks

    def test_source_filter(self):
        cohort = generate_cohort(teams_per_size=2, base_seed=1)
        batch = run_attacks(synthetic=cohort, n_perms=5, seed=0,
                            progress=False)
        assert batch.aggregate(source="real") == {}
        assert batch.aggregate(source="synthetic")

    def test_requires_an_input(self):
        with pytest.raises(ValueError):
            run_attacks(progress=False)
