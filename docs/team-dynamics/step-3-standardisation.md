# Step 3 — Standardisation

**Source:** `sklearn.preprocessing.StandardScaler`, called in the pipeline before classification

## The problem we're solving

After Step 2, each team is represented by 25 numbers. But look at the range of values:

- `reciprocity` is always between **-1 and 1** (small numbers)
- `mean_rater_std` might be around **4.2** (raw score spread)
- `triad_003` might be **0.0001** (a tiny fraction)

If you compare two teams by measuring "how far apart" their 25 numbers are, the features with big numbers will dominate the comparison — not because they're more important, but just because they're bigger. That's a bug, not a feature.

**Standardisation is the fix.** It rescales every feature so they're all on the same playing field before any comparison happens.

---

## What standardisation does

It transforms each feature using this formula:

```
z = (x - mean) / std
```

Where:
- `x` = the raw value for a team
- `mean` = the average of that feature across all teams
- `std` = how spread out that feature is across all teams
- `z` = the result — called a **z-score**

You're asking: *"How far is this team from average, in units of spread?"*

A z-score of:
- **0** → exactly average
- **+2** → two standard deviations above average
- **−1** → one standard deviation below average

After this transform, every feature has mean = 0 and standard deviation = 1. They're all on the same scale.

---

## Real-world analogy

Imagine comparing students across two subjects: Maths (out of 100) and Art (out of 10).

Alice: 80 in Maths, 7 in Art.
Bob: 60 in Maths, 9 in Art.

You can't just add raw numbers — 80 is 10× bigger than 7 just because of how each subject is graded. But if you convert each to a z-score ("how far above average for this subject"), you can compare fairly.

That's exactly what standardisation does here.

---

## Where it happens in the code

The scaler is trained on all real team data, then used to transform both the real teams and the archetypes:

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)   # learn mean/std from real data, then scale it

arch_scaled = scaler.transform(arch_raw) # apply the same formula to archetype vectors
```

**Why use the same scaler for both?** Because the archetypes need to live in the same coordinate system as the real teams. If you scaled them separately, the distances would be meaningless.

---

## The Fit-then-Transform pattern

This is a standard machine learning pattern:

1. **Fit** — learn the statistics (mean, std) from your data
2. **Transform** — apply those statistics to convert the data

You fit once. You transform everything else — archetypes, new incoming teams — using those same learned statistics. Never fit again on new data, or the scaling changes and comparisons break.

---

## Why this matters for the next step

Step 5 measures how far each team is from each archetype. That distance only makes sense if all features are on the same scale.

Without standardisation: a team that differs from an archetype by 0.1 in `reciprocity` and 3 in `mean_rater_std` would look "further away" because of the raw units — even if the `reciprocity` gap is more unusual.

After standardisation: 1 unit of difference means the same thing across all features — "one standard deviation away from normal."

---

## Key concept to remember

Standardisation converts each feature to "how many standard deviations from average." This means features don't compete based on the size of their units — only on how unusual a team actually is.
