"""Dash web app for peer-assessment analysis dashboard.

Run with:
    python3 -m src.visualization.app

Opens a local server at http://127.0.0.1:8050 with:
  - Force-layout graph visualisation
  - Grouped bar chart comparing IWFs across models
  - Color-coded results table
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import dash
from dash import dcc, html, dash_table
from dash.dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output

from src.models.baseline import baseline_average
from src.models.peerrank import peerrank
from src.models.webpa import webpa
from src.models.peerhits import peerhits
from src.parsing.parser import parse_session
from src.visualization.force_layout import force_layout


DATA_DIR = Path("data")

MODELS = {
    "baseline": baseline_average,
    "peerrank": peerrank,
    "webpa": webpa,
    "peerhits": peerhits,
}

MODEL_COLORS = {
    "baseline": "#636EFA",
    "peerrank": "#EF553B",
    "webpa": "#00CC96",
    "peerhits": "#AB63FA",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _discover_csvs() -> list[Path]:
    return sorted(DATA_DIR.glob("*.csv"))


def _load_matrices(csv_path: Path) -> dict:
    return parse_session(csv_path)


def _run_models(score_matrix) -> dict[str, dict]:
    """Run all models on a ScoreMatrix; return {model_name: {student_name: iwf}}."""
    results = {}
    for name, fn in MODELS.items():
        try:
            result = fn(score_matrix)
            results[name] = {
                s.name: round(float(result.iwf_vector[s.index]), 3)
                for s in score_matrix.students
            }
        except ValueError:
            results[name] = {s.name: None for s in score_matrix.students}
    return results


def _iwf_color(value: float) -> str:
    """Return a background color for an IWF cell (red < 8, yellow ~10, green > 12)."""
    if value is None:
        return "white"
    if value <= 7.0:
        return "rgba(215, 48, 39, 0.3)"
    elif value <= 8.5:
        return "rgba(253, 174, 97, 0.3)"
    elif value <= 11.5:
        return "rgba(255, 255, 191, 0.3)"
    elif value <= 13.0:
        return "rgba(166, 217, 106, 0.3)"
    else:
        return "rgba(26, 150, 65, 0.3)"


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = dash.Dash(__name__, title="Peer Assessment Dashboard")

csv_files = _discover_csvs()
if not csv_files:
    print(f"No CSV files found in {DATA_DIR}/. Add CSV files and try again.", file=sys.stderr)
    sys.exit(1)

_initial_matrices = _load_matrices(csv_files[0])
_initial_keys = sorted(_initial_matrices.keys())
_initial_teams = sorted({k[0] for k in _initial_keys})
_initial_questions = sorted({k[1] for k in _initial_keys})

app.layout = html.Div(
    style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1400px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H2("Peer Assessment Dashboard", style={"marginBottom": "5px"}),
        html.P(
            "Compare IWF models side by side with force-layout graphs.",
            style={"color": "#666", "marginTop": "0"},
        ),

        # --- Dropdowns ---
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap", "marginBottom": "20px"},
            children=[
                html.Div([
                    html.Label("CSV File", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="csv-dropdown",
                        options=[{"label": p.name, "value": str(p)} for p in csv_files],
                        value=str(csv_files[0]),
                        clearable=False,
                        style={"width": "420px"},
                    ),
                ]),
                html.Div([
                    html.Label("Team", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="team-dropdown",
                        options=[{"label": t, "value": t} for t in _initial_teams],
                        value=_initial_teams[0],
                        clearable=False,
                        style={"width": "300px"},
                    ),
                ]),
                html.Div([
                    html.Label("Question", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="question-dropdown",
                        options=[{"label": q, "value": q} for q in _initial_questions],
                        value=_initial_questions[0],
                        clearable=False,
                        style={"width": "200px"},
                    ),
                ]),
            ],
        ),

        # --- Two-column layout: graph + bar chart ---
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "20px"},
            children=[
                html.Div([
                    html.H4("Force-Layout Graph", style={"marginBottom": "5px"}),
                    dcc.Loading(
                        dcc.Graph(id="force-graph", style={"height": "550px"}),
                        type="circle",
                    ),
                ]),
                html.Div([
                    html.H4("IWF Model Comparison", style={"marginBottom": "5px"}),
                    dcc.Loading(
                        dcc.Graph(id="bar-chart", style={"height": "550px"}),
                        type="circle",
                    ),
                ]),
            ],
        ),

        # --- Results table ---
        html.Div([
            html.H4("Detailed Results", style={"marginBottom": "10px"}),
            html.Div(id="results-table"),
        ]),

        dcc.Store(id="matrices-store"),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

_matrices_cache: dict[str, dict] = {}


def _get_matrices(csv_path_str: str) -> dict:
    if csv_path_str not in _matrices_cache:
        _matrices_cache[csv_path_str] = _load_matrices(Path(csv_path_str))
    return _matrices_cache[csv_path_str]


@app.callback(
    Output("team-dropdown", "options"),
    Output("team-dropdown", "value"),
    Output("question-dropdown", "options"),
    Output("question-dropdown", "value"),
    Input("csv-dropdown", "value"),
)
def update_dropdowns_on_csv_change(csv_path: str):
    """When CSV changes, refresh team and question dropdowns."""
    matrices = _get_matrices(csv_path)
    keys = sorted(matrices.keys())
    teams = sorted({k[0] for k in keys})
    questions = sorted({k[1] for k in keys})

    team_opts = [{"label": t, "value": t} for t in teams]
    question_opts = [{"label": q, "value": q} for q in questions]
    return team_opts, teams[0], question_opts, questions[0]


@app.callback(
    Output("force-graph", "figure"),
    Output("bar-chart", "figure"),
    Output("results-table", "children"),
    Input("csv-dropdown", "value"),
    Input("team-dropdown", "value"),
    Input("question-dropdown", "value"),
)
def update_dashboard(csv_path: str, team: str, question: str):
    """Update all dashboard components for the selected team/question."""
    matrices = _get_matrices(csv_path)
    key = (team, question)

    empty_fig = go.Figure().update_layout(
        title="No data for this team/question combination",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )

    if key not in matrices:
        return empty_fig, empty_fig, html.P("No data available.")

    sm = matrices[key]
    model_results = _run_models(sm)
    student_names = [s.name for s in sm.students]

    # --- Force layout graph ---
    force_fig = force_layout(sm)

    # --- Grouped bar chart ---
    bar_fig = go.Figure()
    for model_name in MODELS:
        iwfs = model_results.get(model_name, {})
        values = [iwfs.get(name, 0) or 0 for name in student_names]
        bar_fig.add_trace(go.Bar(
            name=model_name.capitalize(),
            x=student_names,
            y=values,
            marker_color=MODEL_COLORS[model_name],
        ))

    bar_fig.add_hline(y=10.0, line_dash="dash", line_color="gray", opacity=0.5,
                      annotation_text="Mean (10.0)", annotation_position="top left")
    bar_fig.update_layout(
        barmode="group",
        title=dict(text=f"{team} — {question}", x=0.5),
        xaxis_title="Student",
        yaxis_title="IWF",
        yaxis=dict(range=[0, max(
            max((v or 0) for v in model_results.get(m, {}).values()) if model_results.get(m) else 10
            for m in MODELS
        ) * 1.15]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=60, b=80),
    )

    # --- Color-coded table ---
    table_data = []
    for name in student_names:
        row = {"Student": name}
        for model_name in MODELS:
            iwfs = model_results.get(model_name, {})
            row[model_name.capitalize()] = iwfs.get(name)
        # Compute max deviation from 10 across models
        vals = [row[m.capitalize()] for m in MODELS if row.get(m.capitalize()) is not None]
        row["Max Δ"] = round(max(abs(v - 10.0) for v in vals), 2) if vals else 0
        table_data.append(row)

    columns = [{"name": "Student", "id": "Student"}]
    for m in MODELS:
        columns.append({"name": m.capitalize(), "id": m.capitalize(), "type": "numeric",
                         "format": Format(precision=3, scheme=Scheme.fixed)})
    columns.append({"name": "Max Δ", "id": "Max Δ", "type": "numeric",
                     "format": Format(precision=2, scheme=Scheme.fixed)})

    # Build conditional styles for color coding
    style_conditions = []
    for model_name in MODELS:
        col_id = model_name.capitalize()
        for threshold, color in [
            (7.0, "rgba(215, 48, 39, 0.25)"),
            (8.5, "rgba(253, 174, 97, 0.25)"),
            (11.5, "rgba(255, 255, 191, 0.3)"),
            (13.0, "rgba(166, 217, 106, 0.25)"),
        ]:
            if threshold == 7.0:
                style_conditions.append({
                    "if": {"column_id": col_id, "filter_query": f"{{{col_id}}} <= {threshold}"},
                    "backgroundColor": color, "fontWeight": "bold",
                })
            elif threshold == 8.5:
                style_conditions.append({
                    "if": {"column_id": col_id, "filter_query": f"{{{col_id}}} > 7.0 && {{{col_id}}} <= {threshold}"},
                    "backgroundColor": color,
                })
            elif threshold == 11.5:
                style_conditions.append({
                    "if": {"column_id": col_id, "filter_query": f"{{{col_id}}} > 8.5 && {{{col_id}}} <= {threshold}"},
                    "backgroundColor": color,
                })
            elif threshold == 13.0:
                style_conditions.append({
                    "if": {"column_id": col_id, "filter_query": f"{{{col_id}}} > 11.5 && {{{col_id}}} <= {threshold}"},
                    "backgroundColor": color,
                })
        # Dark green for > 13
        style_conditions.append({
            "if": {"column_id": col_id, "filter_query": f"{{{col_id}}} > 13.0"},
            "backgroundColor": "rgba(26, 150, 65, 0.25)", "fontWeight": "bold",
        })

    # Highlight high Max Δ rows
    style_conditions.append({
        "if": {"column_id": "Max Δ", "filter_query": "{Max Δ} >= 3"},
        "backgroundColor": "rgba(215, 48, 39, 0.2)", "fontWeight": "bold",
    })

    table = dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                     "fontFamily": "system-ui, sans-serif"},
        style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold", "fontSize": "13px"},
        style_data_conditional=style_conditions,
        sort_action="native",
        sort_by=[{"column_id": "Max Δ", "direction": "desc"}],
    )

    return force_fig, bar_fig, table


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n  Peer Assessment Dashboard")
    print("  Open http://127.0.0.1:8050 in your browser\n")
    app.run(debug=True)
