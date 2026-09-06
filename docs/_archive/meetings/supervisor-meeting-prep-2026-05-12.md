# Supervisor Meeting Prep — Team Dynamics Classification

**Date:** 2026-05-12

---

## What to Actually Say — Script

### Opening (1 min)

> "I've been working on the team dynamics classification pipeline — the part of RQ3 where we try to label each team's peer-rating behaviour. I want to walk you through what I've built, show you the results, and then get your input on a problem I've hit."

---

### Explaining the method (3–4 min)

> "The core challenge is that teams have different sizes — 4 to 8 students — so you can't directly compare their rating matrices. What I do is compress each matrix into a fixed 25-number fingerprint, regardless of team size."

> "The first 9 numbers are behavioural metrics — things like: do people tend to rate each other similarly? Is one person receiving much less than everyone else? Are ratings one-sided or symmetric?"

> "The remaining 16 come from something called a triad census. I convert the matrix into a directed graph — there's an arrow from A to B if A gave B above-average scores — then I look at every group of 3 students and classify the arrow pattern between them. There are 16 possible patterns. This captures local structure that the global metrics miss."

_If she asks why triads:_

> "Two teams can have identical global stats but totally different local structure — one has mutual buddy pairs everywhere, the other has universal appreciation. The triads distinguish those."

> "Once I have the 25 numbers, I standardise them so no feature dominates just because of its units. Then I classify each team by measuring how close it is to five hand-crafted prototype matrices — one per dynamic label. The closest prototype wins. I use Mahalanobis distance rather than plain Euclidean because several features are correlated, and Mahalanobis accounts for that so nothing gets double-counted."

---

### Showing the results (1–2 min)

> "Across 105 teams from 2023 and 2024, the results are: 102 Cohesive, 2 Dominant, 1 Free-rider, 0 Collusive, 0 Conflict."

> "The Dominant teams have noticeably higher cross-model disagreement — Δ of 1.73 versus 0.55 for Cohesive — which supports the hypothesis that unusual team dynamics affect how the scoring models disagree."

> "But the 102 out of 105 is the problem I want to talk about."

---

### Raising the archetype problem (3–4 min)

> "I think 102 Cohesive is telling me my prototype matrices are too extreme. They're textbook-perfect examples of each dynamic — so extreme that real teams barely resemble any of them except Cohesive, which is the mildest one. Everything defaults to it."

> "I see three ways to address this and I'd like your input."

> "Option one: soften the prototypes — make the free-rider a bit less extreme, the conflict factions a bit less hostile. The problem is it's arbitrary — I'd be tuning by hand until the results look right, which is hard to justify."

> "Option two: let the data define the archetypes. I actually already ran something called Archetypal Analysis — an algorithm that finds the extreme points of the real data rather than using my hand-crafted ones. The issue is that when I ask for 5 archetypes it's quite unstable — reproducibility of 0.50. But when I ask for just 2, it's very stable — 0.92. So the data seems to robustly support a binary split: Typical versus Anomalous. I wonder if that's actually the honest finding — most teams look the same, a small number are genuinely unusual."

> "Option three: keep the current archetypes but add a distance threshold. If a team is too far from all five reference points, label it Unclassified rather than forcing it into the nearest one. That at least makes the classifier honest about what it can't detect."

> "My instinct is that Option 2 is the most intellectually honest — the k=2 binary finding might be more defensible than a 5-label taxonomy the data doesn't really support. But I wanted your view before committing to a direction."

---

### Close (1 min)

> "The other thing I want to flag: one feature — assortativity — turns out to be always zero for these matrices, so it's just noise. I'll drop it regardless."

> "And I'm thinking non-submitters should be a separate flag rather than folded into the dynamic label — the classifier doesn't handle them well."

> "So the main thing I need from today is: which direction on the archetypes, and whether you think a binary Typical/Anomalous framing is worth pursuing."

---

## The Method (what to explain)

### Big picture

We classify each team's peer-rating matrix into one of five dynamic labels — **Cohesive, Collusive, Free-rider, Dominant, Conflict** — using a four-step pipeline.

### Step 1 — Input: the score matrix

Each team produces a matrix where every student distributes 60 points across their teammates. Rows = recipients, columns = givers. That's the raw input.

### Step 2 — Feature extraction (25 numbers)

Teams vary in size (4–8 students), so you can't compare matrices directly. Each matrix is compressed into a fixed 25-number fingerprint:

- **9 behavioural metrics** — reciprocity (do people rate each other similarly?), Gini inequality (is one person getting much less?), asymmetry (are ratings one-sided?), clustering, rater variance, non-submitter fraction, self-score share.
- **16 triad census proportions** — binarize the matrix into a directed graph (arrow exists if score is above that person's own average), then count every 3-person subgraph pattern across all possible groups of 3 students. This captures local structure that global metrics miss — two teams can have identical reciprocity but one has mutual buddy pairs (Collusive) while the other has universal mutual appreciation (Cohesive).

### Step 3 — Standardisation

The 25 features are on different scales. We standardise each to a z-score ("how many standard deviations from average across all teams") so no feature dominates just because of its units. The same scaler is applied to both real teams and archetypes so they live in the same space.

### Step 4 — Classification by Mahalanobis distance

We hand-craft 5 prototype matrices — one per label — designed to be textbook examples of each dynamic. These go through the same pipeline to become 5 reference points in the same 25-dimensional space.

Each real team is assigned the label of whichever prototype it's **closest to**, using **Mahalanobis distance** rather than plain Euclidean distance. Mahalanobis accounts for correlations between features so correlated features aren't double-counted.

Output: a hard label + a confidence score (softmax over the 5 distances).

---

## Key Results

| Label      | Count | Mean Δ |
| ---------- | ----- | ------ |
| Cohesive   | 102   | 0.55   |
| Dominant   | 2     | 1.73   |
| Free-rider | 1     | —      |
| Collusive  | 0     | —      |
| Conflict   | 0     | —      |

- 102/105 teams land as Cohesive — the synthesised archetypes are quite extreme, so only genuinely anomalous teams escape.
- Dominant teams have higher Δ (cross-model disagreement), supporting the hypothesis that unusual dynamics affect how scoring models disagree.
- Team 6 (Caffeine Overload) has the highest Δ (7.06) but is classified Cohesive — has a non-submitter present which the classifier doesn't capture well.
- Team 16 (PeerHITS amplification case) classified Cohesive with Δ = 3.78.

---

## Anticipated Questions

**"Why did you choose synthesised archetypes rather than learning them from data?"**

> The dataset (105 teams) is too small to reliably learn cluster centroids from scratch. Hand-crafted prototypes give us interpretable, guaranteed-representative examples of each dynamic without needing labelled training data. The tradeoff is that the prototypes may be more extreme than any real team.

**"102 out of 105 teams are Cohesive — is the classifier actually doing anything useful?"**

> It confirms that most teams in this dataset do behave cohesively, which is plausible for a university course. But it also suggests the archetype boundaries may be too extreme — a real team would need very unusual scoring behaviour to escape Cohesive. This is the main limitation to address.

**"Why Mahalanobis and not something simpler like Euclidean distance or cosine similarity?"**

> Several of our 25 features are correlated (e.g. high clustering tends to co-occur with high triad_102). Euclidean distance would double-count that signal. Mahalanobis stretches the feature space to account for those correlations, so each dimension contributes independently.

**"Why Ledoit-Wolf shrinkage?"**

> Estimating a 25×25 covariance matrix from 105 data points is noisy. Ledoit-Wolf regularises the estimate by blending it towards a scaled identity matrix, making the precision matrix stable and invertible.

**"What is assortativity and why is it in the feature set?"**

> Degree assortativity measures whether high-scoring people tend to rate other high-scoring people. In practice it's always ~0 for these dense peer-rating matrices, making it uninformative noise. It should probably be dropped.

**"Have you considered a data-driven approach to archetypes?"**

> Yes — we also ran Archetypal Analysis (AA), which learns extreme points from the data itself (Frank-Wolfe algorithm). At k=2 it's very stable (reproducibility 0.92); at k=5 (chosen by RSS elbow) stability drops to 0.50. The k=2 finding suggests the data may only robustly support a binary Typical/Anomalous split rather than our 5-label taxonomy.

**"What does Δ (delta) mean?"**

> Delta is the cross-model disagreement metric — how much the different scoring models (WebPA, PeerRank, PeerHITS etc.) disagree on a team's rankings. High Δ means the models give very different answers for that team.

---

## Open Questions / Things to Raise with Anna

1. **Are the synthesised archetypes too extreme?** Conflict archetype sits ~58 Mahalanobis units from the data centre; Cohesive sits ~8. This likely explains why almost everything is labelled Cohesive.

2. **Should assortativity be dropped?** It's always ~0 for peer-rating matrices — it's adding noise, not signal.

3. **Should we report k=2 AA as the primary finding?** k=2 (Typical/Anomalous) is far more stable than k=5. It may be more honest to say the data supports a binary split.

4. **Should "non-submitter present" be a separate flag?** The classifier doesn't handle this well (e.g. Team 6 is Cohesive but has a non-submitter driving a high Δ). A binary flag independent of the dynamic label might be cleaner.

5. **How extreme should the archetypes be?** If Anna thinks the current prototypes are too idealized, options are: (a) soften them, (b) use AA-derived archetypes, (c) use a threshold on distance rather than nearest-neighbour.

---

## Next Steps

- [ ] Drop `assortativity` from the feature vector (always zero, confirmed noise)
- [ ] Re-run classification without assortativity and check if results change meaningfully
- [ ] Revisit archetype extremity — consider softening the Conflict and Free-rider prototypes
- [ ] Add a `non_submitter_flag` field to ClassificationResult, independent of the dynamic label
- [ ] Decide with Anna whether to report k=2 or k=5 AA as the primary finding
- [ ] Write up the classification method section for the thesis

---

## The Archetype Problem — What to Say

The main issue is that 102/105 teams land as Cohesive. This almost certainly means the synthesised archetypes are too extreme — they represent textbook-perfect cases that no real team ever looks like, so everything defaults to the nearest one (Cohesive).

There are three options. I want Anna's input on which to pursue.

---

**Option 1 — Soften the synthesised archetypes**

> "The prototype matrices I designed are quite extreme — for example the free-rider keeps 52 of their 60 points. I could redesign them to be less extreme so they sit closer to where real teams actually are, which would let more teams escape the Cohesive bucket."

_The problem with this:_ it's arbitrary tuning. I'd be adjusting numbers by hand until the results look right, which is hard to justify methodologically.

---

**Option 2 — Let the data define the archetypes (Archetypal Analysis)**

> "Instead of hand-crafting the reference points, I ran an algorithm called Archetypal Analysis that finds the extreme points of the actual data — so the archetypes are grounded in what real teams look like, not what I imagined."

> "The issue is stability. When I ask for 5 archetypes, the algorithm gives different answers each run — reproducibility is only 0.50. But when I ask for just 2, it's very stable (0.92). So the data seems to support a binary split — Typical vs Anomalous — more than a 5-label taxonomy."

> "That might actually be the honest finding: most teams are cohesive and indistinguishable, and a small number are genuinely anomalous. The 5 labels might be more than the data can support."

---

**Option 3 — Add a distance threshold (short-term fix)**

> "A simpler fix: keep the current archetypes but add a rule — if a team is too far from all five reference points, label it 'Unclassified' rather than forcing it into whichever archetype happens to be closest. Right now a team that looks nothing like any archetype still gets called Cohesive by default. A threshold makes the classifier honest about what it can't detect."

---

**My instinct going into the meeting:**

Option 3 is the quickest fix. But Option 2 is the most intellectually honest result — the k=2 Archetypal Analysis finding (Typical/Anomalous, stability 0.92) is a real finding worth reporting, not a failure. I want Anna's view on whether to reframe the contribution around that.
