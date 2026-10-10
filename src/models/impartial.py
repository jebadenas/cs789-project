"""Impartial share: the 2026 CS399 weighting with rater-side normalisation.

Background (decisions.md 2026-10-11)
------------------------------------
From 2026 CS399 weights peer scores with the "average excluding self" (AES):
each student's mean peer score, self excluded, divided by the team's total AES
and multiplied by N. That is exactly ``baseline_normalised`` up to a constant.
It removes the whole-team zero-self uplift, but students still split a fixed
10·N budget *including themselves*, so a self-score still matters indirectly:
every point a rater keeps for themselves is a point their peers do not get,
which lowers the peers' AES and raises the rater's share of the team total.
(Worked example, N = 5, honest = 10 each: one rater giving self 30 and 5 to
each peer lifts their own weight from 10.0 to 11.1.)

This model closes that gap with one change: before averaging, each rater's
scores are divided by the average that rater gave their *peers* (self
excluded). A rater's self-score therefore never enters the calculation, and
only the *relative* split among peers counts.

Property: impartiality
----------------------
A student's weight depends only on other students' ratings, so nothing a
student reports can change their own weight. This is the impartiality
property of de Clippel, Moulin & Tideman (2008), "Impartial division of a
dollar", JET 139(1). Consequences checked in ``tests/test_impartial.py``:
self-inflation, partial and full zero-self all leave every weight unchanged.

Impartiality is not collusion-proofness: two students can still agree to rate
each other up or a third student down (targeted-downvote is unaffected).

Scale
-----
Neutral value 10 (a rater's average peer score maps to 10). On a complete
matrix the team mean is exactly 10 without any rescaling, because every
rater's normalised scores sum to N−1. The result is deliberately **not**
rescaled to the team mean: with missing ratings, rescaling would let a
student's own report move their weight through the team total, breaking
impartiality. On incomplete matrices the mean is therefore close to, not
exactly, 10.
"""

from __future__ import annotations

import warnings

import numpy as np

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix


def impartial_share(score_matrix: ScoreMatrix) -> ModelResult:
    """Compute IWFs as the self-excluded mean of rater-normalised peer scores.

    For each rater j, every score j gave a peer is divided by the mean score j
    gave their peers (self excluded). Each student's IWF is 10 × the mean of
    the normalised scores they received from others.

    Raters who gave every peer 0, and non-submitters (all-NaN columns),
    contribute nothing. A student nobody rated gets NaN.

    Args:
        score_matrix: N×N matrix, ``matrix[i][j]`` = score giver j gave
            recipient i. NaN = no rating.

    Returns:
        ModelResult with neutral value 10 (team mean exactly 10 on complete
        matrices).
    """
    peers = score_matrix.matrix.astype(float).copy()
    np.fill_diagonal(peers, np.nan)  # self-scores never enter

    with warnings.catch_warnings():  # all-NaN columns (non-submitters)
        warnings.simplefilter("ignore", RuntimeWarning)
        rater_means = np.nanmean(peers, axis=0)  # mean each rater gave peers
    usable = np.isfinite(rater_means) & (rater_means > 0.0)

    normalised = np.full_like(peers, np.nan)
    normalised[:, usable] = peers[:, usable] / rater_means[usable]

    with warnings.catch_warnings():  # students nobody rated
        warnings.simplefilter("ignore", RuntimeWarning)
        received = np.nanmean(normalised, axis=1)

    return ModelResult(
        model_name="Impartial Share",
        iwf_vector=received * 10.0,
        students=score_matrix.students,
    )
