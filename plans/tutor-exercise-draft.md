# Tutor exercise — DRAFT v0.1 (to refine)

> The instrument for the validation study in `dashboard-study-design.md`. This is a first
> draft to react to, not a final form. Snippet examples here are **invented** for
> illustration — real snippets come from the dashboard and carry real names (kept local).
>
> **Unit = one (team, sprint)**, not a whole team (a full team is ~1.5 h of reading; one
> sprint is ~25 min). Two parts per cell, in this order (order is load-bearing — see §B):
> **Part 1 — independent triage. Part 2 — blind snippet classification.** The parts are
> decoupled: Part 2 runs broad and cheap; Part 1 (the read) runs on a small targeted set
> (~5-8 cells per tutor).

---

## PART A — what the tutor sees

### Intro (shown once, up front)

> Thanks for helping. You'll look at student project teams **one sprint at a time**. For
> each, you'll read that sprint's journals and answer two short things: first, how you'd
> respond to the team; then, a few highlighted lines to label. There are no right answers —
> we're comparing your read to an automated tool's. Each sprint takes about **25 minutes**.
> The journals are confidential — please don't share or copy anything from them.

### Part 1 — Your read of the team *(before you see any highlights)*

Read **this sprint's** journals for the team, then:

**1a. Based only on this sprint's journals, how would you respond to this team?**
- ○ **They seem fine** — I wouldn't do anything.
- ○ **I'd keep an eye on them** — something to watch, not act on yet.
- ○ **I'd step in** — reach out / intervene.

**1b. (optional) In one line, why?** `__________________________________`

> Judge the team's **functioning / health** — how they're working together — *not* how
> good their final product or likely grade is. A strong project can hide a struggling team,
> and a shaky project can come from a perfectly healthy one.

### Part 2 — Labelling highlighted lines *(now the highlights appear)*

For each highlighted passage, shown **in the surrounding text** so you have context:

**Which of these does this passage indicate? (tick all that apply)**
- ☐ Open conflict / interpersonal tension
- ☐ Uneven workload / effort imbalance
- ☐ A member under-contributing or disengaged
- ☐ Communication breakdown
- ☐ Leadership problem or vacuum
- ☐ A core few carrying the team
- ☐ A single member singled out (the weakest, or the standout)
- ☐ Mutual support / the team working well
- ☐ **None** — this doesn't really indicate any of these
- ☐ **Can't tell** without more context

*(You are not shown what the tool thought — we want your own read.)*

#### Worked examples (illustrative)

**Ex. 1** — context shown, highlight in ⟦ ⟧:
> "Sprint 3 was rough on scheduling. ⟦I ended up doing most of the backend myself over the
> weekend because two of the others hadn't started their parts.⟧ It worked for the demo but
> the split wasn't fair."
→ a reasonable answer: *Uneven workload* **and** *A member under-contributing*.

**Ex. 2**:
> "We'd been tense for a couple of weeks. ⟦It came to a head in the meeting — two members
> started arguing and one walked out; it wasn't about the code any more.⟧ We talked it
> through the week after."
→ *Open conflict / interpersonal tension*.

**Ex. 3** *(the "None" case — this is the point of the option)*:
> "⟦We disagreed about whether to use React or Vue and debated it for a while⟧ before
> settling on React and moving on."
→ *None* — ordinary task disagreement, not a team-dynamics problem. (If the tool had
tagged this as conflict, this is how we'd catch that false flag.)

### The option definitions (so labelling is consistent)

| Option | Means |
|---|---|
| Open conflict / interpersonal tension | Friction, arguments, or tension **beyond** ordinary task/technical disagreement. |
| Uneven workload / effort imbalance | Workload clearly uneven *in amount* — one or two did much more. |
| A member under-contributing | ≥1 member not pulling their weight / disengaging / repeatedly missing their part. |
| Communication breakdown | Sustained poor communication (unanswered messages, people out of the loop) — not a one-off. |
| Leadership problem or vacuum | A leader ineffective or bypassed, or no one leading/coordinating. |
| A core few carrying the team | A 2–3 person core did the substantive work while others were peripheral. |
| A single member singled out | One *identifiable* member named as the notably weakest **or** the notable standout/carrier. |
| Mutual support / working well | Members supported each other through difficulty, or the team simply worked well. |
| None | The passage doesn't indicate any of the above. |
| Can't tell | Genuinely ambiguous even with the surrounding context. |

---

## PART B — researcher notes (NOT shown to the tutor)

- **Order is load-bearing.** Part 1 (triage) must be recorded **before** the highlights or
  the tool's labels appear — otherwise the human read is anchored on the model and the
  comparison goes circular. The UI must lock in 1a before revealing Part 2.
- **Blind labelling.** In Part 2 the tutor never sees which dynamic the tool assigned;
  agreement = the tool's flag is among the tutor's ticks.
- **Non-overlapping context windows.** When several highlights sit close together in one
  journal, trim/merge their surrounding-text windows so they don't overlap — each highlight
  is judged on its own context, no passage is shown twice, and no *other* highlight sits
  inside the context of the one being labelled.
- **Unit = one (team, sprint).** Compare against the tool's **per-sprint** read
  (`marking_sprint`), not the whole-project marks. Sample a **spread of (team, sprint)
  cells** — early/late, quiet/troubled.
- **Decoupled sizing.** Part 2 (snippets) runs **broad** (~40-50 cells, cheap); Part 1
  (triage read) runs on a **small targeted set** — peer-fine-but-flagged cells + controls,
  **~5-8 cells per tutor**, ~20-30 total across ~3-5 tutors.
- **Cap per cell.** Show at most ~5 highlights per sprint to bound time; if the tool
  flagged more, sample across the dynamics it found.
- **≥2 tutors on an overlap block** (~15 cells both rate) → the human-vs-human ceiling.
- **What each part scores:** Part 1 → Analysis B (does the tool flag the teams a human
  would act on, *especially* peer-healthy ones). Part 2 → Analysis A (faithfulness) +
  the **None** rate as the false-flag / hallucination check.

---

## PART C — settled decisions (2026-09-12; revisit after supervisor)

1. **Triage granularity → 3 levels** (fine / keep an eye / step in). The value claim only
   needs "would act (watch+step-in) vs not"; a 4th level adds noise.
2. **Time budget →** slow triage read on **~5-8 (team, sprint) cells per tutor** (~3-4 h);
   cheap snippet task on ~40-50 cells. Sizes the sample with study-doc §6.
3. **Control snippets → yes, ~25%** non-flagged passages mixed in, to check tutors aren't
   labelling everything a problem (guards a yes-bias) and to give a real precision check.
4. **Context →** *snippets:* the surrounding journal entry, non-overlapping windows.
   *Triage:* that sprint's full journals, read/skim to a confident call.
5. **Delivery → a simple web form** — the clean way to enforce the order-lock (triage
   before highlights) and the blinding.
6. **Free-text "why" on Part 1 → keep it, optional.** One line, cheap, useful colour.
