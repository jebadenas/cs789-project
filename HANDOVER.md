# Session Handover — 2026-05-18

## What to do first

**Build `src/attacks/`** — the synthetic attack simulation for RQ1 and RQ2.

Start the session by planning the approach (review Phase 4 of
`plans/peer-assessment-grading-engine.md` and proposal §3.4), then implement.
Do not start coding before aligning on the design.

---

## Why this is the priority (strategic reasoning)

The full analysis behind this decision is in
`plans/peer-assessment-grading-engine.md` (Status & forward roadmap section at
the top). Short version:

- **RQ1 (manipulation resistance) is the proposal's flagship question** — it
  calls it "the most practically urgent problem." The models are all built and
  working. The attack simulator is the only missing piece. It needs zero
  external data.
- **The project is ~week 9–10 of 15.** Attack simulation was scheduled for
  weeks 7–9. It is unbuilt. Writing starts week 11. This is the gap to close.
- **Almost all recent effort went into RQ3** (team-dynamics classification,
  two pivots). That work is done and parked. The effort allocation needs to
  rebalance toward RQ1/RQ2 now.
- **Real data is thin** (18 usable teams, 39 matrices). Synthetic teams with
  known ground-truth contribution vectors carry proportionally more weight for
  RQ1/RQ2 — lean on them.

---

## What the attack build should deliver

Per Phase 4 / proposal §3.4:

1. Four attack transforms on a `ScoreMatrix`: uniform inflation, zero-self
   (full + partial collusion), targeted down-vote, single outlier (Monte Carlo,
   100 perms)
2. Synthetic team generator — N×N matrices for N=4,5,6 with known
   ground-truth contribution vectors
3. Attack Delta metric + RQ2 convergence tracking under single-outlier
4. Applied to both clean real matrices and synthetic teams
5. Robustness bar charts with Monte Carlo error bars (Plotly, HTML export)
6. Include non-submitter amplification as a fifth documented vulnerability
   ("strategic non-submission") — already discovered, already documented in
   `docs/diary/2026-04-20-non-submitter-amplification.md`, just needs
   folding in

Closes Issues #9 and #10.

---

## Things to NOT do

- **Do not keep iterating on RQ3** (team-dynamics/atypicality). That work is
  complete. Issue #11 is closed and merged.
- **Do not block on external data.** Git metrics, journals, and more CSVs may
  arrive — they are possible but unconfirmed. Keep interface seams clean
  (Git Alignment stub already exists) but do not wait.
- **Do not reframe RQ3 without Anna's sign-off.** The dissertation framing
  (internal-consistency signal, not free-riding detection) needs to be agreed
  with her first. See `docs/meetings/supervisor-meeting-prep-2026-05-19.md`.

---

## Key context

**RQ3 framing:** The atypicality↔Δ result (r=0.37, p=0.02, n=39 clean) is an
*internal-consistency* claim — "unusual rating structures cause models to
disagree." It is NOT "Δ detects free-riding" — that requires Git data which
doesn't exist. Do not present or build on it as the stronger claim.

**Data-quality finding:** 35 teams total, only 18 usable, only 6 complete.
This is a co-headline result for RQ3, not a footnote. It also means synthetic
experiments are load-bearing for RQ1/RQ2.

**Supervisor meeting 2026-05-19 (tomorrow):** Meeting prep is at
`docs/meetings/supervisor-meeting-prep-2026-05-19.md`. Key agenda: RQ3 pivot
rationale, data-quality finding, and surfacing the data question (more CSVs /
Git / journals — what's the realistic path?). Get sign-off on RQ3/RQ4 scope
reframe.

---

## Authoritative docs to read if needed

| Doc | Purpose |
|---|---|
| `plans/peer-assessment-grading-engine.md` | Full plan — status table, RQ table, forward roadmap at top; Phase 4 spec below |
| `Badenas_Jos_421180443_Research_Proposal.pdf` | Source proposal — RQs (p.6), attack specs (§3.4, pp.9–10) |
| `docs/team-dynamics/findings-2026-05-17.md` | RQ3 pivot decision record + empirical results |
| `docs/diary/2026-04-20-non-submitter-amplification.md` | Non-submitter vulnerability finding |
| `docs/meetings/supervisor-meeting-prep-2026-05-19.md` | Anna meeting prep for tomorrow |
