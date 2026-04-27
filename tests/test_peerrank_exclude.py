"""Tests for the PeerRank-Exclude model variant."""

import numpy as np
import pytest

from src.models.peerrank_exclude import peerrank_exclude
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


class TestPeerRankExclude:
    """Behaviour: peerrank_exclude removes non-submitters from the matrix and
    runs PeerRank on submitters only."""

    def test_model_name(self):
        """Behaviour: returns model_name 'PeerRank-Exclude'."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))
        assert result.model_name == "PeerRank-Exclude"

    def test_no_non_submitters_matches_core_peerrank(self):
        """Behaviour: with no non-submitters, results are identical to core PeerRank."""
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        sm = _make_score_matrix(matrix)

        result_exclude = peerrank_exclude(sm)
        result_core = peerrank(sm)

        np.testing.assert_array_almost_equal(
            result_exclude.iwf_vector, result_core.iwf_vector, decimal=6
        )

    def test_non_submitter_gets_nan_iwf(self):
        """Behaviour: excluded non-submitter receives NaN in the IWF vector."""
        # Student C (j=2) is non-submitter
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))

        assert np.isnan(result.iwf_vector[2]), "Non-submitter should have NaN IWF"

    def test_submitters_get_finite_iwf(self):
        """Behaviour: submitters receive finite IWFs when non-submitter is excluded."""
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))

        assert np.isfinite(result.iwf_vector[0])
        assert np.isfinite(result.iwf_vector[1])

    def test_submitter_iwfs_match_reduced_matrix(self):
        """Behaviour: submitter IWFs match running core PeerRank on the submatrix directly."""
        from src.models.peerrank import peerrank

        # Full 3×3 with Student C as non-submitter
        full_matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        # Manually reduced 2×2 of submitters A and B
        reduced_matrix = np.array([
            [0, 6],
            [3, 0],
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

        result_exclude = peerrank_exclude(_make_score_matrix(full_matrix))
        result_reduced = peerrank(reduced_sm)

        np.testing.assert_array_almost_equal(
            result_exclude.iwf_vector[:2], result_reduced.iwf_vector, decimal=6
        )

    def test_full_student_list_preserved(self):
        """Behaviour: all students appear in result, including excluded ones."""
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))

        assert len(result.students) == 3
        assert len(result.iwf_vector) == 3

    def test_fewer_than_2_submitters_returns_all_nan(self):
        """Behaviour: if fewer than 2 students submitted, all IWFs are NaN."""
        # Only Student A submitted; B is non-submitter
        matrix = np.array([
            [0,    np.nan],
            [5,    np.nan],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))

        assert np.all(np.isnan(result.iwf_vector))
        assert result.converged is None

    def test_all_non_submitters_returns_all_nan(self):
        """Behaviour: if all students are non-submitters, all IWFs are NaN."""
        matrix = np.full((3, 3), np.nan)

        result = peerrank_exclude(_make_score_matrix(matrix))

        assert np.all(np.isnan(result.iwf_vector))
        assert result.converged is None

    def test_convergence_metadata_returned(self):
        """Behaviour: convergence metadata is passed through from core."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank_exclude(_make_score_matrix(matrix))

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

        result = peerrank_exclude(_make_score_matrix(matrix))

        submitter_iwfs = result.iwf_vector[:3]
        np.testing.assert_array_almost_equal(submitter_iwfs, np.full(3, 10.0))
        assert np.isnan(result.iwf_vector[3])
