# Radar Chart (Spider/Polar Chart) for Team Dynamic Profiles

## Overview

A radar chart plots a team's dynamic profile as a polygon on a polar coordinate
system, where each axis represents one metric (reciprocity, variance, asymmetry,
etc.). The **shape** of the polygon IS the team's fingerprint — different dynamics
produce visually distinct shapes that can be compared at a glance.

This is the **comparison visualisation** — while the force-layout graph shows
one team in detail, the radar chart lets you overlay multiple teams and spot
outliers instantly.

**Foundational concept:** Radar charts (also called spider charts, star plots, or
Kiviat diagrams) were introduced for multivariate data comparison. Their use in
network analysis for profiling graph properties is a practical application of
standard multivariate visualisation.

---

## How It Works

### Structure

A radar chart has:
- **Axes:** Radial spokes emanating from the centre, one per metric
- **Scale:** Each axis runs from 0 (centre) to 1 (outer edge), normalised
- **Polygon:** A closed shape connecting the team's value on each axis
- **Fill:** Semi-transparent interior to make shape visible

```
                Reciprocity (0.8)
                     ▲
                    ╱ ╲
                   ╱   ╲
   Assortativity  ╱     ╲  Variance
      (0.3) ────╱── ● ──╲──── (0.6)
               ╱    ╱╲    ╲
        Gini  ╱   ╱    ╲   ╲  Clustering
       (0.7) ╱  ╱        ╲  ╲ (0.4)
              ╲╱            ╲╱
                 Asymmetry
                   (0.2)
```

### The Metrics (Axes)

Each axis is one of the team-level graph metrics. All are normalised to [0, 1]
using the distribution across ALL teams in the dataset (percentile or min-max
scaling):

| Axis | Metric | What High Values Mean |
|---|---|---|
| **Reciprocity** | Mean pairwise scoring symmetry | Team members rate each other similarly |
| **Variance** | Mean score variance per rater | Raters differentiate between teammates |
| **Asymmetry** | Mean absolute difference of reciprocal pairs | Directional/unequal scoring relationships |
| **Clustering** | Mean weighted clustering coefficient | Tight sub-cliques exist within the team |
| **Gini** | Gini coefficient of total scores received | Score distribution is unequal (free-rider signal) |
| **Assortativity** | Degree assortativity coefficient | High-scorers preferentially rate other high-scorers |

### Normalisation

Raw metrics are on different scales. Before plotting:

```python
# Min-max normalisation across all teams
for metric in metrics:
    values = [team.profile[metric] for team in all_teams]
    min_val, max_val = min(values), max(values)
    for team in all_teams:
        team.normalised[metric] = (team.profile[metric] - min_val) / (max_val - min_val)
```

**Alternative:** Use percentile rank (team's value as a percentile within the
dataset). This is more robust to outliers.

---

## Reading the Shapes

### Cohesive Team

```
         Reciprocity
              ▲
         ╭───●───╮
        ╱    │    ╲
  Assortativity   Variance
       ●─────┼─────●
        ╲    │    ╱
         ╰───●───╯
         Asymmetry
```

**Shape:** Roughly circular, moderate values on all axes.
**Meaning:** Balanced scoring — everyone rates everyone moderately and
symmetrically. No extreme patterns.

### Collusive Team

```
         Reciprocity ← HIGH
              ▲
         ╭───●───────╮
        ╱    │         ╲
  Assortativity       Variance ← LOW
       ●     │              ●
        ╲    │         ╱
         ╰───●───────╯
         Asymmetry ← LOW
```

**Shape:** Stretched toward reciprocity, compressed on variance and asymmetry.
**Meaning:** Everyone rates everyone similarly AND highly. Low differentiation.
Could indicate genuine team harmony or coordinated score inflation.

### Free-Rider Team

```
         Reciprocity ← LOW
              ▲
              ●
             ╱ ╲
  Assortativity   Variance ← HIGH
       ●    │         ●
        ╲  ╱│╲       ╱
         ╲╱ │  ╲   ╱
         ●──│────●
   Gini ← HIGH
```

**Shape:** Spike on Gini and variance, low reciprocity.
**Meaning:** Scores are unevenly distributed (one student gets much less).
High variance because raters are trying to differentiate the free-rider.
Low reciprocity because the free-rider doesn't rate others proportionally.

### Conflict Team

```
         Reciprocity ← LOW
              ▲
              ●
              │
  Assortativity   Variance ← HIGH
       ●     │              ●
        ╲    │         ╱
         ╲   │       ╱
          ╲──●─────╱
         Asymmetry ← HIGH
```

**Shape:** Stretched toward asymmetry and variance, compressed on reciprocity.
**Meaning:** Highly directional scoring (A rates B high, B rates A low). High
disagreement about who contributed what.

---

## Overlaying Multiple Teams

The power of radar charts is **comparison**. Overlay 2–4 teams with different
fill colours:

```python
fig = go.Figure()

fig.add_trace(go.Scatterpolar(
    r=team_12_values + [team_12_values[0]],   # close the polygon
    theta=metric_names + [metric_names[0]],
    fill='toself',
    fillcolor='rgba(31, 119, 180, 0.2)',       # semi-transparent blue
    line=dict(color='rgb(31, 119, 180)'),
    name='Team 12 (Cohesive)'
))

fig.add_trace(go.Scatterpolar(
    r=team_7_values + [team_7_values[0]],
    theta=metric_names + [metric_names[0]],
    fill='toself',
    fillcolor='rgba(255, 127, 14, 0.2)',       # semi-transparent orange
    line=dict(color='rgb(255, 127, 14)'),
    name='Team 7 (Conflict)'
))

fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    showlegend=True,
    title="Team Dynamic Comparison"
)
```

**Readability limit:** More than ~5 overlaid polygons become unreadable.
For large datasets, use small multiples (one radar per team in a grid)
instead of overlaying.

---

## Constructing the Radar from ScoreMatrix

The data pipeline is:

```
ScoreMatrix
    │
    ▼
Graph Metrics (dynamics.py)
    │ reciprocity, variance, asymmetry,
    │ clustering, gini, assortativity
    ▼
Normalisation (across all teams)
    │
    ▼
Scatterpolar trace (Plotly)
    │
    ▼
Interactive HTML
```

Each `ScoreMatrix` produces a dict of raw metric values. These are normalised
relative to the full dataset, then plotted.

---

## Advantages and Limitations

### Advantages

1. **Instant pattern recognition.** Different team dynamics produce visibly
   different shapes — no need to compare numbers in a table.
2. **Cross-team comparison.** Overlay or juxtapose teams to find outliers.
3. **Compact.** Six dimensions in one small chart.
4. **Interactive (Plotly).** Hover for exact values, toggle teams on/off.
5. **Classification validation.** If your threshold-based classifier labels
   a team as "Collusive," the radar shape should match the expected pattern.

### Limitations

1. **Axis ordering matters.** Different orderings produce different visual
   shapes for the same data. Choose a consistent order and stick with it.
2. **Area is misleading.** Polygon area doesn't have a meaningful
   interpretation — it depends on axis ordering and value distribution.
   Don't interpret "bigger polygon = better/worse team."
3. **Not for >5 teams overlaid.** Use small multiples instead.
4. **Normalisation sensitivity.** One extreme outlier team can compress all
   other teams' values toward the centre. Consider percentile-based
   normalisation for robustness.

---

## References

1. Chambers, J.M., Cleveland, W.S., Kleiner, B. and Tukey, P.A. *Graphical
   Methods for Data Analysis*. Wadsworth & Brooks/Cole, 1983.
   ISBN: 978-0-534-98052-8.
   — Early treatment of star plots and radar charts for multivariate data.

2. Few, S. "Keep Radar Graphs Below the Radar — Far Below."
   *Perceptual Edge*, 2005.
   [https://www.perceptualedge.com/articles/dmreview/radar_graphs.pdf](https://www.perceptualedge.com/articles/dmreview/radar_graphs.pdf).
   — Critical analysis of radar chart limitations and when to use alternatives.

3. Saary, M.J. "Radar plots: a useful way for presenting multivariate health
   care data." *Journal of Clinical Epidemiology*, 61(4):311–317, 2008.
   [doi:10.1016/j.jclinepi.2007.04.021](https://doi.org/10.1016/j.jclinepi.2007.04.021).
   — Defence of radar charts for profile comparison with practical guidelines.

### Library Documentation

- Plotly Radar Charts: [https://plotly.com/python/radar-chart/](https://plotly.com/python/radar-chart/)
- Plotly `go.Scatterpolar`: [https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatterpolar.html](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatterpolar.html)
- Plotly Express `line_polar`: [https://plotly.com/python-api-reference/generated/plotly.express.line_polar.html](https://plotly.com/python-api-reference/generated/plotly.express.line_polar.html)
