"""Interactive force-directed graph visualisation of team peer scores.

Renders a ScoreMatrix as a Plotly directed force-layout graph where:
  - Node size  = weighted in-degree (total score received)
  - Node color = IWF (if ModelResult provided), else weighted in-degree
  - Edge thickness = proportional to score
  - Edge color = RdYlGn gradient (low → high score)
  - Direction  = midpoint triangle markers pointing toward recipient
  - Hover      = rich detail on nodes and edges

References:
    Fruchterman, T.M.J. and Reingold, E.M. (1991). doi:10.1002/spe.4380211102
"""

from __future__ import annotations

import math
from typing import Optional

import networkx as nx
import numpy as np
import plotly.graph_objects as go

from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix
from src.visualization.graph import build_team_graph

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

# Discrete RdYlGn stops matching plotly's built-in "RdYlGn" colourscale.
_RDYLGN: list[tuple[float, str]] = [
    (0.0, "rgb(215, 48, 39)"),
    (0.25, "rgb(253, 174, 97)"),
    (0.5, "rgb(255, 255, 191)"),
    (0.75, "rgb(166, 217, 106)"),
    (1.0, "rgb(26, 150, 65)"),
]


def _score_to_color(value: float, vmin: float, vmax: float) -> str:
    """Map a scalar *value* in [vmin, vmax] to an RdYlGn RGB string."""
    if vmax == vmin:
        return "rgb(255, 255, 191)"  # yellow (neutral) when no spread
    t = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    # Linearly interpolate between the two surrounding stops.
    for idx in range(len(_RDYLGN) - 1):
        t0, c0 = _RDYLGN[idx]
        t1, c1 = _RDYLGN[idx + 1]
        if t0 <= t <= t1:
            frac = (t - t0) / (t1 - t0)
            r0, g0, b0 = _parse_rgb(c0)
            r1, g1, b1 = _parse_rgb(c1)
            r = int(r0 + frac * (r1 - r0))
            g = int(g0 + frac * (g1 - g0))
            b = int(b0 + frac * (b1 - b0))
            return f"rgb({r}, {g}, {b})"
    return "rgb(26, 150, 65)"  # fallback: greenest stop


def _parse_rgb(s: str) -> tuple[int, int, int]:
    """Extract (r, g, b) ints from an 'rgb(r, g, b)' string."""
    inner = s.removeprefix("rgb(").removesuffix(")")
    parts = [int(p.strip()) for p in inner.split(",")]
    return parts[0], parts[1], parts[2]


# ---------------------------------------------------------------------------
# Layout and geometry helpers
# ---------------------------------------------------------------------------


def _midpoint_along_edge(
    x0: float, y0: float, x1: float, y1: float, t: float = 0.8,
) -> tuple[float, float]:
    """Return the point at fraction *t* from (x0, y0) toward (x1, y1)."""
    return x0 + t * (x1 - x0), y0 + t * (y1 - y0)


def _angle_degrees(x0: float, y0: float, x1: float, y1: float) -> float:
    """Angle in degrees from (x0,y0) to (x1,y1), measured from the +x axis."""
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def force_layout(
    score_matrix: ScoreMatrix,
    model_result: Optional[ModelResult] = None,
    *,
    seed: int = 42,
    layout_iterations: int = 50,
) -> go.Figure:
    """Render an interactive force-directed graph for one team.

    Args:
        score_matrix: N×N peer-assessment matrix for a single team/question.
        model_result: Optional IWF result for node colouring.  When *None*,
            nodes are coloured by weighted in-degree instead.
        seed: Random seed for reproducible layout.
        layout_iterations: Fruchterman–Reingold iterations.

    Returns:
        A Plotly ``Figure`` object.  Call ``.show()`` to open in a browser
        or ``.write_html(path)`` to save.
    """
    G = build_team_graph(score_matrix)
    n = G.number_of_nodes()

    # --- Layout ----------------------------------------------------------
    pos = nx.spring_layout(
        G, weight="weight", seed=seed, iterations=layout_iterations,
    )

    # --- Per-node metrics ------------------------------------------------
    # Weighted in-degree = total score received (excluding self)
    in_deg = dict(G.in_degree(weight="weight"))

    # Determine node-colour values
    if model_result is not None:
        color_values = {
            s.index: float(model_result.iwf_vector[s.index])
            for s in score_matrix.students
        }
        color_label = "IWF"
        color_center = 10.0
    else:
        color_values = {nid: in_deg.get(nid, 0.0) for nid in G.nodes}
        color_label = "In-degree"
        color_center = np.mean(list(color_values.values())) if color_values else 0.0

    # --- Per-edge metrics ------------------------------------------------
    weights = [d["weight"] for _, _, d in G.edges(data=True)]
    w_min = min(weights) if weights else 0.0
    w_max = max(weights) if weights else 1.0

    # --- Build edge traces (one per edge for individual styling) ---------
    edge_traces: list[go.Scatter] = []
    arrow_x: list[float | None] = []
    arrow_y: list[float | None] = []
    arrow_colors: list[str] = []
    arrow_angles: list[float] = []

    for u, v, data in G.edges(data=True):
        w = data["weight"]
        x0, y0 = pos[u]
        x1, y1 = pos[v]

        # Thickness: scale linearly between 1 and 8 px
        thickness = 1.0 + 7.0 * ((w - w_min) / (w_max - w_min)) if w_max > w_min else 4.0
        # Opacity: 0.3 to 1.0
        opacity = 0.3 + 0.7 * ((w - w_min) / (w_max - w_min)) if w_max > w_min else 0.65
        color = _score_to_color(w, w_min, w_max)

        giver_name = G.nodes[u].get("name", str(u))
        recipient_name = G.nodes[v].get("name", str(v))

        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode="lines",
            line=dict(width=thickness, color=color),
            opacity=opacity,
            hoverinfo="text",
            hovertext=f"{giver_name} → {recipient_name}: {w:.1f} pts",
            showlegend=False,
        ))

        # Midpoint arrow marker
        mx, my = _midpoint_along_edge(x0, y0, x1, y1, t=0.75)
        arrow_x.append(mx)
        arrow_y.append(my)
        arrow_colors.append(color)
        arrow_angles.append(_angle_degrees(x0, y0, x1, y1))

    # Arrow marker trace (triangles rotated to point along edge direction)
    arrow_trace = go.Scatter(
        x=arrow_x,
        y=arrow_y,
        mode="markers",
        marker=dict(
            symbol=["triangle-up"] * len(arrow_x),
            size=8,
            color=arrow_colors,
            angle=[-a + 90 for a in arrow_angles],  # plotly angle convention
            line=dict(width=0),
        ),
        hoverinfo="skip",
        showlegend=False,
    )

    # --- Node trace ------------------------------------------------------
    node_x = [pos[nid][0] for nid in G.nodes]
    node_y = [pos[nid][1] for nid in G.nodes]

    # Size: scale weighted in-degree to marker size range [20, 60]
    in_deg_vals = [in_deg.get(nid, 0.0) for nid in G.nodes]
    id_min = min(in_deg_vals) if in_deg_vals else 0.0
    id_max = max(in_deg_vals) if in_deg_vals else 1.0
    if id_max == id_min:
        node_sizes = [40.0] * n
    else:
        node_sizes = [
            20 + 40 * ((v - id_min) / (id_max - id_min)) for v in in_deg_vals
        ]

    # Color: RdYlGn centred on color_center
    c_vals = [color_values.get(nid, 0.0) for nid in G.nodes]
    # Symmetric range around center so the midpoint maps to yellow
    c_max_dev = max(abs(cv - color_center) for cv in c_vals) if c_vals else 1.0
    c_max_dev = c_max_dev or 1.0  # avoid zero-division
    node_colors = [
        _score_to_color(cv, color_center - c_max_dev, color_center + c_max_dev)
        for cv in c_vals
    ]

    # Hover text
    node_hover: list[str] = []
    total_given = dict(G.out_degree(weight="weight"))
    for nid in G.nodes:
        name = G.nodes[nid].get("name", str(nid))
        received = in_deg.get(nid, 0.0)
        given = total_given.get(nid, 0.0)
        parts = [
            f"<b>{name}</b>",
            f"Scores received: {received:.1f}",
            f"Scores given: {given:.1f}",
        ]
        if model_result is not None:
            iwf = color_values.get(nid, 0.0)
            parts.append(f"IWF: {iwf:.3f}")
        node_hover.append("<br>".join(parts))

    node_labels = [G.nodes[nid].get("name", str(nid)) for nid in G.nodes]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=1.5, color="white"),
        ),
        text=node_labels,
        textposition="top center",
        textfont=dict(size=11),
        hoverinfo="text",
        hovertext=node_hover,
        showlegend=False,
    )

    # --- Assemble figure -------------------------------------------------
    title = f"Team {score_matrix.team_name} — {score_matrix.question_label}"

    fig = go.Figure(
        data=[*edge_traces, arrow_trace, node_trace],
        layout=go.Layout(
            title=dict(text=title, x=0.5),
            showlegend=False,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, visible=False),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=20),
        ),
    )

    return fig
