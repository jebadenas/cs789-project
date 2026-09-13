# Study design: a journal-based team-health dashboard, and how we validate it

> Supersedes the framing in `journal-early-warning.md` for the *primary* study. That
> doc's per-sprint early-warning idea is now a **secondary/future** thread (see §7);
> this doc is the main line. Design sketch worked out 2026-09-12 — **not yet run.**

---

## 1. The one-line claim

Peer assessment measures **contribution**, so it reliably catches a **freeloader** — but
it is structurally **blind** to a team that is *contributing evenly yet falling apart*
(interpersonal conflict, burnout, a quiet member in distress). Reflective **journals**
see that. An LLM makes the journal signal usable across a whole cohort. **So the tool
surfaces a category of at-risk team that the course's existing safety net misses.**

That — not "an LLM that flags conflict," not "an LLM that predicts grades" — is the
contribution. Everything below is designed to test it honestly.

## 2. The artifact (built as a prototype)

A **coordinator-facing** dashboard (not tutor-facing — a tutor reads their 6–7 teams
anyway; the coordinator oversees ~40 and cannot). For each team, one card:

- **Health status** — Healthy / Watch / At-risk, from a **concern score** composed only
  from the *reliable* flags (severity + multiplicity + run-to-run unanimity − positives),
  with At-risk = the **worst ~15% within each cohort** (relative, so it adapts to how
  verbose a cohort's journals are; an absolute cut over-flagged 50–68%).
- **An LLM-written summary** of the team's dynamic — generated from the model's own
  findings (the flags), **anonymous by construction** (the summariser is never shown the
  quotes, so it cannot surface a student's name).
- **The reliable flags + verbatim journal quotes** as the evidence.

Prototype: `scripts/build_dashboard.py` → `prototypes/*.html` (local + git-ignored;
the quotes carry real names). Built from the existing v1 marks (119 teams). **The study
validates the per-sprint version** (`marking_sprint`, one card per team per sprint); the
whole-project view above is the at-a-glance overview.

## 3. Ground truth: fresh tutors, retrospective, on the data we have

The blocker was always Q11 — no "this team was in trouble" label external to the LLM and
the peer scores. Resolved this session: **tutors can rate the existing journals
retrospectively.** Recruit **fresh** tutors (capstone-experienced, *not* the original
tutors of these teams) so the label is unbiased and uncontaminated by having seen the
peer scores.

**The unit is one (team, sprint), not a whole team.** A team's full journal set is ~19k
words median (~1.5 h to read); a single sprint is ~5 short entries (~25 min). The tool
runs per sprint anyway, and peer contribution scores also come per session — so the
journals, the peer signal, and the tutor's judgment all line up at the **same moment**. We
**sample a spread of (team, sprint) cells** (early/late, quiet/troubled).

**The two tutor tasks are decoupled and sized differently** (the reading budget — §6):
- the **snippet task is cheap** (a highlight + a paragraph, ~2-3 min) -> run it **broad**;
- the **triage task is expensive** (read a sprint, ~25 min) -> run it on a **small,
  targeted set** (~5-8 cells per tutor).

**Two-step protocol per (team, sprint) — order matters:**

1. **Independent triage (blind to the LLM).** Tutor reads **that one sprint's** journals
   and records a single 3-way call: **okay / keep an eye on / interfere** (interfere+watch
   = "would act"), about team **health**, not product quality — *before* any LLM output is
   shown, or the judgment anchors on the model and the comparison goes circular. (From one
   sprint the tutor can't see whether a problem persists — the question is deliberately
   "based on *this* sprint", matching how the tool operates.)
2. **Blind snippet classification (the LLM's label stays hidden).** For each snippet the
   tool flagged, the tutor sees the quote **with its surrounding source text** and picks,
   from a fixed list, which dynamic(s) it indicates — *not* a leading "agree/disagree",
   because that invites acquiescence. The options are **the same reliable-flag vocabulary
   the tool uses** (open_conflict, effort_imbalance, member_under_contributed,
   communication_breakdown, leadership_problem, core_subgroup_carried, singled_out,
   mutual_support), plus **None** ("doesn't indicate a problem") and **Can't tell**.
   Select-all-that-apply.
   - **Agreement** = the LLM's flag for that snippet is among the tutor's picks
     (independent coding, not a nudge).
   - **None** picks give the tool's **false-flag rate**; the per-dynamic breakdown shows
     which dynamics humans confirm vs contest (expect conflict/imbalance high, fuzzier
     ones lower — matching the reliability pattern).
   - **Non-overlapping context windows:** when a team has several flagged snippets close
     together, trim/merge their surrounding-text windows so they do **not** overlap — each
     snippet is judged on its own context, no passage is shown twice, and no *other*
     flagged snippet bleeds into the one being classified.

Step 1 feeds Analysis B (the value); step 2 feeds Analysis A (faithfulness). Same read,
both results, no contamination. **≥2 tutors on an overlapping subset** → the
**human-vs-human agreement ceiling** (the LLM can't be expected to match humans better
than humans match each other).

## 4. Two analyses (kept deliberately separate)

**A — Faithfulness / is the LLM a trustworthy reader?**
From step 2 of the tutor protocol: on each flagged snippet (shown in context, the LLM's
label hidden), does the tutor **independently classify** the same dynamic the LLM did?
Validates the *instrument*. NB this is **not** a prediction claim — it is honestly
labelled as reader-agreement. Because the tutor codes blind rather than confirming a
shown label, the measure sidesteps acquiescence bias; the **None** rate doubles as the
hallucination / false-flag check.

**B — The blind-spot value (the headline).** At the **(team, sprint)** unit.
1. Rank cells by the **peer signal for that session** — contribution scores are collected
   *every* session, so this is a genuine per-sprint baseline (here the RQ1–3 peer
   machinery re-enters).
2. Find cells the peer scores call **fine** but the tool flags.
3. A tutor reads *those* sprints and confirms: real trouble, or false alarm?

If a meaningful share of "peer-fine, journal-flagged" cells are tutor-confirmed troubled
→ **the journals catch what the numbers can't, quantified.** No circularity (peer scores
and journals are independent sources), no shaky prediction.

## 5. What we deliberately dropped (and why)

- **Early-prediction study** ("early-sprint flag → later collapse") — with only a handful
  of genuinely-failed teams across 119, the numbers are too thin to defend. Parked.
- **Self-journal vs peer-comment comparison** — peer free-text comments are sparse (most
  students write little), so that second "window" isn't a rich enough signal.
- **Named attribution** in the research outputs — keep anonymous ("a member"); naming
  needs the crosswalk (re-identification) and is an ethics escalation. A *deployed* tool
  under institutional consent could name people; the study does not.

## 6. The binding constraint: tutor reading budget

Measured on the data: a team's full journal set is **~19k words median (~1.5 h)** — so
whole-team reading is infeasible at any real sample size. Two moves fix it:

1. **Per-sprint unit.** Judge one sprint (~5 entries, ~25 min), not the whole team — ~4x
   less reading, and more realistic (the tool runs per sprint too).
2. **Decouple the tasks.** The cheap snippet task runs broad (many cells); the expensive
   triage runs on a small targeted set — the **peer-fine-but-flagged** cells + controls,
   ~**5-8 per tutor** (~3-4 h), **~20-30 cells total** across **~3-5 tutors**, some cells
   double-rated for the human ceiling.

Report Study B as **triage/recall** (missing a bad team ≫ a false flag), not accuracy.

## 7. Per-sprint is now the unit; persistence is the future extension

The per-sprint coding (`marking_sprint.py`, `run sprint`) is the study's **unit** (§3),
not a side thread — piloted on 2024_s1, to be extended to all four cohorts (one cluster
job). The genuinely *future* piece is **persistence across sprints** (flagged in sprint 2,
still flagged in sprint 4 = chronic vs a blip) — a richer severity signal and an
"early-warning" angle, but not needed for the main validation. Keep warm; don't gate on it.

## 8. Honest caveats (put in the write-up)

- Tutor concern is a **proxy** outcome, not a hard ground truth.
- Small n per cohort; report with care.
- Peer-blind-spot claim depends on the peer signal being a fair baseline — define it
  explicitly (contribution dispersion / lowest score / cascade state) and pre-register it.
- **Observer effect** applies to a *deployed* tool (students could sanitise journals if
  they knew a model scans them); the retrospective study is unaffected — say so.

## 9. Open decisions / supervisor asks

1. **Tutor recruitment** — can we get ≥2 fresh capstone-experienced tutors for a
   ~50-team rating exercise (with overlap)?
2. **The peer baseline** — which per-session peer quantity is the fair "at-risk by the
   numbers" comparator (contribution-score dispersion that session? the lowest score?).
   Contribution scores exist at *every* session, so the baseline is genuinely per-sprint.
3. **Raw team marks** — still worth requesting as a coarse external anchor (secondary).
4. **Ethics scope** — confirm retrospective tutor re-reading of existing journals sits
   within current approval.

## 10. First concrete steps (once the above is agreed)

1. Extend per-sprint marking (`run sprint`) from 2024_s1 to all four cohorts (cluster job).
2. Wrap the per-session peer signal into one comparable per-(team, sprint)
   "at-risk-by-numbers" score → compute the peer-fine-but-flagged cell set.
3. Finalise the tutor exercise + sampling frame of (team, sprint) cells (see
   `tutor-exercise-draft.md`).
4. (Parallel) optional 72B pass to regenerate dashboard summaries at higher quality.


## 11. Preliminary evidence (exploratory — NOT the validation)

A first-pass journal-vs-peer cross on all four cohorts (`scripts/blind_spot.py`), pending the
supervisor confirmations in §9. Unit = (team, sprint); peer signal = the minimum perceived
contribution (PC) per team that session (100 = an equal share); mapping **Session k ↔ Sprint
k** (session = journal_index − 1).

- **The blind spot.** Of the (team, sprint) cells where the journals flag conflict / comms /
  leadership, **~65% (79/122 at PC ≥ 85) look FINE on peer contribution** — i.e. the peer
  numbers miss the majority of the interpersonal/functional trouble the journals surface.
  Across cohorts: 2023_s2 31 · 2024_s2 21 · 2025_s1 17 · 2024_s1 10.
- **Robust to the threshold.** 58–72 % peer-invisible across PC ≥ 90 … ≥ 75, so the headline
  doesn't hinge on where "even contribution" is drawn.
- **The mapping is sound.** Session k ↔ Sprint k is the only offset that covers all 433 cells
  and ties for the best same-construct agreement; when the peer scores flag a freeloader, the
  journals independently flag contribution imbalance **at the mapped sprint 85 % of the time**.
  (The reverse — journals flag imbalance, peer agrees — is only 35 %, because journals over-flag
  mild/subjective imbalance the numbers don't register: a sensitivity difference, not a timing one.)
- **Caveats.** "Journal-flag" = the LLM flagged it — **validity comes from the tutor study
  (Analysis B), not this cross**. The PC threshold and the session-pairing are provisional. This
  is exploratory support for the headline direction, not the result.

Reproduce: `python3 scripts/blind_spot.py` (tunable `TH` and mapping offset).
