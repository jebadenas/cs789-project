"""Integration test: Issue #7 — full pipeline verification.

Runs the complete model comparison + rank reversal pipeline against
real data from the project's data/ directory.  Skips if no CSV files
are available.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pytest

from src.evaluation.rank_reversal import compute_rank_reversals, RankReversalSummary
from src.models.baseline import baseline_average
from src.models.peerrank import peerrank
from src.models.webpa import webpa
from src.models.peerhits import peerhits
from src.parsing.parser import parse_session

DATA_DIR = Path("data")

MODELS = {
    "baseline": baseline_average,
    "peerrank": peerrank,
    "webpa": webpa,
    "peerhits": peerhits,
}

ADVANCED_MODELS = ["peerrank", "webpa", "peerhits"]


def _find_team(team_substr: str, csv_glob: str = "*.csv"):
    """Find a (csv_path, key, ScoreMatrix) for a team name substring."""
    for csv in sorted(DATA_DIR.glob(csv_glob)):
        matrices = parse_session(csv)
        for k in sorted(matrices.keys()):
            if team_substr in k[0]:
                return csv, k, matrices[k]
    return None, None, None


@pytest.fixture(autouse=True)
def require_data():
    csvs = sorted(DATA_DIR.glob("*.csv"))
    if not csvs:
        pytest.skip("No CSV files in data/")


class TestTeam11ExquisiTech:
    """Criterion 7: Verified on Team 11 - ExquisiTech."""

    def test_all_models_run_successfully(self):
        """All 4 models produce valid IWF vectors for Team 11."""
        _, key, sm = _find_team("ExquisiTech", "*2024*Session 4*")
        assert sm is not None, "Team 11 - ExquisiTech not found in 2024 Session 4 data"

        for name, fn in MODELS.items():
            result = fn(sm)
            assert result.iwf_vector is not None
            assert len(result.iwf_vector) == len(sm.students)
            assert not np.all(np.isnan(result.iwf_vector)), f"{name} produced all-NaN"

    def test_convergence_metadata_present(self):
        """PeerRank and PeerHITS return convergence metadata."""
        _, _, sm = _find_team("ExquisiTech", "*2024*Session 4*")

        for model_name in ["peerrank", "peerhits"]:
            result = MODELS[model_name](sm)
            assert result.iterations is not None
            assert result.converged is not None
            assert result.converged is True
            assert result.iterations >= 1

    def test_rank_reversals_computed(self):
        """Rank reversals are computable for all advanced models."""
        _, _, sm = _find_team("ExquisiTech", "*2024*Session 4*")
        baseline_result = baseline_average(sm)

        for adv_name in ADVANCED_MODELS:
            adv_result = MODELS[adv_name](sm)
            summary = compute_rank_reversals(baseline_result, adv_result, delta_iwf=1.5)

            assert isinstance(summary, RankReversalSummary)
            assert summary.all_pair_count == len(sm.students) * (len(sm.students) - 1) // 2
            assert summary.reversal_count <= summary.eligible_pair_count

    def test_bar_chart_renders(self):
        """Plotly grouped bar chart can be generated for Team 11."""
        _, key, sm = _find_team("ExquisiTech", "*2024*Session 4*")
        student_names = [s.name for s in sm.students]

        fig = go.Figure()
        for name, fn in MODELS.items():
            result = fn(sm)
            values = [float(result.iwf_vector[s.index]) for s in sm.students]
            fig.add_trace(go.Bar(name=name, x=student_names, y=values))

        fig.update_layout(barmode="group")

        assert len(fig.data) == len(MODELS)
        assert fig.layout.barmode == "group"

    def test_html_export(self, tmp_path):
        """Chart can be exported as standalone HTML."""
        _, _, sm = _find_team("ExquisiTech", "*2024*Session 4*")

        fig = go.Figure()
        for name, fn in MODELS.items():
            result = fn(sm)
            values = [float(result.iwf_vector[s.index]) for s in sm.students]
            fig.add_trace(go.Bar(name=name, x=[s.name for s in sm.students], y=values))

        html_path = tmp_path / "test_export.html"
        fig.write_html(str(html_path), full_html=True, include_plotlyjs=True)

        assert html_path.exists()
        content = html_path.read_text()
        assert "plotly" in content.lower()
        assert len(content) > 1000  # Sanity: not an empty file
