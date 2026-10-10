# Tutor validation study: preliminary results (5 of 6 tutors, 2026-10-11)

Script: `scripts/tutor_study.py` (run from the checkout holding the gitignored data).
Inputs: `data/study/responses/<tutor>/` exports; `survey/src/app/cases.data.json`
(the 2026-09-24 build the tutors used). All 176 answers join to that build.
Aggregate figures only. Re-run when the sixth tutor's export arrives.

**Setup.** 2026_s2, journal 3 (weeks 6–7). Each tutor rated only their own teams.
Part 1: per team, "seems fine / keep an eye on / step in" before seeing anything from the
tool. Part 2: per snippet (in context, the tool's label hidden), pick conflict / unequal
contribution / coordination (multi-select), "none" or "can't tell". 95% CIs are a
team-level cluster bootstrap (10,000 resamples).

| | Result |
|---|---|
| Answers | 36 team triage, 176 snippet answers (113 tool-flagged, 30 obvious-flag controls, 33 benign controls) |
| Tool-flagged snippets: tutor picked the tool's flag | 59/113 = **52%** (39–65%) |
| ... tutor picked any problem | 71/113 = 63% (49–76%) |
| ... tutor said "none" | 39/113 = **35%** (23–47%) |
| Unequal contribution flags agreed | 22/33 = **67%** (47–86%); "none" 15% |
| Coordination flags agreed | 37/76 = 49% (35–63%); "none" **43%** |
| Conflict flags agreed | 0/4 (tutors read 3 of 4 as coordination) |
| Obvious-flag controls (all 3 runs agreed) | 16/30 = 53%, no better than ordinary flags |
| Benign controls (never flagged): tutor said none | 27/33 = 82%; picked a problem 3/33 |
| Agreement range across tutors | 35%–74% |
| Teams the tool flagged at least once (whole cohort) | **40/43** |
| Triage vs tool | Concerned (watch/step in): 15/16 flagged. Fine: 18/20 flagged. Fisher p = 1.0. Mean flagged snippets 3.7 vs 2.7 (Mann–Whitney p = 0.08) |

**Reading.**
1. About half of the tool's flags match what the tutor saw; a third the tutor read as no
   problem. Unequal contribution holds up best.
2. Coordination is the weak flag: most numerous (76 of 113) and the most often judged "none".
   Matches the tutor comment that a plan not working out is not a coordination breakdown.
3. Run-to-run unanimity does not predict tutor agreement (obvious controls 53% vs 52%).
   Consistent is not the same as correct.
4. Benign controls were mostly read as "none", so tutors were not picking problems
   indiscriminately.
5. At team level the tool flags nearly every team (40/43), so as it stands it cannot sort
   teams; tutors' "keep an eye on" teams carry slightly more flags, not significantly.
6. Tutors differ a lot (35%–74%), and each rated only their own teams, so there is no
   human-human agreement ceiling.

Report as a feasibility / face-validity pilot. Tutor free-text comments:
`notes/study-tutor-feedback.md` in the COMPSCI-789 workspace (paraphrased, private).
