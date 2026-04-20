"""Smoke tests for the force-layout visualisation (src/visualization/force_layout.py)."""

import numpy as np
import plotly.graph_objects as go
import pytest

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix, StudentInfo
from src.visualization.force_layout import force_layout


def _make_score_matrix(matrix: np.ndarray, **kwargs) -> ScoreMatrix:
    """Build a ScoreMatrix from a numpy array with sensible defaults."""
    n = matrix.shape[0]
    defaults = dict(
        matrix=matrix,
        team_name="Test Team",
        question_label="test",
        year="2024",
        semester="S1",
        session_number=1,
        students=[
            StudentInfo(
                name=f"Student {chr(65 + i)}",
                email=f"s{chr(97 + i)}@test.ac.nz",
                index=i,
            )
            for i in range(n)
        ],
        excluded_students=[],
    )
    defaults.update(kwargs)
    return ScoreMatrix(**defaults)


def _make_model_result(iwf_vector: np.ndarray, students: list[StudentInfo]) -> ModelResult:
    """Build a ModelResult with the given IWF vector."""
    return ModelResult(
        model_name="Test Model",
        iwf_vector=iwf_vector,
        students=students,
    )


class TestForceLayout:
    """Behaviour: force_layout produces an interactive Plotly figure."""

    def test_returns_plotly_figure(self):
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))
        assert isinstance(fig, go.Figure)

    def test_figure_has_expected_traces(self):
        """6 edge traces + 1 arrow trace + 1 node trace = 8 total."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))

        # 6 edges (3 students, no self-loops) + 1 arrow marker + 1 node
        assert len(fig.data) == 8

    def test_title_contains_team_and_question(self):
        matrix = np.array([[0, 5], [5, 0]], dtype=float)
        sm = _make_score_matrix(matrix, team_name="Alpha", question_label="Q1")
        fig = force_layout(sm)
        assert "Alpha" in fig.layout.title.text
        assert "Q1" in fig.layout.title.text

    def test_with_model_result(self):
        """Providing a ModelResult should not crash and should use IWF for colour."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        sm = _make_score_matrix(matrix)
        mr = _make_model_result(
            iwf_vector=np.array([9.0, 10.0, 11.0]),
            students=sm.students,
        )
        fig = force_layout(sm, model_result=mr)
        assert isinstance(fig, go.Figure)

    def test_nan_non_submitter_does_not_crash(self):
        matrix = np.array([
            [0, 6, np.nan],
            [3, 0, np.nan],
            [6, 4, np.nan],
        ], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))
        assert isinstance(fig, go.Figure)

    def test_2_person_team(self):
        """Minimal team: 2 students, 2 edges."""
        matrix = np.array([[0, 8], [5, 0]], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))
        # 2 edge traces + 1 arrow + 1 node = 4
        assert len(fig.data) == 4

    def test_uniform_scores(self):
        """All identical scores should not crash (zero-spread edge case)."""
        matrix = np.array([
            [0, 10, 10],
            [10, 0, 10],
            [10, 10, 0],
        ], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))
        assert isinstance(fig, go.Figure)

    def test_axes_are_hidden(self):
        """Layout should hide axes since positions are abstract."""
        matrix = np.array([[0, 5], [5, 0]], dtype=float)
        fig = force_layout(_make_score_matrix(matrix))
        assert fig.layout.xaxis.visible is False
        assert fig.layout.yaxis.visible is False
