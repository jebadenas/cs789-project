"""Model-implementation audit fixes — regeneration and before/after comparison.

Handoff-9 (audit 2026-08-09). Additive: recomputes every model-relative artefact
(cross-model Δ, RQ3 correlations, Δ-by-state, attack-by-state) under the fixed
models and writes the results to a **parallel** location, ``output/audit_fix/``,
leaving the pre-fix outputs untouched so both stay reproducible.

Baseline handling (handoff-9b, reversing handoff-9 Task 2): the institutional
``baseline_cs399`` is unscaled (its level is meaningful); a separate
``baseline_normalised`` is scaled to mean 10 and is what cross-model Δ uses
(Δ measures relative standing). So the "pre/post" Δ comparison here contrasts an
unscaled-baseline Δ with the normalised-baseline Δ; the latter is the definition
we keep. WebPA's canonical normalisation is a proven no-op on this fixed-budget
instrument; PeerRank/PeerHITS are documentation-only.

`absolute.py` adds the RQ1 absolute-vs-relative view (handoff-9b Tasks 3/4):
whole-team zero-self collusion is a pure +25%/+20% level inflation under
``baseline_cs399``, invisible to every mean-10 model and to Δ.

Entry point:
    python3 -m src.audit          # delta + absolute + attacks
"""
