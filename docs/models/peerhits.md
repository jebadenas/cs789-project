# PeerHITS Dual-Score Model

## Theoretical Background

PeerHITS adapts Kleinberg's HITS (Hyperlink-Induced Topic Search) algorithm to peer
assessment. In web search, HITS distinguishes between **authorities** (pages with good
content) and **hubs** (pages that link to good content). In peer assessment:

- **Authority** = contribution quality — how highly a student is rated by good assessors
- **Hub** = assessment quality — how well a student's ratings align with consensus

This dual-score approach is a key advantage over PeerRank: it produces a separate measure
of **rater credibility** (the hub score) alongside the IWF (the authority score).

### The update rules

Given an N×N score matrix M where M[i][j] = score giver j gave to recipient i, with
the diagonal zeroed (self-scores excluded):

```
authority_i = Σ(j≠i) hub_j × M[i][j]
hub_j       = Σ(i≠j) authority_i × M[i][j]
```

Authority is high when you receive high scores from high-hub (credible) raters.
Hub is high when you give high scores to high-authority (strong) contributors.

Both vectors are L2-normalised after each update to prevent unbounded growth.

### Convergence

Iteration continues until the L1 norm of successive authority updates falls below ε:

```
Σ_i | authority_i^(t+1) - authority_i^(t) | < ε
```

### IWF conversion

After convergence, both vectors are scaled so their mean equals 10.0:

```
IWF_i = authority_i / mean(authority) × 10
hub_i = hub_i / mean(hub) × 10
```

---

## Algorithm Walkthrough

1. **Prepare matrix.** Zero the diagonal (exclude self-scores). Convert NaN to 0
   (non-submitters contribute nothing).
2. **Initialise.** Set authority and hub vectors to `1/√N` (unit L2 length, uniform).
3. **Iterate.**
   - Compute new authority: `authority = M @ hub`
   - Compute new hub: `hub = M.T @ authority`
   - L2-normalise both vectors
   - Check convergence on authority L1 delta
4. **Scale.** Multiply both vectors so their means equal 10.0.

---

## Non-Submitter Handling

The core PeerHITS algorithm converts non-submitter NaN columns to zeros. This causes the
same **non-submitter amplification bug** as PeerRank (see Issue #24): the non-submitter
has zero hub quality but still receives full authority scores from credible raters.

Two variant models address this:

### PeerHITS-Impute

Replaces non-submitter NaN columns with equal raw scores (10 to every teammate including
self) before running the core algorithm. The diagonal is then zeroed as usual. This gives
the non-submitter **neutral hub quality** — they are treated as an average assessor.

### PeerHITS-Exclude

Removes non-submitter rows and columns entirely, running PeerHITS on the reduced submatrix
of submitting students only. Non-submitters receive **NaN** in both the IWF (authority) and
hub vectors. If fewer than 2 students submitted, all outputs are NaN.

---

## Implementation Notes

**File:** `src/models/peerhits.py` (core algorithm)
**Variants:** `src/models/peerhits_impute.py`, `src/models/peerhits_exclude.py`

The core implementation uses matrix multiplication for the HITS updates:

```python
new_authority = matrix @ hub
new_hub = matrix.T @ authority
```

**Self-scores:** Diagonal zeroed before iteration (`np.fill_diagonal(matrix, 0.0)`).

**L2 normalisation:** Each vector is divided by its L2 norm after every update. If the
norm is zero (degenerate case), the vector is returned unchanged.

**Scaling:** `_scale_to_mean_ten()` divides by the mean and multiplies by 10. If the
mean is zero, the vector is returned unchanged.

**Returns:** A `ModelResult` with:
- `model_name`: `"PeerHITS"` (core), `"PeerHITS-Impute"`, or `"PeerHITS-Exclude"`
- `iwf_vector`: authority scores scaled to team mean 10.0
- `hub_vector`: hub scores scaled to team mean 10.0
- `students`: list of `StudentInfo` objects
- `converged`: True if L1 norm fell below ε
- `iterations`: number of iterations performed
- `final_l1_norm`: L1 norm of the last authority update

---

## Example

### Input matrix

3 students: A, B, C. `matrix[i][j]` = score giver j gave to recipient i.

```
          A(j=0)  B(j=1)  C(j=2)
A(i=0)  [  10,      2,      3  ]
B(i=1)  [  15,     10,     14  ]
C(i=2)  [  15,      8,     10  ]
```

### Step 1 — Prepare matrix

Zero diagonal (self-scores):

```
          A(j=0)  B(j=1)  C(j=2)
A(i=0)  [   0,      2,      3  ]
B(i=1)  [  15,      0,     14  ]
C(i=2)  [  15,      8,      0  ]
```

### Step 2 — Initialise

```
authority = [0.577, 0.577, 0.577]   (1/√3 each)
hub       = [0.577, 0.577, 0.577]
```

### Step 3 — First iteration

Authority update (`M @ hub`):
```
authority_A = 0×0.577 + 2×0.577 + 3×0.577 = 2.887
authority_B = 15×0.577 + 0×0.577 + 14×0.577 = 16.732
authority_C = 15×0.577 + 8×0.577 + 0×0.577 = 13.272
```

L2 normalise: norm = 19.335
```
authority = [0.149, 0.865, 0.686]
```

Hub update (`M.T @ authority`):
```
hub_A = 0×0.149 + 15×0.865 + 15×0.686 = 23.270
hub_B = 2×0.149 + 0×0.865 + 8×0.686 = 5.789
hub_C = 3×0.149 + 14×0.865 + 0×0.686 = 12.559
```

L2 normalise: norm = 27.088
```
hub = [0.859, 0.214, 0.464]
```

Iteration continues until convergence.

### Converged result

Student B has the highest authority (received most from credible raters).
Student A has the highest hub (their high scores to B and C align with consensus).

---

## Relationship to PeerRank

| Aspect | PeerRank | PeerHITS |
|--------|----------|----------|
| Algorithm | PageRank-inspired fixed-point | HITS-inspired dual-score |
| Output | Single IWF vector | IWF (authority) + hub vector |
| Rater credibility | Implicit (peer grade = credibility) | Explicit (hub score) |
| Self-scores | Excluded | Excluded |
| Normalisation | Column fractions sum to 1 | L2 normalisation per iteration |

The hub score is a potential avenue for **rewarding credible raters** in their own IWF
(hub-authority hybrid) — see the non-submitter amplification explainer for discussion.

---

## References

- Kleinberg, J. M. Authoritative sources in a hyperlinked environment. *Journal of the
  ACM*, 46(5):604–632, 1999.

- Walsh, T. The PeerRank method for peer assessment. In *Proceedings of the 21st European
  Conference on Artificial Intelligence (ECAI 2014)*, pages 909–914. IOS Press, 2014.
