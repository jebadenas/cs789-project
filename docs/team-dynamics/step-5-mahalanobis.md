# Step 5 — Mahalanobis Classification

**Source:** `src/dynamics/classifier.py` → `fit_precision()`, `classify_teams()`, `_mahalanobis()`

## The goal

At this point we have:
- Each real team → a 25-number vector (standardised)
- 5 archetypes → 5 reference points (also standardised)

We want to ask: **which archetype is this team most similar to?**

Answer: measure the distance from the team to each archetype, pick the closest one.

But *which kind of distance?*

---

## Why not plain Euclidean distance?

Euclidean distance — the straight-line formula from school — treats all 25 features as equally important and completely independent.

But they're not independent. A team with high `clustering` probably also has high `triad_102` (buddy-pair triads). If you use plain Euclidean distance, you double-count that signal. It's like measuring someone's "unusualness" using both their height in cm *and* their height in inches — you're adding the same thing twice.

---

## Mahalanobis distance — the fix

**Analogy first:** imagine describing how unusual a person's body measurements are. Being 6'5" is unusual. Being 6'5" *and* 120kg is unusual in a *different* way — tall people tend to be heavier, so that combination is less surprising than 6'5" + 60kg. A good unusualness measure accounts for the typical correlation between height and weight.

Mahalanobis distance does exactly that for our 25 features. It stretches and rotates the space to account for how features typically co-vary, so correlated features don't get counted twice.

The formula:

```
d²(u, v) = (u − v)ᵀ · Σ⁻¹ · (u − v)
```

- `u` = real team's 25-dim vector
- `v` = archetype's 25-dim vector
- `Σ⁻¹` = the **precision matrix** (inverse of the covariance matrix)

The precision matrix carries all the information about feature correlations. Without it, you get plain Euclidean distance.

---

## Where the precision matrix comes from

The covariance matrix `Σ` is estimated from real team data — it describes how each pair of the 25 features moves together across all real teams.

Problem: 136 teams and 25 features is a small dataset. Estimating a 25×25 matrix from 136 points is noisy. The naive estimate can be unreliable or even singular (impossible to invert).

The fix is **Ledoit-Wolf shrinkage** — a regularisation technique that blends the sample covariance with a simpler, more stable form. Think of it as: "I don't fully trust my sample, so I'll hedge slightly towards a conservative default."

```python
# classifier.py → fit_precision()
from sklearn.covariance import LedoitWolf
precision = LedoitWolf().fit(X_scaled).precision_
```

`precision_` is `Σ⁻¹`, ready to use.

---

## Computing distance efficiently — Cholesky decomposition

Computing `(u-v)ᵀ Σ⁻¹ (u-v)` directly involves a matrix multiply for every team-archetype pair. Instead, the code uses a **Cholesky decomposition** — a one-time factorisation of the precision matrix:

```
Σ⁻¹ = L · Lᵀ
```

This turns the distance formula into a simple vector norm:

```
d = ||Lᵀ(u − v)||
```

```python
L = np.linalg.cholesky(precision)   # computed once before the loop

def _mahalanobis(u, v, L):
    y = L.T @ (u - v)
    return np.sqrt(np.dot(y, y))
```

`L` is computed once, then reused for every team-archetype comparison — same result, much faster.

---

## The classification loop

```python
for row in X_scaled:
    dists = [_mahalanobis(row, arch, L) for arch in archetypes]  # 5 distances
    label = ARCHETYPE_LABELS[np.argmin(dists)]                    # closest = winner
```

The team receives the label of whichever archetype it's closest to.

---

## Soft membership weights

As well as a hard label, the code computes **weights** — how much does each archetype contribute to this team's profile?

### The naive approach — and why it fails

You might think: just divide each distance by the total of all distances.

```
total = 1.2 + 4.5 + 5.1 + 4.8 + 5.3 = 20.9
Cohesive = 1.2 / 20.9 = 0.057   (6%)
```

But that's backwards — bigger distance means *less* similar, so Cohesive should get the **biggest** fraction, not the smallest.

### Step 1: flip the distances

Negate them so the closest archetype has the largest (least negative) value:

```
[-1.2, -4.5, -5.1, -4.8, -5.3]
```

### Step 2: apply softmax

```python
neg_d = -dists
neg_d -= neg_d.max()   # subtract largest value for numerical safety
exp_d = np.exp(neg_d)
weights = exp_d / exp_d.sum()
```

Working through the example:

```
neg_d after subtract max:  [0.0, -3.3, -3.9, -3.6, -4.1]
after exp():               [1.0, 0.037, 0.020, 0.027, 0.017]
after dividing by sum:     [0.91, 0.034, 0.018, 0.025, 0.015]
```

Cohesive gets 91% of the weight.

### Why exp() and not just divide?

**It amplifies differences.** `exp()` grows fast, so a small gap in distance becomes a large gap in weight. A clearly Cohesive team gets a weight close to 1.0, not just "a bit bigger than the others":

```
Without exp:  [0.26, 0.22, 0.19, 0.21, 0.18]  ← barely separated
With exp:     [0.91, 0.03, 0.02, 0.03, 0.02]  ← clearly separated
```

It also always produces positive numbers — `exp()` of any value is always > 0, so weights are always valid fractions.

### Why subtract the max first?

`exp()` of a large positive number overflows to infinity on a computer. Subtracting the max shifts all values to be ≤ 0, keeping `exp()` results between 0 and 1. The final fractions are mathematically identical — the constant cancels out in the division — but the numbers stay safe.

### What the weights tell you

```
Clear case:  [0.91, 0.03, 0.02, 0.03, 0.01]  → confidently Cohesive
Borderline:  [0.48, 0.44, 0.03, 0.03, 0.02]  → nearly tied: Cohesive vs Collusive
Ambiguous:   [0.25, 0.24, 0.24, 0.23, 0.04]  → no strong signal at all
```

The hard label only tells you the winner. The weights tell you how convincing the win was.

---

## Key concept to remember

Classification picks the closest archetype by Mahalanobis distance — a distance metric that accounts for feature correlations so no signal gets double-counted. Softmax converts the 5 raw distances into percentages: closer = bigger weight, with `exp()` amplifying differences so confident and borderline cases are clearly distinguishable.
