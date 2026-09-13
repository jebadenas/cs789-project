"""Degeneracy classification for peer-rating score matrices.

A matrix is *degenerate* when it carries no usable peer-rating signal, for one of
two independent reasons:
  - **non_submitter**: a teammate left their column blank (partial data), or
  - **flat**: zero rater variation — everyone split points evenly, so the graph is
    structureless.

This is the sole surviving piece of the old team-dynamics package: `is_degenerate`
defines the RQ1 attack "clean set" (see `src.attacks.runner`). The archetypal-
analysis / Mahalanobis-atypicality lane this module used to host was cut (scope
revision 2026-08-18); the current dynamics work is the cascade in `src.cascade`.
"""

from __future__ import annotations

from src.dynamics.features import FEATURE_NAMES, TeamFeatures


def degenerate_cause(tf: TeamFeatures) -> str:
    """Why a team carries no usable signal: none / non_submitter / flat / both.

    The two causes are kept distinguishable for the data-quality write-up
    (participation failures vs. engagement failures).
    """
    has_non_sub = tf.non_submitter_count > 0
    mean_rater_std = float(tf.values[FEATURE_NAMES.index("mean_rater_std")])
    is_flat = mean_rater_std < 1e-9

    if has_non_sub and is_flat:
        return "both"
    if has_non_sub:
        return "non_submitter"
    if is_flat:
        return "flat"
    return "none"


def is_degenerate(tf: TeamFeatures) -> bool:
    """True if a team carries no usable peer-rating signal (any cause)."""
    return degenerate_cause(tf) != "none"
