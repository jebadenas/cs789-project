# Progress log — research + applications (2026-09-21)

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
- **Per-sprint reliability:** all 11 v1 binaries code reliably per (team, sprint)
  — 86–96% run-to-run over 433 cells, job 16854 (1299 marks, 0 failed). The value
  dynamics (leadership 96%, open_conflict 96%, comms 91%) are the most reliable and fire
  selectively. `docs/qualitative/llm-per-sprint-reliability.md`.
- **Per-sprint 72B summaries: DONE.** `marks_summary/` contains 493 files covering all 5
  cohorts. The dashboard reads them automatically. (Was listed as pending in the Sep-13
  version of this doc; since confirmed complete.)

### Data-quality audit + reliability≠validity (NEW, 2026-09-14)
Reviewing the dashboard evidence surfaced that the per-sprint **marks are reliable but
their cited quotes often are not**: across 348 fired flags (2025_s1), **69% had the 3 runs
return different supporting quotes**, and a minority attach a quote that contradicts the
flag (e.g. `effort_imbalance` fired with a "team is happy/balanced" quote; `core_subgroup_
carried` fired on an even frontend/backend split). Reliability ≠ validity.
- Fixed now (no re-run): glued-text repair (3.6% of journals, centralised in
  `blobs._entries`), member attribution (96.5% of quotes map to one member), multi-quote
  evidence, green positives — see `docs/qualitative/per-sprint-data-quality-findings.md`.
- **Dashboard shows real names** (local tool; via the `anon_id` crosswalk). **Questionnaire
  is fully anonymised** (`src/qualitative/llm/anonymise.py` → 0/634 own-team leaks; emails +
  UPIs stripped) with real anonymised cases fed in (`scripts/gen_survey_data.py`).
- **Evidence-grounded re-run (built, needs cluster auth):** `marking_sprint_v2` (step
  `sprint_v2`, `slurm/journal_sprint_v2.sh`) — a flag fires only with a directly-supporting
  verbatim quote, 1–3 quotes per flag each tagged with its Member, tightened definitions;
  writes `marks_sprint_v2/` for a v1-vs-v2 reliability **and validity** comparison.

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
`marking_sprint`/`marking_sprint_v2` (11 binaries ×3 shuffled), `marking_summary` (72B
per-sprint summary — DONE, 493 files), `sprint_analysis` (consensus + per-flag reliability
+ local summaries), `run` (steps: notes/aggregate/mark/mark_v2/sprint/summarize). Cluster
jobs in `slurm/journal_*.sh`. Analysis scripts in `scripts/`.

### Cluster gotchas (all baked into the slurm scripts)
Host `foscsmlprd01`, user `jbad180`, model on `/data/jbad180`. VPN drops often (re-open the
`ssh -fN` master). Jobs sit in an admin-approval hold. Serve fixes: `CPATH`→extracted
py3.11 headers; `CUDA_HOME`→pip nvidia-cu13 wheel; `VLLM_USE_FLASHINFER_SAMPLER=0`;
`VLLM_ATTENTION_BACKEND=FLASH_ATTN`. Large `hf download` stalls on the proxy — use `wget -c`.

### Next research steps
1. Deepen the **journal-vs-peer mismatch** analysis — characterise where/why they diverge.
2. Recruit tutors + run the validation study (questionnaire app is ready).
3. Run the **per-sprint early-warning pilot** on one cohort (`plans/journal-early-warning.md`
   Phase-2) — needs a cluster run with `marking_sprint_v2`.

---

## Applications

Two **separate** Next.js 16 apps (Primer / GitHub design system), each its own dev server.

### Dashboard — `ui/` (port 3000)
Coordinator view. Routes under `/dashboard/[cohortId]/` — cohort selector on landing page.
Sub-routes: `/sprints/[id]` (full breakdown, clickable stat filters),
`/teams/[id]?sprint=` (profile-style, sprint trajectory strip),
`/queue/[id]` (sprint-level triage queue). Real data for cohort **2025_s1** (24 teams ×
4 sprints), 72B summaries loaded.
- **Data flow (decoupled):** marks → `scripts/gen_dashboard_data.py` → `ui/src/app/dashboard/teams.data.json` + `cohorts.data.json` → `data.ts` imports them. Both JSONs are **gitignored** (student names) — regenerate locally.
- Run: `cd ui && pnpm install && pnpm dev`. See `ui/README.md`.

### Survey / questionnaire — `survey/` (port 3001)
Tutor exercise app. **v2 architecture** — multi-session, non-linear Part 1, resumable Part 2.

**Screen flow:**
```
Intro → Home (contents) → Part 1 hub (case list, any order) → Triage screen
     └→ Part 2 (snippet queue, sequential, Back button) → Complete & export (zip)
```

**Key behaviours:**
- localStorage persistence — survives browser close, resumes exactly where left off.
- Part 1 freely editable until the moment Part 2 is first entered; then locks entirely.
- Part 2: Back button revises the immediately-previous snippet only.
- Journal text rendered with `renderJournalText` — section headers, week dividers, Team
  Dynamics section highlighted; Time Sheet section suppressed; template prompts muted.
- Zip export (JSON + CSV in one download) via JSZip.

**Data:** `survey/src/app/cases.data.json` — **gitignored** (blinded journal content).
Regenerate: `python3 -m scripts.gen_survey_data`. Design docs: `plans/ui-design-brief.md`,
`plans/questionnaire-v2-plan.md`, `plans/questionnaire-v2-design-brief.md`.

### Standalone HTML prototypes (superseded by the apps)
`prototypes/*.html` (gitignored — contain real names) via `scripts/build_dashboard.py`.

### Next app steps
- Wire in non-anonymised data path for the live cohort (see `plans/questionnaire-v2-plan.md` §8).
- Recruit tutors; deploy the questionnaire for the validation study.

---

## Privacy
Never committed: `data/**`, `output/**`, `ui/src/app/dashboard/teams.data.json`,
`ui/src/app/dashboard/cohorts.data.json`, `survey/src/app/cases.data.json`,
`prototypes/*.html`, the crosswalk. Real names live only in gitignored local files. The
dashboard is a local tool (names kept by deliberate decision); research outputs are
name-scrubbed or aggregate.
