"""Tests for the CLI runner (python3 -m src run)."""

import pandas as pd
import pytest
from pathlib import Path

CSV_2023 = Path(
    "/Users/josbadenas/Documents/Uni/2025 S2/COMPSCI 399/"
    "COMPSCI399-S1-2023_Peer Feedback Session 1 - S1, 2023_result (1).csv"
)

EXPECTED_COLUMNS = {
    "session", "team", "question", "student_name", "student_email",
    "model", "iwf", "converged", "iterations", "final_l1_norm",
}


@pytest.fixture(autouse=True)
def require_csv():
    if not CSV_2023.exists():
        pytest.skip("2023 CSV not available")


class TestDiscoverCSVs:
    """Behaviour: discover_csvs finds CSV files in a directory."""

    def test_returns_csv_paths_found_in_directory(self, tmp_path):
        """Behaviour: returns sorted list of CSV paths present in the directory."""
        from src.cli import discover_csvs

        (tmp_path / "file_b.csv").touch()
        (tmp_path / "file_a.csv").touch()
        (tmp_path / "notes.txt").touch()

        result = discover_csvs(tmp_path)

        assert [p.name for p in result] == ["file_a.csv", "file_b.csv"]

    def test_returns_empty_list_when_no_csvs_present(self, tmp_path):
        """Behaviour: returns empty list when directory has no CSV files."""
        from src.cli import discover_csvs

        result = discover_csvs(tmp_path)

        assert result == []


class TestCLIAutoDiscovery:
    """Behaviour: omitting csv_path triggers auto-discovery from data/."""

    def test_run_with_no_path_and_user_picks_first_file(self, tmp_path, monkeypatch):
        """Behaviour: no csv_path → discovers CSVs, user picks 1 → runs against that file."""
        from src.cli import run

        # Set up a data/ dir with a real CSV
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        import shutil
        shutil.copy(CSV_2023, data_dir / CSV_2023.name)

        output = tmp_path / "out.csv"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "1")

        run(["--output", str(output)])

        df = pd.read_csv(output)
        assert len(df) > 0

    def test_run_with_empty_data_dir_exits_with_message(self, tmp_path, monkeypatch, capsys):
        """Behaviour: no CSVs in data/ → prints helpful message and exits."""
        from src.cli import run

        (tmp_path / "data").mkdir()
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit):
            run([])

        assert "no csv" in capsys.readouterr().out.lower()

    def test_run_with_invalid_pick_exits_with_error(self, tmp_path, monkeypatch, capsys):
        """Behaviour: user enters a number out of range → error message and exit."""
        from src.cli import run

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        import shutil
        shutil.copy(CSV_2023, data_dir / CSV_2023.name)

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "99")

        with pytest.raises(SystemExit):
            run([])

        assert "invalid" in capsys.readouterr().out.lower()


class TestCLIRun:
    """Behaviour: `python3 -m src run data/file.csv` produces a tidy CSV."""

    def test_run_produces_csv_with_correct_columns(self, tmp_path):
        """Tracer bullet: running against a real CSV produces a file with the full schema."""
        from src.cli import run

        output = tmp_path / "out.csv"
        run([str(CSV_2023), "--output", str(output)])

        df = pd.read_csv(output)
        assert EXPECTED_COLUMNS.issubset(df.columns)
        assert len(df) > 0

    def test_model_flag_filters_to_named_model_only(self, tmp_path):
        """Behaviour: --model peerrank-impute produces only peerrank-impute rows in the CSV."""
        from src.cli import run

        output = tmp_path / "out.csv"
        run([str(CSV_2023), "--model", "peerrank-impute", "--output", str(output)])

        df = pd.read_csv(output)
        assert set(df["model"].unique()) == {"peerrank-impute"}

    def test_multiple_model_flags_runs_only_those_models(self, tmp_path):
        """Behaviour: --model baseline --model peerrank-impute runs exactly those two."""
        from src.cli import run

        output = tmp_path / "out.csv"
        run([str(CSV_2023), "--model", "baseline", "--model", "peerrank-impute", "--output", str(output)])

        df = pd.read_csv(output)
        assert set(df["model"].unique()) == {"baseline", "peerrank-impute"}

    def test_unknown_model_exits_with_error(self, tmp_path, capsys):
        """Behaviour: unknown --model name exits with SystemExit and lists valid models."""
        from src.cli import run

        with pytest.raises(SystemExit):
            run([str(CSV_2023), "--model", "nonexistent", "--output", str(tmp_path / "out.csv")])

        captured = capsys.readouterr()
        assert "baseline" in captured.err
        assert "peerrank" in captured.err

    def test_team_flag_filters_to_named_team_only(self, tmp_path):
        """Behaviour: --team filters CSV rows to that team only."""
        from src.cli import run

        output = tmp_path / "out.csv"
        run([str(CSV_2023), "--team", "Team 20", "--output", str(output)])

        df = pd.read_csv(output)
        assert set(df["team"].unique()) == {"Team 20"}

    def test_no_team_flag_runs_all_teams(self, tmp_path):
        """Behaviour: omitting --team produces rows for more than one team."""
        from src.cli import run

        output = tmp_path / "out.csv"
        run([str(CSV_2023), "--output", str(output)])

        df = pd.read_csv(output)
        assert df["team"].nunique() > 1

    def test_unknown_team_exits_with_error_listing_teams(self, tmp_path, capsys):
        """Behaviour: unknown --team exits with SystemExit and lists available teams."""
        from src.cli import run

        with pytest.raises(SystemExit):
            run([str(CSV_2023), "--team", "Team 99", "--output", str(tmp_path / "out.csv")])

        captured = capsys.readouterr()
        assert "Team 20" in captured.err

    def test_output_flag_writes_to_specified_path(self, tmp_path):
        """Behaviour: --output writes the CSV to the given path."""
        from src.cli import run

        output = tmp_path / "custom" / "result.csv"
        run([str(CSV_2023), "--output", str(output)])

        assert output.exists()

    def test_default_output_written_to_output_directory(self, tmp_path, monkeypatch):
        """Behaviour: without --output, CSV is written to output/<stem>_<timestamp>.csv."""
        from src.cli import run

        # Run from tmp_path so output/ is created there, not in the project root
        monkeypatch.chdir(tmp_path)
        returned_path = run([str(CSV_2023)])

        assert returned_path.parent.name == "output"
        assert CSV_2023.stem in returned_path.name
        assert returned_path.exists()
