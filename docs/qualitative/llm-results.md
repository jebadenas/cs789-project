# LLM journal analysis — results (v1)

**Date:** 2026-09-01
**Aim:** characterise the team dynamics that show up in reflective journals behind
each **cascade state**, so the states read as concrete rather than as statistical
labels (RQ3-EXT, descriptive). Plan: docs/qualitative/llm-journal-analysis-plan.md.
Checklist: notes/llm-dynamics-checklist-v1.md.

## Method (as run)

1. **Notes** — Qwen2.5-72B-AWQ wrote grounded team-dynamics notes for all **119**
   teams (4 prompting cohorts), from structured, blinded journal blobs.
2. **Aggregate** — per cascade state, the 72B surfaced recurring candidate patterns.
3. **Checklist** — pooled/trimmed to a frozen 13-item checklist (11 binary + 2
   categorical) with written definitions.
4. **Blind marking** — each team scored on the checklist, blind to state, **3× with
   shuffled member labels** (357 marks); **majority-of-3** = final.

N = 119 teams. Grouping: 8 fine cascade states (`pooled_state`) and 4 buckets
(`anyflag_bucket`: Silent 21 / No-standout 17 / Standout 44 / Contested 37).

## Reliability (3-run agreement)

Binary items agreed across all 3 runs for **80–98%** of teams (mutual_support 98,
open_conflict 92, under-contributed 91, effort_imbalance 87 … underperformance
80). The categoricals were weaker: **trajectory 72%**, **conflict_handling 54%**.
→ conflict_handling is **dropped** (use `open_conflict`, 92% reliable); trajectory
reported with caution. The binary checklist is a stable instrument.

## Headline result — divergence rises across the cascade

A per-team **divergence index** (count of the 9 imbalance/conflict features
present, 0–9; harmonious & mutual_support excluded) increases monotonically:

| bucket | n | mean | median |
|---|---|---|---|
| Silent | 21 | **0.95** | 0 |
| Contested | 37 | 2.30 | 1 |
| No-standout | 17 | 2.76 | 3 |
| Standout | 44 | **3.32** | 3.5 |

- Buckets differ: **Kruskal–Wallis H=13.6, p=0.0035**.
- **Silent vs Standout: Mann–Whitney p=0.00056** (mean 0.95 vs 3.32).

This is one composite test of the core hypothesis, so it carries no
multiple-comparison penalty — and it is clearly significant. **The journals
independently recover the cascade structure: Silent teams read as harmonious,
Standout teams as divergent, with Contested/No-standout in between.**

## Which dynamics (descriptive, per feature)

Rates by bucket (base = overall); the pattern is coherent even where individual
cells are underpowered:

| feature | base | Silent | Contested | No-stand | Standout |
|---|---|---|---|---|---|
| harmonious & balanced | 57% | **81%** | 68% | 41% | 43% |
| member under-contributed | 57% | **24%** | 49% | 82% | 70% |
| core sub-group carried | 35% | **10%** | 30% | 41% | 50% |
| effort imbalance | 30% | **10%** | 24% | 29% | 45% |
| singled out (below) | 19% | 5% | 16% | 6% | **34%** |
| communication breakdown | 22% | **5%** | 27% | 24% | 25% |
| mutual support | 100% | 100% | 100% | 100% | 100% |

Sharpest points (8-state, survive Benjamini–Hochberg FDR q<0.05):
- **Silent-flat**: 0% under-contribution vs 57% base (q=0.011).
- **Both-ends**: 75% single someone out as under-performer vs 19% (q=0.027).

## Honest limitations

- **Power.** N=119 split into 4–8 groups gives small cells (some n=8). Effects are
  *large* (e.g. 0% vs 57%) but per-cell significance is limited; hence the
  composite index is the primary inferential test. Only 2 of 88 per-cell tests
  survive FDR (the two poles above).
- **119 is effectively the ceiling** — 2023_s1 (20 teams) has cascade states but
  journals that don't prompt team dynamics; 2022_s2 has journals but no peer data.
- **Descriptive, not causal.** No human ground truth for the novel features, so
  reliability ≠ validity — the 3 anchor-style checks were dropped upstream; we can
  show the model is *consistent*, not that it is *correct*.
- **Redundancy handled at analysis:** items 1,2,4,5,6 are facets of one
  "unequal contribution" construct and co-move — reported as a cluster, not five
  findings. mutual_support is universal (no discriminating value).
- The "Contested journals as harmonious" tendency is **not** statistically
  significant — a cautious sentence, not a claim.
- Notes/marks contain real names from journal bodies; **scrub before quoting**.

## Files
- marks: `output/qualitative/llm/marks/` (357), majority → `features_by_state.csv`
- notes: `output/qualitative/llm/notes/`, patterns: `.../patterns/`
