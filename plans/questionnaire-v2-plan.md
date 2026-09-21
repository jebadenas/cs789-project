# Questionnaire v2 — implementation plan

> Engineering plan for the changes agreed 2026-09-19 (see memory
> `questionnaire-live-tool-pivot` / this session). Companion doc for a design handoff:
> `questionnaire-v2-design-brief.md`. Not yet built — this is the plan.

## 1. What's changing and why

The questionnaire stops being purely a blinded retrospective validation instrument and
becomes **tutors' real journal-reading interface for their own live cohort** — they read
inside our tool (as they need to anyway) and answer the study's triage/snippet questions
while doing it, so the journals get read once. Marking itself stays in whatever tool they
already use. Full reasoning in the memory doc; settled, not re-litigated here.

That reframe is what's driving every UX change below: this now has to survive being used
across multiple real sessions (open it, work for 20 minutes, close the laptop, come back
tomorrow) rather than one sitting.

## 2. Screen map (three levels)

```
Intro (confidentiality, "Start")
  -> Home / Contents            <- persistent, reachable from anywhere (header link)
       - Part 1 - Triage        [n of N done]                  -> Part 1 case hub
       - Part 2 - Snippets      [locked until Part 1 is done]  -> continue queue
       - Complete & export      [visible, locked until both done]
  -> Part 1 case hub            <- one row per (team, sprint) case; read/answered state;
                                    click ANY case in ANY order
       -> Triage screen (existing case-detail UI, now also an EDIT view for answered
          cases) -> submits back to the Part 1 case hub, not auto-advance to "next"
  -> Part 2 queue               <- flat; "continue from where you left off"; no jump-to;
                                    auto-advances snippet -> snippet within a session
  -> Complete & export
```

Dropped: the old standalone "Part 1 complete, Part 2 starts now" transition screen — Home
naturally shows Part 2 unlocking, so a dedicated interstitial is redundant.

## 3. State model

Current (`survey/src/app/questionnaire.tsx`): one flat `State` with
`phase: "intro"|"triage"|"transition"|"snippet"|"complete"`, a **sequential index**
(`triageIdx`, `snippetIdx`) into the case/snippet arrays, `sessionStorage`.

New:
```ts
type Phase = "intro" | "home" | "part1-hub" | "triage" | "snippet" | "complete";

type State = {
  phase: Phase;
  activeCaseId: string | null;      // which case the "triage" screen is showing
  part1Locked: boolean;             // true from the first moment Part 2 is entered
  answers: {
    triage: Record<string, TriageRecord>;   // keyed by caseId, not a sequential index —
                                             // this is what makes Part 1 non-linear and
                                             // makes "answered?" a map lookup, not a
                                             // position comparison
    snippets: Record<string, SnippetRecord>; // keyed by snippetId
  };
  snippetCursor: number;   // index of the first UNANSWERED snippet in the flat queue —
                            // recomputed from `answers.snippets`, not hand-tracked, so it
                            // can't drift out of sync
};
```

Part 1 "progress" (`n of N done`) = `Object.keys(answers.triage).length` vs total cases.
Part 2 likewise from `answers.snippets`. No separate progress counters to keep in sync.

## 4. Persistence

- `sessionStorage` → **`localStorage`** (the whole reason for this ask — must survive
  quitting the browser, not just the tab).
- Same per-tutor key scheme as now (`cs789-survey-<tutor-id>`), so a per-tutor build still
  can't collide with another tutor's saved state if somehow run on a shared machine.
- On load: read `localStorage`; if `phase` was `"triage"` or `"snippet"` with an
  `activeCaseId`/cursor, land there directly (true resume) rather than bouncing through
  Home — but Home is always one click away regardless.

## 5. Editability rules

- **Part 1**: freely editable (re-open any answered case from the hub, change the call,
  resave) **until `part1Locked` flips true** — which happens the first time the tutor
  enters Part 2. Once locked, part1-hub renders answered cases as view-only (can still
  read the journals + see the saved answer, can't change it) — same "locked" language as
  today, just triggered by phase instead of by "did you click continue."
- **Part 2**: **open question, not yet decided** — you confirmed editability in general,
  but Part 2 has no jump-to-a-specific-item UI by design ("you just continue"). Without
  *some* navigation back, "editable" has nothing to act on. I'd suggest a plain
  **Back button** (revise the immediately-previous snippet, single step, no arbitrary
  jump) as the minimal thing that satisfies both constraints — flagging this for the
  design brief rather than assuming it.

## 6. New/changed components

| Component | Status |
|---|---|
| `HomeHub` | **new** — the 3-tile contents page |
| `Part1CaseHub` | **new** — per-case list, read/answered state, click any order |
| `TriagePage` | **modified** — gains an edit mode (pre-filled, re-savable) instead of write-once; drop the `IntersectionObserver` scroll-gate entirely |
| `SnippetPage` | **modified** — valence-grouped option layout (spacing only, see design brief); optional Back button per §5 |
| `CompleteExportPage` | **modified** — zip export instead of two separate JSON/CSV downloads |
| Header | **modified** — persistent "Home" link, visible on every screen |

## 7. Export: zip instead of two separate downloads

No backend, so this needs a client-side zip library — **JSZip** (`pnpm add jszip` in
`survey/`) is the standard choice, MIT-licensed, no server round-trip. Build the same
JSON payload and CSV rows already generated, write both into one `JSZip` instance, trigger
one `.zip` download. Small, contained change to the existing `onExportJson`/`onExportCsv`
handlers — merge them into one `onExportZip`.

## 8. Explicitly deferred (separate tasks, not this round)

- **Journal layout fidelity** — real fix needs structural extraction from the original
  `.docx`/`.pdf` files (`data/journals/raw/`, confirmed still present), not more regex
  cleanup on the already-flattened text. Bigger, separate pipeline task.
- **Live-cohort, real-name data pipeline** — `gen_survey_data.py` currently anonymises
  (`Member A/B/C`) and reads from a frozen historical cohort's marks. The live-tool use
  case needs a **non-anonymised** path (mirroring `gen_dashboard_data.py`'s `SCRUB=False`)
  pointed at whatever the **current, in-progress** cohort's journal ingestion produces —
  not the same thing as pointing at a different value of `COHORT` in the existing script,
  since "current cohort" implies data that's still arriving, not a finished batch. This is
  real Python/data-pipeline work, independent of the UI rebuild below — **the UI changes
  in this plan can be built and tested against the existing (anonymised, historical)
  `cases.data.json` in the meantime**, since the UI doesn't care what the underlying case
  data looks like, only that it conforms to the same shape.

## 9. Open questions before/while building

1. Part 2 Back-button — confirm or propose an alternative (§5).
2. Does "Home reachable at any point" need an explicit confirm-dialog when leaving an
   **unsaved** in-progress triage read (journals scrolled but not yet submitted), or is
   silently discarding the unsaved read fine? Nothing is lost that was ever saved either
   way — just flagging the UX choice.
3. Live-cohort pipeline (§8) — when does that become the priority, relative to this UI
   round? Not blocking the UI build, but worth sequencing consciously.
