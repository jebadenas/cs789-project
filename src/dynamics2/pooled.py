"""Pooled team-level cascade — one state per team, pooling its questions.

The per-matrix cascade in ``gates`` needs a rater pair to share ≥3 commonly-rated
recipients before Kendall τ-b is computable. In a team of four each rater rates 3
teammates and any two raters share at most 2 — one short — so *every* N=4 matrix
is ``Silent-incomparable`` regardless of content. Pooling a team's three
artefacts (code, report, poster) keys each rater's vector by
``(recipient, question)`` instead of ``recipient``, so an N=4 rater pair shares
2 recipients × 3 questions = 6 common keys and the bar is cleared.

This module mirrors ``gates`` at the team level. It is an **additive** lane: it
does not touch ``matrix_states.csv`` or the per-matrix cascade, which stays as
the validated instrument (handoff-11 B0). The pooling primitive
``pooled_tau_matrix`` lives here and is imported by ``contested`` (the 4c faction
test), so the two share one definition.

Team identity is keyed on ``(csv_path, team_name)`` — never the bare team name,
because team numbers recur across cohorts (the 137-vs-139 trap). ``csv_path``
carries the cohort.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.dynamics2 import gates, ranks
from src.dynamics2.nulls import DEFAULT_N_PERM, permute_matrix, seed_from_key

ALPHA = 0.05

# One (emails, prepared_matrix) per question. ``prepared`` = diagonal already NaN.
Item = tuple[list[str], np.ndarray]


# --------------------------------------------------------------------------- #
# Pooling primitives (shared with contested.py's 4c faction test)
# --------------------------------------------------------------------------- #

def pooled_rank_vectors(items: list[Item]) -> dict[str, dict[tuple[str, int], float]]:
    """Each rater's pooled normalised-rank vector, keyed by ``(recipient, qi)``.

    A rater appears iff they qualify (≥2 finite entries, non-zero SD) in **at
    least one** question — non-qualifying columns are already NaN in
    ``normalised_rank_matrix`` and contribute nothing.
    """
    pooled: dict[str, dict[tuple[str, int], float]] = {}
    for qi, (emails, mat) in enumerate(items):
        R = ranks.normalised_rank_matrix(mat)
        n, m = R.shape
        for j in range(m):
            rater = emails[j]
            for i in range(n):
                v = R[i, j]
                if np.isfinite(v):
                    pooled.setdefault(rater, {})[(emails[i], qi)] = float(v)
    return pooled


def pooled_tau_matrix(items: list[Item], min_common: int = 3) -> tuple[np.ndarray, list[str]]:
    """τ-b between raters over their common ``(recipient, question)`` keys.

    ``items`` is one ``(emails, prepared_matrix)`` per question. Returns the
    (r×r) τ-b matrix over the ``r`` raters that qualify in ≥1 question, and the
    sorted rater-email list. A pair with fewer than ``min_common`` shared pooled
    keys is left NaN.
    """
    pooled = pooled_rank_vectors(items)
    raters = sorted(pooled)
    r = len(raters)
    T = np.full((r, r), np.nan)
    for a in range(r):
        for b in range(a + 1, r):
            va, vb = pooled[raters[a]], pooled[raters[b]]
            common = sorted(set(va) & set(vb))
            if len(common) < min_common:
                continue
            x = np.array([va[k] for k in common])
            y = np.array([vb[k] for k in common])
            t = ranks.tau_b(x, y)
            T[a, b] = T[b, a] = t
    return T, raters


def pooled_mean_tau(items: list[Item]) -> float:
    """Team agreement: mean of the finite off-diagonal pooled τ-b entries.

    NaN if no rater pair shares ≥3 pooled keys (the team is *incomparable* even
    after pooling).
    """
    T, _ = pooled_tau_matrix(items)
    iu = np.triu_indices(T.shape[0], k=1)
    vals = T[iu]
    vals = vals[np.isfinite(vals)]
    return float(np.mean(vals)) if vals.size else float("nan")


def pooled_consensus(items: list[Item]) -> dict[str, float]:
    """Per-recipient consensus: mean normalised rank over every ``(rater,
    question)`` cell in which that recipient appears (across all questions)."""
    acc: dict[str, list[float]] = {}
    for _, (emails, mat) in enumerate(items):
        R = ranks.normalised_rank_matrix(mat)
        n, m = R.shape
        for i in range(n):
            row = R[i, :]
            for v in row[np.isfinite(row)]:
                acc.setdefault(emails[i], []).append(float(v))
    return {e: float(np.mean(vs)) for e, vs in acc.items() if vs}


def _sorted_consensus(items: list[Item]) -> np.ndarray:
    return np.sort(np.array(list(pooled_consensus(items).values()), dtype=float))


def _bot_gap(items: list[Item]) -> float:
    s = _sorted_consensus(items)
    return float(s[1] - s[0]) if s.size >= 3 else float("nan")


def _top_gap(items: list[Item]) -> float:
    s = _sorted_consensus(items)
    return float(s[-1] - s[-2]) if s.size >= 3 else float("nan")


# --------------------------------------------------------------------------- #
# Pooled permutation null — permute within (rater, question)
# --------------------------------------------------------------------------- #

def pooled_permutation_p(items: list[Item], stat_fn, key: tuple[object, ...],
                         n_perm: int = DEFAULT_N_PERM,
                         larger_is_extreme: bool = True) -> tuple[float, float, int]:
    """Add-one p-value for ``stat_fn(items)`` under the pooled null.

    The null shuffles **each question matrix's columns independently**
    (``permute_matrix`` per item), preserving each rater's severity, spread and
    ties within each question and destroying only the recipient-to-score
    correspondence. Returns ``(observed, p_value, n_valid_null)``.
    """
    observed = float(stat_fn(items))
    if not np.isfinite(observed):
        return observed, float("nan"), 0
    rng = np.random.default_rng(seed_from_key(*key))
    count = 0
    n_valid = 0
    for _ in range(n_perm):
        perm_items = [(emails, permute_matrix(mat, rng)) for emails, mat in items]
        val = float(stat_fn(perm_items))
        if not np.isfinite(val):
            continue
        n_valid += 1
        if (val >= observed) if larger_is_extreme else (val <= observed):
            count += 1
    return observed, (1 + count) / (1 + n_perm), n_valid


# --------------------------------------------------------------------------- #
# The pooled cascade
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PooledState:
    """Pooled cascade result for one team. NaN fields = the gate was not reached."""

    n_members: int
    n_raters: int
    mean_tau: float
    bot_gap: float
    top_gap: float
    p_tau: float
    p_bot: float
    p_top: float
    state: str


def classify_team(items: list[Item], key: tuple[str, str],
                  n_perm: int = DEFAULT_N_PERM, alpha: float = ALPHA) -> PooledState:
    """Run the pooled cascade on one team's question-matrices.

    ``items`` is every readable question of the team as ``(emails,
    prepared_matrix)`` (diagonal already NaN); non-qualifying columns are
    tolerated. ``key`` = ``(csv_path, team_name)``. Gate B precedes Gate C, as
    in the per-matrix cascade: a team whose raters do not agree cannot support a
    claim that one person stands out.
    """
    n_members = max((mat.shape[0] for _, mat in items), default=0)
    T, raters = pooled_tau_matrix(items)
    n_raters = len(raters)
    nan = float("nan")

    # --- Gate A: is there an ordering? ---
    if n_raters == 0:
        return PooledState(n_members, 0, nan, nan, nan, nan, nan, nan, gates.SILENT_FLAT)
    if n_raters == 1:
        return PooledState(n_members, 1, nan, nan, nan, nan, nan, nan, gates.SILENT_LONE)

    mean_tau = pooled_mean_tau(items)
    if not np.isfinite(mean_tau):
        # ≥2 raters but no pair shares ≥3 pooled keys — no comparison exists.
        return PooledState(n_members, n_raters, nan, nan, nan, nan, nan, nan,
                           gates.SILENT_INCOMPARABLE)

    # --- Gate B: do the orderings agree? ---
    _, p_tau, _ = pooled_permutation_p(items, pooled_mean_tau, key=(*key, "pooled-tau"),
                                       n_perm=n_perm, larger_is_extreme=True)
    if p_tau > alpha:
        return PooledState(n_members, n_raters, mean_tau, nan, nan, p_tau, nan, nan,
                           gates.CONTESTED)

    # --- Gate C: is anyone detached? ---
    s = _sorted_consensus(items)
    if s.size < 3:
        return PooledState(n_members, n_raters, mean_tau, nan, nan, p_tau, nan, nan,
                           gates.NO_STANDOUT)
    b_obs, p_bot, _ = pooled_permutation_p(items, _bot_gap, key=(*key, "pooled-bot"),
                                           n_perm=n_perm, larger_is_extreme=True)
    t_obs, p_top, _ = pooled_permutation_p(items, _top_gap, key=(*key, "pooled-top"),
                                           n_perm=n_perm, larger_is_extreme=True)
    bot_sig = p_bot <= alpha
    top_sig = p_top <= alpha
    if bot_sig and not top_sig:
        state = gates.ONE_AT_BOTTOM
    elif top_sig and not bot_sig:
        state = gates.ONE_AT_TOP
    elif bot_sig and top_sig:
        state = gates.BOTH_ENDS
    else:
        state = gates.NO_STANDOUT

    return PooledState(n_members, n_raters, mean_tau, b_obs, t_obs,
                       p_tau, p_bot, p_top, state)
