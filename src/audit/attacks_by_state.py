"""Attack Δ at per-matrix granularity, joined to dynamics2 state (Tasks 7 & 8).

The existing ``output/attacks/attack_summary.csv`` aggregates over all real
matrices, so it cannot be broken down by state after the fact. Here we retain the
per-matrix rows (identity-keyed) and run the same attacks × six (fixed) models,
so attack Δ can be joined to ``output/dynamics2/matrix_states.csv``.

Attacks run on **all 417** matrices (not just the 217 clean) precisely because
the hypothesis is about low-signal / Silent teams: a flat matrix has no structure
to defend, so we must keep those states in the attack set. Per-model failures on
degenerate matrices (e.g. all-zero columns) are caught and skipped.

No changes to ``src/attacks`` — the transforms, Δ metric and Monte-Carlo harness
are imported and driven at finer granularity, exactly as the handoff requires.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.attacks.delta import attack_delta, monte_carlo_single_outlier
from src.attacks.transforms import targeted_downvote, uniform_inflation, zero_self
from src.batch_runner import MODELS
from src.dynamics2.dataio import load_matrices

DETERMINISTIC = {
    "uniform-inflation": uniform_inflation,
    "zero-self-full": lambda sm: zero_self(sm, full=True),
    "zero-self-partial": lambda sm: zero_self(sm, full=False),
    "targeted-downvote": targeted_downvote,
}
SINGLE_OUTLIER = "single-outlier"


def attack_rows_per_matrix(n_perms: int = 100, seed: int = 0,
                           progress: bool = True) -> pd.DataFrame:
    """Per-(matrix, attack, model) attack Δ over all 417 matrices."""
    records = load_matrices()
    rows: list[dict] = []
    for idx, rec in enumerate(records):
        if progress and idx % 50 == 0:
            print(f"  attack {idx + 1}/{len(records)}", file=sys.stderr, flush=True)
        base_key = {"csv_path": rec.csv_path, "team_name": rec.team_name,
                    "question_label": rec.question_label}
        for model_name, fn in MODELS.items():
            try:
                base = fn(rec.sm)
            except Exception:
                continue  # model can't run on this (degenerate) matrix
            for atk_name, transform in DETERMINISTIC.items():
                try:
                    d = attack_delta(base, fn(transform(rec.sm)))
                except Exception:
                    d = float("nan")
                rows.append({**base_key, "attack": atk_name,
                            "model": model_name, "delta": d})
            try:
                mc = monte_carlo_single_outlier(rec.sm, fn, n_perms=n_perms, seed=seed)
                d = mc.mean
            except Exception:
                d = float("nan")
            rows.append({**base_key, "attack": SINGLE_OUTLIER,
                        "model": model_name, "delta": d})
    return pd.DataFrame(rows)


def join_state(rows: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    keys = ["csv_path", "team_name", "question_label"]
    return rows.merge(states[keys + ["state", "degenerate"]], on=keys, how="left")


def attack_by_state(rows_with_state: pd.DataFrame) -> pd.DataFrame:
    """Mean and median attack Δ per (attack, model, state)."""
    g = rows_with_state.dropna(subset=["delta"]).groupby(["attack", "model", "state"])
    out = g["delta"].agg(mean_delta="mean", median_delta="median", n="size").reset_index()
    return out
