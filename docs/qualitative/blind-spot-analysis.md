# Blind-spot analysis: where journals see what peer scores miss

> Script: `scripts/blind_spot.py` (reproduces all numbers below).
> Data: 433 (team, sprint) cells across 4 cohorts (2023_s2, 2024_s1, 2024_s2, 2025_s1).
> Mapping: journal_index *j* → peer Session (*j* − 1). Threshold: min PC ≥ 85.
> Date: 2026-09-22.

---

## The claim

Peer assessment measures **contribution** — it catches freeloaders. It is structurally
blind to a team that contributes evenly yet is falling apart (conflict, communication
breakdown, leadership vacuum). Reflective journals see that. This analysis quantifies
the mismatch and shows it has **predictive** value.

---

## 1. Headline: 65% of journal-flagged cells are peer-invisible

Of the 122 cells where the LLM journals flag at least one non-contribution dynamic
(open conflict, communication breakdown, or leadership problem), **79 (65%)** have
peer-contribution scores that look fine (every member's PC ≥ 85). The blind-spot rate
is stable across cohorts (2023_s2: 31, 2024_s1: 10, 2024_s2: 21, 2025_s1: 17).

## 2. Per-flag breakdown: which dynamics the peers miss

**Non-contribution dynamics** are peer-invisible at high rates:

| Flag | Fires | Peer fine | Blind-spot rate |
|------|------:|----------:|----------------:|
| open_conflict | 30 | 20 | **67%** |
| leadership_problem | 47 | 31 | **66%** |
| communication_breakdown | 92 | 59 | **64%** |

**Contribution dynamics** follow a gradient — the more clearly the dynamic maps to
unequal output, the more the peer scores pick it up:

| Flag | Fires | Peer fine | Blind-spot rate |
|------|------:|----------:|----------------:|
| singled_out_below | 60 | 23 | 38% |
| core_subgroup_carried | 83 | 45 | 54% |
| effort_imbalance | 133 | 75 | 56% |
| underperformance_unaddressed | 164 | 96 | 59% |
| member_under_contributed | 229 | 147 | 64% |

`singled_out_below` (38%) is the only flag the peers reliably catch — when one member
is singled out as the weakest, the contribution scores reflect it more than half the
time. At the other end, `member_under_contributed` (64%) fires so broadly that it
often describes a mild pattern the peer numbers don't register.

**Asymmetry.** For all three non-contribution flags, when the journal flags them,
~64–67% of the time the peer scores show nothing. These are complementary signals
measuring different constructs, not redundant readings of the same one.

## 3. Blind-spot cells are functioning-but-fraying teams

Of the 79 blind-spot cells (peer fine + non-contribution flag fired):

- **91%** also have `mutual_support` firing — members still help each other.
- Only **9%** have `harmonious_balanced` — things are not harmonious.

These teams have not collapsed. They are contributing evenly and supporting each other,
but friction is building underneath — conflict, communication breakdown, or a
leadership vacuum. Exactly the kind of team a coordinator would want to check in on
but would never find from the peer scores alone.

## 4. Blind-spot flags predict later peer decline (p = 0.003)

**Sprint k → k+1:** when a blind-spot cell occurs at sprint *k* (journal flags
conflict/comms/leadership, peer contribution fine), there is a **31% chance the peer
scores drop below threshold at sprint *k*+1** — vs a **14% base rate** among cells
with no non-contribution flag and fine peer scores. Fisher exact OR = **2.71**,
one-sided p = **0.003**.

The journals see trouble a sprint before it shows up in the numbers.

### Per-flag predictive odds ratios

| Flag | Fire → drop | Fire → ok | Rate | Base | OR | p |
|------|------------:|----------:|-----:|-----:|---:|--:|
| leadership_problem | 11 | 14 | 44% | 16% | **4.18** | 0.002 |
| core_subgroup_carried | 14 | 23 | 38% | 15% | **3.37** | 0.002 |
| effort_imbalance | 20 | 38 | 35% | 14% | **3.25** | <0.001 |
| communication_breakdown | 16 | 33 | 33% | 15% | **2.70** | 0.006 |
| member_under_contributed | 31 | 84 | 27% | 12% | **2.76** | 0.002 |
| underperformance_unaddressed | 22 | 53 | 29% | 14% | **2.52** | 0.005 |
| open_conflict | 3 | 11 | 21% | 18% | 1.21 | 0.50 |

`leadership_problem` is the strongest predictor (OR = 4.18): when the journal flags a
leadership vacuum and the peer scores look fine, there is a 44% chance the peer scores
deteriorate next sprint. `open_conflict` is not predictive, but fires rarely (n = 30
total; only 14 transitions in the predictive window) — likely a power issue.

### Early → late trajectory

Teams with a blind-spot cell in their early sprints show a later peer decline 51% of
the time, vs 34% for teams without (OR = 2.07, p = 0.051 — borderline, n = 119 teams
with ≥2 sprints).

## 5. Mapping check: journals and peers agree on contribution

As a sanity check on the Session *k* ↔ Journal (*k*+1) mapping: when peer scores flag
low contribution (min PC < 85), the journals also report contribution imbalance
(`effort_imbalance` or `member_under_contributed`) **85% of the time**. The two
instruments agree when measuring the same construct — the divergence in §§1–4 is a
genuine construct difference, not a mapping artefact.

---

## Caveats

- **Threshold sensitivity.** The 85 PC threshold is provisional. `--th 90` raises the
  blind-spot count (more cells count as "peer fine"); `--th 80` lowers it. The
  qualitative pattern (non-contribution flags ≫ contribution flags in blind-spot rate)
  is stable across 75–95; confirmed 58–72% range in `plans/dashboard-study-design.md` §11.
- **Multiple testing.** The per-flag predictive ORs are 9 tests. At Bonferroni α = 0.006,
  `effort_imbalance` (p < 0.001), `leadership_problem` (0.002), `core_subgroup_carried`
  (0.002), and `member_under_contributed` (0.002) survive. `communication_breakdown`
  (0.006) and `underperformance_unaddressed` (0.005) are borderline.
- **Non-independence — addressed with GEE.** Multiple sprints per team. A GEE
  (exchangeable correlation, logistic link, team clusters) gives OR = **2.66**, robust
  SE = 0.340, z = 2.87, p = **0.004** (two-sided) / **0.002** (one-sided). The
  within-team correlation is low (ρ = 0.037), so clustering barely changes the
  estimate (simple logistic: OR = 2.71, p = 0.003). Per-flag GEE: `leadership_problem`
  OR = 3.11 (p = 0.023), `communication_breakdown` OR = 1.95 (p = 0.10),
  `open_conflict` OR = 0.73 (p = 0.60). Script: `scripts/blind_spot.py --gee`.
  259 transitions across 117 teams.
- **LLM as coder.** The journal flags are LLM-generated (Qwen2.5-72B, 3 shuffled runs,
  majority consensus). Reliability is 80–98% for the binary flags used here
  (`llm-reliability-diagnosis.md`). The **tutor validation study** is what establishes
  whether the flags are *valid*, not just reliable.
- **Peer "fine" ≠ team fine.** PC ≥ 85 means no one member is rated as contributing
  markedly less. It does not mean the team is healthy — it means the contribution
  instrument has nothing to report.

---

## What this means for the dissertation

1. **§5 Results:** the blind-spot rate (65%) and the per-flag breakdown give the
   structural-blindness argument in concrete, per-dynamic terms. The predictive
   result (OR = 2.71, p = 0.003) is the practical argument for the tool: journals
   see trouble a sprint before the peer scores do.
2. **§6 Discussion:** `leadership_problem` as the strongest predictor (OR = 4.18)
   is worth a paragraph — leadership vacuums are invisible to a contribution instrument
   and are the clearest category of "falling apart while contributing evenly".
3. **The functioning-but-fraying characterisation** (91% mutual_support, 9%
   harmonious_balanced) gives the qualitative texture: these are not broken teams,
   they are teams with friction building under the surface.
4. **RQ4 framing:** the headline is now stronger than "the cascade sorts teams into
   readable and unreadable". It is: *"the journal signal complements the peer signal,
   surfacing a category of at-risk team the existing instrument misses — and it
   predicts escalation."*

---

## To deepen (open threads)

- [ ] **Which dynamics diverge most** — is it always the same flags, or does the
  mix shift across cohorts / across early vs late sprints?
- [x] **Case studies** — 5 blind-spot cells with confirmed next-sprint decline, read in
  detail: `docs/qualitative/blind-spot-case-studies.md`. Cross-case patterns: leadership
  flags dominate, sprint 1 is the weakest point for peer scores, flat PCs are the
  riskiest signal, journals capture a gradient not a binary, under-performance is noted
  but not confronted.
- [ ] **Does divergence predict a poor team mark?** (Blocked on Q11 — raw team project
  marks from the coordinator.)
- [x] **GEE for non-independence** — GEE (exchangeable, team clusters) confirms the
  headline: OR = 2.66, robust p = 0.004 (two-sided). Within-team correlation ρ = 0.037
  (low), so clustering barely changes the estimate. Per-flag: `leadership_problem`
  OR = 3.11 (p = 0.023). Script: `--gee` flag.
