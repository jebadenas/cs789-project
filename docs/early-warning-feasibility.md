# Per-session peer data & the early-warning idea — feasibility

**Date:** 2026-09-08. **Scope:** can we turn the triage cascade into a *per-sprint
early-warning* signal for tutors, using data we already have? Short answer: **partly
— the journals are per-sprint, but the validated peer cascade only exists at two
timepoints (proposal + final), and the early one is mostly unreadable.**

Motivated by the tutor-tool discussion: tutors each own 6-7 capstone teams, read the
journals to mark them, never see the peer-rating data, and work in 3-4 sprints each
with a journal + a peer round. That structure suggested an early-warning tool. This
note records what the data actually supports.

## 1. What we have, per sprint

- **Journals are per-sprint and re-cuttable now.** `journal_index` cleanly separates
  4-5 journals per team. Journal 1 is a standalone **intro/expectations reflection**
  (longest; 67% intro-language vs 34-47% for later ones; and every cohort has exactly
  one more journal than peer sessions). Journals 2..N are the per-sprint work
  reflections, pairing **journal _k+1_ ↔ peer session _k_**.
- **Per-session peer exports were recovered** into `data/peer_sessions/` (Sessions
  1..4 for all four LLM-study cohorts; git-ignored, real names, cluster-forbidden).

## 2. The catch: the cascade only reads the *points* question

The validated parser (`src/parsing/parser.py`) extracts **only the
points-distribution question** into score matrices. Points are collected in exactly
two sessions:

| Session | Points questions | Matrices parsed (S2-2024) |
|---|---|---|
| 1 (project **proposal**) | 1 | 43 |
| 2, 3 (mid-sprints) | **0** | **0** |
| 4 (**final**: code / report / poster) | 3 | 129 |

Sessions 2-3 carry only contribution-% (CC/PC) and Likert behaviours — which the
parser ignores. So with the existing instrument there is **no cascade for the middle
sprints**: the peer cascade is two snapshots (proposal, final), not a trajectory.

## 3. Prototype — does the proposal cascade foreshadow the final one?

`scripts/prototype_proposal_vs_final.py` computes the proposal-stage pooled state for
the four study cohorts and cross-tabs it against the final `pooled_state`.

**Result (118 teams):**
- **57% (67/118) are Silent/incomparable at proposal.** The proposal has a *single*
  points question, so the pooled cascade can't clear its comparability bar for many
  teams (an N=4 rater pair shares only 2 recipients × 1 question < 3). Dominant
  proposal states are Silent-flat (33) and Silent-lone-dissenter (32) — i.e. too few
  qualifying raters to order anyone.
- **The signal that remains is weak/noisy.** Collapsed to flag / calm / silent:

  | proposal ↓ / final → | calm | flag | silent |
  |---|---|---|---|
  | flag (30) | 12 | 14 | 4 |
  | calm (20) | 5 | 15 | 0 |
  | silent (66) | 30 | 20 | 16 |

  A proposal "flag" splits ~evenly at final; proposal "calm" teams frequently end up
  flagged. No clean early→late predictive story falls out.

## 4. Verdict

- **Journal-only early warning is buildable now** (journals 2..N, per sprint) — the
  strongest thing runnable on existing data without new instruments.
- **Peer-cascade early warning is thin with the validated instrument**: two
  timepoints, and the proposal snapshot is >50% unreadable. Not a per-sprint
  trajectory, and a poor standalone early signal.
- **A real per-sprint peer trajectory needs a different instrument** — the
  contribution-estimate (CC/PC) is present in *every* session but is (a) not parsed
  today and (b) single-column, so it hits the same N=4 comparability wall and would
  need pooling with Likert. That is genuine new parser + cascade work, and a *new*
  (unvalidated) instrument, not a re-slice.

## 5. Questions for the course coordinator

1. Confirm journal 1 = intro reflection, and the journal_{k+1} ↔ session_k pairing.
2. Why is the **points** step collected only at proposal + final (not mid-sprints)?
   That design choice is what caps the peer trajectory at two timepoints.
3. Is per-sprint peer scoring likely to continue unchanged in future cohorts (matters
   for a prospective vs retrospective tool study).

## Reproduce

```
python3 -m scripts.prototype_proposal_vs_final     # proposal vs final cross-tab
```
Per-session exports: `data/peer_sessions/`. Final states:
`output/dynamics2/pooled/team_states.csv`. Journal structure: `journal_index` in
`data/journals/processed/entries.parquet`.
