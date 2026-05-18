# Step 1 — The Score Matrix

**Source:** `src/parsing/schemas.py` → `ScoreMatrix`

## What it is

A `ScoreMatrix` is the structured representation of one team's peer-assessment responses for one question. Each student distributes **60 points** across all team members (including themselves).

## Matrix convention

```
matrix[i][j] = score that student j gave to student i
```

- **Rows** = recipients (who received the score)
- **Columns** = givers (who assigned the score)
- Each **column** sums to 60
- The **diagonal** `matrix[i][i]` is student i's self-score
- A column of all `NaN` means that student did not submit

### Example (3 students)

```
             Alice gives   Bob gives   Carol gives
Alice            20           15           10
Bob              15           20           25
Carol            25           25           25
```

Alice's column: 20 + 15 + 25 = 60 ✓

## Internal transposition

Feature extraction immediately transposes the matrix:

```python
A = matrix.T   # A[giver][recipient]
```

This makes row-iteration natural: each row of `A` is one student's full allocation.

## Key fields

| Field | Description |
|---|---|
| `matrix` | `(n, n)` numpy array, `float`, `NaN` for missing |
| `team_name` | String identifier for the team |
| `students` | List of `StudentInfo` (name, email, index) |
| `excluded_students` | Students removed before analysis |

## Key concept to remember

`matrix[i][j]` means *j gave to i* — recipient on the row, giver on the column. The code transposes to `A[giver][recipient]` immediately, so all downstream computation uses the transposed form.
