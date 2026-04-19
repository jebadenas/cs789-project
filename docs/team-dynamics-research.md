# Team Dynamics Identification & Visualisation Using Peer Scores: Graph Clustering

## Executive Summary

This report investigates graph clustering and network analysis methods for identifying and visualising team dynamics from peer-assessment score data, specifically in the context of the COMPSCI 789 research project — an algorithmic peer-assessment grading engine for COMPSCI 399 data. The project already models peer scores as N×N directed weighted matrices (`ScoreMatrix`)[^1] and computes Individual Weighting Factors (IWFs) via baseline averaging and PeerRank (Walsh, 2014)[^2]. The central research question is: **can graph-based methods reveal qualitative team dynamics (collusion, free-riding, conflict, cohesion) from the same peer-score matrices?**

The key finding is that classical community detection algorithms (Louvain, Leiden, Label Propagation) are **poorly suited** for intra-team analysis because teams contain only 5–8 students — far below the scale where modularity optimisation produces meaningful partitions[^3]. Instead, this report recommends a **composite approach**: (1) a numeric profile of per-team graph metrics (reciprocity, centrality, variance, asymmetry, clustering coefficient, Gini index), (2) threshold-based classification into dynamic labels, and (3) interactive visualisation using directed force-layout graphs and radar charts via Plotly and NetworkX — both already in the project's dependency set[^4].

---

## Table of Contents

1. [Problem Context & Data Structure](#1-problem-context--data-structure)
2. [Graph Clustering Algorithms: A Survey](#2-graph-clustering-algorithms-a-survey)
   - 2.1 [Louvain Method](#21-louvain-method)
   - 2.2 [Leiden Algorithm](#22-leiden-algorithm)
   - 2.3 [Spectral Clustering](#23-spectral-clustering)
   - 2.4 [Label Propagation](#24-label-propagation)
   - 2.5 [Girvan–Newman (Edge Betweenness)](#25-girvannewman-edge-betweenness)
   - 2.6 [Stochastic Block Models](#26-stochastic-block-models)
3. [The Small-Graph Problem](#3-the-small-graph-problem)
4. [Recommended Approach: Graph Metrics for Team Dynamics](#4-recommended-approach-graph-metrics-for-team-dynamics)
   - 4.1 [Metric Definitions](#41-metric-definitions)
   - 4.2 [Classification Schema](#42-classification-schema)
5. [Visualisation Strategies](#5-visualisation-strategies)
   - 5.1 [Per-Team Directed Graph (Force Layout)](#51-per-team-directed-graph-force-layout)
   - 5.2 [Radar/Spider Chart](#52-radarspider-chart)
   - 5.3 [Heatmap of Score Matrix](#53-heatmap-of-score-matrix)
   - 5.4 [Chord Diagrams](#54-chord-diagrams)
6. [Implementation Architecture](#6-implementation-architecture)
7. [Key Libraries & Tools](#7-key-libraries--tools)
8. [Confidence Assessment](#8-confidence-assessment)
9. [References](#9-references)
10. [Footnotes](#10-footnotes)

---

## 1. Problem Context & Data Structure

The cs789-project parses COMPSCI 399 peer feedback CSV files into `ScoreMatrix` objects[^1], where:

- `matrix[i][j]` = score that **giver j** assigned to **recipient i**
- Rows are recipients, columns are givers
- Students are ordered alphabetically by email
- Teams are typically 5–8 students
- Scores are numeric point distributions (e.g., "Distribute a total of 60 points")[^5]
- Non-submitters are represented as NaN columns[^6]

Each `ScoreMatrix` is scoped to a single **(team, question)** pair[^7], meaning peer scores only exist **within** teams — there are no cross-team edges. This is a fundamental constraint that shapes which graph clustering methods are applicable.

### Current Models

| Model | Description | File |
|-------|-------------|------|
| Baseline | Simple NaN-aware mean of peer scores received | `src/models/baseline.py`[^8] |
| PeerRank | Walsh (2014) credibility-weighted fixed-point iteration | `src/models/peerrank.py`[^2] |
| WebPA | (Referenced in CLI) | `src/cli.py:15`[^9] |

The existing models compute **individual** IWFs. The qualitative/dynamics module would complement these by characterising **team-level** patterns.

---

## 2. Graph Clustering Algorithms: A Survey

### 2.1 Louvain Method

**Origin:** Blondel, V.D. et al. "Fast unfolding of communities in large networks." *Journal of Statistical Mechanics*, 2008[^10].

**Mechanism:** A greedy modularity optimisation algorithm that operates in two repeating phases:

1. **Local node moves:** Each node is moved to the neighbouring community that produces the greatest increase in modularity Q, defined as:

```
Q = (1/2m) Σ_ij [A_ij - (k_i × k_j)/(2m)] × δ(c_i, c_j)
```

where A is the adjacency matrix, k_i is the degree of node i, m is the total edge weight, and δ(c_i, c_j) = 1 if nodes i and j are in the same community[^10].

2. **Network aggregation:** Communities are collapsed into super-nodes, edges between communities become weighted edges between super-nodes.

**Complexity:** O(n log n) in practice[^10].

**NetworkX API:**
```python
communities = nx.community.louvain_communities(G, weight="weight", resolution=1.0, seed=42)
```
The function returns a list of sets, each containing node identifiers for one community[^11]. The `resolution` parameter controls granularity — higher values produce more/smaller clusters.

**Limitations:**
- Produces non-overlapping communities only[^10]
- Can produce arbitrarily badly connected (even disconnected) communities — the "bridge node" problem[^10]
- Subject to the **resolution limit of modularity**: small communities may be merged into larger ones, hiding substructure[^10][^12]
- Designed for large networks; degenerates on small graphs (N < 10)
- Has been shown to overfit empirical data[^10]

### 2.2 Leiden Algorithm

**Origin:** Traag, V.A. et al. "From Louvain to Leiden: guaranteeing well-connected communities." *Scientific Reports*, 2019[^12].

**Mechanism:** An improvement over Louvain that adds a **refinement phase** between the node-moving and aggregation steps. This refinement ensures communities remain well-connected by:
- Placing each node in its own community within the discovered partition
- Re-merging only nodes that maintain community connectivity
- Using the Reichardt-Bornholdt Potts Model (RB) quality function with a resolution parameter γ[^12]

```
Q = Σ_ij (A_ij - γ × (k_i × k_j)/(2m)) × δ(c_i, c_j)
```

**Advantages over Louvain:**
- Guarantees well-connected communities (no disconnected community problem)[^12]
- Constant Potts Model (CPM) variant addresses the resolution limit[^12]
- More efficient node visitation strategy[^12]

**NetworkX status:** Available via `nx.community.leiden_partitions()` and `nx.community.leiden_communities()`, but only through installable backends — no native NetworkX implementation[^13]. The primary Python implementation is the `leidenalg` package (wraps C++ igraph).

**Applicability to project:** Same small-graph limitations as Louvain. The resolution parameter helps, but with N=5–8 the algorithm still lacks sufficient structure to find meaningful sub-communities.

### 2.3 Spectral Clustering

**Origin:** Shi, J. and Malik, J. "Normalized cuts and image segmentation." *IEEE TPAMI*, 2000[^14].

**Mechanism:**
1. Construct the graph Laplacian L = D - A (where D is the diagonal degree matrix, A the adjacency matrix)[^14]
2. Compute the k smallest eigenvectors of L (or the normalised Laplacian L^norm = I - D^{-1/2}AD^{-1/2})
3. Use rows of the eigenvector matrix as feature vectors
4. Apply k-means clustering on these features[^14]

The physical intuition is a mass-spring system: tightly connected masses (students who rate each other highly) move together in low-frequency vibration modes[^14].

**scikit-learn API:**
```python
from sklearn.cluster import SpectralClustering

sc = SpectralClustering(n_clusters=2, affinity='precomputed', n_init=100, assign_labels='discretize')
labels = sc.fit_predict(adjacency_matrix)
```
The `affinity='precomputed'` setting accepts the peer-score matrix directly as the adjacency/affinity matrix[^15].

**Advantages:**
- Works directly on the score matrix (no graph construction needed)
- Can handle non-convex cluster shapes
- Theoretically well-understood (connected to normalised cuts)

**Limitations:**
- **Requires specifying k** (number of clusters) in advance — this is unknown for team dynamics
- With N=5–8, the eigengap heuristic for choosing k is unreliable
- Assumes the affinity matrix is symmetric — peer scores are inherently asymmetric (matrix[i][j] ≠ matrix[j][i]). Symmetrisation (e.g., averaging) loses directional information
- Computational cost is O(n³) for eigenvector computation, though irrelevant at this scale

### 2.4 Label Propagation

**Origin:** Raghavan, U.N. et al. "Near linear time algorithm to detect community structures in large-scale networks." *Physical Review E*, 2007[^16].

**Mechanism:**
1. Each node starts with a unique label
2. In each iteration, each node adopts the most frequent label among its neighbours
3. Repeat until convergence (every node has the label most common among its neighbours)[^16]

**NetworkX API:**
```python
communities = nx.community.label_propagation_communities(G)
```

**Advantages:**
- No parameters required (unlike Louvain's resolution or Spectral's k)
- Near-linear time complexity O(m)[^16]
- Simple to implement and understand

**Limitations:**
- **Non-deterministic:** produces different community structures from the same initial condition due to random label initialisation and processing order[^16]
- On small dense graphs (5–8 nodes, all connected), tends to converge to a single community trivially
- No quality guarantee — may produce meaningless partitions

### 2.5 Girvan–Newman (Edge Betweenness)

**Origin:** Girvan, M. and Newman, M.E.J. "Community structure in social and biological networks." *PNAS*, 2002[^17].

**Mechanism:** A divisive (top-down) hierarchical algorithm:
1. Calculate edge betweenness for all edges (number of shortest paths passing through each edge)
2. Remove the edge with highest betweenness
3. Recalculate betweenness for all affected edges
4. Repeat until no edges remain[^17]

This produces a **dendrogram** from top down — the entire network at the top, individual nodes at the leaves.

**NetworkX API:**
```python
communities_generator = nx.community.girvan_newman(G)
top_level_communities = next(communities_generator)  # first split
```

**Advantages:**
- Produces a full hierarchy of partitions (dendrogram)
- Principled: edges between communities naturally have high betweenness
- Works on small graphs — betweenness is meaningful even with 5–8 nodes

**Limitations:**
- O(m²n) complexity — very slow for large graphs, but fine for N=5–8
- Still produces partitions based on structural connectivity, not dynamic labels like "collusive" or "conflict"

**Applicability:** Among pure clustering methods, Girvan–Newman is **the most suitable** for small-team analysis because betweenness centrality is well-defined on small graphs and the hierarchical output reveals substructure naturally.

### 2.6 Stochastic Block Models

**Origin:** Holland, P.W. et al. "Stochastic blockmodels: First steps." *Social Networks*, 1983[^18].

**Mechanism:** A probabilistic generative model that assumes:
- Nodes belong to latent groups C_1, ..., C_r
- Edge probability between nodes u ∈ C_i and v ∈ C_j is given by a probability matrix P_ij[^18]
- The model is fitted by maximum likelihood or Bayesian inference

**Types:**
- **Assortative:** P_ii > P_ij (dense within communities, sparse between) — matches collusion patterns
- **Disassortative:** P_ii < P_ij (sparse within, dense between) — possible but uncommon in peer scoring

**Implementations:** The `graph-tool` library (C++/Python) provides efficient SBM inference. Not available in NetworkX.

**Applicability:** Theoretically ideal for detecting latent group structures in peer-scoring networks. However:
- Requires additional dependency (`graph-tool`, complex installation)
- SBM inference on N=5–8 is statistically unreliable — insufficient data for latent variable estimation
- The parameter space (number of groups, edge probabilities) is under-determined at this scale

---

## 3. The Small-Graph Problem

The fundamental challenge for applying graph clustering to this project's data is **team size**. With N=5–8 students per team:

| Algorithm | Minimum Useful N | Behaviour at N=5–8 |
|-----------|-----------------|---------------------|
| Louvain | ~30+ | Returns 1 community or N singletons |
| Leiden | ~30+ | Same as Louvain |
| Spectral | ~20+ | Eigengap is noisy; k selection fails |
| Label Propagation | ~15+ | Converges to single community trivially |
| Girvan–Newman | ~5+ | **Works**, but partitions may not align with "dynamics" |
| SBM | ~50+ | Under-determined parameter estimation |

**Why modularity optimisation fails on small graphs:**

Modularity Q compares actual edge density to expected density under a null model (random rewiring preserving degree sequence). For a complete or near-complete graph with 5–8 nodes, the null model expectation is very close to the actual density — the modularity gain from any partition is negligible[^10][^12]. This is the **resolution limit** at its extreme.

**The resolution parameter is not a solution:** While both Louvain and Leiden support a `resolution` parameter to control granularity, tuning this on a 5-node graph produces unstable, inconsistent results. There is simply not enough structural variation for the algorithm to exploit.

### What Works Instead: Direct Graph Metrics

For graphs of this size, the entire adjacency matrix is small enough to analyse directly. Rather than clustering nodes into communities, we can compute **per-graph and per-node metrics** that characterise the team's dynamic profile. This is the standard approach in social network analysis for small groups (Wasserman & Faust, 1994)[^19].

---

## 4. Recommended Approach: Graph Metrics for Team Dynamics

### 4.1 Metric Definitions

The following metrics can be computed from each team's `ScoreMatrix`, modelled as a directed weighted graph where `G.add_weighted_edges_from([(j, i, matrix[i][j])])` (giver j → recipient i).

#### 4.1.1 Reciprocity

**Definition:** Measures the symmetry of scoring relationships. For each pair (i, j), compare score[i→j] with score[j→i].

**Computation:**
```python
# Pairwise reciprocity
for i, j (i < j):
    reciprocity_ij = 1 - |matrix[i][j] - matrix[j][i]| / max(matrix[i][j], matrix[j][i])

# Team-level: mean of all pairwise reciprocities
```

**NetworkX:** `nx.overall_reciprocity(G)` measures the fraction of edges that are reciprocated (binary), but for weighted analysis, custom computation on the matrix is more informative[^20].

**Interpretation:**
- High reciprocity + high scores → mutual respect or potential collusion
- High reciprocity + low scores → mutual indifference
- Low reciprocity → asymmetric relationships (conflict, power imbalance)

#### 4.1.2 Score Variance per Rater (Differentiation)

**Definition:** Standard deviation of the scores each student gives to their teammates.

**Computation:**
```python
for j in range(N):  # for each giver
    peer_scores = matrix[:, j]  # excluding self
    variance_j = np.nanstd(peer_scores[peer_scores != matrix[j, j]])
```

**Interpretation:**
- Low variance → "flat rater" (gives everyone similar scores; possible disengagement or strategic scoring)
- High variance → "differentiator" (distinguishes between teammates; potentially more honest)
- Team-level mean variance indicates overall differentiation culture

#### 4.1.3 Weighted In-Degree Centrality

**Definition:** Total score received by each student, normalised by the maximum possible.

**Computation:**
```python
in_degree = dict(G.in_degree(weight="weight"))
# Or directly: np.nansum(matrix, axis=1) for each row (recipient)
```

**NetworkX:** `nx.in_degree_centrality(G)` (unweighted) or weighted variant via `G.in_degree(weight="weight")`[^21].

**Interpretation:**
- Identifies high-performers vs. low-performers within the team
- Combined with Gini coefficient, reveals whether scores are concentrated or evenly distributed

#### 4.1.4 Score Asymmetry

**Definition:** Mean absolute difference between reciprocal peer scores across all pairs.

**Computation:**
```python
asymmetry = 0
count = 0
for i in range(N):
    for j in range(i+1, N):
        if not np.isnan(matrix[i][j]) and not np.isnan(matrix[j][i]):
            asymmetry += abs(matrix[i][j] - matrix[j][i])
            count += 1
team_asymmetry = asymmetry / count if count > 0 else 0
```

**Interpretation:**
- High asymmetry → directional scoring (one person rates the other high, but not vice versa)
- Signals power imbalance, unrequited contribution recognition, or manipulation

#### 4.1.5 Weighted Clustering Coefficient

**Definition:** Measures how tightly connected a node's neighbours are to each other, weighted by edge strength.

**NetworkX:** `nx.clustering(G, weight="weight")`[^22]

For weighted graphs, the definition uses the geometric average of subgraph edge weights, normalised by the maximum weight[^22]. For directed graphs, there are separate in/out/cycle/middleman variants.

**Interpretation:**
- High clustering → tight sub-cliques within the team (e.g., 3 students who all rate each other highly)
- Low clustering → more distributed scoring patterns

#### 4.1.6 Gini Coefficient of Scores Received

**Definition:** Measures inequality in how scores are distributed across recipients.

**Computation:**
```python
def gini(scores):
    sorted_scores = np.sort(scores)
    n = len(sorted_scores)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * sorted_scores) / (n * np.sum(sorted_scores))) - (n + 1) / n

row_sums = np.nansum(matrix, axis=1)  # total score each recipient received
team_gini = gini(row_sums)
```

**Interpretation:**
- High Gini → one or two students receive disproportionately high/low scores (free-rider signal)
- Low Gini → egalitarian scoring (cohesive or undifferentiated)

#### 4.1.7 Degree Assortativity

**Definition:** Measures whether high-degree nodes connect preferentially to other high-degree nodes.

**NetworkX:** `nx.degree_assortativity_coefficient(G, x='out', y='in', weight='weight')`[^23]

Based on Newman (2003)[^23]: computes the Pearson correlation of degrees across edges.

**Interpretation:**
- Positive assortativity → high-scorers rate other high-scorers highly (assortative mixing; clique formation)
- Negative assortativity → high-scorers rate low-scorers, and vice versa (disassortative; possible compensatory behaviour)

### 4.2 Classification Schema

Using the metrics from §4.1, each team can be classified into one or more dynamic labels:

| Dynamic Label | Rule | Key Metrics |
|---------------|------|-------------|
| **Cohesive** | Moderate reciprocity + low asymmetry + moderate variance + low Gini | Balanced team |
| **Collusive** | High reciprocity + low variance + uniformly high scores + high clustering | Score inflation |
| **Free-rider present** | High Gini + one student's in-degree well below team mean + high variance from that student's raters | Unequal contribution |
| **Conflict** | High asymmetry + high variance + low reciprocity | Interpersonal friction |
| **Dysfunctional** | Low reciprocity + high variance + high asymmetry + high Gini | Multiple issues |
| **Dominant member** | High Gini (scores received) + one node with much higher in-degree centrality | Single leader/star |

**Threshold calibration:** Thresholds should be determined empirically from the COMPSCI 399 dataset using distribution analysis (percentiles). For example:
- "High reciprocity" = team reciprocity > 75th percentile across all teams
- "High Gini" = Gini > 0.2 (or 75th percentile)

This calibration should be done as a pre-processing step on the full dataset before applying labels.

---

## 5. Visualisation Strategies

All visualisation approaches below use libraries already in the project's `requirements.txt` (Plotly, NetworkX, Pandas)[^4].

### 5.1 Per-Team Directed Graph (Force Layout)

**Purpose:** Visualise the scoring relationships within a single team as an interactive directed graph.

**Method:**
1. Build a `nx.DiGraph` from the `ScoreMatrix` (edge j→i with weight `matrix[i][j]`)
2. Compute positions using `nx.spring_layout(G, weight="weight", seed=42)` — high-scoring pairs are pulled closer[^24]
3. Render with Plotly `go.Scatter` traces for edges and nodes[^25]

**Visual encodings:**
- **Node size:** Proportional to total score received (in-degree)
- **Node colour:** IWF score from PeerRank (or classification label)
- **Edge thickness:** Proportional to score magnitude
- **Edge colour:** Gradient from red (low score) to green (high score)
- **Arrow direction:** Shows who scored whom
- **Hover text:** Student name, scores given/received, IWF

**Implementation sketch:**
```python
import networkx as nx
import plotly.graph_objects as go

def build_team_graph(score_matrix: ScoreMatrix) -> nx.DiGraph:
    G = nx.DiGraph()
    for s in score_matrix.students:
        G.add_node(s.index, name=s.name, email=s.email)
    for i in range(len(score_matrix.students)):
        for j in range(len(score_matrix.students)):
            if i != j and not np.isnan(score_matrix.matrix[i][j]):
                G.add_edge(j, i, weight=score_matrix.matrix[i][j])
    return G

def visualise_team_graph(G: nx.DiGraph, title: str) -> go.Figure:
    pos = nx.spring_layout(G, weight="weight", seed=42)
    
    # Edge traces (one per edge for individual styling)
    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines',
            line=dict(width=data['weight'] / 5, color='rgba(100,100,100,0.5)'),
            hoverinfo='text',
            text=f"{G.nodes[u]['name']} → {G.nodes[v]['name']}: {data['weight']}"
        ))
    
    # Node trace
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_sizes = [sum(d['weight'] for _, _, d in G.in_edges(n, data=True)) for n in G.nodes()]
    node_text = [G.nodes[n]['name'] for n in G.nodes()]
    
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        marker=dict(size=[s/max(node_sizes)*40+10 for s in node_sizes],
                    color=node_sizes, colorscale='Viridis', showscale=True),
        text=node_text, textposition="top center", hoverinfo='text'
    )
    
    fig = go.Figure(data=edge_traces + [node_trace],
                    layout=go.Layout(title=title, showlegend=False,
                                     xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                     yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    return fig
```

**NetworkX spring layout** uses the Fruchterman–Reingold force-directed algorithm[^24]: nodes are treated as charged particles that repel each other, while edges act as springs pulling connected nodes together. Edge weight controls spring strength — high-scoring pairs cluster closer.

### 5.2 Radar/Spider Chart

**Purpose:** Compare team dynamic profiles at a glance across multiple teams.

**Method:** Each team's metrics from §4.1 are normalised to [0, 1] and plotted on a radar chart with one axis per metric.

```python
import plotly.graph_objects as go

def radar_chart(team_profiles: dict[str, dict[str, float]]) -> go.Figure:
    metrics = ['reciprocity', 'variance', 'asymmetry', 'clustering', 'gini', 'assortativity']
    fig = go.Figure()
    
    for team_name, profile in team_profiles.items():
        values = [profile[m] for m in metrics] + [profile[metrics[0]]]  # close the polygon
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics + [metrics[0]],
            fill='toself',
            name=team_name
        ))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                      showlegend=True, title="Team Dynamic Profiles")
    return fig
```

**Interpretation:** Teams with different shapes have different dynamics. A team with a "spike" on Gini but low reciprocity looks very different from one with uniform moderate values.

### 5.3 Heatmap of Score Matrix

**Purpose:** Direct visualisation of the raw peer-score matrix for a single team.

```python
import plotly.express as px

def score_heatmap(score_matrix: ScoreMatrix) -> go.Figure:
    names = [s.name for s in score_matrix.students]
    fig = px.imshow(score_matrix.matrix,
                    x=names, y=names,
                    labels=dict(x="Giver", y="Recipient", color="Score"),
                    color_continuous_scale="RdYlGn",
                    title=f"{score_matrix.team_name} — {score_matrix.question_label}")
    return fig
```

**Value:** Shows asymmetry directly (off-diagonal pairs), identifies flat raters (uniform columns), and highlights outlier scores visually.

### 5.4 Chord Diagrams

**Purpose:** Show bidirectional scoring relationships with thickness proportional to score magnitude.

Plotly does not natively support chord diagrams, but they can be approximated using circular layouts in NetworkX with Plotly rendering, or via the `holoviews` / `bokeh` ecosystem. For this project, the directed graph (§5.1) provides similar information more simply.

---

## 6. Implementation Architecture

Proposed file structure within the existing project:

```
src/
  qualitative/
    __init__.py          # (existing, empty)
    dynamics.py          # Compute numeric profile from ScoreMatrix → TeamProfile
    classify.py          # Apply threshold rules → TeamLabel enum
    thresholds.py        # Calibrate thresholds from full dataset
  visualization/
    __init__.py          # (existing, empty)
    team_graph.py        # Per-team directed graph (Plotly)
    radar.py             # Radar chart comparing teams
    heatmap.py           # Score matrix heatmap
```

**Data flow:**

```
ScoreMatrix (from parser)
       │
       ▼
 dynamics.py ──────► TeamProfile (dataclass)
       │                    │
       ▼                    ▼
 classify.py          team_graph.py
       │              radar.py
       ▼              heatmap.py
 TeamLabel(s)              │
       │                   ▼
       └───────────► Plotly Figure (HTML output)
```

**Integration with existing CLI:**

The CLI (`src/cli.py`)[^9] could be extended with a `--dynamics` flag:
```bash
python3 -m src run data/myfile.csv --dynamics
```

This would compute the team profile, generate labels, and produce interactive Plotly HTML files in the `output/` directory.

---

## 7. Key Libraries & Tools

| Library | Already in Project? | Purpose | Key APIs |
|---------|:-------------------:|---------|----------|
| **NetworkX** | ✅[^4] | Graph construction, metrics, layouts | `nx.DiGraph`, `nx.spring_layout`, `nx.clustering`, `nx.reciprocity`, `nx.degree_assortativity_coefficient` |
| **Plotly** | ✅[^4] | Interactive visualisation | `go.Scatter`, `go.Scatterpolar`, `px.imshow` |
| **NumPy** | ✅ (via Polars/scikit-learn) | Matrix operations | `np.nanmean`, `np.nanstd`, `np.nansum` |
| **Pandas** | ✅[^4] | DataFrames for profile tables | `pd.DataFrame` |
| **scikit-learn** | ✅[^4] | Spectral clustering (if desired) | `SpectralClustering(affinity='precomputed')` |
| **leidenalg** | ❌ | Leiden algorithm | `la.find_partition()` |
| **graph-tool** | ❌ | Stochastic block models | `graph_tool.inference` |

**Recommendation:** No new dependencies needed. The entire team dynamics analysis can be built with NetworkX + Plotly + NumPy, all already in `requirements.txt`.

---

## 8. Confidence Assessment

| Claim | Confidence | Basis |
|-------|:----------:|-------|
| Community detection (Louvain/Leiden/etc.) is unsuitable for N=5–8 | **High** | Well-documented resolution limit[^10][^12]; confirmed by algorithm design (modularity optimisation requires sufficient scale) |
| Graph metrics (reciprocity, centrality, etc.) can characterise team dynamics | **High** | Standard SNA methodology (Wasserman & Faust, 1994)[^19]; metrics are well-defined on small directed weighted graphs |
| Classification thresholds will need empirical calibration | **High** | No universal thresholds exist; depends on score distribution in COMPSCI 399 data |
| Plotly + NetworkX can produce publication-quality team visualisations | **High** | Both libraries support interactive directed graph rendering[^24][^25]; already in project dependencies |
| Girvan–Newman is the most suitable *pure clustering* method for this scale | **Medium** | Works on small graphs, but its output (partitions) may not directly map to dynamic labels |
| The proposed classification schema captures real team dynamics | **Medium** | Reasonable heuristics based on SNA literature, but validation against ground truth (e.g., instructor assessments) is needed |
| Spectral clustering could work with symmetrised matrices | **Low** | Theoretically possible, but symmetrisation loses directional information which is critical for detecting asymmetric dynamics |

---

## 9. References

1. Blondel, V.D., Guillaume, J.-L., Lambiotte, R. and Lefebvre, E. "Fast unfolding of communities in large networks." *Journal of Statistical Mechanics: Theory and Experiment*, 2008(10), P10008. [doi:10.1088/1742-5468/2008/10/P10008](https://doi.org/10.1088/1742-5468/2008/10/P10008). Also available at [arXiv:0803.0476](https://arxiv.org/abs/0803.0476).
2. Walsh, T. "The PeerRank method for peer assessment." In *Proceedings of the 21st European Conference on Artificial Intelligence (ECAI 2014)*, pp. 909–914. IOS Press, 2014. [doi:10.3233/978-1-61499-419-0-909](https://doi.org/10.3233/978-1-61499-419-0-909).
3. Traag, V.A., Waltman, L. and van Eck, N.J. "From Louvain to Leiden: guaranteeing well-connected communities." *Scientific Reports*, 9:5233, 2019. [doi:10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z). Also available at [arXiv:1810.08473](https://arxiv.org/abs/1810.08473).
4. Shi, J. and Malik, J. "Normalized cuts and image segmentation." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 22(8):888–905, 2000. [doi:10.1109/34.868688](https://doi.org/10.1109/34.868688).
5. Raghavan, U.N., Albert, R. and Kumara, S. "Near linear time algorithm to detect community structures in large-scale networks." *Physical Review E*, 76(3):036106, 2007. [doi:10.1103/PhysRevE.76.036106](https://doi.org/10.1103/PhysRevE.76.036106). Also available at [arXiv:0709.2938](https://arxiv.org/abs/0709.2938).
6. Girvan, M. and Newman, M.E.J. "Community structure in social and biological networks." *Proceedings of the National Academy of Sciences*, 99(12):7821–7826, 2002. [doi:10.1073/pnas.122653799](https://doi.org/10.1073/pnas.122653799).
7. Holland, P.W., Laskey, K.B. and Leinhardt, S. "Stochastic blockmodels: First steps." *Social Networks*, 5(2):109–137, 1983. [doi:10.1016/0378-8733(83)90021-7](https://doi.org/10.1016/0378-8733(83)90021-7).
8. Newman, M.E.J. "Mixing patterns in networks." *Physical Review E*, 67(2):026126, 2003. [doi:10.1103/PhysRevE.67.026126](https://doi.org/10.1103/PhysRevE.67.026126). Also available at [arXiv:cond-mat/0209450](https://arxiv.org/abs/cond-mat/0209450).
9. Wasserman, S. and Faust, K. *Social Network Analysis: Methods and Applications*. Cambridge University Press, 1994. [doi:10.1017/CBO9780511815478](https://doi.org/10.1017/CBO9780511815478). ISBN: 978-0-521-38707-1.
10. Fruchterman, T.M.J. and Reingold, E.M. "Graph drawing by force-directed placement." *Software: Practice and Experience*, 21(11):1129–1164, 1991. [doi:10.1002/spe.4380211102](https://doi.org/10.1002/spe.4380211102).
11. Freeman, L.C. "Centrality in social networks: Conceptual clarification." *Social Networks*, 1(3):215–239, 1979. [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7).
12. Page, L., Brin, S., Motwani, R. and Winograd, T. "The PageRank citation ranking: Bringing order to the web." Technical Report 1999-66, Stanford InfoLab, 1999. Available at [http://ilpubs.stanford.edu:8090/422/](http://ilpubs.stanford.edu:8090/422/).
13. Fortunato, S. and Barthélemy, M. "Resolution limit in community detection." *Proceedings of the National Academy of Sciences*, 104(1):36–41, 2007. [doi:10.1073/pnas.0605965104](https://doi.org/10.1073/pnas.0605965104). — Foundational paper on the modularity resolution limit.
14. Hagberg, A.A., Schult, D.A. and Swart, P.J. "Exploring network structure, dynamics, and function using NetworkX." In *Proceedings of the 7th Python in Science Conference (SciPy 2008)*, pp. 11–15, 2008. Available at [https://conference.scipy.org/proceedings/scipy2008/paper_2/](https://conference.scipy.org/proceedings/scipy2008/paper_2/). — Primary NetworkX reference.
15. Pedregosa, F. et al. "Scikit-learn: Machine learning in Python." *Journal of Machine Learning Research*, 12:2825–2830, 2011. Available at [https://jmlr.org/papers/v12/pedregosa11a.html](https://jmlr.org/papers/v12/pedregosa11a.html). — Primary scikit-learn reference.

---

## 10. Footnotes

[^1]: `src/parsing/schemas.py:17-52` — `ScoreMatrix` class with N×N matrix, team_name, question_label, students list. `matrix[i][j]` = score giver j assigned to recipient i.

[^2]: `src/models/peerrank.py:1-101` — PeerRank implementation following Walsh (2014). Credibility-weighted fixed-point iteration with normalised score matrix A, learning rate α=0.1, convergence threshold ε=10⁻⁶.

[^3]: Fortunato, S. and Barthélemy, M. "Resolution limit in community detection." *PNAS*, 104(1):36–41, 2007. [doi:10.1073/pnas.0605965104](https://doi.org/10.1073/pnas.0605965104). Also discussed in Blondel et al. (2008) [Ref 1]: modularity optimisation merges small communities into larger ones, hiding substructure.

[^4]: `requirements.txt` — Lists: polars, scikit-learn, networkx, plotly, ipykernel, pydantic, jupyter, pandas, pyarrow.

[^5]: `src/parsing/parser.py:21` — `_POINT_DIST_PATTERN = re.compile(r"Distribute a total of", re.IGNORECASE)` — filters for point-distribution questions.

[^6]: `src/parsing/parser.py:264-277` — Non-submitter detection: "all their scores are NaN" → column stays NaN. Teams with ≥50% non-submitters are dropped.

[^7]: `src/parsing/parser.py:31-75` — `parse_session()` returns `dict[tuple[str, str], ScoreMatrix]` keyed by `(team_name, question_label)`.

[^8]: `src/models/baseline.py:1-21` — Baseline model: `np.nanmean(matrix, axis=1)` after zeroing diagonal.

[^9]: `src/cli.py:15` — `from src.models.webpa import webpa` — WebPA model imported in CLI.

[^10]: Blondel, V.D. et al. "Fast unfolding of communities in large networks." *J. Stat. Mech.*, P10008, 2008. [doi:10.1088/1742-5468/2008/10/P10008](https://doi.org/10.1088/1742-5468/2008/10/P10008) — Algorithm description: modularity formula Q = (1/2m)Σ[A_ij - k_ik_j/2m]δ(c_i,c_j), two-phase iteration, O(n log n) complexity. Resolution limit discussed in Fortunato & Barthélemy (2007) [Ref 13].

[^11]: Hagberg, A.A., Schult, D.A. and Swart, P.J. "Exploring network structure, dynamics, and function using NetworkX." *SciPy 2008*, pp. 11–15. NetworkX `louvain_communities` documentation: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html).

[^12]: Traag, V.A., Waltman, L. and van Eck, N.J. "From Louvain to Leiden: guaranteeing well-connected communities." *Scientific Reports*, 9:5233, 2019. [doi:10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z) — Refinement phase, Reichardt-Bornholdt Potts Model (RB), Constant Potts Model (CPM), guaranteed well-connected communities.

[^13]: NetworkX documentation, community module: [https://networkx.org/documentation/stable/reference/algorithms/community.html](https://networkx.org/documentation/stable/reference/algorithms/community.html) — Leiden functions require an installable backend; no native NetworkX implementation. Primary Leiden implementation: `leidenalg` Python package, see Traag et al. (2019) [Ref 3].

[^14]: Shi, J. and Malik, J. "Normalized cuts and image segmentation." *IEEE TPAMI*, 22(8):888–905, 2000. [doi:10.1109/34.868688](https://doi.org/10.1109/34.868688) — Graph Laplacian L = D - A, normalised Laplacian L^norm = I - D^{-1/2}AD^{-1/2}, spectral embedding via eigenvectors of smallest eigenvalues.

[^15]: Pedregosa, F. et al. "Scikit-learn: Machine learning in Python." *JMLR*, 12:2825–2830, 2011. scikit-learn `SpectralClustering` documentation: [https://scikit-learn.org/stable/modules/generated/sklearn.cluster.SpectralClustering.html](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.SpectralClustering.html) — `affinity='precomputed'` accepts an adjacency matrix directly.

[^16]: Raghavan, U.N., Albert, R. and Kumara, S. "Near linear time algorithm to detect community structures in large-scale networks." *Physical Review E*, 76(3):036106, 2007. [doi:10.1103/PhysRevE.76.036106](https://doi.org/10.1103/PhysRevE.76.036106) — No parameters required; near-linear time O(m); non-deterministic due to random initialisation and processing order.

[^17]: Girvan, M. and Newman, M.E.J. "Community structure in social and biological networks." *PNAS*, 99(12):7821–7826, 2002. [doi:10.1073/pnas.122653799](https://doi.org/10.1073/pnas.122653799) — Divisive algorithm: progressively removes edges with highest betweenness centrality, producing a dendrogram of community structure.

[^18]: Holland, P.W., Laskey, K.B. and Leinhardt, S. "Stochastic blockmodels: First steps." *Social Networks*, 5(2):109–137, 1983. [doi:10.1016/0378-8733(83)90021-7](https://doi.org/10.1016/0378-8733(83)90021-7) — Generative model for random graphs with latent community structure; nodes belong to groups with distinct intra/inter-group edge probabilities.

[^19]: Wasserman, S. and Faust, K. *Social Network Analysis: Methods and Applications*. Cambridge University Press, 1994. [doi:10.1017/CBO9780511815478](https://doi.org/10.1017/CBO9780511815478), pp. 169–215 (Chapter 5: Centrality) — foundational text on small-group network analysis metrics.

[^20]: NetworkX documentation, `overall_reciprocity(G)`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.reciprocity.overall_reciprocity.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.reciprocity.overall_reciprocity.html). See also Garlaschelli, D. and Loffredo, M.I. "Patterns of link reciprocity in directed networks." *Physical Review Letters*, 93(26):268701, 2004. [doi:10.1103/PhysRevLett.93.268701](https://doi.org/10.1103/PhysRevLett.93.268701).

[^21]: Freeman, L.C. "Centrality in social networks: Conceptual clarification." *Social Networks*, 1(3):215–239, 1979. [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7). NetworkX `in_degree_centrality`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.in_degree_centrality.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.in_degree_centrality.html).

[^22]: Barrat, A., Barthélemy, M., Pastor-Satorras, R. and Vespignani, A. "The architecture of complex weighted networks." *PNAS*, 101(11):3747–3752, 2004. [doi:10.1073/pnas.0400087101](https://doi.org/10.1073/pnas.0400087101) — Weighted clustering coefficient generalisation. NetworkX `clustering`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.cluster.clustering.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.cluster.clustering.html).

[^23]: Newman, M.E.J. "Mixing patterns in networks." *Physical Review E*, 67(2):026126, 2003. [doi:10.1103/PhysRevE.67.026126](https://doi.org/10.1103/PhysRevE.67.026126), Eq. (21). NetworkX `degree_assortativity_coefficient`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.assortativity.degree_assortativity_coefficient.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.assortativity.degree_assortativity_coefficient.html).

[^24]: Fruchterman, T.M.J. and Reingold, E.M. "Graph drawing by force-directed placement." *Software: Practice and Experience*, 21(11):1129–1164, 1991. [doi:10.1002/spe.4380211102](https://doi.org/10.1002/spe.4380211102). NetworkX `spring_layout`: [https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html).

[^25]: Plotly Python documentation, "Network Graphs in Python": [https://plotly.com/python/network-graphs/](https://plotly.com/python/network-graphs/) — Constructing `go.Scatter` traces for edges (mode='lines') and nodes (mode='markers') from NetworkX graph positions.
