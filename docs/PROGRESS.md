# Progress log — research + applications (2026-09-13)

A single "where we are / how to pick it back up" note spanning the two strands: the
**research** (does a journal-reading LLM surface team trouble the peer scores miss?) and
the **applications** (a coordinator dashboard + a tutor questionnaire). British/NZ spelling.

---

## Research

### Confirmed
- **RQ4 headline (clean data):** a journal-coded divergence index rises across the peer
  cascade (Silent→Contested→No-standout→Standout), Kruskal–Wallis H=12.0, p=0.0075. The
  journals independently recover the cascade. `docs/qualitative/llm-results.md`.
- **Whole-project reliability (WS1/WS3):** binary flags 80–98% across 3 shuffled runs;
  `conflict_handling` fixed by a gate+follow-up rewrite (55→80%), `trajectory` did not
  improve (report gate-only). `docs/qualitative/llm-reliability-diagnosis.md`,
  `llm-reliability-v2-results.md`.
- **Per-sprint reliability (NEW):** all 11 v1 binaries code reliably per (team, sprint)
  — 86–96% run-to-run over 433 cells, job 16854 (1299 marks, 0 failed). The value
  dynamics (leadership 96%, open_conflict 96%, comms 91%) are the most reliable and fire
  selectively. Sparsity worry disproven. `docs/qualitative/llm-per-sprint-reliability.md`.

### The headline direction: journals vs peer scores DON'T MATCH (blind spot)
Peer assessment measures *contribution*; it is structurally blind to a team that
contributes evenly yet is falling apart (conflict / comms / leadership). Journals see that.
- **Preliminary evidence:** per-sprint, ~**65%** of the (team,sprint) cells the journals
  flag for conflict/comms/leadership look **fine on peer contribution** (robust 58–72%
  across thresholds). Mapping Session k↔Sprint k validated (85% same-construct agreement
  when peer flags a freeloader). `scripts/blind_spot.py`, `plans/dashboard-study-design.md` §11.
- **To push further (open thread):** characterise *where and why* journals and peer scores
  diverge — the asymmetry (journals over-flag mild imbalance the numbers miss), which
  dynamics diverge most, whether divergence predicts a poor team mark. This mismatch IS the
  contribution; deepen it.

### The study (designed, not run)
`plans/dashboard-study-design.md` + `plans/tutor-exercise-draft.md`. Fresh tutors,
retrospective, per (team, sprint): **(1)** independent triage (fine/watch/step-in), then
**(2)** blind snippet classification. Two analyses: A faithfulness (does the LLM read like
a human — validity), B the blind-spot value. Ground truth = tutor concern; **validity of
the flags comes from this study, not the blind-spot cross.**

### Open decisions / supervisor asks
Peer baseline quantity + threshold; confirm Session↔Sprint pairing; raw team marks;
ethics scope for retrospective tutor reading. (`plans/dashboard-study-design.md` §9.)

### Pipeline (code)
`src/qualitative/llm/`: `blobs` (per-sprint blob), `marking`/`marking_v2` (whole-project),
`marking_sprint` (11 binaries ×3 shuffled), `marking_summary` (72B per-sprint summary —
built, NOT yet run on cluster), `sprint_analysis` (consensus + per-flag reliability + local
summaries), `run` (steps: notes/aggregate/mark/mark_v2/sprint/summarize). Cluster jobs in
`slurm/journal_*.sh`. Analysis scripts in `scripts/`.

### Cluster gotchas (all baked into the slurm scripts)
Host `foscsmlprd01`, user `jbad180`, model on `/data/jbad180`. VPN drops often (re-open the
`ssh -fN` master). Jobs sit in an admin-approval hold. Serve fixes: `CPATH`→extracted
py3.11 headers; `CUDA_HOME`→pip nvidia-cu13 wheel; `VLLM_USE_FLASHINFER_SAMPLER=0`;
`VLLM_ATTENTION_BACKEND=FLASH_ATTN`. Large `hf download` stalls on the proxy — use `wget -c`.

### Next research steps
1. Run the **72B per-sprint summaries** (`sbatch slurm/journal_summary.sh`, ~433 calls),
   pull `marks_summary/` back → dashboard swaps to them automatically.
2. Deepen the **journal-vs-peer mismatch** analysis (above).
3. Recruit tutors + run the validation study.

---

## Applications

Two **separate** Next.js 16 apps (Primer / GitHub design system), each its own dev server.

### Dashboard — `ui/` (port 3000)
Coordinator view. `/` → `/dashboard` → current sprint. One page type: `/dashboard/sprints/[id]`
(full breakdown, clickable stat filters) + `/dashboard/teams/[id]?sprint=` (profile-style,
sprint trajectory strip). Real data for cohort **2025_s1** (24 teams × 4 sprints).
- **Data flow (decoupled):** marks → `scripts/gen_dashboard_data.py` → `ui/src/app/dashboard/teams.data.json` → `data.ts` imports it. The JSON is **gitignored** (student names) — regenerate locally.
- Run: `cd ui && pnpm install && pnpm dev`. See `ui/README.md`.

### Survey / questionnaire — `survey/` (port 3001)
Standalone tutor exercise: `/` intro → `/cases/[caseId]/triage` → `/snippet/[i]` →
`/rationale` → `/submitted` → `/complete`. Currently synthetic case data. Design to be
finished later. Run: `cd survey && pnpm install && pnpm dev -p 3001`. See `survey/README.md`.

### Standalone HTML prototypes (superseded by the apps)
`prototypes/*.html` (gitignored — contain real names) via `scripts/build_dashboard.py`.

### Next app steps
Swap in 72B summaries when ready; finish the questionnaire design; (optional) wire all four
cohorts / a cohort selector into the dashboard.

---

## Privacy
Never committed: `data/**`, `output/**`, `ui/src/app/dashboard/teams.data.json`,
`prototypes/*.html`, the crosswalk. Real names live only in gitignored local files. The
dashboard is a local tool (names kept by deliberate decision); research outputs are
name-scrubbed or aggregate.
