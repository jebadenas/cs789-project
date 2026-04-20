# Per-Team Directed Force-Layout Graph

## Overview

A force-directed graph visualises scoring relationships within a single team as an
interactive directed network. Students are nodes, peer scores are weighted arrows
between them. A physics simulation positions nodes so that students who rate each
other highly cluster together, while weakly-connected students drift apart.

This is the **primary visualisation** for team dynamics — you can directly *see*
collusion pairs, free-riders, asymmetric relationships, and dominant members.

**Foundation paper:** Fruchterman, T.M.J. and Reingold, E.M. "Graph drawing by
force-directed placement." *Software: Practice and Experience*,
21(11):1129–1164, 1991.
[doi:10.1002/spe.4380211102](https://doi.org/10.1002/spe.4380211102).

---

## Theoretical Background

### The Fruchterman–Reingold Algorithm

The layout algorithm models the graph as a **physical system**:

- **Every node** = electrically charged particle → **repels** all other nodes
- **Every edge** = spring connecting two nodes → **attracts** them
- **Edge weight** (peer score) = spring stiffness → high scores pull harder

The algorithm iterates a simulation:

1. **Repulsive forces:** Every pair of nodes pushes each other apart.
   Force is proportional to 1/d² (inverse square of distance), like
   electrostatic repulsion.

   ```
   f_repulsive(u, v) = -k² / d(u, v)
   ```

   where k = optimal distance between nodes (derived from graph area / node count).

2. **Attractive forces:** Connected nodes pull each other together.
   Force is proportional to d²/k (spring force), scaled by edge weight.

   ```
   f_attractive(u, v) = d(u, v)² / k × weight(u, v)
   ```

3. **Temperature cooling:** Early iterations allow large movements (explore the
   space), later iterations make small adjustments (converge to equilibrium).
   This is analogous to simulated annealing.

4. **Equilibrium:** After enough iterations, forces balance and nodes settle
   into stable positions.

### What the Layout Means for Peer Scores

```
  High mutual scores        Low/no scores          Asymmetric scores
  (strong springs)          (no spring)            (one-way spring)

    A ←══════→ B            A           B          A ════════→ B
    (close together)        (far apart)            (A pulled toward B,
                                                    B not pulled back)
```

**Important caveat:** With only 5–8 nodes, spatial position carries less
information than in large graphs. The visual encodings on nodes and edges
(size, colour, thickness) carry MORE information than layout position.

---

## Visual Encoding Scheme

### Nodes (Students)

| Attribute | Encoding | Meaning |
|---|---|---|
| **Size** | Proportional to total score received (weighted in-degree) | Big node = highly valued by team |
| **Colour** | Mapped to IWF score, or Girvan–Newman community | Shows contribution level or sub-group |
| **Label** | Student name | Identification |
| **Hover text** | Name, total given, total received, IWF | Detailed stats on interaction |

### Edges (Scores)

| Attribute | Encoding | Meaning |
|---|---|---|
| **Thickness** | Proportional to score magnitude | Thick = high score |
| **Colour** | Red → Yellow → Green gradient | Low → Medium → High score |
| **Arrow direction** | Points from giver to recipient | Who scored whom |
| **Opacity** | Lower for low scores | De-emphasise weak connections |
| **Hover text** | "Alice → Bob: 15 points" | Exact score on interaction |

---

## Reading the Graph — Pattern Recognition

### Collusion / Mutual High-Raters

```
         ╔═══════════╗
    A ◄══╣  thick,    ╠══▶ B
         ║  green,    ║
         ║  both ways ║
         ╚═══════════╝

Two nodes very close together with thick bidirectional green arrows.
Both gave each other high scores.
```

**Could mean:** Genuine strong collaboration, OR score inflation pact.
Cross-reference with their scores to the rest of the team — if they
rate everyone else low but each other high, collusion is more likely.

### Free-Rider / Excluded Member

```
    A ──── B ──── C         D (far away, small node)
     \    / \    /           ╱
      \  /   \  /       thin╱red arrows
       \/     \/          ╱
        E                ╱
                        ╱
```

One node far from the cluster, small (low scores received), with thin/red
incoming arrows. The team doesn't value this student's contribution.

### Asymmetric Relationship

```
    A ════thick green═══════▶ B
    A ◄────thin red────────── B
```

A rates B very highly, but B doesn't reciprocate. Could indicate:
- A recognises B's technical contribution but B doesn't value A's
- Power imbalance
- One-sided effort recognition

### Cohesive / Egalitarian Team

```
        A
       ╱ ╲
      ╱   ╲     (all nodes roughly equidistant,
     B─────C     similar-sized, moderate green edges)
      ╲   ╱
       ╲ ╱
        D
```

All nodes similar size, roughly equidistant, moderate-thickness green edges.
Everyone rates everyone similarly. Low variance, high reciprocity.

### Dominant / Star Member

```
         B
         │
    thick│green
         ▼
    C ──▶ A ◀── D        (A = large node in centre,
         ▲               thick incoming arrows from all)
         │
         E
```

One large node at the centre with thick incoming arrows from all directions.
This student is the acknowledged leader or top contributor.

---

## Constructing the Graph from ScoreMatrix

The `ScoreMatrix` stores `matrix[i][j]` = score giver j assigned to recipient i.
To build the NetworkX graph:

```python
import networkx as nx
import numpy as np

def build_team_graph(score_matrix: ScoreMatrix) -> nx.DiGraph:
    """Build a directed weighted graph from a ScoreMatrix.

    Edge j → i with weight = matrix[i][j] (giver j scored recipient i).
    Self-scores (diagonal) are excluded.
    NaN values (non-submitters) are excluded.
    """
    G = nx.DiGraph()
    students = score_matrix.students
    matrix = score_matrix.matrix

    for s in students:
        G.add_node(s.index, name=s.name, email=s.email)

    for i in range(len(students)):      # recipient
        for j in range(len(students)):  # giver
            if i != j and not np.isnan(matrix[i][j]):
                G.add_edge(j, i, weight=float(matrix[i][j]))

    return G
```

**Convention:** Edge direction is **giver → recipient** (j → i), matching the
natural reading "j scored i". The weight is the score magnitude.

---

## Layout Computation

```python
pos = nx.spring_layout(
    G,
    weight="weight",    # use score as spring stiffness
    seed=42,            # reproducible layout
    k=None,             # auto-compute optimal distance
    iterations=50,      # default is 50; increase for more stability
)
# Returns: {node_id: np.array([x, y]), ...}
```

**Parameters:**
- `weight="weight"`: Higher scores → stronger springs → closer nodes.
- `seed=42`: Fix the random seed so the same data always produces the same layout.
- `k`: Optimal distance between nodes. `None` = auto-calculated as
  `1/√n` where n = number of nodes. Can be tuned if nodes overlap.
- `iterations`: More iterations = more stable layout, but diminishing returns
  past ~100 for small graphs.

---

## Rendering with Plotly

Plotly renders the graph as interactive HTML — hoverable, zoomable, exportable
as PNG for papers.

The rendering involves two types of traces:

1. **Edge traces** (`go.Scatter` with `mode='lines'`): One trace per edge for
   individual styling (thickness, colour per score).

2. **Node trace** (`go.Scatter` with `mode='markers+text'`): All nodes in one
   trace, with size/colour arrays for encoding.

The layout hides axes (no grid, ticks, or labels) since positions are abstract
— only relative distances matter.

---

## Limitations and Mitigations

| Limitation | Mitigation |
|---|---|
| Non-deterministic layout (random initialisation) | Fix `seed` parameter for reproducibility |
| 5–8 nodes may look trivial spatially | Rely on edge/node visual encoding more than position |
| Directed edges need arrows | Plotly doesn't natively support arrows on `go.Scatter` lines; use annotation arrows or `matplotlib` fallback |
| Overlapping edges in dense graphs | Adjust `k` parameter or curve edges |
| Score scale varies by question | Normalise scores before building graph, or use relative (rank-based) encoding |

---

## References

1. Fruchterman, T.M.J. and Reingold, E.M. "Graph drawing by force-directed
   placement." *Software: Practice and Experience*, 21(11):1129–1164, 1991.
   [doi:10.1002/spe.4380211102](https://doi.org/10.1002/spe.4380211102).
   — The force-directed layout algorithm used by `nx.spring_layout`.

2. Eades, P. "A heuristic for graph drawing." *Congressus Numerantium*,
   42:149–160, 1984.
   — Early spring-based graph drawing; Fruchterman–Reingold builds on this.

3. Kobourov, S.G. "Spring Embedders and Force Directed Graph Drawing Algorithms."
   *arXiv:1201.3011*, 2012.
   [arXiv:1201.3011](https://arxiv.org/abs/1201.3011).
   — Comprehensive survey of force-directed methods, trade-offs, and extensions.

4. Hagberg, A.A., Schult, D.A. and Swart, P.J. "Exploring network structure,
   dynamics, and function using NetworkX." *SciPy 2008*, pp. 11–15.
   [https://conference.scipy.org/proceedings/scipy2008/paper_2/](https://conference.scipy.org/proceedings/scipy2008/paper_2/).

### Library Documentation

- NetworkX `spring_layout`: [https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html)
- Plotly Network Graphs: [https://plotly.com/python/network-graphs/](https://plotly.com/python/network-graphs/)
- Plotly `go.Scatter`: [https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html)
