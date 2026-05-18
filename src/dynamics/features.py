"""Feature extraction for team-dynamics classification.

Produces a fixed-length feature vector per ScoreMatrix combining weighted-graph
behavioural metrics and rater-mean-binarized triad-census proportions.

Matrix convention: ScoreMatrix.matrix[i][j] = score giver j assigned to recipient i.
All computation here uses A = matrix.T where A[giver][recipient].

Non-submitters (entire column NaN in matrix → entire row NaN in A) are excluded
from graph metrics; their fraction is captured as a separate scalar feature.
Self-scores are excluded from the graph and captured as mean_self_share.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import networkx as nx

from src.parsing.schemas import ScoreMatrix
from src.dynamics.triad import TRIAD_CLASSES, binarize_rater_mean, triad_census_proportions


BEHAVIORAL_FEATURE_NAMES: list[str] = [
    "reciprocity",
    "gini_in_degree",
    "mean_rater_std",
    "std_rater_std",
    "asymmetry",
    "clustering",
    "assortativity",
    "non_submitter_frac",
    "mean_self_share",
]

FEATURE_NAMES: list[str] = BEHAVIORAL_FEATURE_NAMES + [f"triad_{c}" for c in TRIAD_CLASSES]


@dataclass(frozen=True)
class TeamFeatures:
    """Fixed-length feature vector for one score matrix."""

    csv_path: str
    team_name: str
    question_label: str
    values: np.ndarray
    n_students: int
    non_submitter_count: int


def extract_features(
    sm: ScoreMatrix,
    csv_path: str = "",
    question_label: str = "",
) -> TeamFeatures:
    """Extract the 25-dim feature vector from a ScoreMatrix."""
    n = sm.matrix.shape[0]
    A = sm.matrix.T.copy().astype(float)  # A[giver][recipient]

    non_sub_mask = np.all(np.isnan(sm.matrix), axis=0)
    non_submitter_count = int(non_sub_mask.sum())
    non_submitter_frac = non_submitter_count / n

    diag = np.array([sm.matrix[i, i] for i in range(n)], dtype=float)
    mean_self_share = float(np.nanmean(diag / 60.0)) if not np.all(np.isnan(diag)) else 0.0

    np.fill_diagonal(A, np.nan)

    reciprocity = _reciprocity(A)
    gini = _gini(np.nanmean(A, axis=0))
    mean_std, std_std = _rater_variance(A)
    asymmetry = _asymmetry(A)
    clustering, assortativity = _graph_metrics(A, n)

    behavioral: list[float] = [
        reciprocity, gini, mean_std, std_std, asymmetry,
        clustering, assortativity, non_submitter_frac, mean_self_share,
    ]

    G_bin = binarize_rater_mean(A)
    proportions = triad_census_proportions(G_bin)
    triad_vals = [proportions[c] for c in TRIAD_CLASSES]

    values = np.array(behavioral + triad_vals, dtype=float)

    return TeamFeatures(
        csv_path=csv_path,
        team_name=sm.team_name,
        question_label=question_label or sm.question_label,
        values=values,
        n_students=n,
        non_submitter_count=non_submitter_count,
    )


def _reciprocity(A: np.ndarray) -> float:
    """Pearson correlation of A[i,j] vs A[j,i] over all valid symmetric pairs."""
    n = A.shape[0]
    fwd, rev = [], []
    for i in range(n):
        for j in range(i + 1, n):
            v_ij, v_ji = A[i, j], A[j, i]
            if not (np.isnan(v_ij) or np.isnan(v_ji)):
                fwd.append(v_ij)
                rev.append(v_ji)
    if len(fwd) < 2:
        return 0.0
    corr = np.corrcoef(fwd, rev)[0, 1]
    return float(corr) if not np.isnan(corr) else 0.0


def _gini(values: np.ndarray) -> float:
    """Gini coefficient over non-NaN values in [0, 1]."""
    v = values[~np.isnan(values)]
    if v.size == 0 or v.sum() == 0:
        return 0.0
    v = np.sort(v)
    n = v.size
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum() - (n + 1) * v.sum()) / (n * v.sum()))


def _rater_variance(A: np.ndarray) -> tuple[float, float]:
    """Mean and std of per-rater score standard deviations."""
    stds: list[float] = []
    for row in A:
        valid = row[~np.isnan(row)]
        if valid.size >= 2:
            stds.append(float(np.std(valid)))
    if not stds:
        return 0.0, 0.0
    return float(np.mean(stds)), float(np.std(stds)) if len(stds) >= 2 else 0.0


def _asymmetry(A: np.ndarray) -> float:
    """Normalized Frobenius asymmetry: ||A − Aᵀ||_F / (||A + Aᵀ||_F + ε)."""
    valid = ~np.isnan(A) & ~np.isnan(A.T)
    if not valid.any():
        return 0.0
    diff = np.where(valid, A - A.T, 0.0)
    total = np.where(valid, A + A.T, 0.0)
    denom = float(np.sqrt((total ** 2).sum())) + 1e-9
    return float(np.sqrt((diff ** 2).sum()) / denom)


def _graph_metrics(A: np.ndarray, n: int) -> tuple[float, float]:
    """Weighted directed clustering coefficient and degree assortativity."""
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for i in range(n):
        for j in range(n):
            if i != j and not np.isnan(A[i, j]):
                G.add_edge(i, j, weight=float(A[i, j]))

    clust_values = list(nx.clustering(G, weight="weight").values())
    clustering = float(np.mean(clust_values)) if clust_values else 0.0

    try:
        assort = nx.degree_assortativity_coefficient(G)
        assortativity = float(assort) if not np.isnan(assort) else 0.0
    except Exception:
        assortativity = 0.0

    return clustering, assortativity
