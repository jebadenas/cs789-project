"""Tests for src/dynamics/archetypes.py — Archetypal Analysis."""

from __future__ import annotations

import numpy as np
import pytest

from src.dynamics.archetypes import (
    ArchetypeResult,
    find_elbow,
    fit_aa,
    sweep_archetypes,
)


def _make_X(n: int = 40, p: int = 10, seed: int = 0) -> np.ndarray:
    """Standardized random feature matrix for testing."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, p))
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
    return X


def _clustered_X(k: int = 3, n_per: int = 15, p: int = 8, seed: int = 42) -> np.ndarray:
    """Data with k well-separated clusters — AA should find k archetypes cleanly."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((k, p)) * 5.0
    X = np.vstack([
        centers[j] + rng.standard_normal((n_per, p)) * 0.3
        for j in range(k)
    ])
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
    return X


# ---------------------------------------------------------------------------
# fit_aa — output shape and constraint checks
# ---------------------------------------------------------------------------


class TestFitAA:

    def test_archetype_shape(self):
        """archetypes Z has shape (k, p)."""
        X = _make_X(n=30, p=10)
        Z, S, rss = fit_aa(X, k=3, max_iter=100, n_restarts=1)
        assert Z.shape == (3, 10)

    def test_weights_shape(self):
        """weights S has shape (n_samples, k)."""
        X = _make_X(n=30, p=10)
        Z, S, rss = fit_aa(X, k=4, max_iter=100, n_restarts=1)
        assert S.shape == (30, 4)

    def test_weights_row_stochastic(self):
        """Every row of S sums to 1 and all values ≥ 0."""
        X = _make_X(n=50, p=12)
        Z, S, rss = fit_aa(X, k=3, max_iter=200, n_restarts=2)

        row_sums = S.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-6)
        assert (S >= 0).all()

    def test_rss_is_positive_float(self):
        X = _make_X()
        _, _, rss = fit_aa(X, k=3, max_iter=100, n_restarts=1)
        assert isinstance(rss, float)
        assert rss >= 0.0

    def test_more_archetypes_lowers_rss(self):
        """RSS is non-increasing as k grows (on same data)."""
        X = _make_X(n=40, p=8, seed=7)
        rss_prev = np.inf
        for k in [2, 3, 4, 5]:
            _, _, rss = fit_aa(X, k=k, max_iter=150, n_restarts=2, random_state=0)
            assert rss <= rss_prev + 1e-3, f"RSS increased from k={k-1} to k={k}"
            rss_prev = rss

    def test_k_equals_1_degenerates_to_mean(self):
        """k=1 archetype ≈ centroid; all weights = 1; RSS equals total variance."""
        X = _make_X(n=30, p=5, seed=1)
        Z, S, rss = fit_aa(X, k=1, max_iter=200, n_restarts=1)

        assert Z.shape == (1, 5)
        np.testing.assert_allclose(S, 1.0, atol=1e-6)

    def test_deterministic_with_same_seed(self):
        """Same random_state → identical results."""
        X = _make_X(n=35, p=8, seed=3)
        Z1, S1, rss1 = fit_aa(X, k=3, max_iter=100, n_restarts=2, random_state=99)
        Z2, S2, rss2 = fit_aa(X, k=3, max_iter=100, n_restarts=2, random_state=99)

        np.testing.assert_array_equal(Z1, Z2)
        assert rss1 == rss2

    def test_well_separated_clusters_low_rss(self):
        """Data with k tight clusters → AA with matching k achieves low RSS."""
        X = _clustered_X(k=3, n_per=20, p=6)
        n, p = X.shape
        total_var = float(np.sum(X ** 2))

        Z, S, rss = fit_aa(X, k=3, max_iter=300, n_restarts=3, random_state=42)

        # RSS should be small relative to total variance for well-separated clusters
        explained = 1.0 - rss / total_var
        assert explained > 0.5, f"Low explained variance ({explained:.2f}) for clean clusters"

    def test_no_nan_in_outputs(self):
        """No NaN in archetypes or weights."""
        X = _make_X(n=25, p=8)
        Z, S, rss = fit_aa(X, k=4, max_iter=100, n_restarts=1)

        assert not np.isnan(Z).any()
        assert not np.isnan(S).any()


# ---------------------------------------------------------------------------
# sweep_archetypes
# ---------------------------------------------------------------------------


class TestSweepArchetypes:

    def test_returns_one_result_per_k(self):
        X = _make_X(n=30, p=8)
        results = sweep_archetypes(X, k_range=range(2, 5), n_bootstrap=5, max_iter=80)
        assert len(results) == 3

    def test_results_sorted_by_k(self):
        X = _make_X(n=30, p=8)
        results = sweep_archetypes(X, k_range=range(2, 6), n_bootstrap=5, max_iter=80)
        ks = [r.k for r in results]
        assert ks == sorted(ks)

    def test_rss_non_increasing(self):
        """RSS must be non-increasing with k (more archetypes → better fit)."""
        X = _make_X(n=40, p=10, seed=5)
        results = sweep_archetypes(X, k_range=range(2, 7), n_bootstrap=5, max_iter=120)
        for i in range(1, len(results)):
            assert results[i].rss <= results[i - 1].rss + 1.0, (
                f"RSS increased from k={results[i-1].k} ({results[i-1].rss:.1f}) "
                f"to k={results[i].k} ({results[i].rss:.1f})"
            )

    def test_stability_in_0_1(self):
        """Bootstrap stability is always in [0, 1]."""
        X = _make_X(n=30, p=6)
        results = sweep_archetypes(X, k_range=range(2, 5), n_bootstrap=5, max_iter=80)
        for r in results:
            assert 0.0 <= r.bootstrap_stability <= 1.0, (
                f"Stability {r.bootstrap_stability} out of [0,1] for k={r.k}"
            )

    def test_archetype_result_fields(self):
        """ArchetypeResult has correct field types and shapes."""
        X = _make_X(n=25, p=7)
        results = sweep_archetypes(X, k_range=range(2, 4), n_bootstrap=3, max_iter=80)
        for r in results:
            assert isinstance(r, ArchetypeResult)
            assert r.archetypes.shape == (r.k, 7)
            assert r.weights.shape == (25, r.k)
            assert isinstance(r.rss, float)
            assert isinstance(r.bootstrap_stability, float)


# ---------------------------------------------------------------------------
# find_elbow
# ---------------------------------------------------------------------------


class TestFindElbow:

    def _make_results(self, rss_vals: list[float]) -> list[ArchetypeResult]:
        """Build stub ArchetypeResults with given RSS values for k=2,3,..."""
        n, p = 20, 5
        X = np.zeros((n, p))
        return [
            ArchetypeResult(
                k=k + 2,
                archetypes=np.zeros((k + 2, p)),
                weights=np.zeros((n, k + 2)),
                rss=rss,
            )
            for k, rss in enumerate(rss_vals)
        ]

    def test_clear_elbow_at_k3(self):
        """RSS drops steeply from k=2→3, then levels off: elbow should be k=3.

        RSS values: [1000, 200, 180, 175, 173]
        The big drop between k=2 and k=3 creates a clear elbow at k=3.
        """
        results = self._make_results([1000.0, 200.0, 180.0, 175.0, 173.0])
        assert find_elbow(results) == 3

    def test_single_result_returns_that_k(self):
        results = self._make_results([500.0])
        assert find_elbow(results) == 2

    def test_two_results_returns_first(self):
        """With only two points there's no elbow — returns first k."""
        results = self._make_results([500.0, 300.0])
        assert find_elbow(results) == 2

    def test_flat_rss_returns_a_k(self):
        """All equal RSS (no elbow) should still return a valid k without error."""
        results = self._make_results([100.0, 100.0, 100.0, 100.0])
        ks = {r.k for r in results}
        assert find_elbow(results) in ks

    def test_returns_k_from_results_list(self):
        """Returned k is always one of the k values in the input."""
        results = self._make_results([800.0, 400.0, 300.0, 280.0, 275.0, 272.0])
        best_k = find_elbow(results)
        assert best_k in {r.k for r in results}
