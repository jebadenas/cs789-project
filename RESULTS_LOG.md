# Results log

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
