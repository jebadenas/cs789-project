"""PeerHITS dual-score iterative IWF model."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def peerhits(
    score_matrix: ScoreMatrix,
    epsilon: float = 1e-6,
    max_iterations: int = 1000,
) -> ModelResult:
    """Compute IWFs via a HITS-inspired dual-score algorithm.

    Produces separate authority (contribution quality) and hub (assessment
    quality) vectors. Authority scores become the IWF; hub scores capture
    how well a student's ratings align with consensus.

    Each iteration:
      authority_i = sum over j≠i of (hub_j × score j gave to i)
      hub_j       = sum over i≠j of (authority_i × score j gave to i)

    Both vectors are L2-normalised after each update.

    Documentation items (audit 2026-08-09, Task 4)
    ----------------------------------------------
    **4a — raw scores, no rater normalisation (asymmetry with PeerRank).** This
    model operates on the raw score matrix, whereas ``peerrank.py`` column-
    normalises each rater's budget to sum 1. We keep raw scores deliberately and
    do **not** normalise: canonical HITS (Kleinberg 1999) is defined on the raw
    adjacency matrix, and column-normalising here would itself be a deviation from
    the published method and would manufacture a change with no source support.
    The consequence must be stated in §4: when the two "advanced" models are
    compared, part of the difference is this raw-vs-normalised asymmetry, not the
    algorithms alone. (Verified: this choice leaves PeerHITS output unchanged from
    the prior implementation — it is a documentation item, not a code change.)

    **4b — simultaneous vs sequential update.** Both vectors are updated from the
    *previous* iteration's values (simultaneous), rather than deriving the hub
    from the freshly-updated authority as in Kleinberg's sequential form. Both are
    power iterations on ``A Aᵀ`` / ``Aᵀ A`` and converge to the same principal
    eigenvector, so this is non-standard but not a bug; §4 should note it. The
    convergence check ``|new_authority − authority|`` can oscillate under the
    two-step period, but terminates cleanly on all 417 matrices (verified
    2026-08-09).

    Args:
        score_matrix: N×N peer-assessment matrix (matrix[i][j] = score giver j
            gave to recipient i). NaN columns indicate non-submitters.
        epsilon: Convergence threshold (L1 norm of authority update). Default 1e-6.
        max_iterations: Iteration cap. Default 1000.

    Returns:
        ModelResult with IWF vector (from authority scores, scaled to team
        mean = 10.0) and hub_vector.
    """
    matrix = score_matrix.matrix.copy()
    n = len(score_matrix.students)

    np.fill_diagonal(matrix, 0.0)
    matrix = np.nan_to_num(matrix, nan=0.0)

    authority = np.ones(n) / np.sqrt(n)
    hub = np.ones(n) / np.sqrt(n)

    converged = False
    final_delta = 0.0

    for iteration in range(1, max_iterations + 1):
        new_authority = matrix @ hub
        new_hub = matrix.T @ authority

        new_authority = _l2_normalise(new_authority)
        new_hub = _l2_normalise(new_hub)

        final_delta = float(np.sum(np.abs(new_authority - authority)))
        authority = new_authority
        hub = new_hub

        if final_delta < epsilon:
            converged = True
            break

    iwf_vector = _scale_to_mean_ten(authority)
    hub_scaled = _scale_to_mean_ten(hub)

    return ModelResult(
        model_name="PeerHITS",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
        hub_vector=hub_scaled,
        converged=converged,
        iterations=iteration,
        final_l1_norm=final_delta,
    )


def _l2_normalise(vector: np.ndarray) -> np.ndarray:
    """Normalise a vector to unit L2 length, returning zeros if norm is zero."""
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        return vector
    return vector / norm


def _scale_to_mean_ten(vector: np.ndarray) -> np.ndarray:
    """Scale a vector so its mean equals 10.0."""
    mean = vector.mean()
    if mean == 0.0:
        return vector
    return vector / mean * 10.0
