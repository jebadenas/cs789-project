"""Tests for the PeerRank-Impute model variant."""

import numpy as np
import pytest

from src.models.peerrank_impute import peerrank_impute
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


class TestPeerRankImpute:
    """Behaviour: peerrank_impute imputes non-submitter columns with equal scores
    before running the PeerRank algorithm."""

    def test_model_name(self):
        """Behaviour: returns model_name 'PeerRank-Impute'."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank_impute(_make_score_matrix(matrix))
        assert result.model_name == "PeerRank-Impute"

    def test_no_non_submitters_matches_core_peerrank(self):
        """Behaviour: with no non-submitters, results are identical to core PeerRank."""
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        sm = _make_score_matrix(matrix)

        result_impute = peerrank_impute(sm)
        result_core = peerrank(sm)

        np.testing.assert_array_almost_equal(
            result_impute.iwf_vector, result_core.iwf_vector, decimal=6
        )

    def test_uniform_scores_with_non_submitter_all_equal(self):
        """Behaviour: uniform scores + non-submitter → all IWFs ≈ 10.0.

        This is the key fix for Issue #24. When all submitters give uniform
        scores, the imputed non-submitter also gives uniform scores, so
        all IWFs should be equal.
        """
        # 5 submitters give everyone 10, Student F (j=5) is non-submitter
        matrix = np.array([
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
            [10, 10, 10, 10, 10, np.nan],
        ], dtype=float)

        result = peerrank_impute(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(
            result.iwf_vector, np.full(6, 10.0), decimal=3
        )

    def test_non_submitter_gets_finite_iwf(self):
        """Behaviour: non-submitter receives a finite IWF (not NaN or Inf)."""
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank_impute(_make_score_matrix(matrix))

        assert len(result.iwf_vector) == 3
        assert np.all(np.isfinite(result.iwf_vector))

    def test_convergence_metadata_returned(self):
        """Behaviour: convergence metadata is passed through from core."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank_impute(_make_score_matrix(matrix))

        assert result.converged is True
        assert result.iterations is not None
        assert result.final_l1_norm is not None

    def test_full_student_list_preserved(self):
        """Behaviour: all students appear in result, including non-submitters."""
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank_impute(_make_score_matrix(matrix))

        assert len(result.students) == 3
        assert len(result.iwf_vector) == 3
