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
        Students who receive more total points get higher IWFs.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,      6,      8  ]   → sum = 24
          B(i=1) [  12,     10,     14  ]   → sum = 36
          C(i=2) [   8,     14,     12  ]   → sum = 34

        Mean sum = (24+36+34)/3 = 31.333
        PA_A = 24/31.333 = 0.766  → IWF = 7.66
        PA_B = 36/31.333 = 1.149  → IWF = 11.49
        PA_C = 34/31.333 = 1.085  → IWF = 10.85
        """
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        assert result.model_name == "WebPA"
        assert len(result.students) == 3
        mean_sum = (24 + 36 + 34) / 3
        np.testing.assert_array_almost_equal(
            result.iwf_vector,
            [24 / mean_sum * 10, 36 / mean_sum * 10, 34 / mean_sum * 10],
        )

    def test_uniform_scores_produce_equal_iwf(self):
        """When everyone gives equal scores, all IWFs are 10.0."""
        matrix = np.full((5, 5), 10.0)

        result = webpa(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(result.iwf_vector, np.full(5, 10.0))

    def test_self_scores_are_included(self):
        """
        WebPA includes self-scores (original paper). Verify by checking
        that the sum uses the diagonal value.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  20,      6,      8  ]   → sum = 34 (includes self=20)
          B(i=1) [   5,     10,      5  ]   → sum = 20
          C(i=2) [   5,      8,     17  ]   → sum = 30

        If self were excluded: A sum=14, B sum=10, C sum=13
        """
        matrix = np.array([
            [20, 6, 8],
            [5, 10, 5],
            [5, 8, 17],
        ], dtype=float)

        result = webpa(_make_score_matrix(matrix))

        mean_sum = (34 + 20 + 30) / 3
        assert result.iwf_vector[0] == pytest.approx(34 / mean_sum * 10)

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
