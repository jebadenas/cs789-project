"""Tests for the PeerHITS-Exclude model variant."""

import numpy as np
import pytest

from src.models.peerhits_exclude import peerhits_exclude
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


class TestPeerHITSExclude:
    """Behaviour: peerhits_exclude removes non-submitters from the matrix and
    runs PeerHITS on submitters only."""

    def test_model_name(self):
        """Behaviour: returns model_name 'PeerHITS-Exclude'."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))
        assert result.model_name == "PeerHITS-Exclude"

    def test_no_non_submitters_matches_core_peerhits(self):
        """Behaviour: with no non-submitters, results are identical to core PeerHITS."""
        from src.models.peerhits import peerhits

        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)
        sm = _make_score_matrix(matrix)

        result_exclude = peerhits_exclude(sm)
        result_core = peerhits(sm)

        np.testing.assert_array_almost_equal(
            result_exclude.iwf_vector, result_core.iwf_vector, decimal=6
        )
        np.testing.assert_array_almost_equal(
            result_exclude.hub_vector, result_core.hub_vector, decimal=6
        )

    def test_non_submitter_gets_nan_iwf(self):
        """Behaviour: excluded non-submitter receives NaN in the IWF vector."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert np.isnan(result.iwf_vector[2]), "Non-submitter should have NaN IWF"

    def test_non_submitter_gets_nan_hub(self):
        """Behaviour: excluded non-submitter receives NaN in the hub vector."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert result.hub_vector is not None
        assert np.isnan(result.hub_vector[2]), "Non-submitter should have NaN hub"

    def test_submitters_get_finite_iwf_and_hub(self):
        """Behaviour: submitters receive finite IWFs and hub scores."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert np.isfinite(result.iwf_vector[0])
        assert np.isfinite(result.iwf_vector[1])
        assert np.isfinite(result.hub_vector[0])
        assert np.isfinite(result.hub_vector[1])

    def test_submitter_iwfs_match_reduced_matrix(self):
        """Behaviour: submitter IWFs match running core PeerHITS on the submatrix."""
        from src.models.peerhits import peerhits

        full_matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        reduced_matrix = np.array([
            [10,  8],
            [12, 10],
        ], dtype=float)
        reduced_sm = ScoreMatrix(
            matrix=reduced_matrix,
            team_name="Test Team",
            question_label="test",
            year="2024",
            semester="S1",
            session_number=1,
            students=[
                StudentInfo(name="Student A", email="sa@test.ac.nz", index=0),
                StudentInfo(name="Student B", email="sb@test.ac.nz", index=1),
            ],
            excluded_students=[],
        )

        result_exclude = peerhits_exclude(_make_score_matrix(full_matrix))
        result_reduced = peerhits(reduced_sm)

        np.testing.assert_array_almost_equal(
            result_exclude.iwf_vector[:2], result_reduced.iwf_vector, decimal=6
        )
        np.testing.assert_array_almost_equal(
            result_exclude.hub_vector[:2], result_reduced.hub_vector, decimal=6
        )

    def test_full_student_list_preserved(self):
        """Behaviour: all students appear in result, including excluded ones."""
        matrix = np.array([
            [10,  8, np.nan],
            [12, 10, np.nan],
            [ 8, 12, np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert len(result.students) == 3
        assert len(result.iwf_vector) == 3
        assert len(result.hub_vector) == 3

    def test_fewer_than_2_submitters_returns_all_nan(self):
        """Behaviour: if fewer than 2 students submitted, all IWFs and hubs are NaN."""
        matrix = np.array([
            [10,    np.nan],
            [ 8,    np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert np.all(np.isnan(result.iwf_vector))
        assert np.all(np.isnan(result.hub_vector))
        assert result.converged is None

    def test_all_non_submitters_returns_all_nan(self):
        """Behaviour: if all students are non-submitters, all outputs are NaN."""
        matrix = np.full((3, 3), np.nan)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert np.all(np.isnan(result.iwf_vector))
        assert np.all(np.isnan(result.hub_vector))
        assert result.converged is None

    def test_convergence_metadata_returned(self):
        """Behaviour: convergence metadata is passed through from core."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        assert result.converged is True
        assert result.iterations is not None
        assert result.final_l1_norm is not None

    def test_uniform_scores_with_non_submitter(self):
        """Behaviour: uniform scores among submitters + excluded non-submitter
        → submitter IWFs all equal 10.0, non-submitter NaN."""
        matrix = np.array([
            [10, 10, 10, np.nan],
            [10, 10, 10, np.nan],
            [10, 10, 10, np.nan],
            [10, 10, 10, np.nan],
        ], dtype=float)

        result = peerhits_exclude(_make_score_matrix(matrix))

        submitter_iwfs = result.iwf_vector[:3]
        np.testing.assert_array_almost_equal(submitter_iwfs, np.full(3, 10.0))
        assert np.isnan(result.iwf_vector[3])
