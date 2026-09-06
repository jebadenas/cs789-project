# Step 4 — Archetypes

**Source:** `src/dynamics/classifier.py` → `build_synthesised_archetypes()`

## The big idea

Before classifying a real team, we need something to compare it *against*. We need to know: what does a Cohesive team look like? What does a Free-rider team look like?

The answer: we **hand-craft one fake team for each label** — a perfect, textbook example of that dynamic. We call these **archetypes** (or prototypes).

There are 5, one per label:

```
Cohesive    →  archetype matrix
Collusive   →  archetype matrix
Free-rider  →  archetype matrix
Dominant    →  archetype matrix
Conflict    →  archetype matrix
```

Each archetype is a standard 5×5 score matrix — the same format as a real peer assessment from Step 1. The numbers are designed by hand so they perfectly represent that dynamic.

---

## Rules for each matrix

The same constraints as real peer assessments apply:
- 5 students (columns and rows)
- Every **column must sum to 60** — each student distributes exactly 60 points
- The **diagonal** is the self-score

---

## The five archetypes

### Cohesive

Everyone rates everyone fairly. No favourites. Scores hover around 12 (= 60 ÷ 5, a perfectly equal split).

```
[[12, 11, 13, 12, 12],
 [11, 12, 11, 13, 12],
 [13, 11, 12, 11, 13],
 [12, 13, 11, 12, 12],
 [12, 13, 13, 12, 11]]
```

---

### Collusive

Students form **buddy pairs** — Alice inflates Bob's score, Bob inflates Alice's. Students 0 and 1 are buddies (they give each other 18). Students 2 and 3 are buddies. Self-scores are low (6) because budget is dumped onto the buddy.

```
[[ 6, 18, 14, 12, 10],
 [18,  6, 10, 14, 12],
 [14, 10,  6, 18, 12],
 [12, 14, 18,  6, 10],
 [10, 12, 12, 10, 16]]
```

---

### Free-rider

Student 4 is the free-rider. Active students (0–3) give them only 2 points. The free-rider gives 2 to everyone and keeps 52 for themselves.

```
[[13, 15, 15, 15,  2],
 [15, 13, 15, 15,  2],
 [15, 15, 13, 15,  2],
 [15, 15, 15, 13,  2],
 [ 2,  2,  2,  2, 52]]
```

---

### Dominant

Student 0 is the star. Students 1–4 each give ~27 of their 60 points to student 0, leaving only ~8 for each other. Student 0 themselves distributes evenly.

```
[[12, 28, 27, 26, 27],
 [12,  8,  8,  9,  8],
 [12,  8,  8,  9,  8],
 [12,  8,  9,  8,  9],
 [12,  8,  8,  8,  8]]
```

---

### Conflict

Two factions: {0, 2} and {1, 3}. Each faction inflates its own members and penalises the other. Arrows between factions point in opposite directions.

```
[[12, 20,  5, 20,  5],
 [ 5, 12, 20,  5, 20],
 [20,  5, 12, 20,  5],
 [ 5, 20,  5, 12, 20],
 [18,  3, 18,  3, 10]]
```

---

## From matrix to feature vector

Once each archetype matrix is built, it passes through the same pipeline as any real team:

```python
# classifier.py → build_synthesised_archetypes()
for mat in prototypes:
    sm = _make_sm(mat, n=5)          # wrap in a ScoreMatrix object
    tf = extract_features(sm)         # Step 2: produce the 25-dim vector
    vectors.append(tf.values)

arch_raw = np.array(vectors)          # shape: (5, 25)
arch_scaled = scaler.transform(arch_raw)  # Step 3: standardise using real data's scaler
```

Each hand-crafted matrix becomes a 25-number fingerprint. After standardisation, the 5 archetypes are 5 fixed points in the same 25-dimensional space as all the real teams.

---

## Key concept to remember

Archetypes are hand-designed score matrices — idealized examples of each dynamic. Once run through feature extraction and standardisation, they become **reference points in feature space**. Classification is simply asking: which reference point is this real team closest to?
