"""CLI entry point for the peer-assessment grading engine."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from src.models.baseline import baseline_average
from src.models.peerrank import peerrank
from src.models.webpa import webpa
from src.parsing.parser import parse_session

def discover_csvs(data_dir: Path) -> list[Path]:
    """Return sorted list of CSV files found in data_dir."""
    return sorted(data_dir.glob("*.csv"))


MODELS = {
    "baseline": baseline_average,
    "peerrank": peerrank,
    "webpa": webpa,
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
                iwf = float(result.iwf_vector[s.index])
                rows.append({
                    "session": session,
                    "team": team,
                    "question": question,
                    "student_name": s.name,
                    "student_email": s.email,
                    "model": model_name,
                    "iwf": round(iwf, 4),
                    "converged": result.converged,
                    "iterations": result.iterations,
                    "final_l1_norm": result.final_l1_norm,
                })
                key = (team, question, s.name)
                summary.setdefault(key, {})[model_name] = iwf

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
        print(row_fmt.format(student_name, *values))


def main() -> None:
    """Dispatch subcommands for `python3 -m src`."""
    if len(sys.argv) < 2 or sys.argv[1] != "run":
        print("Usage: python3 -m src run data/file.csv [--model MODEL] [--team TEAM] [--output PATH]")
        sys.exit(1)
    run(sys.argv[2:])
