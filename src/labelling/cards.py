"""Blinded rater cards for the hand-labelled anchor set (Task 2).

One page per sampled team in a single self-contained PDF, per rubric §2. Each
card shows only evidence the model does NOT use as its output — the raw rating
matrices, the team graph, and per-member in-degree — so the resulting labels
stay independent of Δ / atypicality.

Blinding (rubric §2, hard requirements):
  * Members anonymised to A–F, CONSISTENT across a team's three questions (same
    person = same letter), assigned by sorted email.
  * Card ids anonymised (card_01…), order randomised (seeded). The id->team map
    lives in card_key.csv, kept separate from the PDF.
  * Cards show NO archetype, flag, Δ, atypicality, degeneracy cause, or team
    name — only member letters and the ratings themselves.

Also emits the blank entry sheet raters fill in. Journals are not yet delivered
(handoff 5); a placeholder box reserves the slot so cards need not be regenerated.

Run:
    python3 -m src.labelling.cards

Outputs (output/labelling/):
    cards.pdf                  40 one-page cards, blinded, randomised order
    card_key.csv               card_id -> team (the secret key; never hand over)
    label_sheet_template.csv   blank sheet for a rater to fill in
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from src.parsing.parser import parse_session_with_diagnostics
from src.labelling.constants import QUESTIONS, VALID_LABELS

OUT = Path("output/labelling")
SEED = 42
LETTERS = "ABCDEF"


def _load_sessions(csv_paths: set[str]) -> dict[str, dict]:
    """Parse each needed session once; return {csv_path: {(team,q): ScoreMatrix}}."""
    return {p: parse_session_with_diagnostics(p)[0] for p in csv_paths}


def _letter_map(matrices: list) -> dict[str, str]:
    """Stable email->letter map across a team's matrices (sorted by email)."""
    emails = sorted({s.email for sm in matrices for s in sm.students})
    return {e: LETTERS[i] for i, e in enumerate(emails)}


def _heatmap(ax, sm, lmap: dict[str, str], title: str) -> None:
    """Rows = recipient, cols = giver; diagonal blanked; NaN = grey."""
    n = len(sm.students)
    labels = [lmap[s.email] for s in sm.students]
    A = sm.matrix.astype(float).copy()
    np.fill_diagonal(A, np.nan)
    im = ax.imshow(A, cmap="viridis", aspect="equal")
    ax.set_xticks(range(n)); ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("giver (column)", fontsize=7)
    ax.set_ylabel("recipient (row)", fontsize=7)
    ax.set_title(title, fontsize=9)
    for i in range(n):
        for j in range(n):
            v = A[i, j]
            if np.isnan(v):
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                           color="lightgrey"))
            else:
                ax.text(j, i, f"{v:g}", ha="center", va="center",
                        fontsize=7, color="white")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def _graph(ax, sm, lmap: dict[str, str], question: str) -> None:
    """Directed above-average edges only (giver -> recipient), static layout."""
    n = len(sm.students)
    labels = {i: lmap[sm.students[i].email] for i in range(n)}
    A = sm.matrix.astype(float)
    finite = A[np.isfinite(A)]
    thr = float(np.mean(finite)) if finite.size else 0.0
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for i in range(n):        # recipient
        for j in range(n):    # giver
            if i != j and np.isfinite(A[i, j]) and A[i, j] > thr:
                G.add_edge(j, i, weight=A[i, j])
    pos = nx.circular_layout(G)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#cfe3ff", node_size=650)
    nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=9)
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowsize=12,
                           edge_color="#4a4a4a", connectionstyle="arc3,rad=0.08")
    ax.set_title(f"above-average ratings, {question} (giver → recipient)",
                 fontsize=9)
    ax.axis("off")


def _indegree(ax, matrices: list, lmap: dict[str, str]) -> None:
    """Per-member total received (in-degree), grouped bar per question."""
    letters = sorted(set(lmap.values()))
    x = np.arange(len(letters))
    width = 0.8 / max(1, len(matrices))
    for k, (q, sm) in enumerate(matrices):
        by_letter = {lmap[s.email]: i for i, s in enumerate(sm.students)}
        A = sm.matrix.astype(float)
        recv = np.nansum(A, axis=1)  # row sum = total received
        vals = [recv[by_letter[l]] if l in by_letter else 0.0 for l in letters]
        ax.bar(x + k * width, vals, width, label=q)
    ax.set_xticks(x + width * (len(matrices) - 1) / 2)
    ax.set_xticklabels(letters, fontsize=8)
    ax.set_ylabel("total received", fontsize=7)
    ax.set_title("in-degree per member", fontsize=9)
    ax.legend(fontsize=6, loc="upper right")


def _render_card(pdf: PdfPages, card_id: str, sm_by_q: dict) -> None:
    matrices = [(q, sm_by_q[q]) for q in QUESTIONS if q in sm_by_q]
    lmap = _letter_map([sm for _, sm in matrices])

    fig = plt.figure(figsize=(11.7, 8.3))  # A4 landscape
    fig.suptitle(f"{card_id}", fontsize=14, x=0.06, ha="left")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.1, 1.0], hspace=0.45, wspace=0.35)

    for k, (q, sm) in enumerate(matrices):
        _heatmap(fig.add_subplot(gs[0, k]), sm, lmap, q)

    _graph(fig.add_subplot(gs[1, 0]), matrices[0][1], lmap, matrices[0][0])
    _indegree(fig.add_subplot(gs[1, 1]), matrices, lmap)

    box = fig.add_subplot(gs[1, 2]); box.axis("off")
    box.add_patch(plt.Rectangle((0.02, 0.05), 0.96, 0.9, fill=False,
                                linestyle="--", edgecolor="grey"))
    box.text(0.5, 0.5, "Journal excerpts:\npending", ha="center", va="center",
             fontsize=11, color="grey")

    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(OUT / "labelling_sample.csv")

    # seeded randomised card order -> card_NN
    order = sample.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    order["card_id"] = [f"card_{i + 1:02d}" for i in range(len(order))]

    sessions = _load_sessions(set(order["csv_path"]))

    with PdfPages(OUT / "cards.pdf") as pdf:
        for _, r in order.iterrows():
            mats = sessions[r["csv_path"]]
            sm_by_q = {q: mats[(r["team_name"], q)]
                       for q in QUESTIONS if (r["team_name"], q) in mats}
            _render_card(pdf, r["card_id"], sm_by_q)

    # secret key (card -> team). Kept separate; NEVER handed to a rater.
    order[["card_id", "team_id", "csv_path", "team_name"]].to_csv(
        OUT / "card_key.csv", index=False)

    # blank entry sheet: one primary per team + optional per-question override
    template = pd.DataFrame({"card_id": order["card_id"]})
    template["primary_label"] = ""
    template["secondary_label"] = ""
    template["confidence"] = ""          # H / M / L
    for q in QUESTIONS:                  # fill ONLY if the team's questions disagree
        template[f"primary_{q.replace(' ', '_')}"] = ""
    template["notes"] = ""
    template.to_csv(OUT / "label_sheet_template.csv", index=False)

    print(f"Wrote {len(order)} cards -> output/labelling/cards.pdf")
    print("Wrote card_key.csv  [secret — do NOT hand to raters]")
    print("Wrote label_sheet_template.csv")
    print(f"Valid primary/secondary labels: {', '.join(VALID_LABELS)}")


if __name__ == "__main__":
    main()
