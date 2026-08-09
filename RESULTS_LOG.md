# Results log

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

- **2026-07-20 — Hand-labelling tooling (RQ3-EXT Step 3, handoff-4).** Added
  `src/labelling/{sample,cards,kappa}.py`. Team-level sampler (unit =
  `(csv_path, team_name)`; AA k=4 majority, no-majority → Mixed) drew 40 of 139
  teams, stratified over {A0,A1,A2,A3,Mixed}×{Typical,Anomalous}; all cells
  filled, no shortfall. Cell counts (Anom/Typ): A0 6/4, A1 3/4, A2 5/2 (full
  census), A3 5/6, Mixed 3/2. Blinded `cards.pdf` (A–F, randomised, journals
  pending) + `card_key.csv` + `label_sheet_template.csv`. `mixture.py` now
  persists `output/dynamics/aa_k4_assignments.csv` (loads 71/172/40/134 reproduce
  exactly). Design record: `docs/labelling-design.md`.
