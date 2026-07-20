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

# 4. (after two raters fill sheets) score agreement
python3 -m src.labelling.kappa rater_A.csv rater_B.csv
```

`sample.py` auto-generates the assignments file if you skip step 1.

## How a rater uses this

You are given **`cards.pdf`** and a copy of **`label_sheet_template.csv`**. You
are **not** given `card_key.csv` or `labelling_sample.csv` — those hold the team
identity and model archetype the blinding exists to hide.

For each card (one team, three assessment matrices — source code / group report /
showcase poster):

1. Read the rating matrices (rows = recipient, cols = giver; grey = no rating /
   non-submitter), the above-average team graph, and the in-degree bars.
2. Apply the rubric's decision order (Disengaged → Free-rider → Dominant →
   Collusive → Conflict → else Cohesive → else Unclassified) and record **one
   `primary_label`** for the team, an optional `secondary_label`, and
   `confidence` (H/M/L).
3. Only if the team's three assessments clearly disagree, fill the per-question
   `primary_<question>` columns and note it; otherwise leave them blank.

Valid labels: `Cohesive, Dominant, Free-rider, Collusive, Conflict, Disengaged,
Unclassified`.

Two raters label independently without conferring, then run `kappa.py`. It
inner-joins on `card_id`, so a second rater who does only a **subset** (e.g. the
supervisor on 15–20 cards) is fine — κ is computed on the shared cards. The same
command also scores an intra-rater **test–retest** (your own two passes) if a
second human isn't available.

**Freeze** the labelled sheets before looking at how they line up with the
clusters (rubric §3.8) — no relabelling after seeing the validation.

## Outputs (`output/labelling/`)

| file | shown to rater? | contents |
|---|---|---|
| `labelling_sample.csv` | **no** | the 40 teams + archetype/flag/per-question — the record |
| `cards.pdf` | **yes** | 40 blinded one-page cards, randomised order |
| `card_key.csv` | **no** | card_id → team (the secret key) |
| `label_sheet_template.csv` | **yes** | blank sheet to fill in |
| `disagreements.csv` | — | written by `kappa.py` for adjudication |
