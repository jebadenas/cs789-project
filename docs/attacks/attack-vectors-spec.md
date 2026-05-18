# Attack Vectors — Design Spec

**Status:** spec for review. No code yet. Locks the attack suite for
`src/attacks/transforms.py` (Phase 4, RQ1/RQ2). Companion to
`synthetic-generator-spec.md` (the teams these attacks run on). Written
dissertation-ready for the methods chapter.

**Locked 2026-05-18, research-backed.** Six vectors. Each maps to a
documented empirical pattern with a citation — none invented. Reciprocal
log-rolling evaluated and **rejected** as redundant. Satisficing evaluated
and moved to a generator profile (see generator spec), **not** an attack.

**Scope note:** #1–4 are proposal §3.4. #5–#6 are evidence-based extensions
beyond the proposal → gated on supervisor sign-off
(`supervisor-meeting-prep-2026-05-19.md`).

---

## TL;DR

Six static transforms on a `ScoreMatrix → ScoreMatrix`. Applied to clean
real matrices *and* synthetic teams; all 6 models in `batch_runner.MODELS`
re-run; **Attack Delta** = mean absolute IWF difference (attacked vs
unattacked) per model. Freed-budget redistribution is **proportional** to
the rater's existing allocation (decision 2026-05-18 — preserves rating
structure, most realistic collusion). Budget conserved per modified column.

---

## The six vectors

### #1 — Uniform inflation  *(proposal §3.4)*

- **Mechanism:** every rater gives every recipient the uniform share (all
  off-diagonal = 10) → all baseline IWFs collapse to 10.0.
- **Documented pattern:** *pervasive collusion* — top scores to all, no
  coordination needed; ~10% of reviews in Song et al.'s cross-discipline
  data; Hooshangi et al. confirm tacit mutual inflation as the default
  failure mode in cohesive capstone teams.
- **Source:** Song et al. [11]; Hooshangi et al. [4].
- **Acceptance:** baseline → IWF = 10.0 ∀ students.

### #2 — Zero-self collusion (full + partial)  *(proposal §3.4)*

- **Mechanism:** colluding raters award self 0; their self-share is
  redistributed **proportionally** to teammates. Self silently discarded
  but IWF denominator stays N−1 → surplus injected into the teammate pool.
  Full = all members; partial = 2 of N.
- **Documented pattern:** *small-circle collusion* + the IWF-specific
  surplus-injection exploit. **Reciprocal log-rolling lives here** — Song &
  Gehringer's taxonomy classifies pairwise reciprocal inflation *as*
  small-circle collusion; the partial (2-of-N) variant is exactly that
  case. No separate transform.
- **Source:** Song et al. [11].
- **Acceptance:** full vs partial produce distinct results; modified
  columns still sum to budget.

### #3 — Targeted down-vote  *(proposal §3.4)*

- **Mechanism:** the victim receives 0 from all other members (their share
  redistributed proportionally among remaining recipients); the victim's
  *own* outgoing ratings stay honest (unmodified).
- **Documented pattern:** status-hierarchy exclusion — low-status members
  deliberately excluded by higher-status teammates; "involuntary
  free-rider" assessed as such by peers who took ownership.
- **Source:** Hall & Buzwell [2]; Vernon (cited in [2]).
- **Acceptance:** baseline → victim IWF = 0; victim's column unchanged.

### #4 — Single outlier (Monte Carlo)  *(proposal §3.4)*

- **Mechanism:** one rater's column ← random permutation of the full point
  budget. MC: 100 seeded perms, sweeping which rater and which permutation.
  Reports mean/std/min/max Attack Delta. Primary RQ2 vector (PeerRank
  convergence stability in small graphs).
- **Documented pattern:** graders vary systematically in bias and
  reliability; one unreliable rater is 20–25% of a 4–6-person graph. **This
  is a PG1 grader with τ → 0** — same model as the synthetic generator, so
  generator and attack share one in-scope citation.
- **Source:** Piech et al. [10].
- **Acceptance:** 100 perms/team; distribution reported; PeerRank
  iteration counts / non-convergence documented.

### #5 — Strategic non-submission  *(extension — own finding)*

- **Mechanism:** drop one rater's column entirely (→ NaN), as if they never
  submitted the peer form.
- **Documented pattern:** iterative models inflate a non-submitter *above*
  participating students (zero rater-credibility removes their dampening
  effect on peers while they still receive full scores). Baseline/WebPA
  immune; PeerRank/PeerHITS impute-variants vulnerable.
- **Source:** own empirical finding —
  `docs/diary/2026-04-20-non-submitter-amplification.md`; a PeerRank
  (Walsh [12]) / PeerHITS structural pathology.
- **Acceptance:** impute-variant IWF of the dropped rater exceeds the
  participating-student mean (amplification reproduced).
- **Gate:** scope extension → Anna sign-off 2026-05-19.

### #6 — Competitive sabotage  *(extension — new citation)*

- **Mechanism:** a self-interested colluder deflates the *strongest*
  contributor (lowest scores to the top-ranked recipient); freed budget
  redistributed proportionally to the remaining recipients (incl. the
  saboteur's allies / self-benefiting targets). Attacker's other ratings
  otherwise plausible.
- **Documented pattern:** under relative grading, agents misreport to
  improve their own standing by harming strong competitors. **Distinct from
  #3:** #3 is *social* exclusion of a *low-status* member, attacker not a
  beneficiary; #6 is *self-interested* deflation of the *top* contributor.
  Applies to IWF because IWF is scaled to the team mean — pulling the top
  contributor down mechanically lifts every other IWF, including the
  saboteur's.
- **Source:** strategyproof-peer-grading literature — *Catch Me if I Can*
  (Dhull et al., strategic-behaviour detection + released dataset); TSP
  (Wang et al., truthful strategyproof peer selection for MOOCs); Dollar
  Partition (Aziz et al.). **New citation, not in the proposal.**
- **Acceptance:** top-contributor IWF strictly drops; ≥1 other IWF rises;
  budget conserved.
- **Gate:** scope extension → Anna sign-off 2026-05-19.

---

## Rejected candidate

**Reciprocal / dyadic log-rolling — rejected (redundant).** Song &
Gehringer's own taxonomy classifies pairwise reciprocal inflation *as*
small-circle collusion; the literature's analytical split is small-circle
vs pervasive — exactly the #2-vs-#1 split already implemented. Adding it
would be relabelling, not a new mechanism. Resolution: documented as the
small-circle interpretation of #2's partial variant, no separate transform.
Decision recorded so the question isn't reopened later.

---

## Cross-cutting design

- **Redistribution:** proportional to the rater's pre-attack allocation
  (decision 2026-05-18). Equal-split considered and rejected as
  unrealistically structure-flattening.
- **Budget conservation:** every modified column re-sums to the point pool
  (pool/self-score convention to verify against `src/parsing/parser.py` at
  impl — see generator spec Open Q1).
- **Metric:** Attack Delta = mean |IWF_attacked − IWF_unattacked| per
  model; synthetic teams additionally report vs known ground truth.
- **Applied to:** clean real matrices + synthetic teams (N = 4, 5, 6).
- **Output:** grouped bar chart, mean Attack Delta per model per attack,
  Monte-Carlo error bars on #4; standalone HTML → `output/attacks/`.
- **Self-inflation** (rate self high) is intentionally **not** a vector:
  all models exclude the diagonal, so it is a structural no-op — noted to
  pre-empt the reviewer question.

---

## References

- Song, Y., Hu, Z., Gehringer, E. F. Collusion in educational peer
  assessment: How much do we need to worry about it? *FIE 2017*. (Proposal
  ref [11]. Pervasive vs small-circle taxonomy; log-rolling rejection.)
- Hall, D., Buzwell, S. The problem of free-riding in group projects.
  *Active Learning in Higher Education* 14(1), 2013. (Proposal ref [2].)
- Hooshangi, S. et al. Evaluating assessment practices in team-based
  computing capstone projects. *ITiCSE-WGR 2025*. (Proposal ref [4].)
- Piech, C. et al. Tuned Models of Peer Assessment in MOOCs. *EDM 2013*.
  (Proposal ref [10]. #4 + synthetic generator.)
- Walsh, T. The PeerRank method. *ECAI 2014*. (Proposal ref [12]. #5
  pathology.)
- Dhull, K. et al. Catch Me if I Can: Detecting Strategic Behaviour in
  Peer Assessment. *AAAI 2022*. (**New** — basis for #6.)
- Wang et al. TSP: Truthful Grading-Based Strategyproof Peer Selection for
  MOOCs. (Supporting #6 — competitive misreporting in MOOC peer grading.)
- Proposal §3.4; `plans/peer-assessment-grading-engine.md` Phase 4.
