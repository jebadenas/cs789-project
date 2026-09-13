# Supervisor Meeting Prep — 2026-05-19

**Date:** 2026-05-19
**Topics:** RQ3 pivot, new results, data-quality finding, more data

> **Read `agenda-2026-05-19.md` first** — that is the simple, in-order,
> read-aloud version. This file is the detailed backup: deeper
> explanations and answers to likely follow-up questions.

---

## What to Actually Say — Script

### Opening (1 min)

> "Since last time I've made a significant change to the RQ3 approach. The
> 5-label classification wasn't working — I found out why, fixed it, and
> the new results are more interesting. I also discovered a data-quality
> problem that I think is worth discussing."

---

### Why the old method failed (2 min)

> "The original method classified each team into one of five types —
> Cohesive, Collusive, Free-rider, Dominant, Conflict — by measuring how
> close each team was to five hand-crafted example matrices. The problem:
> 102 of 105 teams ended up labelled Cohesive."

> "That's not a real finding — it's a calibration failure. The five
> example matrices I built were too extreme. They sit so far from where
> real teams actually land that every real team is nearest the
> least-extreme one, which is Cohesive. The classifier always returned
> an answer, but the answer was meaningless."

_If she asks why not just recalibrate the examples:_

> "I looked into that. The deeper problem is that the data doesn't
> actually contain five distinct groups. I tested this using something
> called bootstrap stability — I'll explain that in a second — and the
> result was clear: the data only robustly supports two groups, not five."

---

### Why a 5-type taxonomy isn't supported (2–3 min)

> "To check how many real groups exist, I tested every split from
> k=2 up to k=8 — two groups, three groups, all the way to eight.
> For each one I asked: if I re-ran this split on a slightly different
> random sample of the teams, would I get the same groups back?"

> "If yes — the groups are real structure in the data."
> "If no — I'm inventing structure that isn't there."

> "I didn't choose two groups — the data told me two was the only
> honest answer. It was the only value of k where the split was
> stable. Everything from k=3 onwards collapsed to a coin flip."

> "To be specific: a standard fit metric called RSS suggested k=5
> as the best split — more groups always fits better, so RSS pointed
> there. But when I tested whether those five groups were actually
> reproducible, they weren't. k=2 was the only split that held up
> every time — stability of 0.92 out of 1. At k=5 it was 0.50,
> which is no better than random."

_If she asks how I ran this test:_

> "I used a method called Archetypal Analysis. The idea is: instead of
> finding the average team in each group, find the most extreme teams
> — the ones that best describe the edges of the data. Then I tested
> whether those extremes were real or just an artefact of which teams
> happened to be in the dataset."

> "To test that, I re-ran the analysis 50 times. Each time I randomly
> left out 20% of teams and re-ran on the remaining 80%. Then I asked:
> did I find the same extreme teams each time, or different ones?"

> "At k=2 — two extreme poles — the answer was yes, almost identical
> every time. Stability of 0.92. At k=5, the answer was no — I got
> completely different groups each time. Stability of 0.50, which is
> no better than random. So two poles are real. Five types are not."

_If she asks what 0.92 and 0.50 mean concretely:_

> "0.92 means: every time I re-sample 80% of the teams and re-run the
> split, I get basically the same two groups. 0.50 means: the five
> groups I get are completely different each time. There's no stable
> five-type structure in this data."

> "And the two groups aren't 'Type A teams' and 'Type B teams' — it's
> more like one big ordinary cluster and a small unusual tail. Most
> teams rate each other normally. A handful have something unusual
> going on."

---

### The new method and results (2 min)

> "So instead of forcing teams into five boxes, I now give each team a
> single continuous score — how unusual is their peer-rating behaviour
> compared to the average team? I call this the atypicality score."

> "The main result: teams flagged as atypical have a mean cross-model
> disagreement of 2.12, compared to 0.22 for typical teams. That's
> about a 10× difference."

> "The correlation between atypicality and model disagreement is
> r=0.37, p=0.02, on the 39 teams with clean data. Moderate but real
> and statistically significant."

_If she asks about the full-set correlation (r=0.51):_

> "The full-set correlation is 0.51, but that's inflated by a data
> quality problem I'll mention next. The honest number on clean data
> is 0.37."

---

### Data-quality finding (2 min)

> "This is the other thing I wanted to flag. Of the 105 team-matrices
> in the dataset, 66 have no usable signal — I'm calling these
> degenerate."

> "There are two causes. First, non-submitters: if even one person
> didn't fill in the peer form, the whole matrix has a gap. Second,
> flat scoring: some teams gave everyone identical points — everyone
> got 12 out of 60. That looks like perfect harmony but it's actually
> just form-clicking with no information."

> "When I break it down: 28 matrices are flat, 24 have a
> non-submitter, 14 have both. That leaves only 39 matrices from
> 18 teams with real signal. Of those 18 teams, only 6 are clean
> across all their questions."

> "The root cause is that we only have two course sessions — 2023 and
> 2024. 35 teams total before the attrition. I think we need more data."

---

### The data question (1 min)

> "Is there more peer-assessment data available beyond the two sessions
> I have? Other semesters, other courses? If yes, adding it would
> directly strengthen the analysis — more teams, less attrition
> pressure. If not, I'll frame thin-n as a structural limitation in
> the writeup."

---

### Closing ask (1 min)

> "Four things I'd like your input on:
> 1. Does the pivot from 5-label classification to continuous
>    atypicality scoring make sense to you methodologically?
> 2. Is there more data I can access?
> 3. How do you want me to handle the non-independence issue —
>    each team appears up to 3 times (once per question). Should
>    I aggregate to per-team, or is per-question fine with a caveat?
> 4. I want to add two attack vectors beyond the four in the
>    proposal — is that scope extension OK? (Detail below.)"

---

## Attack scope extension (sign-off ask)

> "Proposal §3.4 specifies four synthetic attacks. I want to run six.
> Two are extensions beyond the proposal — both research-backed:"

> "**#5 Strategic non-submission.** Not in the proposal — it's my own
> empirical finding. Iterative models (PeerRank/PeerHITS) *inflate* a
> non-submitter above students who did participate. Already documented
> (April diary entry). It's a genuine vulnerability, so I want it in the
> attack suite as a fifth vector."

> "**#6 Competitive sabotage.** A colluder deflates the *strongest*
> contributor to lift their own relative IWF. Distinct from the
> proposal's targeted down-vote — that one models social exclusion of a
> low-status member (Hall & Buzwell); this one is self-interested and
> targets the top contributor. Backed by the strategyproof-peer-grading
> literature (Catch Me if I Can; TSP; Dollar Partition). It needs one
> new citation."

> "I also checked a third candidate — reciprocal log-rolling — and
> *rejected* it: Song & Gehringer's own taxonomy classes it as
> small-circle collusion, which my zero-self partial-collusion variant
> already covers. I didn't want to pad the suite."

_The ask:_
> "Are you OK with six attacks instead of four, given #5 and #6 are
> evidence-based and #6 brings one new reference? Or would you rather I
> stay strictly within the proposal's four?"

_If she wants to minimise scope:_
> "Then #5 and #6 become a documented 'further vulnerabilities'
> subsection rather than full experimental vectors — the core four
> still answer RQ1/RQ2 as proposed."

---

## Key numbers to remember

| What | Value |
|---|---|
| Clean correlation (RQ3 headline) | r=+0.37, p=0.02, n=39 |
| Anomalous mean Δ | 2.12 |
| Typical mean Δ | 0.22 |
| Degenerate matrices | 66 / 105 |
| Usable teams | 18 of 35 |
| k=2 stability | 0.92 (robust) |
| k=5 stability | 0.50 (coin flip) |

---

## If the conversation goes off-script

**If she defends the 5-label taxonomy:**
> "The issue isn't the labels themselves — it's that the data can't
> reproduce those groups under resampling. If we get more data, it's
> worth retesting whether five groups become stable."

**If she questions the data-quality cutoff:**
> "I flagged non-submitters and zero-variation matrices. Both produce
> structureless fingerprints that contaminate the centroid estimate.
> I'm reporting results both with and without them so the impact is
> transparent."

**If she asks what's next:**
> "More data if available, re-run the pipeline, check whether the
> result strengthens. Then writeup of RQ3 as: atypicality score +
> binary flag + data-quality as co-headline finding."
