# PeerRank Model, CLI Runner & Documentation

**Date:** 6 April 2026  
**Issues:** #5, #15  
**PRs:** #16 (PeerRank, merged), #17 (CLI, merged)

## What I Did

Big productive day — implemented the second model, built the CLI runner, and wrote project documentation.

### PeerRank Model (Issue #5, PR #16)

Implemented Walsh's (2014) PeerRank fixed-point iterative algorithm:

- **Credibility weighting:** each rater's scores are weighted by how closely they agree with the current consensus
- **Fixed-point iteration:** IWF vector updated each round using credibility-weighted averages until convergence
- **Configurable parameters:** alpha (damping), epsilon (convergence threshold), max_iterations
- **Convergence metadata:** tracks whether the algorithm converged, number of iterations, and final L1 norm

Key insight: PeerRank amplifies differences. If one student is rated slightly higher than average, the iterative process magnifies this because raters who agree with the consensus gain credibility, reinforcing the pattern. This is by design — it rewards "accurate" raters — but it also means small score differences can become large IWF differences.

### CLI Runner (Issue #15, PR #17)

Built a proper CLI interface using Python's argparse:
- `python3 -m src run <csv_file>` — run all models on all teams
- `--model MODEL` — run a specific model only
- `--team TEAM` — filter to a specific team
- Auto-discovers all registered models from a `MODELS` dict in `cli.py`
- Outputs results to CSV files in `output/` directory
- Clean tabular console output with model comparison per team

### Documentation

- Rewrote `README.md` with setup instructions, usage examples, and project overview
- Created `docs/models/baseline.md` — mathematical formulation, implementation notes, edge cases
- Created `docs/models/peerrank.md` — algorithm description, convergence properties, parameter guide

## Testing

- PeerRank: 8 tests covering convergence, uniform scores, non-submitter handling, parameter sensitivity
- CLI: 8 tests covering argument parsing, model dispatch, CSV output, error handling
- Total: 42 tests passing

## Reflections

The CLI runner makes it much easier to experiment with different models and datasets. Previously I had to write ad-hoc scripts — now I can run `python3 -m src run data/file.csv` and get a full comparison.

The model documentation was also valuable — writing out the math formally helped me catch a subtle issue with how PeerRank handles the alpha damping parameter.

## Stats

- 292 lines for PeerRank (model + tests)
- 393 lines for CLI (runner + tests)
- 339 lines of documentation
