# Team Dynamics Classification — Similarity Metrics Research

**Status:** Research note for RQ3 (team-dynamics classification, Issue #11)
**Date:** 2026-05-04 (pre 5-May supervisor meeting)
**Question:** How should we classify each team's peer-rating matrix into a team-dynamic archetype (Cohesive / Collusive / Free-rider / Dominant member / Conflict)?

---

## Problem framing

Two approaches were proposed in the 28 April supervisor discussion:

- **Approach A — Graph-to-graph similarity.** Map each team to a graph, synthesise reference graphs representing each team-dynamic archetype, classify by graph-similarity to the closest archetype.
- **Approach B — Vector-to-vector similarity.** Map each team to a feature vector of graph metrics, synthesise reference vectors per archetype, classify by vector-similarity to the closest archetype.

Both share the same underlying logic: *define archetypes → measure similarity to each → threshold-classify.* The substantive choice is what space the comparison lives in (graph space vs. feature-vector space) and which similarity metric to use.

The data: 136 score matrices across 35 teams of 5–8 students each. Matrices are dense, weighted, directed, with NaN columns for non-submitters.

---

## Approach A — Graph-to-graph similarity

### Constraints from the literature

| Family | Examples | What it captures | Why it struggles on our data |
|---|---|---|---|
| Spectral distances | Adjacency / Laplacian / Normalized-Laplacian eigenvalue distance | Community structure (low-k eigenvalues); local features (high-k) | Eigenvalues of 5–8-node weighted graphs are noisy; co-spectral non-isomorphic graphs collapse to zero distance |
| Matrix distances | Graph Edit Distance (GED), resistance-perturbation, **DeltaCon** | Edge changes; node-affinity diffusion | All require **node correspondence**, which we don't have between different teams |
| Feature-based | **NetSimile**, signature vectors | Aggregated node/egonet features | Actually a hybrid — graph→vector→vector similarity (so it really sits in Approach B) |
| Subgraph-counting | **Triad census**, motif fingerprints | Frequencies of 16 directed triad classes | Discrete and noisy at n=5–8, but principled and interpretable |

### Key references

- **Wills & Meyer (2020),** *Metrics for Graph Comparison: A Practitioner's Guide,* PLOS One — the canonical benchmark, but explicitly restricts to *"unlabelled and undirected graphs, with no self-loops"*. Adaptations needed.
- **Sanfeliu & Fu (1983)** introduced GED. **Gao et al. (2010)** survey GED. On dense weighted graphs GED collapses to a sum of weight differences and loses relational signal.
- **Koutra, Vogelstein & Faloutsos (2013/2016),** *DeltaCon* — uses Fast Belief Propagation to compare node-affinity matrices. Sensitive to local + global structure but **assumes node correspondence** (ok within a team across time, not across teams).
- **Kriege, Johansson & Morris (2020),** *A Survey on Graph Kernels* — Weisfeiler-Lehman, random-walk, shortest-path kernels. All need either node labels or sparse structure to discriminate; they degenerate on dense 6-node graphs.
- **Faust (2007),** *Comparing Social Networks: Size, Density and Local Structure* — triad census is the standard fingerprint for small directed networks. The 16 directed triad classes (003, 012, 102, 021D, 021U, 021C, 111D, 111U, 030T, 030C, 201, 120D, 120U, 120C, 210, 300) map naturally to our archetypes:
  - Collusion → many 030T / 300 (mutually reciprocating)
  - Dominant member → 021U / 021D into one node
  - Conflict → 021C and 111D (asymmetric chains)

### Verdict

Graph-to-graph similarity is theoretically interesting but works against us: literature is built for big sparse graphs; ours are small and dense; no node correspondence between teams. The one component worth keeping is **triad-census fingerprints** — but those collapse into a feature vector, which lands us in Approach B.

---

## Approach B — Vector-to-vector similarity

This route has direct precedent in CATME (Ohland et al. 2012) and the broader peer-evaluation literature, and lines up with the metrics already itemised in the 28 April agenda.

### Step 1 — Feature vector per team

Per-team graph metrics (some already in the 28 April agenda):

| Metric | What it detects |
|---|---|
| Reciprocity | Symmetric vs. asymmetric scoring |
| Gini coefficient (in-degree) | Score concentration → free-rider / dominant member |
| Score variance per rater | Differentiating raters vs. flat / strategic raters |
| Asymmetry (Frobenius ‖A − Aᵀ‖) | One-directional imbalances (conflict signal) |
| Clustering coefficient | Tight sub-group mutual inflation (collusion) |
| Degree assortativity | Whether high-rated students preferentially rate each other |
| Triad-census proportions (16 classes) | Local interaction signatures |

This is what **NetSimile (Berlingerio, Koutra, Eliassi-Rad & Faloutsos 2012, arXiv:1209.2684)** formalises: extract node-level features, aggregate via mean / median / std-dev / skewness / kurtosis to a fixed-length signature vector. *Size-invariant by construction.* At n=6, 5-moment aggregation is overkill — mean and std are likely enough.

### Step 2 — Archetype vectors

Two complementary options:

**(a) Synthesised archetypes (CATME-style).** Hand-construct prototype score matrices for each archetype, compute the same feature vector. Interpretable; ties directly to the 28 April agenda's threshold-based classification.

**(b) Learned archetypes — Archetypal Analysis (Cutler & Breiman 1994, *Technometrics* 36(4); survey: Mair & Alfons 2025, arXiv:2504.12392).** Finds the convex hull of the data and identifies *extreme exemplars* (archetypes) at its vertices. Each real team is then expressed as a convex combination ("70% Cohesive, 30% Free-rider"). Differs from k-means: clustering uses *averages* as prototypes; AA uses *extremes* as frontiers. Since our archetypes are by definition extreme behaviours (collusion = uniform high; conflict = max asymmetry), AA is the principled way to derive them rather than guess them.

The two approaches can validate each other: do hand-synthesised archetypes land near the data-driven AA archetypes? If yes, our priors are confirmed. If no, that mismatch is itself a finding.

### Step 3 — Similarity metric

Backed by a 70-year literature in psychology (Cronbach & Gleser 1953, *Assessing similarity between profiles*, Psychological Bulletin 50(6)):

| Family | Examples | Behaviour |
|---|---|---|
| Distance-based | Euclidean, Manhattan, Chebyshev | Treats each metric independently; sensitive to scale; over-counts correlated features |
| Correlation-based | Pearson Q-correlation, cosine | Captures profile *shape* but ignores elevation/level — wrong for us when magnitude itself matters |
| Covariance-aware | **Mahalanobis** | Accounts for correlations between metrics; chi-squared distributed → principled threshold |

A modern comparison — **van Dam et al. (2024), *A Comparison of Measures for Assessing Profile Similarity in Dyads*, Psychologica Belgica** — finds Pearson Q-correlation "inconsistent and very sensitive to varying data characteristics."

**Mahalanobis distance (Mahalanobis 1936; modern: Ghosh et al. 2024, arXiv:2402.08283)** is the right pick for our case:

- Our graph metrics are correlated (reciprocity ↔ clustering; Gini ↔ degree variance). Euclidean over-counts these.
- Mahalanobis whitens the covariance structure.
- Chi-squared distributed → "similarity threshold" gets a probabilistic interpretation rather than an arbitrary cutoff.
- Cosine similarity is wrong here: it's scale-invariant (great for text embeddings, bad when "magnitude of asymmetry" is itself meaningful).

### Verdict

Approach B is more defensible and aligns with how CATME and similar frameworks already classify teams. Each step has academic backing: Cronbach 1953 (profile similarity), Mahalanobis 1936 (distance metric), Cutler & Breiman 1994 (archetypes from data), Faust 2007 (triad census), Ohland 2012 (CATME teamwork classification).

---

## Open questions for the 5 May meeting

- **Synthesised vs. data-driven archetypes:** keep both for cross-validation, or commit to one?
- **Threshold strategy:** chi-squared p-value (Mahalanobis-native), percentile-based across the 136 matrices, or absolute thresholds from literature?
- **Multi-label teams:** Cutler-Breiman AA naturally yields convex combinations ("70% / 30%"). Do we keep that as a soft labelling, or pick the dominant archetype?
- **Sequencing vs. attack simulation (#9):** Does this work go before or alongside #9? Argument for first: labelled real teams contextualise synthetic-attack results.

---

## Source list

- Wills & Meyer (2020), *Metrics for Graph Comparison: A Practitioner's Guide,* PLOS One. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0228728
- Koutra, Vogelstein & Faloutsos (2013), *DeltaCon: A Principled Massive-Graph Similarity Function,* arXiv:1304.4657. https://arxiv.org/abs/1304.4657
- Berlingerio, Koutra, Eliassi-Rad & Faloutsos (2012), *NetSimile: A Scalable Approach to Size-Independent Network Similarity,* arXiv:1209.2684. https://arxiv.org/abs/1209.2684
- Kriege, Johansson & Morris (2020), *A Survey on Graph Kernels,* Applied Network Science. https://link.springer.com/article/10.1007/s41109-019-0195-3
- Borgwardt et al. (2020), *Graph Kernels: State-of-the-Art and Future Challenges,* arXiv:2011.03854. https://arxiv.org/abs/2011.03854
- Cutler & Breiman (1994), *Archetypal Analysis,* Technometrics 36(4). https://www.tandfonline.com/doi/abs/10.1080/00401706.1994.10485840
- Mair & Alfons (2025), *A Survey on Archetypal Analysis,* arXiv:2504.12392. https://arxiv.org/abs/2504.12392
- Cronbach & Gleser (1953), *Assessing similarity between profiles,* Psychological Bulletin 50(6).
- van Dam et al. (2024), *A Comparison of Measures for Assessing Profile Similarity in Dyads,* Psychologica Belgica. https://psychologicabelgica.com/articles/10.5334/pb.1297
- Ghosh et al. (2024), *Classification Using Global and Local Mahalanobis Distances,* arXiv:2402.08283. https://arxiv.org/abs/2402.08283
- Mahalanobis (1936), *On the generalized distance in statistics,* Proc. National Institute of Sciences of India 2(1).
- Sanfeliu & Fu (1983), *A distance measure between attributed relational graphs for pattern recognition,* IEEE TSMC.
- Faust (2007), *Comparing Social Networks: Size, Density and Local Structure,* Metodološki zvezki 4(2).
- Holland & Leinhardt (1976), *Local structure in social networks,* Sociological Methodology 7.
- Felzer et al. (2021), *Dyads, triads, and tetrads: a multivariate simulation approach to uncovering network motifs in social graphs,* Applied Network Science. https://link.springer.com/article/10.1007/s41109-021-00403-5
- Ohland et al. (2012), *The Comprehensive Assessment of Team Member Effectiveness (CATME),* Academy of Management Learning & Education 11. https://peer.asee.org/the-comprehensive-assessment-of-team-member-effectiveness-a-new-peer-evaluation-instrument.pdf
