# LLM journal analysis — canonical record

**Strand:** RQ3-EXT (qualitative). **Branch:** `llm-journal-analysis`. **Dates:** 2026-08-29 → 09-01.

Characterise the team dynamics behind each **cascade state** by reading students'
reflective journals with an LLM — so the states read as concrete kinds of team,
not just statistical labels. This file is the index + method + findings; the detail
lives in the companion docs linked below.

## Aim & core commitment

Descriptive, not a recovery test. The methodological rule: **never ask a model to
summarise a state directly** (it will produce a confident story regardless).
Instead — discover candidates openly → freeze a checklist → measure blindly →
compare. The comparison, not the model's confidence, is the evidence.

## Data

- **119 teams**, 4 cohorts whose reflection template *prompts* team-dynamics
  reflection (2023_s2, 2024_s1, 2024_s2, 2025_s1). Inclusion is data-driven (audit §9
  template survey), not arbitrary.
- Excluded: 2023_s1 (has cascade states but journals don't prompt dynamics) and
  2022_s2 (journals but no peer data → no cascade state). **119 is the ceiling.**
- Grouping: cascade state from `output/dynamics2/pooled/team_states.csv`, at two
  resolutions — 8 fine states (`pooled_state`) and 4 buckets (`anyflag_bucket`:
  Silent 21 / No-standout 17 / Standout 44 / Contested 37). Joined to journals on
  `(cohort, real_team)`; all 119 match.
- Journals: `data/journals/processed/entries.parquet` (ingested from raw; the study
  set was expanded 72→139 linked, 119 usable, on 2026-08-29).

## Model & infrastructure

- **Qwen2.5-72B-Instruct-AWQ** on the UoA CS-ML cluster (1× A100 80GB), served with
  **vLLM 0.28 (cu129)**, YaRN rope-scaling (factor 4, `--hf-overrides`) for
  `--max-model-len 73728` (blobs reach ~67k tokens), temperature 0.2.
- Pipeline is backend-agnostic via `src/qualitative/llm/model.py:call_model`
  (`ollama` local / `openai` = vLLM). Local trial used `qwen2.5:7b` — **too weak**
  (54% of notes drifted into activity-recaps; the 72B fixed it, 0% drift).
- Cluster gotchas are recorded in the memory note and `cluster-setup.md`: `/home`
  100 MB quota (set HOME→/data), cu129 not cu130, YaRN via `--hf-overrides`,
  Python 3.12 for Triton headers, bypass squid for localhost.

## Method — the pipeline (reproducible)

Code: `src/qualitative/llm/`. Slurm jobs: `slurm/`. All steps write to
`output/qualitative/llm/`.

| # | step | how | output |
|---|---|---|---|
| 1 | **Blobs** | one structured, blinded blob per team (`Member A — Journal 3: …`) | in-memory |
| 2 | **Notes** | 72B writes open dynamics notes per team (one-shot example in prompt, 6–10 obs) | `notes/` (119) |
| 3 | **Group** | notes grouped by cascade state (lookup) | — |
| 4 | **Aggregate** | 72B finds recurring candidate patterns per state (label hidden) | `patterns/` (8) |
| 5 | **Checklist** | pooled/trimmed → **frozen** 13-item checklist w/ definitions | `notes/llm-dynamics-checklist-v1.md` |
| 6 | **Mark** | 72B scores every team on the checklist, **blind**, **3× with shuffled member labels**, strict JSON | `marks/` (357) |
| 7 | **Consistency** | per-item agreement across 3 runs; **majority-of-3** = final | in analysis |
| 8 | **Compare** | rates per state vs base rate; Fisher+BH per cell; **composite divergence index** | `features_by_state.csv` |

Commands (cluster): `sbatch slurm/journal_notes.sh` → `journal_aggregate.sh` →
(freeze checklist) → `journal_mark.sh`; analysis is local pandas/scipy.

Key parameters: notes capped at 6–10 observations; marking `temperature=0.2`,
`response_format=json_object`; 3 runs re-label members deterministically per
`(team, seed)`; categoricals `conflict_handling`/`trajectory` dropped/flagged for low
reliability (54% / 72%).

## Findings

### 1. Headline (reliable, inferential) — see `llm-results.md`
A per-team **divergence index** (count of 9 imbalance/conflict features) rises across
the cascade: **Silent 0.95 < Contested 2.30 < No-standout 2.76 < Standout 3.32**.
Kruskal–Wallis **p=0.0035**; Silent vs Standout **p=0.00056**. One composite test =
no multiple-comparison penalty. Reliability: binary items 80–98% run-to-run.
*The journals independently recover the cascade structure.* (Per-cell Fisher tests
are underpowered at n≈8–48; only 2/88 survive FDR — the two poles. This is a
power limit, not a weak effect.)

### 2. Type portraits (descriptive) — see `llm-type-portraits.md`
Each state has a distinct feature fingerprint: Silent-flat = textbook team;
Both-ends = a carrying core + a named dead weight, *no* open conflict; One-at-top =
friction around an over-carrier; No-standout = the average; Contested = calm surface.

### 3. Within-type textures (exploratory) — see `llm-deep-dive.md`
The real patterns, beyond the checklist. **The *kind* of conflict distinguishes the
types, not the amount:**
- **Contested** — friction is about *the work* (integration, quality), debated & resolved (a minority are factional, on a culture/language seam).
- **One-at-top** — imbalance *voiced*: the over-carrier vents, escalates.
- **Both-ends** — imbalance *avoided*: a silent freeze-out; plus a **perception disconnect** (under-contributors don't see the problem the carriers do — why the ratings split).
- **Silent-lone-dissenter** — dissent over *ideas/direction*, aired civilly.
New dimensions the checklist never held: perception disconnects, language/culture
seams, and **assessment used as a covert conflict channel**.

## Limitations
Descriptive, not causal; N=119 caps per-cell power; no human ground truth for the
novel features (consistent ≠ correct); imbalance items 1/2/4/5/6 co-move (one
construct); deep-dive is n=8 leads, not tallies; notes/marks contain real names —
**scrub before quoting.**

## File map
- Plan: `llm-journal-analysis-plan.md` · Infra: `cluster-setup.md`
- Checklist (frozen): `../../notes/llm-dynamics-checklist-v1.md`
- Results: `llm-results.md` · Portraits: `llm-type-portraits.md` · Deep dive: `llm-deep-dive.md`
- Code: `src/qualitative/llm/` · Jobs: `slurm/journal_*.sh`
- Outputs: `output/qualitative/llm/{notes,patterns,marks}/`, `features_by_state.csv`
