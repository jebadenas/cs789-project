# Research Proposal Submission & CSV Parser Rewrite

**Date:** 3 April 2026  

## What I Did

### Research Proposal

Submitted the formal research proposal PDF (`Badenas_Jos_421180443_Research_Proposal.pdf`) to the repository. The proposal outlines:
- Comparing IWF algorithms (baseline, PeerRank, WebPA, PeerHITS) for peer assessment
- Four research questions: manipulation resistance (RQ1), grade neutrality (RQ2), red-flag identification (RQ3), qualitative sentiment (RQ4)
- Evaluation methodology using real COMPSCI 399 data

### CSV Parser Rewrite (Issue #2)

Completely rewrote the parser from the March 23 prototype. Major changes:

- **ScoreMatrix model:** N×N numpy array where `matrix[i][j]` = score giver j gave to recipient i
- **StudentInfo:** name, email, index with bidirectional lookup
- **Non-submitter handling:** missing raters (No Response/Not Submitted) have their row+column removed, maintaining a square matrix
- **Validation:** column sum consistency (±1 of team median), cross-check against summary stats
- **Team filtering:** teams with ≥50% missing raters are dropped with a warning
- **Question detection:** identifies point-distribution questions by "Distribute a total of..." prefix

### Project Planning

Created the full project plan (`plans/peer-assessment-grading-engine.md`) and opened GitHub Issues #1–#13 to track all work items:
- Issue #1: PRD (master tracking issue)
- Issues #2–#6: Core models (parser, baseline, WebPA, PeerRank, PeerHITS)
- Issues #7–#13: Visualisation, evaluation, and qualitative pipeline

## Testing

21 integration tests covering:
- Matrix shape and directionality
- Non-submitter removal
- Column sum validation
- Cross-check against CSV summary stats
- Verified against Team 11 ExquisiTech (Session 4, 2024, Q2) — exact 6×6 matrix

## Reflections

The rewrite was substantial but necessary. The original parser was too fragile. The Pydantic-based approach gives us validation at the boundary — if a ScoreMatrix is constructed, we know the data is clean.

Key design decision: `matrix[i][j]` = score **from** j **to** i (not the other way around). This means each column j is "all the scores j gave" and each row i is "all the scores i received." This convention makes computing IWFs natural: `np.nanmean(matrix[i, :])` gives the mean score received by student i.
