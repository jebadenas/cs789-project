"""Permutation harness — the methodological core.

Every threshold in the cascade is set by this null rather than by fiat.

**The null.** For one matrix, permute **each rater's own scores among exactly the
recipients they actually rated**. That preserves team size, which raters
submitted, who rated whom, and each rater's exact multiset of values (their
leniency, their spread, their ties). It destroys only *which recipient received
which score* — i.e. the agreement signal, and nothing else.

**Search-inside-null rule.** Any statistic computed via a **search over
candidates** (e.g. the faction test keeps the maximum over all 2-partitions) must
repeat that entire search inside the null, otherwise the max-over-candidates
inflates the statistic and the false-positive rate is wrong. This is enforced
structurally: the harness takes a callable mapping a matrix to a scalar and never
compares against a precomputed null. Whatever search the callable does on the
observed matrix, it does again on every permuted matrix.

**Determinism.** The RNG is seeded from a stable string key (identity of the
matrix plus the statistic name) via BLAKE2b, *not* from a global counter and
*not* from Python's ``hash()`` (which is salted per process and will not
reproduce across runs). Same key → same permutations → same p-value, regardless
of iteration order.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

import numpy as np

# Add-one p-value default; overridable via CLI. The exploratory numbers were
# produced at 100 — expect p-values to move slightly at 1000.
DEFAULT_N_PERM = 1000


def seed_from_key(*parts: object) -> int:
    """Stable 64-bit seed from a key, reproducible across processes and runs.

    Uses BLAKE2b, not ``hash()``: Python's built-in hash is salted per process
    (``PYTHONHASHSEED``) and would make results depend on the run.
    """
    key = "|".join(str(p) for p in parts)
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def permute_matrix(mat: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One null draw: shuffle each column's finite entries among their own slots.

    Column = rater. Shuffling within the finite positions permutes a rater's
    scores among exactly the recipients they rated, preserving their multiset of
    values and leaving NaN (non-rated / self / non-submitter) slots untouched.
    """
    out = mat.copy()
    n, m = out.shape
    for j in range(m):
        finite_idx = np.where(np.isfinite(out[:, j]))[0]
        if finite_idx.size >= 2:
            perm = rng.permutation(finite_idx.size)
            out[finite_idx, j] = out[finite_idx[perm], j]
    return out


@dataclass(frozen=True)
class NullResult:
    """Observed statistic, its permutation p-value, and bookkeeping."""

    observed: float
    p_value: float
    n_perm: int
    n_valid_null: int  # finite null draws actually compared


def permutation_p(
    mat: np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    key: tuple[object, ...],
    n_perm: int = DEFAULT_N_PERM,
    larger_is_extreme: bool = True,
) -> NullResult:
    """Add-one permutation p-value for ``stat_fn`` on ``mat``.

    ``p = (1 + #{null >= observed}) / (1 + n_perm)`` (add-one form: p is never
    exactly 0). Non-finite null draws are skipped in the count but the
    denominator stays ``n_perm`` so the test is conservative, never anti-
    conservative. If the observed statistic is non-finite, p is NaN.

    Determinism: the RNG is seeded from ``key`` (which must uniquely identify the
    matrix *and* the statistic). The callable is re-evaluated on every permuted
    matrix, so any internal search over candidates is repeated inside the null.
    """
    observed = float(stat_fn(mat))
    if not np.isfinite(observed):
        return NullResult(observed=observed, p_value=float("nan"),
                          n_perm=n_perm, n_valid_null=0)

    rng = np.random.default_rng(seed_from_key(*key))
    count = 0
    n_valid = 0
    for _ in range(n_perm):
        val = float(stat_fn(permute_matrix(mat, rng)))
        if not np.isfinite(val):
            continue
        n_valid += 1
        if larger_is_extreme:
            if val >= observed:
                count += 1
        else:
            if val <= observed:
                count += 1

    p = (1 + count) / (1 + n_perm)
    return NullResult(observed=observed, p_value=float(p),
                      n_perm=n_perm, n_valid_null=n_valid)
