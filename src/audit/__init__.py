"""Model-implementation audit fixes — regeneration and before/after comparison.

Handoff-9 (audit 2026-08-09). Additive: recomputes every model-relative artefact
(cross-model Δ, RQ3 correlations, Δ-by-state, attack-by-state) under the fixed
models and writes the results to a **parallel** location, ``output/audit_fix/``,
leaving the pre-fix outputs untouched so both stay reproducible.

Only one model changed numerically: ``baseline_average`` now scales to a team
mean of 10.0 (Task 2). WebPA's canonical normalisation is a proven no-op on this
fixed-budget instrument (Task 1); PeerRank/PeerHITS are documentation-only. So
every downstream shift here is attributable to the baseline scale fix alone.

Entry point:
    python3 -m src.audit
"""
