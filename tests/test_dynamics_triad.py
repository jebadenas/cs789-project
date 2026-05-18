"""Tests for src/dynamics/triad.py — directed triad census."""

from __future__ import annotations

import numpy as np
import networkx as nx
import pytest

from src.dynamics.triad import (
    TRIAD_CLASSES,
    binarize_rater_mean,
    triad_census_proportions,
)


def _adj(n: int, edges: list[tuple[int, int]], weights: dict | None = None) -> np.ndarray:
    """Build an A[giver][recipient] matrix with NaN on diagonal."""
    A = np.full((n, n), np.nan)
    np.fill_diagonal(A, np.nan)
    for i, j in edges:
        A[i, j] = (weights or {}).get((i, j), 10.0)
    return A


# ---------------------------------------------------------------------------
# binarize_rater_mean
# ---------------------------------------------------------------------------


class TestBinarizeRaterMean:
    """Edge i→j appears iff score(i→j) strictly > mean of rater i's valid scores."""

    def test_single_preferred_peer(self):
        """Rater gives [8, 10, 20] to three peers → mean=12.67 → only highest gets edge."""
        # 4 students: rater 0 gives to peers 1, 2, 3
        A = np.full((4, 4), np.nan)
        A[0, 1] = 8.0
        A[0, 2] = 10.0
        A[0, 3] = 20.0

        G = binarize_rater_mean(A)

        # mean = (8+10+20)/3 = 12.67; only 20 > 12.67
        assert G.has_edge(0, 3)
        assert not G.has_edge(0, 1)
        assert not G.has_edge(0, 2)

    def test_all_equal_scores_no_edges(self):
        """Rater with all equal scores: none strictly exceed the mean → no out-edges."""
        A = np.array([
            [np.nan, 12.0, 12.0, 12.0],
            [12.0, np.nan, 12.0, 12.0],
            [12.0, 12.0, np.nan, 12.0],
            [12.0, 12.0, 12.0, np.nan],
        ])
        G = binarize_rater_mean(A)

        assert G.number_of_edges() == 0

    def test_non_submitter_row_produces_no_edges(self):
        """Non-submitter (entire row NaN) generates no out-edges."""
        A = np.array([
            [np.nan, 12.0, 8.0],
            [10.0, np.nan, 14.0],
            [np.nan, np.nan, np.nan],  # non-submitter
        ])
        G = binarize_rater_mean(A)

        out_edges = list(G.out_edges(2))
        assert out_edges == []

    def test_no_self_loops(self):
        """Binarized graph must not contain self-loops."""
        A = np.array([
            [np.nan, 8.0, 20.0],
            [15.0, np.nan, 5.0],
            [6.0, 18.0, np.nan],
        ])
        G = binarize_rater_mean(A)

        for i in range(3):
            assert not G.has_edge(i, i)

    def test_only_strict_greater_than_mean(self):
        """Score exactly equal to mean is NOT an edge (strict >)."""
        # Rater 0: gives 10 and 10 → mean = 10; neither is strictly > 10
        A = np.array([
            [np.nan, 10.0, 10.0],
            [10.0, np.nan, 10.0],
            [10.0, 10.0, np.nan],
        ])
        G = binarize_rater_mean(A)

        assert G.number_of_edges() == 0

    def test_two_preferred_peers_among_four(self):
        """Rater 0 gives [5, 5, 15, 15] → mean=10 → edges to peers 2 and 3."""
        A = np.full((5, 5), np.nan)
        A[0, 1] = 5.0
        A[0, 2] = 5.0
        A[0, 3] = 15.0
        A[0, 4] = 15.0

        G = binarize_rater_mean(A)

        assert G.has_edge(0, 3)
        assert G.has_edge(0, 4)
        assert not G.has_edge(0, 1)
        assert not G.has_edge(0, 2)

    def test_returns_directed_graph(self):
        """Return type is networkx DiGraph."""
        A = np.array([[np.nan, 12.0], [8.0, np.nan]])
        G = binarize_rater_mean(A)
        assert isinstance(G, nx.DiGraph)

    def test_all_nodes_present(self):
        """All n nodes present even if isolated."""
        A = np.array([
            [np.nan, 12.0, 12.0],
            [12.0, np.nan, 12.0],
            [12.0, 12.0, np.nan],
        ])
        G = binarize_rater_mean(A)
        assert G.number_of_nodes() == 3


# ---------------------------------------------------------------------------
# triad_census_proportions
# ---------------------------------------------------------------------------


class TestTriadCensusProportions:

    def test_returns_all_16_classes(self):
        """Output dict has exactly the 16 directed triad classes."""
        G = nx.DiGraph()
        G.add_nodes_from(range(3))
        result = triad_census_proportions(G)
        assert set(result.keys()) == set(TRIAD_CLASSES)

    def test_empty_graph_all_003(self):
        """3-node graph with no edges → every triad is '003' (no connections)."""
        G = nx.DiGraph()
        G.add_nodes_from(range(3))
        result = triad_census_proportions(G)

        assert result["003"] == pytest.approx(1.0)
        for cls in TRIAD_CLASSES:
            if cls != "003":
                assert result[cls] == pytest.approx(0.0)

    def test_proportions_sum_to_one(self):
        """Proportions always sum to 1 when there are triads."""
        G = nx.DiGraph()
        G.add_nodes_from(range(5))
        # Add some asymmetric edges
        G.add_edges_from([(0, 1), (1, 2), (2, 0), (3, 4)])
        result = triad_census_proportions(G)

        assert sum(result.values()) == pytest.approx(1.0, abs=1e-9)

    def test_fully_connected_3_node_graph_all_300(self):
        """3 nodes with all 6 directed edges → single triad of type '300'."""
        G = nx.DiGraph()
        G.add_nodes_from(range(3))
        for i in range(3):
            for j in range(3):
                if i != j:
                    G.add_edge(i, j)

        result = triad_census_proportions(G)

        assert result["300"] == pytest.approx(1.0)

    def test_fewer_than_3_nodes_returns_zeros(self):
        """Graphs with < 3 nodes return all zeros."""
        for n in [0, 1, 2]:
            G = nx.DiGraph()
            G.add_nodes_from(range(n))
            result = triad_census_proportions(G)
            assert all(v == 0.0 for v in result.values()), f"Expected zeros for n={n}"

    def test_in_star_3_nodes_all_021U(self):
        """3-node in-star (B→A, C→A) → '021U' triad (two in, zero out from centre).

        Holland & Leinhardt notation:
          021U = two directed edges pointing into one node, no mutual ties.
        """
        G = nx.DiGraph()
        G.add_nodes_from([0, 1, 2])
        G.add_edge(1, 0)  # B→A
        G.add_edge(2, 0)  # C→A

        result = triad_census_proportions(G)

        assert result["021U"] == pytest.approx(1.0)

    def test_collusive_pattern_via_binarize(self):
        """Uniform scores → empty binary graph → all '003' triads.

        A team where everyone gives equal scores to all peers signals
        non-differentiating (collusive-like) behaviour in the triad census.
        """
        A = np.array([
            [np.nan, 12.0, 12.0, 12.0],
            [12.0, np.nan, 12.0, 12.0],
            [12.0, 12.0, np.nan, 12.0],
            [12.0, 12.0, 12.0, np.nan],
        ])
        G = binarize_rater_mean(A)
        result = triad_census_proportions(G)

        # No edges → all triads are 003
        assert result["003"] == pytest.approx(1.0)

    def test_dominant_member_pattern_via_binarize(self):
        """Concentrated scoring (all peers give max to one person) → 021U-dominated census.

        3-person team: raters A and B both concentrate points on C.
          A gives: B=0, C=20 → mean=10 → edge A→C
          B gives: A=0, C=20 → mean=10 → edge B→C
        This should produce an in-star at C.
        """
        A = np.array([
            [np.nan,  0.0, 20.0],
            [0.0,  np.nan, 20.0],
            [np.nan, np.nan, np.nan],  # C doesn't submit (non-submitter)
        ])
        G = binarize_rater_mean(A)
        result = triad_census_proportions(G)

        # Edges: A→C, B→C.  Triad (A,B,C): two edges into C → 021U
        assert result["021U"] == pytest.approx(1.0)
