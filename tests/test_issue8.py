"""Tests for Issue #8 — Full Dataset Ingestion & Data Quality Report.

Covers parse diagnostics, batch runner, report generation, and
dataset-shape invariants from real data.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from src.batch_runner import BatchResult, RunRecord, run_full_dataset, compute_aggregate_reversals
from src.models.types import ModelResult
from src.parsing.diagnostics import DiagnosticCollector, DiagnosticEvent, ParseDiagnostic
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session, parse_session_with_diagnostics
from src.parsing.schemas import ScoreMatrix, StudentInfo
from src.reporting.data_quality import build_report, render_markdown, render_json


DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_NAMES = {
    "baseline", "peerrank-impute", "peerrank-exclude",
    "webpa", "peerhits-impute", "peerhits-exclude",
}
SKIP_NO_DATA = pytest.mark.skipif(
    not DATA_DIR.exists() or not list(DATA_DIR.glob("*.csv")),
    reason="No CSV data files available",
)


@lru_cache(maxsize=1)
def _data_csvs() -> tuple[Path, ...]:
    return tuple(discover_csvs(DATA_DIR))


@lru_cache(maxsize=1)
def _expected_matrix_count() -> int:
    return sum(len(parse_session(csv)) for csv in _data_csvs())


# ─── Parse Diagnostics ───────────────────────────────────────────────

class TestParseDiagnostics:
    """Test that parse_session_with_diagnostics captures events."""

    @SKIP_NO_DATA
    def test_returns_same_matrices_as_parse_session(self):
        """New function should produce identical ScoreMatrix results."""
        csv = sorted(DATA_DIR.glob("*.csv"))[0]
        original = parse_session(csv)
        with_diag, diagnostics = parse_session_with_diagnostics(csv)

        assert set(original.keys()) == set(with_diag.keys())
        for key in original:
            np.testing.assert_array_equal(
                original[key].matrix, with_diag[key].matrix,
            )

    @SKIP_NO_DATA
    def test_captures_missing_raters(self):
        """S1-2023 Session 1 has known non-submitters (Team 19, etc.)."""
        csv = sorted(DATA_DIR.glob("*.csv"))[0]
        _, diagnostics = parse_session_with_diagnostics(csv)

        missing = [d for d in diagnostics if d.event == DiagnosticEvent.RATER_MISSING]
        assert len(missing) > 0, "Should detect non-submitting raters"
        # All missing rater diagnostics should have student info
        for d in missing:
            assert d.student_email, f"Missing rater diagnostic should have email: {d}"

    @SKIP_NO_DATA
    def test_captures_team_excluded(self):
        """Known real dataset contains teams excluded for ≥50% missing raters."""
        diagnostics = []
        for csv in _data_csvs():
            _, csv_diagnostics = parse_session_with_diagnostics(csv)
            diagnostics.extend(csv_diagnostics)

        excluded = [d for d in diagnostics if d.event == DiagnosticEvent.TEAM_EXCLUDED]
        assert len(excluded) > 0, "Should detect excluded teams"
        assert all(d.team_name for d in excluded)

    def test_diagnostic_collector_by_event(self):
        """DiagnosticCollector.by_event filters correctly."""
        collector = DiagnosticCollector()
        collector.add("f.csv", "Team A", "q1", DiagnosticEvent.RATER_MISSING, "test")
        collector.add("f.csv", "Team B", "q1", DiagnosticEvent.TEAM_EXCLUDED, "test2")
        collector.add("f.csv", "Team C", "q1", DiagnosticEvent.RATER_MISSING, "test3")

        assert len(collector.missing_raters) == 2
        assert len(collector.excluded_teams) == 1


# ─── Discovery ────────────────────────────────────────────────────────

class TestDiscovery:

    @SKIP_NO_DATA
    def test_discovers_all_csvs(self):
        csvs = discover_csvs(DATA_DIR)
        assert csvs == sorted(DATA_DIR.glob("*.csv"))

    def test_empty_dir(self, tmp_path):
        csvs = discover_csvs(tmp_path)
        assert csvs == []


# ─── Batch Runner ─────────────────────────────────────────────────────

class TestBatchRunner:

    @SKIP_NO_DATA
    def test_full_dataset_headline_counts(self):
        """Verify batch headline numbers match the currently available real data."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        expected_matrices = _expected_matrix_count()

        assert batch.csv_count == len(_data_csvs())
        assert batch.matrix_count == expected_matrices
        assert len(batch.run_records) == expected_matrices * len(MODEL_NAMES)
        assert len(batch.succeeded) + len(batch.failed) == len(batch.run_records)
        assert len(batch.succeeded) > 0

    @SKIP_NO_DATA
    def test_all_models_represented(self):
        """Every model should have run on every matrix (minus failures)."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        model_counts = {}
        for rec in batch.run_records:
            model_counts[rec.model_name] = model_counts.get(rec.model_name, 0) + 1

        assert set(model_counts.keys()) == MODEL_NAMES
        for model, count in model_counts.items():
            assert count == batch.matrix_count, (
                f"{model} should have {batch.matrix_count} runs, got {count}"
            )

    @SKIP_NO_DATA
    def test_known_failure(self):
        """peerrank-exclude fails on Team 6 Caffeine Overload (all-zero scores)."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        failures = batch.failed
        assert len(failures) >= 1
        fail = failures[0]
        assert fail.model_name == "peerrank-exclude"
        assert "Team 6 - Caffeine Overload" in fail.team_name
        assert "ValueError" in fail.error

    @SKIP_NO_DATA
    def test_diagnostics_captured(self):
        """Batch runner should accumulate diagnostics from all CSVs."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        assert len(batch.diagnostics) > 50  # known to have ~89-97


# ─── Aggregate Reversals ──────────────────────────────────────────────

class TestAggregateReversals:

    @SKIP_NO_DATA
    def test_all_advanced_models_present(self):
        """Reversal stats computed for all 5 advanced models."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        agg = compute_aggregate_reversals(batch)

        expected = {
            "peerrank-impute", "peerrank-exclude",
            "webpa", "peerhits-impute", "peerhits-exclude",
        }
        assert set(agg.keys()) == expected

    @SKIP_NO_DATA
    def test_rates_are_valid(self):
        """Reversal rates should be between 0 and 1."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        agg = compute_aggregate_reversals(batch)

        for model, stats in agg.items():
            assert 0.0 <= stats["mean_rate"] <= 1.0, f"{model} mean_rate out of range"
            assert 0.0 <= stats["pooled_rate"] <= 1.0, f"{model} pooled_rate out of range"
            assert stats["total_reversals"] <= stats["total_eligible"]

    @SKIP_NO_DATA
    def test_peerrank_has_most_reversals(self):
        """PeerRank models should have more reversals than PeerHITS (known from data)."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        agg = compute_aggregate_reversals(batch)

        pr_reversals = agg["peerrank-impute"]["total_reversals"]
        ph_reversals = agg["peerhits-impute"]["total_reversals"]
        assert pr_reversals >= ph_reversals


# ─── Report Generation ────────────────────────────────────────────────

class TestReportGeneration:

    @SKIP_NO_DATA
    def test_build_report_structure(self):
        """Report should have all expected sections populated."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        report = build_report(batch)

        assert report.csv_count == len(_data_csvs())
        assert report.total_matrices == _expected_matrix_count()
        assert report.succeeded == len(batch.succeeded)
        assert len(report.convergence) == 4  # 4 iterative models
        assert len(report.reversals) == 5  # 5 advanced models
        assert report.team_sizes["min"] > 0
        assert report.iwf_range["min"] >= 0

    @SKIP_NO_DATA
    def test_render_markdown_not_empty(self):
        batch = run_full_dataset(DATA_DIR, progress=False)
        report = build_report(batch)
        md = render_markdown(report)

        assert "# Data Quality Report" in md
        assert "Parsing Summary" in md
        assert "Convergence" in md
        assert "Rank Reversal" in md
        assert len(md) > 500

    @SKIP_NO_DATA
    def test_render_json_serializable(self):
        """JSON output should be fully serializable (no numpy types)."""
        import json

        batch = run_full_dataset(DATA_DIR, progress=False)
        report = build_report(batch)
        j = render_json(report)

        # This will raise if there are non-serializable types
        json_str = json.dumps(j)
        assert len(json_str) > 100

    @SKIP_NO_DATA
    def test_convergence_stats_correct(self):
        """Convergence stats should reflect known behaviour."""
        batch = run_full_dataset(DATA_DIR, progress=False)
        report = build_report(batch)

        for cs in report.convergence:
            if "peerrank" in cs.model_name:
                # PeerRank typically converges in ~93-379 iterations
                assert cs.iteration_min >= 1
                assert cs.iteration_max <= 1000
                assert cs.converged_count == cs.total_runs
            elif "peerhits" in cs.model_name:
                # PeerHITS typically 1-172 iterations
                assert cs.iteration_min >= 1


# ─── CLI Subcommand ───────────────────────────────────────────────────

class TestCLI:

    @SKIP_NO_DATA
    def test_report_command(self, tmp_path):
        """CLI report subcommand produces output files."""
        from src.cli import report

        report(["--data-dir", str(DATA_DIR), "--output", str(tmp_path)])

        md_file = tmp_path / "data_quality_report.md"
        json_file = tmp_path / "data_quality_report.json"
        assert md_file.exists()
        assert json_file.exists()
        assert md_file.stat().st_size > 500
        assert json_file.stat().st_size > 100
