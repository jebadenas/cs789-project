# Non-Submitter Amplification in Iterative Models

**Date:** 2026-04-20  
**Related issue:** [#24](https://github.com/jebadenas/cs789-project/issues/24)

## Discovery

While reviewing the force-layout graph for **Team 8 - Sentry** (Session 4, 2024), I noticed Robin Kunwar — a non-submitter — was displayed as a large green node despite all baseline IWFs being 10.0 across the team.

Investigating the raw score matrix revealed:
- All 5 submitters gave every teammate (including Robin) uniform scores of 10
- Robin's column was entirely NaN (non-submitter)
- Baseline and WebPA correctly returned 10.0 for all students
- **PeerRank inflated Robin to 12.631** and deflated everyone else to 9.474
- **PeerHITS inflated Robin to 12.0** and deflated everyone else to 9.6

## Analysis

The root cause is how iterative models handle NaN → 0 replacement for non-submitters:

1. Robin has zero credibility as a rater (no outgoing scores after NaN → 0)
2. Robin still receives full scores from 5 credible raters
3. Other students only receive credibility-weighted scores from 4 raters (Robin's are gone)
4. The iterative convergence amplifies this asymmetry
5. Scaling to team mean 10.0 further inflates Robin and deflates submitters

This means a student who **didn't even participate** in peer review gets a **higher IWF** than those who did — the opposite of fair.

## Implications for Research

- **RQ1 (manipulation resistance):** Strategic non-submission becomes a viable manipulation strategy when teammates give uniform scores. This is a vulnerability in both PeerRank (Walsh, 2014) and PeerHITS.
- **Baseline and WebPA are immune** because they don't use iterative credibility weighting.
- This finding strengthens the argument for composite model evaluation — no single model handles all edge cases.

## Next Steps

- Decide on a fix strategy (exclude, impute, or penalise non-submitters)
- Test fix across all sessions to check for unintended side effects
- Document as a key finding in the evaluation chapter
