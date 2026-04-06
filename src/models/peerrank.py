"""PeerRank iterative IWF model (Walsh 2014)."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def peerrank(
    score_matrix: ScoreMatrix,
    alpha: float = 0.1,
    epsilon: float = 1e-6,
    max_iterations: int = 1000,
) -> ModelResult:
    """Compute IWFs via Walsh's PeerRank fixed-point algorithm.

    Credibility weighting: a student rated poorly by peers has their votes
    dampened in subsequent iterations.

    Args:
        score_matrix: N×N peer-assessment matrix (matrix[i][j] = score giver j
            gave to recipient i). NaN columns indicate non-submitters.
        alpha: Learning rate in (0, 1). Default 0.1 follows Walsh (2014).
        epsilon: Convergence threshold (L1 norm of update). Default 1e-6.
        max_iterations: Iteration cap. Default 1000.

    Returns:
        ModelResult with IWF vector and convergence metadata.

    Raises:
        ValueError: If any non-NaN column sums to zero (all-zero submission).
    """
    matrix = score_matrix.matrix.copy()
    N = len(score_matrix.students)

    # Build normalised A matrix: a_ji = fraction of j's budget allocated to i
    # Self-scores (diagonal) excluded from normalisation and iteration.
    A = np.zeros((N, N))
    for j in range(N):
        col = matrix[:, j].copy()

        # Check for non-submitter using peer entries only (before zeroing diagonal)
        peer_mask = np.ones(N, dtype=bool)
        peer_mask[j] = False
        if np.all(np.isnan(col[peer_mask])):
            # Non-submitter: leave column as zeros (no credibility contribution)
            continue

        col[j] = 0.0  # exclude self-score
        col = np.nan_to_num(col, nan=0.0)
        col_sum = col.sum()

        if col_sum == 0.0:
            raise ValueError(
                f"Student {score_matrix.students[j].email} submitted all-zero "
                f"peer scores. Cannot normalise — check data quality."
            )

        A[:, j] = col / col_sum

    # Initialise grades: X_i^(0) = (1/(N-1)) * sum over j≠i of a_ji
    X = np.array([
        sum(A[i, j] for j in range(N) if j != i) / (N - 1)
        for i in range(N)
    ])
    X = X / X.sum()

    # Iterate until convergence or max_iterations
    converged = False
    final_l1_norm = 0.0

    for iteration in range(1, max_iterations + 1):
        X_new = np.zeros(N)
        for i in range(N):
            peer_indices = [j for j in range(N) if j != i]
            peer_grade_sum = sum(X[j] for j in peer_indices)
            weighted = sum(X[j] * A[i, j] for j in peer_indices)
            update = weighted / peer_grade_sum if peer_grade_sum > 0 else 0.0
            X_new[i] = (1 - alpha) * X[i] + alpha * update

        final_l1_norm = float(np.sum(np.abs(X_new - X)))
        X = X_new

        if final_l1_norm < epsilon:
            converged = True
            break

    # Convert to IWFs: IWF_i = X_i / X_bar * 10
    X_bar = X.mean()
    iwf_vector = X / X_bar * 10

    return ModelResult(
        model_name="PeerRank",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
        converged=converged,
        iterations=iteration,
        final_l1_norm=final_l1_norm,
    )
