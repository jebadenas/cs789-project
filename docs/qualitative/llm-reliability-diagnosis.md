# LLM reliability diagnosis — why two questions wobble (Workstream 1)

**Date:** 2026-09-03. **Scope:** why the two weak checklist questions disagree
across the 3 shuffled runs. Analysis is on the **existing** marks
(`output/qualitative/llm/marks/`, 119 teams × 3 runs) — no re-run. Contrast
question **open_conflict** (reliable, 92%) included as a control.

## Headline
Both weak questions fail in the **same place**: the boundary between *"nothing
happened"* and *"a small thing happened but it turned out fine."* The severe end
of each scale is solid; the **low-end cutoff is undefined**, so the model guesses
it — differently each run. It is a **definition problem, not a data problem.**

## 1. The disagreements are not random — they cluster on one pair

| Question | Run-to-run agreement | Dominant split (of all splits) |
|---|---|---|
| **conflict_handling** | 55% (65/119 unanimous, 54 split) | **none ↔ resolved — 31/54** |
| **trajectory** | 72% (86/119 unanimous, 33 split) | **stable ↔ recovered — 21/33** |
| open_conflict (control) | 92% (110/119, 9 split) | true ↔ false — 9/9 (thin-journal cases) |

- conflict_handling: the model almost never confuses *resolved* vs *festered*
  (only 9 splits). It wobbles on **whether a minor issue counts as a "conflict" at
  all** (none vs resolved). Other splits: festered/none 12, festered/resolved 9,
  all-three 2.
- trajectory: it almost never touches *deteriorated* (deteriorated/stable 2,
  deteriorated/recovered 9). It wobbles on **whether a small dip-and-bounce counts
  as a "recovery"** or is just noise inside an overall stable team.

Both = the *floor* of the scale ("null" vs "benign-positive"), not the severe end.

## 2. The smoking gun — same evidence, opposite verdict
The model's own stored reasons show it reading the **same events** and disagreeing
on whether they *count*:

- **conflict_handling — 2024_s2 team_27:**
  - run: *"resolved the TypeScript→JavaScript switch and merge conflicts"* → **resolved**
  - run: *"no evidence of any conflict that needed handling"* → **none**
  - The disagreement is purely *"does a routine task problem count as a conflict?"*
- **trajectory — 2024_s2 team_41:**
  - run: *"faced challenges in sprint 2 but recovered"* → **recovered**
  - run: *"stable throughout, no deterioration or recovery"* → **stable**
  - The disagreement is purely *"is a small sprint hiccup a 'recovery'?"*

Same journal, contradictory reason, because the cutoff was never specified.

## 3. Other explanations ruled out
- **Not thin/short journals, not the "middle" cascade types.** Split vs unanimous
  teams are near-identical: conflict_handling ~23–25k words, ~30 entries, ~44–49%
  No-standout/Contested either way; trajectory likewise. It's the *question*, not
  the *teams*. (The control is the exception: open_conflict's 9 splits **are** the
  shortest journals — 16.7k vs 24.9k words, 22% vs 49% mid — i.e. genuine
  thin-evidence wobble, a different and rarer mechanism.)
- **Not missing information.** Crude lexical scan: conflict words present in 98% of
  journals, outcome words 94%, change-over-time words 100% — no difference between
  split and unanimous. The words are there; the model just can't categorise them
  consistently. (Caveat: keyword presence ≠ a clearly-stated outcome.)

## 4. A twist: trajectory is *confidently* inconsistent
Hedging in the model's own reasons (uncertainty markers like "no clear",
"seems", "possibly"), average terms per team:

| Question | unanimous | split |
|---|---|---|
| conflict_handling | 0.11 | **0.22** (more hedging when it splits — it "knows") |
| trajectory | 0.10 | **0.03** (LESS hedging when it splits — no self-awareness) |

On trajectory the model states each contradictory verdict confidently ("stable
throughout" / "recovered") with no hedge — the more dangerous failure mode: no
internal signal that it is guessing. *(Caveat: the hedge metric is contaminated for
binaries — open_conflict's high counts, 2.31/1.89, are mostly "no explicit conflict"
boilerplate, not true uncertainty. Read the metric only within the categoricals.)*

## 5. Why the control works — and the fix it hands us
**open_conflict (92%)** is reliable because its definition carries an **explicit
floor**: *"friction beyond task disagreement."* That one carve-out is exactly what
conflict_handling lacks. The fix the data points to:

1. **Give both weak questions an explicit floor.** conflict_handling: align with
   open_conflict — *routine task problem-solving ≠ conflict → none*. trajectory:
   *"recovered" requires a real downturn (dysfunction/crisis), not a sprint hiccup.*
2. **Restructure as a gate + follow-up.** A reliable yes/no first ("was there real
   conflict at all?" / "was there a real downturn at all?"), then ask the
   sub-category **only if yes**. The reliable question already *is* a gate; the weak
   ones jammed the gate and the sub-choice into one 3-way call. **This is what the
   Workstream 3 re-run should test** (gate+follow-up rewrite vs current one-shot).

## Reproduce
Analysis over `output/qualitative/llm/marks/*.json` (values + stored `reasons`),
blob length/counts via `src.qualitative.llm.blobs.build_blob`. See conversation /
`llm-writeup-guardrails.md` §5 for the reliability tiers this refines.
