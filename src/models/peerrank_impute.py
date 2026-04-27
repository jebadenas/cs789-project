"""PeerRank-Impute: PeerRank with equal-score imputation for non-submitters."""

from __future__ import annotations

import numpy as np

from src.models.peerrank import peerrank
from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def peerrank_impute(
    score_matrix: ScoreMatrix,
    alpha: float = 0.1,
    epsilon: float = 1e-6,
    max_iterations: int = 1000,
) -> ModelResult:
    """Compute IWFs via PeerRank with equal-score imputation for non-submitters.

    Non-submitters (all-NaN columns) are imputed with equal raw scores —
    each teammate (including self) receives 10 points. After the core
    algorithm's normalisation step, this produces a neutral rater who
    allocates 1/(N-1) to each peer.

    Args:
        score_matrix: N×N peer-assessment matrix. NaN columns = non-submitters.
        alpha: Learning rate. Default 0.1 (Walsh 2014).
        epsilon: Convergence threshold (L1 norm). Default 1e-6.
        max_iterations: Iteration cap. Default 1000.

    Returns:
        ModelResult with IWF vector and convergence metadata.
    """
    matrix = score_matrix.matrix.copy()
    n = len(score_matrix.students)

    for j in range(n):
        col = matrix[:, j]
        peer_mask = np.ones(n, dtype=bool)
        peer_mask[j] = False
        if np.all(np.isnan(col[peer_mask])):
            # Non-submitter: impute with equal scores (10 to everyone)
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

    result = peerrank(imputed_sm, alpha=alpha, epsilon=epsilon, max_iterations=max_iterations)

    return ModelResult(
        model_name="PeerRank-Impute",
        iwf_vector=result.iwf_vector,
        students=result.students,
        converged=result.converged,
        iterations=result.iterations,
        final_l1_norm=result.final_l1_norm,
    )
