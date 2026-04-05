"""Simple Average (Baseline) IWF model."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def baseline_average(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWF as the NaN-aware mean of scores received per student."""
    iwf_vector = np.nanmean(score_matrix.matrix, axis=1)

    return ModelResult(
        model_name="Simple Average (Baseline)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
