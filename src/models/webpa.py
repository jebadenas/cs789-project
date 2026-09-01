"""WebPA (Willey & Gardner) peer-assessment factor model.

Normalisation and the fixed-budget instrument (audit 2026-08-09)
----------------------------------------------------------------
WebPA's defining step is to divide every score a rater awarded by that rater's
own total, so each rater contributes fractional scores summing to 1 before the
received fractions are summed per student. This module implements that step
canonically, dividing by the rater's total **including their self-score**, per
Willey & Gardner and the Loughborough worked example.

On *this* dataset the normalisation is a **mathematically exact no-op**. The
instrument is a fixed-budget zero-sum allocation: every rater distributes the
same team total (verified — rater column sums *including* self are constant,
spread exactly 0, in all 417 matrices). Dividing every column by the same
constant cancels in the PA factor, so canonical WebPA reproduces the
un-normalised received-score ratio exactly (verified r = 1.0000 vs the previous
implementation; see `tests/test_webpa.py`).

The normalisation is therefore *redundant by design here, not omitted by error*:
the instrument enforces upfront exactly what the normalisation exists to enforce.
A consequence is that WebPA and the simple average are near-equivalent on this
data (WebPA↔baseline mean r = 0.967, median 0.987); the residual difference is
self-score inclusion (WebPA keeps it, baseline drops it) and missing-rater
handling, **not** peer weighting. This bears directly on the "four models
compared" framing in §3/§5 and should be stated plainly.

We deliberately do **not** normalise over peers only. That would deviate from the
published method, manufacture model separation that does not exist in the data,
and break the zero-self attack analysis — that attack works precisely because
self-scores sit inside the budget, so zeroing your own score frees points to
redirect; under peer-only normalisation the manipulation would become
arithmetically invisible.
"""

from __future__ import annotations

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def webpa(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWFs using the WebPA peer-assessment factor.

    Each rater's ratings are divided by that rater's total (self-score included)
    to give fractional scores summing to 1; the fractions each student receives
    are summed, and the PA factor is that sum over the team-mean sum. On the
    fixed-budget instrument here the division is exactly redundant (see module
    docstring). Non-submitter columns (all NaN → zero total) contribute nothing.

    Args:
        score_matrix: N×N peer-assessment matrix (matrix[i][j] = score giver j
            gave to recipient i). NaN columns indicate non-submitters.

    Returns:
        ModelResult with IWF vector (team mean = 10.0).
    """
    matrix = score_matrix.matrix.astype(float)

    # Per-rater totals (column sums), self-score included. Non-submitter columns
    # (all NaN) and all-zero columns give a zero total and contribute no fraction.
    rater_totals = np.nansum(matrix, axis=0)
    fractional = np.zeros_like(matrix)
    active = rater_totals > 0.0
    fractional[:, active] = (
        np.nan_to_num(matrix[:, active], nan=0.0) / rater_totals[active]
    )

    scores_received = fractional.sum(axis=1)
    mean_scores_received = scores_received.mean()

    if mean_scores_received == 0.0:
        raise ValueError(
            "All scores in the matrix are zero. Cannot compute WebPA factors "
            "— check data quality."
        )

    pa_factors = scores_received / mean_scores_received
    iwf_vector = pa_factors * 10.0

    return ModelResult(
        model_name="WebPA",
        iwf_vector=iwf_vector,
        students=score_matrix.students,
    )
