"""Shared data loading for the dynamics2 lane.

Enumerates the same 417 team×question score matrices the rest of the project
uses (via `discover_csvs` + `parse_session_with_diagnostics`) and reads the AA
k=4 assignments for read-only comparison. Nothing here re-parses differently
from `src/dynamics`; divergence in the matrix count is a stop-and-report trigger.
"""

from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics
from src.parsing.schemas import ScoreMatrix

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output") / "dynamics2"
AA_ASSIGNMENTS = Path("output") / "dynamics" / "aa_k4_assignments.csv"


@dataclass(frozen=True)
class MatrixRecord:
    """One team×question score matrix with its identity keys."""

    csv_path: str
    team_name: str
    question_label: str
    sm: ScoreMatrix

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.csv_path, self.team_name, self.question_label)


def load_matrices(data_dir: Path = DATA_DIR) -> list[MatrixRecord]:
    """All team×question matrices, parser diagnostics silenced (they go to stderr)."""
    records: list[MatrixRecord] = []
    with contextlib.redirect_stderr(io.StringIO()):
        for csv_path in discover_csvs(data_dir):
            matrices, _ = parse_session_with_diagnostics(csv_path)
            for (team_name, question_label), sm in matrices.items():
                records.append(MatrixRecord(
                    csv_path=str(csv_path),
                    team_name=team_name,
                    question_label=question_label,
                    sm=sm,
                ))
    return records


def load_aa_assignments(path: Path = AA_ASSIGNMENTS) -> pd.DataFrame:
    """AA k=4 assignments (read-only) — for `degenerate` / `atypicality_flag` join."""
    if not path.exists():
        print(f"  Warning: {path} not found — degenerate/atypicality columns will be blank",
              file=sys.stderr)
        return pd.DataFrame(columns=["csv_path", "team_name", "question_label",
                                     "degenerate", "atypicality_flag"])
    return pd.read_csv(path)
