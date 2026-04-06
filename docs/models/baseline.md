# Simple Average (Baseline) Model

## Theoretical Background

The Simple Average model is the IWF (Individual Weighting Factor) formulation introduced by
Kaufman, Felder and Fuller (2000) and used directly by COMPSCI 399 at the University of
Auckland.

Each student in a team of N distributes a fixed pool of 10×N points among all teammates
(including themselves). The IWF for student i is the mean of all peer scores they received:

```
IWF_i = (1 / (N-1)) × Σ(j≠i) s_ji
```

where s_ji is the score awarded to student i by peer j. Self-scores are excluded from the
numerator but the denominator is fixed at N-1 regardless of how many peers actually submitted.

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

1. For each student i, collect all scores they received from peers j ≠ i.
2. Sum those scores and divide by N-1.
3. The result is IWF_i directly — no iteration, no normalisation.

That's it. The baseline is a plain mean of received scores, computed independently per
student.

---

## Implementation Notes

**File:** `src/models/baseline.py`

The implementation uses `np.nanmean` over each row of the score matrix rather than
implementing the mean manually. This is deliberate: `nanmean` automatically skips NaN
values, which represent non-submitters (students whose entire column is NaN). A
non-submitter's column is excluded from any student's average without special-casing.

```python
iwf_vector = np.nanmean(score_matrix.matrix, axis=1)
```

`axis=1` computes the mean across columns (givers) for each row (recipient). The diagonal
(self-scores) is included in the mean — this matches the COMPSCI 399 convention confirmed
by the dataset's own "Average Points" column.

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

```
IWF_A = (10 + 6 + 8) / 3  =  24 / 3  =  8.000
IWF_B = (12 + 10 + 14) / 3 = 36 / 3  = 12.000
IWF_C = (8 + 14 + 12) / 3  = 34 / 3  ≈ 11.333
```

Note: self-scores (diagonal) are included, matching COMPSCI 399 behaviour.

### Expected output

```
iwf_vector = [8.000, 12.000, 11.333]
```

---

## References

- Kaufman, D. B., Felder, R. M., and Fuller, H. Accounting for individual effort in
  cooperative learning teams. *Journal of Engineering Education*, 89(2):133–140, 2000.
