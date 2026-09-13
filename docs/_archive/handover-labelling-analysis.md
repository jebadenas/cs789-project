# Handover — labelling analysis scripts (`summary.py`, `naming.py`)

**For:** Claude Code · **Raised:** 2026-07-26 · **Branch:** cut from `handoff-4/labelling-tooling` (or main if #31 is merged)

Closes the two gaps flagged in `docs/labelling-next-steps.md` §6–7 ("*this script
does not exist yet — write it*"). Read `docs/labelling-design.md` for why the
labelling tooling is shaped as it is, and `notes/labelling-rubric.md` §7 (in the
COMPSCI 789 workspace) for the operative codebook.

---

## The one constraint that matters

**Build both scripts. Do not run them on real labels. Do not open
`card_key.csv` or `labelling_sample.csv` in any way that surfaces their contents
to Jos.**

Jos is currently the only rater and the intra-rater test–retest fallback is
still live. That fallback requires his second pass to be blind to model output.
If he sees which archetype a team landed in — or even which teams the cards
correspond to — the retest is void and the anchor set loses its only available
reliability estimate. Verify with synthetic fixtures only (see Testing).

Corollary: `summary.py` must be safe to run *before* the freeze, so it is
forbidden from touching archetype data at all. `naming.py` is post-freeze only.

---

## Prerequisite (check first, stop if unmet)

`output/labelling/labels_jos.csv` is currently **the blank template** — 40 rows,
every `primary_label` empty, byte-identical to `label_sheet_template.csv`. If it
is still blank when you pick this up, stop and report; do not fabricate or
stub label data into it.

`output/labelling/` is gitignored. Regenerate inputs with:

```bash
python3 -m src.dynamics.mixture     # -> output/dynamics/aa_k4_assignments.csv
python3 -m src.labelling.sample     # -> labelling_sample.csv
python3 -m src.labelling.cards      # -> cards.pdf, card_key.csv, label_sheet_template.csv
```

---

## Script 1 — `src/labelling/summary.py`

Single-sheet descriptive summary. **Reads one rater sheet and nothing else.**

```bash
python3 -m src.labelling.summary output/labelling/labels_jos.csv
```

Report:

1. **Label distribution** — count and share per `primary_label`, including
   `Unclassified` and any blanks. Blanks are an error condition: print a loud
   warning listing the offending `card_id`s (a partial UI export is the likely
   cause and is easy to miss).
2. **Confidence distribution** — H/M/L counts, and the H/M/L breakdown crossed
   with `primary_label`.
3. **Secondary-label usage** — how often used, and the primary→secondary pairs.
4. **Per-question field usage** — how many cards used
   `primary_{source_code,group_report,showcase_poster}`, i.e. how often the
   three assessments were judged to disagree.
5. **Order/drift check** — `card_id` order is the randomised presentation
   order, so position is a usable proxy for time. Split the sheet into
   quartiles by card number and report the confidence mix per quartile.
   Purpose: detect a rater growing more confident with practice, which would
   silently bias any confidence-based split in `naming.py`. Report the pattern
   descriptively; do **not** run a significance test on n=40.

Print a plain-text report to stdout and write
`output/labelling/summary_<rater>.csv` (long format: `metric,category,value`).

**Must not import or read** `card_key.csv`, `labelling_sample.csv`,
`aa_k4_assignments.csv`, or anything under `src/dynamics/`. Add a comment at the
top of the file saying so, and why.

---

## Script 2 — `src/labelling/naming.py`

The validation step. Post-freeze only.

```bash
python3 -m src.labelling.naming output/labelling/labels_jos.csv \
    [--second output/labelling/labels_<rater2>.csv] \
    [--key output/labelling/card_key.csv] \
    [--sample output/labelling/labelling_sample.csv]
```

### Join path

`labels_*.csv` → (`card_id`) → `card_key.csv` → (`team_id`) →
`labelling_sample.csv`, which **already carries team-level `archetype` and
`flag`** for exactly these 40 teams.

Use those columns. Do **not** recompute the team majority from
`aa_k4_assignments.csv` — `sample.py:build_team_table()` already did it, and a
second implementation is a silent-divergence risk. `team_id` is
`"{csv_path} :: {team_name}"`; never key on team name or number alone (numbers
recur across cohorts).

Assert the join is total: 40 in, 40 out, no NaN archetype. Fail loudly otherwise.

### Outputs

1. **Binary cross-tab (the headline).** `primary_label` × `flag`
   (Typical/Anomalous). This is the primary claim — 2 columns, n=40, and the
   binary partition is the more stable one (~0.95).
2. **k=4 cross-tab (descriptive).** `primary_label` × `archetype`, with `Mixed`
   retained as its own column. Print **raw counts**. Suppress the percentage
   for any cell with n < 8. No χ², no p-values, no significance stars — the
   cells are single-digit and a test would be meaningless. Put that reason in
   the docstring so nobody "fixes" it later.
3. **Partition agreement.** Adjusted Rand index and normalised mutual
   information between the human `primary_label` partition and (a) the binary
   flag, (b) the k=4 archetype. `sklearn.metrics.adjusted_rand_score`,
   `normalized_mutual_info_score`.
4. **Confidence sensitivity.** Repeat 1–3 on the high-confidence subset. With
   two raters the subset is cards **both** marked High (conjunction — never
   average confidence across raters, the scales are uncalibrated self-reports
   and thresholds differ between people). With one rater it is that rater's
   Highs, and the output must label it as the weaker single-rater version.
   Report n alongside every restricted statistic.
5. **Naming candidates.** For each archetype, the modal human label and its
   share, as a one-line-per-group table. This is the actual deliverable — the
   thing that turns "A2" into a name. Print the share and the n it rests on
   side by side; a modal share off n=5 must not be readable as a strong claim.

Write `output/labelling/naming_crosstab.csv` and
`output/labelling/naming_agreement.csv`; print everything to stdout too.

### Second-rater handling

Optional. When `--second` is supplied, use the **adjudicated** label if an
adjudicated column exists, otherwise run the cross-tab on each rater separately
and report both rather than silently picking one. Do not invent an adjudication
rule.

---

## Testing

Fixtures under `tests/fixtures/labelling/`, generated in-test — **not** copies
of real labels. Cover:

- A full synthetic sheet with a deliberately clean label↔archetype mapping;
  assert ARI is high and the modal-label table recovers the planted structure.
- A random-label sheet; assert ARI ≈ 0. This is the one that catches a broken
  join — a bug there tends to produce spurious agreement.
- A sheet with blanks and a sheet with an invalid label string; assert both are
  caught with a clear error rather than silently dropped.
- A subset second sheet (20 of 40 cards); assert the inner-join behaviour
  matches `kappa.py`'s.

Follow existing repo conventions for test layout and runner.

---

## Guardrails

Do not touch: dissertation `.tex`, `src/dynamics/` pipeline logic,
`src/attacks/`, `src/qualitative/`, `src/models/`. Do not re-fit AA — read the
persisted `aa_k4_assignments.csv` only. Do not modify `kappa.py`.

## Done when

- Both scripts exist, are importable as `python3 -m src.labelling.{summary,naming}`, and are covered by the fixture tests.
- `summary.py` demonstrably reads no archetype data (grep the imports).
- Neither script has been run against real labels.
- `src/labelling/README.md` gains a section for both, and
  `docs/labelling-next-steps.md` items 6–7 are ticked with a pointer here.
