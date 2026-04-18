"""WebPA (Willey & Gardner) peer-assessment factor model."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def webpa(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWFs using the WebPA peer-assessment factor.

    Self-scores are included per the original Willey & Gardner formulation.
    Non-submitter columns (all NaN) are handled via NaN-safe summation.

    The PA factor for student i is the ratio of scores received by i to the
    mean of scores received across all students. The result is scaled to a
    team mean of 10.0 for cross-model comparability.

    Args:
        score_matrix: N×N peer-assessment matrix (matrix[i][j] = score giver j
            gave to recipient i). NaN columns indicate non-submitters.

    Returns:
        ModelResult with IWF vector (team mean = 10.0).
    """
    scores_received = np.nansum(score_matrix.matrix, axis=1)
    mean_scores_received = scores_received.mean()

    pa_factors = scores_received / mean_scores_received
    iwf_vector = pa_factors * 10.0

    return ModelResult(
        model_name="WebPA",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
