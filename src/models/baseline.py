"""Simple Average (Baseline) IWF model."""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def baseline_average(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWF as the NaN-aware mean of peer scores received, excluding self.

    The mean is scaled to a team mean of 10.0 so it sits on the same scale as
    WebPA, PeerRank and PeerHITS. Without this, the baseline's team mean varies
    (pre-fix: mean 9.886, sd 0.565, range 7.50–14.00), and that scale offset
    leaks into every cross-model Δ as spurious "disagreement" that is really just
    a difference in level (audit 2026-08-09, Task 2). Scaling is a per-team
    constant and does not change the ordering of students within a team.
    """
    matrix = score_matrix.matrix.copy()
    np.fill_diagonal(matrix, np.nan)
    iwf_vector = np.nanmean(matrix, axis=1)

    team_mean = np.nanmean(iwf_vector)
    if team_mean and not np.isnan(team_mean):
        iwf_vector = iwf_vector / team_mean * 10.0

    return ModelResult(
        model_name="Simple Average (Baseline)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
