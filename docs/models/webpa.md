# WebPA Peer-Assessment Factor Model

## Theoretical Background

WebPA is a peer-assessment factor model introduced by Willey and Gardner (2010) as part of
the WebPA online peer-assessment system. It computes a PA (Peer Assessment) factor for each
student based on the ratio of scores they received to the team average.

Each student in a team of N distributes a fixed pool of 10×N points among all teammates
(including themselves). The PA factor for student i is:

```
PA_i = Σ(j=1..N) s_ji / mean(Σ(j=1..N) s_j1, ..., Σ(j=1..N) s_jN)
```

where s_ji is the score awarded to student i by peer j (including self-scores). The
denominator is the mean of total scores received across all students.

The IWF is then:

```
IWF_i = PA_i × 10
```

This guarantees **grade neutrality** — the team mean IWF is always exactly 10.0.

### Self-scores

Unlike baseline, PeerRank, and PeerHITS, WebPA **includes self-scores** in the calculation.
This is faithful to the original Willey and Gardner formulation. A student's self-assessment
contributes to their total received score alongside peer assessments.

### Non-submitter handling

Non-submitters have an all-NaN column in the score matrix. Their scores are excluded via
NaN-safe summation (`nansum`), contributing zero to every student's received total.

Because WebPA is a **ratio model**, a non-submitter's absence affects all students on the
team equally — every student loses one source of incoming scores. The relative ratios between
students are unchanged, so the non-submitter's absence does not distort the ordering or
inflate/deflate any individual's IWF.

The non-submitter themselves still receives an IWF computed from the scores their peers gave
them. Unlike the iterative models (PeerRank, PeerHITS), WebPA does not suffer from the
non-submitter amplification bug documented in Issue #24.

### Known limitations

**Self-score inflation.** Because self-scores are included, a student can boost their own
IWF by awarding themselves a disproportionately high self-score. This is a known trade-off
of the Willey and Gardner design.

**Equal rater weight.** Like baseline, all submitting raters contribute equally regardless
of their own credibility or assessment quality. There is no mechanism to discount unreliable
or strategic raters.

**No convergence.** WebPA is a single-pass calculation — it cannot iteratively refine
estimates based on rater credibility the way PeerRank and PeerHITS do.

---

## Algorithm Walkthrough

1. For each student i, sum all scores they received (including self-score), skipping NaN.
2. Compute the mean of those sums across all students.
3. Divide each student's sum by the mean to get PA_i.
4. Multiply by 10 to get IWF_i.

---

## Implementation Notes

**File:** `src/models/webpa.py`

The implementation uses `np.nansum` to compute scores received per student, which
automatically skips NaN values from non-submitter columns.

```python
scores_received = np.nansum(score_matrix.matrix, axis=1)
mean_scores_received = scores_received.mean()
pa_factors = scores_received / mean_scores_received
iwf_vector = pa_factors * 10.0
```

**Self-scores included:** No diagonal exclusion is performed, matching the original
Willey and Gardner formulation.

**Division by zero guard:** If all scores in the matrix are zero, a `ValueError` is
raised rather than producing NaN/Inf results.

**Returns:** A `ModelResult` with:
- `model_name`: `"WebPA"`
- `iwf_vector`: numpy array of length N (team mean = 10.0)
- `students`: list of `StudentInfo` objects
- `converged`, `iterations`, `final_l1_norm`: all `None` (not applicable)

---

## Example

### Input matrix

3 students: A, B, C. `matrix[i][j]` = score giver j gave to recipient i.

```
          A(j=0)  B(j=1)  C(j=2)
A(i=0)  [  10,      6,      8  ]
B(i=1)  [  12,     10,     14  ]
C(i=2)  [   8,     14,     12  ]
```

### Computation

Self-scores are included:

```
scores_received_A = 10 + 6 + 8   = 24
scores_received_B = 12 + 10 + 14 = 36
scores_received_C = 8 + 14 + 12  = 34

mean_scores_received = (24 + 36 + 34) / 3 = 31.333

PA_A = 24 / 31.333 = 0.766
PA_B = 36 / 31.333 = 1.149
PA_C = 34 / 31.333 = 1.085

IWF_A = 0.766 × 10 =  7.660
IWF_B = 1.149 × 10 = 11.489
IWF_C = 1.085 × 10 = 10.851
```

Team mean IWF = (7.660 + 11.489 + 10.851) / 3 = 10.000 ✓

### Expected output

```
iwf_vector = [7.660, 11.489, 10.851]
```

---

## References

- Willey, K. and Gardner, A. Investigating the capacity of self and peer assessment
  activities to engage students and promote learning. *European Journal of Engineering
  Education*, 35(4):429–443, 2010.
