"""Tests for the WebPA IWF model."""

import numpy as np
import pytest

from src.models.webpa import webpa
from src.parsing.schemas import ScoreMatrix, StudentInfo


def _make_score_matrix(matrix: np.ndarray, **kwargs) -> ScoreMatrix:
    """Build a ScoreMatrix from a numpy array with sensible defaults."""
    n = matrix.shape[0]
    defaults = dict(
        matrix=matrix,
        team_name="Test Team",
        question_label="test",
        year="2024",
        semester="S1",
        session_number=1,
        students=[
            StudentInfo(name=f"Student {chr(65 + i)}", email=f"s{chr(97 + i)}@test.ac.nz", index=i)
            for i in range(n)
        ],
        excluded_students=[],
    )
    defaults.update(kwargs)
    return ScoreMatrix(**defaults)


class TestWebPA:
    """WebPA computes PA factors scaled to a team mean of 10.0."""

    def test_grade_neutrality_invariant(self):
        """The mean of all IWFs must always equal 10.0."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        assert result.iwf_vector.mean() == pytest.approx(10.0)

    def test_asymmetric_scores_produce_correct_ranking(self):
        """
        Students who receive more (normalised) points get higher IWFs.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,      6,      8  ]
          B(i=1) [  12,     10,     14  ]
          C(i=2) [   8,     14,     12  ]

        Rater totals (col sums) = [30, 30, 34] — unequal, so the canonical
        per-rater normalisation is NOT a no-op here (unlike the fixed-budget real
        data). Expected = received fractions ÷ team-mean × 10.
        """
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        assert result.model_name == "WebPA"
        assert len(result.students) == 3
        received = (matrix / matrix.sum(axis=0)).sum(axis=1)  # canonical WebPA
        expected = received / received.mean() * 10
        np.testing.assert_array_almost_equal(result.iwf_vector, expected)
        assert result.iwf_vector.mean() == pytest.approx(10.0)

    def test_uniform_scores_produce_equal_iwf(self):
        """When everyone gives equal scores, all IWFs are 10.0."""
        matrix = np.full((5, 5), 10.0)

        result = webpa(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(result.iwf_vector, np.full(5, 10.0))

    def test_self_scores_are_included(self):
        """
        WebPA includes self-scores in each rater's total (original paper), so the
        diagonal enters both the per-rater normalisation and the received sum.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  20,      6,      8  ]
          B(i=1) [   5,     10,      5  ]
          C(i=2) [   5,      8,     17  ]

        Rater totals (incl self) = [30, 24, 30]. Result must match canonical WebPA
        with the diagonal included, and must DIFFER from the self-excluded variant.
        """
        matrix = np.array([
            [20, 6, 8],
            [5, 10, 5],
            [5, 8, 17],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        received = (matrix / matrix.sum(axis=0)).sum(axis=1)  # self included
        expected = received / received.mean() * 10
        np.testing.assert_array_almost_equal(result.iwf_vector, expected)

        # Self-excluded normalisation would give a different vector.
        m_excl = matrix.copy()
        np.fill_diagonal(m_excl, 0.0)
        received_excl = (m_excl / m_excl.sum(axis=0)).sum(axis=1)
        expected_excl = received_excl / received_excl.mean() * 10
        assert not np.allclose(result.iwf_vector, expected_excl)

    def test_non_submitter_still_receives_iwf(self):
        """
        A non-submitter (NaN column) is skipped in summation but still
        gets an IWF from scores others gave them.

                  A(j=0)  B(j=1)  C(j=2)  D(j=3)
          A(i=0) [  10,      8,     12,    NaN  ]   → nansum = 30
          B(i=1) [  12,     10,      8,    NaN  ]   → nansum = 30
          C(i=2) [   8,     12,     10,    NaN  ]   → nansum = 30
          D(i=3) [   6,      6,      6,    NaN  ]   → nansum = 18

        Mean sum = (30+30+30+18)/4 = 27
        """
        matrix = np.array([
            [10,  8, 12, np.nan],
            [12, 10,  8, np.nan],
            [ 8, 12, 10, np.nan],
            [ 6,  6,  6, np.nan],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        assert len(result.students) == 4
        assert result.iwf_vector.mean() == pytest.approx(10.0)
        mean_sum = (30 + 30 + 30 + 18) / 4
        np.testing.assert_array_almost_equal(
            result.iwf_vector,
            [30 / mean_sum * 10, 30 / mean_sum * 10, 30 / mean_sum * 10, 18 / mean_sum * 10],
        )

    def test_grade_neutrality_holds_for_large_team(self):
        """Invariant holds regardless of team size or score distribution."""
        rng = np.random.default_rng(42)
        matrix = rng.integers(1, 20, size=(8, 8)).astype(float)

        result = webpa(_make_score_matrix(matrix))

        assert result.iwf_vector.mean() == pytest.approx(10.0)
