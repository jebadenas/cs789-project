# Hand-labelling tooling (RQ3 anchor set)

Three small tools that produce a ~40-team hand-labelled validation set for the
team-dynamics classification strand, **blind to model output**. See
[`docs/labelling-design.md`](../../docs/labelling-design.md) for *why* each choice
was made, and `notes/labelling-rubric.md` for the codebook raters apply.

## Pipeline

```bash
# 1. (once) persist the per-matrix AA k=4 archetype assignment
python3 -m src.dynamics.mixture          # writes output/dynamics/aa_k4_assignments.csv

# 2. choose the ~40 teams (stratified, seeded)
python3 -m src.labelling.sample          # -> output/labelling/labelling_sample.csv

# 3. generate the blinded rater cards + blank entry sheet
python3 -m src.labelling.cards           # -> cards.pdf, card_key.csv, label_sheet_template.csv

# 3b. generate the browser labelling UI (the rater-friendly front end)
python3 -m src.labelling.ui              # -> label_ui.html (self-contained)

# 4. (after two raters fill sheets) score agreement
python3 -m src.labelling.kappa rater_A.csv rater_B.csv

# 5a. descriptive summary of ONE sheet (archetype-blind; safe before freeze)
python3 -m src.labelling.summary output/labelling/labels_<rater>.csv

# 5b. naming + external-validity cross-tabs (POST-FREEZE ONLY)
python3 -m src.labelling.naming output/labelling/labels_<rater>.csv \
    [--second output/labelling/labels_<rater2>.csv]
```

`sample.py` auto-generates the assignments file if you skip step 1; `ui.py`
needs `card_key.csv`, so run `cards.py` first.

## How a rater uses this

**The easy path: open `label_ui.html` in any browser.** It is fully
self-contained (no server, no Python, no internet — email it to a second rater),
shows every card, has the label dropdowns beside each, autosaves to the browser,
and a **Download CSV** button produces the sheet `kappa.py` reads. This is the
recommended front end, especially for a non-technical second rater.

(The `cards.pdf` + `label_sheet_template.csv` route still works if you'd rather
label on paper / in a spreadsheet — same columns, same output.)

Either way you are **not** given `card_key.csv` or `labelling_sample.csv` — those
hold the team identity and model archetype the blinding exists to hide.

For each card (one team, three assessment matrices — source code / group report /
showcase poster):

1. Read the rating matrices (rows = recipient, cols = giver; grey = no rating /
   non-submitter), the above-average team graph, and the in-degree bars.
2. Pick the **one `primary_label`** that best fits the whole team, plus an
   optional `secondary_label` and `confidence` (H/M/L). The UI shows a signal
   hint per label as reference — but there is deliberately no forced decision
   sequence (that would anchor raters and inflate κ); form your own judgement.
3. Only if the team's three assessments clearly disagree, fill the per-question
   `primary_<question>` fields and note it; otherwise leave them blank.

Valid labels: `Cohesive, Dominant, Free-rider, Conflict, Disengaged,
Unclassified`. (Collusive was dropped — it isn't reliably distinguishable from
Cohesive on the matrix alone; see `docs/labelling-design.md`.)

Two raters label independently without conferring, then run `kappa.py`. It
inner-joins on `card_id`, so a second rater who does only a **subset** (e.g. the
supervisor on 15–20 cards) is fine — κ is computed on the shared cards. The same
command also scores an intra-rater **test–retest** (your own two passes) if a
second human isn't available.

**Freeze** the labelled sheets before looking at how they line up with the
clusters (rubric §3.8) — no relabelling after seeing the validation.

## Analysis scripts

- **`summary.py`** — descriptive summary of a *single* rater sheet (label &
  confidence distributions, secondary/per-question usage, a presentation-order
  drift check). Imports **no** archetype data (not `card_key.csv`,
  `labelling_sample.csv`, `aa_k4_assignments.csv`, or `src/dynamics`), so it is
  safe to run **before the freeze** without contaminating a test–retest. Writes
  `summary_<rater>.csv`.
- **`naming.py`** — **post-freeze** validation. Joins labels →
  `card_key.csv` → `labelling_sample.csv` and reports: primary_label × flag
  (headline), primary_label × archetype (raw counts; % suppressed for cells
  < 8; no χ² — cells are single-digit), ARI/NMI partition agreement, a
  high-confidence sensitivity pass, and the modal-label-per-archetype naming
  table. `--second` reports a second rater separately (or uses an
  `adjudicated_label` column if present). Writes `naming_crosstab.csv`,
  `naming_agreement.csv`.

Running order for reliability + naming, once labels exist: `kappa.py` (κ) →
freeze → `naming.py`. Taxonomy/columns are centralised in `constants.py`.

## Outputs (`output/labelling/`)

| file | shown to rater? | contents |
|---|---|---|
| `labelling_sample.csv` | **no** | the 40 teams + archetype/flag/per-question — the record |
| `label_ui.html` | **yes** | self-contained browser labelling UI (recommended) |
| `cards.pdf` | **yes** | 40 blinded one-page cards, randomised order (paper route) |
| `card_key.csv` | **no** | card_id → team (the secret key) |
| `label_sheet_template.csv` | **yes** | blank sheet to fill in (paper route) |
| `disagreements.csv` | — | written by `kappa.py` for adjudication |
