# Results log

- **2026-08-04 — Journal reading UI (RQ4 recon + Step-4 structured read, handoff-6).**
  Added `src/qualitative/{sample,reader}.py` + `README.md`. `sample.py` draws
  seeded batches: `recon` (25 entries from `2022_s2`, 5/journal-index spanning
  word-count terciles, `ok`-only, +3 `extract_suspect` trailing) and `teams`
  (one batch/cohort, grouped by team, pseudonymised `team_NN` + members `A`–`F`;
  un-blinding `team_key_<cohort>.csv` never loaded by the HTML). `reader.py`
  emits a self-contained offline HTML reader (inline CSS/JS, no CDN/network):
  keyboard-first coding, per-entry + team-level schema (single `CODING_SCHEMA`),
  `localStorage` autosave keyed by batch+rater, CSV import/export, reset-guard;
  blinded per rubric §2. Batches generated for 3 cohorts (recon 0.09 MB; teams
  391/998/376 entries, 1.3/4.8/1.6 MB — `2023_s2` near the 5 MB split threshold).
  Verified headlessly (jsdom): code 3 → reopen restores → export CSV columns
  match schema; teams panel locks until all member entries coded. No sentiment
  analysis (handoff-7). Nothing under `data/`/`output/` committed.

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
