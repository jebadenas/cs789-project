"""PeerHITS-Impute: PeerHITS with equal-score imputation for non-submitters."""

from __future__ import annotations

import numpy as np

from src.models.peerhits import peerhits
from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def peerhits_impute(
    score_matrix: ScoreMatrix,
    epsilon: float = 1e-6,
    max_iterations: int = 1000,
) -> ModelResult:
    """Compute IWFs via PeerHITS with equal-score imputation for non-submitters.

    Non-submitters (all-NaN columns) are imputed with equal raw scores —
    each teammate (including self) receives 10 points. The core algorithm
    then zeroes the diagonal and proceeds normally, giving the non-submitter
    neutral hub quality.

    Args:
        score_matrix: N×N peer-assessment matrix. NaN columns = non-submitters.
        epsilon: Convergence threshold (L1 norm of authority update). Default 1e-6.
        max_iterations: Iteration cap. Default 1000.

    Returns:
        ModelResult with IWF vector, hub_vector, and convergence metadata.
    """
    matrix = score_matrix.matrix.copy()
    n = len(score_matrix.students)

    for j in range(n):
        col = matrix[:, j]
        peer_mask = np.ones(n, dtype=bool)
        peer_mask[j] = False
        if np.all(np.isnan(col[peer_mask])):
            matrix[:, j] = 10.0

    imputed_sm = ScoreMatrix(
        matrix=matrix,
        team_name=score_matrix.team_name,
        question_label=score_matrix.question_label,
        year=score_matrix.year,
        semester=score_matrix.semester,
        session_number=score_matrix.session_number,
        students=score_matrix.students,
        excluded_students=score_matrix.excluded_students,
    )

    result = peerhits(imputed_sm, epsilon=epsilon, max_iterations=max_iterations)

    return ModelResult(
        model_name="PeerHITS-Impute",
        iwf_vector=result.iwf_vector,
        students=result.students,
        hub_vector=result.hub_vector,
        converged=result.converged,
        iterations=result.iterations,
        final_l1_norm=result.final_l1_norm,
    )
