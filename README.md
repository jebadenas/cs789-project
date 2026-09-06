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

**Full map: [`ARCHITECTURE.md`](ARCHITECTURE.md)** — the authoritative guide to where everything is (packages → research questions → files).

```
src/
  parsing/       # CSV → ScoreMatrix (shared input type)
  models/        # IWF models: baseline, webpa, peerrank, peerhits (+ non-submitter variants)
  attacks/       # RQ1 manipulation simulator
  audit/         # Δ / attack-by-state / absolute table regeneration
  evaluation/    # RQ2 convergence; RQ1 rank-reversal
  dynamics2/     # the state cascade (current RQ3)
  dynamics/      # degeneracy + feature-extraction utility (RQ1 clean-set) — NOT the cascade
  qualitative/   # RQ4: llm/ (current LLM journal pipeline) + retired human-coding files
  reporting/     # LaTeX table fragments, data-quality
  visualization/ # Dash dashboard, force-layout graph
  batch_runner.py, cli.py, __main__.py   # model registry + entry points
data/            # CSVs + journals (gitignored — privacy)
output/          # Generated results (gitignored)
tests/           # Pytest suite (mirrors modules)
docs/            # Design docs; docs/qualitative/ = live analysis write-ups
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

## The state cascade (RQ3)

Each team×question matrix is sorted by a three-gate **state cascade** (`src/dynamics2/`) into readable vs unreadable states — the current RQ3 lane. The earlier archetypal-analysis / atypicality approach was cut (scope revision 2026-08-18; see `docs/_archive/`).

```bash
python3 -m src.dynamics2      # → output/dynamics2/
```

## Qualitative journal analysis (RQ4)

An open-weight LLM reads each team's reflective journals and codes team-dynamics questions (`src/qualitative/llm/`). Method, results, and the reliability diagnosis are written up in **`docs/qualitative/README.md`**.

See **[`ARCHITECTURE.md`](ARCHITECTURE.md)** for the full package map.
