# Results log

- **2026-08-20 — Pooled team-level cascade (handoff-11 B).**
  New `src/dynamics2/pooled.py` mirrors the per-matrix gate cascade at team
  level, keying rater vectors by `(recipient, question)` so N=4 teams (every one
  `Silent-incomparable` per matrix) become comparable. Pooling primitive
  `pooled_tau_matrix` moved out of `contested.py` (4c faction test reproduces
  bit-for-bit, 66/66). New `pooled` command → `output/dynamics2/pooled/
  team_states.csv` + `concordance.csv`; `validate.py` gains a 3-questions-per-team
  arm → `output/dynamics2/validation/pooled_validation.csv`; `tests/test_pooled.py`
  (7). **Synthetic free-rider recall N=4/5/6 pooled vs per-matrix-any-flag on the
  same 3 questions: 0.72/0.94/0.96 vs 0.00/0.46/0.94** — pooling reads N=4
  free-riders the per-matrix lane is 0% blind to and doubles N=5 recall, with
  **pooled Even false-positive ≤4%** (calibrated). Single-question standout
  recall (pooled) 0.00/0.06/0.06 — the expected dilution cost. **Real corpus
  (139 teams, N=5/6): pooled vs any-flag agree 80/139**; readable-team
  disagreement is directional (pooling resolves 25 low-power `Contested`→`No
  standout`, dilutes 17 single-artefact standouts, promotes 16 to `Standout`) —
  a construct difference (any-flag *max* vs pooled *average*), not a defect;
  argues for keeping both lanes. Additive: `matrix_states.csv` and RQ4 tiers
  untouched (pre-registration, B0). 325 tests pass.

- **2026-08-20 — Attack-transform diagonal fix + RQ1 table regen (handoff-11 A).**
  Fixed self-score (diagonal) handling in `src/attacks/transforms.py`
  (`single_outlier`, `uniform_inflation`, `zero_self`; `targeted_downvote` was
  correct) — WebPA reads the diagonal, so the old code mis-measured it.
  `tests/test_transform_diagonal.py` (16). Re-ran attacks over all **417** real
  matrices + synthetic → `output/attacks/attack_summary.csv`,
  `attack_absolute_vs_relative.csv`; regenerated
  `output/tables/table_rq1_attacks.tex` (caption n=217→N=417, model corrections
  folded in). Corrected real numbers: **single-outlier WebPA 0.265 (was 0.784),
  now the most robust — ratio 0.78 vs baseline**; **zero-self-full WebPA 0.625,
  zero-self-partial 1.152 (were 0.000)** — WebPA is *not* immune to zero-self,
  the old immunity was a whole-column scaling its normalisation cancels.
  peerrank/peerhits/baseline diagonal-agnostic cells unchanged. Reverses §1.4
  contribution 2 and narrows the handoff-9b zero-self immunity claim to
  PeerRank/PeerHITS (prose is Jos's, A5). 325 tests pass.

- **2026-08-11 — Synthetic validation of the dynamics2 triage cascade (handoff-10).**
  New `src/dynamics2/validate.py` (+ `tests/test_validate.py`, 14 pass) plants
  **known team states** with `src/attacks/synthetic.py` extended to the CS399
  form (10·N points/rater incl. self, diagonal populated), runs the **unmodified**
  cascade, and scores recovery. 7 planted states × N∈{4,5,6} × 50 reps × 500
  perms. Outputs → `output/dynamics2/validation/`: `confusion_raw.csv`,
  `confusion_matrix.csv`, `headline_metrics.csv` (Task 2), `lazy_test.csv`
  (Task 3), `power_curve.csv` (Task 4), `robustness.csv` (Task 5),
  `realism_permatrix.csv` + `realism_summary.csv` (Task 6). Headlines (Wilson
  CIs in file): **free-rider recall** 0/24/68% at N=4/5/6; **Even false-positive
  into a standout 0.7%** (≪10% deploy trigger); **Contested recall 100% at
  N≥5** (0% at N=4) — so the real-data faction null is *genuine, not a power
  failure* — though Contested over-fires on Even/Disengaged teams (95/150 each),
  making it a low-agreement flag rather than a faction proof. **Lazy-rater test:
  cohesive vs disengaged are indistinguishable** (94 vs 94 Contested) —
  demonstrates the cohesive/disengaged distinction is unrecoverable from a
  matrix. **Detection floor:** only reliable N=6 crosses 50% (δ≈4), never 80%;
  lazy ≈0 everywhere. **Realism:** generator is cleaner on coverage (0% Silent
  vs 37% real; 100% vs 62.6% τ-coverage) but *not* easier on agreement (median
  τ 0.47 vs 0.79), so recall figures are **upper bounds**; %Contested matches
  real (23.5 vs 24.0). No changes to `src/dynamics2/` gate logic.

- **2026-08-10 — Reversed handoff-9 baseline scaling; zero-self is an inflation attack invisible to Δ (handoff-9b).**
  Handoff-9 Task 2 (scale baseline to mean 10) **misrepresented the CS399
  instrument** and made baseline look immune to zero-self collusion — an
  artefact. Corrected: **split into two models.** `baseline_cs399` (unscaled,
  self-excluded mean = `total_from_peers/(N−1)`, level meaningful) is the
  institutional model and the default alias `baseline_average`; `baseline_normalised`
  (mean 10) is used **only** for cross-model Δ (which measures relative standing).
  The Δ registry points at `baseline_normalised`, so **Δ and all handoff-9
  conclusions are unchanged** (RQ3 partial −0.038 still collapses; Δ-by-state
  ordering unchanged; Silent-excluded tautology p=0.081, not significant).
  New `src/audit/absolute.py` reports RQ1 attacks under absolute vs relative views.
  - Instrument verified: 10·N budget incl self holds in **398/417 (95.4%)**
    (N=6 324/324, N=5 74/93).
  - **Zero-self-full is a pure inflation:** under cs399 every member's weight rises
    **+25% (N=5) / +20% (N=6)** with **relative Δ = 0** and **no loser**;
    **≈0 change in every mean-10 model** (webpa/peerrank/peerhits/baseline_normalised)
    — structurally immune, which the relative-only analysis could not express.
  - Transforms classified: **inflationary** = zero-self-full (pure), zero-self-partial
    (+8%, mixed), uniform-inflation (+24%, mixed); **redistributive** =
    targeted-downvote, single-outlier.
  - **Detectability asymmetric:** N=6 inflation separable (natural max 10.88 <
    implied 12.0); N=5 not (2/93 natural teams ≥12.5). Descriptive only — no team
    labelled as colluding.
  - Files: `output/attacks/attack_absolute_vs_relative.csv`,
    `output/audit_fix/inflation_detectability{,_permatrix}.csv`. 288 tests pass.

- **2026-08-09 — Model-implementation audit fixes + downstream regeneration (handoff-9).**
  Audited `src/models/` against primary sources. **Baseline** now scales to team
  mean 10.0 (Task 2) — the one real numeric fix; it removes a scale offset that
  was leaking into every cross-model Δ. **WebPA** normalisation implemented
  canonically (÷ rater total incl self) and verified a **provable no-op** on this
  fixed-budget instrument (rater sums incl self constant 417/417; output identical
  to before, r=1.0000) — Task 1 was a false alarm that became a finding.
  **PeerRank/PeerHITS**: deviations from Walsh/Kleinberg declared in docstrings
  (no logic change); PeerHITS convergence confirmed on all 417 (max 78 iters).
  Renamed `modularity`→`split_quality` in `dynamics2` (states unmoved). New
  `src/audit/` regenerates Δ, RQ3 and attack-by-state to the parallel path
  `output/audit_fix/` (pre-fix outputs untouched). 291 tests pass (+`test_audit_fixes.py`).
  - **WebPA↔baseline** mean r **0.967** (median 0.987) — a *principled*
    near-equivalence: on a fixed-budget instrument WebPA's normalisation is
    redundant by design. All four models now team-mean exactly 10.0.
  - **Δ overall** 0.427→**0.394** (−7.6%); **Δ-by-state median ordering unchanged**.
  - **RQ3 survives:** clean row r +0.385→+0.380; team-level (n=84) +0.465→+0.443
    (p<1e-4); **partial r −0.055→−0.038, still collapses** — shared-variance holds.
  - **Tautology check (Task 8):** all-states KW H=212, p=3e-42, but **excluding
    Silent it is NOT significant** (H=8.31, p=0.081, ε²=0.017; no pair survives
    Holm). Only the *weak* triage claim is supported (Δ tracks presence, not type,
    of structure).
  - **Attack-by-state (Task 7):** the "no signal ⇒ manipulable" hypothesis is
    **reversed** — Silent-flat has the lowest attack Δ (0.77), rising to One-at-top
    (1.64); flat matrices are hard to move because already compressed.
    Targeted-downvote is uniformly effective (~3.4); zero-self near-immune
    post-fix. Files: `output/attacks/attack_by_state{,_permatrix}.csv`.
  - **RQ1 side-effect:** scaling baseline makes it grade-neutral → now immune to
    the *uniform* zero-self-full attack (was literal grade uplift); partial attack
    still bites. Jos decides text changes; pre-fix numbers preserved.

- **2026-08-09 — `src/dynamics2/` rank-based state cascade, permanent + tested (handoff-8).**
  Made the 2026-08-07 exploratory Lane B reproducible: new **additive** package
  `src/dynamics2/` (`src/dynamics/` untouched, both lanes runnable). Transforms
  each rater's ratings to within-rater normalised ranks (÷(k+1)) to divide out
  leniency/severity/range, then runs a three-gate cascade — Gate A count
  qualifying raters (Silent-flat / -lone-dissenter / -incomparable), Gate B mean
  pairwise Kendall **τ-b** vs a per-rater permutation null (Contested), Gate C
  bottom/top consensus-gap vs null (One at bottom / top / Both ends / No
  standout). Every threshold is the null in `nulls.py` (add-one p, BLAKE2b-seeded
  per (matrix, statistic), search-inside-null enforced by a matrix→scalar
  callable). `contested.py` adds the faction (size-1 = lone deviant, not a
  faction), concentration, and pooled team-level tests; `crossq.py` the
  cross-question bottom consistency; plus the strong free-rider join.
  Run `python3 -m src.dynamics2 --n-perm 1000` → `output/dynamics2/`
  (matrix_states, contested_factions[_pooled], contested_concentration,
  cross_question, strong_freerider_candidates); bit-for-bit reproducible.
  - **States (417):** Silent **156** (87/61/8, exact) · Contested 99 · No standout
    99 · One at bottom 37 · One at top **22** · Both ends **4**; clean Silent **42**.
    Contested +9 / standouts −few vs the n_perm=100 exploratory, entirely the
    add-one p-value tipping borderline-agreement matrices into Contested (expected).
  - **Orthogonality (261 computable):** τ vs `mean_rater_std` **+0.055**,
    reciprocity −0.124, asymmetry +0.122, gini +0.200 — exact; rank transform
    leaks no rater effect. **Coverage 261/417 · 175/217** — exact.
  - **Factions:** **1** genuine multi-person faction (pooled) + 4 lone-deviant;
    per-matrix 2 genuine + 4 lone-deviant. The "Contested is noise not camps"
    negative holds on three independent tests (>3 genuine would have overturned it).
  - **Cross-question:** 93/139 readable, same bottom 3q/2q/1q = **31/39/23**,
    mean τ **0.335** — exact. **One-at-bottom is 23 A0** (~3× base rate, exact).
  - **New for §5.3:** **13 strong free-rider candidates** (same student bottom on
    all three tasks *and* a significant bottom gap) — a number that did not exist
    before. 17 new unit tests; full suite 275 passed. Whether this lane replaces
    `dynamics` for §5.3 is Jos's call — no decision taken, nothing overturned.

- **2026-08-06 — Codebook v2 + main-run sample (RQ3-EXT Step 4, handoff-7).**
  Applied the pilot findings (`notes/pilot-coding-findings.md` R1–R7) as codebook
  **v2** in `reader.py`: per-entry cut 5→3 fields (`teammate_content_valence`
  replaces `negative_teammate_content`; dropped `discusses_team_process` +
  entry `concern_rating`); team-level gains `singled_out_direction` (Dominant vs
  Free-rider) and conditional `singled_out`/`agreed` fields, inline scale anchors
  (fixes the reversed-divergence misread), `evidence_sufficient` (renamed), and a
  **required** `team_notes`; every row now carries `codebook_version` + per-record
  `coded_at`. Regenerated `reader_teams_<cohort>.html` (v2); `reader_pilot.html`
  left as the frozen v1 artefact. Main-run sample (`sample.py main` →
  `output/qualitative/main_run_sample.csv`, 32 teams): A0=8 + A2=10 census
  (gate held under mean-load argmax), A1=10 stratified 5-low/5-high mean journal
  word count (231–415 vs 742–1347, clean tails), A3=4 random; `mean_word_count`
  per team + `team_mean_word_count` in manifests; 2 census teams flagged
  `in_pilot`. Task 4 (`wordcount_suspect_check.md`): the 3 flagged short files
  (46/48/48 w) sit below the corpus 1st percentile (58 w) — proxy available but
  circular, real test deferred to the main run. Verified headlessly (jsdom):
  conditional fields, required-notes gating, anchors, v2 provenance. No coding
  done; no sentiment analysis.

- **2026-08-04 — Journal reading UI, team-based (pilot + Step-4 read, handoff-6 amended).**
  Added `src/qualitative/{sample,reader,templates}.py` + `README.md`. Reading unit
  is the **team** (construct = within-team agreement, not affect; VADER dropped).
  `sample.py` draws seeded batches: `pilot` (3 hand-picked teams, one per named
  archetype, chosen by **mean-load argmax** — A2 `2024_s1` Team 12, A1 `2024_s1`
  Team 5, A0 `2023_s2` Team 33; zero anchor-set spend; +3 `extract_suspect`) and
  `teams` (per cohort, grouped, pseudonymised `team_NN`/members `A`–`F`; keys
  never loaded by the HTML). `reader.py` emits a self-contained offline HTML reader
  (inline CSS/JS, no CDN): keyboard-first coding, per-entry + team-level schema
  (single `CODING_SCHEMA`; team-level `within_team_divergence`,
  `singled_out_agreed`, `engagement_visible` are the A2/A0/A1 hypothesis tests),
  `localStorage` autosave, CSV import/export, member headers, extract-check screen;
  blinded per rubric §2. Team archetype re-derived as mean-load argmax (majority-
  vote ties on 21/139, unanimous on 41/139; kept alongside for comparison).
  Audit §9 template survey: `2023_s2`+`2024_s1` prompt team dynamics, `2022_s2`+
  `2023_s1` don't; `2024_s1`'s section is absent at J1 then ~70–78% J2–J5
  (introduced mid-semester). Verified headlessly (jsdom): full team coded →
  reopen restores → export columns match schema; team panel locks until members
  coded; extract-check is free-text-only. No sentiment analysis (handoff-7).

- **2026-08-04 — Journal ingest + linkage audit (RQ4 / RQ3-EXT Step 4, handoff-5).**
  Hardened `.gitignore` to deny-by-default under `data/` and added
  `src/qualitative/{ingest,audit}.py` (+ pinned `pdfplumber==0.11.10`,
  `python-docx==1.2.0`). Ingested **2796** Canvas journal files across 4 cohorts
  (2022_s2, 2023_s1, 2023_s2, 2024_s1) → **618** pseudonymised students; filename
  parse rate 100%, extraction 99.0% (42 `extract_suspect <50w`, 19 unsupported,
  2 errors). Linkage audit (`output/qualitative/linkage_audit.md`, git-ignored):
  analysable intersection with peer data = **2023_s1, 2023_s2, 2024_s1**;
  2022_s2 = `calibration_only`; export does **not** reach 2024_s2/2025_s1.
  Match rates 98.2% / 95.9% / 89.1% — `2024_s1` peer CSV uses `First Last` not
  `Last, First`, recovered by an order-invariant **exact** join (82/92, 0
  ambiguous, 0 false matches in the last-first cohorts). Team coverage viable in
  all three (median 6 members journaled, 0 thin teams) → Step 4 not blocked.
  Doc-metadata dates recoverable for 83% of files. No sentiment analysis (gated,
  handoff-6). Nothing under `data/`/`output/` is committed.
- **2026-07-26 — Labelling UX overhaul.** Added `src/labelling/ui.py` →
  self-contained `label_ui.html` (embedded card images, dropdowns, autosave,
  Download-CSV) so a non-technical second rater can label with zero setup.
  Taxonomy trimmed 7→5+Unclassified (dropped Collusive: not matrix-separable from
  Cohesive). No guided decision tree (would inflate κ); cards stay raw data. See
  `docs/labelling-design.md §labelling-ux`.

- **2026-07-20 — Hand-labelling tooling (RQ3-EXT Step 3, handoff-4).** Added
  `src/labelling/{sample,cards,kappa}.py`. Team-level sampler (unit =
  `(csv_path, team_name)`; AA k=4 majority, no-majority → Mixed) drew 40 of 139
  teams, stratified over {A0,A1,A2,A3,Mixed}×{Typical,Anomalous}; all cells
  filled, no shortfall. Cell counts (Anom/Typ): A0 6/4, A1 3/4, A2 5/2 (full
  census), A3 5/6, Mixed 3/2. Blinded `cards.pdf` (A–F, randomised, journals
  pending) + `card_key.csv` + `label_sheet_template.csv`. `mixture.py` now
  persists `output/dynamics/aa_k4_assignments.csv` (loads 71/172/40/134 reproduce
  exactly). Design record: `docs/labelling-design.md`.
