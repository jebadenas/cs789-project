"""Attack transforms on a ScoreMatrix (Phase 4, attacks #1–4).

Each transform is a pure ``ScoreMatrix → ScoreMatrix``: it copies the
matrix, perturbs it, and leaves metadata untouched (the runner tracks
which attack was applied).

Conventions, from docs/attacks/attack-vectors-spec.md:

- ``matrix[i][j]`` = score giver *j* gave recipient *i*; diagonal is the
  self-score (NaN in synthetic data, excluded by every model).
- Non-submitter columns are entirely NaN and are **left untouched** by
  every transform (they are not raters).
- Freed budget is redistributed **proportionally** to the rater's existing
  allocation; every modified column conserves its own pre-attack nansum
  (convention-agnostic — see spec Open Q1 resolution).
"""

from __future__ import annotations

import numpy as np

from src.parsing.schemas import ScoreMatrix


def _submitter_cols(matrix: np.ndarray) -> list[int]:
    """Column indices that are raters (not entirely NaN)."""
    return [j for j in range(matrix.shape[1])
            if not np.all(np.isnan(matrix[:, j]))]


def _with_matrix(sm: ScoreMatrix, matrix: np.ndarray) -> ScoreMatrix:
    """Clone ``sm`` with a replaced matrix, metadata preserved."""
    return sm.model_copy(update={"matrix": matrix})


def _redistribute(
    col: np.ndarray,
    j: int,
    drain: list[int],
    gain: list[int],
) -> None:
    """Move all mass on ``drain`` recipients onto ``gain``, in place.

    Redistribution is proportional to ``gain``'s current values; if those
    are all zero it falls back to an equal split.  The self entry (i == j)
    is never a target.  Column sum is conserved.
    """
    freed = float(np.nansum(col[drain])) if drain else 0.0
    for i in drain:
        col[i] = 0.0
    if not gain or freed <= 0:
        return
    weights = np.array([col[i] for i in gain], dtype=float)
    total = weights.sum()
    if total <= 0:
        weights = np.ones(len(gain))
        total = weights.sum()
    for i, w in zip(gain, weights):
        col[i] += freed * w / total


def uniform_inflation(sm: ScoreMatrix) -> ScoreMatrix:
    """#1 Pervasive collusion — every rater scores every recipient equally.

    Each rater spreads their full budget evenly across the recipients they
    rate (off-diagonal). Baseline IWF collapses to a single value (= the
    per-recipient share); the peer-assessment signal is destroyed.
    """
    m = sm.matrix.copy()
    n = m.shape[0]
    for j in _submitter_cols(m):
        recips = [i for i in range(n) if i != j]
        budget = float(np.nansum(m[:, j]))
        share = budget / len(recips)
        col = np.full(n, np.nan)
        for i in recips:
            col[i] = share
        m[:, j] = col
    return _with_matrix(sm, m)


def zero_self(
    sm: ScoreMatrix,
    colluders: list[int] | None = None,
    *,
    full: bool = True,
    self_share: float | None = None,
) -> ScoreMatrix:
    """#2 Small-circle / zero-self collusion (full or partial 2-of-N).

    The IWF-specific exploit (proposal §3.4): a colluder awards self 0.
    Self-scores are discarded but the IWF denominator stays N−1, so the
    self-allocation is **injected as surplus** onto teammates — a grade
    uplift with no contribution increase. This is *not* budget-conserving
    by design; that injection is the attack.

    Each colluder's would-be self share is taken as ``self_share`` of the
    budget they distribute among N targets (default = an equal 1/N split,
    i.e. scale the off-diagonal column up by N/(N−1)). The surplus lands
    proportionally on existing allocations (the proportional-redistribution
    decision). ``full`` = the whole team colludes; otherwise the first two
    submitter columns (or an explicit ``colluders`` list) form the circle.
    This is also the implementation home for reciprocal **log-rolling**
    (Song & Gehringer classify it as small-circle collusion).
    """
    m = sm.matrix.copy()
    n = m.shape[0]
    subs = _submitter_cols(m)
    if colluders is None:
        colluders = subs if full else subs[:2]
    colluders = [j for j in colluders if j in subs]
    if len(colluders) < 2:
        raise ValueError("zero_self needs ≥ 2 submitting colluders")

    # Default: rater would have split equally over all N (incl. self);
    # freeing that 1/N self share scales the N−1 off-diagonal entries by
    # N/(N−1).
    factor = (
        n / (n - 1) if self_share is None else 1.0 / (1.0 - self_share)
    )
    for j in colluders:
        m[:, j] *= factor
    return _with_matrix(sm, m)


def targeted_downvote(
    sm: ScoreMatrix,
    victim: int | None = None,
) -> ScoreMatrix:
    """#3 Status-based exclusion — one member zeroed by everyone else.

    Every other rater gives the victim 0 and redistributes that share
    proportionally among the remaining non-victim recipients. The victim's
    own column (their outgoing ratings) stays honest/unmodified. Baseline
    IWF of the victim → 0.
    """
    m = sm.matrix.copy()
    n = m.shape[0]
    subs = _submitter_cols(m)
    if victim is None:
        victim = subs[0]

    for j in subs:
        if j == victim:
            continue
        col = m[:, j].copy()
        others = [i for i in range(n) if i != j and i != victim]
        _redistribute(col, j, drain=[victim], gain=others)
        m[:, j] = col
    return _with_matrix(sm, m)


def single_outlier(
    sm: ScoreMatrix,
    outlier: int | None = None,
    *,
    rng: np.random.Generator | None = None,
) -> ScoreMatrix:
    """#4 Single unreliable rater — one column randomly permuted.

    One rater's allocation is replaced by a random permutation of the same
    budget across the recipients they rate. Budget is conserved exactly
    (it is a permutation). ``rng`` makes Monte-Carlo runs reproducible.
    """
    m = sm.matrix.copy()
    n = m.shape[0]
    subs = _submitter_cols(m)
    rng = rng or np.random.default_rng()
    if outlier is None:
        outlier = int(rng.choice(subs))

    j = outlier
    recips = [i for i in range(n) if i != j]
    vals = np.array([m[i, j] for i in recips], dtype=float)
    perm = rng.permutation(vals)
    col = np.full(n, np.nan)
    for i, v in zip(recips, perm):
        col[i] = v
    m[:, j] = col
    return _with_matrix(sm, m)
