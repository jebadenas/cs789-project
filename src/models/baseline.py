"""Simple Average (Baseline) IWF model.

Replicates the Kaufman et al. peer-rating formula used in COMPSCI 399.
IWF_i = NaN-aware mean of all scores received by student i (including
self-score).  Non-submitter columns (all NaN) are automatically excluded
from the denominator by ``np.nanmean``.
"""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def baseline_average(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWF as the simple mean of scores received per student.

    Parameters
    ----------
    score_matrix:
        N×N peer-assessment matrix where ``matrix[i][j]`` is the score
        giver *j* assigned to recipient *i*.  Non-submitter columns
        contain NaN.

    Returns
    -------
    ModelResult with the IWF vector (length N) and student identifiers.
    """
    iwf_vector = np.nanmean(score_matrix.matrix, axis=1)

    return ModelResult(
        model_name="Simple Average (Baseline)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
