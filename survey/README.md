# Tutor Questionnaire (survey)

Standalone Next.js 16 app for the tutor validation exercise — separate from the dashboard.
Single-page, two-phase state machine (no routing):

**Phase 1 — Triage** (all cases): read a sprint's journals, then one 3-way call
(fine / watch / step-in) + optional one-line why. The call is **scroll-gated** — locked
until the tutor has scrolled to the end of the last journal (`NEXT_PUBLIC_REQUIRE_SCROLL`).
**Phase 2 — Snippets** (all passages): each flagged passage shown as a plain blockquote
(no highlight marker), labelled from a uniform 10-option list (8 dynamics + None / Can't
tell, the last two exclusive). The tool's flag is hidden from the tutor, kept in the data.

Blinding is preserved globally: Phase 1 fully precedes Phase 2. On completion the tutor
downloads their answers (**JSON + CSV**, tagged with the tutor id and the hidden scoring
fields) and sends the file back — nothing is transmitted.

## Distributed per-tutor build

The tutor identity is baked in at **build time** (`NEXT_PUBLIC_*` are inlined by Next):

```bash
NEXT_PUBLIC_TUTOR_ID="Tutor B" pnpm build   # one build per tutor
pnpm start -p 3001
# dev: pnpm dev -p 3001   (defaults to "Tutor A")
```

- `NEXT_PUBLIC_TUTOR_ID` — recorded with every answer (default `Tutor A`).
- `NEXT_PUBLIC_REQUIRE_SCROLL` — set `false` to drop the scroll-gate (default on).
- `NEXT_PUBLIC_DEFAULT_THEME` — `dark` to start dark (toggle always available).
- `NEXT_PUBLIC_CASE_LIMIT` — caps how many cases load (default: the full pool). For a
  **quick demo/preview build** that's easy to click all the way through:
  ```bash
  NEXT_PUBLIC_CASE_LIMIT=2 pnpm dev -p 3001
  ```
  Part 1 then has just those 2 cases to triage, and Part 2 only their passages (~2 dozen,
  not ~1,140). This only trims the pool size — everything else (scroll-gate, blinding,
  export) behaves the same. Real per-tutor runs leave it unset.

## Data

Not hand-authored. The pipeline generates it:
```
per-sprint v2 marks → scripts/gen_survey_data.py --v2 → src/app/cases.data.json
```
`cases.data.json` is **gitignored** (real anonymised journal content). Each case = one
(team, sprint): full anonymised journals + flagged passages, each carrying its member,
the tool's flag (`toolFlag`, hidden), and `passage` (the quote expanded to full sentences).
Cohort: 2025_s1 (96 cases, ~1,140 passages — the whole eligible pool).

> **Per-tutor case selection + control passages** come from the sampler (pending the study
> variables in `plans/`), not yet wired — this build loads the full pool.
