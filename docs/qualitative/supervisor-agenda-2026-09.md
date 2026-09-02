# Supervisor Meeting — LLM Journal Analysis
**COMPSCI 789 · Sep 2026 · ~20 min**

## 1 · Scope (1 min)
- **119 teams, 4 cohorts** (2023 S2, 2024 S1, 2024 S2, 2025 S1) — the cohorts whose reflection template actually *prompts* team-dynamics reflection.
- 2024 S2 + 2025 S1 exports now ingested → adds the free-rider candidates we lacked.
- **Inclusion is data-driven:** 2023 S1 dropped (journals don't prompt dynamics), 2022 S2 (no peer data). The 119 is a **representative subset** of the 139 cascade-labelled teams (bucket proportions within ~2 pts).

## 2 · The full pipeline (6 min)
All generation on **Qwen2.5-72B (AWQ), vLLM on the cluster GPU**. Blinded: pseudonymous member labels, **no team name / cohort / cascade state** *(the journal text itself may name teammates — scrubbed before any quote)*.

| Step | What it does | Output |
|---|---|---|
| **1 · Notes** | Reads each team's raw journals; writes free-form observations on *interpersonal dynamics only* (not project progress), each cited to member/journal. | 119 files |
| **2 · Aggregate** | Groups notes by cascade state (model doesn't know the state); reads each group together; extracts *recurring* patterns. | 8 files |
| **3 · Build the checklist** *(how we got the 13)* | Pool the 8 candidate lists → drop **universal** patterns (appear in every state) + duplicates → keep the recurring, *distinguishing* ones → **13 questions** (11 y/n + 2 categorical), define each, **freeze before any marking**. | frozen instrument |
| **4 · Mark** | Back to raw journals; score every team on the 13, blind, **3× with member labels shuffled**; majority-of-3 = final. | 357 files |
| **5 · Analyse** | Consistency across runs; rates per cascade state; composite divergence index + significance. | results |

### How we got the 13 questions (Step 3, in detail)
Not chosen from theory up front — **discovered from the journals, then frozen before scoring:**
1. **Open discovery (Step 1).** The 72B wrote free-form dynamics notes per team — no preset categories, just "what's going on here."
2. **Recurring patterns per state (Step 2).** For each of the 8 cascade states, the model read that state's notes *together* and listed what **recurred** → 8 candidate lists (verbose, up to ~26 items each: effort imbalance, under-contribution, communication breakdowns, conflict, leadership issues, someone singled out, harmonious, mutual support, trajectory shifts…).
3. **Pool → trim (Step 3).** Merge all 8 lists and cut: **(a) universal** patterns that appear in *every* state (positive early dynamics, "communication," adaptability — they can't distinguish anything), **(b)** duplicates and vague/un-markable items. Keep the recurring **and** distinguishing dynamics.
4. **Land on 13, define, review, freeze.** ~13 questions in 4 groups — *effort & contribution (4), standing out (2), conflict (3), overall shape (4)*; each with a written definition; sharpened for distinctness (e.g. "singled-out" requires a *single identifiable* person, so it isn't a restatement of "under-contributed"); **reviewed and frozen before any team was marked.**

- **Why it's defensible:** grounded in the corpus **and** pre-registered (frozen pre-marking → not fitted to results).
- **Honest caveats:** (i) two items — *singled-out above/below* — were added deliberately as the journal analogue of the cascade's standout direction (not purely emergent); (ii) the checklist was built to **discriminate** (kept features that vary across states, dropped universal ones), which is exactly why the results lean on the "divergence" axis — the richer per-type texture (§4B) only surfaced in a later *open* re-read.

## 3 · Reliability (2 min)
- Binary features: **80–98%** agreement across the 3 shuffled runs — a stable instrument.
- Weak: **conflict_handling 54%**, **trajectory 72%** → definitions need tightening; don't lean on either.
- Dead: **mutual_support = True for all 119** → dropping it.

## 4 · Results (6 min)

**A · The defensible finding — journals recover the cascade (external validation).**
Cascade state comes from *peer ratings*, **not** the LLM — so no circularity. Journal-coded **divergence** (imbalance + conflict features) rises cleanly across it:
**Silent 0.95 → Contested 2.30 → No-standout 2.76 → Standout 3.32** · Kruskal–Wallis **p = 0.0035** · Silent vs Standout **p = 0.0006**.
*(One composite test → no multiple-comparison penalty. Per-cell tests are underpowered — 2/88 survive FDR — so report the composite, not the cells.)*

**B · What each state actually looks like (descriptive — handout).**
The *kind* of friction distinguishes the types, not the amount:
- **Both-ends** — silent freeze-out (core carries, dead weight worked around, 0% open conflict) + a **perception disconnect** (under-contributors don't see the problem).
- **One-at-top** — imbalance *voiced*: over-carrier vents, escalates to lecturers, burnout.
- **Contested** — reads *calm* despite split ratings; the "contest" is deliberative (about the work), + a factional minority.
- **Silent-flat** textbook · **Silent-lone-dissenter** dissent over *ideas* · **No-standout** the average middle.

**C · Trajectory / outcomes (motivates RQ4 — flagged, not a headline).**
Cascade → trajectory *observations*: Silent-flat 10/10 stable; One-at-top ~half deteriorate (escalation); **No-standout = 48 teams, biggest triage pool.** — but see §5.

## 5 · The circularity flag — key discussion (2 min)
- **Trajectory is coded in the same LLM pass as the features**, so any "features → trajectory" separation is partly artefact — and trajectory is our *weakest* field (72%). §4C is a *lead*, not a result.
- **The clean validation is §4A** — features/divergence vs **cascade state**, which is genuinely external to the LLM.
- **Decision to make:** (a) split trajectory into a separate prompt/pass to break the circularity, or (b) lean on cascade-state alignment as the primary validation and treat trajectory purely as motivation for RQ4. *(Lean: both — (a) for the outcome step, keep (b) as the headline.)*

## 6 · Next step → RQ4 (2 min)
- Add a **14th question — "Would you contact this team?" (yes / borderline / no)** as an LLM-coded **outcome label**, in a *separate* pass (breaks circularity).
- Tighten the two noisy features; drop mutual_support.
- → gives the outcome labels for the **RQ4 yield curve** (does the cascade sort surface "contact-worthy" teams faster than the current lowest-score heuristic).

---

### Likely supervisor questions — answers ready
- **"Why 119 not 139?"** → template-based, outcome-independent exclusion; representative subset.
- **"Isn't feature→trajectory circular?"** → yes (raised in §5); external validation is cascade-state; fix is a separate outcome pass.
- **"Small n?"** → that's why we use the composite index (well-powered), not per-cell tests; deep-dive textures are n=8 *leads*, stated as such.
- **"Consistent vs correct?"** → 3× runs show consistency; no human ground truth for novel features, so no validity claim — cascade alignment is the external check.

*Sources: docs/qualitative/{README, llm-results, llm-type-portraits, llm-deep-dive, llm-writeup-guardrails}.md · notes/llm-dynamics-checklist-v1.md*
