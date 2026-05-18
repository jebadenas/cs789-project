"""PCA and UMAP scatter visualisations for team-dynamics archetype analysis.

Each point is a team-matrix, coloured by Δ (mean cross-model IWF disagreement).
Archetype positions are projected into the same 2-D space and marked with stars.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def make_pca_plot(
    pca_coords: np.ndarray,
    delta_vals: np.ndarray,
    labels: list[str],
    pca_var: list[float],
    arch_scaled: np.ndarray,
    pca,
) -> go.Figure:
    """Interactive PCA scatter coloured by model disagreement Δ.

    Args:
        pca_coords: (n, 2) PCA coordinates of teams.
        delta_vals: (n,) per-team Δ values.
        labels: hover labels for each team.
        pca_var: explained variance ratios [PC1, PC2].
        arch_scaled: (k, n_features) archetype vectors in scaled space.
        pca: fitted sklearn PCA object.
    """
    arch_pca = pca.transform(arch_scaled)
    return _scatter_plot(
        coords=pca_coords,
        delta_vals=delta_vals,
        labels=labels,
        arch_coords=arch_pca,
        xaxis_title=f"PC1 ({pca_var[0]:.1%} variance)",
        yaxis_title=f"PC2 ({pca_var[1]:.1%} variance)",
        title=f"Team-space PCA  (PC1: {pca_var[0]:.1%}, PC2: {pca_var[1]:.1%})",
    )


def make_umap_plot(
    umap_coords: np.ndarray,
    delta_vals: np.ndarray,
    labels: list[str],
    arch_scaled: np.ndarray,
    reducer,
) -> go.Figure:
    """Interactive UMAP scatter coloured by model disagreement Δ.

    Args:
        umap_coords: (n, 2) UMAP coordinates of teams.
        delta_vals: (n,) per-team Δ values.
        labels: hover labels for each team.
        arch_scaled: (k, n_features) archetype vectors in scaled space.
        reducer: fitted UMAP object.
    """
    try:
        arch_umap = reducer.transform(arch_scaled)
    except Exception:
        arch_umap = np.full((arch_scaled.shape[0], 2), np.nan)

    return _scatter_plot(
        coords=umap_coords,
        delta_vals=delta_vals,
        labels=labels,
        arch_coords=arch_umap,
        xaxis_title="UMAP-1",
        yaxis_title="UMAP-2",
        title="Team-space UMAP",
    )


def make_rss_plot(k_values: list[int], rss_values: list[float], stabilities: list[float], best_k: int) -> go.Figure:
    """RSS elbow and bootstrap stability chart for archetype count selection."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=k_values,
            y=rss_values,
            mode="lines+markers",
            name="RSS",
            line=dict(color="#E45756", width=2),
            marker=dict(size=8),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=k_values,
            y=stabilities,
            mode="lines+markers",
            name="Bootstrap stability",
            line=dict(color="#4C78A8", width=2, dash="dash"),
            marker=dict(size=8),
        ),
        secondary_y=True,
    )

    fig.add_vline(x=best_k, line_dash="dot", line_color="grey", annotation_text=f"best k={best_k}")

    fig.update_layout(
        title="Archetype count selection: RSS elbow + stability",
        xaxis_title="k (number of archetypes)",
        template="plotly_white",
        legend=dict(x=0.7, y=0.9),
    )
    fig.update_yaxes(title_text="RSS", secondary_y=False)
    fig.update_yaxes(title_text="Bootstrap stability", secondary_y=True, range=[0, 1])

    return fig


def _scatter_plot(
    coords: np.ndarray,
    delta_vals: np.ndarray,
    labels: list[str],
    arch_coords: np.ndarray,
    xaxis_title: str,
    yaxis_title: str,
    title: str,
) -> go.Figure:
    fig = go.Figure()

    delta_text = [f"{d:.3f}" for d in delta_vals]

    fig.add_trace(go.Scatter(
        x=coords[:, 0],
        y=coords[:, 1],
        mode="markers",
        marker=dict(
            color=delta_vals,
            colorscale="RdYlGn_r",
            showscale=True,
            colorbar=dict(title="Δ (model disagreement)"),
            size=9,
            opacity=0.82,
            line=dict(width=0.5, color="white"),
        ),
        text=[f"{lbl}<br>Δ={d}" for lbl, d in zip(labels, delta_text)],
        hovertemplate="%{text}<extra></extra>",
        name="Teams",
    ))

    k = arch_coords.shape[0]
    arch_colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2",
    ]
    for j in range(k):
        if np.any(np.isnan(arch_coords[j])):
            continue
        fig.add_trace(go.Scatter(
            x=[arch_coords[j, 0]],
            y=[arch_coords[j, 1]],
            mode="markers+text",
            marker=dict(
                size=18,
                symbol="star",
                color=arch_colors[j % len(arch_colors)],
                line=dict(width=1.5, color="black"),
            ),
            text=[f"A{j + 1}"],
            textposition="top center",
            textfont=dict(size=12, color="black"),
            name=f"Archetype {j + 1}",
        ))

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_white",
        legend=dict(itemsizing="constant"),
    )

    return fig
