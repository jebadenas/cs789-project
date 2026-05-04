"""Archetypal Analysis for team-dynamics discovery.

Implements AA via the Frank-Wolfe / conditional-gradient algorithm following
Cutler & Breiman (1994).  Each archetype is a convex combination of data points
(the extreme exemplars); each data point is approximated as a convex combination
of archetypes.

Sweeps k = 2..8 archetypes, selects best k via RSS elbow, and estimates archetype
stability via bootstrap subsampling (Mørup & Hansen 2012).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


@dataclass
class ArchetypeResult:
    """AA fit for a specific k."""

    k: int
    archetypes: np.ndarray    # (k, n_features) in the input space
    weights: np.ndarray       # (n_samples, k) — convex combination coefficients
    rss: float
    bootstrap_stability: float = 0.0


def fit_aa(
    X: np.ndarray,
    k: int,
    max_iter: int = 400,
    n_restarts: int = 5,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit Archetypal Analysis with Frank-Wolfe updates and multiple restarts.

    Args:
        X: (n_samples, n_features) standardized feature matrix.
        k: number of archetypes.
        max_iter: Frank-Wolfe iterations per restart.
        n_restarts: number of random initialisations; best RSS is returned.
        random_state: base seed.

    Returns:
        archetypes: (k, n_features)
        weights: (n_samples, k)
        rss: residual sum of squares
    """
    best_Z: np.ndarray | None = None
    best_S: np.ndarray | None = None
    best_rss = np.inf

    for restart in range(n_restarts):
        Z, S, rss = _fit_aa_single(X, k, max_iter, random_state=random_state + restart * 1000)
        if rss < best_rss:
            best_rss = rss
            best_Z = Z
            best_S = S

    return best_Z, best_S, best_rss  # type: ignore[return-value]


def sweep_archetypes(
    X: np.ndarray,
    k_range: range = range(2, 9),
    n_bootstrap: int = 50,
    max_iter: int = 400,
    random_state: int = 42,
) -> list[ArchetypeResult]:
    """Sweep k archetypes, compute RSS elbow and bootstrap stability.

    Args:
        X: (n_samples, n_features) standardized input.
        k_range: range of k values to evaluate.
        n_bootstrap: bootstrap iterations for stability estimate.
        max_iter: Frank-Wolfe iterations per fit.
        random_state: base seed.

    Returns:
        List of ArchetypeResult sorted by k.
    """
    results: list[ArchetypeResult] = []

    for k in k_range:
        print(f"  AA k={k}...", flush=True)
        Z, S, rss = fit_aa(X, k, max_iter=max_iter, random_state=random_state)
        stability = _bootstrap_stability(X, k, Z, n_bootstrap=n_bootstrap, max_iter=max_iter, random_state=random_state)
        results.append(ArchetypeResult(k=k, archetypes=Z, weights=S, rss=rss, bootstrap_stability=stability))

    return results


def find_elbow(results: list[ArchetypeResult]) -> int:
    """Return k at the RSS elbow (maximum perpendicular deviation from chord)."""
    if len(results) < 3:
        return results[0].k
    rss = np.array([r.rss for r in results])
    rss_norm = (rss - rss.min()) / (rss.max() - rss.min() + 1e-9)
    k_norm = np.linspace(0.0, 1.0, len(rss_norm))
    chord = np.array([k_norm[-1] - k_norm[0], rss_norm[-1] - rss_norm[0]])
    chord /= np.linalg.norm(chord) + 1e-9
    perp = np.array([-chord[1], chord[0]])
    vecs = np.column_stack([k_norm - k_norm[0], rss_norm - rss_norm[0]])
    distances = np.abs(vecs @ perp)
    return results[int(np.argmax(distances))].k


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fit_aa_single(
    X: np.ndarray,
    k: int,
    max_iter: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Single-restart AA via Frank-Wolfe.

    X: (n, p)
    C: (n, k) column-stochastic — archetypes as convex combos of data points
    S: (n, k) row-stochastic — data as convex combos of archetypes
    Z = C.T @ X: (k, p) archetypes

    Loss: ||X - S @ Z||_F^2
    """
    rng = np.random.default_rng(random_state)
    n, p = X.shape

    # Initialise C: one data point per archetype
    init_idx = rng.choice(n, k, replace=False)
    C = np.zeros((n, k))
    for j, idx in enumerate(init_idx):
        C[idx, j] = 1.0

    # Initialise S: uniform mixture
    S = np.ones((n, k)) / k

    for t in range(max_iter):
        step = 2.0 / (t + 2)
        Z = C.T @ X  # (k, p)

        # Update S — gradient: dL/dS = -2 * (X - S@Z) @ Z.T  shape (n, k)
        residuals = X - S @ Z
        grad_S = -2.0 * residuals @ Z.T
        S = _fw_rows(S, grad_S, step)

        Z = C.T @ X

        # Update C — gradient: dL/dZ = -2 * S.T @ (X - S@Z)  shape (k, p)
        #            dL/dC = X @ dL_dZ.T  shape (n, k)
        dL_dZ = -2.0 * S.T @ (X - S @ Z)
        grad_C = X @ dL_dZ.T
        C = _fw_cols(C, grad_C, step)

    Z = C.T @ X
    rss = float(np.sum((X - S @ Z) ** 2))
    return Z, S, rss


def _fw_rows(M: np.ndarray, grad: np.ndarray, step: float) -> np.ndarray:
    """Frank-Wolfe update for row-stochastic matrix (each row sums to 1)."""
    n, k = M.shape
    j_star = np.argmin(grad, axis=1)  # (n,)
    e = np.zeros((n, k))
    e[np.arange(n), j_star] = 1.0
    return (1.0 - step) * M + step * e


def _fw_cols(M: np.ndarray, grad: np.ndarray, step: float) -> np.ndarray:
    """Frank-Wolfe update for column-stochastic matrix (each column sums to 1)."""
    n, k = M.shape
    i_star = np.argmin(grad, axis=0)  # (k,)
    e = np.zeros((n, k))
    e[i_star, np.arange(k)] = 1.0
    return (1.0 - step) * M + step * e


def _bootstrap_stability(
    X: np.ndarray,
    k: int,
    Z_full: np.ndarray,
    n_bootstrap: int,
    max_iter: int,
    random_state: int,
) -> float:
    """Estimate archetype stability via bootstrap subsampling.

    Fits AA on 80% subsamples, matches bootstrap archetypes to full-data
    archetypes via linear assignment, and returns 1 - (mean distance / data scale).
    """
    rng = np.random.default_rng(random_state + 99999)
    n = X.shape[0]
    n_sub = max(k + 1, int(n * 0.8))

    scale = float(np.mean(cdist(X, X))) + 1e-9
    distances: list[float] = []

    for _ in range(n_bootstrap):
        idx = rng.choice(n, n_sub, replace=False)
        try:
            Z_sub, _, _ = _fit_aa_single(X[idx], k, max_iter=max_iter // 2, random_state=int(rng.integers(1_000_000)))
        except Exception:
            continue

        D = cdist(Z_sub, Z_full)
        row_ind, col_ind = linear_sum_assignment(D)
        distances.append(float(D[row_ind, col_ind].mean()))

    if not distances:
        return 0.0

    return float(np.clip(1.0 - np.mean(distances) / scale, 0.0, 1.0))
