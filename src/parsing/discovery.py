"""File discovery utilities for peer-assessment CSV data."""

from __future__ import annotations

from pathlib import Path


def discover_csvs(data_dir: Path) -> list[Path]:
    """Return sorted list of CSV files found in data_dir."""
    return sorted(data_dir.glob("*.csv"))
