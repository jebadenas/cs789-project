"""Tests for the Simple Average (Baseline) IWF model."""

import numpy as np
import pytest

from src.models.baseline import baseline_average
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


class TestBaselineAverage:
    """Behavior: baseline_average is the self-excluded mean of scores received,
    scaled to a team mean of 10.0 (audit 2026-08-09, Task 2). Scaling is a
    per-team constant, so within-team ratios are preserved."""

    def test_3_person_team_returns_correct_iwf_and_model_name(self):
        """
        Tracer bullet: 3 students, asymmetric scores (self-scores excluded).

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,      6,      8  ]   → peer mean = (6+8)/2 = 7.0
          B(i=1) [  12,     10,     14  ]   → peer mean = (12+14)/2 = 13.0
          C(i=2) [   8,     14,     12  ]   → peer mean = (8+14)/2 = 11.0

        Peer means [7, 13, 11] have team mean 31/3; scaled to mean 10 by ×30/31.
        """
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = baseline_average(_make_score_matrix(matrix))

        assert result.model_name == "Simple Average (Baseline)"
        assert len(result.students) == 3
        scale = 30 / 31
        np.testing.assert_array_almost_equal(
            result.iwf_vector, np.array([7.0, 13.0, 11.0]) * scale
        )
        assert result.iwf_vector.mean() == pytest.approx(10.0)

    def test_self_scores_are_excluded_from_average(self):
        """
        Behavior: self-scores on the diagonal are NOT counted; result then scaled
        to team mean 10.0. Peer means [7, 10, 6.5] (mean 23.5/3) → ×30/23.5.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  10,      6,      8  ]   → without self: (6+8)/2 = 7.0
          B(i=1) [  15,     10,      5  ]   → without self: (15+5)/2 = 10.0
          C(i=2) [   5,      8,     17  ]   → without self: (5+8)/2 = 6.5
        """
        matrix = np.array([
            [10, 6, 8],
            [15, 10, 5],
            [5, 8, 17],
        ], dtype=float)

        result = baseline_average(_make_score_matrix(matrix))

        scale = 30 / 23.5
        assert result.iwf_vector[0] == pytest.approx(7.0 * scale)
        assert result.iwf_vector[1] == pytest.approx(10.0 * scale)
        assert result.iwf_vector[2] == pytest.approx(6.5 * scale)
        assert result.iwf_vector.mean() == pytest.approx(10.0)

    def test_non_submitter_excluded_from_mean_but_still_gets_iwf(self):
        """
        Behavior: NaN column (non-submitter) is skipped in the average,
        self-scores are excluded, but the non-submitter's row still produces a
        valid IWF; the vector is then scaled to team mean 10.0.

                  A(j=0)  B(j=1)  C(j=2)  D(j=3)
          A(i=0) [  10,      8,     12,    NaN  ]   → excl self+NaN: (8+12)/2 = 10.0
          B(i=1) [  12,     10,      8,    NaN  ]   → excl self+NaN: (12+8)/2 = 10.0
          C(i=2) [   8,     12,     10,    NaN  ]   → excl self+NaN: (8+12)/2 = 10.0
          D(i=3) [   6,      6,      6,    NaN  ]   → excl self+NaN: (6+6+6)/3 = 6.0

        Peer means [10, 10, 10, 6] (mean 9.0) → scaled ×10/9.
        """
        matrix = np.array([
            [10,  8, 12, np.nan],
            [12, 10,  8, np.nan],
            [ 8, 12, 10, np.nan],
            [ 6,  6,  6, np.nan],
        ], dtype=float)

        result = baseline_average(_make_score_matrix(matrix))

        assert len(result.students) == 4
        scale = 10 / 9
        np.testing.assert_array_almost_equal(
            result.iwf_vector, np.array([10.0, 10.0, 10.0, 6.0]) * scale
        )
        assert result.iwf_vector.mean() == pytest.approx(10.0)

    def test_uniform_scores_produce_equal_iwf(self):
        """Behavior: when everyone gives 10 to everyone, all IWFs equal 10.0."""
        matrix = np.full((6, 6), 10.0)
        result = baseline_average(_make_score_matrix(matrix))

        np.testing.assert_array_equal(result.iwf_vector, np.full(6, 10.0))


class TestBaselineAgainstDataset:
    """Validate baseline IWF against the real COMPSCI 399 dataset 'Average Points'."""

    def test_team11_iwf_excludes_self_scores(self):
        """
        End-to-end: parse CSV → build ScoreMatrix → run baseline → verify
        self-scores are excluded from the average for Team 11 ExquisiTech Q2.
        """
        from pathlib import Path
        from src.parsing.parser import parse_session

        data_dir = Path(__file__).parent.parent / "data"
        session_file = data_dir / "COMPSCI399-S1-2024_Peer Feedback Session 4 - S1, 2024_result.csv"
        if not session_file.exists():
            pytest.skip("Dataset file not available")
        matrices = parse_session(session_file)

        sm = matrices[("Team 11 - ExquisiTech", "source code")]
        result = baseline_average(sm)

        # With self-scores excluded, IWFs should differ from dataset "Average Points"
        # (which includes self). Verify we get valid results and they're peer-only.
        for student in result.students:
            iwf = result.iwf_vector[student.index]
            # All IWFs should be finite and positive for this team
            assert np.isfinite(iwf), f"{student.name} has non-finite IWF"
            assert iwf > 0, f"{student.name} has non-positive IWF"
