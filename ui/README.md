# Team Health — coordinator dashboard

Next.js 16 App Router dashboard — a per-sprint view of capstone team health derived from
reflective-journal LLM marks, across multiple cohorts. Real routes, not client-side state:
every screen is a shareable, bookmarkable, back/forward-able URL.

## Routes

```
/dashboard                                      → redirect to the latest cohort's latest sprint
/dashboard/[cohortId]                           → redirect to that cohort's latest sprint
/dashboard/[cohortId]/sprints/[sprintId]        Sprint breakdown
  ?status=attention|watching|healthy              stat-card filter
/dashboard/[cohortId]/teams/[teamId]            Team detail
  ?sprint=k                                       defaults to the cohort's latest sprint
/dashboard/[cohortId]/queue/[sprintId]          Review queue for that sprint
```

- **Sprint breakdown** — sprint tabs + cohort switcher in the header; stat cards filter the
  feed (a URL param — shareable); teams grouped worst-first (attention → watching →
  healthy), each showing a **trajectory strip** (one bar per sprint); sidebar search (local
  only, not a URL param — see below); a rail with cohort **Movement** and **Most common
  issues**.
- **Team** — identity card (status, members, change) + coordinator-triage control; the
  LLM-written **Summary**, a **Trajectory** strip across sprints (each cell links to that
  sprint), and **Journal evidence** (real verbatim quotes with attribution).
- **Review queue** — the flagged teams for one sprint, each with a triage state (Not
  started / Contacted / Watching / Resolved), filterable, with CSV export.

**What's deliberately *not* in the URL:** theme (light/dark), the sidebar search text, and
triage state — all `localStorage`-backed, per-browser preferences/notes, not shareable
resources. Triage is scoped per cohort (`cohortId:teamId` keys) and synced across the
header's queue-count badge and any triage buttons on the same page via a same-tab custom
event (the native `storage` event only fires in *other* tabs).

## Structure

```
dashboard/
  data.ts                    types + COHORTS + route-lookup helpers (findCohort, findTeam, …)
  lib/
    theme.tsx                 pure/presentational: palette, StatusToken, TrajectoryBars, icons
    helpers.ts                 pure data helpers: statusAt, changeText, headline, …
    client-state.tsx          "use client" hooks: useTheme(), useTriage(cohortId)
  components/                "use client" islands: DashboardHeader, TeamSidebar,
                              TriageButtons, TeamTriagePanel, QueueBoard, ExportQueueButton
  [cohortId]/
    sprints/[sprintId]/page.tsx
    teams/[teamId]/page.tsx
    queue/[sprintId]/page.tsx
```

Pages are Server Components (validate params, 404 via `notFound()`, `generateStaticParams`
pre-renders every cohort × sprint × team combination); only the genuinely interactive bits
(search, triage buttons, theme/cohort switcher) are client components.

## Run
```bash
pnpm install
pnpm dev          # http://localhost:3000  (/ → /dashboard)
```

## Data
Not hand-authored. The pipeline generates it:
```
per-sprint v2 marks → scripts/gen_dashboard_data.py --v2 → src/app/dashboard/cohorts.data.json
```
`cohorts.data.json` is **gitignored** — it contains real student names (this is the local,
coordinator-only tool; `SCRUB` is intentionally off). One entry per cohort
(`{id, label, sprints, teams}` — sprint count varies by cohort, so it's carried per-cohort
rather than assumed constant); each team has a `members` count and a finding per sprint
(status, summary, issues, positives, evidence). Regenerate with
`python3 scripts/gen_dashboard_data.py --v2` from the repo root. `data.ts` keeps the types +
helpers; only the data is swapped.

> `Project` and `Tutor` facts render only if present in the data (not in the pipeline yet).
> Summaries prefer the 72B cluster output (`marks_summary/`) over the 7B stopgap when present.
