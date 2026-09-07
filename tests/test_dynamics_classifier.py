"""Tests for src/dynamics/classifier.py — degeneracy classification."""

from __future__ import annotations

import numpy as np

from src.dynamics.classifier import degenerate_cause, is_degenerate
from src.dynamics.features import FEATURE_NAMES, TeamFeatures


def _tf(non_submitter_count: int, mean_rater_std: float) -> TeamFeatures:
    """Minimal TeamFeatures with just the two fields degeneracy reads."""
    values = np.ones(len(FEATURE_NAMES), dtype=float)
    values[FEATURE_NAMES.index("mean_rater_std")] = mean_rater_std
    return TeamFeatures(
        csv_path="", team_name="T", question_label="Q1",
        values=values, n_students=5, non_submitter_count=non_submitter_count,
    )


class TestDegeneracy:

    def test_clean_matrix_is_not_degenerate(self):
        tf = _tf(non_submitter_count=0, mean_rater_std=1.5)
        assert degenerate_cause(tf) == "none"
        assert is_degenerate(tf) is False

    def test_flat_matrix(self):
        tf = _tf(non_submitter_count=0, mean_rater_std=0.0)
        assert degenerate_cause(tf) == "flat"
        assert is_degenerate(tf) is True

    def test_non_submitter(self):
        tf = _tf(non_submitter_count=1, mean_rater_std=1.5)
        assert degenerate_cause(tf) == "non_submitter"
        assert is_degenerate(tf) is True

    def test_both_causes(self):
        tf = _tf(non_submitter_count=2, mean_rater_std=0.0)
        assert degenerate_cause(tf) == "both"
        assert is_degenerate(tf) is True
