"""Δ regeneration + RQ3 recompute + Δ-by-state (Tasks 5 & 8).

Cross-model Δ per matrix is the per-student standard deviation of the six models'
IWFs, averaged over students — exactly the formula in
``src.dynamics.__main__._compute_team_delta`` (keyed per team×question, i.e. per
matrix). We compute it under two model registries:

- **pre-fix**: the previous baseline (un-scaled mean) — every other model is
  numerically unchanged by this handoff.
- **post-fix**: the current (fixed) registry.

The atypicality score and the 24 features are computed from raw scores and do not
depend on model output, so RQ3's atypicality axis is identical pre/post; only Δ
moves. That lets us reuse the reconstructed Bundle from ``dynamics.validity`` and
swap in each Δ.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu, pearsonr, ttest_ind

from src.batch_runner import MODELS
from src.dynamics.features import FEATURE_NAMES
from src.dynamics.validity import (
    Bundle, _low_level_controls, _partial_correlation, load,
)
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


def _delta_array(delta_map: dict, fm: pd.DataFrame) -> np.ndarray:
    keys = list(zip(fm["csv_path"], fm["team_name"], fm["question_label"]))
    return np.array([delta_map[k] for k in keys], dtype=float)


def rq3_stats(b: Bundle, delta: np.ndarray, label: str) -> dict:
    """Row-level, team-level, group-contrast and partial-correlation RQ3 stats."""
    clean = ~b.degenerate
    d_c, atyp_c = delta[clean], b.dist[clean]

    r_row, p_row = pearsonr(atyp_c, d_c)

    # Team-level aggregation (majority-vote flag), matching validity.cmd_b.
    df = b.fm[["csv_path", "team_name"]].copy()
    df["atyp"], df["delta"], df["flag"], df["degen"] = b.dist, delta, b.flag, b.degenerate
    clean_df = df[~df["degen"]].copy()
    clean_df["team_id"] = clean_df["csv_path"] + " :: " + clean_df["team_name"]
    agg = clean_df.groupby("team_id").agg(
        mean_atyp=("atyp", "mean"), mean_delta=("delta", "mean"),
        n_anom=("flag", lambda s: (s == "Anomalous").sum()), n=("flag", "size"),
    ).reset_index()
    agg["team_flag"] = np.where(agg["n_anom"] >= agg["n"] / 2, "Anomalous", "Typical")
    r_team, p_team = pearsonr(agg["mean_atyp"], agg["mean_delta"])
    a = agg.loc[agg.team_flag == "Anomalous", "mean_delta"]
    t = agg.loc[agg.team_flag == "Typical", "mean_delta"]
    welch_p = ttest_ind(a, t, equal_var=False).pvalue if len(a) > 1 and len(t) > 1 else np.nan
    mw_p = mannwhitneyu(a, t, alternative="two-sided").pvalue if len(a) and len(t) else np.nan

    # Partial correlation controlling for low-level structure (validity.cmd_c).
    controls = _low_level_controls(b)[clean]
    raw_r, raw_p = pearsonr(atyp_c, d_c)
    pr, ppart = _partial_correlation(atyp_c, d_c, controls)

    return {
        "variant": label,
        "row_r": r_row, "row_p": p_row, "n_rows": int(clean.sum()),
        "team_r": r_team, "team_p": p_team, "n_teams": len(agg),
        "contrast_anom_meanD": float(a.mean()) if len(a) else np.nan,
        "contrast_typ_meanD": float(t.mean()) if len(t) else np.nan,
        "welch_p": float(welch_p), "mw_p": float(mw_p),
        "raw_atyp_delta_r": raw_r, "partial_atyp_delta_r": pr, "partial_p": ppart,
        "delta_mean_all": float(delta.mean()), "delta_mean_clean": float(d_c.mean()),
    }


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
