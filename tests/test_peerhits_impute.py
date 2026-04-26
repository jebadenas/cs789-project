"""Tests for the PeerHITS-Impute model variant."""

import numpy as np
import pytest

from src.models.peerhits_impute import peerhits_impute
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


class TestPeerHITSImpute:
    """Behaviour: peerhits_impute imputes non-submitter columns with equal scores
    before running the PeerHITS algorithm."""

    def test_model_name(self):
        """Behaviour: returns model_name 'PeerHITS-Impute'."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))
        assert result.model_name == "PeerHITS-Impute"

    def test_no_non_submitters_matches_core_peerhits(self):
        """Behaviour: with no non-submitters, results are identical to core PeerHITS."""
        from src.models.peerhits import peerhits

        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)
        sm = _make_score_matrix(matrix)

        result_impute = peerhits_impute(sm)
        result_core = peerhits(sm)

        np.testing.assert_array_almost_equal(
            result_impute.iwf_vector, result_core.iwf_vector, decimal=6
        )
        np.testing.assert_array_almost_equal(
            result_impute.hub_vector, result_core.hub_vector, decimal=6
        )

    def test_uniform_scores_with_non_submitter_all_equal(self):
        """Behaviour: uniform scores + non-submitter → all IWFs ≈ 10.0.

        This is the key fix for Issue #24 (PeerHITS variant). When all
        submitters give uniform scores, the imputed non-submitter also gives
        uniform scores, so all IWFs should be equal.
        """
        matrix = np.array([
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(
            result.iwf_vector, np.full(6, 10.0), decimal=3
        )

    def test_non_submitter_gets_finite_iwf(self):
        """Behaviour: non-submitter receives a finite IWF (not NaN or Inf)."""
        matrix = np.array([
            [10,  8, 12, np.nan],
            [12, 10,  8, np.nan],
            [ 8, 12, 10, np.nan],
            [ 6,  6,  6, np.nan],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))

        assert len(result.iwf_vector) == 4
        assert np.all(np.isfinite(result.iwf_vector))

    def test_hub_vector_present_and_finite(self):
        """Behaviour: hub vector is returned and finite for all students including non-submitter."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))

        assert result.hub_vector is not None
        assert len(result.hub_vector) == 3
        assert np.all(np.isfinite(result.hub_vector))

    def test_convergence_metadata_returned(self):
        """Behaviour: convergence metadata is passed through from core."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))

        assert result.converged is True
        assert result.iterations is not None
        assert result.final_l1_norm is not None

    def test_full_student_list_preserved(self):
        """Behaviour: all students appear in result, including non-submitters."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_impute(_make_score_matrix(matrix))

        assert len(result.students) == 3
        assert len(result.iwf_vector) == 3
