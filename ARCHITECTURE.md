# Architecture — cs789-project

**The one map.** If you (human or AI) need to find something in this repo, start here.

This repo holds the **code, data pipeline, and analysis** for the COMPSCI 789
dissertation: peer-assessment weighting models, a "state cascade" that triages which
rating matrices carry a readable signal, and an LLM that reads student journals to
characterise the teams behind each state.

The **strategic / writing layer** (notes, meetings, the dissertation itself) lives in
the *workspace*, not here — `~/Documents/University/2026-S2/COMPSCI-789` (its
`codebase/POINTER.md` points back here). The dissertation's source of truth is Overleaf.

## Research question → where the code lives
| RQ | Question | Code |
|----|----------|------|
| RQ1 | manipulation resistance | `src/attacks/`, `src/audit/`, `src/evaluation/rank_reversal.py` |
| RQ2 | convergence / readability | `src/evaluation/convergence.py` |
| RQ3 | validity of the reading (the cascade) | `src/dynamics2/` (the cascade), `src/dynamics/` (degeneracy + features), `src/audit/regen.py` (Δ-by-state) |
| RQ4 | practical value (journals) | `src/qualitative/llm/` |

## Packages (`src/`)
- **`parsing/`** — data in: CSV discovery + parse into `ScoreMatrix` (the shared input type). Start of every pipeline. `schemas.py` defines `ScoreMatrix`/`StudentInfo`.
- **`models/`** — the four IWF models: `baseline`, `webpa`, `peerrank`, `peerhits`. `peerrank.py`/`peerhits.py` are the core algorithms; `*_exclude`/`*_impute` wrap them with a non-submitter convention (**exclude = default**; **impute = sensitivity appendix only**). `types.py` = `ModelResult`.
- **`attacks/`** — RQ1 manipulation simulator: `transforms.py` (attack vectors), `synthetic.py` (planted-truth teams), `delta.py` (Attack Δ + Monte-Carlo), `runner.py` (batch), `profile_sweep.py`.
- **`audit/`** — regenerates Δ / attack-by-state / absolute-vs-relative tables after model fixes. `regen.py` (per-matrix Δ, Δ-by-state, KW stats), `attacks_by_state.py`, `absolute.py`. Entry: `python -m src.audit`.
- **`evaluation/`** — `convergence.py` (RQ2: do the iterative models converge), `rank_reversal.py` (RQ1 metric).
- **`dynamics2/`** — **THE STATE CASCADE (current RQ3).** `gates.py` (the 3-gate cascade), `ranks.py`, `nulls.py`, `contested.py`, `crossq.py`, `pooled.py`, `dataio.py`, `validate.py`. Entry: `python -m src.dynamics2`. Output → `output/dynamics2/`.
- **`dynamics/`** — ⚠ **not the cascade.** A degeneracy + feature-extraction *utility* only: `classifier.is_degenerate` + `features.extract_features` (+ `triad.py`) define the RQ1 attack "clean set." The archetypal-analysis lane this package once held was cut (scope revision 2026-08-18).
- **`qualitative/`** — RQ4. **`llm/`** = the current LLM journal pipeline (`blobs → notes → aggregate → marking → run`; `model.py` = backend wrapper). The flat files (`reader`, `ingest`, `sample`, `templates`, `audit`) are the **retired human-coding** pipeline.
- **`reporting/`** — `aggregate_tables.py` (LaTeX table fragments for the dissertation), `data_quality.py`.
- **`visualization/`** — Dash app (`app.py`) + `graph.py`/`force_layout.py`.
- **Orchestration** — `batch_runner.py` (the `MODELS` registry + batch scoring), `cli.py` (interactive CLI), `__main__.py` (`python -m src`).

## Data, outputs, jobs
- **`data/`** — COMPSCI 399 peer-feedback CSVs + journals. **Gitignored (privacy).**
- **`output/`** — all generated results. **Gitignored.** Key: `output/dynamics2/` (cascade states), `output/attacks/`, `output/qualitative/llm/{notes,marks}/`.
- **`slurm/`** — cluster jobs for the 72B LLM (`journal_*.sh`).

## Docs
- **`docs/qualitative/`** — the live qualitative/LLM analysis write-ups. **Start: `docs/qualitative/README.md`.**
- `docs/models/`, `docs/attacks/` — per-component design docs.
- `docs/_archive/` — superseded docs (old team-dynamics/archetypes, labelling, dev diary, meetings).
- `notes/llm-dynamics-checklist-v1.md` — the frozen 13-item marking checklist.

## Conventions
- **`ScoreMatrix`** (`parsing/schemas.py`) is the unit passed between models / attacks / dynamics.
- A **"matrix"** = one team × one question; a **"team"** pools its questions.
- **Δ** = std of a student's IWF across the model suite (per matrix).
- Tests mirror modules: `tests/test_<module>.py`. Run: `python -m pytest`.
