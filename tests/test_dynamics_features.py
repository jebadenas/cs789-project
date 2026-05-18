"""Tests for src/dynamics/features.py — team feature vector extraction."""

from __future__ import annotations

import numpy as np
import pytest

from src.dynamics.features import (
    BEHAVIORAL_FEATURE_NAMES,
    FEATURE_NAMES,
    TeamFeatures,
    extract_features,
    _asymmetry,
    _gini,
    _reciprocity,
    _rater_variance,
)
from src.parsing.schemas import ScoreMatrix, StudentInfo


def _make_sm(matrix: np.ndarray, **kwargs) -> ScoreMatrix:
    """Build a ScoreMatrix from a raw numpy array (matrix[i][j] = giver j → recipient i)."""
    n = matrix.shape[0]
    defaults = dict(
        matrix=matrix,
        team_name="Test Team",
        question_label="Q1",
        year="2024",
        semester="S1",
        session_number=1,
        students=[
            StudentInfo(name=f"S{i}", email=f"s{i}@test.ac.nz", index=i)
            for i in range(n)
        ],
        excluded_students=[],
    )
    defaults.update(kwargs)
    return ScoreMatrix(**defaults)


# ---------------------------------------------------------------------------
# FEATURE_NAMES structure
# ---------------------------------------------------------------------------


class TestFeatureNames:

    def test_length_is_25(self):
        assert len(FEATURE_NAMES) == 25

    def test_behavioral_names_first(self):
        assert FEATURE_NAMES[:9] == BEHAVIORAL_FEATURE_NAMES

    def test_triad_names_follow(self):
        triad_names = FEATURE_NAMES[9:]
        assert all(n.startswith("triad_") for n in triad_names)
        assert len(triad_names) == 16


# ---------------------------------------------------------------------------
# _reciprocity
# ---------------------------------------------------------------------------


class TestReciprocity:
    """Pearson correlation of A[i,j] vs A[j,i] over valid symmetric pairs."""

    def test_perfect_symmetry_returns_one(self):
        """A = Aᵀ → all pairs (i,j) are perfectly correlated → reciprocity = 1."""
        A = np.array([
            [np.nan, 10.0, 15.0],
            [10.0, np.nan,  8.0],
            [15.0,  8.0, np.nan],
        ])
        assert _reciprocity(A) == pytest.approx(1.0, abs=1e-9)

    def test_perfectly_anti_symmetric_returns_minus_one(self):
        """Concentrated vs zero: one student always high, counterpart always low."""
        A = np.array([
            [np.nan, 20.0,  5.0],
            [ 5.0, np.nan, 20.0],
            [20.0,  5.0, np.nan],
        ])
        # Not perfectly -1 in general; verify it is negative
        assert _reciprocity(A) < 0.0

    def test_uniform_scores_returns_zero(self):
        """All scores equal → zero variance → corrcoef undefined → returns 0.0."""
        A = np.array([
            [np.nan, 12.0, 12.0],
            [12.0, np.nan, 12.0],
            [12.0, 12.0, np.nan],
        ])
        assert _reciprocity(A) == pytest.approx(0.0)

    def test_fewer_than_two_valid_pairs_returns_zero(self):
        """Single valid pair → can't compute correlation → returns 0.0."""
        A = np.full((3, 3), np.nan)
        A[0, 1] = 10.0
        A[1, 0] = 10.0
        # Only one (symmetric) pair → len(fwd) == 1
        assert _reciprocity(A) == pytest.approx(0.0)

    def test_nans_excluded_from_calculation(self):
        """Non-submitter rows (all NaN) don't affect reciprocity of other pairs."""
        A = np.array([
            [np.nan, 10.0, np.nan],
            [10.0, np.nan, np.nan],
            [np.nan, np.nan, np.nan],  # non-submitter
        ])
        # Only one pair (0,1) with values (10, 10) → single pair → 0.0
        assert _reciprocity(A) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _gini
# ---------------------------------------------------------------------------


class TestGini:

    def test_equal_values_returns_zero(self):
        """All equal → Gini = 0."""
        assert _gini(np.array([10.0, 10.0, 10.0, 10.0])) == pytest.approx(0.0)

    def test_all_to_one_returns_high_gini(self):
        """One value dominates → Gini close to 1."""
        v = np.array([0.0, 0.0, 0.0, 60.0])
        assert _gini(v) > 0.7

    def test_hand_computed_4_values(self):
        """4 values [2, 4, 6, 8]: Gini = 0.25.

        Sorted: [2, 4, 6, 8], n=4, sum=20
        Gini = (2*(1*2 + 2*4 + 3*6 + 4*8) - 5*20) / (4*20)
             = (2*(2+8+18+32) - 100) / 80
             = (2*60 - 100) / 80
             = (120 - 100) / 80
             = 0.25
        """
        assert _gini(np.array([2.0, 4.0, 6.0, 8.0])) == pytest.approx(0.25)

    def test_all_zeros_returns_zero(self):
        assert _gini(np.array([0.0, 0.0, 0.0])) == pytest.approx(0.0)

    def test_nan_values_ignored(self):
        """NaN values are excluded before Gini calculation."""
        v = np.array([10.0, 10.0, np.nan])
        assert _gini(v) == pytest.approx(0.0)

    def test_result_in_0_1(self):
        for vals in [[1, 2, 3, 4, 5], [10, 10, 10], [0, 0, 100]]:
            g = _gini(np.array(vals, dtype=float))
            assert 0.0 <= g <= 1.0, f"Gini={g} out of [0,1] for {vals}"


# ---------------------------------------------------------------------------
# _rater_variance
# ---------------------------------------------------------------------------


class TestRaterVariance:

    def test_uniform_rater_returns_zero_std(self):
        """Rater who gives equal scores to all → std = 0."""
        A = np.array([[np.nan, 10.0, 10.0, 10.0]])
        mean_std, std_std = _rater_variance(A)
        assert mean_std == pytest.approx(0.0)

    def test_differentiating_rater(self):
        """Rater who gives [0, 20]: std = 10."""
        A = np.array([[np.nan, 0.0, 20.0]])
        mean_std, std_std = _rater_variance(A)
        assert mean_std == pytest.approx(10.0)

    def test_single_valid_score_excluded(self):
        """Rater with only 1 valid peer score → can't compute std → excluded."""
        A = np.array([
            [np.nan, 10.0, np.nan],
            [10.0, np.nan, 12.0],
        ])
        # Row 0 has 1 valid → excluded. Row 1 has 2 valid → std=1.
        mean_std, std_std = _rater_variance(A)
        assert mean_std == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _asymmetry
# ---------------------------------------------------------------------------


class TestAsymmetry:

    def test_symmetric_matrix_returns_zero(self):
        """A = Aᵀ → asymmetry = 0."""
        A = np.array([
            [np.nan, 10.0, 8.0],
            [10.0, np.nan, 6.0],
            [8.0, 6.0, np.nan],
        ])
        assert _asymmetry(A) == pytest.approx(0.0, abs=1e-9)

    def test_anti_symmetric_returns_high_value(self):
        """One-directional scores → high asymmetry."""
        A = np.array([
            [np.nan, 20.0, 20.0],
            [0.0, np.nan, 20.0],
            [0.0, 0.0, np.nan],
        ])
        assert _asymmetry(A) > 0.3

    def test_all_nan_returns_zero(self):
        A = np.full((3, 3), np.nan)
        assert _asymmetry(A) == pytest.approx(0.0)

    def test_output_in_0_1(self):
        """Asymmetry is normalized and should be in [0, 1]."""
        rng = np.random.default_rng(0)
        for _ in range(20):
            A = rng.uniform(0, 20, (5, 5)).astype(float)
            np.fill_diagonal(A, np.nan)
            v = _asymmetry(A)
            assert 0.0 <= v <= 1.0, f"asymmetry={v} not in [0,1]"


# ---------------------------------------------------------------------------
# extract_features — integration
# ---------------------------------------------------------------------------


class TestExtractFeatures:

    def test_output_shape_25(self):
        """Feature vector has exactly 25 dimensions."""
        matrix = np.full((5, 5), 12.0, dtype=float)
        tf = extract_features(_make_sm(matrix))
        assert tf.values.shape == (25,)

    def test_no_nan_in_output(self):
        """Feature vector must be fully finite (no NaN)."""
        matrix = np.full((6, 6), 10.0, dtype=float)
        tf = extract_features(_make_sm(matrix))
        assert not np.isnan(tf.values).any()

    def test_uniform_team_zero_gini_zero_asymmetry(self):
        """Uniform scores → Gini(in-degree) = 0, asymmetry = 0.

        matrix[i][j] = 12 for all i,j (including diagonal).
        After diagonal removal: A[i][j] = 12 for all i≠j.
        In-degrees all equal → Gini = 0. A = Aᵀ → asymmetry = 0.
        """
        n = 5
        matrix = np.full((n, n), 12.0)
        tf = extract_features(_make_sm(matrix))

        gini_idx = FEATURE_NAMES.index("gini_in_degree")
        asymmetry_idx = FEATURE_NAMES.index("asymmetry")

        assert tf.values[gini_idx] == pytest.approx(0.0)
        assert tf.values[asymmetry_idx] == pytest.approx(0.0, abs=1e-9)

    def test_non_submitter_fraction_correct(self):
        """One non-submitter in 4-person team → non_submitter_frac = 0.25.

        Non-submitter = entire column is NaN.
        matrix[i][j] = giver j → recipient i.
        Column 3 all NaN → student 3 is non-submitter.
        """
        matrix = np.array([
            [10.0,  8.0, 12.0, np.nan],
            [ 8.0, 10.0,  8.0, np.nan],
            [12.0,  8.0, 10.0, np.nan],
            [ 6.0,  6.0,  6.0, np.nan],
        ])
        tf = extract_features(_make_sm(matrix))

        frac_idx = FEATURE_NAMES.index("non_submitter_frac")
        assert tf.values[frac_idx] == pytest.approx(0.25)
        assert tf.non_submitter_count == 1

    def test_mean_self_share_from_diagonal(self):
        """mean_self_share = mean(diagonal / 60).

        Diagonal of matrix = self-scores.
        Students: [12, 18, 6] self-scores → shares: [0.2, 0.3, 0.1] → mean = 0.2.
        """
        n = 3
        matrix = np.full((n, n), 10.0)
        matrix[0, 0] = 12.0
        matrix[1, 1] = 18.0
        matrix[2, 2] = 6.0

        tf = extract_features(_make_sm(matrix))

        share_idx = FEATURE_NAMES.index("mean_self_share")
        assert tf.values[share_idx] == pytest.approx((12 + 18 + 6) / (3 * 60))

    def test_free_rider_high_gini(self):
        """One student receives zero from all peers → high Gini.

        matrix[i][j] = giver j → recipient i.
        Row 3 (student D as recipient) gets very low scores.
        """
        matrix = np.array([
            [10.0, 10.0, 10.0, 10.0],
            [10.0, 10.0, 10.0, 10.0],
            [10.0, 10.0, 10.0, 10.0],
            [ 0.0,  0.0,  0.0,  0.0],  # D gets 0 from everyone, self-score also 0
        ], dtype=float)
        tf = extract_features(_make_sm(matrix))

        gini_idx = FEATURE_NAMES.index("gini_in_degree")
        # in-degrees [10, 10, 10, 0] → Gini = 0.25 (hand-computed)
        assert tf.values[gini_idx] == pytest.approx(0.25)

    def test_triad_proportions_sum_to_one(self):
        """Sum of 16 triad-census features ≈ 1."""
        matrix = np.array([
            [10.0,  5.0, 15.0, 20.0],
            [15.0, 10.0,  5.0, 10.0],
            [10.0, 15.0, 10.0,  5.0],
            [ 5.0, 10.0, 15.0, 10.0],
        ])
        tf = extract_features(_make_sm(matrix))

        triad_vals = tf.values[9:]  # 16 triad dims start at index 9
        assert triad_vals.sum() == pytest.approx(1.0, abs=1e-9)

    def test_metadata_fields(self):
        """csv_path, team_name, question_label, n_students propagated correctly."""
        matrix = np.full((5, 5), 12.0)
        sm = _make_sm(matrix, team_name="Team Alpha", question_label="teamwork")
        tf = extract_features(sm, csv_path="/some/file.csv", question_label="teamwork")

        assert tf.csv_path == "/some/file.csv"
        assert tf.team_name == "Team Alpha"
        assert tf.question_label == "teamwork"
        assert tf.n_students == 5

    def test_assortativity_zero_for_fixed_out_degree(self):
        """In peer-rating graphs all submitters have equal out-degree → assortativity = 0.

        This is a known property of the dataset: since every student rates all peers,
        out-degree is constant (n-1) for submitters, making degree assortativity
        undefined / zero.
        """
        n = 5
        matrix = np.tile(np.array([12, 8, 10, 6, 4], dtype=float), (n, 1)).T
        np.fill_diagonal(matrix, 10.0)  # self-scores on diagonal

        tf = extract_features(_make_sm(matrix))

        assort_idx = FEATURE_NAMES.index("assortativity")
        assert tf.values[assort_idx] == pytest.approx(0.0)

    def test_two_student_team(self):
        """Minimum team size — no triads possible, no NaN in output."""
        matrix = np.array([[10.0, 8.0], [12.0, 10.0]], dtype=float)
        sm = _make_sm(matrix)
        tf = extract_features(sm)

        assert tf.values.shape == (25,)
        assert not np.isnan(tf.values).any()
        # No triads with n=2 → all triad proportions zero
        assert tf.values[9:].sum() == pytest.approx(0.0)

    def test_all_non_submitters_except_one(self):
        """Only one rater → extreme non_submitter_frac, no NaN output."""
        matrix = np.array([
            [10.0, np.nan, np.nan, np.nan],
            [ 8.0, np.nan, np.nan, np.nan],
            [12.0, np.nan, np.nan, np.nan],
            [ 6.0, np.nan, np.nan, np.nan],
        ])
        tf = extract_features(_make_sm(matrix))

        frac_idx = FEATURE_NAMES.index("non_submitter_frac")
        assert tf.values[frac_idx] == pytest.approx(0.75)
        assert not np.isnan(tf.values).any()
