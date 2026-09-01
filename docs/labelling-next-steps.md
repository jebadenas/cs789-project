# Labelling anchor set — next steps (session handoff)

Pickup note for a future session. Context: the RQ3 hand-labelling **tooling** is
built and on branch `handoff-4/labelling-tooling` (PR #31). This file is the
to-do list from there. Read alongside `docs/labelling-design.md` (why the tools
are shaped this way), `src/labelling/README.md` (how a rater uses them), and
`notes/labelling-rubric.md` (the codebook).

## State as of 2026-07-20

- ✅ Tooling built + verified: `src/labelling/{sample,cards,kappa}.py`,
  `mixture.py` persists `output/dynamics/aa_k4_assignments.csv`.
- ✅ Artifacts generated: 40-team sample, `cards.pdf`, `card_key.csv`, blank
  `label_sheet_template.csv` (all under `output/labelling/`, gitignored →
  regenerate with `python3 -m src.labelling.sample` then `... .cards`).
- ✅ Stimulus sanity-checked: a spread of A0/A1/A2/A3/Mixed cards is clearly
  labellable from matrix + graph alone (no journals needed).
- ❌ **No teams labelled yet.** No real κ. Journals (handoff-5) not delivered.

## Immediate

1. **Merge PR #31** (tooling only, non-destructive).

## The labelling (manual — the actual deliverable)

2. **Jos's pass.** Open `output/labelling/label_ui.html` in a browser
   (`python3 -m src.labelling.ui` regenerates it), label all 40 cards blind, and
   click **Download CSV** → `labels_<name>.csv`. Do NOT open `card_key.csv` /
   `labelling_sample.csv` while labelling. Labels: Cohesive, Dominant,
   Free-rider, Conflict, Disengaged, Unclassified (Collusive was dropped — see
   design doc §labelling-ux). Use the per-question fields only when a team's three
   assessments disagree (e.g. the Mixed cards). The `cards.pdf` + spreadsheet
   route still works if preferred.
3. **Second rater** — the critical-path dependency. Supervisor or labmate labels
   independently; a **subset (15–20 cards)** is enough (`kappa.py` inner-joins on
   `card_id`). If no second human, fall back to **intra-rater test–retest** (Jos
   labels again ~2 weeks later, blind to pass 1). *Raise "who is the second
   rater?" at the next supervisor meeting if not yet settled.*
4. **Score:** `python3 -m src.labelling.kappa sheetA.csv sheetB.csv`. Target
   κ ≥ 0.6. If below, refine the codebook and re-label — and report it (rubric §6:
   an unreliable taxonomy is itself a finding).
5. **Freeze** the sheets before any validation analysis (rubric §3.8) — no
   relabelling after seeing how labels line up with clusters.

## What the frozen labels unlock (research-plan §4, `notes/classification-research.md`)

6. **Name the groups:** cross-tab human primary label × AA archetype
   (from `aa_k4_assignments.csv`, aggregated to team majority the same way
   `sample.py` does). A clean mapping ("A2 = 80% Conflict") names the group and
   is evidence it's a real dynamic. *This script does not exist yet — write it.*
7. **External cluster validity:** adjusted Rand index / NMI between the human
   partition and the cluster partition.
8. **Criterion validity (gated on handoff-5):** once Git + journals land, check
   labelled free-rider teams show lopsided commits / distressed journals.

## Known optional refinements (non-blocking)

- Heatmap colour scales auto-scale per question, so equal scores read as
  different colours across the three panels (printed numbers mitigate). A shared
  colour scale per card would be cleaner if a rater finds it confusing.
- If the stimulus proves too thin in practice, the journal placeholder box on
  each card is reserved to slot excerpts in without regenerating layout.

## Guardrails (do NOT touch)

Dissertation `.tex`, `src/dynamics/` pipeline logic, `src/attacks/`,
`src/qualitative/`. The only pipeline-adjacent change made was adding assignment
*persistence* to `mixture.py` (no logic change; loads 71/172/40/134 still
reproduce exactly).
