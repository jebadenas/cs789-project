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
from src.models.types import ModelResult
from src.evaluation.rank_reversal import compute_rank_reversals
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

ADVANCED_MODELS = ["peerrank", "webpa", "peerhits"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _discover_csvs() -> list[Path]:
    return sorted(DATA_DIR.glob("*.csv"))


def _load_matrices(csv_path: Path) -> dict:
    return parse_session(csv_path)


def _run_models(score_matrix) -> dict[str, dict]:
    """Run all models on a ScoreMatrix.

    Returns {model_name: {"iwfs": {name: value}, "result": ModelResult | None, "error": str | None}}.
    """
    results = {}
    for name, fn in MODELS.items():
        try:
            result = fn(score_matrix)
            iwfs = {
                s.name: round(float(result.iwf_vector[s.index]), 3)
                for s in score_matrix.students
            }
            results[name] = {"iwfs": iwfs, "result": result, "error": None}
        except ValueError as e:
            results[name] = {
                "iwfs": {s.name: None for s in score_matrix.students},
                "result": None,
                "error": str(e),
            }
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

        # --- Rank reversal summary ---
        html.Div([
            html.H4("Rank Reversals (vs Baseline)", style={"marginBottom": "10px", "marginTop": "20px"}),
            html.P(
                "Pairs where the baseline ranking is reversed by an advanced model "
                "(δ = 1.5 IWF points on baseline side).",
                style={"color": "#666", "fontSize": "13px", "marginTop": "0"},
            ),
            html.Div(id="reversal-table"),
        ]),

        # --- Export buttons ---
        html.Div(
            style={"marginTop": "30px", "marginBottom": "20px", "display": "flex", "gap": "10px"},
            children=[
                html.Button("Export Bar Chart as HTML", id="export-bar-btn",
                            style={"padding": "8px 16px", "cursor": "pointer"}),
                html.Button("Export Force Graph as HTML", id="export-force-btn",
                            style={"padding": "8px 16px", "cursor": "pointer"}),
                html.Button("Export Full Dashboard as HTML", id="export-full-btn",
                            style={"padding": "8px 16px", "cursor": "pointer"}),
            ],
        ),
        html.Div(id="export-status", style={"color": "#666", "fontSize": "13px"}),
        dcc.Download(id="download-html"),

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
    Output("reversal-table", "children"),
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
        return empty_fig, empty_fig, html.P("No data available."), html.P("No data available.")

    sm = matrices[key]
    model_results = _run_models(sm)
    student_names = [s.name for s in sm.students]

    # --- Force layout graph ---
    force_fig = force_layout(sm)

    # --- Grouped bar chart ---
    bar_fig = go.Figure()
    for model_name in MODELS:
        iwfs = model_results.get(model_name, {}).get("iwfs", {})
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
            max((v or 0) for v in model_results.get(m, {}).get("iwfs", {}).values())
            if model_results.get(m, {}).get("iwfs") else 10
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
            iwfs = model_results.get(model_name, {}).get("iwfs", {})
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

    # Add convergence row for iterative models
    convergence_row = {"Student": "⚙ Convergence"}
    for model_name in MODELS:
        mr = model_results.get(model_name, {}).get("result")
        if mr and mr.iterations is not None:
            convergence_row[model_name.capitalize()] = None  # numeric column; show in tooltip
        else:
            convergence_row[model_name.capitalize()] = None
    convergence_row["Max Δ"] = None

    # Build convergence info line
    conv_parts = []
    for model_name in MODELS:
        mr = model_results.get(model_name, {}).get("result")
        err = model_results.get(model_name, {}).get("error")
        if err:
            conv_parts.append(f"{model_name.capitalize()}: ERROR — {err}")
        elif mr and mr.iterations is not None:
            status = "✓" if mr.converged else "✗"
            conv_parts.append(f"{model_name.capitalize()}: {mr.iterations} iters {status}")

    convergence_info = html.P(
        " · ".join(conv_parts) if conv_parts else "No iterative models ran.",
        style={"color": "#888", "fontSize": "12px", "marginTop": "6px"},
    ) if conv_parts else None

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

    results_section = html.Div([table, convergence_info] if convergence_info else [table])

    # --- Rank reversal summary ---
    baseline_result = model_results.get("baseline", {}).get("result")
    reversal_rows = []

    if baseline_result:
        for adv_name in ADVANCED_MODELS:
            adv_result = model_results.get(adv_name, {}).get("result")
            if adv_result is None:
                continue
            summary = compute_rank_reversals(baseline_result, adv_result, delta_iwf=1.5)
            for rev in summary.reversals:
                reversal_rows.append({
                    "Model": adv_name.capitalize(),
                    "Student A (↑ baseline)": rev.student_a,
                    "Student B (↓ baseline)": rev.student_b,
                    "Baseline Gap": round(rev.baseline_diff, 2),
                    "Advanced Gap": round(rev.advanced_diff, 2),
                    "Magnitude": round(rev.magnitude, 2),
                })

    if reversal_rows:
        rev_columns = [
            {"name": c, "id": c, "type": "numeric" if c in ("Baseline Gap", "Advanced Gap", "Magnitude") else "text"}
            for c in ["Model", "Student A (↑ baseline)", "Student B (↓ baseline)",
                       "Baseline Gap", "Advanced Gap", "Magnitude"]
        ]
        reversal_section = dash_table.DataTable(
            data=reversal_rows,
            columns=rev_columns,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "padding": "6px", "fontSize": "13px",
                         "fontFamily": "system-ui, sans-serif"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold", "fontSize": "13px"},
            style_data_conditional=[{
                "if": {"column_id": "Advanced Gap"},
                "backgroundColor": "rgba(215, 48, 39, 0.15)",
            }],
            sort_action="native",
            sort_by=[{"column_id": "Magnitude", "direction": "desc"}],
        )
    else:
        reversal_section = html.P(
            "No rank reversals detected (δ = 1.5 IWF points).",
            style={"color": "#888", "fontSize": "13px"},
        )

    # Store figures for export callbacks
    _figure_cache["force"] = force_fig
    _figure_cache["bar"] = bar_fig

    return force_fig, bar_fig, results_section, reversal_section


# ---------------------------------------------------------------------------
# Figure cache for export
# ---------------------------------------------------------------------------

_figure_cache: dict[str, go.Figure] = {}


# ---------------------------------------------------------------------------
# Export callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("download-html", "data"),
    Output("export-status", "children"),
    Input("export-bar-btn", "n_clicks"),
    Input("export-force-btn", "n_clicks"),
    Input("export-full-btn", "n_clicks"),
    prevent_initial_call=True,
)
def export_html(bar_clicks, force_clicks, full_clicks):
    """Export chart(s) as standalone HTML file."""
    import io
    from dash import ctx

    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update, dash.no_update

    if triggered == "export-bar-btn" and "bar" in _figure_cache:
        content = _figure_cache["bar"].to_html(full_html=True, include_plotlyjs=True)
        return dict(content=content, filename="bar_chart.html"), "✓ Bar chart exported"
    elif triggered == "export-force-btn" and "force" in _figure_cache:
        content = _figure_cache["force"].to_html(full_html=True, include_plotlyjs=True)
        return dict(content=content, filename="force_graph.html"), "✓ Force graph exported"
    elif triggered == "export-full-btn":
        # Combine both charts into one HTML page
        parts = ["<html><head><title>Peer Assessment Dashboard Export</title></head><body>"]
        parts.append("<h1>Peer Assessment Dashboard</h1>")
        if "bar" in _figure_cache:
            parts.append("<h2>IWF Model Comparison</h2>")
            parts.append(_figure_cache["bar"].to_html(full_html=False, include_plotlyjs="cdn"))
        if "force" in _figure_cache:
            parts.append("<h2>Force-Layout Graph</h2>")
            parts.append(_figure_cache["force"].to_html(full_html=False, include_plotlyjs=False))
        parts.append("</body></html>")
        content = "\n".join(parts)
        return dict(content=content, filename="dashboard_export.html"), "✓ Full dashboard exported"

    return dash.no_update, "No chart data available — select a team first."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n  Peer Assessment Dashboard")
    print("  Open http://127.0.0.1:8050 in your browser\n")
    app.run(debug=True)
