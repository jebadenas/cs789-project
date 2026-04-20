# Baseline IWF Model & TDD Approach

**Date:** 5 April 2026  
**Issue:** #3  
**PR:** #14 (merged same day)

## What I Did

Implemented the first IWF model — the simple average baseline — and established the testing patterns used by all subsequent models.

### ModelResult Type (`src/models/types.py`)
Created the shared Pydantic return type for all models:
- `model_name`: identifies which algorithm produced the result
- `students`: list of student names in index order
- `iwf_vector`: numpy array of Individual Weighting Factors
- `converged`, `iterations`, `final_l1_norm`: convergence metadata (for iterative models)
- `hub_vector`: optional secondary score vector (for PeerHITS)

### Baseline Model (`src/models/baseline.py`)
- Computes IWF as `np.nanmean(matrix[i, :])` — the mean of all scores received by student i
- NaN-aware: non-submitter scores (NaN columns) are automatically excluded from the mean
- At this point, self-scores were **included** in the average (changed later on Apr 18)

### Parser Fix
The parser was previously removing non-submitters entirely from the matrix. Changed it to keep them in the N×N matrix with NaN columns — this preserves team size and allows models to decide how to handle non-submitters.

### TDD Approach
Initially wrote comprehensive tests all at once, then refactored into 5 focused TDD-style vertical slices:
1. **Tracer bullet** — 3-person team returns correct IWF and model name
2. **Self-scores included** — diagonal counted in average
3. **Non-submitter handling** — NaN columns excluded, recipient still gets IWF
4. **Uniform matrix** — all 10s produces equal IWFs
5. **Dataset validation** — Team 11 ExquisiTech matches actual CSV Average Points

## Reflections

The TDD rewrite was worth it. The first batch of tests was correct but monolithic — hard to tell what each test was actually verifying. The vertical slice approach makes each test's purpose obvious and serves as documentation.

The non-submitter parser fix was an important architectural decision. Removing non-submitters changes the matrix dimensions and loses information. Keeping them as NaN columns means every model sees the same N×N matrix and handles missing data in its own way.

## Stats
- 6 files changed, 351 insertions
- 26 tests passing (5 baseline + 21 parser)
