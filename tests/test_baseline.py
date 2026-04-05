"""Tests for the Simple Average (Baseline) IWF model."""

from pathlib import Path

import numpy as np
import pytest

from src.models.baseline import baseline_average
from src.parsing.schemas import ScoreMatrix, StudentInfo

DATA_DIR = Path(__file__).parent.parent / "data"
SESSION_4_2024 = DATA_DIR / "COMPSCI399-S1-2024_Peer Feedback Session 4 - S1, 2024_result.csv"


def _make_students(n: int) -> list[StudentInfo]:
    """Create n dummy students with alphabetical emails."""
    return [
        StudentInfo(name=f"Student {chr(65 + i)}", email=f"s{chr(97 + i)}@test.ac.nz", index=i)
        for i in range(n)
    ]


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
        students=_make_students(n),
        excluded_students=[],
    )
    defaults.update(kwargs)
    return ScoreMatrix(**defaults)


class TestHandComputed3Person:
    """Hand-computed 3-person example with known IWF values."""

    def test_asymmetric_scores(self):
        """
        3 students, all submitted:
          S[i][j] = score giver j gave to recipient i

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,     12,      8  ]   → mean = (10+12+8)/3 = 10.0
          B(i=1) [  15,     10,      5  ]   → mean = (15+10+5)/3 = 10.0
          C(i=2) [   5,      8,     17  ]   → mean = (5+8+17)/3  = 10.0
        """
        matrix = np.array([
            [10, 12, 8],
            [15, 10, 5],
            [5,  8, 17],
        ], dtype=float)

        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        assert result.model_name == "Simple Average (Baseline)"
        assert len(result.students) == 3
        np.testing.assert_array_almost_equal(result.iwf_vector, [10.0, 10.0, 10.0])

    def test_unequal_scores(self):
        """
        3 students with non-uniform averages:

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,      6,      8  ]   → mean = 24/3 = 8.0
          B(i=1) [  12,     10,     14  ]   → mean = 36/3 = 12.0
          C(i=2) [   8,     14,     12  ]   → mean = 34/3 ≈ 11.333
        """
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        expected = [24 / 3, 36 / 3, 34 / 3]
        np.testing.assert_array_almost_equal(result.iwf_vector, expected)


class TestUniformMatrix:
    """When everyone gives 10 to everyone, all IWFs equal 10.0."""

    def test_uniform_4_person(self):
        matrix = np.full((4, 4), 10.0)
        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        np.testing.assert_array_equal(result.iwf_vector, np.full(4, 10.0))

    def test_uniform_6_person(self):
        matrix = np.full((6, 6), 10.0)
        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        np.testing.assert_array_equal(result.iwf_vector, np.full(6, 10.0))


class TestNonSubmitter:
    """Non-submitter columns (NaN) are excluded from the mean via np.nanmean."""

    def test_one_non_submitter_in_4_person_team(self):
        """
        4 students, student D (j=3) is non-submitter (column all NaN).
        3 submitters rate all 4 students.

                  A(j=0)  B(j=1)  C(j=2)  D(j=3)
          A(i=0) [  10,      8,     12,    NaN  ]   → nanmean = 30/3 = 10.0
          B(i=1) [  12,     10,      8,    NaN  ]   → nanmean = 30/3 = 10.0
          C(i=2) [   8,     12,     10,    NaN  ]   → nanmean = 30/3 = 10.0
          D(i=3) [  10,     10,     10,    NaN  ]   → nanmean = 30/3 = 10.0
        """
        matrix = np.array([
            [10,  8, 12, np.nan],
            [12, 10,  8, np.nan],
            [ 8, 12, 10, np.nan],
            [10, 10, 10, np.nan],
        ], dtype=float)

        students = _make_students(4)
        excluded = [students[3]]

        sm = _make_score_matrix(matrix, excluded_students=excluded)
        result = baseline_average(sm)

        np.testing.assert_array_almost_equal(result.iwf_vector, [10.0, 10.0, 10.0, 10.0])
        assert len(result.students) == 4

    def test_non_submitter_gets_different_iwf(self):
        """
        Non-submitter still receives peer ratings and gets a valid IWF.

                  A(j=0)  B(j=1)  C(j=2)  D(j=3)
          A(i=0) [  10,     12,      8,    NaN  ]   → nanmean = 30/3 = 10.0
          B(i=1) [  15,     10,      5,    NaN  ]   → nanmean = 30/3 = 10.0
          C(i=2) [   5,      8,     17,    NaN  ]   → nanmean = 30/3 = 10.0
          D(i=3) [   5,      5,      5,    NaN  ]   → nanmean = 15/3 = 5.0
        """
        matrix = np.array([
            [10, 12,  8, np.nan],
            [15, 10,  5, np.nan],
            [ 5,  8, 17, np.nan],
            [ 5,  5,  5, np.nan],
        ], dtype=float)

        students = _make_students(4)
        excluded = [students[3]]

        sm = _make_score_matrix(matrix, excluded_students=excluded)
        result = baseline_average(sm)

        np.testing.assert_array_almost_equal(result.iwf_vector, [10.0, 10.0, 10.0, 5.0])


class TestModelResultFields:
    """ModelResult has all required fields."""

    def test_result_has_model_name(self):
        matrix = np.full((3, 3), 10.0)
        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        assert result.model_name == "Simple Average (Baseline)"

    def test_result_has_student_identifiers(self):
        matrix = np.full((3, 3), 10.0)
        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        assert len(result.students) == 3
        assert all(s.email for s in result.students)
        assert all(s.name for s in result.students)

    def test_convergence_fields_are_none(self):
        matrix = np.full((3, 3), 10.0)
        sm = _make_score_matrix(matrix)
        result = baseline_average(sm)

        assert result.iterations is None
        assert result.converged is None
        assert result.hub_vector is None


class TestTeam11ExquisiTech:
    """Validate baseline IWF against dataset summary 'Average Points' for Team 11."""

    def test_iwf_matches_dataset_averages(self):
        from src.parsing.parser import parse_session

        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        model_result = baseline_average(sm)

        # Dataset "Average Points" (Q2, source code) for Team 11:
        expected_averages = {
            "alee314@aucklanduni.ac.nz": 9.0,
            "aqui206@aucklanduni.ac.nz": 10.17,
            "hemm904@aucklanduni.ac.nz": 11.67,
            "jhe435@aucklanduni.ac.nz": 6.83,
            "kwil492@aucklanduni.ac.nz": 10.0,
            "llam106@aucklanduni.ac.nz": 12.33,
        }

        for student in model_result.students:
            iwf = model_result.iwf_vector[student.index]
            expected = expected_averages[student.email]
            assert abs(iwf - expected) < 0.01, (
                f"{student.email}: IWF {iwf:.2f} != expected {expected}"
            )
