# Results log

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
