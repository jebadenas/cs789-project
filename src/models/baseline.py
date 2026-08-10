"""Simple Average (Baseline) IWF models.

Two variants, deliberately separated (audit 2026-08-10, handoff-9b, reversing the
handoff-9 decision to scale the baseline):

- ``baseline_cs399`` — the **institutional instrument**. COMPSCI 399 gives each
  student a budget of 10·N points to distribute across the whole team (including
  themselves); a student's weight is the mean of the peer points they received,
  self excluded — ``total_from_peers / (N − 1)``. There is **no team
  normalisation**; the weight is an absolute figure with a neutral value of 10.
  The *level* carries signal (team means genuinely range 7.50–14.00 and correlate
  −0.475 with mean self-allocation), so it must not be scaled away. This is the
  model RQ1's attack analysis uses, because whole-team zero-self collusion raises
  everyone's weight by an exact amount (+25% at N=5, +20% at N=6) with no loser —
  a real grade uplift that is invisible to any normalised comparison.

- ``baseline_normalised`` — the same vector scaled to a team mean of 10.0, for
  like-for-like cross-model Δ only (the other three models self-normalise to 10).
  This view is **blind by construction to uniform level shifts**.

``baseline_average`` is kept as a backward-compatible alias for the institutional
``baseline_cs399`` (its pre-handoff-9 meaning); the cross-model Δ registry points
explicitly at ``baseline_normalised`` instead.
"""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def baseline_cs399(score_matrix: ScoreMatrix) -> ModelResult:
    """Institutional CS399 weight: self-excluded mean of peer points received.

    Unscaled — neutral value 10, but the level is meaningful and must not be
    normalised away. Equals ``total_points_from_peers / (N − 1)``.
    """
    matrix = score_matrix.matrix.copy()
    np.fill_diagonal(matrix, np.nan)
    iwf_vector = np.nanmean(matrix, axis=1)

    return ModelResult(
        model_name="Simple Average (CS399)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )


def baseline_normalised(score_matrix: ScoreMatrix) -> ModelResult:
    """``baseline_cs399`` scaled to a team mean of 10.0 (cross-model Δ only).

    Scaling is a per-team constant, so within-team ratios (relative standing) are
    preserved while the absolute level is discarded. Use this for Δ; use
    ``baseline_cs399`` for the absolute / institutional view.
    """
    res = baseline_cs399(score_matrix)
    iwf_vector = res.iwf_vector.copy()
    team_mean = np.nanmean(iwf_vector)
    if team_mean and not np.isnan(team_mean):
        iwf_vector = iwf_vector / team_mean * 10.0

    return ModelResult(
        model_name="Simple Average (normalised)",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )


# Backward-compatible default: the institutional model. Handoff-9b restores this
# as the default wherever "baseline" is referenced for reporting; the handoff-9
# team-mean-10 scaling misrepresented the instrument.
baseline_average = baseline_cs399
