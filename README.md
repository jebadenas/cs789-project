# cs789-project

Research project for COMPSCI 789 (2026 S1) — algorithmic peer-assessment grading engine.

Implements and compares multiple IWF (Individual Weighting Factor) models for peer-assessment data from COMPSCI 399, investigating manipulation resistance and grading fairness.

## Setup

```bash
pip install -r requirements.txt
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
python3 -m src run data/myfile.csv --model peerrank
python3 -m src run data/myfile.csv --model baseline --model peerrank --team "Team 20"
```

**Override output path** (default: `output/<stem>_<timestamp>.csv`):
```bash
python3 -m src run data/myfile.csv --output results/my_run.csv
```

## Models

| Model | Description |
|---|---|
| `baseline` | Simple average of peer scores |
| `peerrank` | Walsh (2014) credibility-weighted fixed-point iteration |

## Project structure

```
src/
  models/       # IWF models (baseline, peerrank, ...)
  parsing/      # CSV parser and ScoreMatrix schemas
  cli.py        # CLI entry point
data/           # Place CSV files here (gitignored)
output/         # Generated CSV results (gitignored)
tests/          # Pytest test suite
```

## Tests

```bash
python3 -m pytest tests/
```
