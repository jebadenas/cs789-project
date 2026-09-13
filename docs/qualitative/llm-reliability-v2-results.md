# LLM reliability v2 — did the gate+follow-up rewrite fix the two weak fields?

**Date:** 2026-09-08. **Scope:** Workstream 3. Re-ran ONLY the two v1 fields that
wobble (conflict_handling, trajectory) as a reliable **gate** + a **follow-up** asked
only when the gate fires (`notes/llm-dynamics-checklist-v2.md`), 119 teams × 3
shuffled runs on the 72B (job 16462, 357/357 ok). v1 stays frozen; this is a separate
instrument-improvement result, not a change to any headline number.

Follows directly from `llm-reliability-diagnosis.md` (Workstream 1), which located
the failure at the low-end boundary (*"nothing happened"* vs *"a small thing that
turned out fine"*) and proposed exactly this fix.

> **✓ Final (2026-09-10).** 2024_s2 was found to be duplicate-inflated
> (`journal-data-dedup.md`); it has since been **re-marked (v1 + v2) on the deduped
> blobs** (job 16655) and the numbers below are recomputed on clean data. The bug fix
> *raised the v1 baseline* (conflict 54.6→59.7%, trajectory 72.3→73.9%) — i.e. the
> corruption made v1 look slightly worse than reality — while the v2 numbers were
> unchanged. The direction of the result did not move.

## Headline

**Mixed — the fix worked for conflict, not for trajectory.** conflict_handling jumped
**59.7% → 79.8%** (the none↔resolved floor wobble is essentially gone). trajectory
**dropped 73.9% → 64.7%** — an explicit floor + gate did *not* help; if anything it
hurt. So the diagnosis was right where the whole problem was a floor definition
(conflict), but trajectory's unreliability is deeper than a missing cutoff.

## 1. Reliability — v1 frozen vs v2 reworded (reconstructed to the same 3-way)

Run-to-run agreement = teams where all 3 shuffled runs give the same label. v2 is
collapsed back into v1's vocabulary (`none/resolved/festered`,
`stable/deteriorated/recovered`) so the comparison is like-for-like.

| Field | v1 frozen (clean) | v2 reworded | Δ |
|---|---|---|---|
| conflict_handling | 59.7% (71/119) | **79.8% (95/119)** | **+20.1 pp** |
| trajectory | 73.9% (88/119) | **64.7% (77/119)** | **−9.2 pp** |

The gates themselves (the yes/no decision, expected to be the reliable part):

| Gate | agreement |
|---|---|
| open_conflict | 86.6% (103/119) — v1 control was 92% (different prompt context) |
| notable_change | 79.0% (94/119) — new field, less reliable than open_conflict |

The story is in the gates. `open_conflict` is a solid, well-defined yes/no, so building
conflict_handling on top of it lifts the field to the binary tier. `notable_change`
("did the team's functioning materially change?") is itself only 79% — a shakier
gate — so stacking a direction on top of it *compounds* instability rather than
removing it.

## 2. Where the residual disagreement sits

v1's dominant splits were the low-end boundary — conflict_handling *none ↔ resolved*,
trajectory *recovered ↔ stable* (the WS1 diagnosis, pre-dedup, put these at 31/54 and
21/33 of splits respectively).

- **conflict_handling residual splits: festered/none 12, festered/resolved 8,
  none/resolved 4.** The floor wobble is essentially gone (only 4 none/resolved
  remain). What's left is the *severe-end* resolved↔festered call — a harder but more
  legitimate judgment, exactly as the diagnosis predicted. **This is a clean success.**
- **trajectory residual splits: deteriorated/recovered 17, recovered/stable 13,
  deteriorated/stable 7.** The stable↔recovered wobble only partly shrank, and
  deteriorated↔recovered is now the *largest* split — the rewrite didn't relocate the
  disagreement to a defensible place, it added a second unstable boundary at the
  severe end.

## 3. Quote check — are the cited quotes real? (hallucination signal)

Every v2 answer carries a verbatim journal quote; we string-match each back to the
team's blob (whitespace/smart-quote normalised).

- Quotes verified: **582** (846 empty — mostly false gates with nothing to cite) ·
  **not found: 93 (16.0%)**
- Per field: open_conflict **11/107 (10%)** · conflict_outcome **16/107 (15%)** ·
  notable_change **33/184 (18%)** · change_direction **33/184 (18%)**

The normaliser strips **all** whitespace before matching (not just collapses it),
because the model sometimes returns quotes with spaces dropped or line-breaks added
(`"Theteamdynamicisstillterrible…"`) and PDF extraction varies — none of which is
fabrication. That fix alone cut the miss rate from a naive 23.3% to ~16%, so the
residual is closer to true paraphrase/invention. Even so it is an **upper bound** (a
"miss" can still be a lightly-reworded real quote).

The signal that matters is unchanged: **conflict** fields ground better (10–15%)
than **trajectory** fields (18%) — the model is on shakier evidential footing
exactly where reliability also collapsed. The two diagnostics agree: trajectory is the
weak construct.

## 4. What this licenses in the dissertation

- **conflict_handling: report on v2.** Its unreliability *was* a fixable instrument
  artefact — the reworded gate+follow-up recovers it from 55% to ~80% (binary tier),
  and the residual disagreement is the legitimate resolved-vs-festered severity call.
  A clean "we diagnosed the weakness and fixed it" result.
- **trajectory: the rewrite failed — do not claim otherwise.** An explicit floor did
  not help; reliability fell and quote-grounding is weakest here. Best reported as
  **gate-only** (`notable_change`, 79%), dropping the direction sub-category, or
  flagged as a field that resists reliable coding.
- **Why trajectory resists — and what it points to.** Asking the model to judge
  *"did the team change over the whole project"* from one **pooled** blob is an
  inference over a wall of text, not an observation. This is an operationalisation
  problem, not just a wording one — and it is exactly what a **per-sprint** design
  sidesteps: change computed from successive sprint observations is a subtraction, not
  a guess. So trajectory's failure here is positive evidence for the per-sprint
  early-warning direction (`plans/journal-early-warning.md`).

Frozen/instrument split unchanged: the pre-registered v1 tallies and divergence index
do **not** move. v2 is reported as a separate instrument-improvement result.

## Reproduce

```
sbatch slurm/journal_mark_v2.sh                 # 119 x 3 = 357 calls, resumable
python3 -m src.qualitative.llm.reliability_v2   # after pulling marks_v2 back
```
Summary JSON: `output/qualitative/llm/marks_v2/reliability_v2_summary.json`.
