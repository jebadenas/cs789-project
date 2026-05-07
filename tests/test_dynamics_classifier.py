"""Tests for src/dynamics/classifier.py — synthesised archetypes + Mahalanobis classifier."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.preprocessing import StandardScaler

from src.dynamics.classifier import (
    ARCHETYPE_LABELS,
    ClassificationResult,
    _mahalanobis,
    build_synthesised_archetypes,
    classify_teams,
    delta_by_label,
    fit_precision,
)


# ---------------------------------------------------------------------------
# build_synthesised_archetypes
# ---------------------------------------------------------------------------


class TestBuildSynthesisedArchetypes:

    def test_returns_five_labels(self):
        labels, _ = build_synthesised_archetypes()
        assert labels == ARCHETYPE_LABELS
        assert len(labels) == 5

    def test_archetype_matrix_shape(self):
        _, archetypes = build_synthesised_archetypes()
        assert archetypes.shape == (5, 25)

    def test_no_nan_in_archetypes(self):
        _, archetypes = build_synthesised_archetypes()
        assert not np.isnan(archetypes).any()

    def test_archetypes_are_distinct(self):
        """No two archetype vectors are identical — each prototype has a unique signature."""
        _, archetypes = build_synthesised_archetypes()
        for i in range(5):
            for j in range(i + 1, 5):
                assert not np.allclose(archetypes[i], archetypes[j]), (
                    f"Archetypes {ARCHETYPE_LABELS[i]} and {ARCHETYPE_LABELS[j]} are identical"
                )

    def test_free_rider_has_high_gini(self):
        """Free-rider prototype should have above-average Gini coefficient."""
        from src.dynamics.features import FEATURE_NAMES
        _, archetypes = build_synthesised_archetypes()
        gini_idx = FEATURE_NAMES.index("gini_in_degree")
        gini_vals = archetypes[:, gini_idx]
        fr_idx = ARCHETYPE_LABELS.index("Free-rider")
        assert gini_vals[fr_idx] == max(gini_vals) or gini_vals[fr_idx] > np.mean(gini_vals), (
            f"Free-rider Gini ({gini_vals[fr_idx]:.3f}) should be above average ({np.mean(gini_vals):.3f})"
        )

    def test_dominant_has_high_gini(self):
        """Dominant prototype should have the highest (or near-highest) Gini."""
        from src.dynamics.features import FEATURE_NAMES
        _, archetypes = build_synthesised_archetypes()
        gini_idx = FEATURE_NAMES.index("gini_in_degree")
        dom_idx = ARCHETYPE_LABELS.index("Dominant")
        assert archetypes[dom_idx, gini_idx] > np.mean(archetypes[:, gini_idx])

    def test_cohesive_has_low_asymmetry(self):
        """Cohesive prototype should have the lowest asymmetry."""
        from src.dynamics.features import FEATURE_NAMES
        _, archetypes = build_synthesised_archetypes()
        asym_idx = FEATURE_NAMES.index("asymmetry")
        coh_idx = ARCHETYPE_LABELS.index("Cohesive")
        coh_asym = archetypes[coh_idx, asym_idx]
        assert coh_asym < np.mean(archetypes[:, asym_idx]), (
            f"Cohesive asymmetry ({coh_asym:.3f}) should be below average"
        )

    def test_conflict_has_high_asymmetry(self):
        """Conflict prototype should have the highest asymmetry."""
        from src.dynamics.features import FEATURE_NAMES
        _, archetypes = build_synthesised_archetypes()
        asym_idx = FEATURE_NAMES.index("asymmetry")
        con_idx = ARCHETYPE_LABELS.index("Conflict")
        assert archetypes[con_idx, asym_idx] == pytest.approx(max(archetypes[:, asym_idx]), abs=0.05)


# ---------------------------------------------------------------------------
# fit_precision
# ---------------------------------------------------------------------------


class TestFitPrecision:

    def _make_X(self, n: int = 50, p: int = 25, seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        X = rng.standard_normal((n, p))
        return (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)

    def test_shape(self):
        X = self._make_X()
        P = fit_precision(X)
        assert P.shape == (25, 25)

    def test_symmetric(self):
        X = self._make_X()
        P = fit_precision(X)
        np.testing.assert_allclose(P, P.T, atol=1e-9)

    def test_positive_definite(self):
        """All eigenvalues of precision must be positive (Ledoit-Wolf guarantees this)."""
        X = self._make_X()
        P = fit_precision(X)
        eigvals = np.linalg.eigvalsh(P)
        assert (eigvals > 0).all(), f"Precision has non-positive eigenvalue: {eigvals.min():.6g}"

    def test_cholesky_works(self):
        """Precision matrix must be Cholesky-decomposable (required by classifier)."""
        X = self._make_X()
        P = fit_precision(X)
        L = np.linalg.cholesky(P)
        assert L.shape == (25, 25)


# ---------------------------------------------------------------------------
# _mahalanobis (internal)
# ---------------------------------------------------------------------------


class TestMahalanobis:

    def test_zero_distance_to_self(self):
        """Distance from a point to itself is 0."""
        rng = np.random.default_rng(0)
        u = rng.standard_normal(10)
        P = np.eye(10)
        L = np.linalg.cholesky(P)
        assert _mahalanobis(u, u, L) == pytest.approx(0.0)

    def test_identity_precision_equals_euclidean(self):
        """With identity precision, Mahalanobis = Euclidean distance."""
        rng = np.random.default_rng(1)
        u = rng.standard_normal(8)
        v = rng.standard_normal(8)
        P = np.eye(8)
        L = np.linalg.cholesky(P)
        mah = _mahalanobis(u, v, L)
        euc = float(np.linalg.norm(u - v))
        assert mah == pytest.approx(euc, rel=1e-6)

    def test_symmetric(self):
        """d(u, v) == d(v, u)."""
        rng = np.random.default_rng(2)
        u, v = rng.standard_normal(12), rng.standard_normal(12)
        P = np.eye(12)
        L = np.linalg.cholesky(P)
        assert _mahalanobis(u, v, L) == pytest.approx(_mahalanobis(v, u, L))

    def test_non_negative(self):
        """Distance is always ≥ 0."""
        rng = np.random.default_rng(3)
        u, v = rng.standard_normal(10), rng.standard_normal(10)
        P = np.eye(10)
        L = np.linalg.cholesky(P)
        assert _mahalanobis(u, v, L) >= 0.0


# ---------------------------------------------------------------------------
# classify_teams
# ---------------------------------------------------------------------------


class TestClassifyTeams:

    def _setup(self):
        """Build scaled archetypes and precision using real synthesised archetypes."""
        labels, arch_raw = build_synthesised_archetypes()
        scaler = StandardScaler()
        # Fit scaler on the archetypes themselves (minimal dataset)
        scaler.fit(arch_raw)
        arch_scaled = scaler.transform(arch_raw)
        precision = fit_precision(arch_scaled)
        return labels, arch_scaled, precision, scaler

    def test_returns_one_result_per_team(self):
        labels, arch_scaled, precision, _ = self._setup()
        n = 20
        X = np.random.default_rng(0).standard_normal((n, 25))
        results = classify_teams(X, arch_scaled, precision)
        assert len(results) == n

    def test_each_archetype_classifies_to_itself(self):
        """When a team is the archetype prototype, it should classify to that archetype.

        Fits the scaler/precision on a diverse pool (each prototype repeated 20×
        with small noise) to avoid degenerate covariance.
        """
        labels, arch_raw = build_synthesised_archetypes()
        scaler = StandardScaler()

        rng = np.random.default_rng(42)
        noise = rng.standard_normal((100, 25)) * 0.1  # 5 archetypes × 20
        pool = np.tile(arch_raw, (20, 1)) + noise      # (100, 25)
        scaler.fit(pool)

        arch_scaled = scaler.transform(arch_raw)
        pool_scaled = scaler.transform(pool)
        precision = fit_precision(pool_scaled)

        results = classify_teams(arch_scaled, arch_scaled, precision)
        for r, expected in zip(results, labels):
            assert r.label == expected, (
                f"Archetype {expected} classified as {r.label} — self-classification failed"
            )

    def test_distances_shape(self):
        labels, arch_scaled, precision, _ = self._setup()
        X = np.zeros((3, 25))
        results = classify_teams(X, arch_scaled, precision)
        for r in results:
            assert r.distances.shape == (5,)

    def test_weights_sum_to_one(self):
        labels, arch_scaled, precision, _ = self._setup()
        X = np.random.default_rng(5).standard_normal((10, 25))
        results = classify_teams(X, arch_scaled, precision)
        for r in results:
            np.testing.assert_allclose(r.weights.sum(), 1.0, atol=1e-9)

    def test_weights_non_negative(self):
        labels, arch_scaled, precision, _ = self._setup()
        X = np.random.default_rng(6).standard_normal((10, 25))
        results = classify_teams(X, arch_scaled, precision)
        for r in results:
            assert (r.weights >= 0).all()

    def test_label_matches_argmin_distance(self):
        """Assigned label always corresponds to the closest archetype."""
        labels, arch_scaled, precision, _ = self._setup()
        X = np.random.default_rng(7).standard_normal((15, 25))
        results = classify_teams(X, arch_scaled, precision)
        for r in results:
            expected_idx = int(np.argmin(r.distances))
            assert r.label == ARCHETYPE_LABELS[expected_idx]


# ---------------------------------------------------------------------------
# delta_by_label
# ---------------------------------------------------------------------------


class TestDeltaByLabel:

    def test_all_archetype_labels_present(self):
        labels = ["Cohesive"] * 5 + ["Conflict"] * 3
        delta_vals = np.ones(8)
        stats = delta_by_label(labels, delta_vals)
        assert set(stats.keys()) == set(ARCHETYPE_LABELS)

    def test_count_correct(self):
        labels = ["Cohesive", "Cohesive", "Free-rider", "Dominant"]
        delta_vals = np.array([1.0, 2.0, 3.0, 4.0])
        stats = delta_by_label(labels, delta_vals)
        assert stats["Cohesive"]["count"] == 2
        assert stats["Free-rider"]["count"] == 1
        assert stats["Collusive"]["count"] == 0

    def test_mean_correct(self):
        labels = ["Cohesive", "Cohesive", "Cohesive"]
        delta_vals = np.array([1.0, 2.0, 3.0])
        stats = delta_by_label(labels, delta_vals)
        assert stats["Cohesive"]["mean"] == pytest.approx(2.0)

    def test_empty_label_returns_nan(self):
        labels = ["Cohesive"]
        delta_vals = np.array([1.0])
        stats = delta_by_label(labels, delta_vals)
        assert np.isnan(stats["Conflict"]["mean"])
        assert np.isnan(stats["Collusive"]["median"])

    def test_returns_all_stat_keys(self):
        labels = ["Cohesive"]
        delta_vals = np.array([1.5])
        stats = delta_by_label(labels, delta_vals)
        for s in stats.values():
            assert set(s.keys()) == {"count", "mean", "std", "median", "max"}
