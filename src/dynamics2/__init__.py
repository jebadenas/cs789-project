"""Rank-based state cascade — RQ3 re-representation (handoff-8).

A second, additive dynamics lane that removes rater effects *before* measuring
team structure. Where `src/dynamics` computes on raw scores (and is therefore
confounded by how much each rater differentiates — `mean_rater_std` dominates
its partition), this lane transforms each rater's ratings to within-rater
normalised ranks first, so leniency, severity and range are divided out.

On that scale-free representation it runs a three-gate cascade
(Silent / Contested / standout shape) with every threshold set by a per-matrix
permutation null rather than by fiat.

This package does NOT modify or replace `src/dynamics`; both pipelines remain
runnable so the old and new partitions can be compared.

Entry point:
    python3 -m src.dynamics2
"""
