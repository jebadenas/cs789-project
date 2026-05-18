# Synthetic Team Generator — Design Spec

**Status:** spec for review. No code yet. Approved generative model gates the
start of `src/attacks/synthetic.py` (Phase 4, RQ1/RQ2). Written so the core
can be lifted directly into the dissertation methods chapter.

**Decisions locked (2026-05-18, research-backed):** PG1-adapted generator
adopted with budget renormalisation. Attack suite locked at **6 vectors**
(proposal §3.4's four + #5 strategic non-submission + #6 competitive
sabotage); reciprocal log-rolling rejected as redundant with the small-circle
/ zero-self partial variant (Song & Gehringer taxonomy). Lazy/satisficing
folded here as a **low-reliability generator profile**, not a separate attack.
#5 and #6 are scope extensions beyond the proposal, surfaced for supervisor
sign-off (`docs/meetings/supervisor-meeting-prep-2026-05-19.md`).

**Implementation gate:** Anna sign-off on the #5/#6 scope extension
(2026-05-19) before those two vectors are built; #1–4 and the generator are
unblocked.

---

## TL;DR

Synthetic teams are needed because the real data is thin (18 usable teams)
and has **no ground truth** — we never know a student's true contribution, so
we cannot measure how well a model *recovers* it under attack. The generator
produces N×N peer-score matrices for N ∈ {4, 5, 6} with a **known
ground-truth contribution vector**, so Attack Delta and recovery error become
measurable against truth rather than against an unattacked estimate.

The model is **PG1, adapted** (Piech et al., 2013 — *Tuned Models of Peer
Assessment in MOOCs*, EDM). Piech is **already cited in the proposal (ref
[10])** as the empirical basis for the single-outlier attack. Using PG1 for
generation means the synthetic methodology and the single-outlier attack rest
on a single, already-in-scope source — no new citations, and the outlier
attack falls out of the model natively (an outlier rater = a low-reliability
grader).

---

## Why a generative model at all

| Need | Real data | Synthetic |
|---|---|---|
| Ground-truth contribution vector | ✗ never observed | ✓ by construction |
| Controlled attack injection | partial (inject into noisy real matrices) | ✓ clean baseline |
| Sample size for RQ1/RQ2 | thin (18 usable teams) | ✓ unlimited, seeded |
| Sizes N = 4, 5, 6 swept | uneven coverage | ✓ exact control |
| External-data dependency | — | ✓ none |

Recovery error (model IWF vs known truth) is **only definable with
synthetic data**. This is why the handover calls synthetic experiments
"load-bearing" for RQ1/RQ2.

---

## Theoretical background — PG1 (Piech et al., 2013)

PG1 is the canonical probabilistic generative model for peer assessment.
Each submission has a latent true score; each grader has a latent additive
bias and a latent reliability (precision). Canonical form:

```
true submission score   s_u  ~  N(μ₀, 1/γ₀)
grader bias              b_v  ~  N(0,  1/η₀)
grader reliability       τ_v  ~  Gamma(α₀, β₀)        (shape, rate)
observed peer grade      z_uv ~  N(s_u + b_v, 1/τ_v)
```

Piech et al.'s headline empirical finding: grader **bias** is the dominant
source of error (≈95% of correctable RMSE); reliability is secondary but is
exactly the lever the single-outlier attack pulls.

---

## Adaptation to the IWF point-distribution setting

PG1 models one grade per (submission, grader). Our setting is a full N×N
directed matrix under a fixed point budget. The mapping:

| PG1 concept | This project |
|---|---|
| submission true score `s_u` | recipient *i*'s true **contribution `cᵢ`** — the ground-truth vector |
| grader bias `b_v` | rater *j*'s bias `bⱼ` (some raters run generous/harsh) |
| grader reliability `τ_v` | rater *j*'s reliability `τⱼ` (precision of their judgement) |
| observed grade `z_uv` | raw directed score `zᵢⱼ` = score rater *j* gives recipient *i* |
| *(no analogue in PG1)* | per-rater **budget renormalisation** to the 10·N point pool |

The budget step is the one IWF-specific addition: raw PG1 draws are not
constrained to sum to a fixed pool, but the real point-distribution data is.
Renormalisation is a per-column positive rescale — **monotone**, so it
preserves the rank signal the models need to recover while enforcing the same
structural constraint the real matrices carry. This keeps synthetic and real
matrices comparable (acceptance: PeerRank/PeerHITS Attack Deltas should be
interpretable on the same axis for both).

---

## Generative procedure

For a team of N students, fixed RNG seed:

1. **Ground truth.** Draw true contribution for each student
   `cᵢ ~ N(μ₀, 1/γ₀)`, clip to ≥ 0. The vector **c = (c₁…c_N)** is the
   ground truth, stored on the synthetic-team object and rescaled to the IWF
   axis (mean → 10) so recovery error is read in IWF points.

2. **Rater parameters.** For each rater *j*: bias `bⱼ ~ N(0, 1/η₀)`;
   reliability `τⱼ ~ Gamma(α₀, β₀)`.

3. **Raw scores.** For every ordered pair (recipient *i*, rater *j*),
   `zᵢⱼ ~ N(cᵢ + bⱼ, 1/τⱼ)`, clip to ≥ 0. Self entry (i = j) handled per the
   real-data convention (see Open Questions Q1).

4. **Budget renormalisation.** Scale each rater *j*'s column so it sums to the
   point pool (10·N — pool convention pending Q1). Column *j* ← column *j* ×
   (pool / column-sum).

5. **Emit `ScoreMatrix`.** Reuse the existing `ScoreMatrix` /
   `StudentInfo` schema (`src/parsing/schemas.py`) so synthetic teams flow
   through the *same* 6-model registry (`batch_runner.MODELS`) and metrics
   unchanged. Synthetic `StudentInfo` gets placeholder name/email; the
   ground-truth `c` is carried alongside, not inside, the `ScoreMatrix`.

A perfectly unbiased, perfectly reliable panel (bⱼ → 0, τⱼ → ∞) yields every
model IWF ≈ **c**. Recovery error grows with bias spread and rater noise.

---

## Ground truth & recovery metric

- **Ground-truth vector:** `c`, rescaled to mean 10 (IWF axis).
- **Recovery error (clean):** mean absolute difference between a model's IWF
  vector and `c`. Measures inherent model fidelity with no attack.
- **Attack Delta (existing definition):** mean absolute difference between
  attacked and unattacked IWF — unchanged; synthetic teams just give it a
  truth anchor too (attacked-vs-truth alongside attacked-vs-clean).
- Reported clean-vs-attacked and (synthetic-only) vs-truth, per model, per
  attack, per N.

---

## Single-outlier attack — native fit

The proposal §3.4 single-outlier attack ("a single unreliable rater acting in
bad faith or genuine ignorance … replaces one student's scores with a random
permutation of the full point budget") is **exactly a PG1 grader with
τⱼ → 0**. So the same model that generates clean teams also defines the
outlier perturbation — one coherent story, one citation (Piech [10]). Monte
Carlo (100 perms, seeded) sweeps which rater is the outlier and the random
permutation drawn.

---

## Default hyperparameters (proposed)

Chosen so synthetic raw scores land in the real point-distribution range
(per-recipient nominal ≈ 10; IWF axis ~0–60, centred 10).

| Param | Symbol | Default | Rationale |
|---|---|---|---|
| Contribution mean | μ₀ | 10 | per-recipient nominal share of the 10·N pool |
| Contribution precision | γ₀ | 1/2.5² | true-contribution SD ≈ 2.5 IWF pts — realistic spread, clear rank signal |
| Bias precision | η₀ | 1/1.0² | rater bias SD ≈ 1 pt — Piech: bias is the dominant error term, kept non-trivial |
| Reliability shape | α₀ | 2.0 | Gamma mean α/β, var α/β²; gives moderate rater-noise spread |
| Reliability rate | β₀ | 2.0·1.5² | tunes mean obs SD ≈ 1.5 pts (precision mean → ~1/1.5²) |
| Outlier reliability | τ_outlier | ≈ 0 (e.g. 1e-3) | random-permutation rater (single-outlier attack) |
| Team sizes | N | {4, 5, 6} | per Phase 4 spec |
| RNG seed | — | fixed (configurable) | full reproducibility for dissertation |

All knobs are constructor parameters; defaults above are the documented
baseline. A small sensitivity sweep (bias spread, rater noise) is proposed as
a robustness appendix, not the main result.

---

## Generator stress profiles

The generator exposes the same parameters as named profiles so synthetic
runs can sweep panel quality without new code:

| Profile | Settings | Models the case |
|---|---|---|
| `reliable` (default) | defaults table below | competent honest panel |
| `noisy` | reduced reliability mean (lower α₀/β₀ ratio) | imprecise but unbiased panel |
| `lazy` (satisficing) | low τ for **all** raters + bias pulled toward scale centre | central-tendency / least-effort grading — the rejected "candidate C". A reliability failure mode, *not* an attack: it is the all-raters extreme of the same latent-reliability axis the single-outlier attack pulls on one rater |
| `biased` | inflated bias spread (lower η₀) | systematic generosity/harshness |

The `lazy` profile is the research-backed home for satisficing/central-
tendency behaviour (well-documented; literature's own remedy is exactly the
PG1 reliability down-weighting modelled here). Keeping it a profile rather
than a transform avoids padding the attack suite while still letting RQ1
report model behaviour under a low-information panel.

## Integration (context, not new code in this spec)

```
src/attacks/synthetic.py   ← THIS spec governs this file (incl. profiles above)
src/attacks/transforms.py  ← 6 attack transforms (separate spec: attack-vectors-spec.md)
src/attacks/delta.py       ← Attack Delta + MC harness
src/attacks/runner.py      ← attacks × 6 models × (real + synthetic)
```

Note: attack #2 (zero-self partial / small-circle) is the implementation
home for reciprocal **log-rolling** — documented in prose, no separate
transform (Song & Gehringer classify log-rolling *as* small-circle
collusion).

Synthetic teams are consumed by the *same* runner and the *same*
`batch_runner.MODELS` registry as real matrices — no model code changes.

---

## Open questions / to verify before/at implementation

1. **Pool & self-score convention (Q1) — RESOLVED 2026-05-18.** Parser
   (`src/parsing/parser.py`) validates each rater's budget as the **column
   nansum over all recipients (self included)** against the **team median**
   column sum (tolerance 1.0) — it does *not* enforce a fixed 10·N; team
   totals vary. Resolution: attack transforms **conserve each modified
   column's own pre-attack nansum** (convention-agnostic, provably
   budget-preserving regardless of whether self is populated). The generator
   uses a configurable `pool` parameter, default `10·N`, with diagonal/self
   left NaN (baseline/PeerRank exclude it anyway).
2. **Clip vs reject** on negative draws — clip-at-0 proposed (simple, keeps
   budget step well-defined); reject-resample is the alternative.
3. **Reliability parameterisation** — Gamma(shape, rate) as above; confirm
   rate vs scale convention to avoid an inverted-variance bug at impl.
4. **Sensitivity sweep scope** — main result at defaults only, or sweep in
   the dissertation? Proposed: defaults headline + small appendix sweep.

---

## References

- Piech, C., Huang, J., Chen, Z., Do, C., Ng, A., and Koller, D. Tuned
  Models of Peer Assessment in MOOCs. In *Proceedings of the 6th
  International Conference on Educational Data Mining (EDM 2013)*,
  pp. 153–160, 2013. (Proposal ref [10].) arXiv:1307.2579.
- Walsh, T. The PeerRank method for peer assessment. *ECAI 2014*,
  pp. 909–914. (Model under test; proposal ref [12].)
- Proposal §3.4 Synthetic Attack Simulation (attack definitions);
  `plans/peer-assessment-grading-engine.md` Phase 4 (acceptance criteria).
