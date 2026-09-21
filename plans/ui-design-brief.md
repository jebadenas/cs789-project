# UI design brief — tutor questionnaire + coordinator dashboard

> A complete description of both front-ends, written to hand to **Claude Design** for
> refinement. Covers what exists today, the **target** design (including the agreed
> changes not yet built), the content/vocabulary each screen uses, and the research
> constraints that must not be designed away.
>
> Two separate Next.js 16 + Primer apps:
> - **`survey/`** — the tutor **questionnaire** (the live research instrument).
> - **`ui/`** — the coordinator **dashboard** (the demonstration artifact).
>
> Status key in this doc: **[built]** = in the current app · **[target]** = agreed
> change, not yet built · **[later]** = deferred / open.

---

# PART 1 — Tutor questionnaire (`survey/`)

## 1.1 What it is and who uses it

A tutor reads anonymised capstone-team journals **one sprint at a time** and answers two
tasks, so we can compare their human read against an automated tool. Each participant is a
**fresh capstone-experienced tutor** (not the team's own tutor). Delivered as a
**distributed per-tutor build**: each tutor gets their own copy with their identifier and
their assigned cases baked in; there is **no server**; answers **export to a file** the
tutor sends back.

**A "case" = one (team, sprint).** A tutor is assigned two pools:
- a small **triage** set (~5–8 cases) — the slow full read;
- a larger **snippet** set (~40–50 cases) — quick line-labelling; **includes** the triage
  cases plus many snippet-only ones, with ~25% control (non-flagged) snippets mixed in.

## 1.2 Research constraints (do not design these away)

1. **Order-lock / blinding.** The tutor's triage call must be recorded **before** they see
   any highlighted lines or any hint of what the tool thought. **[target]** enforce this
   globally: **Phase 1 (all triage) fully precedes Phase 2 (all snippets).**
2. **Forward-only, locked answers.** Once a step is submitted it cannot be edited; the app
   moves on. No back-navigation into answered steps. **[built]**
3. **Blind labelling.** In the snippet task the tutor never sees the tool's label; agreement
   is scored later as "the tool's flag is among the tutor's ticks." The tool's flag and the
   control/non-control status travel in the data but are **never shown**. **[target data]**
4. **Confidential content.** Journals are anonymised (Member A/B/…) but are real student
   writing — the intro must state confidentiality and "don't copy/share." **[built]**
5. **Per-tutor identity.** Every answer is tagged with the baked-in tutor id. **[target]**

## 1.3 Screen flow (target)

```
Intro
  └─ Phase 1: Triage        (repeat for each of the ~5–8 triage cases)
        read journals → 3-way call → optional one-line "why"
  └─ Phase 2: Snippets      (repeat for each snippet across the ~40–50 cases)
        highlighted line shown in its paragraph → tick all that apply
  └─ Complete → export answers file
```

Current build interleaves triage+snippets **per case** in one linear list; the target
**separates them into two global phases**. Everything below marks what changes.

## 1.4 Screen: Intro **[built, minor edits]**

- Eyebrow "Tutor questionnaire"; H1 "Review anonymised team journal cases".
- Lede: you'll read cases in two parts — first make your own call, then label snippets.
- Three info cards: **Confidentiality** · **Time** (a few minutes per case) · **Forward
  only** (submitted answers lock).
- Primary button "Start questionnaire".
- Footer note: responses stay local / are exported at the end. **[target: reflects export,
  not "not saved anywhere"]**
- **[target]** Optionally surface the tutor's baked-in id ("You are Tutor A") so a
  returned file is traceable.

## 1.5 Screen: Phase 1 — Triage read

For each triage case:

- **Header:** eyebrow "Case N of M", title "Review the journals", progress bar, progress
  text "Part 1 · Triage". **[target: progress reflects the triage-phase count, not a
  per-case 2+snippets total]**
- **Journals block:** one card per member — `Member A` heading + full journal text for that
  sprint. Scannable, readable measure (~65–75ch), clear separation between members.
- **The question (1a):** "How would you respond to this team?" — one choice, required:
  - **They seem fine** — I wouldn't do anything.
  - **I'd keep an eye on them** — something to watch, not act on yet.
  - **I'd step in** — reach out / intervene.
- **Guidance:** judge team **functioning/health**, not product quality.
- **(1b) optional one-line "why"** free-text.
- **Lock note:** "You cannot edit this answer after continuing." → **Continue**.

Design notes: the three choices are the load-bearing control — make them large, obviously
single-select, easy to read. The journals are long; the choice must stay reachable
(sticky footer or a clear anchor) without letting the tutor answer before reading.

## 1.6 Screen: Phase 2 — Snippet labelling

For each snippet (a flat queue across the tutor's snippet cases):

- **Header:** eyebrow "Case N of M" (or a snippet counter), title "Label this line",
  progress "Part 2 · Snippet i of n".
- **The snippet in context** **[target — key change]:** show the line **inside its
  surrounding paragraph**, the line marked as a **neutral locator** ("this is the line to
  judge"), *not* an alarming highlight. See §1.6a — this is anti-bias-critical. Non-
  overlapping windows: no other flagged line appears inside the shown context. *(How the
  paragraph is trimmed/rendered is the main thing to nail in Claude Design.)* Current build
  shows the bare line only.
- **The question:** "Which of these does this passage indicate? Tick all that apply."
  **All ten options styled identically** in one uniform list (see §1.6a). Select-all-that-
  apply; the last two are **exclusive** (ticking one clears the other eight):
  - Open conflict / interpersonal tension
  - Uneven workload / effort imbalance
  - A member under-contributing or disengaged
  - Communication breakdown
  - Leadership problem or vacuum
  - A core few carrying the team
  - A single member singled out (weakest or standout)
  - Mutual support / team working well
  - **None** *(exclusive)* — doesn't indicate any of these
  - **Can't tell** *(exclusive)* — ambiguous even with context
- **Validation:** at least one option required; inline error + focus to the fieldset.
- **Lock note** → **Continue** (last snippet of a case → "Submit case").

Design notes: the marked line must be findable but calm; the option list must be uniform.
Keep the tool's opinion completely absent.

### 1.6a Anti-bias rules (research-critical — do not design these away)

The snippet task *measures* whether tutors agree with the tool, and the **None** rate is
the tool's false-flag rate. So the presentation must not push tutors toward finding a
problem, nor toward/away from any option. Two rules:

**1. The line marker is a locator, not a verdict.**
- You must mark *which* line to judge (that's the task) — but mark it as neutrally as
  possible: a **subtle underline / thin left-rule in a neutral tone**. **No** marker-pen
  fill, **no** red/amber (reads as alarm), **no** label chip (also risks leaking the flag).
  → of the four sketched options, pick **"underline + weight, no fill"**, not the marker-pen.
- **Flagged and control snippets are marked *identically*.** ~25% of snippets are controls
  (nothing flagged), and they carry the same marker. If marking induces a "find a problem"
  bias, the controls' None rate reveals it — the bias becomes *measured*, not assumed away.
  This only works if the two are visually indistinguishable.

**2. All ten options look the same.**
- One **uniform list**, identical styling — **no divider, no group, no different weight**
  for None / Can't tell. Any visual differentiation nudges how often they're picked, and
  None is a measurement.
- None and Can't tell differ **only in behaviour**: they're **exclusive** — ticking one
  clears the other eight. Communicate that through the *interaction* (auto-clear) plus one
  short instruction line ("None / Can't tell can't be combined with the others"), never
  through styling.
- Option order is fixed and identical for every tutor (so it's a constant, not a
  confound); None/Can't tell sit last as the natural "otherwise" options.

### Option definitions (for consistent labelling — could be a hover/aside)

| Option | Means |
|---|---|
| Open conflict / tension | Friction beyond ordinary task/technical disagreement. |
| Uneven workload | Workload clearly uneven *in amount* — one/two did much more. |
| Member under-contributing | ≥1 member not pulling their weight / disengaging / missing their part. |
| Communication breakdown | Sustained poor communication — not a one-off. |
| Leadership problem/vacuum | A leader ineffective/bypassed, or no one coordinating. |
| A core few carrying | A 2–3 person core did the substantive work; others peripheral. |
| A single member singled out | One identifiable member named as notably weakest **or** standout. |
| Mutual support / working well | Members supported each other, or simply worked well. |
| None | Doesn't indicate any of the above (e.g. ordinary tech disagreement). |
| Can't tell | Genuinely ambiguous even with context. |

## 1.7 Screen: phase transition + completion

- **[target]** A brief **"Part 1 complete → starting Part 2"** interstitial when crossing
  from triage into snippets, so the shift in task is explicit.
- **Case submitted** confirmation (per case) → continue to next. **[built]**
- **Complete / Thank you** screen. **[built]**
- **[target] Export step:** on completion, produce a **downloadable answers file** (all
  triage + snippet responses, each with the hidden tool-flag/control fields for scoring,
  tagged with the tutor id) that the tutor sends back. This is the data-capture mechanism.

## 1.8 Cross-cutting UI qualities (already good — preserve)

- Progress bar with `role="progressbar"` + aria values; heading focus on step change.
- Never signal state by colour alone; validation uses `role="alert"` + focus move.
- Responsive to ~400px; readable measure; large tap targets for the radio/checkbox cards.
- Calm, low-chrome, "one task per screen" feel — this is a careful reading task, not a
  dashboard.

---

# PART 2 — Coordinator dashboard (`ui/`)

## 2.1 What it is and who uses it

A **coordinator-facing** overview of capstone team health, derived from an LLM's marks of
reflective journals. A coordinator oversees ~40 teams and can't read every journal; this is
the at-a-glance triage. **Not** tutor-facing. It is the **demonstration artifact** for the
dissertation, not the live study instrument. Largely **[built]**; work remaining is data
quality (better summaries), not new screens.

## 2.2 Core model (drives everything visual)

- **Health status**, three levels, each with a tone:
  - **Requires attention** (danger) · **Needs watching** (warning) · **Healthy** (good).
- **Unit = one (team, sprint).** A team has a finding per sprint; sprints are Sprint 1–4.
- Each finding carries: a **status**, a one-paragraph **summary**, **issue** tags,
  **positive** tags, and **evidence** — flagged items each with one or more **verbatim
  journal quotes** attributed to a **blinded member label** ("Member C").
- Status can **change** sprint-to-sprint (improved / worsened / unchanged) — shown as
  trajectory.
- Data is **pipeline-generated** (`gen_dashboard_data.py`), never hand-authored; the JSON
  is git-ignored (real names). Cohort shown: 2025_s1.

## 2.3 Screen: Cohort overview (`/dashboard`) **[built]**

- **Top bar** with the current sprint label.
- **Head:** eyebrow "Cohort overview", H1 "Team health", subtitle "snapshot of N teams from
  the most recent journal triage".
- **Stat row:** four cards — **Total teams**, then **Attention / Watching / Healthy** counts.
- **Two-panel grid:**
  - *Cohort health over time* — sprint tabs + a **trend chart** of the status mix across
    sprints.
  - *Latest snapshot* — "X teams to review", short guidance ("start with attention, then
    watching"), primary link "View latest sprint".
- **Browse sprint snapshots:** a list, one row per sprint, each showing
  "a attention · b watching · c healthy", linking into that sprint.

## 2.4 Screen: Sprint breakdown (`/dashboard/sprints/[id]`) **[built]**

Three-column layout:

- **Left — Teams sidebar:** quick navigation across teams for this sprint.
- **Main pane:**
  - Head (eyebrow "Sprint snapshot", H1 sprint label, "Full breakdown · N teams") + sprint
    tabs.
  - **Stat cards act as filters:** Total / Attention / Watching / Healthy; clicking one
    filters the feed to that status (active card highlighted; URL `?status=`).
  - **Grouped feed** in fixed order Attention → Watching → Healthy. Each group has a heading
    + count; each **team card** shows the team name (links to team detail), a **status
    badge**, the **change vs previous sprint** ("Improved/Worsened/Unchanged from …"), and a
    "View details" link.
- **Right rail:** supporting context (e.g. the teams most needing review).

## 2.5 Screen: Team profile (`/dashboard/teams/[id]?sprint=k`) **[built]**

Profile-style, two columns:

- **Left identity card:** back link to the sprint; team name + "Capstone team"; **status
  badge**; facts (Viewing = sprint, Change vs previous, "Sprints flagged: X of Y"); **signals
  this sprint** — issue tags (and positive tags if any), or an empty state.
- **Main column:**
  - **Journal summary** — the LLM-written paragraph for this sprint (anonymous by
    construction). *(This is what the pending 72B cluster run improves.)*
  - **Sprint trajectory strip** — one cell per sprint, colour-coded by status, current
    sprint highlighted, each cell links to that sprint's view; a small legend
    (Attention/Watching/Healthy).
  - **Journal evidence** — cards, one per flagged issue: the issue name + one or more
    **verbatim quotes**, each attributed to a blinded member ("— Member C"); positive
    signals styled distinctly; empty state when no evidence.

## 2.6 Cross-cutting UI qualities (preserve)

- Consistent status vocabulary + tone colours everywhere (badge, stat card, trajectory
  cell, evidence). Never colour-only — always pair with the label.
- Coordinator-triage feel: fast scanning, worst-first ordering, counts and deltas prominent.
- Quotes are the evidence — legible, clearly separated, attribution visible.
- Responsive; the three-column sprint view must degrade gracefully to narrow widths.

---

# PART 3 — What to focus on in Claude Design

- **Questionnaire is the priority** (it's the real instrument). The three design problems
  worth the most attention: (1) the **triage read** screen — long journals + a decision that
  must stay reachable but not pre-emptible; (2) the **snippet-in-context** screen — the
  neutral line-marker and the uniform ten-option list (**anti-bias rules §1.6a**); (3) the
  **two-phase flow** + completion/export.
- **Dashboard is essentially done** — refine polish/hierarchy if you like, but no new
  screens are needed; its open work is data quality, not design.
- Both apps already handle accessibility and responsiveness reasonably — keep those
  properties through any redesign.
