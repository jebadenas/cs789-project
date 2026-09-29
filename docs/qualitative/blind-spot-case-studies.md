# Blind-spot case studies: 5 teams the journals saw and the peer scores missed

> Source: `scripts/blind_spot.py`, journal blobs via `blobs.build_blob`, peer PC data
> from `data/peer_sessions/`. All names anonymised below (real names exist only in
> gitignored local data). Date: 2026-09-22.

---

## Selection criteria

Each case is a (team, sprint) cell where:
- the peer contribution scores look **fine** (every member's PC ≥ 85),
- the journals flag at least one **non-contribution dynamic** (conflict, communication
  breakdown, or leadership problem), AND
- the peer scores **decline below threshold at the very next sprint** — confirming the
  journal was seeing trouble the peers had not yet registered.

Cases chosen for diversity: different cohorts, different flag combinations, different
PC trajectories. All 5 involve `leadership_problem` — the strongest predictor of
next-sprint decline (OR = 4.18).

---

## Case 1 — A leadership vacuum as the team scales up work

**Cell:** 2023_s2, Team 33, sprint 1 → sprint 2.
**PC sprint 1:** 91, 95, 99, 102, 107, 107 (range 16, everyone above threshold).
**PC sprint 2:** 61, 70, 113, 116, 117, 124 (two members collapse; range 63).
**Flags:** leadership_problem, communication_breakdown, effort_imbalance,
member_under_contributed, underperformance_unaddressed, core_subgroup_carried,
singled_out_below.

**What the journals say.** Two members describe doing nearly all the work between
them — one on back-end endpoints, the other on code quality and "wrangling team
members." Three others are described as inactive or minimally participating: one
"only listening to conversations and not really adding anything," another assigned a
database task mid-week but producing nothing by the weekend. A member writes: *"I
feel our team may be losing focus a little. Although teamwork-wise our team is still
going strong, I find it harder for our team to find meeting times where everyone is
involved."*

**What the peer scores show at sprint 1.** Nothing. The narrowest spread in the
dataset for this team — every member between 91 and 107. No signal.

**What happens next.** Sprint 2 PCs polarise dramatically: two members drop to 61 and
70 while the others rise above 113. The journal's description of a two-person core
carrying inactive members becomes visible in the numbers — one sprint later.

**The lesson.** The journal captured a team whose communication and task distribution
were already breaking down while the peer scores still reflected a near-even split.
The sprint-1 PC spread of 16 points concealed a growing leadership vacuum that the
sprint-2 spread of 63 points finally revealed.

---

## Case 2 — Perfectly even scores hiding a disengaged half

**Cell:** 2024_s1, Team 15, sprint 1 → sprint 2.
**PC sprint 1:** 99, 99, 99, 100, 100, 102 (spread of 3 — as close to uniform as
the data gets).
**PC sprint 2:** 49, 49, 59, 141, 146, 156 (extreme polarisation; range 107).
**Flags:** leadership_problem, effort_imbalance, member_under_contributed,
underperformance_unaddressed, core_subgroup_carried.

**What the journals say.** The team leader writes: *"The experience as a team leader
hasn't been good. Half of the team doesn't seem so keen on working on the project at
all. I ended up completing almost all the tasks allocated to them myself."* Another
member describes interacting primarily with one other person: *"I still interact
mostly with [one teammate] as the other team members are not as communicative."*
Under-performance is noted but not confronted — *"Maybe they just need some time to
catch up. I'll see."*

**What the peer scores show at sprint 1.** Essentially nothing. A 3-point range
across 6 members — every PC within ±2 of 100. This is the flattest distribution in
the dataset for this team.

**What happens next.** Sprint 2 is the most extreme polarisation in the candidate
set: three members at 49–59, three at 141–156. The disengagement the journal
described at sprint 1 became visible in the peer scores exactly one sprint later.

**The lesson.** A perfectly flat peer-score distribution is not evidence of a healthy
team — it is evidence that the instrument has nothing to report *yet*. The team
leader's journal tells a completely different story. If a coordinator had seen only
the sprint-1 PC scores, this team would have been the last one they checked.

---

## Case 3 — A project manager sees friction the numbers don't

**Cell:** 2025_s1, Team 20, sprint 1 → sprint 2.
**PC sprint 1:** 92, 98, 100, 100, 104, 106 (comfortable range, all above threshold).
**PC sprint 2:** 44, 108, 109, 110, 113, 116 (one member collapses to 44).
**Flags:** leadership_problem, communication_breakdown, effort_imbalance,
member_under_contributed, underperformance_unaddressed.

**What the journals say.** The project manager describes one member lagging on an
assigned task: *"He expressed he would be busy that week, but it became worrisome when
it was almost due, and there was no work done on it."* A separate communication
breakdown is described: *"I had asked everyone well in advance to upload their photos,
yet on submission day, he had still not done so. When I reminded him, he claimed he
could not find the link and asked me to send it again, even though I had already
shared it with the entire team."*

The PM is self-aware about the leadership challenge: *"As project manager, I found
that checking in mid-week helped keep things in motion. Some team members work more
independently than others."*

**What happens next.** One member drops to PC 44 — the lowest in any case here. The
pattern the PM described (one member not following through) becomes a quantifiable
contribution gap.

**The lesson.** The PM's journal is a real-time management log. The peer scores at
sprint 1 register nothing because the team *was* contributing roughly evenly at that
point — the lagging member had not yet missed enough to show up numerically. The
journal captures the leading indicator: missed commitments and unresponsiveness.

---

## Case 4 — A solo contributor describes carrying the team

**Cell:** 2023_s2, Team 07, sprint 2 → sprint 3.
**PC sprint 2:** 95, 95, 98, 99, 113 (mild spread, all above threshold).
**PC sprint 3:** 51, 102, 113, 116, 118 (one member drops to 51).
**Flags:** leadership_problem, communication_breakdown, effort_imbalance,
member_under_contributed, underperformance_unaddressed, singled_out_above.

**What the journals say.** One member writes: *"I was able to get some functionality
on the project by the end of the week (so far, I've contributed to about 100% on the
project)."* The team leader was ill; others had assignments and tests. Communication
broke down over a break period: *"We weren't communicating with each much, despite
my efforts on communicating on our group chats."* The same member directly confronted
the leadership gap: *"I questioned my team leader's lack of involvement and
communication on the project in the past few weeks (which he apologised for it)."*

**What the peer scores show at sprint 2.** The member doing all the work is already
visible as the highest scorer (113 vs 95–99 for the rest), but nobody is below
threshold. The team "looks fine."

**What happens next.** One member drops to 51. The dynamic the journal described —
a solo contributor carrying the project with minimal help — becomes numerically
obvious.

**The lesson.** The journal contains an explicit statement ("100% on the project")
that no peer-score threshold will detect until the gap becomes large enough. The
`singled_out_above` flag (the standout contributor) co-fires with `leadership_problem`
— these are not independent dynamics but two views of the same dysfunction.

---

## Case 5 — Flat peer scores masking unfulfilled commitments

**Cell:** 2023_s2, Team 20, sprint 1 → sprint 2.
**PC sprint 1:** 100, 100, 100, 100, 100, 100 (perfectly flat — all 6 members
identical).
**PC sprint 2:** 68, 89, 98, 111, 116, 118 (one drops to 68).
**Flags:** leadership_problem, effort_imbalance, member_under_contributed,
underperformance_unaddressed, core_subgroup_carried.

**What the journals say.** A member describes working alone on the UI design while
others did not deliver: *"Unfortunately, I seem to have spent most of the week
working on the UI design alone, with some help from [one teammate], who wasn't
supposed to be doing front-end work this week."* The same member identifies the
pattern: *"The only people I've noticed doing anything on the Figma account this
week are myself and [one teammate]."* A specific member is called out for repeatedly
promising work without delivering: *"[He] keeps saying he's going to do it, but he's
not actually doing it."*

**What the peer scores show at sprint 1.** Every member at exactly 100. Not close to
100 — *exactly* 100, all six. This is either a team where contribution was perfectly
equal (contradicted by the journal), or a team where nobody differentiated in their
peer ratings (the more likely explanation for a sprint-1 score where the team has
barely started building).

**What happens next.** Sprint 2 shows a 50-point range, with the member described as
not delivering dropping to 68. The journal's observation at sprint 1 was correct; the
peer instrument simply had no variance to work with yet.

**The lesson.** A flat 100-across-the-board at sprint 1 is a measurement artefact, not
a finding — peers cannot differentiate contribution when the project has barely started.
The journal, by contrast, *can* see who shows up to meetings, who follows through on
assigned tasks, and who engages in discussion. The temporal advantage of journals is
sharpest at the start of a project, when the peer instrument is at its least
informative.

---

## Cross-case patterns

1. **Leadership flags dominate.** All 5 cases fire `leadership_problem`. In 3 of 5 a
   specific leadership vacuum is described (absent team leader, PM noting lack of
   follow-through, questioning the team leader's involvement). The peer instrument does
   not have a "leadership" dimension.

2. **The peer instrument is weakest at sprint 1.** Cases 1, 2, 3, and 5 are all sprint
   1 → 2 transitions. At sprint 1 the project has barely started, peer ratings have
   minimal variance, and the journal is the only source that sees emerging dynamics.

3. **Flat or near-flat peer scores are the riskiest signal.** Case 2 (spread of 3) and
   Case 5 (spread of 0) had the most dramatic subsequent declines. A narrow peer-score
   distribution early is not reassuring — it means the instrument cannot yet distinguish.

4. **The journals describe a gradient, not a binary.** None of these teams is broken at
   the blind-spot sprint. Members still communicate, still attend meetings, still produce
   *some* work. The journal captures the direction of travel — friction building, tasks
   slipping, communication fraying — before it reaches a severity the peer scores detect.

5. **Under-performance is noted but not confronted.** In Cases 2 and 3, the journal
   explicitly records a decision *not* to escalate ("maybe they just need some time";
   "I thought I was being helpful by letting them focus"). A coordinator reading these
   journals would see the hesitation and could intervene before the team dynamic sets.
