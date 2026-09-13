# Team Health — coordinator dashboard

Next.js 16 (App Router) + Primer. A per-sprint view of capstone team health derived from
reflective-journal LLM marks.

## Run
```bash
pnpm install
pnpm dev          # http://localhost:3000  (/ → /dashboard → current sprint)
```

## Routes
- `/dashboard/sprints/[id]` — full breakdown for a sprint; stat cards filter by status.
- `/dashboard/teams/[id]?sprint=k` — profile-style team detail + sprint trajectory strip.

## Data
Not hand-authored. The pipeline generates it:
```
per-sprint marks → scripts/gen_dashboard_data.py → src/app/dashboard/teams.data.json
```
`data.ts` imports `teams.data.json` (which is **gitignored** — it contains student names).
Regenerate with `python3 scripts/gen_dashboard_data.py` from the repo root. `data.ts` keeps
the types + helpers; only the data is swapped. Cohort shown: 2025_s1.

> Note: `AGENTS.md` — this is Next.js 16; read `node_modules/next/dist/docs/` before changing framework code.
