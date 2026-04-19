"""Build a NetworkX directed graph from a ScoreMatrix.

This module converts peer-assessment score matrices into weighted directed
graphs suitable for analysis (Girvan-Newman, centrality metrics) and
visualisation (force-layout, heatmap).

Edge convention: giver j → recipient i, weight = matrix[i][j].
Self-scores (diagonal) are excluded. NaN entries (non-submitters) are skipped.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from src.parsing.schemas import ScoreMatrix


def build_team_graph(score_matrix: ScoreMatrix) -> nx.DiGraph:
    """Build a directed weighted graph from a ScoreMatrix.

    Every student becomes a node (including non-submitters).
    Edge j → i is created with weight = matrix[i][j] when the value
    is finite and i ≠ j.

    Node attributes:
        name (str): Student's display name.
        email (str): Student's email.

    Edge attributes:
        weight (float): Raw peer-assessment score.

    Args:
        score_matrix: N×N peer-assessment matrix where matrix[i][j] is the
            score that giver j assigned to recipient i.

    Returns:
        A NetworkX DiGraph with N nodes and up to N*(N-1) edges.
    """
    G = nx.DiGraph()
    students = score_matrix.students
    matrix = score_matrix.matrix
    n = len(students)

    for s in students:
        G.add_node(s.index, name=s.name, email=s.email)

    for i in range(n):          # recipient
        for j in range(n):      # giver
            if i != j and np.isfinite(matrix[i][j]):
                G.add_edge(j, i, weight=float(matrix[i][j]))

    return G
