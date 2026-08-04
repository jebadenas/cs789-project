# `src/qualitative/` — journal ingest, linkage audit, by-hand reader

Pipeline for the reflective-journal strand (RQ4 §5.4 and RQ3-EXT Step 4).
**No sentiment analysis lives here** — this package is ingest + instrumentation
only. Sentiment/VADER is a later, separately-gated strand.

## ⚠️ Privacy — read first

Everything this package produces is **identifiable student data** and is
**git-ignored** (`data/**` and `output/` are both denied by `.gitignore`).

- Raw journals, extracted text, the crosswalk, batch specs, and the generated
  HTML readers **must never be committed** and **must never leave `output/` or
  `data/`**.
- A generated `reader_*.html` embeds journal text in the file itself. It can be
  emailed to a second rater as one attachment, but it is still identifiable —
  treat it like the raw journals.
- Filename pseudonymisation is **not** text de-identification: entry bodies name
  teammates. Any excerpt quoted in the dissertation must be scrubbed by hand.

## Modules

| module | what it does | run |
|---|---|---|
| `ingest.py` | Canvas exports → pseudonymised `entries.parquet` + crosswalk | `python3 -m src.qualitative.ingest` |
| `audit.py`  | journal ↔ peer-data linkage audit (incl. §9 template survey) | `python3 -m src.qualitative.audit` |
| `templates.py` | reflection-template classification (used by the audit) | imported by `audit.py` |
| `sample.py` | draw a read batch (pilot / teams) | `python3 -m src.qualitative.sample pilot` |
| `reader.py` | batch → self-contained offline HTML reader | `python3 -m src.qualitative.reader pilot` |

## Generating a read batch

```bash
# 1. sample a batch (writes a text-free spec + manifest under output/qualitative/reader/)
python3 -m src.qualitative.sample pilot                 # 3 hand-picked teams (A0/A1/A2) + 3 suspect
python3 -m src.qualitative.sample teams                 # one batch per analysable cohort
python3 -m src.qualitative.sample teams --cohort 2023_s1

# 2. turn a spec into the reader HTML (embeds the journal text)
python3 -m src.qualitative.reader pilot
python3 -m src.qualitative.reader teams_2023_s1
```

Artefacts land in `output/qualitative/reader/`:

- `batch_<name>.json` — spec consumed by `reader.py` (**text-free**).
- `batch_manifest_<name>.csv` — reviewable manifest, ids + counts, **no text**.
- `team_key_<cohort>.csv` / `pilot_key.csv` — `team_NN` → real team + archetype
  (mean-load argmax) + majority-vote + flag. **The HTML never loads these.** They
  exist only so Jos can un-blind *after* coding.
- `reader_<name>.html` — the reader (contains embedded journal text).

### The `pilot` batch

Three hand-selected teams (handoff-6 amended + Jos 2026-08-04), one per named
archetype, chosen by **mean-load argmax** (see the audit §9 note on why not
majority-vote), spending **zero** anchor-set overlap:

- **A2** — `2024_s1` Team 12 (source-code matrix A2, non-degenerate, Anomalous)
- **A1** — `2024_s1` Team 5 (A1 load 1.0)
- **A0** — `2023_s2` Team 33 (A0 load 0.52, not in the anchor set)

> **Caveat, by design:** the A0 team is from a *different cohort* (`2023_s2`) than
> the A1/A2 teams (`2024_s1`). Both cohorts prompt team dynamics in their
> reflection template (audit §9), but the wording differs. Acceptable for a
> feasibility pilot — we test whether the *judgement is makeable*, not compare
> cohorts — **but this cross-cohort mix must not carry into the main validation.**

### Blinding (rubric §2)

In `teams` mode the reader shows only journal text and pseudonymous
`team_NN` / member `A`–`F` labels. It never renders team names, archetypes
(A0–A3), Typical/Anomalous flags, IWF/Δ/atypicality, or the existing hand
labels — so the journal read stays an independent validation of Step 4.

## Using the reader (for a rater)

1. Double-click `reader_<name>.html` — opens in any browser, fully offline.
2. Enter your rater initials when prompted (used to key your saved progress).
3. Code each entry with the keyboard — the key for each option is shown on the
   chip. Selecting a value auto-advances to the next field, then the next entry.
   - `←` / `→` move between screens · `/` focus notes · `Esc` leave notes.
   - In `teams` mode the team-level panel unlocks once every member entry on the
     screen is coded.
4. Progress **autosaves to the browser** on every keystroke; reopening the same
   file restores exactly where you stopped.
5. Click **Export CSV** at any time. Save the file to `output/qualitative/`.
   Filename: `<batch>_<rater>_<timestamp>.csv`.
6. **Import CSV** restores/merges progress on another machine or from a second
   rater's partial file.

### Export CSV shape

One file, two record types (`record_type` column):

- `entry` rows: `entry_uid, cohort, journal_index, section, team_label,
  member_label, mentions_teammates, discusses_team_process,
  negative_teammate_content, affect_style, concern_rating, notes`.
- `team` rows: `team_label, cohort, within_team_divergence, someone_singled_out,
  singled_out_agreed, team_concern, engagement_visible, team_notes` — the
  **team-level fields are the primary measure**. `within_team_divergence`,
  `singled_out_agreed` and `engagement_visible` are the hypothesis tests (A2
  contested inequality, A0 consensual inequality, A1 engaged-vs-disengaged).
- `extract_check` entries (the 3 short `suspect` files) carry only a free-text
  `notes` field — a sanity check, not part of the coded team set.

The coding schema is defined once in `reader.py` (`CODING_SCHEMA`) and shared by
both modes — change fields there, regenerate, and the UI + CSV follow.
