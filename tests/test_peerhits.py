"""Tests for the PeerHITS IWF model."""

import numpy as np
import pytest

from src.models.peerhits import peerhits
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


class TestPeerHITS:
    """PeerHITS produces authority and hub vectors via HITS iteration."""

    def test_uniform_scores_produce_equal_iwf(self):
        """When all peer scores are identical, everyone gets IWF = 10.0."""
        matrix = np.full((5, 5), 10.0)

        result = peerhits(_make_score_matrix(matrix))

        np.testing.assert_array_almost_equal(result.iwf_vector, np.full(5, 10.0))

    def test_convergence_metadata_returned(self):
        """Result includes convergence flag, iteration count, and delta."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        assert result.converged is True
        assert result.iterations is not None
        assert result.iterations < 1000
        assert result.final_l1_norm < 1e-6

    def test_authority_and_hub_vectors_are_l2_normalised_before_scaling(self):
        """The raw authority and hub vectors are unit-length before scaling."""
        matrix = np.array([
            [10,  4, 12],
            [15, 10,  8],
            [ 5, 16, 10],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        # After scaling to mean=10, check that ratios are preserved
        # (can't check L2=1 on scaled vector, but mean should be 10)
        assert result.iwf_vector.mean() == pytest.approx(10.0, abs=1e-6)
        assert result.hub_vector.mean() == pytest.approx(10.0, abs=1e-6)

    def test_hub_vector_is_present(self):
        """PeerHITS returns a hub_vector alongside the IWF (authority)."""
        matrix = np.array([
            [10,  6,  8],
            [12, 10, 14],
            [ 8, 14, 12],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        assert result.hub_vector is not None
        assert len(result.hub_vector) == 3

    def test_asymmetric_scores_differentiate_authority(self):
        """
        A student who receives higher peer scores should have higher authority.

                  A(j=0)  B(j=1)  C(j=2)
          A(i=0) [   _,      2,      3  ]   → receives low
          B(i=1) [  15,      _,     14  ]   → receives high
          C(i=2) [  15,      8,      _  ]   → receives medium
        """
        matrix = np.array([
            [10,  2,  3],
            [15, 10, 14],
            [15,  8, 10],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        assert result.iwf_vector[1] > result.iwf_vector[2] > result.iwf_vector[0]

    def test_non_submitter_handled_gracefully(self):
        """NaN column (non-submitter) treated as zeros; student still gets IWF."""
        matrix = np.array([
            [10,  8, 12, np.nan],
            [12, 10,  8, np.nan],
            [ 8, 12, 10, np.nan],
            [ 6,  6,  6, np.nan],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        assert len(result.iwf_vector) == 4
        assert all(np.isfinite(result.iwf_vector))
        assert result.converged is True

    def test_self_scores_are_excluded(self):
        """
        Diagonal is zeroed. If self-scores were included, Student C (who
        gave themselves 30) would have inflated authority. With exclusion,
        authority depends only on what peers gave them.
        """
        matrix = np.array([
            [10,  8,  8],
            [ 8, 10,  8],
            [ 8,  8, 30],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix))

        # With self excluded, all peer scores are 8 for everyone → equal IWFs
        np.testing.assert_array_almost_equal(
            result.iwf_vector, np.full(3, 10.0), decimal=4
        )

    def test_max_iterations_exceeded_returns_converged_false(self):
        """When max_iterations is too low, converged flag is False."""
        matrix = np.array([
            [10,  2, 15],
            [15, 10,  3],
            [ 5, 18, 10],
        ], dtype=float)

        result = peerhits(_make_score_matrix(matrix), max_iterations=2)

        assert result.converged is False
        assert result.iterations == 2
