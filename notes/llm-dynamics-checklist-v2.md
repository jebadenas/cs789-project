# LLM team-dynamics checklist — v2 (instrument-improvement re-run)

**Date:** 2026-09-07
**Status:** SCOPED — targets only the two weak v1 fields. v1 stays FROZEN.
**Strand:** qualitative / RQ3-EXT. See docs/qualitative/llm-reliability-diagnosis.md
(Workstream 1) for why this rewrite exists.

## What this is (and is not)

v1 (`llm-dynamics-checklist-v1.md`) is **frozen**. Every **headline result** — the
per-state tallies, the divergence index, the Kruskal–Wallis test — stays on v1 and
does **not** change. v2 is a **separate instrument-improvement experiment**: we
diagnosed *why* two v1 fields wobble run-to-run (conflict_handling 55%, trajectory
72%) and here we test whether a reworded instrument fixes them. Reported alongside
v1, never mixed into the pre-registered numbers.

Only the two weak fields are re-asked. The other 11 items are untouched.

## The diagnosis this rewrite acts on

Both weak fields fail at the **same boundary**: *"nothing happened"* vs *"a small
thing happened but it turned out fine."* The severe end of each scale is solid; the
**low-end cutoff was undefined**, so the 3-way call guessed it differently each run.
The reliable control field **open_conflict (92%)** works because its definition
carries an explicit floor — *"friction beyond ordinary task disagreement."* The fix:
give each weak field that same floor, and split the jammed 3-way into a reliable
**gate** (yes/no) + a **follow-up** asked only when the gate fires.

## The reworded fields

### Conflict — reuse open_conflict as the gate

- **`open_conflict`** `y/n` *(gate — identical wording to v1 item 7)*: explicit
  friction, arguments, or interpersonal tension **beyond ordinary task/technical
  disagreement**. Routine "we argued about TypeScript vs JavaScript then moved on"
  is task disagreement → **NO**.
- **`conflict_outcome`** `resolved / festered` *(follow-up — asked ONLY if
  open_conflict = YES)*: was the conflict **resolved** (worked through, stopped
  affecting the team) or did it **fester** (stayed unresolved, kept affecting them)?
- If `open_conflict` = NO → outcome is **none** by construction (not asked).

This removes the *none ↔ resolved* wobble (31 of 54 v1 splits) by construction: the
"is this even a conflict?" decision is now made once, by the field that already
does it reliably.

### Trajectory — add a real-downturn floor, then a direction

- **`notable_change`** `y/n` *(gate — new binary)*: did the team's functioning
  **materially** change over the project — a genuine **downturn** (crisis, breakdown,
  serious sustained dip) or a genuine **turnaround**? A minor sprint hiccup, a single
  rough week, or ordinary deadline pressure the team handled **does NOT count** →
  that is a **stable** team, not a change.
- **`change_direction`** `deteriorated / recovered` *(follow-up — asked ONLY if
  notable_change = YES)*: did the team end **worse** (deteriorated — ended in a bad
  place) or **dip-then-recover** (recovered — a real rough patch that genuinely
  turned around)?
- If `notable_change` = NO → trajectory is **stable** by construction (not asked).

This removes the *stable ↔ recovered* wobble (21 of 33 v1 splits): "was there a real
downturn at all?" is now a floor, so a small dip-and-bounce no longer flips between
*stable* and *recovered*.

## Reconstruction back to v1 labels (for the reliability comparison)

To compare like-for-like against v1's 55% / 72%, collapse v2's gate+follow-up back
into the v1 3-way categories:

| v1 field | reconstructed from v2 |
|---|---|
| `conflict_handling` | `none` if not open_conflict; else `conflict_outcome` (resolved/festered) |
| `trajectory` | `stable` if not notable_change; else map change_direction (deteriorated/recovered) |

## Protocol

Same as v1 Step 6: **119 teams × 3 runs**, shuffled member labels per run, blind to
cascade state, temperature 0.2, strict JSON. Every answer additionally carries a
**verbatim quote** from the journals so we can (a) audit the evidence and (b)
string-match quotes back to the source and report a **quote-not-found rate** as a
hallucination signal.

Code: `src/qualitative/llm/marking_v2.py` · driver `run mark_v2` ·
`slurm/journal_mark_v2.sh`. Reliability + quote check:
`src/qualitative/llm/reliability_v2.py`. Outputs: `output/qualitative/llm/marks_v2/`.
