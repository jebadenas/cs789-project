# `data/` — inputs (privacy-critical)

**Nothing in this tree is committed except this file and the peer-CSV schema
notes.** The `.gitignore` denies everything under `data/` by default and adds an
explicit, redundant block on `data/journals/`. See `git check-ignore -v <path>`
if in doubt.

## Contents (all git-ignored)

```
data/
├── *.csv                       # COMPSCI 399 peer-feedback exports (one per cohort session)
└── journals/                   # Canvas reflective-journal exports — identifiable student data
    ├── raw/                    # untouched Canvas exports; cohort folders dropped in as-is
    │   └── <cohort>/journal_<n>/<canvasfilename>.{pdf,docx,...}
    ├── interim/                # extracted plain text, still identifiable (<cohort>/<journal_n>/<canvasId>.txt)
    ├── processed/              # analysis-ready, pseudonymised tables (ANON_ID only)
    │   ├── entries.parquet      # one row per journal file, incl. extracted text
    │   └── entry_manifest.csv   # same minus text — reviewable, carries no journal content
    └── crosswalk/              # identity map (normalised name -> ANON_ID) — the single
                                 # most sensitive file in the repo. Never leaves this machine.
```

## Cohorts

| cohort   | journals | peer CSV | role                                           |
|----------|:--------:|:--------:|------------------------------------------------|
| 2022_s2  |    ✓     |    –     | `calibration_only` (held-out; no peer data)    |
| 2023_s1  |    ✓     |    ✓     | analysable (journals 1–4 only)                 |
| 2023_s2  |    ✓     |    ✓     | analysable                                     |
| 2024_s1  |    ✓     |    ✓     | analysable                                     |
| 2024_s2  |    –     |    ✓     | peer-only — contributes nothing to RQ4         |
| 2025_s1  |    –     |    ✓     | peer-only — contributes nothing to RQ4         |

The **join key is the normalised name** (lowercased, non-alphanumerics stripped),
not the Canvas numeric ID — the Canvas ID appears nowhere in the peer data.

## Pipeline

- `python3 -m src.qualitative.ingest`  → parses filenames, extracts text,
  pseudonymises, writes `processed/` + `crosswalk/`.
- `python3 -m src.qualitative.audit`   → writes `output/qualitative/linkage_audit.md`.

**Filename pseudonymisation is not text de-identification** — entry bodies name
teammates. Any excerpt quoted in the dissertation must be manually scrubbed first.
