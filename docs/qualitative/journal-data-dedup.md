# Journal data duplication in 2024_s2 — found + fixed

**Date:** 2026-09-09. **Severity:** affects all 43 2024_s2 teams' marking blobs
(frozen v1 **and** v2). Other three study cohorts are clean. Found while validating
the per-sprint blob primitive (`plans/journal-early-warning.md`).

## What was wrong (2024_s2 only)

Two compounding bugs inflated every 2024_s2 team's blob with **repeated journal text**:

- **(A) Parquet row duplication.** `data/journals/processed/entries.parquet` stores
  **241 submissions twice, byte-identical** (2024_s2: 1172 rows / 931 unique; the
  clean cohorts have 0 duplicate rows). The `submission_id` join in
  `blobs._entries` then fans these out.
- **(B) Journal 2 ≡ Journal 3.** In `batch_teams_2024_s2.json`, journal_index **2 and
  3 point at the identical set of 233 submissions** (100% overlap) — the same "Weeks
  4 & 5" file tagged under two indices. So 2024_s2 has **4 real journals, not 5**.

Combined, a member's Weeks-4&5 journal appeared up to **4×** in the blob; other
journals up to 2×. Every one of the 43 teams had duplicate blocks (e.g. team_01:
41 journal blocks, only 29 unique).

## The fix

One row per `(team_label, member_label, submission_id)` in `blobs._entries`, keeping
the **lowest** journal_index:

```python
merged = (merged.sort_values("journal_index")
                .drop_duplicates(["team_label", "member_label", "submission_id"],
                                 keep="first")
                .reset_index(drop=True))
```

Removes (A) the verbatim parquet dups and (B) the spurious journal 3 (same submission
as journal 2). Validated: **0/all teams** now have duplicate blocks; 2024_s2 journal
indices become `[1, 2, 4, 5]`; the clean cohorts (already one submission per journal)
lose only a handful of exact dups and are otherwise unchanged. The raw parquet/batch
are left untouched — the fix is at the load layer.

## Impact on results — RESOLVED (2026-09-10)

2024_s2 was **re-marked (v1 + v2) on the deduped blobs** (job 16655, 129+129 marks),
pulled back, and both downstream results recomputed:

- **WS3 reliability** (`llm-reliability-v2-results.md`): recomputed. The bug had made
  the **v1 baseline** look worse (conflict 54.6→**59.7%**, trajectory 72.3→**73.9%**);
  the **v2** numbers were unchanged (conflict 79.8%, trajectory 64.7%). Conclusion
  unchanged: conflict fixed, trajectory regressed.
- **RQ4 divergence-index headline** (`llm-results.md`, via `scripts/divergence_index.py`):
  recomputed. Still monotonic and significant — Kruskal–Wallis softened from
  **p=0.0035 to p=0.0075**, Silent-vs-Standout from p=0.00056 to **p=0.0013**. The
  reconstruction reproduces the pre-dedup figures exactly on the old marks, so the
  shift is the data fix, not method drift.

Net: the corruption slightly *understated* v1 reliability and slightly *overstated* the
headline's strength; correcting it leaves every substantive conclusion standing. Buggy
2024_s2 marks archived under `output/qualitative/llm/_backup_buggy_2024s2/`. Other
three cohorts were unaffected throughout.

## Reproduce the diagnosis

```
# per-cohort duplicate-row count and journal 2≡3 check
python3 -c "import pandas as pd; d=pd.read_parquet('data/journals/processed/entries.parquet'); \
x=d[d.cohort=='2024_s2']; print(len(x), x.submission_id.nunique())"
```
