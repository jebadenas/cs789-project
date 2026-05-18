# Team Dynamics Classification — Technical Documentation

This directory documents the full pipeline for classifying peer-assessment score matrices into team dynamic labels.

## Pipeline Overview

```
Score Matrix  →  Feature Extraction  →  Standardisation  →  Mahalanobis Classification
(parsing/)        (features.py)          (sklearn)            (classifier.py)
```

## Files

| File | Contents |
|---|---|
| [step-1-score-matrix.md](step-1-score-matrix.md) | The raw input: what a ScoreMatrix is and how it's structured |
| [step-2-feature-extraction.md](step-2-feature-extraction.md) | How each of the 25 features is computed from a score matrix |
| [step-3-standardisation.md](step-3-standardisation.md) | Why and how features are standardised before comparison |
| [step-4-archetypes.md](step-4-archetypes.md) | How the 5 hand-crafted prototype matrices are defined |
| [step-5-mahalanobis.md](step-5-mahalanobis.md) | Mahalanobis distance, the precision matrix, and classification |
| [step-6-archetypal-analysis.md](step-6-archetypal-analysis.md) | Optional: data-driven archetype discovery via Frank-Wolfe AA |

## Findings & Decision Records

| File | Contents |
|---|---|
| [findings-2026-05-17.md](findings-2026-05-17.md) | Pivot from 5-prototype classification to continuous atypicality scoring; data-quality finding (35 teams → 18 usable); open questions for next session |

> Note: the 5-prototype classification (step-4, step-5) is retained as a
> secondary descriptive lens only. The primary RQ3 measure is now the
> continuous atypicality score — see the findings record above.

## Team Dynamic Labels

| Label | Signature |
|---|---|
| **Cohesive** | Near-uniform reciprocal scoring — everyone rates fairly |
| **Collusive** | Buddy pairs mutually inflate each other's scores |
| **Free-rider** | One student receives near-zero from all peers |
| **Dominant** | One student receives disproportionately high scores from everyone |
| **Conflict** | Factions — group A inflates group A and penalises group B, and vice versa |
