# Questionnaire v2 — design handoff

> New/changed screens only, for Claude Design. This is a **delta** on top of the original
> `ui-design-brief.md` §1 (which is still the source of truth for anything not mentioned
> here — the option vocabulary, colour tokens, journal-card styling, the "locked after
> continuing" language, accessibility rules). Companion engineering doc:
> `questionnaire-v2-plan.md`. Status tags: **[new]** = doesn't exist yet · **[modify]** =
> changes an existing screen · **[unchanged]** = carries over as-is, noted for context.

## Why (one line for context, not to re-litigate)

The questionnaire is no longer only a one-sitting research exercise — tutors will use it
as their actual journal-reading interface for their own live cohort, across multiple
sessions (open it, work a while, close the laptop, come back tomorrow). Every change below
follows from that: it has to be resumable, non-linear, and forgiving of mistakes.

---

## 1. Home / Contents **[new]**

The book's table-of-contents page. Sits between Intro and everything else, and is
**reachable from anywhere** via a persistent header link (see §5) — this is the "go back
to home" + "resume where I left off" screen combined.

Three tiles/rows, always visible in this fixed order:

1. **Part 1 — Triage** — progress ("n of N cases done"). Always open. Click → Part 1 case
   hub (§2).
2. **Part 2 — Snippets** — progress ("n of N passages done") once unlocked. **Hard-locked**
   or until every Part 1 case has an answer — locked, not just discouraged; render it
   visibly disabled/greyed with a short reason ("Unlocks once Part 1 is complete"), not a
   clickable dead end. Click when unlocked → jumps straight into the Part 2 queue at the
   tutor's current position (no intermediate hub screen — see §3).
3. **Complete & export** — visible from the start (so the destination is never a surprise),
   locked until both parts are fully done, same locked/disabled treatment as #2 until then.
   Click when unlocked → Export screen (§4).

Design notes: this needs to read at a glance — a tutor opening the app mid-project should
immediately see "where am I, what's left." Progress counts matter more here than anywhere
else in the app. Keep it calm/uncluttered — three items, not a dashboard.

## 2. Part 1 case hub **[new]**

The per-case list *inside* Part 1 — one row per (team, sprint) case assigned to this
tutor. **Non-linear**: click any case, in any order, at any time (until Part 1 locks —
see §3).

Each row shows: team/sprint label, a status (not started / answered), and — once
answered — the saved triage call as a quick-glance summary (e.g. the chosen response's
short label). Clicking:
- An **unanswered** case → the existing triage/read screen (§3), fresh.
- An **answered** case, *before* Part 1 locks → the same screen, **pre-filled and
  editable** — this is now an edit view, not a one-shot form. Label the action
  accordingly ("Save changes", not "Continue").
- An **answered** case, *after* Part 1 has locked (i.e. Part 2 has been entered) → a
  **read-only** view — journals still readable, the saved answer visible, no inputs.

## 3. Triage screen **[modify]**

Same core layout as before (journals on the left, the 3-way call + optional "why" on the
right) with two changes:

- **No scroll-gate.** Drop "locked until you have scrolled to the end of the last
  journal" entirely — the three response options are live/clickable from the moment the
  screen loads. (This was our own proxy for "read carefully"; it doesn't actually
  guarantee reading and it fights the real workflow — tutors know how to read a journal.)
- **Submitting returns to the Part 1 case hub**, not automatically to "the next case" —
  there is no fixed "next" anymore, the tutor picks.

Global rule carried over unchanged and still load-bearing: **Part 1 as a whole locks the
instant Part 2 is entered for the first time** — not per-case, the whole part, all at
once. That's what still guarantees a triage call is never revised with knowledge of what
Part 2 shows.

## 4. Snippet screen **[modify]**

Same core layout (passage in context + the option list) with one visual change:

- **Group the ten options by valence — negative / neutral / positive — using spacing
  only.** No colour-coding, no different font-weight or size between groups, no group
  labels that imply one group matters more than another. This is a scanability aid, not
  an emphasis change — the anti-bias rule from the original brief (§1.6a: None/Can't-tell
  must stay visually identical to every other option, since their pick-rate is itself a
  measurement) still applies in full **within** each group and **across** groups. If in
  doubt, a slightly wider gap between clusters is enough; anything that reads as "this
  cluster is less important" is too much.

  Needs a decision on where the trickier options sit: *"a core few carrying the team"*
  and *"a single member singled out"* aren't cleanly negative or positive — pick a
  grouping and apply it consistently (I'd lean neutral for both, but call it out plainly
  wherever it ends up so it's a visible decision, not an implied one).

Open question to resolve in this design pass, not before: **should there be a "back"
affordance** to revise the immediately-previous snippet? Part 2 deliberately has no
jump-to-a-specific-passage navigation, so "editable" (which was agreed) currently has
nothing to act on without at least a single-step back. See `questionnaire-v2-plan.md` §5.

## 5. Persistent Home link **[new]**

A small, always-visible header element (every screen except the intro) — "Home" or
similar — that returns to §1 from anywhere, including mid-journal-read or mid-snippet.
This is what makes "quit and resume tomorrow" actually usable rather than theoretical.

## 6. Export screen **[modify]**

Same completion screen as before, but the two separate "Download answers (JSON)" /
"Download answers (CSV)" buttons become **one** "Download answers (.zip)" — a single zip
containing both files. Copy should say so plainly (tutors shouldn't need to guess what's
inside).

---

## What did *not* change (carried from the original brief, still true)

- The full option vocabulary and definitions (§1.6 of `ui-design-brief.md`).
- Journal-card styling, the "your answer locks after continuing" framing (still true
  within a case, just triggered differently now — see §2/§3 above).
- Accessibility baseline: focus management on screen change, `role="alert"` +
  focus-move on validation errors, responsive to ~400px, never colour-only.
- Blinding: the tutor never sees the tool's flag on a snippet, still true, unaffected by
  any of the above.
