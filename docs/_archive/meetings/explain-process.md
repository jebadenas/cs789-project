### Step 1 — Input: the score matrix

Each team produces a matrix where every student distributes 60 points across their teammates. Rows = recipients, columns = givers. That's the raw input.

### Step 2 — Feature extraction (25 numbers)

- **9 behavioural metrics** — reciprocity (do people rate each other similarly?), Gini inequality (is one person getting much less?), asymmetry (are ratings one-sided?), clustering, rater variance, etc.
- **16 triad census proportions** — binarize the matrix into a directed graph (arrow exists if score is above that person's own average), then count every 3-person subgraph pattern across all possible groups of 3 students. This captures local structure that global metrics miss — two teams can have identical reciprocity but one has mutual buddy pairs (Collusive) while the other has universal mutual appreciation (Cohesive).

### The 16 triad types visualised

Nodes = students (A, B, C). Arrows = above-average score.
Layout is always: A top-left, B top-right, C bottom.
The code counts **M**utual / **A**symmetric / **N**ull pairs (e.g. `102` = 1 mutual, 0 asymmetric, 2 null).

Between 3 people there are 3 pairs. Each pair can be mutual (↔), asymmetric (→ one way), or null (no arrow). The digit combination tells you how many of each:

| Code  | Mutual | Asymmetric | Null | Possible shapes | Letter used |
| ----- | ------ | ---------- | ---- | --------------- | ----------- |
| `003` | 0      | 0          | 3    | 1               | —           |
| `012` | 0      | 1          | 2    | 1               | —           |
| `102` | 1      | 0          | 2    | 1               | —           |
| `021` | 0      | 2          | 1    | 3               | D, U, C     |
| `111` | 1      | 1          | 1    | 2               | D, U        |
| `030` | 0      | 3          | 0    | 2               | T, C        |
| `201` | 2      | 0          | 1    | 1               | —           |
| `120` | 1      | 2          | 0    | 3               | D, U, C     |
| `210` | 2      | 1          | 0    | 1               | —           |
| `300` | 3      | 0          | 0    | 1               | —           |

**What the letters mean:**

| Letter | Meaning                                                | Which types            |
| ------ | ------------------------------------------------------ | ---------------------- |
| **D**  | Diverge — arrows fan _out_ from a node or mutual pair  | `021D`, `111D`, `120D` |
| **U**  | Up/Converge — arrows fan _in_ to a node or mutual pair | `021U`, `111U`, `120U` |
| **C**  | Cycle/Chain — arrows form a loop or directed path      | `021C`, `030C`, `120C` |
| **T**  | Transitive — strict hierarchy (A→B, A→C, B→C)          | `030T`                 |

Types with no letter have only one possible shape for their digit combination.

```
003                   012                   102
A      B              A──→B                 A←→B

    C                     C                     C

no arrows             one arrow, C silent   A & B rate each other,
                                            C is outsider


021D                  021U                  021C
    A                 B      C              A──→B
   / \                 \    /
  ↓   ↓                ↓  ↓                         ↓
  B    C                  A               C (A→B→C, a chain)

A→B and A→C           B→A and C→A
(fan out from A)      (fan in to A)


111D                  111U                  030T
A←→B                  A←→B                 A──→B
↓                          ↑               ↓    ↓
C                     C                    C
                                           (A→B, A→C, B→C —
A↔B mutual,           A↔B mutual,           a strict hierarchy)
A→C outward           C→A inward


030C                  201                   120D
A──→B                 A←→B                 A←→B
↑       ↓             ↕                     ↓    ↓
└───C───┘             C    (B–C no arrow)   C

A→B→C→A               A↔B and A↔C,         A↔B mutual,
(a cycle)              B–C null              A→C and B→C


120U                  120C                  210
A←→B                  A←→B                 A←→B
↑    ↑                ↓    ↑               ↕    ↓
C                     C                    C

A↔B mutual,           A↔B mutual,          A↔B and A↔C mutual,
C→A and C→B           A→C→B (cycle)        B→C (5 of 6 arrows)


300
A←→B
↕    ↕
C

all 6 arrows present — every pair rates each other above average
```

**Which triads signal which dynamic:**

All 16 are counted and used as features. The ones with a clear interpretation are marked — the rest contribute signal but are harder to tie to a single dynamic.

| Triad  | Arrows             | Clearest signal                                              |
| ------ | ------------------ | ------------------------------------------------------------ |
| `003`  | None               | Equal scoring — nobody stands out (Cohesive or Free-rider)   |
| `012`  | A→B only           | Weak one-sided preference, C uninvolved                      |
| `102`  | A↔B, C isolated    | Mutual buddy pair — outsider excluded (Collusive)            |
| `021D` | A→B, A→C           | One person gives above-average to two others                 |
| `021U` | B→A, C→A           | Two people rate one person above average (Dominant receiver) |
| `021C` | A→B→C              | Directed chain, no reciprocation                             |
| `111D` | A↔B, A→C           | Mutual pair with one outward arrow                           |
| `111U` | A↔B, C→A           | Mutual pair with one inward arrow                            |
| `030T` | A→B, A→C, B→C      | Strict hierarchy — one person clearly on top                 |
| `030C` | A→B→C→A            | Directional cycle — no one reciprocates (Conflict)           |
| `201`  | A↔B, A↔C, B–C null | Two mutual pairs but those two ignore each other             |
| `120D` | A↔B, A→C, B→C      | Mutual pair both pointing outward to C                       |
| `120U` | A↔B, C→A, C→B      | C feeds into a mutual pair — C may be the dominant giver     |
| `120C` | A↔B, A→C→B         | Mutual pair with a cycle running through C                   |
| `210`  | A↔B, A↔C, B→C      | Near-complete — one asymmetric edge only                     |
| `300`  | All ↔              | Universal mutual appreciation (Cohesive)                     |

---

### Step 3 — Standardisation

The 25 features are on different scales. We standardise each to a z-score ("how many standard deviations from average across all teams") so no feature dominates just because of its units. The same scaler is applied to both real teams and archetypes so they live in the same space.

### Step 4 — Classification by Mahalanobis distance

We hand-craft 5 prototype matrices — one per label — designed to be textbook examples of each dynamic. These go through the same pipeline to become 5 reference points in the same 25-dimensional space.

Each real team is assigned the label of whichever prototype it's **closest to**, using **Mahalanobis distance** rather than plain Euclidean distance. Mahalanobis accounts for correlations between features so correlated features aren't double-counted.

Output: a hard label + a confidence score (softmax over the 5 distances).

### The 5 hand-crafted prototype matrices

Each column is one student's allocation (sums to 60). Diagonal = self-score.

**Cohesive** — near-uniform scoring, everyone rates fairly (~12 per peer):

```
[[12, 11, 13, 12, 12],
 [11, 12, 11, 13, 12],
 [13, 11, 12, 11, 13],
 [12, 13, 11, 12, 12],
 [12, 13, 13, 12, 11]]
```

**Collusive** — buddy pairs (0↔1 and 2↔3) inflate each other with 18 points:

```
[[ 6, 18, 14, 12, 10],
 [18,  6, 10, 14, 12],
 [14, 10,  6, 18, 12],
 [12, 14, 18,  6, 10],
 [10, 12, 12, 10, 16]]
```

**Free-rider** — student 4 receives only 2 from all peers and hoards 52 for themselves:

```
[[13, 15, 15, 15,  2],
 [15, 13, 15, 15,  2],
 [15, 15, 13, 15,  2],
 [15, 15, 15, 13,  2],
 [ 2,  2,  2,  2, 52]]
```

**Dominant** — student 0 receives ~27 from every other student:

```
[[12, 28, 27, 26, 27],
 [12,  8,  8,  9,  8],
 [12,  8,  8,  9,  8],
 [12,  8,  9,  8,  9],
 [12,  8,  8,  8,  8]]
```

**Conflict** — two factions ({0,2} vs {1,3}) inflate their own and penalise the other:

```
[[12, 20,  5, 20,  5],
 [ 5, 12, 20,  5, 20],
 [20,  5, 12, 20,  5],
 [ 5, 20,  5, 12, 20],
 [18,  3, 18,  3, 10]]
```

---

## Key Results

| Label      | Count | Mean Δ |
| ---------- | ----- | ------ |
| Cohesive   | 102   | 0.55   |
| Dominant   | 2     | 1.73   |
| Free-rider | 1     | —      |
| Collusive  | 0     | —      |
| Conflict   | 0     | —      |
