# Plan: Peer-Assessment Grading Engine

> Source PRD: Badenas_Jos_421180443_Research_Proposal.pdf — "Optimising Peer-Assessment Reliability in Capstone Software Projects through Algorithmic Weighting and Qualitative Red-Flagging"

---

## Status & forward roadmap — 2026-05-18

### Phase completion

| Phase | Description | Status |
|---|---|---|
| Phase 1 | CSV parser + baseline model (one team) | ✅ Done |
| Phase 2 | All four models, single team | ✅ Done |
| Phase 3 | Full dataset ingestion + data quality report | ✅ Done |
| Phase 4 | Synthetic attack simulation | ❌ Not started — `src/attacks/` empty |
| Phase 5 | Delta-Analysis & Red-Flag Dashboard (RQ3) | ⚠️ Pivoted — see below |
| Phase 6 | Qualitative Sentiment Pipeline (RQ4) | ❌ Not started — `src/qualitative/` empty |
| Phase 7 | Validation tests & final evaluation | ⚠️ Partial — 237 tests passing, but attack/qualitative untested |

Additionally implemented (not in original phases): PeerRank-Impute/Exclude, PeerHITS-Impute/Exclude variants (Issue #5/#6), rank reversal metric (Issue #7), team-dynamics atypicality pipeline (Issue #11, RQ3 work), force-layout + Dash dashboard.

### RQ status

| RQ | Proposal intent | Current state |
|---|---|---|
| **RQ1 — Manipulation resistance** | 4 models vs baseline under uniform-inflation + zero-self, real data + synthetic attacks | Models ✅. Attack simulation ❌. Non-submitter amplification finding already documented (strong preliminary result). |
| **RQ2 — Convergence stability** | PeerRank sensitivity to single outlier raters (Monte Carlo) | Convergence metadata ✅. Perturbation experiment ❌ (depends on `attacks/`). |
| **RQ3 — Δ as collusion detector** | Δ vs Git Gini / verified free-riding | Pivoted: atypicality↔Δ result ✅ (r=0.37, p=0.02, n=39 clean). Git validation ❌ (no Git data). Data-quality finding co-headline (35 teams → 18 usable → 6 complete). |
| **RQ4 — Journal sentiment** | Sentiment-IWF divergence catches involuntary non-contribution | ❌ Not started. No journal data. |

### Forward plan (rest of research, ~5–6 weeks)

**Principle:** build what needs no data first; leave clean interfaces for data that may arrive.

#### Track 1 — Attack simulation (RQ1 + RQ2) — *immediate priority*

Implement `src/attacks/` per Phase 4 spec. No external data required.

- Four attack transforms: uniform inflation, zero-self (full + partial collusion), targeted down-vote, single outlier (Monte Carlo, 100 perms)
- Synthetic team generator: controlled N×N matrices for N=4,5,6 with known ground-truth contribution vectors — lean on these because real n is thin (18 usable teams)
- Attack Delta metric + RQ2 convergence tracking under single-outlier
- Apply to both clean real matrices and synthetic teams; robustness bar charts with MC error bars
- Fold in non-submitter amplification as a fifth documented vulnerability ("strategic non-submission")
- Closes Issues #9 and #10

#### Track 2 — Reframe RQ3/RQ4 with Anna (parallel, ~half day prep)

Raise at next supervisor meeting:
- **RQ3:** present atypicality↔Δ + data-quality finding as the contribution. Frame claim as "internal-consistency signal," not free-riding detection. Git validation conditional on data arrival.
- **RQ4:** either preliminary prototype on CSV confidential-comment columns, or documented limitation — get Anna's decision.
- Surface the data question directly: are more CSVs, Git logs, or journals realistically obtainable? What's the path?
- Agree to formally narrow scope where data doesn't exist; adjust dissertation framing accordingly.

#### Track 3 — Conditional on data arrival (only if/when it lands)

| Data | Unlock |
|---|---|
| More peer-score CSVs | Re-run all pipelines; lifts n for every RQ |
| Git metrics | Implement stubbed `git_alignment()` and Δ-vs-Gini correlation (proper proposal-RQ3) |
| Journals | `JournalAdapter` behind Layer-1 interface; Layers 2–3 (VADER + classifier) unchanged |

Keep interfaces defined (Git Alignment stub, `JournalAdapter` spec) so data slots in without rework.

#### Track 4 — Writing (start in parallel with Track 1)

Dissertation-ready now: model implementations + theory, data-quality finding, non-submitter amplification, RQ3 pivot narrative. Start drafting these chapters while Track 1 runs.

#### Approximate sequencing

| Period | Focus |
|---|---|
| Now → +2 weeks | Track 1: build attacks, Track 2: reframe note for Anna |
| +2 → +4 weeks | Track 1: analysis/charts, Track 4: draft RQ1/RQ2 + methods/data chapters |
| +4 → end | Track 3 (if data arrived), finalise writing |

---

## Architectural decisions

Durable decisions that apply across all phases:

- **Core data structure**: `ScoreMatrix` — an N×N numpy array per team per question, where `S[i][j]` = score student `j` gave to student `i`. Accompanied by metadata: team name, session identifier, year, semester, question label, and a bidirectional student-index mapping (name/email ↔ row/column index).
- **Data validation**: Pydantic models at the parsing boundary. Catches malformed entries (`"Not Submitted"`, `"No Response"`, missing raters) before they propagate into the engine.
- **Engine core**: numpy for all matrix operations and iterative convergence. pandas for CSV loading and exploratory analysis in notebooks.
- **Four IWF models**:
  - **Simple Average (Baseline)**: Kaufman et al. formula. IWF_i = mean of peer scores received (excluding self).
  - **WebPA (Normalisation)**: Peer Assessment Factor scaled to preserve grade neutrality (sum of weighted grades = team grade).
  - **PeerRank (Iterative Graph)**: Walsh's fixed-point algorithm. α parameterized (default 0.1). Convergence threshold ε = 10⁻⁶, max 1000 iterations, convergence flag and iteration count tracked.
  - **PeerHITS (Dual-Score Iterative Graph)**: Novel variant. Separate authority (contribution quality) and hub (assessment quality) scores. L2-normalised per iteration. Same convergence parameters as PeerRank.
- **Primary data source**: Point distribution questions (10×N pool) from COMPSCI 399 peer feedback CSVs. 8 independent score matrices across 4 sessions (S1-2023 Session 1 Q6, S1-2023 Session 3 Q2/Q3/Q4, S1-2024 Session 1 Q6, S1-2024 Session 4 Q2/Q3/Q4). Each treated as an independent matrix.
- **Secondary data**: Q1 contribution estimates (100-point scale) usable as a validation signal, not primary model input.
- **Missing data strategy**: Exclude non-submitting raters (columns) from the matrix. Drop entire team only if ≥50% of raters are missing.
- **Attack simulation**: 4 attack vectors — uniform inflation, zero-self (full + partial collusion), targeted down-vote (victim remains honest rater), single outlier (Monte Carlo, 100 permutations). Applied to both real data (injection into existing matrices) and fully synthetic teams.
- **Evaluation metrics**: Rank Reversal Rate (δ parameterized, default 0.15), Attack Delta (raw mean absolute difference), Git Alignment (Pearson correlation, stubbed until Git data available).
- **Qualitative pipeline**: 3-layer architecture — Input Adapter (CSV text feedback now, journal entries later) → Sentiment Analyzer (VADER via NLTK) → Trajectory & Red-Flag Classifier (4 categories from proposal). Prototyped against existing text feedback; output flagged as preliminary.
- **Visualisation**: Plotly for interactive charts (exportable as standalone HTML for dissertation). Jupyter notebooks for interactive exploration.
- **Testing**: Post-implementation validation — hand-computed analytical test cases, property-based invariant checks, attack sanity tests.
- **Project structure**:
  ```
  cs789-project/
  ├── src/
  │   ├── parsing/         # CSV parsing → ScoreMatrix objects
  │   ├── models/          # 4 IWF models
  │   ├── attacks/         # Synthetic attack simulator
  │   ├── evaluation/      # Metrics (rank reversal, attack delta, git alignment)
  │   ├── qualitative/     # Sentiment pipeline
  │   └── visualization/   # Plotly charts
  ├── notebooks/           # Jupyter notebooks for exploration/reporting
  ├── tests/               # Unit/property tests
  ├── data/                # CSVs (gitignored)
  ├── plans/               # This file
  └── requirements.txt
  ```

---

## Phase 1: One Team Through the Full Pipeline

**Research questions**: Foundation for all RQs — proves data extraction and baseline IWF computation work end-to-end.

### What to build

A complete vertical slice from raw CSV to computed IWF vector for a single team. Parse one CSV file, locate the directed giver→recipient data section within a point-distribution question, extract all rows for one team, construct a validated `ScoreMatrix` (N×N numpy array with Pydantic-validated metadata), run the Simple Average baseline model (exclude self-scores on the diagonal, compute mean of peer scores per student), and output the resulting IWF vector with student names.

The parser must handle the two-section structure of each question block: skip the summary statistics section and target the directed data section (identified by the `Giver's Name` column header). The Pydantic schema must validate that point totals sum to 10×N per rater (within tolerance for rounding) and flag anomalies.

### Acceptance criteria

- [ ] CSV parser correctly identifies and extracts the directed giver→recipient data section (not the summary statistics) for point-distribution questions
- [ ] `ScoreMatrix` is constructed as an N×N numpy array with correct giver→recipient orientation (`S[i][j]` = score from j to i)
- [ ] Pydantic validation catches and reports malformed entries (e.g., "Not Submitted", "No Response") without crashing
- [ ] Baseline Simple Average model excludes self-scores and computes IWF vector matching hand-calculated expected values
- [ ] Output displays team name, student names, and IWF vector in a readable format
- [ ] Non-submitting raters are excluded (column removed) and IWF denominator adjusted accordingly

---

## Phase 2: All Four Models, Single Team

**Research questions**: RQ1 (manipulation resistance), RQ2 (convergence stability) — establishes model computation and comparison.

### What to build

Implement the remaining three IWF models (WebPA, PeerRank, PeerHITS) and run all four against the same ScoreMatrix from Phase 1. Each model takes the same N×N matrix and produces an N-length IWF vector. PeerRank and PeerHITS also return convergence metadata (iteration count, whether convergence was achieved).

Build a basic Plotly grouped bar chart showing the four models' IWF vectors side-by-side for the team, making rank reversals visually apparent. Compute the Rank Reversal metric for each advanced model relative to the baseline, using the parameterized δ threshold.

### Acceptance criteria

- [ ] WebPA produces IWF vectors where the sum of (IWF_i / 10 × G_team) across all students equals N × G_team (grade neutrality preserved)
- [ ] PeerRank converges within 1000 iterations and returns the iteration count and convergence flag
- [ ] PeerRank α is parameterized (default 0.1) and produces different IWF vectors at different α values
- [ ] PeerHITS produces separate authority and hub score vectors, both L2-normalised
- [ ] PeerHITS converges within 1000 iterations with iteration count tracked
- [ ] Plotly bar chart displays all 4 models' IWFs for the team, exportable as standalone HTML
- [ ] Rank reversals between baseline and each advanced model are correctly identified using δ threshold
- [ ] All four models produce identical IWF vectors (all 10.0) when given a perfectly uniform score matrix (sanity check)

---

## Phase 3: Full Dataset Ingestion

**Research questions**: RQ1, RQ2, RQ3 — enables analysis at scale across the full historical dataset.

### What to build

Scale the parser to process all 7 CSV files and extract ScoreMatrix objects for every team across all 8 point-distribution questions. Handle the varying question numbering across sessions (Q6 in Session 1 files, Q2/Q3/Q4 in final session files) by matching on question text pattern ("Distribute a total of...") rather than question number.

Implement the full missing-data strategy: identify non-submitting raters, exclude their columns, flag teams with ≥50% missing raters for exclusion, and produce a data quality report summarising what was included/excluded and why. Run all 4 models across every valid ScoreMatrix. Compute aggregate Rank Reversal Rate across the entire dataset.

### Acceptance criteria

- [ ] All 7 CSV files are parsed and point-distribution questions are identified by text pattern, not question number
- [ ] ScoreMatrix objects are constructed for every team in all 8 point-distribution question instances
- [ ] Missing data is handled per the agreed strategy: non-submitting rater columns excluded, teams with ≥50% missing raters dropped
- [ ] A data quality report is generated listing: total teams parsed, teams excluded (with reasons), raters excluded per team, anomalies detected
- [ ] All 4 models run successfully across the full dataset without errors or hangs
- [ ] Aggregate Rank Reversal Rate is computed for each advanced model vs. baseline across all teams
- [ ] PeerRank and PeerHITS convergence metadata is aggregated: distribution of iteration counts, any non-convergent cases identified

---

## Phase 4: Synthetic Attack Simulation

**Research questions**: RQ1 (manipulation resistance), RQ2 (convergence stability under attack).

### What to build

Implement the four synthetic attack vectors and an attack simulation framework that applies each attack to both real score matrices (from Phase 3) and fully synthetic teams with known ground-truth contribution vectors.

For real data: take each team's original ScoreMatrix, apply each attack transformation, re-run all 4 models, compute Attack Delta (mean absolute difference between attacked and unattacked IWF vectors).

For synthetic data: generate controlled N×N matrices for teams of 4, 5, and 6 students with predefined contribution profiles, apply attacks, measure how well each model recovers the true IWF.

The single outlier attack uses Monte Carlo simulation (100 random permutations per team) and reports the distribution (mean, std, min, max) of Attack Delta.

The zero-self attack is tested in both full-collusion (all members) and partial-collusion (2 of N members) variants.

Build Plotly robustness charts: grouped bar chart of mean Attack Delta per model per attack type, with error bars for Monte Carlo results.

### Acceptance criteria

- [ ] Uniform inflation attack: when applied, baseline produces IWF = 10.0 for all students (verified)
- [ ] Zero-self attack: both full and partial collusion variants implemented and produce distinct results
- [ ] Targeted down-vote attack: victim receives IWF = 0 under baseline; victim's own ratings remain honest (unmodified)
- [ ] Single outlier attack: Monte Carlo with 100 permutations per team; reports mean, std, min, max of Attack Delta
- [ ] Attack Delta computed correctly as raw mean absolute difference between attacked and unattacked IWF vectors
- [ ] Attacks applied to both real dataset matrices and fully synthetic teams (sizes 4, 5, 6)
- [ ] Robustness bar chart shows clear differentiation between models (PeerRank/PeerHITS should show smaller Attack Deltas than baseline for collusion attacks)
- [ ] PeerRank convergence behaviour under single-outlier attack is documented (iteration counts, any non-convergence)

---

## Phase 5: Delta-Analysis & Red-Flag Dashboard (RQ3)

**Research questions**: RQ3 — whether cross-model divergence serves as a reliable red flag for instructor attention.

### What to build

Compute the divergence ("Delta") between IWF vectors produced by different model pairs for every team in the dataset. A team with large Delta between the baseline and an advanced model is a candidate for instructor review — the models disagree on the rank ordering, suggesting the raw scores may be unreliable.

Build an instructor-facing Plotly dashboard with:
1. A Delta heatmap: teams on one axis, model-pairs on the other, colored by divergence magnitude. High-Delta cells are red flags.
2. Drill-down capability: clicking a team shows the 4 models' IWF vectors, the raw score matrix, and any anomalies detected during parsing.
3. A ranked list of teams sorted by maximum Delta, prioritising those most warranting review.

Correlate high-Delta teams with observable patterns in the raw data (e.g., uniform scores, zero self-scores, one student receiving dramatically different scores across models).

### Acceptance criteria

- [ ] Delta computed for all model pairs (baseline–WebPA, baseline–PeerRank, baseline–PeerHITS, PeerRank–PeerHITS, etc.) across all teams
- [ ] Delta heatmap clearly highlights teams with large cross-model divergence
- [ ] Teams are ranked by maximum Delta to produce a prioritised review list
- [ ] Drill-down view shows raw score matrix alongside the 4 models' IWF outputs for any selected team
- [ ] High-Delta teams are cross-referenced with observable patterns (uniform scores, zero self-scores, score variance)
- [ ] Dashboard is exportable as standalone HTML

---

## Phase 6: Qualitative Sentiment Pipeline (RQ4)

**Research questions**: RQ4 — whether sentiment–IWF discrepancies identify cases of involuntary non-contribution.

### What to build

Extract text feedback from the directed qualitative questions (Q6/Q7 in most sessions — confidential comments about teammates and team dynamics). Build the 3-layer sentiment pipeline:

**Layer 1 — Input Adapter**: Parse CSV text feedback into structured `(giver, recipient, session, text)` tuples. Handle "No Response" entries.

**Layer 2 — Sentiment Analyzer**: Apply VADER (via NLTK) to each text entry, producing a compound sentiment score in [-1, 1]. Compute per-student aggregate sentiment (mean of all feedback received) and per-student sentiment trajectory across sessions.

**Layer 3 — Red-Flag Classifier**: Compare each student's IWF z-score against their sentiment z-score. Classify into the 4 categories from the proposal: aligned positive, aligned negative, suppressed distress, masked exclusion. The masked exclusion category (high IWF, negative sentiment) is the primary target.

Build Plotly sentiment-vs-IWF scatter plot colored by category, and time-series charts showing sentiment trajectory overlaid with IWF trajectory for flagged students.

All classifier output is flagged as **preliminary** — designed for journal data, prototyped here against text feedback.

### Acceptance criteria

- [ ] Text feedback extracted from all sessions with giver→recipient mapping preserved
- [ ] VADER sentiment scores computed for all non-empty feedback entries
- [ ] Per-student aggregate sentiment and per-session trajectory computed
- [ ] Students classified into the 4 proposal categories using z-score divergence threshold
- [ ] Masked exclusion cases (high IWF, negative sentiment) identified and flagged
- [ ] Scatter plot and trajectory charts produced in Plotly, exportable as HTML
- [ ] All output clearly marked as preliminary (prototyped on text feedback, not journal data)
- [ ] Input Adapter interface is documented so a `JournalAdapter` can be swapped in later without changing Layers 2-3

---

## Phase 7: Validation Tests & Final Evaluation

**Research questions**: All RQs — ensures correctness and produces dissertation-ready outputs.

### What to build

Write comprehensive validation tests for the entire system:

**Analytical tests**: Hand-compute IWF vectors for small teams (3-4 students) with known score matrices. Verify each of the 4 models produces the exact expected output. Include the 3-person zero-self example from the proposal (Section 1.2).

**Property-based invariant tests**: For any valid ScoreMatrix, verify: WebPA grade neutrality holds, PeerRank converges for non-degenerate matrices, all IWFs are non-negative, self-score exclusion does not change results, PeerHITS authority and hub vectors are unit-normalised (L2).

**Attack sanity tests**: Uniform inflation → all IWFs = 10.0 under baseline. Targeted down-vote → victim IWF = 0 under baseline.

**Git Alignment stub**: Define the interface (`git_alignment(iwf_vector, git_contribution_vector) → Pearson r`) with documentation, ready for implementation when Git data arrives.

**Final evaluation report**: Compile all metrics across the full dataset into a comprehensive summary with dissertation-ready Plotly charts: IWF comparison dashboards, attack robustness charts, Delta heatmaps, convergence plots, sentiment divergence charts.

### Acceptance criteria

- [ ] Analytical test cases pass for all 4 models with hand-computed expected values
- [ ] Property invariants hold across the full dataset (WebPA grade neutrality, convergence, non-negativity, L2 normalisation)
- [ ] Attack sanity tests pass for trivial cases
- [ ] Git Alignment interface is defined with clear documentation and type signatures
- [ ] All Plotly charts are exported as standalone HTML files suitable for dissertation inclusion
- [ ] A summary report documents: dataset statistics, per-model aggregate metrics, attack robustness comparison, Delta-Analysis findings, sentiment pipeline preliminary results
- [ ] All tests are runnable via a single command (e.g., `pytest`)
