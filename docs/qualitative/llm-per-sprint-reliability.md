# Per-sprint LLM reliability — is single-sprint text too thin to code reliably?

**Date:** 2026-09-13. **Scope:** Workstream 3 (qualitative / LLM strand). Ran the
per-sprint pipeline (`src/qualitative/llm/marking_sprint.py`), which codes each
(team, sprint) on the **11 "v1" binary team-dynamics flags**, 3× with shuffled member
labels, on Qwen2.5-72B on the UoA cluster (job 16854, **1299/1299 complete, 0 failed**).
Reliability = run-to-run agreement (all 3 shuffled runs identical) over the **433
(team, sprint) cells** that have ≥2 non-empty runs, computed by
`src/qualitative/llm/sprint_analysis.py`. The whole-project v1 binaries stay frozen;
this is a separate result about whether the *per-sprint* unit of analysis holds up.

The open question this answers: a single sprint's text is much thinner than a whole
project's pooled journal, so the worry was that per-sprint coding would be too sparse
to be reliable. If that were true, the whole per-sprint early-warning direction would
be dead on arrival.

## Headline

**Per-sprint coding is reliable across ALL 11 flags (86–96%).** The sparsity worry is
disproven — agreement on thin single-sprint text is *comparable to or tighter than*
the whole-project binaries (which ran 80–98%). The peer-blind "value" dynamics that
the tool is built around are the most reliable of the lot, and they fire selectively
rather than firing everywhere, so the reliability is discriminating signal, not the
trivial reliability of a flag that never fires.

## 1. Reliability per flag

`agree%` = cells where all 3 shuffled runs give the same label. `base%` = how often the
flag fires (its prevalence). Both are needed to read the result: a rare flag can post a
high `agree%` partly for free, because agreeing on "false" is easy when the flag is
mostly false — so `agree%` must always be read alongside `base%`.

| Flag | agree% | base% |
|---|---|---|
| leadership_problem | **96.3** | 10.9 |
| open_conflict | **96.1** | 6.9 |
| mutual_support | 94.9 | 96.1 |
| singled_out_below | 94.2 | 13.9 |
| singled_out_above | 93.1 | 6.7 |
| communication_breakdown | **91.2** | 21.2 |
| harmonious_balanced | 91.0 | 58.9 |
| effort_imbalance | 90.1 | 30.7 |
| member_under_contributed | 89.8 | 52.9 |
| underperformance_unaddressed | 86.4 | 37.9 |
| core_subgroup_carried | 86.4 | 19.2 |

## 2. The value dynamics are the most reliable — and discriminating

The peer-blind dynamics central to a tutor-facing tool — **leadership_problem (96.3%),
open_conflict (96.1%), communication_breakdown (91.2%)** — are the *most* reliable
flags in the set. Crucially, they fire **selectively** (base rates 7–21%), so their
high agreement is not the artefact of a never-firing flag: the model both codes them
consistently and reserves them for a minority of sprints. That is exactly the profile
you want from an early-warning signal — reliable *and* discriminating.

## 3. Reading the base rates

- **mutual_support fires ~96% of the time** — near-universal. It is reliable (94.9%)
  but **not discriminating**: it is a background condition of most sprints, not a
  distinguishing signal. This was anticipated in the v1 checklist as a base-rate item,
  so it is behaving as designed rather than surprisingly.
- **harmonious_balanced fires ~59%** — a common "things are fine" read, useful as a
  contrast label but not a rare event.
- The six-flag **contribution cluster** — effort_imbalance, member_under_contributed,
  underperformance_unaddressed, core_subgroup_carried, singled_out_below,
  singled_out_above — fires at moderate rates. These are **not surfaced individually**:
  at scoring/display time they are collapsed into a single **"unequal contribution"**
  signal (see `plans/dashboard-study-design.md`), so their individual base rates matter
  less than the reliability of the collapsed signal, and every component here clears
  86%.

## 4. What this is — and what it is not

- **This is reliability, not validity.** The result says the model codes each sprint
  *consistently* run-to-run under label shuffling. It does **not** say the coding
  matches ground truth — that is validity, and validity is what the tutor study is
  designed to measure.
- **But reliability was the gate.** A flag that wobbles run-to-run cannot drive a
  tutor-facing tool, whatever its validity — an unstable signal is unusable before the
  question of correctness even arises. All 11 flags clear that gate here, so none of
  them is disqualified on reliability grounds before the study begins.
- **`agree%` is not a standalone quality score.** As noted above, a mostly-false flag
  earns part of its agreement trivially. Read the table as (agreement, prevalence)
  pairs, not as a leaderboard of `agree%` alone.

## 5. What this licenses in the dissertation

The per-sprint unit of analysis is **viable**. The concern that single-sprint text is
too sparse to code reliably is answered: it is not. This **unblocks** the per-sprint
early-warning / dashboard study (`plans/dashboard-study-design.md`,
`plans/tutor-exercise-draft.md`) — the reliability precondition for a per-sprint
tutor-facing signal is now met for all 11 flags, and the study can move to the
validity question.

## Reproduce

```
rsync back the per-sprint marks from the cluster (job 16854, 1299 files):
  output/qualitative/llm/marks_sprint/
python3 -m src.qualitative.llm.sprint_analysis
```
Source data: `output/qualitative/llm/marks_sprint/` (1299 files, 433 codeable cells).
