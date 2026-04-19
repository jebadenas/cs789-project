"""Tests for the graph builder (src/visualization/graph.py)."""

import numpy as np
import pytest

from src.parsing.schemas import ScoreMatrix, StudentInfo
from src.visualization.graph import build_team_graph


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


class TestBuildTeamGraph:
    """Behaviour: build_team_graph converts a ScoreMatrix into a directed weighted graph."""

    def test_3_person_team_node_count(self):
        """All 3 students appear as nodes."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))
        assert G.number_of_nodes() == 3

    def test_3_person_team_edge_count(self):
        """3 students, no self-loops → 3*2 = 6 directed edges."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))
        assert G.number_of_edges() == 6

    def test_edge_direction_and_weight(self):
        """Edge j→i has weight = matrix[i][j]."""
        matrix = np.array([
            [0, 6, 3],
            [3, 0, 6],
            [6, 4, 0],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        # matrix[0][1] = 6 means giver j=1 → recipient i=0, weight=6
        assert G.has_edge(1, 0)
        assert G[1][0]["weight"] == 6.0

        # matrix[2][0] = 6 means giver j=0 → recipient i=2, weight=6
        assert G.has_edge(0, 2)
        assert G[0][2]["weight"] == 6.0

    def test_self_loops_excluded(self):
        """Diagonal entries (self-scores) must not create edges."""
        matrix = np.array([
            [10, 6, 3],
            [3, 10, 6],
            [6, 4, 10],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        for nid in G.nodes:
            assert not G.has_edge(nid, nid), f"Self-loop found on node {nid}"

    def test_nan_column_non_submitter_no_outgoing_edges(self):
        """NaN column (non-submitter) → no outgoing edges from that student."""
        matrix = np.array([
            [0, 6, np.nan],
            [3, 0, np.nan],
            [6, 4, np.nan],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        # Student C (index=2) is a non-submitter
        outgoing_from_c = list(G.successors(2))
        assert outgoing_from_c == [], "Non-submitter should have no outgoing edges"

    def test_nan_non_submitter_still_has_node(self):
        """Non-submitter still appears as a node."""
        matrix = np.array([
            [0, 6, np.nan],
            [3, 0, np.nan],
            [6, 4, np.nan],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        assert 2 in G.nodes, "Non-submitter node should be present"
        assert G.number_of_nodes() == 3

    def test_nan_non_submitter_receives_incoming_edges(self):
        """Non-submitter still has incoming edges (others scored them)."""
        matrix = np.array([
            [0, 6, np.nan],
            [3, 0, np.nan],
            [6, 4, np.nan],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        incoming_to_c = list(G.predecessors(2))
        assert len(incoming_to_c) == 2, "Non-submitter should receive edges from A and B"

    def test_node_attributes(self):
        """Nodes carry name and email attributes from StudentInfo."""
        matrix = np.array([[0, 5], [5, 0]], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        assert G.nodes[0]["name"] == "Student A"
        assert G.nodes[0]["email"] == "sa@test.ac.nz"

    def test_4_person_team_full_connectivity(self):
        """4 students, all finite scores → 4*3 = 12 edges."""
        matrix = np.array([
            [0, 3, 4, 5],
            [6, 0, 7, 8],
            [2, 1, 0, 9],
            [4, 5, 3, 0],
        ], dtype=float)
        G = build_team_graph(_make_score_matrix(matrix))

        assert G.number_of_nodes() == 4
        assert G.number_of_edges() == 12
