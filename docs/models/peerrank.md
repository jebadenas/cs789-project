# PeerRank Model

## Theoretical Background

PeerRank is a fixed-point iterative algorithm introduced by Walsh (2014) for peer assessment.
It is directly inspired by Google's PageRank algorithm (Page et al., 1999): just as a web
page is considered authoritative if it is linked to by other authoritative pages, a student
is considered a strong contributor if they are rated highly by other strong contributors.

The key insight is **credibility weighting**: a student rated poorly by their team has their
votes dampened in subsequent iterations. This creates a structural incentive for honest
grading — inflating a peer's score when you yourself are poorly-rated has diminishing effect.

### The normalised score matrix

Let s_ji denote the score awarded to student i by peer j (i.e. `matrix[i][j]` in code).
The first step is to convert raw scores into fractions of each giver's budget:

```
a_ji = s_ji / Σ(k≠j) s_jk
```

where the denominator sums over all recipients excluding j's self-score. So a_ji represents
the fraction of j's total peer budget allocated to student i. Every non-NaN column of A
sums to exactly 1.0.

### The update rule

Grades are represented as a vector X where X_i is student i's current grade estimate.
At each iteration t, grades are updated as:

```
X_i^(t+1) = (1 - α) × X_i^(t)  +  α × [ Σ(j≠i) X_j^(t) × a_ji ] / [ Σ(j≠i) X_j^(t) ]
```

where α ∈ (0, 1) is the learning rate. The update is a blend of:
- The student's current grade (momentum term, weighted by 1-α)
- A credibility-weighted average of what peers think of them (weighted by α)

The credibility-weighted average gives more influence to peers who are themselves
highly graded. A peer j with a high X_j^(t) has their allocated fraction a_ji counted
more heavily.

### Convergence

Iteration continues until the L₁ norm of successive updates falls below a threshold ε:

```
Σ_i | X_i^(t+1) - X_i^(t) | < ε
```

### IWF conversion

After convergence, the grade vector is converted to IWFs by scaling relative to the
team mean:

```
IWF_i = X_i / X̄ × 10
```

where X̄ is the mean of the converged grade vector. This anchors the scale so that an
average student always receives IWF = 10.0.

---

## Algorithm Walkthrough

1. **Build normalised matrix A.** For each giver j, divide their peer scores by the sum
   of all peer scores they gave (excluding self). Non-submitters (NaN columns) are set to
   zero — they contribute no credibility weight. An all-zero non-NaN column raises a
   ValueError (malformed submission).

2. **Initialise grades.** Set X_i^(0) = (1/(N-1)) × Σ(j≠i) a_ji for all i, then
   normalise so Σ X_i^(0) = 1. This seeds the algorithm with a simple average of
   allocated fractions.

3. **Iterate.** For each student i, compute the credibility-weighted average of peer
   opinions and blend it with the current grade using the learning rate α. Repeat until
   convergence or the iteration cap is reached.

4. **Check convergence.** Compute the L₁ norm of the update after each full pass. Stop
   when it falls below ε = 10⁻⁶ (converged=True) or when max_iterations is reached
   (converged=False — not an error, just metadata).

5. **Convert to IWFs.** Divide each converged grade by the team mean and multiply by 10.

---

## Implementation Notes

**File:** `src/models/peerrank.py`

**Self-score exclusion.** The normalisation denominator excludes the diagonal (self-score).
This is checked before zeroing the diagonal entry to correctly distinguish a genuine
non-submitter (all-NaN peers) from a zero-self-score submitter.

**NaN vs zero.** In the COMPSCI 399 dataset, non-submission is encoded as `"No Response"`
which the parser converts to NaN — never as 0. Genuine zero scores exist (a student
deliberately giving a peer 0 points) and are meaningful. The implementation therefore
treats NaN columns as non-submitters and raises a ValueError for all-zero non-NaN columns.

**Learning rate.** α controls convergence speed, not the fixed point. A higher α converges
in fewer iterations but produces the same final IWF vector. Default α = 0.1 follows Walsh.

**Returns:** A `ModelResult` with:
- `model_name`: `"PeerRank"`
- `iwf_vector`: numpy array of length N
- `students`: list of `StudentInfo` objects
- `converged`: True if L₁ norm fell below ε, False if iteration cap was reached
- `iterations`: number of iterations performed
- `final_l1_norm`: L₁ norm of the last update step

---

## Example

### Input matrix

3 students: A, B, C. `matrix[i][j]` = score giver j gave to recipient i.
Diagonal = 0 (self-scores excluded from normalisation).

```
          A(j=0)  B(j=1)  C(j=2)
A(i=0)  [   0,      6,      3  ]
B(i=1)  [   3,      0,      6  ]
C(i=2)  [   6,      4,      0  ]
```

### Step 1 — Build normalised matrix A

Column sums (excluding diagonal):
- A gives: 3 + 6 = 9
- B gives: 6 + 4 = 10
- C gives: 3 + 6 = 9

Normalised fractions:
```
a_BA = 3/9  = 0.333   (A allocated 1/3 of budget to B)
a_CA = 6/9  = 0.667   (A allocated 2/3 of budget to C)
a_AB = 6/10 = 0.600   (B allocated 3/5 of budget to A)
a_CB = 4/10 = 0.400   (B allocated 2/5 of budget to C)
a_AC = 3/9  = 0.333   (C allocated 1/3 of budget to A)
a_BC = 6/9  = 0.667   (C allocated 2/3 of budget to B)
```

### Step 2 — Initialise grades

```
X_A^(0) = (a_BA + a_CA) / 2 = (0.600 + 0.333) / 2 = 0.467
X_B^(0) = (a_AB + a_CB) / 2 = (0.333 + 0.667) / 2 = 0.500
X_C^(0) = (a_AC + a_BC) / 2 = (0.333 + 0.400) / 2 = 0.533 (wait — a_AC and a_BC)
```

Wait — corrected:
```
X_A^(0) = (a_BA + a_CA) / 2   where a_BA = B's fraction to A, a_CA = C's fraction to A
        = (0.600 + 0.333) / 2 = 0.467
X_B^(0) = (a_AB + a_CB) / 2
        = (0.333 + 0.667) / 2 = 0.500
X_C^(0) = (a_AC + a_BC) / 2
        = (0.667 + 0.400) / 2 = 0.533
```

Normalise so Σ = 1:  sum = 1.500
```
X^(0) = [0.311, 0.333, 0.356]
```

### Step 3 — First iteration (α = 0.1)

For student A:
```
weighted  = X_B × a_BA + X_C × a_CA = 0.333×0.600 + 0.356×0.333 = 0.200 + 0.119 = 0.319
peer_sum  = X_B + X_C = 0.333 + 0.356 = 0.689
update    = 0.319 / 0.689 = 0.463
X_A^(1)  = 0.9×0.311 + 0.1×0.463 = 0.280 + 0.046 = 0.326
```

For student B:
```
weighted  = X_A × a_AB + X_C × a_CB = 0.311×0.333 + 0.356×0.667 = 0.104 + 0.237 = 0.341
peer_sum  = X_A + X_C = 0.311 + 0.356 = 0.667
update    = 0.341 / 0.667 = 0.511
X_B^(1)  = 0.9×0.333 + 0.1×0.511 = 0.300 + 0.051 = 0.351
```

For student C:
```
weighted  = X_A × a_AC + X_B × a_BC = 0.311×0.667 + 0.333×0.400 = 0.207 + 0.133 = 0.340
peer_sum  = X_A + X_B = 0.311 + 0.333 = 0.644
update    = 0.340 / 0.644 = 0.528
X_C^(1)  = 0.9×0.356 + 0.1×0.528 = 0.320 + 0.053 = 0.373
```

This continues for 104 iterations until convergence (L₁ norm < 10⁻⁶).

### Converged result

```
X = [0.465, 0.511, 0.527]
X̄ = 0.501

IWF_A = 0.465 / 0.501 × 10 =  9.278
IWF_B = 0.511 / 0.501 × 10 = 10.196
IWF_C = 0.527 / 0.501 × 10 = 10.526
```

Student C is rated most highly — their peers allocated them the largest fractions of budget,
and those peers were themselves credible raters.

---

## References

- Walsh, T. The PeerRank method for peer assessment. In *Proceedings of the 21st European
  Conference on Artificial Intelligence (ECAI 2014)*, pages 909–914. IOS Press, 2014.

- Page, L., Brin, S., Motwani, R., and Winograd, T. The PageRank citation ranking: Bringing
  order to the web. Technical Report 1999-66, Stanford InfoLab, 1999.
