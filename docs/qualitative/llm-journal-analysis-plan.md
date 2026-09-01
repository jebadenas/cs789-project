# LLM journal analysis — plan

**Date:** 2026-08-29
**Status:** Design frozen (spine). Three parameters deferred; see §9.
**Strand:** Qualitative / RQ3-EXT. Reads reflective journals, groups by cascade
state, and describes the team dynamics behind each state.

---

## 1. Aim

Characterise, for each **cascade state**, the team dynamics that typically show
up in the members' reflective journals — so the states read as something
concrete ("here's what a *Contested* team sounds like") rather than as bare
statistical labels.

This is **descriptive / informative**, not a recovery test. We are *not*
claiming the state can be predicted from the text; we are describing what tends
to co-occur with each state. That lower evidential bar is deliberate and sets
what "enough" means throughout.

The core methodological commitment: **never ask a model to summarise a state
directly** (it will produce a confident story whether or not a real pattern
exists). Instead — discover candidate patterns openly, freeze them into a
checklist, then measure each one blindly and compare across states. The
comparison, not the model's confidence, is the evidence.

## 2. Scope & data

**In: 4 cohorts, N = 119 teams.** Inclusion criterion is data-driven — a cohort
is in only if its reflection template **actually prompted team-dynamics
reflection** (verified via the audit §9 template survey; re-run 2026-08-29
across all 6 cohorts).

| Cohort  | Teams | Team-dynamics prompt |
|---------|-------|----------------------|
| 2023_s2 | 37    | yes                  |
| 2024_s1 | 15    | yes (variant wording, pooled) |
| 2024_s2 | 43    | yes                  |
| 2025_s1 | 24    | yes                  |
| **Total** | **119** |                    |

**Excluded:**
- **2023_s1 (20 teams)** — journals never prompt team dynamics; no signal to
  mine, only noise to hallucinate on.
- **2022_s2** — has journals but **no peer-assessment CSV**, so no cascade state
  to group by.

Cohorts are **pooled**; no per-semester handling despite minor prompt-wording
differences (2024_s1 differs slightly). The 4-vs-other-strands cohort mismatch
is fine — the journal strand and the peer-scoring strand (WebPA / PeerRank /
PeerHits) are independent, and the journal inclusion criterion is defensible on
its own terms.

**Text volume:** ~28k tokens per team blob on average. One team fits a marking
call comfortably; a whole state does **not** fit one context window (drives the
map-reduce design in §5).

## 3. Grouping — the spine

Group by **cascade state at 8-state resolution** (`pooled_state` in
`output/dynamics2/pooled/team_states.csv`), joined to journal teams on
`(cohort, real_team) = (cohort, team_name)` — all 119 join cleanly.

| Cascade state          | Teams (N=119) |
|------------------------|---------------|
| No standout            | 48            |
| One at bottom          | 26            |
| Silent-lone-dissenter  | 10            |
| Silent-flat            | 10            |
| One at top             | 8             |
| Contested              | 8             |
| Both ends              | 8             |
| Silent-incomparable    | 1  → footnote |

The cascade states are **already computed for all cohorts** from the peer-ranking
matrices (`dynamics2`), independently of journals and of the peer-scoring
models. This strand only **reads** them (read-only join at §5 step 8); it never
recomputes them.

## 4. Unit of analysis

One **structured text blob per team**: every member's every journal entry,
each delimited and tagged, e.g. `Member A — Journal 3: …`. Tagging preserves
*who* said it and *which assessment* it came from, so within-team divergence and
per-journal differences stay visible instead of being flattened into mush. All
journal indices are kept (2024_s1 J1 is simply sparse on dynamics — acceptable).

Coverage is uniform: every team has **4–6 journalling members** (min 4), so no
thin-team exclusions are needed.

## 5. The pipeline

### Step 1 — Prep
Build the 119 structured team blobs (§4).

### Step 2 — Per-team notes ("map")
Feed each team's blob to the model, one team at a time. It writes **free-form**
observations about that team's dynamics — no fixed checklist, no cascade label.
Open on purpose, to keep discovery exploratory. → 119 note-files.

### Step 3 — Group notes by state
Plain lookup — sort the 119 notes into their 8 cascade states. No model.

### Step 4 — Recurring patterns per state ("reduce")
For each state, feed **all** its notes together (they fit) and ask what recurs
across the teams. The "what keeps coming up" judgment is cross-team, so it must
see every team in the state at once — which map-reduce delivers and sampling /
batching would not. → a candidate pattern list per state.

### Step 5 — Lock the checklist
Pool all 8 states' candidates → trim duplicates, vague items, template noise →
land on **one shared ~10–15-item checklist**, each item a clear yes/no (a few
may be simple levels, e.g. conflict = none / mild / strong). **Jos reviews and
trims once** (~20–30 min — the single frozen instrument, the one place human
sign-off earns its keep). **Freeze and date** the checklist before Step 6.

A **shared** checklist is what makes comparison possible: every team is scored on
the *same* items, so "this pattern from Contested — does it also appear in
Silent?" becomes answerable.

### Step 6 — Blind marking
Model goes **team by team** (one team per call, ~28k tokens), **not told the
state**. For each checklist item: **yes/no + a one-line supporting reason/quote**
(reasons make findings quotable and let us spot-check for invention). Run
**3× per team with shuffled member order**; **majority-of-3** is the final mark.
→ one row per team in `output/qualitative/llm_features.csv`.

### Step 7 — Consistency check
From the 3 runs, compute **per-item agreement** (self-consistency). An item that
flips run-to-run is unreliable. Reliability **floor is deferred** (§9); items
below it will be *flagged, not reported*. This is the **only** validity check —
we dropped the human anchor codes, so we can show the marking is **consistent**,
not that it is **correct**. Findings are framed accordingly (§7).

### Step 8 — Count & compare
For each item: its **rate in each state** next to its **overall base rate** across
all 119 teams, with per-cell **n** and the supporting **quotes**. A pattern
"counts" for a state only if its rate there clearly beats the base rate — a row
that's flat everywhere means nothing. This baseline is the confabulation-catch
that lets us drop the discovery-stage decoy.

- **(a) Descriptive table** — the headline finding (rates, base rate, n, quotes).
- **(b) Noise guardrail** — a light "bigger-than-chance" flag per notable cell
  (permutation / bootstrap), as a *guide, not gospel*: with ~15 items × 8 states
  ≈ 120 cells, a few trip a naive test by chance, so it annotates (a), never
  gatekeeps it. Method deferred (§9).

Output: the **state × pattern table** — the actual finding.

## 6. Why the decoy was dropped

The decoy (running discovery on a random team mix to see if the model invents
equal coherence) was an *early warning* against confabulation. It's redundant
with Step 8: a pattern the model invented won't show up more in its state than
in general, so it washes out in the counting anyway. Step 8 is the stronger,
quantitative version of the same check. We keep Step 8, drop the decoy.

## 7. Honesty framing (for the write-up)

- **Discovery is label-aware** (Step 4 groups notes by state), so the checklist
  is a **hypothesis**. The blind marking + counting (Steps 6–8) are the
  **evidence**. Keep these visibly separate.
- **Consistent ≠ correct.** With no human ground truth, Step 7 shows the model
  marks *steadily*, not that it marks *rightly*. Report novel patterns as
  **suggestive**, not validated.
- **Small cells.** Several states are ~8 teams; always show n, and lean on the
  Step 8 guardrail so "5 of 8 = 62%" isn't over-read.

## 8. What's already done (2026-08-29)

- **Expanded the dataset 72 → 139 teams.** Re-ran `ingest` (all 6 cohorts:
  4,640 files, 1,009 students), built `team_key` linkage for 2024_s2 and
  2025_s1 via `sample teams`. All 139 cascade-labelled teams link cleanly; the
  119 prompting-cohort subset is the study set.
- Pre-ingest `entries.parquet` / crosswalk backed up under `/tmp/*.bak`.
- Confirmed the cascade / archetype / peer-scoring outputs were **untouched**
  (journal-only, additive change).

## 9. Open items (deferred, non-blocking)

1. **Exact model** — API or cluster (privacy not a constraint; capable frontier
   model assumed). Jos to confirm.
2. **Reliability floor** (Step 7) — the per-item agreement threshold for
   "report vs flag". To be pre-committed *before* looking at results.
3. **Noise-guardrail method** (Step 8b) — permutation vs bootstrap; and whether
   any multiple-comparison handling.

## 10. Pipeline at a glance

```
119 team blobs
   │  Step 2: per-team notes (model, open)
   ▼
119 notes ──Step 3: group by state──► 8 note-groups
   │  Step 4: recurring patterns per state (model)
   ▼
8 candidate lists ──Step 5: pool + trim + Jos review──► 1 frozen checklist
   │  Step 6: blind mark every team ×3, majority-of-3 (yes/no + reason)
   ▼
llm_features.csv ──Step 7: per-item consistency──► reliability flags
   │  Step 8: rate per state vs base rate (+ noise guardrail)
   ▼
state × pattern table  ← the finding
```
