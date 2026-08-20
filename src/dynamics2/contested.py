"""The two (three) sub-tests that run only on `Contested` matrices / teams.

Once Gate B has said the raters do not agree on the ordering, the question
becomes *what shape* the disagreement has:

- **4a Faction test** — do the raters split into two internally-consistent camps?
  A winning partition of size 1 is a *lone deviant rater*, not a faction, and is
  reported as its own category. That distinction is load-bearing: it is what turns
  an apparent positive into a correct negative.
- **4b Concentration test** — is the disagreement about *one* member (they alone
  are disputed) or spread across everyone?
- **4c Pooled faction test** — the per-matrix faction test is underpowered (most
  Contested matrices have <4 qualifying raters); pooling a team's three questions
  roughly doubles the testable set.

Every threshold is the permutation null of `nulls`, with the full candidate
search (all 2-partitions) repeated inside the null (search-inside-null rule).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from src.dynamics2 import ranks
from src.dynamics2.dataio import MatrixRecord
from src.dynamics2.nulls import (
    DEFAULT_N_PERM, permutation_p, permute_matrix, seed_from_key,
)
from src.dynamics2.pooled import pooled_tau_matrix

ALPHA = 0.05
MIN_FACTION_RATERS = 4  # below this the 2-partition search is not meaningful


# --------------------------------------------------------------------------- #
# Partition enumeration and scoring (shared by per-matrix and pooled tests)
# --------------------------------------------------------------------------- #

def enumerate_partitions(m: int):
    """All 2-partitions of ``m`` items, one of each complementary pair.

    ``|S|`` runs 1..m//2. For the even split (``|S| == m/2``) each partition and
    its complement have equal size, so we keep only those containing item 0 to
    avoid emitting both halves of the same partition twice.
    """
    items = list(range(m))
    for s in range(1, m // 2 + 1):
        for S in combinations(items, s):
            if 2 * s == m and 0 not in S:
                continue
            yield set(S)


def best_partition(tau_matrix: np.ndarray) -> tuple[float, int]:
    """Max split-quality ``Q`` over all 2-partitions of a rater×rater τ-b matrix.

    ``Q = mean(τ within groups) − mean(τ between groups)``. A partition is scored
    only if it has ≥1 within-group pair *and* ≥1 between-group pair with a finite
    τ. Returns ``(max_Q, faction_size)`` where ``faction_size`` is the size of the
    smaller side of the winning partition; ``(nan, 0)`` if nothing is scorable.

    NB: this is deliberately called **split_quality**, not *modularity*.
    Newman–Girvan modularity is defined against a degree-preserving configuration
    null; this quantity is a within-minus-between τ contrast evaluated against a
    rating-permutation null — a different construction, null and quantity (audit
    2026-08-09, Task 6).
    """
    m = tau_matrix.shape[0]
    best_q = -np.inf
    best_size = 0
    for S in enumerate_partitions(m):
        within: list[float] = []
        between: list[float] = []
        for a in range(m):
            for b in range(a + 1, m):
                t = tau_matrix[a, b]
                if not np.isfinite(t):
                    continue
                if (a in S) == (b in S):
                    within.append(t)
                else:
                    between.append(t)
        if within and between:
            q = float(np.mean(within) - np.mean(between))
            if q > best_q:
                best_q = q
                best_size = min(len(S), m - len(S))
    if best_q == -np.inf:
        return float("nan"), 0
    return best_q, best_size


def _rater_tau_matrix(mat: np.ndarray, min_common: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """τ-b matrix over qualifying raters only. Returns (T, qualifying_col_indices)."""
    R = ranks.normalised_rank_matrix(mat)
    qual_idx = np.where(ranks.qualifying_raters(mat))[0]
    q = qual_idx.size
    T = np.full((q, q), np.nan)
    for ai in range(q):
        for bi in range(ai + 1, q):
            ca, cb = R[:, qual_idx[ai]], R[:, qual_idx[bi]]
            common = np.isfinite(ca) & np.isfinite(cb)
            if int(common.sum()) < min_common:
                continue
            t = ranks.tau_b(ca[common], cb[common])
            T[ai, bi] = T[bi, ai] = t
    return T, qual_idx


def _faction_max_q(mat: np.ndarray) -> float:
    """Scalar max-Q for the null callable (full enumeration repeated per draw)."""
    T, _ = _rater_tau_matrix(mat)
    return best_partition(T)[0]


# --------------------------------------------------------------------------- #
# 4a — per-matrix faction test
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FactionRow:
    n_raters: int
    faction_size: int
    split_quality: float
    p_value: float
    category: str


def faction_test(mat: np.ndarray, key: tuple[str, str, str],
                 n_perm: int = DEFAULT_N_PERM, alpha: float = ALPHA) -> FactionRow:
    """4a. Two-camp structure among a Contested matrix's raters."""
    n_raters = int(ranks.qualifying_raters(mat).sum())
    if n_raters < MIN_FACTION_RATERS:
        return FactionRow(n_raters, 0, float("nan"), float("nan"), "too few raters")

    T, _ = _rater_tau_matrix(mat)
    max_q, size = best_partition(T)
    res = permutation_p(mat, _faction_max_q, key=(*key, "faction"),
                        n_perm=n_perm, larger_is_extreme=True)
    category = _faction_category(res.p_value, size, alpha)
    return FactionRow(n_raters, size, max_q, res.p_value, category)  # max_q = split_quality


def _faction_category(p: float, size: int, alpha: float) -> str:
    if not np.isfinite(p):
        return "unstructured"
    if p > alpha:
        return "unstructured"
    # significant structure:
    return "lone deviant" if size == 1 else "structured"


# --------------------------------------------------------------------------- #
# 4b — per-matrix concentration test
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ConcentrationRow:
    n_disputed_recipients: int
    gap: float
    p_value: float
    verdict: str


def _dispersion_gap(mat: np.ndarray, min_raters: int = 2, min_recipients: int = 3) -> float:
    """Gap between the most- and second-most-disputed recipient.

    Per recipient rated by ≥``min_raters`` qualifying raters, the SD of their
    normalised rank; ``gap = max − second_max`` over ≥``min_recipients`` such
    recipients (else NaN).
    """
    R = ranks.normalised_rank_matrix(mat)
    sds: list[float] = []
    for i in range(R.shape[0]):
        vals = R[i, :][np.isfinite(R[i, :])]
        if vals.size >= min_raters:
            sds.append(float(np.std(vals)))
    if len(sds) < min_recipients:
        return float("nan")
    ordered = np.sort(sds)[::-1]
    return float(ordered[0] - ordered[1])


def concentration_test(mat: np.ndarray, key: tuple[str, str, str],
                       n_perm: int = DEFAULT_N_PERM, alpha: float = ALPHA) -> ConcentrationRow:
    """4b. One disputed member vs diffuse disagreement."""
    R = ranks.normalised_rank_matrix(mat)
    n_disputed = int(sum(np.isfinite(R[i, :]).sum() >= 2 for i in range(R.shape[0])))
    res = permutation_p(mat, _dispersion_gap, key=(*key, "concentration"),
                        n_perm=n_perm, larger_is_extreme=True)
    if not np.isfinite(res.observed):
        return ConcentrationRow(n_disputed, float("nan"), float("nan"), "insufficient")
    verdict = ("Concentrated — one disputed member" if res.p_value <= alpha
               else "Spread — nobody agrees on anyone")
    return ConcentrationRow(n_disputed, res.observed, res.p_value, verdict)


# --------------------------------------------------------------------------- #
# 4c — pooled (team-level) faction test
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PooledRow:
    n_raters: int
    faction_size: int
    split_quality: float
    p_value: float
    category: str


def _pooled_max_q(items: list[tuple[list[str], np.ndarray]]) -> float:
    # ``pooled_tau_matrix`` is the shared pooling primitive (src/dynamics2/pooled.py);
    # the pooled cascade and this faction test read the same rater×rater τ-b.
    T, _ = pooled_tau_matrix(items)
    return best_partition(T)[0]


def pooled_faction_test(items: list[tuple[list[str], np.ndarray]],
                        key: tuple[str, str], n_perm: int = DEFAULT_N_PERM,
                        alpha: float = ALPHA) -> PooledRow:
    """4c. Pool a Contested team's questions; test for a genuine faction.

    Null permutes **within (rater, question)** — each question matrix's columns
    are shuffled independently — preserving the question structure. The full
    2-partition search is repeated inside the null.
    """
    T, raters = pooled_tau_matrix(items)
    m = len(raters)
    if m < MIN_FACTION_RATERS:
        return PooledRow(m, 0, float("nan"), float("nan"), "too few raters")

    max_q, size = best_partition(T)
    observed = max_q
    if not np.isfinite(observed):
        return PooledRow(m, size, float("nan"), float("nan"), "unstructured")

    rng = np.random.default_rng(seed_from_key(*key, "pooled"))
    count = 0
    valid = 0
    for _ in range(n_perm):
        perm_items = [(emails, permute_matrix(mat, rng)) for emails, mat in items]
        val = _pooled_max_q(perm_items)
        if not np.isfinite(val):
            continue
        valid += 1
        if val >= observed:
            count += 1
    p = (1 + count) / (1 + n_perm)
    category = _faction_category(p, size, alpha)
    return PooledRow(m, size, max_q, p, category)
