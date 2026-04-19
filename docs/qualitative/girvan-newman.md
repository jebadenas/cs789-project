# Girvan–Newman Community Detection

## Overview

Girvan–Newman is a **divisive (top-down) hierarchical** community detection algorithm.
It finds sub-groups within a network by progressively removing edges that act as
"bridges" between communities. It is the most suitable graph clustering method for
small peer-assessment teams (N = 5–8) because edge betweenness centrality is
well-defined on small graphs and requires no parameters to tune.

**Paper:** Girvan, M. and Newman, M.E.J. "Community structure in social and
biological networks." *Proceedings of the National Academy of Sciences*,
99(12):7821–7826, 2002.
[doi:10.1073/pnas.122653799](https://doi.org/10.1073/pnas.122653799).

---

## Theoretical Background

### Edge Betweenness Centrality

The core concept is **edge betweenness** — the number of shortest paths between all
pairs of nodes that pass through a given edge.

For an edge e, its betweenness centrality is:

```
B(e) = Σ_{s≠t} σ_st(e) / σ_st
```

where:
- σ_st = total number of shortest paths from node s to node t
- σ_st(e) = number of those shortest paths that pass through edge e

**Intuition:** If two sub-groups in a team are only loosely connected by one or two
scoring relationships, then ALL shortest paths between members of those sub-groups
must pass through those edges. Those edges get high betweenness. They are the
"bridges" between cliques.

### Why Edge Betweenness Works for Peer Scores

In a peer-assessment graph:
- Nodes = students
- Edges = scores (directed, weighted: giver → recipient)
- A high-score edge = strong connection (short path)
- A low-score edge = weak connection (long path)

The edge with highest betweenness is the weakest link between the two most
distinct sub-groups in the team. Removing it "reveals" the underlying community
structure.

---

## Algorithm — Step by Step

### Phase 1: Calculate Betweenness

For every edge in the graph, compute how many shortest paths between all node pairs
pass through it.

```
Example: 5-person team

    Alice ──15──▶ Bob ──12──▶ Carol
      │                         │
     10                        18
      ▼                         ▼
    Dave ──── 8 ────▶ Eve

Shortest path Alice→Eve goes through Alice→Dave→Eve.
Shortest path Carol→Dave goes through Carol→Eve→Dave (if that's shorter)
   or Carol→Bob→Alice→Dave.

The edge between the two clusters gets HIGH betweenness because
many shortest paths funnel through it.
```

### Phase 2: Remove the Highest-Betweenness Edge

Cut the single edge with the highest betweenness score. This may or may not
split the graph into disconnected components.

### Phase 3: Recalculate Betweenness

**Critical:** Betweenness must be recalculated after every removal. The network
adapts — removing one bridge may shift traffic to another edge, making it the
new bridge.

### Phase 4: Repeat

Continue removing edges and recalculating until no edges remain. At each step,
record the connected components — these are the communities at that level.

### Result: A Dendrogram

The output is a hierarchical tree (dendrogram) showing how the team splits:

```
Level 0: {Alice, Bob, Carol, Dave, Eve}         ← whole team
Level 1: {Alice, Dave}, {Bob, Carol, Eve}        ← first split
Level 2: {Alice, Dave}, {Bob}, {Carol, Eve}      ← second split
Level 3: {Alice}, {Dave}, {Bob}, {Carol, Eve}    ← third split
Level 4: all singletons                          ← fully decomposed
```

The **first split** is the most informative — it reveals the primary structural
divide within the team.

---

## Interpreting the Dendrogram for Team Dynamics

| Dendrogram Pattern | Interpretation |
|---|---|
| First split isolates 1 student | Loosely connected member (free-rider, excluded, or non-submitter) |
| First split is roughly even (3+2 or 3+3) | Two sub-cliques within the team |
| Many edges removed before any split | Dense, cohesive team — no clear sub-groups |
| First split matches high-scorer vs low-scorer groups | Performance-based social divide |
| Early cascade of splits (each step isolates 1 node) | Star topology — one central member connected to all |

---

## Handling Weighted Directed Graphs

The default `nx.community.girvan_newman(G)` uses unweighted betweenness. For
peer-score data, we need **weighted betweenness** where high scores = short
distances and low scores = long distances.

This requires a custom `most_valuable_edge` function:

```python
def most_central_edge(G):
    """Find the edge with highest betweenness, using score weights."""
    centrality = nx.edge_betweenness_centrality(G, weight="weight")
    return max(centrality, key=centrality.get)

comp = nx.community.girvan_newman(G, most_valuable_edge=most_central_edge)
```

**Weight interpretation:** In NetworkX's betweenness calculation with
`weight="weight"`, the weight is treated as a **distance** (cost to traverse).
Since our weights are scores (high = good), we may need to invert them
(e.g., `1 / score`) so that high-scoring edges are "short" (easy to traverse)
and low-scoring edges are "long" (hard to traverse). This ensures betweenness
correctly identifies weak links.

---

## Complexity

- **Time:** O(m²n) where m = edges, n = nodes.
- **For a 6-person team:** m ≈ 30 (complete directed graph), n = 6.
  That's ~5,400 operations — effectively instant.
- **Contrast with Louvain/Leiden:** Those are designed for networks with
  thousands–millions of nodes and are overkill (and unreliable) at this scale.

---

## Advantages and Limitations

### Advantages

1. **No parameters to tune.** No k (number of clusters), no resolution, no seed.
   The algorithm deterministically finds the hierarchy.
2. **Works on small graphs.** Edge betweenness is meaningful even with 5 nodes.
3. **Directed + weighted support.** Via the custom edge function.
4. **Hierarchical output.** The dendrogram reveals structure at multiple levels,
   not just a single flat partition.
5. **Interpretable.** "This edge was cut first because it had the highest
   betweenness" is a clear, explainable result.

### Limitations

1. **Structural, not semantic.** Finding that {Alice, Dave} form a sub-group
   doesn't tell you *why* — you need the graph metrics (reciprocity, Gini, etc.)
   to interpret the dynamics.
2. **Edge betweenness can be unstable.** If multiple edges have similar
   betweenness, the first split can be somewhat arbitrary. In practice, for
   small dense graphs with clear sub-structure, this is rarely an issue.
3. **No overlapping communities.** Each node belongs to exactly one community at
   each level. Real team dynamics may involve students who "bridge" two sub-groups.

---

## Comparison with Other Clustering Methods

| Method | Min Useful N | Parameters | Directed? | Weighted? | Output |
|---|---|---|---|---|---|
| **Girvan–Newman** | **~5** | **None** | **Yes** | **Yes (custom)** | **Dendrogram** |
| Louvain | ~30 | resolution | Yes | Yes | Flat partition |
| Leiden | ~30 | resolution, γ | Yes | Yes | Flat partition |
| Spectral Clustering | ~20 | k (num clusters) | No (symmetric) | Yes | Flat partition |
| Label Propagation | ~15 | None | Yes | Yes | Flat partition (non-deterministic) |
| Stochastic Block Model | ~50 | Num groups | Yes | Yes | Probabilistic partition |

Girvan–Newman is the clear choice for N = 5–8.

---

## References

1. Girvan, M. and Newman, M.E.J. "Community structure in social and biological
   networks." *PNAS*, 99(12):7821–7826, 2002.
   [doi:10.1073/pnas.122653799](https://doi.org/10.1073/pnas.122653799).

2. Newman, M.E.J. and Girvan, M. "Finding and evaluating community structure in
   networks." *Physical Review E*, 69(2):026113, 2004.
   [doi:10.1103/PhysRevE.69.026113](https://doi.org/10.1103/PhysRevE.69.026113).
   — Introduces modularity Q as a quality measure for choosing the best level
   in the dendrogram.

3. Brandes, U. "A faster algorithm for betweenness centrality." *Journal of
   Mathematical Sociology*, 25(2):163–177, 2001.
   [doi:10.1080/0022250X.2001.9990249](https://doi.org/10.1080/0022250X.2001.9990249).
   — The O(mn) betweenness algorithm used internally by NetworkX.

4. Freeman, L.C. "A set of measures of centrality based on betweenness."
   *Sociometry*, 40(1):35–41, 1977.
   [doi:10.2307/3033543](https://doi.org/10.2307/3033543).
   — Original definition of betweenness centrality.

5. Hagberg, A.A., Schult, D.A. and Swart, P.J. "Exploring network structure,
   dynamics, and function using NetworkX." *SciPy 2008*, pp. 11–15.
   [https://conference.scipy.org/proceedings/scipy2008/paper_2/](https://conference.scipy.org/proceedings/scipy2008/paper_2/).

### NetworkX API Reference

- `girvan_newman`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.centrality.girvan_newman.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.centrality.girvan_newman.html)
- `edge_betweenness_centrality`: [https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.edge_betweenness_centrality.html](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.edge_betweenness_centrality.html)
