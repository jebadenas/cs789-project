"""Scale-free rank representation — the single source of truth for the transform.

Everything downstream (`nulls`, `gates`, `contested`, `crossq`) imports from here.

Matrix convention (handoff-8, opposite orientation to `src/dynamics/features.py`):
`ScoreMatrix.matrix[i][j]` = score that **giver j** assigned to **recipient i**,
so **column j is rater j's ratings**. We work directly on `matrix` with the
diagonal (self-scores) set to NaN and read columns as raters. Non-submitters are
all-NaN columns.

Why ranks: WebPA and the iterative models divide by each rater's total, so Lane A
already corrects for rater leniency/severity/range. Raw-score features do not.
Transforming each rater's ratings to within-rater normalised ranks divides those
rater effects out, leaving only *which recipient a rater placed above which* —
the agreement signal.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

from src.parsing.schemas import ScoreMatrix


def prepare_matrix(sm: ScoreMatrix) -> np.ndarray:
    """Return a float copy of the score matrix with the diagonal set to NaN.

    Column `j` is rater `j`'s ratings of every recipient; the diagonal (a
    rater's self-score) is removed. All rank statistics read columns as raters.
    """
    mat = np.asarray(sm.matrix, dtype=float).copy()
    np.fill_diagonal(mat, np.nan)
    return mat


def qualifying_raters(mat: np.ndarray) -> np.ndarray:
    """Boolean mask over columns: which raters express an ordering.

    Column `j` qualifies iff it has **≥2 finite entries** AND **non-zero standard
    deviation** over those entries. A rater who gave everyone the same number
    expresses no ordering and is excluded from every statistic here.
    """
    m = mat.shape[1]
    mask = np.zeros(m, dtype=bool)
    for j in range(m):
        col = mat[:, j]
        finite = col[np.isfinite(col)]
        if finite.size >= 2 and np.std(finite) > 0:
            mask[j] = True
    return mask


def normalised_rank_matrix(mat: np.ndarray) -> np.ndarray:
    """(n_recipient × n_rater) array of within-rater normalised ranks.

    For a qualifying rater who rated `k` recipients, their finite ratings become
    ``rankdata(ratings) / (k + 1)``. Dividing by ``k + 1`` keeps raters who rated
    different numbers of people on a comparable 0–1 scale. Entries are NaN where a
    rater did not rate a recipient or the rater does not qualify.
    """
    n, m = mat.shape
    R = np.full((n, m), np.nan)
    qual = qualifying_raters(mat)
    for j in range(m):
        if not qual[j]:
            continue
        col = mat[:, j]
        finite_idx = np.where(np.isfinite(col))[0]
        k = finite_idx.size
        ranks = rankdata(col[finite_idx]) / (k + 1)
        R[finite_idx, j] = ranks
    return R


def consensus_vector(mat: np.ndarray) -> np.ndarray:
    """Per-recipient mean normalised rank across all qualifying raters who rated them.

    Length `n`; NaN for a recipient no qualifying rater rated.
    """
    R = normalised_rank_matrix(mat)
    n = R.shape[0]
    out = np.full(n, np.nan)
    for i in range(n):
        row = R[i, :]
        finite = row[np.isfinite(row)]
        if finite.size:
            out[i] = float(finite.mean())
    return out


def tau_b(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall τ-b (tie-corrected) computed directly.

    These normalised-rank vectors tie constantly, so τ-b (not τ-a) is required.
    Implemented directly rather than via `scipy.stats.kendalltau` because it is
    called millions of times inside the permutation harness and is the dominant
    cost. Verified against ``scipy.stats.kendalltau(variant='b')`` in the tests.

    Returns NaN if the denominator is zero (one vector is entirely tied).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    signs_x = np.sign(x[:, None] - x[None, :])
    signs_y = np.sign(y[:, None] - y[None, :])
    iu = np.triu_indices(x.size, k=1)
    sx = signs_x[iu]
    sy = signs_y[iu]
    n0 = sx.size
    n1 = int(np.sum(sx == 0))  # tied pairs in x
    n2 = int(np.sum(sy == 0))  # tied pairs in y
    denom = np.sqrt((n0 - n1) * (n0 - n2))
    if denom == 0:
        return float("nan")
    return float(np.sum(sx * sy) / denom)


def pairwise_taus(R: np.ndarray, min_common: int = 3) -> list[float]:
    """τ-b for every rater pair over the recipients they *both* rated.

    `R` is a normalised-rank matrix (recipients × raters). A pair contributes only
    if it shares **≥ min_common** commonly-rated recipients. Non-qualifying raters
    are already all-NaN columns and drop out automatically.
    """
    n, m = R.shape
    taus: list[float] = []
    for a in range(m):
        for b in range(a + 1, m):
            ca, cb = R[:, a], R[:, b]
            common = np.isfinite(ca) & np.isfinite(cb)
            if int(common.sum()) < min_common:
                continue
            t = tau_b(ca[common], cb[common])
            if np.isfinite(t):
                taus.append(t)
    return taus


def mean_pairwise_tau(mat: np.ndarray, min_common: int = 3) -> float:
    """Team-level agreement: mean τ-b over all computable rater pairs.

    NaN if no rater pair shares ``min_common`` recipients (the matrix is
    *incomparable* — it passes the rater count but yields no comparison).
    """
    taus = pairwise_taus(normalised_rank_matrix(mat), min_common=min_common)
    return float(np.mean(taus)) if taus else float("nan")
