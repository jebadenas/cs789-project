"""Batch runner for executing all IWF models across the full dataset.

Orchestrates parsing all CSVs, running all 6 model variants on each
ScoreMatrix, and collecting structured results and diagnostics.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from src.evaluation.rank_reversal import RankReversalSummary, compute_rank_reversals
from src.models.baseline import baseline_average
from src.models.peerrank_impute import peerrank_impute
from src.models.peerrank_exclude import peerrank_exclude
from src.models.webpa import webpa
from src.models.peerhits_impute import peerhits_impute
from src.models.peerhits_exclude import peerhits_exclude
from src.models.types import ModelResult
from src.parsing.diagnostics import ParseDiagnostic
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics
from src.parsing.schemas import ScoreMatrix


MODELS: dict[str, Callable[[ScoreMatrix], ModelResult]] = {
    "baseline": baseline_average,
    "peerrank-impute": peerrank_impute,
    "peerrank-exclude": peerrank_exclude,
    "webpa": webpa,
    "peerhits-impute": peerhits_impute,
    "peerhits-exclude": peerhits_exclude,
}


@dataclass(frozen=True)
class RunRecord:
    """Result of running a single model on a single ScoreMatrix."""

    csv_path: str
    team_name: str
    question_label: str
    model_name: str
    result: Optional[ModelResult] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.result is not None and self.error is None


@dataclass
class BatchResult:
    """Complete output from a full dataset run."""

    run_records: list[RunRecord] = field(default_factory=list)
    diagnostics: list[ParseDiagnostic] = field(default_factory=list)
    csv_count: int = 0
    matrix_count: int = 0
    total_elapsed_s: float = 0.0

    @property
    def succeeded(self) -> list[RunRecord]:
        return [r for r in self.run_records if r.succeeded]

    @property
    def failed(self) -> list[RunRecord]:
        return [r for r in self.run_records if not r.succeeded]


def run_full_dataset(
    data_dir: Path,
    model_names: list[str] | None = None,
    delta_iwf: float = 1.5,
    progress: bool = True,
) -> BatchResult:
    """Run all models across all CSVs in data_dir.

    Args:
        data_dir: Directory containing CSV files.
        model_names: Models to run (default: all 6).
        delta_iwf: Threshold for rank reversal metric.
        progress: Print progress to stderr.

    Returns:
        BatchResult with all run records and parse diagnostics.
    """
    start = time.monotonic()
    csvs = discover_csvs(data_dir)

    if not csvs:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    models_to_run = model_names or list(MODELS.keys())
    unknown = [m for m in models_to_run if m not in MODELS]
    if unknown:
        raise ValueError(f"Unknown model(s): {', '.join(unknown)}")

    batch = BatchResult(csv_count=len(csvs))

    for csv_idx, csv_path in enumerate(csvs):
        if progress:
            print(
                f"  [{csv_idx + 1}/{len(csvs)}] {csv_path.name}...",
                file=sys.stderr,
                flush=True,
            )

        matrices, diags = parse_session_with_diagnostics(csv_path)
        batch.diagnostics.extend(diags)
        batch.matrix_count += len(matrices)

        for (team_name, question_label), sm in sorted(matrices.items()):
            for model_name in models_to_run:
                model_fn = MODELS[model_name]
                t0 = time.monotonic()
                try:
                    result = model_fn(sm)
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    batch.run_records.append(RunRecord(
                        csv_path=str(csv_path),
                        team_name=team_name,
                        question_label=question_label,
                        model_name=model_name,
                        result=result,
                        elapsed_ms=elapsed_ms,
                    ))
                except Exception as exc:
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    batch.run_records.append(RunRecord(
                        csv_path=str(csv_path),
                        team_name=team_name,
                        question_label=question_label,
                        model_name=model_name,
                        error=f"{type(exc).__name__}: {exc}",
                        elapsed_ms=elapsed_ms,
                    ))

    batch.total_elapsed_s = time.monotonic() - start

    if progress:
        n_ok = len(batch.succeeded)
        n_fail = len(batch.failed)
        print(
            f"  Done: {n_ok} succeeded, {n_fail} failed "
            f"({batch.total_elapsed_s:.1f}s)",
            file=sys.stderr,
        )

    return batch


def compute_aggregate_reversals(
    batch: BatchResult,
    delta_iwf: float = 1.5,
) -> dict[str, dict]:
    """Compute rank reversal stats for each advanced model vs baseline.

    Returns dict keyed by advanced model name with:
        - team_summaries: list of RankReversalSummary per (team, question)
        - mean_rate: mean of per-team reversal rates
        - pooled_rate: total reversals / total eligible pairs
        - total_reversals: int
        - total_eligible: int
    """
    # Group successful baseline results by (csv, team, question)
    baseline_by_key: dict[tuple, ModelResult] = {}
    advanced_by_key: dict[str, dict[tuple, ModelResult]] = {}

    for rec in batch.succeeded:
        key = (rec.csv_path, rec.team_name, rec.question_label)
        if rec.model_name == "baseline":
            baseline_by_key[key] = rec.result
        else:
            advanced_by_key.setdefault(rec.model_name, {})[key] = rec.result

    results: dict[str, dict] = {}

    for model_name, model_results in sorted(advanced_by_key.items()):
        summaries: list[RankReversalSummary] = []
        total_reversals = 0
        total_eligible = 0
        rates: list[float] = []

        for key, adv_result in model_results.items():
            base_result = baseline_by_key.get(key)
            if base_result is None:
                continue

            summary = compute_rank_reversals(
                base_result, adv_result, delta_iwf=delta_iwf,
            )
            summaries.append(summary)
            total_reversals += summary.reversal_count
            total_eligible += summary.eligible_pair_count
            if summary.eligible_pair_count > 0:
                rates.append(summary.reversal_rate)

        pooled_rate = (
            total_reversals / total_eligible if total_eligible > 0 else 0.0
        )
        mean_rate = float(np.mean(rates)) if rates else 0.0

        results[model_name] = {
            "team_summaries": summaries,
            "mean_rate": mean_rate,
            "pooled_rate": pooled_rate,
            "total_reversals": total_reversals,
            "total_eligible": total_eligible,
            "teams_with_eligible_pairs": len(rates),
        }

    return results
