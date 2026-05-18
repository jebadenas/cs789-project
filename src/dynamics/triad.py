"""Directed triad census on binarized peer-rating matrices.

Binarization rule: edge i→j exists iff giver i's score to recipient j strictly
exceeds giver i's mean score across all recipients (rater-mean threshold).

Returns the 16 directed triad-class proportions from Holland & Leinhardt (1976),
normalized so they sum to 1.  Flat raters (all scores equal) have zero out-edges
and will appear as isolated nodes — an intentional signal of non-differentiating
behaviour.
"""

from __future__ import annotations

import numpy as np
import networkx as nx

TRIAD_CLASSES: list[str] = [
    "003", "012", "102", "021D", "021U", "021C",
    "111D", "111U", "030T", "030C", "201",
    "120D", "120U", "120C", "210", "300",
]


def binarize_rater_mean(A: np.ndarray) -> nx.DiGraph:
    """Convert weighted adjacency A to binary DiGraph using rater-mean threshold.

    A[i][j] = score giver i gave to recipient j (NaN for self / non-submitters).
    Edge i→j is added iff A[i, j] > mean of giver i's valid scores.
    """
    n = A.shape[0]
    G = nx.DiGraph()
    G.add_nodes_from(range(n))

    for i in range(n):
        row = A[i, :]
        valid = row[~np.isnan(row)]
        if valid.size == 0:
            continue
        rater_mean = float(np.mean(valid))
        for j in range(n):
            if i != j and not np.isnan(row[j]) and row[j] > rater_mean:
                G.add_edge(i, j)

    return G


def triad_census_proportions(G: nx.DiGraph) -> dict[str, float]:
    """Return normalized proportions of each of the 16 directed triad classes.

    Returns all-zeros if the graph has fewer than 3 nodes or no triads.
    """
    if G.number_of_nodes() < 3:
        return {cls: 0.0 for cls in TRIAD_CLASSES}

    census = nx.triadic_census(G)
    total = sum(census.values())

    if total == 0:
        return {cls: 0.0 for cls in TRIAD_CLASSES}

    return {cls: census.get(cls, 0) / total for cls in TRIAD_CLASSES}
