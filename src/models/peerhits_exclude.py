"""PeerHITS-Exclude: PeerHITS with non-submitters removed from the calculation."""

from __future__ import annotations

import numpy as np

from src.models.peerhits import peerhits
from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix, StudentInfo


def peerhits_exclude(
    score_matrix: ScoreMatrix,
    epsilon: float = 1e-6,
    max_iterations: int = 1000,
) -> ModelResult:
    """Compute IWFs via PeerHITS with non-submitters excluded entirely.

    Non-submitters (all-NaN columns) are removed from the score matrix
    before running PeerHITS. The algorithm runs on the reduced submatrix
    of submitting students only. Non-submitters receive NaN in both the
    IWF vector (authority) and hub vector.

    Args:
        score_matrix: N×N peer-assessment matrix. NaN columns = non-submitters.
        epsilon: Convergence threshold (L1 norm of authority update). Default 1e-6.
        max_iterations: Iteration cap. Default 1000.

    Returns:
        ModelResult with full-length IWF and hub vectors (NaN for excluded
        students) and complete students list.
    """
    matrix = score_matrix.matrix.copy()
    n = len(score_matrix.students)

    # Identify submitters (non-NaN columns)
    submitter_mask = np.zeros(n, dtype=bool)
    for j in range(n):
        col = matrix[:, j]
        peer_mask = np.ones(n, dtype=bool)
        peer_mask[j] = False
        submitter_mask[j] = not np.all(np.isnan(col[peer_mask]))

    submitter_indices = np.where(submitter_mask)[0]

    # Edge case: fewer than 2 submitters — cannot run PeerHITS
    if len(submitter_indices) < 2:
        iwf_vector = np.full(n, np.nan)
        hub_vector = np.full(n, np.nan)
        return ModelResult(
            model_name="PeerHITS-Exclude",
            iwf_vector=iwf_vector,
            students=score_matrix.students,
            hub_vector=hub_vector,
            converged=None,
            iterations=None,
            final_l1_norm=None,
        )

    # Build reduced submatrix: only submitter rows and columns
    sub_matrix = matrix[np.ix_(submitter_indices, submitter_indices)]
    sub_students = [
        StudentInfo(
            name=score_matrix.students[i].name,
            email=score_matrix.students[i].email,
            index=idx,
        )
        for idx, i in enumerate(submitter_indices)
    ]

    sub_sm = ScoreMatrix(
        matrix=sub_matrix,
        team_name=score_matrix.team_name,
        question_label=score_matrix.question_label,
        year=score_matrix.year,
        semester=score_matrix.semester,
        session_number=score_matrix.session_number,
        students=sub_students,
        excluded_students=score_matrix.excluded_students,
    )

    result = peerhits(sub_sm, epsilon=epsilon, max_iterations=max_iterations)

    # Reconstruct full-length vectors with NaN for excluded students
    iwf_vector = np.full(n, np.nan)
    hub_vector = np.full(n, np.nan)
    for idx, i in enumerate(submitter_indices):
        iwf_vector[i] = result.iwf_vector[idx]
        hub_vector[i] = result.hub_vector[idx]

    return ModelResult(
        model_name="PeerHITS-Exclude",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
        hub_vector=hub_vector,
        converged=result.converged,
        iterations=result.iterations,
        final_l1_norm=result.final_l1_norm,
    )
