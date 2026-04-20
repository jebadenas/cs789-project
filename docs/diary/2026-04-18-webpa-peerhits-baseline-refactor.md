# WebPA, PeerHITS & Baseline Self-Score Refactor

**Date:** 18 April 2026  
**Issues:** #4, #6  
**PRs:** #18 (baseline refactor), #19→#22 (WebPA), #20→#23 (PeerHITS)

## What I Did

Implemented the remaining two IWF models and refactored the baseline — completing the full model suite.

### Baseline Self-Score Exclusion (PR #18)

Refactored the baseline model to exclude self-scores from the IWF calculation:
- Set the diagonal of the score matrix to NaN before computing means
- Aligns with the Kaufman et al. formula where IWF should reflect **peer** assessment, not self-assessment
- Updated 39 lines of test expectations

This was a design decision I went back and forth on. The COMPSCI 399 system includes self-scores in their average, but the literature (Kaufman et al.) argues against it. I went with the literature — the point of peer assessment is to capture how teammates perceive your contribution, not how you perceive your own.

### WebPA Model (Issue #4, PR #22)

Implemented the Willey & Gardner (2007) WebPA normalisation model:
- PA factor = (scores received by student) / (mean scores received across team)
- Self-scores **included** per the original paper
- Output scaled to team mean of 10.0 for cross-model comparability
- Grade neutrality invariant verified: mean IWF always equals 10.0
- **Bug found during code review:** division by zero when all scores are zero — added `ValueError` guard

### PeerHITS Model (Issue #6, PR #23)

Implemented a HITS-inspired dual-score iterative model:
- **Authority score:** how well a student contributes (the IWF output)
- **Hub score:** how well a student assesses peers (stored in `ModelResult.hub_vector`)
- Self-scores excluded
- L2-normalised per iteration, convergence at epsilon=1e-6
- **Bug found during code review:** convergence metric used L2 norm but `ModelResult` field is named `final_l1_norm` — changed to actual L1 norm (`np.sum(np.abs(...))`)

## Stacked PR Complication

These three features were developed as stacked branches: baseline → WebPA → PeerHITS. When merging PR #18 (baseline), GitHub auto-closed PRs #19 and #20 because their base branches were deleted. Had to:
1. Rebase each branch onto main
2. Create new PRs (#22 for WebPA, #23 for PeerHITS)
3. Re-review and merge

Lesson learned: stacked PRs in GitHub are fragile. Next time, either merge bottom-up more carefully or use independent branches.

## Testing

- WebPA: 6 tests (hand-computed, uniform, grade neutrality, non-submitter)
- PeerHITS: 8 tests (convergence, dual vectors, hub quality, uniform)
- All 48 tests passing after merge

## Model Suite Complete

With all four models merged, the engine now supports:

| Model | Type | Self-Scores | Key Property |
|-------|------|-------------|-------------|
| Baseline | Non-iterative | Excluded | Simple, transparent |
| WebPA | Non-iterative | Included | Grade-neutral by construction |
| PeerRank | Iterative | Included | Credibility-weighted consensus |
| PeerHITS | Iterative | Excluded | Separate contribution + assessment scores |
