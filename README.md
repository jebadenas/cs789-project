# cs789-project

Research project for COMPSCI 789 (2026 S1) — algorithmic peer-assessment grading engine.

Implements and compares multiple IWF (Individual Weighting Factor) models for peer-assessment data from COMPSCI 399, investigating manipulation resistance and grading fairness.

## Setup

```bash
pip3 install -r requirements.txt
```

## Usage

Place CSV files from COMPSCI 399 peer feedback sessions into `data/`.

**Run interactively** (pick from available files):
```bash
python3 -m src run
```

**Run against a specific file:**
```bash
python3 -m src run data/myfile.csv
```

**Filter by model or team:**
```bash
python3 -m src run data/myfile.csv --model peerrank-impute
python3 -m src run data/myfile.csv --model baseline --model peerrank-impute --team "Team 20"
```

**Override output path** (default: `output/<stem>_<timestamp>.csv`):
```bash
python3 -m src run data/myfile.csv --output results/my_run.csv
```

## Models

| Model | Description |
|---|---|
| `baseline` | Simple average of peer scores (self-scores excluded) |
| `webpa` | WebPA normalisation — grade-neutral peer assessment factor |
| `peerrank-impute` | Walsh (2014) credibility-weighted iteration; non-submitters imputed with team mean |
| `peerrank-exclude` | Walsh (2014) credibility-weighted iteration; non-submitters excluded (IWF = N/A) |
| `peerhits-impute` | Dual-score (authority/hub) iterative model; non-submitters imputed |
| `peerhits-exclude` | Dual-score (authority/hub) iterative model; non-submitters excluded |

## Project structure

```
src/
  models/       # IWF models (baseline, webpa, peerrank, peerhits + variants)
  parsing/      # CSV parser and ScoreMatrix schemas
  attacks/      # Synthetic attack simulator (planned)
  evaluation/   # Metrics: rank reversal, attack delta (planned)
  dynamics/     # Team-dynamics classification pipeline (RQ3)
  qualitative/  # Sentiment pipeline (planned)
  visualization/ # Dash dashboard, force-layout graph, archetype map
  cli.py        # CLI entry point
data/           # Place CSV files here (gitignored)
output/         # Generated results (gitignored)
tests/          # Pytest test suite
docs/           # Research docs, diary, meeting notes
```

## Tests

```bash
python3 -m pytest tests/
```

## Dashboard

Interactive model comparison dashboard with force-layout graph:

```bash
python3 -m src.visualization.app
# Open http://127.0.0.1:8050
```

## Team-dynamics classification (RQ3)

Classifies each team's peer-rating matrix into latent team-dynamic archetypes using a 25-dimensional feature vector and Archetypal Analysis (Cutler & Breiman 1994).

**Feature vector (25 dims per team-matrix):**
- 9 behavioural metrics on the weighted directed graph: reciprocity, Gini (in-degree), mean/std rater variance, asymmetry, clustering coefficient, assortativity, non-submitter fraction, mean self-share
- 16 directed triad-census proportions (Holland & Leinhardt 1976), computed on the rater-mean-binarized graph

**Pipeline:**
1. Featurize all 136 score matrices → standardize
2. PCA (2-D, interpretable axes) + UMAP (2-D, non-linear structure)
3. Archetypal Analysis sweep k=2–8: RSS elbow + bootstrap stability to select k
4. Colour scatter plots by Δ (mean cross-model IWF disagreement) — tests whether archetypes predict model instability

**Run:**
```bash
pip install umap-learn  # one-time
python3 -m src.dynamics
# Outputs to output/dynamics/:
#   feature_matrix.csv       — 25-dim vectors + Δ per team
#   pca_plot.html            — interactive PCA scatter
#   umap_plot.html           — interactive UMAP scatter
#   rss_plot.html            — archetype count selection chart
#   archetypes.json          — archetype vectors + RSS per k
#   archetype_stability.csv  — bootstrap stability per k
```

**Research background:** `docs/team-dynamics-similarity-research.md`
