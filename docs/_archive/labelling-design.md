# Hand-labelling anchor set — design decisions

Design record for the `src/labelling/` tooling (handoff-4, RQ3-EXT Step 3). This
captures the decisions taken when the handoff met the actual data, several of
which override or sharpen the original brief. Companion docs: the codebook
(`notes/labelling-rubric.md`), the strategy memo (`notes/classification-research.md`),
and the rater workflow (`src/labelling/README.md`).

## Purpose

Produce a ~40-team hand-labelled set of real teams, labelled by two independent
raters against a rubric, **blind to Δ / atypicality / archetype**. It does two
jobs (rubric §5): (a) *names* the four data-driven AA k=4 groups by
cross-tabulating human labels against archetype, and (b) serves as a held-out
**external-validity** set, independent of model output.

## Key numbers (what the data forced)

At team level (139 teams, each exactly 3 question-matrices), the AA k=4 majority
archetype × flag population is:

| | Anomalous | Typical | total |
|---|---|---|---|
| A0 | 14 | 5 | 19 |
| A1 (flat mode) | 4 | 54 | 58 |
| A2 (anomalous tail) | 5 | 2 | **7** |
| A3 | 12 | 22 | 34 |
| Mixed (no majority) | 8 | 13 | **21** |

Two of the handoff's stop-and-report triggers fired immediately: **A2 is only 7
teams** at team level (was n=40 at *matrix* level), and **21/139 (15%) have no
majority archetype**. Both are handled by design below rather than by heuristic.

## Decisions

1. **Unit = team, keyed by `(csv_path, team_name)`.** Team *numbers* recur across
   cohorts — "Team 6" is three different teams across 2023/24/25 — so the session
   file is part of the identity. Never key on the team number alone.

2. **Team-level archetype = majority across the 3 matrices; no majority → a real
   `Mixed` stratum.** Mixed teams are not force-fit into an archetype; they carry
   an overall label only when a majority exists, and are labelled per-question
   otherwise (rubric §3). Per-question archetypes are always retained and shown.

3. **Sample the whole frame (139), including Mixed.** Excluding the ambiguous 15%
   would bias the external-validity estimate toward easy cases (the "ground-truth
   bias" trap the memo cites) and inflate κ. Mixed gets ~5 slots — its population
   share, not oversampled — and is a genuine test of whether raters also find
   those teams ambiguous.

4. **Sample and score at team level, NOT per assessment.** Sampling individual
   matrices would be cleaner (native archetypes, no ties, A2 has 40) but
   reintroduces the exact non-independence the rubric bans: three matrices from
   one team aren't independent, so per-matrix κ is pseudoreplicated and inflated,
   and a per-matrix set misaligns from the team/person-level external data
   (Git/journals). Instead the **cards show all three assessments** and raters may
   label per-question, but the unit of analysis and κ stay at team level.

5. **Quota over {A0,A1,A2,A3,Mixed} × {Typical,Anomalous}, total 40** — rare cells
   oversampled, not proportional (rubric §4):

   | | Anomalous | Typical |
   |---|---|---|
   | A0 | 6 | 4 |
   | A1 | 3 | 4 |
   | A2 | 5 | 2 |
   | A3 | 5 | 6 |
   | Mixed | 3 | 2 |

   - **A2 is a full census** (all 7) — the rare tail can't afford attrition.
   - **A1 (flat/disengaged) is capped at 7** despite being 42% of the population.
     Proportional would spend ~17 slots on trivially-labellable flat teams that
     inflate κ for the wrong reason and starve the informative cells. Flat stays
     represented (one of the seven rubric labels is "Disengaged") but doesn't
     dominate.

6. **Exemplars are fill-don't-expand calibration anchors.** The 32 archetype
   exemplar rows map to 26 owner-teams; forcing all of them in would pre-commit
   27/40 slots and skew the design (and 6 of the 26 are themselves Mixed at team
   level). Instead the quota is fixed first and exemplar owner-teams are merely
   *preferred* when filling a cell. Anchoring on the exemplar *matrix* (which
   appears on the team's card) preserves the calibration value even when the owner
   team is Mixed. **Team 6 "Caffeine Overload"** (high-Δ non-submitter) is the one
   hard force-include.

7. **AA labels are persisted, never re-fit downstream.** The seeded AA k=4 refit
   lives in `src/dynamics/mixture.py` (now committed); it writes
   `output/dynamics/aa_k4_assignments.csv` once and everything reads that. The
   deprecated `dynamic_label` column in `classifications.csv` (failed 5-prototype
   run) is **not** used.

8. **Cards output as one self-contained PDF, static matplotlib graph.** Easy to
   hand to a second rater (supervisor); no server, no headless-JS pain. Blinding:
   members → A–F consistent across a team's three questions; randomised seeded
   card order; `card_key.csv` kept separate; no archetype/flag/Δ/name on the card.

9. **Label now, matrix + graph only; freeze; journals inform validation later.**
   Journals (handoff 5) aren't delivered. They were always a "where available"
   cross-check (rubric §2/§3), so the anchor set is labelled and frozen on the
   matrix + graph stimulus now; journals later feed *validation*, not relabelling
   (the freeze-once rule, rubric §3.8). A placeholder box reserves the slot so
   cards need not be regenerated.

## Labelling UX (added after a first labelling attempt proved too hard)

A trial run showed that reading raw heatmaps against the full 7-label rubric was
too high-effort and error-prone — a warning sign, since a struggling rater
produces low κ and a second (non-technical) rater would struggle more. Four
changes, each kept *inside* the blind-to-the-model constraint:

- **Browser UI (`ui.py` → `label_ui.html`).** A single self-contained HTML file
  (card images embedded base64) that any rater opens in a browser and fills in
  with dropdowns, then exports a CSV identical to `label_sheet_template.csv`.
  Chosen over a CLI so a supervisor/labmate can use it with zero setup — the
  second rater is the whole reason κ is worth computing.
- **Taxonomy trimmed 7 → 5 + Unclassified** (dropped **Collusive**). Collusive
  is not reliably separable from Cohesive on the rating matrix alone (both look
  even/high) without journals; keeping it just manufactures noise. The remaining
  labels (Cohesive, Dominant, Free-rider, Conflict, Disengaged) each have a
  matrix-visible signature, so the taxonomy still distinguishes the groups — the
  human label count need not equal the cluster count (naming is a many-to-one
  cross-tab).
- **No guided decision tree.** Considered and rejected: forcing raters through a
  fixed question sequence anchors them toward the analyst's framing AND inflates
  κ (shared procedure manufactures agreement, so κ stops measuring genuine
  independent judgement). The rubric is shown as *reference* only (label
  definitions + one-line signal hints).
- **Cards stay raw data, no interpretive text.** "Richer" cards must be more
  views of the data, never words like "B is the free-rider" — that pre-chews the
  judgement, the same anchoring problem. The rubric §2 stimulus (matrices +
  above-average graph + in-degree bars) is kept as-is.

10. **Reliability is rater-agnostic.** `kappa.py` inner-joins two sheets on
    `card_id`, so it scores two independent humans, a second rater on a *subset*,
    or an intra-rater **test–retest** with the same code. Jos being the only rater
    now blocks nothing: build + label now, obtain a second rater (supervisor on a
    subset) for the inter-rater κ, with test–retest as the documented fallback.
    The **model is not a valid second rater** — that would destroy the
    independence the anchor set is built to provide.
