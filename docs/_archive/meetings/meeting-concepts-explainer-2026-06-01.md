# Plain-English Explainer — Meeting Concepts (2026-06-01)

This file explains every technical term used in the meeting agenda.
No prior knowledge assumed.

---

## What is this project about?

Students in COMPSCI399 (capstone project course) review each other's work by
giving teammates a score. This is called **peer assessment**.

The question is: are these peer scores fair? Can students cheat the system?
And can we tell which teams have unusual scoring patterns?

There are four **models** — different mathematical formulas — for turning raw
peer scores into a final grade weight called an **IWF** (Individual Weighting
Factor). Higher IWF = bigger share of the team mark.

The four models are:
- **Baseline** — simple average of scores received
- **WebPA** — a ratio formula, widely used in UK universities
- **PeerRank** — an iterative method that weights scores by how credible the rater is
- **PeerHITS** — another iterative method, tracks both "gave good scores" and "received good scores" separately

---

## What is a "matrix"?

A peer-assessment **matrix** is a table of scores. Rows = who received the score.
Columns = who gave the score. Each number is how much student A rated student B.

One matrix = one team, answering one peer-review question (e.g. "contribution to design").
Teams fill these in multiple times per semester (one per question).

---

## What are "degenerate" matrices?

A degenerate matrix has no useful signal. There are two types:

1. **Flat scoring** — everyone gave everyone else exactly the same score
   (e.g. everyone got 12/60). The team "played it safe" and clicked the
   same number for everyone. No information about who contributed more.

2. **Non-submitter gap** — one or more students didn't fill in the form at all.
   Their column is blank (NaN). This creates a hole in the data.

We exclude degenerate matrices from the main analysis. The agenda shows
both "clean" (degenerate excluded) and "full" numbers so the effect is transparent.

---

## What is RQ3? What is "atypicality"?

**RQ3** = Research Question 3. It asks: do teams with unusual peer-rating
behaviour cause more disagreement between models?

**Atypicality score** = a single number per team measuring how unusual their
scoring pattern is compared to a typical team. Think of it as a "weirdness meter."

- A low score = the team rated each other normally.
- A high score = the team has some unusual pattern (e.g. one person getting much
  higher/lower scores than everyone else, or a suspicious cluster of matching scores).

Teams with a high atypicality score are labelled **Anomalous**.
Teams with a low score are labelled **Typical**.

How it's calculated: we measure 24 features of each team's matrix (things like
how much scores vary, whether there are cliques, whether scores are reciprocal).
Then we use a statistical distance measure (**Mahalanobis distance**) to ask
"how far is this team from the average team?" — farther = more atypical.

---

## What is "model disagreement" (delta, Δ)?

Different models produce different IWF scores for the same student.
**Delta (Δ)** = how much the models disagree on a student's IWF.

Example: If Baseline gives Alice 10.5 and WebPA gives Alice 8.2,
the delta for Alice is 2.3 points. A big delta means the models
can't agree — which matters for fairness.

**RQ3 finding:** anomalous teams (high atypicality) have a mean delta
of 1.22, while typical teams have a mean delta of 0.32.
The models argue ~4× more when the team's scoring is unusual.

---

## What does the correlation (r) mean?

**Pearson's r** measures how strongly two things move together.

- r = 1.0 → perfect positive relationship (as one goes up, so does the other)
- r = 0.0 → no relationship at all
- r = -1.0 → perfect negative relationship

**r = 0.385** (our result) means: as atypicality goes up, model disagreement tends
to go up too. The relationship is moderate but consistent.

**p-value** = the probability that this result is a fluke if there's actually
no relationship. p < 0.001 means less than 0.1% chance it's random noise.
That's very strong evidence the relationship is real.

---

## What are the attacks? (RQ1)

**RQ1** tests whether students can game the system — deliberately change their
IWF by submitting strategic scores instead of honest ones.

Four attack strategies were tested:

| Attack name | What the student does |
|---|---|
| **Single outlier** | One student gives one teammate an extreme score (very high or very low) |
| **Targeted downvote** | One student gives a specific peer a score of zero to hurt their grade |
| **Uniform inflation** | A group of friends all give each other maximum scores |
| **Zero-self (collusion ring)** | A colluding group all leave self-assessment blank to confuse the model |

**Mean delta (Δ)** in the attack results = how many IWF points the attack moved someone.
A delta of 2.8 on WebPA for targeted downvote means: if you zero-score a teammate,
their IWF drops by about 2.8 points on average.

---

## What is RQ2? What is "convergence"?

PeerRank and PeerHITS are **iterative** models — they don't calculate the answer
in one step. Instead they start with a guess, improve it, improve it again,
and repeat until the answer stops changing.

**Convergence** = the point where the answer has stabilised enough to stop.

**RQ2** asks: do these models always converge? Or do they sometimes loop forever or blow up?

**Finding:** they always converge on our dataset. PeerHITS is fast (~10 rounds).
PeerRank is slower (~100 rounds), but reliable.

**Alpha (α)** = the "close enough" threshold. α=0.1 means "stop when the answer
changes by less than 0.1 between rounds." Smaller α = stricter = more iterations.

---

## What is "non-independence"?

Some teams appear multiple times in the dataset — once per peer-review question
(e.g. "contribution to design", "contribution to implementation", "contribution to testing").

If we treat each row as independent (separate data points), we're pretending
these are different teams. But they're not — it's the same people.

This is called a **non-independence problem**. We have two approaches:
1. **Per-matrix**: treat every row separately (n=217). More data, but rows within a team are correlated.
2. **Per-team**: average across questions first (n=84 teams). Less data, but truly independent rows.

Both analyses give similar results (r=0.385 vs r=0.465), which is reassuring.
We need the supervisor's view on which to present as the primary result.

---

## What is "assortativity"? (Why we dropped it)

**Assortativity** was feature #25 — a graph metric that measures whether
students with similar scores tend to rate each other. ("Do high scorers grade
other high scorers?")

It caused computational problems on very small teams (3–4 people) because
the calculation breaks down when there aren't enough nodes. We removed it
and now use 24 features. The results barely changed (r moved by less than 0.005).

---

## Key terms quick reference

| Term | Plain English |
|---|---|
| IWF | Individual Weighting Factor — your share of the team mark |
| Matrix | Table of peer scores for one team, one question |
| Degenerate matrix | Matrix with no useful info (everyone gave same score, or someone didn't submit) |
| Atypicality score | How unusual a team's scoring pattern is |
| Delta (Δ) | How much two models disagree on a student's IWF |
| Pearson's r | Correlation — how strongly two things move together (0 = none, 1 = perfect) |
| p-value | Probability the result is a fluke (p < 0.05 = unlikely to be random) |
| Convergence | Iterative model reaches a stable answer |
| Alpha (α) | "Close enough" threshold for convergence |
| Non-independence | Same people appearing in multiple rows of the dataset |
