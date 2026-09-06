# Force-Layout Graph Visualisation

**Date:** 19 April 2026  
**PR:** #21 (merged 20 April)

## What I Did

Built an interactive force-directed graph visualisation for exploring team peer-score dynamics.

### Graph Construction (`src/visualization/graph.py`)

- `build_team_graph()` converts a ScoreMatrix into a NetworkX DiGraph
- Edge convention: directed edge from giver j → recipient i, weight = `matrix[i][j]`
- Self-loops excluded (diagonal entries)
- NaN entries (non-submitters) excluded
- 53 lines, reusable by any visualisation that needs the graph structure

### Force Layout Rendering (`src/visualization/force_layout.py`)

- Fruchterman-Reingold spring layout algorithm via NetworkX
- **Node size** = weighted in-degree (total scores received) — larger nodes received more points
- **Node colour** = IWF value (if model results provided) or in-degree, using RdYlGn colour scale
- **Edge thickness** = proportional to raw score given
- **Edge colour** = RdYlGn gradient (red = low score, green = high score)
- **Midpoint arrow markers** to show edge direction
- Rich hover text on nodes (name, IWF, scores received) and edges (from → to, score)
- 273 lines of rendering code

### Visual Encoding Design

The visual encoding was designed to make team dynamics immediately apparent:
- **Balanced teams:** similar-sized nodes, all green, evenly distributed
- **Star performers:** one large green node pulling edges inward
- **Free riders:** small red node on the periphery with thin incoming edges
- **Collusion clusters:** subgroups with thick green edges between them, thin red edges to outsiders
- **Conflict pairs:** asymmetric red edges between specific students

## Research Documentation

Also committed 1,455 lines of research docs:
- `docs/team-dynamics-research.md` — analysis of graph clustering approaches for small teams (N=5-8). Key finding: classical community detection (Girvan-Newman, Louvain) doesn't work well at this scale; recommend graph metrics (reciprocity, clustering coefficient, betweenness centrality) instead.
- `docs/qualitative/girvan-newman.md` — detailed notes on Girvan-Newman algorithm applicability
- `docs/visualization/force-layout-graph.md` — technical documentation for the force layout
- `docs/visualization/radar-chart.md` — notes on radar chart alternative (not yet implemented)

## Testing

- 9 unit tests for graph construction (NaN handling, self-loops, edge direction, weights)
- 8 smoke tests for force layout rendering (figure creation, node/edge traces, colour mapping)
- All 17 new tests passing

## Reflections

The force-layout graph turned out to be more useful than I expected for qualitative analysis. Within seconds of viewing a team, you can spot:
- Whether the team is balanced or has outliers
- Whether scoring patterns suggest genuine peer assessment or collusion
- Whether non-submitters are affecting the picture

This led directly to the non-submitter amplification discovery the next day (see 2026-04-20 entry).
