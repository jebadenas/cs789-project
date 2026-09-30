# Reference audit — started 2026-09-30

Scope so far: Ch1, Ch2 and Ch3 §3.1–3.3 as they stand on `dissertation-writing`.
Re-run this audit as each new section lands.

## Done (verified via Crossref / the paper itself)

- DOIs added: kaufman2000accounting, loddington2009webpa, friess2020continuous,
  hall2013freeriding, ohland2012catme, walsh2014peerrank, song2017collusion,
  hundhausen2023combining, hooshangi2025assessment.
- friess2020continuous: pages corrected 82–89 → **82–87**.
- New entries: `brown1995autorating` (the original RMIT autorating system Kaufman
  builds on), `riegler2025collusion` (collusion in group-work peer assessment),
  `kendall1945ties` (τ-b), `phipson2010permutation` (permutation p-values).
- Confirmed from the Kaufman et al. (2000) PDF: weighting factor = individual
  average ÷ team average, capped at 1.10; self-ratings normally *not* included;
  they list "team members will agree to give everyone identical ratings" as a
  standard concern and measured it.

## Mis-citations to fix (claim ≠ what the source says)

| Where | Claim | Problem | Fix |
|---|---|---|---|
| Ch2 §Reflective writing | "Peer assessment has no external ground truth" `\citep{lei2016groundtruth}` | Lei et al. is about **clustering** validity indices, not peer assessment | **done**: reworded as a statement about COMPSCI 399; no citation needed |
| Ch1 §Motivation, Ch2 | Teammates rating each other uniformly high `\citep{song2017collusion}` | Song et al. study collusion in **Expertiza artefact peer review** (reputation systems), not within-team contribution ratings | Cite `kaufman2000accounting` + `riegler2025collusion` instead; keep Song only as "collusion in peer review generally" |
| Ch1 §Instrument, Ch2 | Instructors "reported this pattern directly" `\citep{hooshangi2025assessment}` | Abstract mentions reliability concerns and students' reluctance to critique peers; **collusion not in abstract** | **verified OK**: preprint reports instructors saw students "game the system" by informally agreeing to rate one another positively. Keep. |
| Ch2 §Iterative models | PeerRank "evaluated on online courses with hundreds of participants" | Walsh (2014) evaluates on **synthetic data** | Rewrite the sentence (keep piech/dealfaro for the MOOC point) |

## Claims that need a citation (none currently)

| Where | Claim | Suggested source | Status |
|---|---|---|---|
| Ch1 §Instrument | COMPSCI 399's scheme (10N points, self excluded, grade × IWF/10) | Probably not written down: ask Anna (`notes/questions-for-anna.md` Q1); may be cited as personal communication | **Anna** |
| Ch1 §Instrument | COMPSCI 399 "follows the framework of Kaufman et al." | Ask Anna (Q1), else reword to "resembles" | **Anna** |
| Ch3 §3.2 WebPA | "most widely adopted normalisation method" | Removed in the 2026-09-30 rewrite | done |
| Ch3 §3.2 WebPA | WebPA algorithm (divide by rater total, incl. self) | `webpa_workedexample` (Loughborough worked example) | **inserted** 2026-09-30 |
| Ch2/Ch3 PeerHITS | "HITS has not previously been applied to within-team peer assessment" | Jos found `soprano2019hits` (HITS on reader ratings of papers); also `mizzaro2007hits`. Claim narrowed to within-team contribution ratings and both cited | **done** in Ch3; Ch2 sentence to align when Ch2 is revised |
| Ch3 §3.3 cascade | Kendall τ-b | `kendall1938tau` + `kendall1945ties` | inserted 2026-09-30 |
| Ch3 §3.3 cascade | Permutation p = (1+count)/(1+n) | `north2002empirical`, `phipson2010permutation` | inserted 2026-09-30 |
| Ch3 §3.3 cascade | Within-rater ranks remove leniency/severity | `linacre1989mfrm` | inserted 2026-09-30 |

- Walsh (2014) checked against the paper: synthetic data only; α = β = 0.1; α and the
  starting grades "not critical"; self-grades assumed "but this can be relaxed".

## Coming up (for sections not yet written)

- §3.4 attacks: collusion / self-sacrifice literature (above), any synthetic-team generator source.
- §3.5 LLM pipeline: Qwen2.5 technical report (Qwen Team 2024, arXiv:2412.15115); vLLM
  (Kwon et al. 2023, SOSP); LLM deductive coding reliability, e.g. Xiao et al. 2023
  (IUI Companion, doi 10.1145/3581754.3584136). To verify before inserting.
- §3.6: Kruskal–Wallis (Kruskal & Wallis 1952, JASA).
- §3.7: GEE (Liang & Zeger 1986, Biometrika).

## Bib entries for cut strands (not cited; leave or prune at the end)

Archetypal analysis, VADER, clustering stability (von Luxburg, Ben-Hur, Ben-David,
Wang), BIC/ICL, Mahalanobis, Ledoit–Wolf, Dixon/Dean–Dixon, hamer2021gitmetrics.
