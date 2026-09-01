"""The three-gate state cascade — one row per team×question matrix.

Design decision (belongs in §6.4): the gates run in a fixed order and each
matrix lands in exactly one state. Because **Gate B precedes Gate C**, a
genuinely contested team that *also* has a clear scapegoat is filed as
`Contested`, not as both. Disagreement about who is worst is treated as prior to,
and disqualifying of, any claim that a particular person stands out — you cannot
call someone a detached low-scorer when the raters do not even agree on the
ordering. This is deliberate; the alternative (report both) would double-count
and overstate the standout cells.

Gate A — is there an ordering?      (count qualifying raters)
Gate B — do the orderings agree?    (mean pairwise τ-b vs null)
Gate C — is anyone detached?        (bottom / top consensus gap vs null)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.dynamics2 import ranks
from src.dynamics2.nulls import DEFAULT_N_PERM, NullResult, permutation_p

ALPHA = 0.05

# States
SILENT_FLAT = "Silent-flat"
SILENT_LONE = "Silent-lone-dissenter"
SILENT_INCOMPARABLE = "Silent-incomparable"
CONTESTED = "Contested"
ONE_AT_BOTTOM = "One at bottom"
ONE_AT_TOP = "One at top"
BOTH_ENDS = "Both ends"
NO_STANDOUT = "No standout"


@dataclass(frozen=True)
class GateRow:
    """Cascade result for one matrix. NaN fields = the gate was not reached."""

    n: int
    n_raters: int
    mean_tau: float
    bot_gap: float
    top_gap: float
    p_tau: float
    p_bot: float
    p_top: float
    state: str


def _sorted_consensus(mat: np.ndarray) -> np.ndarray:
    """Finite consensus entries, ascending."""
    s = ranks.consensus_vector(mat)
    s = s[np.isfinite(s)]
    return np.sort(s)


def _bot_gap_stat(mat: np.ndarray) -> float:
    s = _sorted_consensus(mat)
    return float(s[1] - s[0]) if s.size >= 3 else float("nan")


def _top_gap_stat(mat: np.ndarray) -> float:
    s = _sorted_consensus(mat)
    return float(s[-1] - s[-2]) if s.size >= 3 else float("nan")


def classify_matrix(
    mat: np.ndarray,
    key: tuple[str, str, str],
    n_perm: int = DEFAULT_N_PERM,
    alpha: float = ALPHA,
) -> GateRow:
    """Run the cascade on one prepared matrix (diagonal already NaN)."""
    n = mat.shape[0]
    qual = ranks.qualifying_raters(mat)
    n_raters = int(qual.sum())

    nan = float("nan")

    # --- Gate A: is there an ordering? ---
    if n_raters == 0:
        return GateRow(n, n_raters, nan, nan, nan, nan, nan, nan, SILENT_FLAT)
    if n_raters == 1:
        return GateRow(n, n_raters, nan, nan, nan, nan, nan, nan, SILENT_LONE)

    mean_tau = ranks.mean_pairwise_tau(mat)
    if not np.isfinite(mean_tau):
        # ≥2 raters but no rater pair shares ≥3 recipients — no comparison exists.
        return GateRow(n, n_raters, nan, nan, nan, nan, nan, nan, SILENT_INCOMPARABLE)

    # --- Gate B: do the orderings agree? ---
    tau_res: NullResult = permutation_p(
        mat, ranks.mean_pairwise_tau, key=(*key, "tau"), n_perm=n_perm,
        larger_is_extreme=True,
    )
    p_tau = tau_res.p_value
    if p_tau > alpha:
        return GateRow(n, n_raters, mean_tau, nan, nan, p_tau, nan, nan, CONTESTED)

    # --- Gate C: is anyone detached? ---
    s = _sorted_consensus(mat)
    if s.size < 3:
        return GateRow(n, n_raters, mean_tau, nan, nan, p_tau, nan, nan, NO_STANDOUT)

    bot_res = permutation_p(mat, _bot_gap_stat, key=(*key, "bot"),
                            n_perm=n_perm, larger_is_extreme=True)
    top_res = permutation_p(mat, _top_gap_stat, key=(*key, "top"),
                            n_perm=n_perm, larger_is_extreme=True)

    bot_sig = bot_res.p_value <= alpha
    top_sig = top_res.p_value <= alpha
    if bot_sig and not top_sig:
        state = ONE_AT_BOTTOM
    elif top_sig and not bot_sig:
        state = ONE_AT_TOP
    elif bot_sig and top_sig:
        state = BOTH_ENDS
    else:
        state = NO_STANDOUT

    return GateRow(
        n=n, n_raters=n_raters, mean_tau=mean_tau,
        bot_gap=bot_res.observed, top_gap=top_res.observed,
        p_tau=p_tau, p_bot=bot_res.p_value, p_top=top_res.p_value,
        state=state,
    )
