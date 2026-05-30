"""RQ2 convergence analysis for the iterative IWF models.

Aggregates convergence behaviour of the four iterative models
(PeerRank impute/exclude, PeerHITS impute/exclude) across all 417
matrices, sweeps the PeerRank learning rate ``alpha``, and characterises
which matrix shapes fail to converge (or fail outright).

Run:
    python3 -m src.evaluation.convergence

Outputs to output/convergence/:
    iteration_distribution.csv  — per-model iteration stats + (non)convergence
    alpha_sweep.csv             — alpha × PeerRank variant → iters + nonconvergence
    nonconvergence_cases.csv    — per-matrix failures (error / cap) with shape
    iteration_histogram.html    — iteration-count distribution per model
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.models.peerhits_exclude import peerhits_exclude
from src.models.peerhits_impute import peerhits_impute
from src.models.peerrank_exclude import peerrank_exclude
from src.models.peerrank_impute import peerrank_impute
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics
from src.parsing.schemas import ScoreMatrix

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output") / "convergence"

ITERATIVE_MODELS = {
    "peerrank-impute": peerrank_impute,
    "peerrank-exclude": peerrank_exclude,
    "peerhits-impute": peerhits_impute,
    "peerhits-exclude": peerhits_exclude,
}
PEERRANK_VARIANTS = {
    "peerrank-impute": peerrank_impute,
    "peerrank-exclude": peerrank_exclude,
}
ALPHA_GRID = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
MAX_ITER = 1000


def _load_matrices() -> list[tuple[str, str, ScoreMatrix]]:
    out: list[tuple[str, str, ScoreMatrix]] = []
    for csv_path in discover_csvs(DATA_DIR):
        matrices, _ = parse_session_with_diagnostics(csv_path)
        for (team, label), sm in sorted(matrices.items()):
            out.append((f"{csv_path.name}:{team}", label, sm))
    return out


def _matrix_shape(sm: ScoreMatrix) -> dict:
    """Descriptive shape used to characterise failure cases."""
    A = sm.matrix
    n = len(sm.students)
    non_sub = 0
    for j in range(n):
        peer = np.delete(A[:, j], j)
        if np.all(np.isnan(peer)):
            non_sub += 1
    rater_stds = []
    for j in range(n):
        col = A[:, j]
        vals = col[~np.isnan(col)]
        if vals.size:
            rater_stds.append(float(np.std(vals)))
    mean_rater_std = float(np.mean(rater_stds)) if rater_stds else 0.0
    return {"team_size": n, "non_submitters": non_sub,
            "mean_rater_std": round(mean_rater_std, 4)}


def iteration_distribution(matrices) -> tuple[pd.DataFrame, dict[str, list[int]]]:
    """Per-model iteration stats at default settings + raw iters for histogram."""
    iters_by_model: dict[str, list[int]] = {m: [] for m in ITERATIVE_MODELS}
    nonconv_by_model: dict[str, int] = {m: 0 for m in ITERATIVE_MODELS}
    errors_by_model: dict[str, int] = {m: 0 for m in ITERATIVE_MODELS}

    for _, _, sm in matrices:
        for name, fn in ITERATIVE_MODELS.items():
            try:
                res = fn(sm)
            except Exception:
                errors_by_model[name] += 1
                continue
            if res.iterations is not None:
                iters_by_model[name].append(res.iterations)
            if res.converged is False:
                nonconv_by_model[name] += 1

    rows = []
    for name in ITERATIVE_MODELS:
        it = np.array(iters_by_model[name], dtype=float)
        rows.append({
            "model": name,
            "n_runs": len(it),
            "n_errored": errors_by_model[name],
            "n_nonconverged": nonconv_by_model[name],
            "mean_iter": round(float(it.mean()), 2) if it.size else None,
            "median_iter": int(np.median(it)) if it.size else None,
            "min_iter": int(it.min()) if it.size else None,
            "max_iter": int(it.max()) if it.size else None,
            "p95_iter": int(np.percentile(it, 95)) if it.size else None,
            "std_iter": round(float(it.std()), 2) if it.size else None,
        })
    return pd.DataFrame(rows), iters_by_model


def alpha_sweep(matrices) -> pd.DataFrame:
    """Sweep PeerRank alpha; record iterations + non-convergence per alpha."""
    rows = []
    for alpha in ALPHA_GRID:
        for name, fn in PEERRANK_VARIANTS.items():
            iters, nonconv, errored = [], 0, 0
            for _, _, sm in matrices:
                try:
                    res = fn(sm, alpha=alpha, max_iterations=MAX_ITER)
                except Exception:
                    errored += 1
                    continue
                if res.iterations is not None:
                    iters.append(res.iterations)
                if res.converged is False:
                    nonconv += 1
            it = np.array(iters, dtype=float)
            rows.append({
                "alpha": alpha,
                "model": name,
                "n_runs": len(it),
                "n_nonconverged": nonconv,
                "n_errored": errored,
                "mean_iter": round(float(it.mean()), 2) if it.size else None,
                "median_iter": int(np.median(it)) if it.size else None,
                "max_iter": int(it.max()) if it.size else None,
            })
    return pd.DataFrame(rows)


def nonconvergence_cases(matrices) -> pd.DataFrame:
    """Matrices where any iterative model errors or hits the iteration cap."""
    rows = []
    for key, label, sm in matrices:
        shape = _matrix_shape(sm)
        for name, fn in ITERATIVE_MODELS.items():
            outcome = None
            try:
                res = fn(sm)
                if res.converged is False or (
                    res.iterations is not None and res.iterations >= MAX_ITER
                ):
                    outcome = "hit_cap"
            except Exception as exc:
                outcome = f"error:{type(exc).__name__}"
            if outcome is not None:
                rows.append({
                    "matrix": key, "question": label, "model": name,
                    "outcome": outcome, **shape,
                })
    return pd.DataFrame(rows)


def _histogram(iters_by_model: dict[str, list[int]], path: Path) -> None:
    import plotly.graph_objects as go

    fig = go.Figure()
    for name, iters in iters_by_model.items():
        if iters:
            fig.add_trace(go.Histogram(x=iters, name=name, opacity=0.6,
                                       nbinsx=40))
    fig.update_layout(
        barmode="overlay",
        title="Convergence-iteration distribution across all matrices (RQ2)",
        xaxis_title="iterations to convergence",
        yaxis_title="count",
    )
    fig.write_html(str(path))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading matrices...", flush=True)
    matrices = _load_matrices()
    print(f"  {len(matrices)} matrices", flush=True)

    print("Iteration distribution (default settings)...", flush=True)
    dist_df, iters_by_model = iteration_distribution(matrices)
    dist_path = OUTPUT_DIR / "iteration_distribution.csv"
    dist_df.to_csv(dist_path, index=False)
    print(dist_df.to_string(index=False), flush=True)
    print(f"  Saved {dist_path}", flush=True)

    print("\nAlpha sensitivity sweep (PeerRank)...", flush=True)
    sweep_df = alpha_sweep(matrices)
    sweep_path = OUTPUT_DIR / "alpha_sweep.csv"
    sweep_df.to_csv(sweep_path, index=False)
    print(sweep_df.to_string(index=False), flush=True)
    print(f"  Saved {sweep_path}", flush=True)

    print("\nNon-convergence / failure cases...", flush=True)
    fail_df = nonconvergence_cases(matrices)
    fail_path = OUTPUT_DIR / "nonconvergence_cases.csv"
    fail_df.to_csv(fail_path, index=False)
    if len(fail_df):
        print(f"  {len(fail_df)} (matrix, model) failure events", flush=True)
        print(fail_df["outcome"].value_counts().to_string(), flush=True)
    else:
        print("  none — every model converged on every matrix at default α",
              flush=True)
    print(f"  Saved {fail_path}", flush=True)

    _histogram(iters_by_model, OUTPUT_DIR / "iteration_histogram.html")
    print(f"  Saved {OUTPUT_DIR / 'iteration_histogram.html'}", flush=True)


if __name__ == "__main__":
    main()
