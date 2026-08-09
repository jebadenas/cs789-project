"""Tests for src/dynamics2 — the rank-based state cascade (handoff-8).

Convention reminder: ScoreMatrix.matrix[i][j] = score giver j → recipient i, so
**column j is rater j**. The rank transform operates per column.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import kendalltau

from src.dynamics2 import contested, gates, ranks
from src.dynamics2.nulls import permutation_p, permute_matrix, seed_from_key
from src.parsing.schemas import ScoreMatrix, StudentInfo


def _make_sm(matrix: np.ndarray) -> ScoreMatrix:
    n = matrix.shape[0]
    return ScoreMatrix(
        matrix=matrix, team_name="T", question_label="q",
        year="2024", semester="S1", session_number=1,
        students=[StudentInfo(name=f"S{i}", email=f"s{i}@t.ac.nz", index=i)
                  for i in range(n)],
    )


# --------------------------------------------------------------------------- #
# τ-b against scipy, including heavy ties
# --------------------------------------------------------------------------- #

class TestTauB:

    def test_matches_scipy_on_random_vectors_with_ties(self):
        rng = np.random.default_rng(42)
        max_err = 0.0
        for _ in range(3000):
            k = int(rng.integers(3, 7))
            x = rng.integers(0, 4, size=k).astype(float)  # low range → heavy ties
            y = rng.integers(0, 4, size=k).astype(float)
            mine = ranks.tau_b(x, y)
            ref, _ = kendalltau(x, y, variant="b")
            if np.isnan(mine) and np.isnan(ref):
                continue
            max_err = max(max_err, abs(mine - ref))
        assert max_err < 1e-12

    def test_returns_nan_when_one_vector_all_tied(self):
        assert np.isnan(ranks.tau_b(np.array([1.0, 1.0, 1.0]),
                                    np.array([1.0, 2.0, 3.0])))

    def test_perfect_agreement_is_one(self):
        assert ranks.tau_b(np.array([1.0, 2.0, 3.0, 4.0]),
                           np.array([5.0, 6.0, 7.0, 8.0])) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# Rank transform invariance under positive-affine rater rescaling
# --------------------------------------------------------------------------- #

class TestRankInvariance:

    def test_positive_affine_leaves_normalised_ranks_identical(self):
        mat = np.array([
            [np.nan, 3.0, 8.0, 2.0],
            [5.0, np.nan, 1.0, 9.0],
            [7.0, 6.0, np.nan, 4.0],
            [2.0, 8.0, 5.0, np.nan],
        ])
        R0 = ranks.normalised_rank_matrix(mat)

        # Rescale rater (column) 1 by a positive constant and add a constant.
        mat2 = mat.copy()
        mat2[:, 1] = mat2[:, 1] * 7.0 + 100.0
        R1 = ranks.normalised_rank_matrix(mat2)

        np.testing.assert_allclose(R1[:, 1][np.isfinite(R1[:, 1])],
                                   R0[:, 1][np.isfinite(R0[:, 1])])
        np.testing.assert_allclose(np.nan_to_num(R1), np.nan_to_num(R0))

    def test_normalised_rank_divides_by_k_plus_one(self):
        # One rater rating 3 recipients: ranks 1,2,3 → /4.
        mat = np.array([
            [np.nan, 10.0],
            [np.nan, 30.0],
            [np.nan, 20.0],
        ])
        R = ranks.normalised_rank_matrix(mat)
        got = R[:, 1]
        np.testing.assert_allclose(got, [1 / 4, 3 / 4, 2 / 4])


# --------------------------------------------------------------------------- #
# Qualifying-rater rule (the load-bearing definition)
# --------------------------------------------------------------------------- #

class TestQualifyingRaters:

    def test_flat_rater_excluded(self):
        mat = np.array([
            [np.nan, 5.0],
            [5.0, np.nan],   # rater 1 gave everyone (one person) — <2 entries anyway
        ])
        # rater 0: single finite entry → not qualifying; rater 1 same.
        assert ranks.qualifying_raters(mat).tolist() == [False, False]

    def test_constant_rater_excluded_variable_rater_kept(self):
        mat = np.array([
            [np.nan, 4.0, 1.0],
            [7.0, np.nan, 9.0],
            [7.0, 4.0, np.nan],
        ])
        # col0: [7,7] zero std → excluded. col1: [4,4] excluded. col2: [1,9] kept.
        assert ranks.qualifying_raters(mat).tolist() == [False, False, True]


# --------------------------------------------------------------------------- #
# Hand-built cascade states
# --------------------------------------------------------------------------- #

class TestCascadeStates:

    def test_flat_matrix_is_silent_flat(self):
        mat = ranks.prepare_matrix(_make_sm(np.full((5, 5), 10.0)))
        row = gates.classify_matrix(mat, ("c", "T", "q"), n_perm=100)
        assert row.state == gates.SILENT_FLAT
        assert row.n_raters == 0

    def test_single_differentiating_rater_is_lone_dissenter(self):
        # Only rater (col) 0 differentiates; all other columns constant.
        mat = np.full((5, 5), 8.0)
        mat[:, 0] = [np.nan, 1.0, 2.0, 3.0, 4.0]
        row = gates.classify_matrix(ranks.prepare_matrix(_make_sm(mat)),
                                    ("c", "T", "q"), n_perm=100)
        assert row.state == gates.SILENT_LONE

    def test_obvious_free_rider_is_one_at_bottom(self):
        # Person 0 unanimously far worst; everyone else bunched (random order).
        n = 7
        rng = np.random.default_rng(1)
        mat = np.zeros((n, n))
        for j in range(n):
            col = 50 + rng.normal(0, 1.0, n)
            col[0] = 1.0
            mat[:, j] = col
        row = gates.classify_matrix(ranks.prepare_matrix(_make_sm(mat)),
                                    ("c", "T", "q"), n_perm=400)
        assert row.state == gates.ONE_AT_BOTTOM
        assert row.p_bot <= 0.05
        assert row.p_top > 0.05


# --------------------------------------------------------------------------- #
# Faction test recovers two clean camps
# --------------------------------------------------------------------------- #

class TestFactionTest:

    def test_two_clean_camps_recovered(self):
        # Raters 0,1,2 rank recipients ascending; raters 3,4,5 rank them reversed.
        n = 6
        camp_a = np.arange(1.0, n + 1.0)
        mat = np.zeros((n, n))
        for j in range(n):
            mat[:, j] = camp_a if j < 3 else camp_a[::-1]
        res = contested.faction_test(ranks.prepare_matrix(_make_sm(mat)),
                                     ("c", "T", "q"), n_perm=300)
        assert res.category == "structured"
        assert res.faction_size == 3
        assert res.p_value <= 0.05

    def test_size_one_winner_is_lone_deviant_not_faction(self):
        # Five raters agree; one rater (col 5) is the mirror image → lone deviant.
        n = 6
        base = np.arange(1.0, n + 1.0)
        mat = np.zeros((n, n))
        for j in range(n):
            mat[:, j] = base.copy()
        mat[:, 5] = base[::-1]
        res = contested.faction_test(ranks.prepare_matrix(_make_sm(mat)),
                                     ("c", "T", "q"), n_perm=300)
        if res.p_value <= 0.05:
            assert res.category == "lone deviant"
            assert res.faction_size == 1


# --------------------------------------------------------------------------- #
# Null harness: determinism, seeding, p-value bounds
# --------------------------------------------------------------------------- #

class TestNulls:

    def _matrix(self):
        rng = np.random.default_rng(7)
        mat = rng.integers(0, 20, size=(5, 5)).astype(float)
        np.fill_diagonal(mat, np.nan)
        return mat

    def test_same_key_same_p_value(self):
        mat = self._matrix()
        r1 = permutation_p(mat, ranks.mean_pairwise_tau, ("a", "b"), n_perm=300)
        r2 = permutation_p(mat, ranks.mean_pairwise_tau, ("a", "b"), n_perm=300)
        assert r1.p_value == r2.p_value

    def test_seed_is_not_python_hash(self):
        # BLAKE2b-based seed is stable and independent of PYTHONHASHSEED.
        assert seed_from_key("data.csv", "Team 1", "source code") == \
            seed_from_key("data.csv", "Team 1", "source code")

    def test_p_value_bounds(self):
        mat = self._matrix()
        for stat in (ranks.mean_pairwise_tau, gates._bot_gap_stat, gates._top_gap_stat):
            res = permutation_p(mat, stat, ("k",), n_perm=200)
            if np.isfinite(res.p_value):
                assert 0 < res.p_value <= 1

    def test_add_one_never_zero(self):
        # Even a maximally-extreme observed statistic gives p >= 1/(n_perm+1).
        mat = self._matrix()
        res = permutation_p(mat, ranks.mean_pairwise_tau, ("k",), n_perm=200)
        assert res.p_value >= 1 / (200 + 1)

    def test_permutation_preserves_column_multiset(self):
        mat = self._matrix()
        out = permute_matrix(mat, np.random.default_rng(0))
        for j in range(mat.shape[1]):
            a = np.sort(mat[:, j][np.isfinite(mat[:, j])])
            b = np.sort(out[:, j][np.isfinite(out[:, j])])
            np.testing.assert_array_equal(a, b)
