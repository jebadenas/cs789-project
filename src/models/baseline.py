"""Simple Average (Baseline) IWF model."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def baseline_average(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWF as the NaN-aware mean of peer scores received, excluding self-scores."""
    matrix = score_matrix.matrix.copy()
    np.fill_diagonal(matrix, np.nan)
    iwf_vector = np.nanmean(matrix, axis=1)

    return ModelResult(
        model_name="Simple Average (Baseline)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
