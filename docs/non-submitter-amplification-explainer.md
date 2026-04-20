# Why PeerRank & PeerHITS Inflate Non-Submitters

> A plain-English explainer for the bug documented in [Issue #24](https://github.com/jebadenas/cs789-project/issues/24).

## The Setup

Imagine a team of 6 students. Five of them submit peer reviews giving everyone (including Robin) a score of **10**. Robin doesn't submit anything — their column in the score matrix is all NaN (missing).

```
          Giver →
           Alice  Bob  Carol  Dave  Eve  Robin
Alice        –    10    10    10    10    NaN
Bob         10     –    10    10    10    NaN
Carol       10    10     –    10    10    NaN
Dave        10    10    10     –    10    NaN
Eve         10    10    10    10     –    NaN
Robin       10    10    10    10    10    NaN
```

Everyone scored everyone the same. You'd expect all IWFs to come out equal at **10.0**. And for baseline and WebPA, they do.

But PeerRank gives Robin **12.631** and everyone else **9.474**. How?

## How Baseline Handles It (Correctly)

Baseline just averages the scores each person received, ignoring NaN:

- Robin received: 10, 10, 10, 10, 10 → mean = **10.0** ✅
- Alice received: 10, 10, 10, 10 (Robin's NaN skipped) → mean = **10.0** ✅

Simple. Fair. No problems.

## How PeerRank Creates the Problem

PeerRank is an **iterative** algorithm. It doesn't just average scores — it **weights** each rater's scores by how credible that rater is. Credibility is determined by how much a rater's scores agree with the current consensus.

Here's where it breaks down, step by step:

### Step 1: NaN → 0

Before iterating, the algorithm replaces Robin's NaN scores with **0**. Now Robin "gave" everyone a 0. The matrix looks like:

```
           Alice  Bob  Carol  Dave  Eve  Robin
Alice        –    10    10    10    10     0
Bob         10     –    10    10    10     0
...
Robin       10    10    10    10    10     0
```

### Step 2: Credibility Calculation

PeerRank asks: "How well does each rater's scores match the consensus?"

- **Alice, Bob, Carol, Dave, Eve** all gave 10s across the board → they **agree** with the consensus → **high credibility**
- **Robin** gave all 0s → completely **disagrees** with the consensus → **zero credibility**

### Step 3: Credibility-Weighted Averaging

Now scores are weighted by rater credibility:

- **Robin receives scores from:** Alice (credible, score 10), Bob (credible, score 10), Carol (credible, score 10), Dave (credible, score 10), Eve (credible, score 10) → **5 credible scores**
- **Alice receives scores from:** Bob (credible, 10), Carol (credible, 10), Dave (credible, 10), Eve (credible, 10), Robin (zero credibility, score 10 — but weight ≈ 0) → effectively **4 credible scores**

Robin's incoming scores all carry full weight. Everyone else loses one source of credibility (Robin's scores are worthless). So Robin's weighted average is **higher**.

### Step 4: Iteration Amplifies

The algorithm repeats steps 2–3 multiple times. Each round, Robin's advantage compounds:
- Round 1: Robin slightly higher → consensus shifts toward Robin being higher
- Round 2: Raters who scored Robin high gain more credibility → Robin even higher
- Round 3, 4, ... → keeps amplifying until convergence

### Step 5: Scaling to Team Mean

Finally, all IWFs are scaled so the team mean = 10.0. Robin is above average, so everyone else gets pushed **below** 10.0 to compensate.

**Result: Robin = 12.631, everyone else = 9.474**

## Why PeerHITS Has the Same Problem

PeerHITS uses a different algorithm (HITS instead of PeerRank) but the same pattern applies:

1. Non-submitter's scores become 0 → zero "hub" quality (assessment ability)
2. Non-submitter still receives full scores from everyone
3. Authority scores (the IWF output) get inflated for the non-submitter
4. Result: Robin = 12.0, everyone else = 9.6

## Why Baseline & WebPA Are Immune

Both are **non-iterative** — they compute a single-pass average or ratio. There's no credibility weighting, so Robin's missing scores don't create an asymmetry. NaN values are simply skipped.

## The Real-World Problem

This means a student could **strategically not submit** their peer review and potentially get a **higher grade** than teammates who participated honestly. That's the opposite of what peer assessment should incentivise.

Even without strategic intent, it's unfair: a student who forgot to submit shouldn't be rewarded for it.

## The Deeper Problem: Credibility Flows the Wrong Way

The current algorithms reward **being rated by** credible people, not **being** a credible rater:

| What the model rewards | Who benefits |
|---|---|
| Being **rated by** credible people | Recipients — including non-submitters who didn't participate |
| Being a **credible rater** yourself | Nobody's IWF — your credibility only amplifies your influence on *others'* scores |

This is backwards. In a fair system, submitting an honest review should benefit **you**, not just the people you rated. A student who puts in the effort to assess their peers carefully gets nothing for it in their own IWF.

### Why Not Reward Credible Raters Directly?

PeerHITS already computes a **hub score** — a separate measure of how good you are at assessing peers. But it keeps this completely separate from the authority score (the IWF). The hub score is informational only; it doesn't affect your grade.

A potential modification: **feed hub quality back into the IWF calculation.** If your hub score is high (you're a credible, accurate rater), your own IWF gets a boost. If your hub score is zero (you didn't submit), you get no boost — solving the non-submitter problem naturally without explicit penalties.

This would be a novel modification to the HITS-based approach — worth discussing as a potential research contribution.

### The Reciprocity Question

Should the model enforce **reciprocity** — requiring students to rate others in order to receive a credibility-weighted IWF? Options:

1. **Hard reciprocity:** Non-submitters are excluded entirely (IWF = NaN)
2. **Soft reciprocity:** Non-submitters fall back to a simpler model (e.g., baseline average) while submitters get the credibility-weighted result
3. **Hub-authority hybrid:** Hub score feeds into IWF, so non-submitters naturally get a lower result

## Proposed Fixes

| Strategy | How It Works | Trade-off |
|----------|-------------|-----------|
| **Exclude** | Remove non-submitters from model output entirely (return NaN for their IWF) | Instructor must handle separately; may affect team grade pool |
| **Impute** | Replace NaN column with team mean scores before running the model | Assumes non-submitter is "average"; may be too generous |
| **Penalise** | Cap non-submitter IWF at the team minimum or apply a fixed penalty | Punitive; may be unfair if non-submission was due to illness etc. |
| **Hub-authority hybrid** | Feed hub score back into IWF so non-submitters get no rater-quality boost | Novel approach; needs careful design and testing |

The best approach likely depends on the course policy. This is something to discuss with the supervisor.
