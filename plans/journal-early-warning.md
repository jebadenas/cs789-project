# Plan: Journal-only early-warning for capstone tutors

> Companion to `docs/early-warning-feasibility.md` (why journal-only) and the tutor-tool
> discussion. This is a **design sketch / next-step plan**, not yet built.

---

## Aim

Give a capstone **tutor** (owns 6-7 teams, reads each sprint's journals to mark them,
never sees the peer data) an **early signal** — during the term, not after — of which
of their teams is heading for trouble, from the journals they're already reading.

Not "read less" (they read all 6-7 anyway) but **read sooner, and with a cross-cohort
yardstick**. Triage-of-attention over time.

## Why journal-only (settled)

The peer cascade exists at only two timepoints (proposal + final) and the proposal
snapshot is >50% unreadable — see `docs/early-warning-feasibility.md`. Journals, by
contrast, are genuinely per-sprint (`journal_index`; journal 1 = intro, then
journal_{k+1} ↔ sprint k). So the per-sprint signal has to come from the journals.

## The unit and the signals

- **Unit:** (team, sprint). For each team, sprints are its work journals J2..J_N,
  position-normalised (sprint k of N → k/N) so 4-journal and 5-journal cohorts line up
  by *position*, not absolute number.
- **Signals per sprint:** the **reliable** LLM checklist variables only — the binary
  gates that pass the reliability bar (open_conflict ≈92%, plus the v2 reworded gates
  `notable_change` / `conflict_outcome` once Workstream 3 lands). Do **not** use the
  wobbly 3-way fields. Each sprint's journal is coded independently.

## The validation design (leave-future-out)

Retrospective, on the 4 study cohorts:

> Using only signals from journals **up to sprint k**, predict trouble **evidenced
> after k**. Slide k. (3-journal-of-work teams give "J2 → J3+"; 4 give more runway.)

This sidesteps the missing external outcome (open-questions Q11) with a *within-
semester* target: earlier sprints predicting later ones. Two honest targets:
1. **Later-sprint journal-evidenced trouble** (e.g. a reliable flag firing in a later
   journal). Internal, but the only per-sprint target available.
2. **Raw team project mark** — the one genuinely external anchor, used as a coarse
   end-of-line check (does early flagging relate to a poor final mark?).

Report as a **triage/recall** problem, not accuracy: the cost of missing a failing
team ≫ the cost of a false flag, so measure *how many teams that ended badly were
flagged early* (recall), and the false-flag rate as the tutor-time cost.

## What has to be built (the one real new capability)

The current pipeline pools **all** a team's journals into one blob
(`blobs.build_blob`). Early warning needs **per-sprint** coding:

| Phase | Description | Status |
|---|---|---|
| 1 | Per-sprint blob: variant of `build_blob` restricted to a given `journal_index` (or cumulative J≤k), blind to cascade + sprint label | ❌ not started |
| 2 | Run the **reliable** checklist per (team, sprint) — reuse the marking pipeline, new output dir | ❌ not started |
| 3 | Leave-future-out analysis: early-sprint signals → later-sprint trouble; recall + false-flag rate | ❌ not started |
| 4 | Coarse external check against raw team mark | ❌ not started (needs the team-mark data) |
| 5 | Tutor-facing framing: what a flag *shows* and what action it triggers | ❌ design only |

## Honest caveats (put in the write-up)

- **Cold start:** sprint 1-2 are thin, so early warning is weakest exactly when it
  first speaks; it strengthens later. Set expectations.
- **Within-semester target ≠ external outcome.** "Later sprints" is journal-evidence
  predicting journal-evidence — better than nothing, not a clean ground truth.
- **Reliability gate:** only variables that survive Workstream 3 are eligible; a signal
  that wobbles run-to-run can't drive a tutor-facing flag.
- **Observer effect (deployment, not retrospective):** if students knew a model scans
  their reflections for flags, journals could sanitise and the signal erode. The
  retrospective study is unaffected; a deployed tool must weigh this.

## ACE framing

Retrospective early-warning study (method + leave-future-out validation on the study
cohorts) with the tool presented as a *designed* application + honest limits. The
deployed/evaluated tool is the next paper.

## First concrete step

Phase 1 + a Phase-2 pilot on **one** cohort with the single most reliable signal
(open_conflict) — prove per-sprint coding runs end-to-end and that an early flag has
*any* relationship to a later one, before building the full instrument.
