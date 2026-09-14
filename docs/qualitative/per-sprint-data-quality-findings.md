# Per-sprint marks: data-quality audit & the reliability–validity gap

*Cohort audited: 2025_s1 (24 teams, 96 team-sprint cells, 3 shuffled runs each).*
*Trigger: reviewing the dashboard evidence for one team (Team 8 / "Status 418")
surfaced four issues; auditing the cohort turned them into a general finding.*

## TL;DR

The per-sprint **binary marks are reliable** (run-to-run agreement 86–96%, measured
earlier) **but the evidence behind them often is not**. Across 348 fired flags in
2025_s1, **69% had the three runs return *different* supporting quotes** for the same
flag, and a visible minority attach a quote that does not support — or outright
contradicts — the flag. Reliability ≠ validity: a flag can be stably reproduced and
still be wrong. This motivates an **evidence-grounded re-run** (a flag may fire only
with a directly-supporting verbatim quote) rather than trusting the mark alone.

## What we found

| # | Problem | Evidence | Root cause |
|---|---------|----------|-----------|
| 1 | Glued/unreadable snippet (`Forexample,myPRfor…`) | **23/634 (3.6%)** source journals in 2025_s1 have runs of 18+ letters with spaces lost; 11 teams affected | **Upstream text extraction** dropped internal spaces; the model quoted the broken text faithfully |
| 2 | A positive signal shown as a concern (amber) | "Members supported each other" rendered like a problem | Display only — positives weren't distinguished from concerns |
| 3 | Concern flag with a *contradicting* quote | e.g. `effort_imbalance` fired (2/3 runs) with a quote saying the team was *happy and balanced* | **LLM validity failure** — over-fires and attaches a non-supporting quote as "evidence" |
| 4 | Concern flag with an *irrelevant* quote | e.g. `core_subgroup_carried` fired on a quote describing an *even* frontend/backend split | **LLM semantic error** — misread "a core few carrying" as any sub-grouping |
| 5 | No author on a snippet ("Team journal") | — | Author never stored; **recoverable**: 96.5% (1018/1055) of quotes match exactly one member's journal |
| 6 | One snippet per flag | — | Only the first run's quote kept; up to 3 available (one per run) |

**Quote instability (the headline).** Of 348 consensus-fired flags:
- **69% (241)** had ≥2 *distinct* quotes across the runs that fired them — the mark is
  stable, the cited evidence is not.
- 0 fired flags had *no* quote at consensus.
- A positive-language heuristic flagged ~12 concern flags whose quote reads positive;
  manual review confirms a real (smaller) subset are genuine mismatches like #3/#4.

## What we changed now (from existing marks — no re-run)

- **#1** Glued text repaired centrally (`textrepair.resegment`, wordlist + DP) in
  `blobs._entries`, so the marking blob, dashboard and questionnaire all read clean
  text (0/634 glued afterwards).
- **#2** Positive signals (`mutual_support`, `harmonious_balanced`) tagged and rendered
  green, not amber.
- **#5** Each quote attributed to the member whose journal contains it. The **dashboard**
  shows the **real name** (local-only coordinator tool; recovered via the `anon_id`
  crosswalk + peer roster, "First Last"). The **questionnaire** shows the blinded
  **"Member X"** label instead.
- **#6** Up to 3 distinct quotes per flag, with substring-overlapping near-duplicates
  collapsed (keep the longest).
- **Questionnaire anonymisation** (`anonymise.py`): every real name in journal text and
  quotes is replaced with the matching "Member X" label (or `[teammate]` when it can't
  be attributed), and emails + UoA UPIs are stripped. Verified **0/634** own-team name
  leaks cohort-wide.

**#3/#4 are deliberately left visible** on the dashboard: the quote *is* the model's own
cited evidence for the flag, so it honestly shows the validity gap. The fix is the re-run,
not hiding the symptom.

## The evidence-grounded re-run (next)

`marking_sprint_v2` (step `sprint_v2`, `slurm/journal_sprint_v2.sh`) keeps the same 11
binaries but:
1. a flag is **present only if** the model supplies a verbatim quote that *directly*
   supports it — no quote ⇒ not present (attacks #3/#4 over-firing);
2. returns **1–3 quotes per flag, each tagged with its Member** (native #5/#6);
3. **tightens** the definitions the model misread (esp. `core_subgroup_carried` — an even
   frontend/backend split is explicitly *not* it).

Output goes to a **new** dir (`marks_sprint_v2/`) so we can compare v1 vs v2 on both
**reliability** (run-to-run agreement) and **validity** (does the quote support the flag)
— the latter is the metric v1 was missing.

### Suggested validity metric for the comparison
For each fired flag, does at least one cited quote *directly support* it? Score this
(human spot-check on a sample, or an LLM-as-judge with the flag definition) for v1 vs v2.
Expect v2's fired-flag count to drop (fewer unsupported flags) and support-rate to rise.

## Open questions
- Is the 3.6% glued-text rate similar in other cohorts? (repair is applied to all.)
- Does evidence-grounding hurt *recall* (miss real issues that lack a crisp quote)? The
  tutor study's blind-spot analysis is the external check.
