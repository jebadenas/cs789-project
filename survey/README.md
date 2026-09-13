# Tutor Questionnaire (survey)

Standalone Next.js 16 + Primer app for the tutor validation exercise — separate from the
dashboard. Two-step, per (team, sprint): independent triage, then blind snippet
classification.

## Run
```bash
pnpm install
pnpm dev -p 3001   # http://localhost:3001
```

## Flow
`/` (intro) → `/cases/[caseId]/triage` → `/cases/[caseId]/snippet/[i]` →
`/cases/[caseId]/rationale` → `/cases/[caseId]/submitted` → `/complete`.

Case data is currently synthetic (`src/app/data.ts`); the design is a work in progress
(see `plans/tutor-exercise-draft.md` in the repo). Real journals would be wired in later,
locally (student names).
