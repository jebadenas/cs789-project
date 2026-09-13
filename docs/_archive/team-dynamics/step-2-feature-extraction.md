# Step 2 — Feature Extraction

**Source:** `src/dynamics/features.py`, `src/dynamics/triad.py`

## The problem we're solving

Imagine you have 50 teams. Some have 4 students, some have 6. You want to compare them — but you can't directly compare a 4×4 grid of numbers to a 6×6 grid. They're different shapes.

So instead, we summarise each team into **25 numbers that mean the same thing regardless of team size.** That summary is the feature vector.

Think of it like a doctor's checkup. Instead of handing the doctor your entire medical history, they measure your blood pressure, heart rate, temperature — a fixed set of readings that summarise your health. Same idea here.

```
9 numbers  →  behavioural metrics  (how people scored each other)
16 numbers →  triad proportions    (patterns in who-rates-who-highly)
─────────────────────────────────────────────────────────────────
25 total
```

---

## Part A — Behavioural Metrics (features 1–9)

### 1. `reciprocity`

**Question it answers:** When Alice gives Bob a high score, does Bob tend to give Alice a high score back?

Imagine listing every pair of students:

```
Alice → Bob:   Alice gave Bob 18,  Bob gave Alice 17   ← similar  ✓
Alice → Carol: Alice gave Carol 8, Carol gave Alice 15  ← very different ✗
Bob → Carol:   Bob gave Carol 12,  Carol gave Bob 11   ← similar  ✓
```

Reciprocity is a single number between -1 and 1:
- **Close to 1** → scoring is mutual (if I rate you high, you rate me high)
- **Close to 0** → no relationship
- **Negative** → opposite (if I rate you high, you rate me *low*)

```
collect all pairs (i, j) with i < j:
  fwd = A[i, j]  (what i gave j)
  rev = A[j, i]  (what j gave i)
reciprocity = Pearson correlation(fwd, rev)
```

| Label | Expected value |
|---|---|
| Cohesive | High (~1) |
| Conflict | Low or negative |

---

### 2. `gini_in_degree`

**Question it answers:** Is attention spread evenly, or does one person receive most of it?

This uses the same Gini coefficient from economics — it measures inequality. Here "income" is the average peer score each student receives.

```
Equal team:    Alice 12,  Bob 12,  Carol 12,  Dave 12   →  Gini ≈ 0
Free-rider:    Alice 15,  Bob 15,  Carol 15,  Dave  2   →  Gini ≈ 0.5
```

| Label | Expected value |
|---|---|
| Cohesive | Low (~0) |
| Free-rider | High (free-rider pulls inequality up) |
| Dominant | Moderate–high |

---

### 3. `mean_rater_std` and 4. `std_rater_std`

Think of each student as a judge on a talent show.

Some judges give scores like: `10, 11, 10, 10, 9` — very consistent, not much spread.
Other judges give scores like: `18, 5, 20, 3, 14` — very spread out.

**Feature 3** (`mean_rater_std`) = on average, how spread out are people's scores?
**Feature 4** (`std_rater_std`) = how much do people *differ from each other* in their spreading style?

A **Collusive** team has high spread — students give a huge score to their buddy and low scores to everyone else.

---

### 5. `asymmetry`

**Question it answers:** Is scoring one-sided?

If Alice gives Bob 18 and Bob gives Alice 18 — that's symmetric.
If Alice gives Bob 18 and Bob gives Alice 4 — that's asymmetric.

```
asymmetry = ‖A − Aᵀ‖_F / (‖A + Aᵀ‖_F + ε)
```

A score of 0 means everything is perfectly mirrored. A high score means lots of one-sided relationships.

| Label | Expected value |
|---|---|
| Cohesive | Near 0 |
| Conflict | High — one faction rates the other low, but not vice versa |

---

### 6. `clustering`

**Question it answers:** Do tight sub-groups form?

Think of high school cliques — some students only rate their close circle highly. High clustering means those tight bubbles exist. Low clustering means the team is more open and spread.

A **Collusive** team has high clustering — buddy pairs form tight sub-cliques.

---

### 7. `assortativity`

**Question it answers:** Do popular people tend to connect to other popular people?

In a **Dominant** team, one person gets all the attention — like a wheel with spokes. The hub connects to everyone, but the spokes only connect to the hub, not to each other. That produces low (or negative) assortativity.

---

### 8. `non_submitter_frac`

What fraction of students didn't hand in their assessment at all? (Their entire column is missing.)

---

### 9. `mean_self_share`

On average, what fraction of the 60 points did students keep for themselves?

A **Free-rider** typically gives themselves 52 out of 60 — keeping most of the budget. That makes this feature spike sharply.

---

## Part B — Triad Census Proportions (features 10–25)

### Step 1: build a directed graph

Before counting triads, we convert the score matrix into a **directed graph** — dots (students) connected by arrows (scores). But we don't draw an arrow for every score. We only draw one when the score is **above that person's own average.**

For example, if Alice's average score to others is 12:
- She gave Bob 18 → draw Alice → Bob ✓
- She gave Carol 8 → no arrow ✗

**Why use each person's own average, not a fixed number?** Because different students use different scales. One student's "15" might be another's "12." Using each person's own average makes it a fair, relative question: *"did this person give above-average attention to that person?"*

```python
# src/dynamics/triad.py → binarize_rater_mean()
for each giver i:
    rater_mean = mean of giver i's scores to others
    edge i → j  exists  iff  A[i, j] > rater_mean
```

---

### Step 2: what is a triad?

A triad is what you get when you **zoom in on any 3 students** from that graph and look at only the arrows between those 3.

With 3 people — A, B, C — there are 6 possible arrows:

```
A→B,  B→A,  A→C,  C→A,  B→C,  C→B
```

Each can be present or absent. All the possible combinations collapse down to **16 distinct patterns**, called triad types. Each has a short code.

---

### The naming convention

The code has 3 characters, like `003`, `012`, `111D`. The numbers count three kinds of relationships between pairs:

```
first digit  = number of MUTUAL pairs   (A→B and B→A both present)
second digit = number of ASYMMETRIC pairs  (only one direction)
third digit  = number of NULL pairs     (no arrow either way)
```

Letters like `D`, `U`, `C`, `T` distinguish sub-types when the counts are identical but the shape is different.

---

### Key triad types explained

#### `003` — Complete silence
```
A    B    C      (no arrows at all)
```
Nobody rated anybody above average among these 3. Happens when a rater gives everyone near-equal scores — they produce no edges and appear isolated.

A **Cohesive** team can have many `003` triads for this reason — everyone scores fairly equally, so nobody stands out as "above average."

---

#### `012` — One single arrow
```
A ──→ B    C
```
One person gave one other person above-average scores. Nothing else connects these three.

---

#### `102` — One mutual pair, one outsider
```
A ←→ B    C
```
A and B rate each other highly. C is not involved.

A **Collusive** team has many `102` triads — buddy pairs form mutual relationships while the third person is excluded.

---

#### `030C` — A cycle
```
A ──→ B
↑         │
│         ↓
└──── C ──┘
```
A rates B highly, B rates C highly, C rates A highly — a chain that loops back. Nobody rates back the way they received.

---

#### `300` — Complete mutual admiration
```
All 6 arrows present — every pair rates each other above average.
```
A **Cohesive** team has many `300` triads — everyone appreciates everyone.

---

### Why triads add information the other 9 features miss

The first 9 features look at the whole matrix at once — totals, averages, correlations. Triads zoom in on **local pockets of 3 people.**

Two teams could have identical reciprocity and Gini scores, but:
```
Team X:  lots of 300 triads → mutual appreciation is universal
Team Y:  lots of 102 triads → mutual appreciation exists but only in isolated pairs
```
Team X is Cohesive. Team Y is Collusive. The top-level stats alone can't tell them apart.

---

### How each dynamic shows up in the triad census

| Label | Expected triad signature |
|---|---|
| **Cohesive** | High `300` (universal mutual appreciation) |
| **Collusive** | High `102` (mutual pairs), low `300` (pairs don't extend to the whole group) |
| **Free-rider** | High `003` and `012` (free-rider produces few edges; others rate them below average) |
| **Dominant** | High `012` and `021D` (arrows flow toward the dominant person; few mutual triads) |
| **Conflict** | High asymmetric types like `021C`, `030C` (directional chains, not mutual) |

---

### Step 3: count and normalise

```python
census = nx.triadic_census(G)          # count all 16 types across every group of 3
total  = sum(census.values())
proportions = {cls: count / total      # convert to fractions summing to 1
               for cls in TRIAD_CLASSES}
```

For a team of 5 students: `C(5,3) = 10` triples get classified.
For a team of 6 students: `C(6,3) = 20` triples get classified.

Normalising to proportions makes the 16 numbers comparable across team sizes.

**Source:** `src/dynamics/triad.py` → `triad_census_proportions()`

---

## The Full 25-dim Vector

```
Index  Feature
 0     reciprocity
 1     gini_in_degree
 2     mean_rater_std
 3     std_rater_std
 4     asymmetry
 5     clustering
 6     assortativity
 7     non_submitter_frac
 8     mean_self_share
 9     triad_003
10     triad_012
11     triad_102
12     triad_021D
13     triad_021U
14     triad_021C
15     triad_111D
16     triad_111U
17     triad_030T
18     triad_030C
19     triad_201
20     triad_120D
21     triad_120U
22     triad_120C
23     triad_210
24     triad_300
```

## Key concept to remember

The 25-dim vector is a fixed-size fingerprint of a team's scoring behaviour, regardless of team size. Every downstream step — standardisation, archetype comparison, classification — operates on this vector.
