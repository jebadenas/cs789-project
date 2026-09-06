"""Δ regeneration + Δ-by-state (Tasks 5 & 8).

Cross-model Δ per matrix is the per-student standard deviation of the models'
IWFs, averaged over students (keyed per team×question, i.e. per matrix). We
compute it under two model registries:

- **pre-fix**: the previous baseline (un-scaled mean) — every other model is
  numerically unchanged by this handoff.
- **post-fix**: the current (fixed) registry.

Δ is then summarised by cascade state (``src.dynamics2``). The earlier
atypicality-fingerprint recompute (RQ3 §5.3.1) was cut; only Δ-by-state survives.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu

from src.batch_runner import MODELS
from src.dynamics2.dataio import OUTPUT_DIR as DYN2_OUT
from src.dynamics2.dataio import load_matrices
from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix

SILENT_STATES = {"Silent-flat", "Silent-lone-dissenter", "Silent-incomparable"}
NONSILENT_ORDER = ["Contested", "No standout", "One at bottom", "One at top", "Both ends"]


def _prefix_baseline(sm: ScoreMatrix) -> ModelResult:
    """Baseline as it was BEFORE Task 2: self-excluded mean, no scale to 10."""
    matrix = sm.matrix.copy()
    np.fill_diagonal(matrix, np.nan)
    return ModelResult(model_name="Simple Average (Baseline)",
                       iwf_vector=np.nanmean(matrix, axis=1),
                       students=sm.students)


def _registries() -> tuple[dict, dict]:
    """(pre_fix, post_fix) model registries. Only baseline differs."""
    post = dict(MODELS)
    pre = dict(MODELS)
    pre["baseline"] = _prefix_baseline
    return pre, post


def matrix_deltas(registry: dict) -> dict[tuple[str, str, str], float]:
    """Per-matrix cross-model Δ under a model registry (same formula as dynamics)."""
    out: dict[tuple[str, str, str], float] = {}
    for rec in load_matrices():
        vecs: list[np.ndarray] = []
        for fn in registry.values():
            try:
                vecs.append(np.asarray(fn(rec.sm).iwf_vector, dtype=float))
            except Exception:
                continue
        if len(vecs) < 2:
            out[rec.key] = 0.0
            continue
        n = max(len(v) for v in vecs)
        stds: list[float] = []
        for i in range(n):
            vals = [v[i] for v in vecs if i < len(v) and not np.isnan(v[i])]
            if len(vals) >= 2:
                stds.append(float(np.std(vals)))
        out[rec.key] = float(np.mean(stds)) if stds else 0.0
    return out


def _epsilon_squared(H: float, n: int, k: int) -> float:
    """Kruskal–Wallis effect size ε² = (H − k + 1) / (n − k)."""
    return float((H - k + 1) / (n - k)) if n > k else float("nan")


def _rank_biserial(x: np.ndarray, y: np.ndarray) -> float:
    """Rank-biserial correlation from Mann–Whitney U (effect size for a pair)."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return float("nan")
    U = mannwhitneyu(x, y, alternative="two-sided").statistic
    return float(2 * U / (nx * ny) - 1)


def delta_by_state(delta_map: dict, states: pd.DataFrame, value_col: str = "delta") -> pd.DataFrame:
    """One row per state: n, mean, median of Δ (or any per-matrix value)."""
    keys = list(zip(states["csv_path"], states["team_name"], states["question_label"]))
    vals = np.array([delta_map[k] for k in keys], dtype=float)
    d = states[["state"]].copy()
    d[value_col] = vals
    g = d.groupby("state")[value_col]
    out = g.agg(n="size", mean="mean", median="median").reset_index()
    return out.sort_values("median").reset_index(drop=True)


def state_group_test(delta_map: dict, states: pd.DataFrame,
                     exclude_silent: bool) -> dict:
    """Kruskal–Wallis + pairwise Holm-corrected Mann–Whitney + effect sizes."""
    keys = list(zip(states["csv_path"], states["team_name"], states["question_label"]))
    vals = np.array([delta_map[k] for k in keys], dtype=float)
    d = states[["state"]].copy()
    d["v"] = vals
    if exclude_silent:
        d = d[~d["state"].isin(SILENT_STATES)]
    groups = [d.loc[d.state == s, "v"].values for s in d["state"].unique()
              if (d.state == s).sum() > 0]
    labels = [s for s in d["state"].unique() if (d.state == s).sum() > 0]
    H, p = kruskal(*groups)
    n = len(d)
    eps2 = _epsilon_squared(H, n, len(groups))

    # Pairwise Mann–Whitney with Holm correction.
    pairs = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            xi, xj = groups[i], groups[j]
            pu = mannwhitneyu(xi, xj, alternative="two-sided").pvalue
            pairs.append({"a": labels[i], "b": labels[j], "n_a": len(xi), "n_b": len(xj),
                          "p_raw": pu, "rank_biserial": _rank_biserial(xi, xj)})
    # Holm step-down.
    pairs_sorted = sorted(pairs, key=lambda r: r["p_raw"])
    m = len(pairs_sorted)
    for rank, row in enumerate(pairs_sorted):
        row["p_holm"] = min(1.0, row["p_raw"] * (m - rank))
    # enforce monotonicity
    running = 0.0
    for row in pairs_sorted:
        running = max(running, row["p_holm"])
        row["p_holm"] = running

    return {"H": float(H), "p": float(p), "n": n, "k": len(groups),
            "epsilon_squared": eps2, "pairwise": pairs_sorted, "labels": labels}
