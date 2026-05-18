"""CLI entry point for the peer-assessment grading engine."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from src.models.baseline import baseline_average
from src.models.peerrank_impute import peerrank_impute
from src.models.peerrank_exclude import peerrank_exclude
from src.models.webpa import webpa
from src.models.peerhits_impute import peerhits_impute
from src.models.peerhits_exclude import peerhits_exclude
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session


MODELS = {
    "baseline": baseline_average,
    "peerrank-impute": peerrank_impute,
    "peerrank-exclude": peerrank_exclude,
    "webpa": webpa,
    "peerhits-impute": peerhits_impute,
    "peerhits-exclude": peerhits_exclude,
}

_COLUMNS = [
    "session", "team", "question", "student_name", "student_email",
    "model", "iwf", "converged", "iterations", "final_l1_norm",
]


def _pick_csv(data_dir: Path) -> Path:
    """Interactively prompt user to pick a CSV from data_dir."""
    csvs = discover_csvs(data_dir)

    if not csvs:
        print(f"No CSV files found in {data_dir}/. Add CSV files there and try again.")
        sys.exit(1)

    print("Available files:")
    for i, path in enumerate(csvs, 1):
        print(f"  [{i}] {path.name}")

    raw = input("Pick a file (number): ").strip()
    try:
        choice = int(raw)
        if not 1 <= choice <= len(csvs):
            raise ValueError
    except ValueError:
        print(f"Invalid choice: '{raw}'. Enter a number between 1 and {len(csvs)}.")
        sys.exit(1)

    return csvs[choice - 1]


def run(argv: list[str] | None = None) -> Path:
    """Parse args, run models, write output CSV, print summary table.

    Args:
        argv: Argument list (defaults to sys.argv). Useful for testing.

    Returns:
        Path to the written output CSV.
    """
    parser = argparse.ArgumentParser(
        prog="python3 -m src run",
        description="Run peer-assessment IWF models against a CSV file.",
    )
    parser.add_argument(
        "csv_path", type=Path, nargs="?", default=None,
        help="Path to input CSV file. Omit to pick from data/.",
    )
    parser.add_argument(
        "--model", action="append", dest="models", metavar="MODEL",
        help="Model to run (repeatable). Omit to run all.",
    )
    parser.add_argument(
        "--team", default=None, metavar="TEAM",
        help="Filter to a single team name. Omit to run all teams.",
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="PATH",
        help="Output CSV path. Defaults to output/<stem>_<timestamp>.csv",
    )

    args = parser.parse_args(argv)

    # Auto-discover if no path given
    if args.csv_path is None:
        args.csv_path = _pick_csv(Path("data"))

    # Validate and resolve model names
    model_names = args.models or list(MODELS.keys())
    unknown = [m for m in model_names if m not in MODELS]
    if unknown:
        parser.error(
            f"Unknown model(s): {', '.join(unknown)}. "
            f"Available: {', '.join(MODELS)}"
        )

    # Parse input CSV
    matrices = parse_session(args.csv_path)

    # Validate and apply team filter
    available_teams = sorted({team for team, _ in matrices})
    if args.team is not None and args.team not in available_teams:
        parser.error(
            f"Unknown team: '{args.team}'. "
            f"Available teams:\n  " + "\n  ".join(available_teams)
        )
    if args.team:
        matrices = {k: v for k, v in matrices.items() if k[0] == args.team}

    # Resolve output path
    if args.output:
        output_path = args.output
    else:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{args.csv_path.stem}_{timestamp}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run models and collect rows
    rows = []
    summary: dict[tuple, dict] = {}  # (team, question, student) → {model: iwf}

    for (team, question), sm in sorted(matrices.items()):
        session = f"{sm.semester}-{sm.year}"
        for model_name in model_names:
            try:
                result = MODELS[model_name](sm)
            except ValueError as e:
                print(f"  SKIPPED {team} [{model_name}]: {e}", file=sys.stderr)
                continue
            for s in sm.students:
                iwf_raw = float(result.iwf_vector[s.index])
                iwf = None if np.isnan(iwf_raw) else round(iwf_raw, 4)
                rows.append({
                    "session": session,
                    "team": team,
                    "question": question,
                    "student_name": s.name,
                    "student_email": s.email,
                    "model": model_name,
                    "iwf": iwf,
                    "converged": result.converged,
                    "iterations": result.iterations,
                    "final_l1_norm": result.final_l1_norm,
                })
                key = (team, question, s.name)
                summary.setdefault(key, {})[model_name] = iwf_raw

    # Write CSV
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Print summary table
    _print_summary(summary, model_names)
    print(f"\nOutput written to: {output_path}")

    return output_path


def _print_summary(
    summary: dict[tuple, dict],
    model_names: list[str],
) -> None:
    """Print a human-readable side-by-side IWF table to stdout."""
    current_section = None
    header_fmt = f"  {{:<30}}" + "  {:>10}" * len(model_names)
    row_fmt = f"  {{:<30}}" + "  {:>10.3f}" * len(model_names)

    for (team, question, student_name), model_iwfs in summary.items():
        section = (team, question)
        if section != current_section:
            current_section = section
            print(f"\n{team} — {question}")
            print(header_fmt.format("Name", *model_names))
            print("  " + "-" * (30 + 12 * len(model_names)))

        values = [model_iwfs.get(m, float("nan")) for m in model_names]
        parts = [f"  {student_name:<30}"]
        for v in values:
            if math.isnan(v):
                parts.append(f"  {'N/A':>10}")
            else:
                parts.append(f"  {v:>10.3f}")
        print("".join(parts))


def report(argv: list[str] | None = None) -> Path:
    """Run all models across all CSVs and generate a data quality report.

    Args:
        argv: Argument list (defaults to sys.argv). Useful for testing.

    Returns:
        Path to the primary output file.
    """
    import json as json_mod

    from src.batch_runner import run_full_dataset
    from src.reporting.data_quality import build_report, render_json, render_markdown

    parser = argparse.ArgumentParser(
        prog="python3 -m src report",
        description="Generate a data quality report across the full dataset.",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"),
        help="Directory containing CSV files (default: data/)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output"),
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json", "both"], default="both",
        dest="fmt",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--delta", type=float, default=1.5,
        help="Rank reversal δ threshold in IWF points (default: 1.5)",
    )

    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Running full dataset from {args.data_dir}/...")
    batch = run_full_dataset(args.data_dir, delta_iwf=args.delta)
    dataset_report = build_report(batch, delta_iwf=args.delta)

    paths: list[Path] = []

    if args.fmt in ("markdown", "both"):
        md_path = args.output / "data_quality_report.md"
        md_path.write_text(render_markdown(dataset_report))
        print(f"  Markdown report: {md_path}")
        paths.append(md_path)

    if args.fmt in ("json", "both"):
        json_path = args.output / "data_quality_report.json"
        json_path.write_text(json_mod.dumps(render_json(dataset_report), indent=2))
        print(f"  JSON report: {json_path}")
        paths.append(json_path)

    return paths[0]


def attack(argv: list[str] | None = None) -> Path:
    """Run synthetic attack simulation and export robustness charts.

    Applies the four attack vectors across all six models on real
    matrices and/or synthetic teams, then writes robustness charts and a
    summary CSV.

    Returns:
        Path to the output directory.
    """
    from src.attacks.runner import run_attacks
    from src.attacks.synthetic import generate_cohort
    from src.visualization.attack_robustness import export_charts

    parser = argparse.ArgumentParser(
        prog="python3 -m src attack",
        description="Synthetic attack simulation (RQ1/RQ2).",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"),
        help="Directory of CSVs for real-matrix attacks (default: data/)",
    )
    parser.add_argument(
        "--no-real", action="store_true",
        help="Skip real matrices; synthetic only.",
    )
    parser.add_argument(
        "--no-synthetic", action="store_true",
        help="Skip synthetic teams; real only.",
    )
    parser.add_argument(
        "--teams-per-size", type=int, default=10,
        help="Synthetic teams per size (N=4,5,6) (default: 10)",
    )
    parser.add_argument(
        "--profile", default="reliable",
        help="Synthetic generator profile (default: reliable)",
    )
    parser.add_argument(
        "--perms", type=int, default=100,
        help="Single-outlier Monte-Carlo permutations (default: 100)",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Monte-Carlo / generator seed (default: 0)",
    )
    parser.add_argument(
        "--model", action="append", dest="models", metavar="MODEL",
        help="Model to run (repeatable). Omit to run all 6.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/attacks"),
        help="Output directory (default: output/attacks/)",
    )

    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    synthetic = None
    if not args.no_synthetic:
        print(f"Generating synthetic cohort "
              f"({args.teams_per_size}/size, profile={args.profile})...")
        synthetic = generate_cohort(
            teams_per_size=args.teams_per_size,
            base_seed=args.seed,
            profile=args.profile,
        )

    print("Running attacks...")
    batch = run_attacks(
        real_dir=None if args.no_real else args.data_dir,
        synthetic=synthetic,
        model_names=args.models,
        n_perms=args.perms,
        seed=args.seed,
    )

    paths = export_charts(batch, args.output)
    for p in paths:
        print(f"  Chart: {p}")

    summary_path = args.output / "attack_summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["source", "attack", "model", "mean_delta", "n", "mc_std"]
        )
        for source in ("real", "synthetic"):
            for (atk, mdl), v in sorted(batch.aggregate(source=source).items()):
                writer.writerow([
                    source, atk, mdl,
                    round(v["mean_delta"], 4), v["n"],
                    round(v["mc_std"], 4) if v["mc_std"] is not None else "",
                ])
    print(f"  Summary CSV: {summary_path}")

    return args.output


def main() -> None:
    """Dispatch subcommands for `python3 -m src`."""
    if len(sys.argv) < 2:
        print("Usage: python3 -m src <command>")
        print("Commands:")
        print("  run      Run models on a single CSV file")
        print("  report   Generate data quality report across all CSVs")
        print("  attack   Run synthetic attack simulation (RQ1/RQ2)")
        sys.exit(1)

    command = sys.argv[1]
    if command == "run":
        run(sys.argv[2:])
    elif command == "report":
        report(sys.argv[2:])
    elif command == "attack":
        attack(sys.argv[2:])
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, report, attack")
        sys.exit(1)
