"""Tests for the PeerRank iterative IWF model."""

import numpy as np
import pytest

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


class TestPeerRank:
    """Behaviour: peerrank computes credibility-weighted IWFs via Walsh's fixed-point algorithm."""

    def test_3_person_team_returns_correct_iwf_and_model_name(self):
        """
        Tracer bullet: 3 students, asymmetric scores (diagonal=0, self excluded).

        Agreed test matrix (matrix[i][j] = score giver j gave to recipient i):

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [  0,      6,      3  ]
          B(i=1) [  3,      0,      6  ]
          C(i=2) [  6,      4,      0  ]

        Normalised A:
          a_BA=0.6, a_CA=1/3  (B and C allocated to A)
          a_AB=1/3, a_CB=2/3  (A and C allocated to B)
          a_AC=2/3, a_BC=0.4  (A and B allocated to C)

        Expected IWF (alpha=0.1, converges at iteration 104):
          [9.278, 10.196, 10.526]
        """
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank(_make_score_matrix(matrix))

        assert result.model_name == "PeerRank"
        assert len(result.students) == 3
        np.testing.assert_array_almost_equal(
            result.iwf_vector, [9.27786038, 10.19588629, 10.52625333], decimal=4
        )

    def test_alpha_controls_convergence_speed(self):
        """Behaviour: alpha is parameterized and affects convergence rate.

        PeerRank converges to the same fixed point regardless of alpha —
        alpha controls speed, not the final answer. A higher alpha converges
        in fewer iterations.
        """
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        sm = _make_score_matrix(matrix)

        result_slow = peerrank(sm, alpha=0.1)
        result_fast = peerrank(sm, alpha=0.5)

        assert result_fast.iterations < result_slow.iterations
        # Both converge to the same fixed point
        np.testing.assert_array_almost_equal(
            result_slow.iwf_vector, result_fast.iwf_vector, decimal=3
        )

    def test_convergence_metadata_is_returned(self):
        """Behaviour: converged=True, iteration count, and final L1 norm are returned."""
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank(_make_score_matrix(matrix), epsilon=1e-6)

        assert result.converged is True
        assert result.iterations == 104
        assert result.final_l1_norm is not None
        assert result.final_l1_norm < 1e-6

    def test_max_iterations_exceeded_returns_converged_false(self):
        """Behaviour: hitting max_iterations returns converged=False without raising."""
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)

        result = peerrank(_make_score_matrix(matrix), max_iterations=1)

        assert result.converged is False
        assert result.iterations == 1
        assert result.iwf_vector is not None

    def test_nan_column_non_submitter_is_handled(self):
        """Behaviour: NaN column (non-submitter) contributes no credibility weight,
        but the non-submitter still receives an IWF from peer scores they received.
        """
        from src.models.peerrank import peerrank

        # Student C (j=2) is a non-submitter — entire column is NaN
        matrix = np.array([
            [0,    6,    np.nan],
            [3,    0,    np.nan],
            [6,    4,    np.nan],
        ], dtype=float)

        result = peerrank(_make_score_matrix(matrix))

        assert len(result.iwf_vector) == 3
        assert np.all(np.isfinite(result.iwf_vector))

    def test_all_zero_non_nan_column_raises_value_error(self):
        """Behaviour: a submitted all-zero column is malformed and raises ValueError.

        Zero scores are distinguishable from non-submission (which uses NaN).
        An all-zero submission violates the 'distribute N points' constraint.
        """
        from src.models.peerrank import peerrank

        # Student B (j=1) submitted but gave everyone 0
        matrix = np.array([
            [0, 0, 3],
            [3, 0, 6],
            [6, 0, 0],
        ], dtype=float)

        with pytest.raises(ValueError, match="all-zero"):
            peerrank(_make_score_matrix(matrix))

    def test_uniform_scores_produce_equal_iwf(self):
        """Behaviour: uniform score matrix → all IWFs equal 10.0.

        When everyone gives equal scores, all credibility weights are equal
        and PeerRank degenerates to the simple average. Collusion is not
        detected — this is a known degenerate case documented in Walsh (2014).
        """
        from src.models.peerrank import peerrank

        matrix = np.array([
            [0, 10, 10, 10],
            [10, 0, 10, 10],
            [10, 10, 0, 10],
            [10, 10, 10, 0],
        ], dtype=float)

        result = peerrank(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(result.iwf_vector, np.full(4, 10.0))


class TestPeerRankAgainstDataset:
    """Validate PeerRank against the real COMPSCI 399 dataset."""

    @pytest.fixture(autouse=True)
    def require_data(self):
        from pathlib import Path
        data_dir = Path(__file__).parent.parent / "data"
        if not data_dir.exists():
            pytest.skip("data/ directory not present — place CSV files to run dataset tests")
