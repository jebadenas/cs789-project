# Write-up guardrails — LLM journal analysis

**Date:** 2026-09-02. Mistakes caught while reviewing the supervisor Figma draft, turned
into a checklist so they don't recur in the dissertation. Sources of truth:
`README.md`, `llm-results.md`, `llm-type-portraits.md`, `llm-deep-dive.md`,
`notes/llm-dynamics-checklist-v1.md`.

## 1. Model attribution — the big one
- The analysis model is **Qwen2.5-72B-Instruct (AWQ), served with vLLM on the CS-ML cluster**.
- The **7B local run was a rehearsal that FAILED** (54% of notes drifted into activity-recaps) and its outputs were **discarded**. Never cite 7B numbers or say "7B" as the analysis model.

## 2. Don't claim beyond what an analysis established
- ❌ "In No-standout, leadership is the key variable that decides who stabilises." We **never ran a within-No-standout test** — this was an unsupported assertion on the draft.
- Rule: a per-type *mechanism* claim requires a per-type read (like we did for Contested, Both-ends, One-at-top, Silent-lone-dissenter). No-standout was **not** deep-dived; describe it only as the heterogeneous, at-baseline "average" group.

## 3. State the unit — three different denominators
- **Journal strand = per-team, N=119** (4 prompting cohorts).
- **Cascade pipeline = per-matrix, 417 scorings** (the Gate A/B/C diagram %).
- **Cascade teams = 139** (5 cohorts, peer-assessment level).
- So "Silent-flat = 87 matrices (21%)" and "Silent-flat = 10 teams" are **both correct, different units**. Always label which; never mix them in one sentence.

## 4. Use the verified per-type framings (not vague ones)
- **Silent-flat** — textbook team; harmonious, 0 divergence.
- **Silent-lone-dissenter** — balanced effort **but a distinctive pocket of open dissent over ideas/direction/leadership**, aired civilly. NOT "the dissent is noise."
- **No-standout** — the ordinary middle; sits at base rate on everything; no signature.
- **Contested** — reads **calm despite split ratings**; the "contest" is **deliberative** (friction about the *work* — integration, design — resolved), plus a **factional minority** (often a language/culture seam). NOT "problems and strengths coexist."
- **One-at-bottom** — a quiet under-contributor the team routes around; late surge; most cope.
- **One-at-top** — imbalance **voiced**: over-carrier vents, escalates (lecturers), burnout.
- **Both-ends** — a **silent split**: carrying core + named dead weight, **no open conflict**; plus the **perception disconnect** (under-contributors don't see the problem the carriers do).
- Meta-point to keep: **the *kind* of conflict distinguishes the types, not the amount.**

## 5. Reliability tiers — don't over-lean on the weak fields
- Binary items are reliable (**80–98%** run-to-run) → safe to report.
- `conflict_handling` (**54%**) was **dropped** — do not report the none/resolved/festered split.
- `trajectory` (**72%**) is the weakest reported field — the per-type "X stable / Y deteriorated" counts are accurate to the data but **rest on trajectory**; caveat them, don't build a claim on them alone.

## 6. Inferential vs descriptive — lead with the right test
- **Headline (well-powered, report as the result):** composite **divergence index** rises across the cascade — KW **p=0.0035**; Silent vs Standout **p=0.00056**.
- **Per-cell Fisher tests are underpowered** (n≈8–48): only **2/88 survive FDR** (Silent-flat under-contribution 0%; Both-ends singled-out-below 75%). Don't present raw per-cell percentages as significant findings — frame them as descriptive, backed by the composite test.
- **Deep-dive textures are n=8 leads, not tallies.** Say so.

## 7. Other honesty lines to keep
- **Consistent ≠ correct**: no human ground truth for the novel features; the 3× runs show the model is *consistent*, not *validated*.
- **Contested-looks-harmonious is NOT statistically significant** — a cautious sentence, not a claim.
- **Imbalance items 1/2/4/5/6 co-move** — one construct, not five findings. `mutual_support` is universal (no discriminating value).
- **Scope**: 119 = teams whose journals prompt dynamics; 2023_s1 excluded (no prompt), 2022_s2 (no peer data). It's a **representative** subset of the 139 (bucket proportions within ~2 pts).
- **Names**: notes/marks contain real teammate names — **scrub every quoted excerpt** before it goes in the dissertation.
