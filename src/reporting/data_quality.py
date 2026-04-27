"""Data quality report generator.

Aggregates BatchResult data into a structured DatasetReport and renders
it as markdown or JSON for the dissertation and downstream analysis.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from src.batch_runner import BatchResult, compute_aggregate_reversals
from src.parsing.diagnostics import DiagnosticEvent, ParseDiagnostic


@dataclass
class ConvergenceStats:
    """Iteration statistics for an iterative model."""

    model_name: str
    total_runs: int = 0
    converged_count: int = 0
    non_converged_count: int = 0
    iteration_mean: float = 0.0
    iteration_median: float = 0.0
    iteration_min: int = 0
    iteration_max: int = 0
    non_converged_teams: list[str] = field(default_factory=list)


@dataclass
class ReversalStats:
    """Rank reversal statistics for one advanced model vs baseline."""

    model_name: str
    mean_rate: float = 0.0
    pooled_rate: float = 0.0
    total_reversals: int = 0
    total_eligible: int = 0
    teams_with_eligible_pairs: int = 0


@dataclass
class DatasetReport:
    """Complete data quality and analysis report."""

    # Parsing summary
    csv_count: int = 0
    total_matrices: int = 0
    unique_teams: int = 0
    unique_sessions: int = 0
    teams_excluded: int = 0
    missing_raters: int = 0
    point_mismatches: int = 0
    summary_mismatches: int = 0

    # Model summary
    total_runs: int = 0
    succeeded: int = 0
    failed: int = 0
    failures: list[dict] = field(default_factory=list)

    # Timing
    total_elapsed_s: float = 0.0
    per_model_elapsed_ms: dict[str, float] = field(default_factory=dict)

    # Convergence
    convergence: list[ConvergenceStats] = field(default_factory=list)

    # Rank reversals
    reversals: list[ReversalStats] = field(default_factory=list)

    # Score distribution
    team_sizes: dict[str, float] = field(default_factory=dict)
    iwf_range: dict[str, float] = field(default_factory=dict)

    # Raw diagnostics for detail sections
    diagnostics: list[dict] = field(default_factory=list)


def build_report(batch: BatchResult, delta_iwf: float = 1.5) -> DatasetReport:
    """Build a DatasetReport from a BatchResult."""
    report = DatasetReport(
        csv_count=batch.csv_count,
        total_matrices=batch.matrix_count,
        total_runs=len(batch.run_records),
        succeeded=len(batch.succeeded),
        failed=len(batch.failed),
        total_elapsed_s=batch.total_elapsed_s,
    )

    # --- Parse diagnostics summary ---
    diag_counts = Counter(d.event for d in batch.diagnostics)
    report.teams_excluded = diag_counts.get(DiagnosticEvent.TEAM_EXCLUDED, 0)
    report.missing_raters = diag_counts.get(DiagnosticEvent.RATER_MISSING, 0)
    report.point_mismatches = diag_counts.get(DiagnosticEvent.POINT_TOTAL_MISMATCH, 0)
    report.summary_mismatches = diag_counts.get(DiagnosticEvent.SUMMARY_CROSS_CHECK, 0)
    report.diagnostics = [
        {
            "csv": d.csv_path,
            "team": d.team_name,
            "question": d.question_label,
            "event": d.event.value,
            "detail": d.detail,
            "student": d.student_name,
            "email": d.student_email,
        }
        for d in batch.diagnostics
    ]

    # --- Unique teams and sessions ---
    teams = set()
    sessions = set()
    for rec in batch.run_records:
        teams.add(rec.team_name)
        # Extract session from csv path
        csv_name = rec.csv_path.rsplit("/", 1)[-1] if "/" in rec.csv_path else rec.csv_path
        sessions.add(csv_name)
    report.unique_teams = len(teams)
    report.unique_sessions = len(sessions)

    # --- Failures ---
    report.failures = [
        {
            "model": r.model_name,
            "team": r.team_name,
            "question": r.question_label,
            "error": r.error,
        }
        for r in batch.failed
    ]

    # --- Per-model timing ---
    model_times: dict[str, list[float]] = defaultdict(list)
    for rec in batch.run_records:
        model_times[rec.model_name].append(rec.elapsed_ms)
    report.per_model_elapsed_ms = {
        m: sum(times) for m, times in sorted(model_times.items())
    }

    # --- Convergence stats ---
    iterative_models = [
        "peerrank-impute", "peerrank-exclude",
        "peerhits-impute", "peerhits-exclude",
    ]
    for model_name in iterative_models:
        runs = [r for r in batch.succeeded if r.model_name == model_name]
        if not runs:
            continue

        iterations = []
        non_converged_teams = []
        converged_count = 0

        for r in runs:
            if r.result and r.result.iterations is not None:
                iterations.append(r.result.iterations)
                if r.result.converged:
                    converged_count += 1
                else:
                    non_converged_teams.append(f"{r.team_name} ({r.question_label})")

        if iterations:
            report.convergence.append(ConvergenceStats(
                model_name=model_name,
                total_runs=len(runs),
                converged_count=converged_count,
                non_converged_count=len(non_converged_teams),
                iteration_mean=float(np.mean(iterations)),
                iteration_median=float(np.median(iterations)),
                iteration_min=min(iterations),
                iteration_max=max(iterations),
                non_converged_teams=non_converged_teams,
            ))

    # --- Rank reversals ---
    agg = compute_aggregate_reversals(batch, delta_iwf=delta_iwf)
    for model_name, stats in sorted(agg.items()):
        report.reversals.append(ReversalStats(
            model_name=model_name,
            mean_rate=stats["mean_rate"],
            pooled_rate=stats["pooled_rate"],
            total_reversals=stats["total_reversals"],
            total_eligible=stats["total_eligible"],
            teams_with_eligible_pairs=stats["teams_with_eligible_pairs"],
        ))

    # --- Team size distribution ---
    team_sizes: list[int] = []
    seen_teams: set[tuple] = set()
    for rec in batch.succeeded:
        key = (rec.csv_path, rec.team_name, rec.question_label)
        if key not in seen_teams and rec.model_name == "baseline" and rec.result:
            seen_teams.add(key)
            team_sizes.append(len(rec.result.students))

    if team_sizes:
        report.team_sizes = {
            "min": float(min(team_sizes)),
            "max": float(max(team_sizes)),
            "mean": float(np.mean(team_sizes)),
            "median": float(np.median(team_sizes)),
        }

    # --- IWF range (from baseline) ---
    all_iwfs: list[float] = []
    for rec in batch.succeeded:
        if rec.model_name == "baseline" and rec.result:
            valid = rec.result.iwf_vector[~np.isnan(rec.result.iwf_vector)]
            all_iwfs.extend(valid.tolist())

    if all_iwfs:
        report.iwf_range = {
            "min": float(np.min(all_iwfs)),
            "max": float(np.max(all_iwfs)),
            "mean": float(np.mean(all_iwfs)),
            "std": float(np.std(all_iwfs)),
        }

    return report


def render_markdown(report: DatasetReport) -> str:
    """Render the report as a markdown document."""
    lines = [
        "# Data Quality Report",
        "",
        "## 1. Parsing Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| CSV files processed | {report.csv_count} |",
        f"| Score matrices extracted | {report.total_matrices} |",
        f"| Unique teams | {report.unique_teams} |",
        f"| Teams excluded (≥50% missing) | {report.teams_excluded} |",
        f"| Non-submitting rater events | {report.missing_raters} |",
        f"| Point total mismatches | {report.point_mismatches} |",
        f"| Summary cross-check mismatches | {report.summary_mismatches} |",
        "",
        "## 2. Model Execution Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total model runs | {report.total_runs} |",
        f"| Succeeded | {report.succeeded} |",
        f"| Failed | {report.failed} |",
        f"| Total time | {report.total_elapsed_s:.1f}s |",
        "",
    ]

    if report.per_model_elapsed_ms:
        lines.extend([
            "### Per-Model Timing",
            "",
            "| Model | Total (ms) |",
            "|---|---|",
        ])
        for model, ms in sorted(report.per_model_elapsed_ms.items()):
            lines.append(f"| {model} | {ms:.0f} |")
        lines.append("")

    if report.failures:
        lines.extend([
            "### Failures",
            "",
            "| Model | Team | Question | Error |",
            "|---|---|---|---|",
        ])
        for f in report.failures:
            lines.append(f"| {f['model']} | {f['team']} | {f['question']} | {f['error']} |")
        lines.append("")

    # Convergence
    lines.extend(["## 3. Convergence Summary", ""])
    if report.convergence:
        lines.extend([
            "| Model | Runs | Converged | Iter Mean | Iter Median | Iter Min | Iter Max |",
            "|---|---|---|---|---|---|---|",
        ])
        for c in report.convergence:
            lines.append(
                f"| {c.model_name} | {c.total_runs} | {c.converged_count}/{c.total_runs} "
                f"| {c.iteration_mean:.1f} | {c.iteration_median:.0f} "
                f"| {c.iteration_min} | {c.iteration_max} |"
            )
        lines.append("")

        non_conv = [c for c in report.convergence if c.non_converged_teams]
        if non_conv:
            lines.append("### Non-Converged Cases")
            lines.append("")
            for c in non_conv:
                for team in c.non_converged_teams:
                    lines.append(f"- **{c.model_name}**: {team}")
            lines.append("")

    # Rank reversals
    lines.extend([
        "## 4. Rank Reversal Summary",
        "",
        f"All comparisons are against the **baseline** model (δ = 1.5 IWF points).",
        "",
        "| Model | Mean Rate | Pooled Rate | Reversals | Eligible Pairs | Teams w/ Pairs |",
        "|---|---|---|---|---|---|",
    ])
    for r in report.reversals:
        lines.append(
            f"| {r.model_name} | {r.mean_rate:.3f} | {r.pooled_rate:.3f} "
            f"| {r.total_reversals} | {r.total_eligible} | {r.teams_with_eligible_pairs} |"
        )
    lines.append("")

    # Score distribution
    if report.team_sizes:
        lines.extend([
            "## 5. Score Distribution",
            "",
            "### Team Sizes",
            "",
            f"| Stat | Value |",
            f"|---|---|",
            f"| Min | {report.team_sizes['min']:.0f} |",
            f"| Max | {report.team_sizes['max']:.0f} |",
            f"| Mean | {report.team_sizes['mean']:.1f} |",
            f"| Median | {report.team_sizes['median']:.0f} |",
            "",
        ])

    if report.iwf_range:
        lines.extend([
            "### Baseline IWF Distribution",
            "",
            f"| Stat | Value |",
            f"|---|---|",
            f"| Min | {report.iwf_range['min']:.2f} |",
            f"| Max | {report.iwf_range['max']:.2f} |",
            f"| Mean | {report.iwf_range['mean']:.2f} |",
            f"| Std Dev | {report.iwf_range['std']:.2f} |",
            "",
        ])

    return "\n".join(lines)


def render_json(report: DatasetReport) -> dict[str, Any]:
    """Render the report as a JSON-serializable dict."""
    d = asdict(report)
    # Clean up non-serializable types
    _clean_for_json(d)
    return d


def _clean_for_json(obj: Any) -> None:
    """Recursively convert numpy types to Python natives for JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (np.integer,)):
                obj[k] = int(v)
            elif isinstance(v, (np.floating,)):
                obj[k] = float(v)
            elif isinstance(v, np.ndarray):
                obj[k] = v.tolist()
            elif isinstance(v, (dict, list)):
                _clean_for_json(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (np.integer,)):
                obj[i] = int(v)
            elif isinstance(v, (np.floating,)):
                obj[i] = float(v)
            elif isinstance(v, (dict, list)):
                _clean_for_json(v)
