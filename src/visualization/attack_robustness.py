"""Attack robustness charts (Phase 4).

Grouped bar chart: mean Attack Delta per model per attack type, with
Monte-Carlo error bars on the single-outlier attack. Smaller bars ⇒ more
robust. Standalone HTML export for the dissertation.
"""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from src.attacks.runner import AttackBatch
from src.batch_runner import MODELS

# Stable display order.
_ATTACK_ORDER = [
    "uniform-inflation",
    "zero-self-full",
    "zero-self-partial",
    "targeted-downvote",
    "single-outlier",
]
_MODEL_COLORS = {
    "baseline": "#E45756",
    "webpa": "#F58518",
    "peerrank-impute": "#4C78A8",
    "peerrank-exclude": "#72B7B2",
    "peerhits-impute": "#54A24B",
    "peerhits-exclude": "#B279A2",
}


def make_robustness_chart(
    agg: dict[tuple[str, str], dict],
    *,
    title: str,
) -> go.Figure:
    """Grouped bar of mean Attack Delta per model per attack.

    Args:
        agg: output of ``AttackBatch.aggregate(...)``.
        title: chart title (include the input source / n).
    """
    attacks = [a for a in _ATTACK_ORDER
               if any(k[0] == a for k in agg)]
    models = [m for m in MODELS if any(k[1] == m for k in agg)]

    fig = go.Figure()
    for model in models:
        ys, errs, has_err = [], [], False
        for attack in attacks:
            cell = agg.get((attack, model))
            ys.append(cell["mean_delta"] if cell else 0.0)
            e = cell.get("mc_std") if cell else None
            errs.append(e if e else 0.0)
            has_err = has_err or bool(e)
        fig.add_trace(go.Bar(
            name=model,
            x=attacks,
            y=ys,
            marker_color=_MODEL_COLORS.get(model),
            error_y=dict(
                type="data", array=errs, visible=has_err, thickness=1.2,
            ),
        ))

    fig.update_layout(
        title=title,
        barmode="group",
        xaxis_title="Attack vector",
        yaxis_title="Mean Attack Delta (lower = more robust)",
        template="plotly_white",
        legend=dict(title="Model"),
    )
    return fig


def export_charts(batch: AttackBatch, out_dir: Path) -> list[Path]:
    """Write real and synthetic robustness charts as standalone HTML.

    Returns the paths written (one per input source present).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    sources = [
        ("real", batch.real_matrix_count, "real matrices"),
        ("synthetic", batch.synthetic_team_count, "synthetic teams"),
    ]
    for source, count, noun in sources:
        if count == 0:
            continue
        agg = batch.aggregate(source=source)
        if not agg:
            continue
        fig = make_robustness_chart(
            agg,
            title=f"Attack robustness — {source} ({count} {noun})",
        )
        path = out_dir / f"attack_robustness_{source}.html"
        fig.write_html(str(path))
        written.append(path)

    return written
