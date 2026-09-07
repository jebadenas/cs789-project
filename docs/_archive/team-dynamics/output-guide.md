# Output Files Guide — Team Dynamics Pipeline

All files are written to `output/dynamics/` when you run:

```bash
python3 -m src.dynamics
```

There are 8 output files. The first two are the primary results you care about.
The rest are supporting evidence, diagnostic tools, or visual aids.

---

## Reading order

| Priority | File | What it answers |
|---|---|---|
| 1 | `atypicality_summary.csv` | Does unusual team behaviour cause model disagreement? (the RQ3 answer) |
| 2 | `classifications.csv` | Which teams are unusual, and by how much? |
| 3 | `archetype_stability.csv` | Is a 5-type taxonomy justified? (spoiler: no) |
| 4 | `delta_by_label.csv` | Old 5-bucket results (kept for comparison) |
| 5 | `feature_matrix.csv` | The raw 25 numbers behind every team |
| 6 | `archetypes.json` | Raw AA archetype vectors (rarely needed directly) |
| 7 | `pca_plot.html` | Visual: does the data look like one blob or five clusters? |
| 8 | `rss_plot.html` | Visual: which k (number of archetypes) is honest? |

---

## File 1 — `atypicality_summary.csv`

**The RQ3 answer. Read this first.**

### What it answers

> "Among teams with usable peer-assessment data, do teams with unusual rating
> behaviour cause the 6 scoring models to disagree more?"

### Columns

| Column | Meaning |
|---|---|
| `subset` | Which teams were included: `full` = all 105, `clean` = the 39 with real signal only |
| `n` | Number of team-matrices in the calculation |
| `pearson_r` | Correlation between atypicality and Δ. Range: -1 to +1. Positive = unusual teams cause more disagreement |
| `p_value` | Probability the result happened by chance. Below 0.05 = statistically significant |
| `degenerate_excluded` | Whether the 66 no-signal teams were removed before calculating |

### Current values

```
subset   n    pearson_r   p_value
full     105  +0.515      0.000
clean    39   +0.366      0.022
```

### How to read it

The clean row is the one to cite. In plain English:

> "Among teams with usable data (n=39), more unusual peer-rating behaviour
> is associated with more cross-model disagreement — r=0.366, p=0.022."

r=0.366 is a moderate positive correlation. Not a perfect relationship, but
a real, statistically significant trend. p=0.022 means there is only a 2.2%
chance this pattern is random noise (threshold is 5%).

The full-set r=0.515 looks stronger but is untrustworthy — non-submitters
inflate both atypicality and Δ simultaneously, creating a false signal. Both
rows are shown so a reader can see the confound rather than it being hidden.

### Key takeaway

Unusual teams → more model disagreement. The signal is real but moderate.
The honest n is 39, not 105 — because 66 team-matrices had no usable signal.

---

## File 2 — `classifications.csv`

**Per-team detail. The full picture behind the summary.**

One row per (team × question). 105 rows total.

### Column groups

**Identity — who is this row?**

| Column | Meaning |
|---|---|
| `csv_path` | Which source CSV this came from (2023 or 2024 session) |
| `team_name` | The team's name |
| `question_label` | Which peer-rating question (e.g. "source code", "group report") |

**Primary results — the new method**

| Column | Meaning |
|---|---|
| `delta` | Cross-model disagreement score for this team-question. Higher = models argued more |
| `atypicality` | How unusual this team's peer-rating pattern is. Higher = further from the average team |
| `atypicality_flag` | `Typical` or `Anomalous` — based on a statistically principled cutoff (chi-square at 95%) |
| `degenerate` | `True` if this matrix had no usable signal (excluded from the clean analysis) |
| `degenerate_cause` | *Why* it had no signal: `non_submitter`, `flat`, `both`, or `none` |

**Secondary results — the old 5-prototype method (kept for comparison)**

| Column | Meaning |
|---|---|
| `dynamic_label` | Nearest of the 5 hand-crafted labels: Cohesive / Collusive / Free-rider / Dominant / Conflict |
| `dist_cohesive` … `dist_conflict` | Mahalanobis distance to each of the 5 prototype matrices |
| `weight_cohesive` … `weight_conflict` | How much this team "looks like" each prototype (0–1, sums to 1) |

> **Note:** The `dynamic_label` column is not the primary result. 102 of 105
> teams end up labelled Cohesive because the hand-crafted prototypes are
> too extreme — every real team lands nearest the least-extreme one. Use
> `atypicality` and `atypicality_flag` for the actual analysis.

### How to read it

To find the most unusual clean teams:
1. Filter `degenerate == False`
2. Filter `atypicality_flag == Anomalous`
3. Sort by `atypicality` descending

To understand a specific team, look at both `atypicality` (continuous score)
and `delta` (model disagreement). High atypicality + high delta = the team's
unusual dynamics translated into measurable model confusion.

### Key takeaway

This is the per-team lookup table. `atypicality` and `degenerate_cause` are
the new primary columns. `dynamic_label` is secondary/illustrative only.

---

## File 3 — `archetype_stability.csv`

**Statistical evidence that a 5-type taxonomy is not supported by this data.**

### What it answers

> "If we try to split teams into k groups, how stable is that split? Would we
> get the same groups if we re-ran on a slightly different sample?"

### Columns

| Column | Meaning |
|---|---|
| `k` | Number of archetypes (groups) tested |
| `rss` | Residual Sum of Squares — how well k archetypes fit the data. Lower = better fit |
| `bootstrap_stability` | How reproducible the split is (0 = random, 1 = identical every time) |

### Current values

```
k   rss      bootstrap_stability
2   1788.7   0.917   ← very stable
3   1564.8   0.682
4   1375.4   0.591
5   1202.8   0.500   ← coin flip
6   1048.3   0.478
7    926.3   0.538
8    814.9   0.602
```

### How to read it

RSS always falls as k increases — more groups always fit the data better,
just like drawing more lines through a scatter plot. RSS alone cannot tell
you the right k.

Bootstrap stability is the honest test. It asks: "if I re-ran the split on
80% of the data, would I get the same groups?" 

- k=2: stability 0.917 → the two groups are the same every time → **real structure**
- k=5: stability 0.500 → a coin flip → **no real structure at 5 groups**

This is why the 5-label taxonomy (Cohesive/Collusive/Free-rider/Dominant/
Conflict) was abandoned as the primary result. The data robustly supports
only a binary split: Typical vs Anomalous.

### Key takeaway

0.917 at k=2 = real. 0.500 at k=5 = fiction. Only a binary split is
statistically honest for this dataset.

---

## File 4 — `delta_by_label.csv`

**The old 5-prototype result. Kept for comparison, not the primary finding.**

### What it answers

> "For the (now-demoted) 5-label classification, what is the average model
> disagreement per label?"

### Columns

| Column | Meaning |
|---|---|
| `label` | One of the 5 prototype labels |
| `count` | How many teams were assigned this label |
| `mean` | Average Δ for teams with this label |
| `std` | Standard deviation of Δ |
| `median` | Median Δ |
| `max` | Highest individual Δ in this label |

### Current values

```
label       count  mean   std    median  max
Cohesive    102    0.551  1.194  0.062   7.063
Collusive   0      —
Free-rider  1      0.525  —
Dominant    2      1.732  1.027
Conflict    0      —
```

### Why this is not the primary result

102 of 105 teams are labelled Cohesive regardless of their actual dynamics.
A team with Δ=7.06 (the most disagreement in the dataset) is labelled
Cohesive with 98% confidence by the old method. The new atypicality approach
correctly flags that same team as Anomalous.

The Dominant mean Δ (1.732) vs Cohesive (0.551) does suggest the pattern is
real — but with only 2 Dominant teams, no statistical claims can be made.
Use this file as illustrative context only.

### Key takeaway

102/105 Cohesive = classifier collapse, not a finding. This file is kept so
the failure of the old method is visible and documentable.

---

## File 5 — `feature_matrix.csv`

**The 25 fingerprint numbers for every team. The foundation everything else builds on.**

### What it answers

> "What does each team's peer-rating pattern actually look like, numerically?"

### Columns

**Identity**

| Column | Meaning |
|---|---|
| `csv_path` | Source CSV |
| `team_name` | Team name |
| `question_label` | Which question |

**Behavioural metrics (9 features)**

| Column | Meaning | High value means… |
|---|---|---|
| `reciprocity` | Do people tend to rate each other similarly? (-1 to 1) | Mutual — if A rates B high, B rates A high |
| `gini_in_degree` | How unequal are the received scores? (0 to 1) | One person is getting much more or less than others |
| `mean_rater_std` | On average, how much does each rater vary their scores? | Raters are differentiating — not giving everyone the same |
| `std_rater_std` | How different are raters from each other in variation? | Some raters spread scores widely, others give flat scores |
| `asymmetry` | How one-sided are ratings? | A rates B high but B rates A low |
| `clustering` | Are there tight sub-groups within the team? (0 to 1) | Cliques — everyone within a sub-group rates each other high |
| `assortativity` | Do high-raters tend to rate other high-raters? | Always 0 in this dataset — this feature was confirmed noise and is dropped before analysis |
| `non_submitter_frac` | Fraction of team members who didn't submit | Higher = more missing data |
| `mean_self_share` | Average fraction of points each student kept for themselves | Higher = more self-serving |

**Triad census (16 features — `triad_003` through `triad_300`)**

Each `triad_*` value is the proportion of 3-person subgroups that match a
specific arrow pattern in the binarised graph. Together these 16 numbers
capture local structure that the 9 behavioural metrics miss.

The most interpretable:
- `triad_003` — proportion of triads with NO above-average connections. High = sparse, flat-scoring team
- `triad_300` — proportion of triads with FULL mutual connections. High = everyone rates everyone highly

**Outcome columns**

| Column | Meaning |
|---|---|
| `delta` | Cross-model disagreement for this team-question |
| `dynamic_label` | Old 5-prototype label (secondary, from `classifications.csv`) |

### Key takeaway

This is the raw evidence table. You rarely need to read it directly — the
pipeline builds on it automatically. Useful when you want to understand *why*
a specific team got a high atypicality score (look at their feature values vs
the column averages).

---

## File 6 — `archetypes.json`

**The raw output of Archetypal Analysis. Rarely needed directly.**

Contains the k extreme feature-space points found by AA for each k=2..8,
along with how much each real team is "made of" each archetype (weights).

You would open this file if you wanted to inspect what the data-driven
extremes look like in feature space — for example, to understand what
"Archetype 1 at k=2" represents behaviourally. For day-to-day analysis,
`archetype_stability.csv` has the numbers you need.

---

## File 7 — `pca_plot.html`

**Open in a browser. Visual proof of the blob + tail structure.**

PCA compresses the 25 features down to 2 dimensions so you can see the data.
Each dot = one team-matrix. Colour = Δ (darker/warmer = higher disagreement).

**What to look for:**
- One main cluster of dots close together (the "ordinary" teams)
- A few dots far from the cluster (the anomalous teams — typically the warm/dark ones)
- No five separate clusters — that's the point. The data is one blob with outliers, not five labelled groups.

The AA archetypes are overlaid. Note how far the k=5 archetypes are from where most teams sit — visual confirmation of why the 5-prototype classifier collapsed to Cohesive.

---

## File 8 — `rss_plot.html`

**Open in a browser. Visual explanation of why k=2 is the honest split.**

Two lines on the same chart:
- **RSS** (blue) — drops as k increases. This alone would suggest "more groups is always better." It isn't.
- **Bootstrap stability** (orange) — the honest line. Shows that only k=2 is reproducible (high stability). Everything beyond k=2 drops toward 0.5 (chance).

**What to look for:**
- RSS elbow around k=5 (where the drop slows down) — this is what the old method used to pick k=5
- Stability cliff after k=2 — this is why k=5 is wrong

The gap between "elbow says k=5" and "stability says k=2" is the core
methodological argument for the pivot to the binary Typical/Anomalous flag.

---

## Summary

| File | Cite in thesis? | Primary or secondary? |
|---|---|---|
| `atypicality_summary.csv` | Yes — the RQ3 result | Primary |
| `classifications.csv` | Yes — team-level evidence | Primary |
| `archetype_stability.csv` | Yes — justifies binary split | Primary |
| `delta_by_label.csv` | Yes — shows old method failure | Secondary |
| `feature_matrix.csv` | Maybe — for specific team examples | Supporting |
| `archetypes.json` | No | Internal |
| `pca_plot.html` | Yes — as a figure | Visual |
| `rss_plot.html` | Yes — as a figure | Visual |
