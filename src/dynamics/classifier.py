"""Synthesised archetypes and Mahalanobis distance classifier for team dynamics.

Builds hand-crafted prototype score matrices for each of the 5 team-dynamic
labels (Cohesive, Collusive, Free-rider, Dominant, Conflict), extracts their
25-dim feature vectors, then classifies real teams by Mahalanobis distance.

Pipeline usage
--------------
1. Build raw archetype vectors:  labels, arch_raw = build_synthesised_archetypes()
2. Standardise with the data scaler:  arch_scaled = scaler.transform(arch_raw)
3. Fit precision matrix on all data:  precision = fit_precision(X_scaled)
4. Classify teams:  results = classify_teams(X_scaled, arch_scaled, precision)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2, pearsonr
from sklearn.covariance import LedoitWolf

from src.dynamics.features import FEATURE_NAMES, TeamFeatures, extract_features
from src.parsing.schemas import ScoreMatrix, StudentInfo


ARCHETYPE_LABELS: list[str] = ["Cohesive", "Collusive", "Free-rider", "Dominant", "Conflict"]


@dataclass(frozen=True)
class ClassificationResult:
    """Per-team classification output."""

    label: str
    distances: np.ndarray   # (5,) Mahalanobis distance to each archetype
    weights: np.ndarray     # (5,) softmax-normalised inverse-distance mixture


# ---------------------------------------------------------------------------
# Prototype matrices  (n=5, budget=60 per column — each column is one student's
# point allocation;  matrix[i][j] = score giver j gave to recipient i)
# ---------------------------------------------------------------------------

def _cohesive_matrix() -> np.ndarray:
    """Near-uniform reciprocal scoring — everyone rates fairly.

    Column sums all = 60:
      col0: 12+11+13+12+12 = 60
      col1: 11+12+11+13+13 = 60
      col2: 13+11+12+11+13 = 60
      col3: 12+13+11+12+12 = 60
      col4: 12+13+13+12+10 = 60
    """
    return np.array([
        [12, 11, 13, 12, 12],
        [11, 12, 11, 13, 12],
        [13, 11, 12, 11, 13],
        [12, 13, 11, 12, 12],
        [12, 13, 13, 12, 11],
    ], dtype=float)


def _collusive_matrix() -> np.ndarray:
    """Paired mutual inflation — students inflate their 'buddy' reciprocally.

    Column sums all = 60:
      col0: 6+18+14+12+10 = 60
      col1: 18+6+10+14+12 = 60
      col2: 14+10+6+18+12 = 60
      col3: 12+14+18+6+10 = 60
      col4: 10+12+12+10+16 = 60
    """
    return np.array([
        [ 6, 18, 14, 12, 10],
        [18,  6, 10, 14, 12],
        [14, 10,  6, 18, 12],
        [12, 14, 18,  6, 10],
        [10, 12, 12, 10, 16],
    ], dtype=float)


def _free_rider_matrix() -> np.ndarray:
    """Student 4 (free-rider) receives very low scores from all peers.

    Active students give 15 to active peers and only 2 to the free-rider.
    Free-rider hoards points (self-score 52) and gives only 2 to each peer.
    This creates a highly unequal in-degree distribution → high Gini.

    Column sums all = 60:
      col0–col3: 13+15+15+15+2 = 60
      col4: 2+2+2+2+52 = 60
    """
    return np.array([
        [13, 15, 15, 15,  2],
        [15, 13, 15, 15,  2],
        [15, 15, 13, 15,  2],
        [15, 15, 15, 13,  2],
        [ 2,  2,  2,  2, 52],
    ], dtype=float)


def _dominant_matrix() -> np.ndarray:
    """Student 0 is the dominant contributor — receives disproportionately high scores.

    Student 0 gives equal scores; all others rate student 0 very highly.

    Column sums all = 60:
      col0: 12+12+12+12+12 = 60
      col1: 28+8+8+8+8 = 60
      col2: 27+8+8+9+8 = 60
      col3: 26+9+9+8+8 = 60
      col4: 27+8+8+9+8 = 60
    """
    return np.array([
        [12, 28, 27, 26, 27],
        [12,  8,  8,  9,  8],
        [12,  8,  8,  9,  8],
        [12,  8,  9,  8,  9],
        [12,  8,  8,  8,  8],
    ], dtype=float)


def _conflict_matrix() -> np.ndarray:
    """Alternating directional scoring — A rates B high but B rates A low.

    Students 0,2 inflate 0,2 and penalise 1,3; students 1,3 do the opposite.

    Column sums all = 60:
      col0: 12+5+20+5+18 = 60
      col1: 20+12+5+20+3 = 60
      col2: 5+20+12+5+18 = 60
      col3: 20+5+20+12+3 = 60
      col4: 5+20+5+20+10 = 60
    """
    return np.array([
        [12, 20,  5, 20,  5],
        [ 5, 12, 20,  5, 20],
        [20,  5, 12, 20,  5],
        [ 5, 20,  5, 12, 20],
        [18,  3, 18,  3, 10],
    ], dtype=float)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_synthesised_archetypes() -> tuple[list[str], np.ndarray]:
    """Return (labels, raw_feature_matrix) for the 5 synthesised archetypes.

    Returns:
        labels: ARCHETYPE_LABELS (length 5)
        archetypes: (5, 25) raw feature vectors — standardise with the same
                    scaler fitted on the full dataset before comparing.
    """
    prototypes = [
        _cohesive_matrix(),
        _collusive_matrix(),
        _free_rider_matrix(),
        _dominant_matrix(),
        _conflict_matrix(),
    ]
    vectors = []
    for mat in prototypes:
        n = mat.shape[0]
        sm = _make_sm(mat, n)
        tf = extract_features(sm)
        vectors.append(tf.values)
    return ARCHETYPE_LABELS, np.array(vectors)


def fit_precision(X: np.ndarray) -> np.ndarray:
    """Estimate regularised precision matrix via Ledoit-Wolf shrinkage.

    Ledoit-Wolf handles the p ≈ n regime (136 teams, 25 features) by
    shrinking the sample covariance towards a scaled identity matrix.

    Args:
        X: (n_samples, n_features) standardised feature matrix.

    Returns:
        precision: (n_features, n_features) precision matrix (inverse covariance).
    """
    return LedoitWolf().fit(X).precision_


def atypicality_scores(
    X: np.ndarray,
    precision: np.ndarray,
    centroid: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Mahalanobis distance of every team from the data centroid.

    This is the primary RQ3 measure: a single continuous "how unusual is this
    team vs the crowd" score, replacing the 5-prototype nearest-label scheme.

    Args:
        X: (n_teams, n_features) standardised feature matrix.
        precision: (n_features, n_features) Ledoit-Wolf precision matrix.
        centroid: optional (n_features,) reference point. Defaults to the
            column mean of X (the centre of the blob).

    Returns:
        dist:  (n_teams,) Mahalanobis distance from the centroid.
        dist2: (n_teams,) squared distance — distributed ~ chi2(n_features)
               under the null that the team is a typical draw.
    """
    if centroid is None:
        centroid = X.mean(axis=0)

    L = np.linalg.cholesky(precision)  # precision = L @ L.T
    dist = np.array([_mahalanobis(row, centroid, L) for row in X])
    return dist, dist ** 2


def chi_square_flag(
    dist2: np.ndarray,
    df: int,
    alpha: float = 0.05,
) -> tuple[np.ndarray, float]:
    """Secondary binary Typical/Anomalous flag from a chi-square cutoff.

    Squared Mahalanobis distance from the centroid follows chi2(df) when the
    team is a typical draw, so the (1-alpha) quantile is a principled "too far"
    line — no hand-picked threshold.

    Args:
        dist2: (n_teams,) squared Mahalanobis distances.
        df: degrees of freedom = number of features used.
        alpha: tail mass treated as anomalous (0.05 -> 95th percentile cut).

    Returns:
        labels: (n_teams,) array of "Typical" / "Anomalous".
        cutoff: the chi2 critical value used.
    """
    cutoff = float(chi2.ppf(1.0 - alpha, df))
    labels = np.where(dist2 > cutoff, "Anomalous", "Typical")
    return labels, cutoff


def degenerate_cause(tf: TeamFeatures) -> str:
    """Why a team carries no usable signal: none / non_submitter / flat / both.

    Two independent no-signal causes, kept distinguishable for the writeup:
      - non_submitter: a teammate left their column blank (partial data).
      - flat: zero rater variation — everyone split points evenly, so the
        binarised graph has no above-average edges (structureless).

    Both look "perfectly cohesive" but are actually blank; reported separately
    so the data-quality story can split participation vs. engagement failures.
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


def atypicality_delta_correlation(
    scores: np.ndarray,
    deltas: np.ndarray,
) -> dict[str, float]:
    """Pearson correlation between atypicality and cross-model Δ (the RQ3 test).

    Returns r, two-sided p-value, and n. Caller runs this twice: once on the
    full set and once on the degenerate-excluded subset.
    """
    if scores.size < 3:
        return {"r": float("nan"), "p": float("nan"), "n": int(scores.size)}
    r, p = pearsonr(scores, deltas)
    return {"r": float(r), "p": float(p), "n": int(scores.size)}


def classify_teams(
    X: np.ndarray,
    archetypes: np.ndarray,
    precision: np.ndarray,
) -> list[ClassificationResult]:
    """Classify each row of X by Mahalanobis distance to the archetypes.

    Args:
        X: (n_teams, n_features) standardised feature matrix.
        archetypes: (n_archetypes, n_features) standardised archetype vectors.
        precision: (n_features, n_features) precision matrix.

    Returns:
        List of ClassificationResult (one per team row in X).
    """
    L = np.linalg.cholesky(precision)  # precision = L @ L.T

    results: list[ClassificationResult] = []
    for row in X:
        dists = np.array([_mahalanobis(row, arch, L) for arch in archetypes])
        label_idx = int(np.argmin(dists))

        neg_d = -dists
        neg_d -= neg_d.max()
        exp_d = np.exp(neg_d)
        weights = exp_d / exp_d.sum()

        results.append(ClassificationResult(
            label=ARCHETYPE_LABELS[label_idx],
            distances=dists,
            weights=weights,
        ))
    return results


def delta_by_label(
    labels: list[str],
    delta_vals: np.ndarray,
) -> dict[str, dict]:
    """Compute Delta statistics grouped by team-dynamic label.

    Args:
        labels: per-team classification labels (length n_teams).
        delta_vals: per-team Delta values (length n_teams).

    Returns:
        Dict mapping label → {mean, std, median, count, max}.
    """
    stats: dict[str, dict] = {}
    for label in ARCHETYPE_LABELS:
        mask = np.array([l == label for l in labels])
        vals = delta_vals[mask]
        stats[label] = {
            "count": int(mask.sum()),
            "mean": float(np.mean(vals)) if vals.size > 0 else float("nan"),
            "std": float(np.std(vals)) if vals.size > 0 else float("nan"),
            "median": float(np.median(vals)) if vals.size > 0 else float("nan"),
            "max": float(np.max(vals)) if vals.size > 0 else float("nan"),
        }
    return stats


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_sm(matrix: np.ndarray, n: int) -> ScoreMatrix:
    return ScoreMatrix(
        matrix=matrix,
        team_name="prototype",
        question_label="Q1",
        year="2024",
        semester="S1",
        session_number=1,
        students=[
            StudentInfo(name=f"S{i}", email=f"s{i}@test.ac.nz", index=i)
            for i in range(n)
        ],
        excluded_students=[],
    )


def _mahalanobis(u: np.ndarray, v: np.ndarray, L: np.ndarray) -> float:
    """Mahalanobis distance using Cholesky factor L of the precision matrix.

    precision = L @ L.T  →  d^2 = (u-v)^T precision (u-v) = ||L.T (u-v)||^2
    """
    y = L.T @ (u - v)
    return float(np.sqrt(np.dot(y, y)))
