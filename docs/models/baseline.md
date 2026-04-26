# Simple Average (Baseline) Model

## Theoretical Background

The Simple Average model is the IWF (Individual Weighting Factor) formulation introduced by
Kaufman, Felder and Fuller (2000) and used directly by COMPSCI 399 at the University of
Auckland.

Each student in a team of N distributes a fixed pool of 10×N points among all teammates
(including themselves). The IWF for student i is the mean of all peer scores they received:

```
IWF_i = (1 / P_i) × Σ(j≠i, j∈S) s_ji
```

where s_ji is the score awarded to student i by peer j, S is the set of peers who actually
submitted reviews, and P_i = |S \ {i}| is the number of submitting peers (excluding self).

Self-scores are excluded from the numerator. The denominator adapts to the number of
submitting peers rather than being fixed at N-1. This ensures that a student's IWF is not
penalised by a teammate's non-submission — a missing review is simply ignored rather than
treated as a zero score.

An IWF of 10 indicates exactly equal contribution. Values above 10 receive a grade uplift;
values below 10 attract a penalty. The individual grade is computed as:

```
g_i = G_team × (IWF_i / 10)
```

where G_team is the shared team grade.

### Known limitations

**Collusion through uniform inflation.** If all team members award each other maximum
scores, every IWF equals 10.0 and the mechanism produces no differentiation.

**Equal rater weight.** A student who submits thoughtless or strategic scores is counted
with identical weight to the most engaged contributor. There is no mechanism to discount
unreliable raters.

**Zero-self exploit.** Because self-scores are silently discarded but the denominator stays
fixed at N-1, a student who awards themselves 0 effectively injects surplus points into the
pool available to teammates — inflating all IWFs without any corresponding increase in
contribution.

These limitations motivate the advanced models (PeerRank, WebPA, PeerHITS).

---

## Algorithm Walkthrough

1. For each student i, collect all scores they received from peers j ≠ i who submitted.
2. Sum those scores and divide by the number of submitting peers.
3. The result is IWF_i directly — no iteration, no normalisation.

That's it. The baseline is a plain mean of received scores, computed independently per
student.

---

## Implementation Notes

**File:** `src/models/baseline.py`

The implementation uses `np.nanmean` over each row of the score matrix after setting the
diagonal (self-scores) to NaN. This is deliberate:

- Setting the diagonal to NaN excludes self-scores from the average.
- `nanmean` automatically skips NaN values, which also represent non-submitters (students
  whose entire column is NaN). A non-submitter's missing scores are excluded from any
  student's average without special-casing, and the denominator adapts to the number of
  peers who actually submitted.

```python
np.fill_diagonal(matrix, np.nan)
iwf_vector = np.nanmean(matrix, axis=1)
```

`axis=1` computes the mean across columns (givers) for each row (recipient).

**NaN handling:** Non-submitters have an entire NaN column. `nanmean` skips them, so
the denominator for other students' averages adjusts automatically to the number of
valid scores received.

**Returns:** A `ModelResult` with:
- `model_name`: `"Simple Average (Baseline)"`
- `iwf_vector`: numpy array of length N
- `students`: list of `StudentInfo` objects
- `converged`, `iterations`, `final_l1_norm`: all `None` (not applicable to a non-iterative model)

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

Self-scores (diagonal) are excluded:

```
IWF_A = (6 + 8) / 2   = 14 / 2  =  7.000
IWF_B = (12 + 14) / 2 = 26 / 2  = 13.000
IWF_C = (8 + 14) / 2  = 22 / 2  = 11.000
```

### Expected output

```
iwf_vector = [7.000, 13.000, 11.000]
```

---

## References

- Kaufman, D. B., Felder, R. M., and Fuller, H. Accounting for individual effort in
  cooperative learning teams. *Journal of Engineering Education*, 89(2):133–140, 2000.
