"""PG1-adapted synthetic team generator.

Generates N×N peer-score matrices with a known ground-truth contribution
vector, so attack robustness and recovery can be measured against truth
rather than against a noisy estimate.

Model (Piech et al., 2013 — PG1, adapted to the IWF point-distribution
setting; see docs/attacks/synthetic-generator-spec.md):

    contribution   cᵢ  ~ N(μ₀, contrib_sd²)              clip ≥ 0
    rater bias     bⱼ  ~ N(0, bias_sd²)
    rater precision τⱼ ~ Gamma(α₀, β₀)                    σⱼ = 1/√τⱼ
    raw score      zᵢⱼ ~ N(cᵢ + bⱼ, σⱼ²)   (i ≠ j)        clip ≥ 0

Each rater column is then renormalised to a fixed point budget (``pool``,
default 10·N), matching the real point-distribution structure.  The
diagonal (self-score) is left NaN — every IWF model excludes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.parsing.schemas import ScoreMatrix, StudentInfo

# Generator stress profiles (see spec).  Each overrides the reliable
# defaults; ``central_pull`` shrinks each rater's perceived contribution
# spread toward the team mean (central-tendency / satisficing).
PROFILES: dict[str, dict[str, float]] = {
    "reliable": {},
    "noisy": {"obs_sd": 3.0},
    "lazy": {"obs_sd": 3.5, "bias_sd": 0.5, "central_pull": 0.7},
    "biased": {"bias_sd": 3.0},
}


@dataclass(frozen=True)
class SyntheticTeam:
    """A generated team plus its known ground truth."""

    score_matrix: ScoreMatrix
    ground_truth: np.ndarray
    """Length-N true contribution vector, rescaled to mean 10 (IWF axis)."""
    profile: str
    seed: int
    params: dict = field(default_factory=dict)


def generate_team(
    n: int,
    seed: int,
    *,
    profile: str = "reliable",
    pool: float | None = None,
    mu0: float = 10.0,
    contrib_sd: float = 2.5,
    bias_sd: float = 1.0,
    obs_sd: float = 1.5,
    alpha0: float = 2.0,
) -> SyntheticTeam:
    """Generate one synthetic team.

    Args:
        n: team size (4, 5, or 6 per Phase 4).
        seed: RNG seed — fully determines the team.
        profile: one of ``PROFILES`` (reliable/noisy/lazy/biased).
        pool: per-rater point budget (column sum). Default 10·(n−1) —
            self is excluded, so this anchors the per-recipient nominal
            share (and clean-panel baseline IWF) at 10.
        mu0: mean true contribution (per-recipient nominal share).
        contrib_sd: SD of the true contribution vector.
        bias_sd: SD of per-rater additive bias.
        obs_sd: target mean per-rater observation SD (sets Gamma rate).
        alpha0: Gamma shape for rater precision.

    Returns:
        SyntheticTeam with the ScoreMatrix and ground-truth vector.
    """
    if profile not in PROFILES:
        raise ValueError(
            f"Unknown profile {profile!r}; choose from {sorted(PROFILES)}"
        )
    if n < 2:
        raise ValueError(f"Team size must be ≥ 2, got {n}")

    p = dict(
        mu0=mu0, contrib_sd=contrib_sd, bias_sd=bias_sd,
        obs_sd=obs_sd, alpha0=alpha0, central_pull=0.0,
    )
    p.update(PROFILES[profile])

    pool = float(pool) if pool is not None else 10.0 * (n - 1)
    rng = np.random.default_rng(seed)

    # True contribution vector (ground truth).
    c = np.clip(rng.normal(p["mu0"], p["contrib_sd"], n), 0.0, None)

    # Rater parameters: additive bias and precision → per-rater noise SD.
    bias = rng.normal(0.0, p["bias_sd"], n)
    beta0 = p["alpha0"] * (p["obs_sd"] ** 2)
    tau = rng.gamma(p["alpha0"], 1.0 / beta0, n)
    sigma = 1.0 / np.sqrt(tau)

    # Central-tendency: a satisficing rater compresses the contribution
    # range toward the team mean before forming their scores.
    c_mean = float(np.mean(c))
    perceived = c_mean + (1.0 - p["central_pull"]) * (c - c_mean)

    matrix = np.full((n, n), np.nan, dtype=float)
    for j in range(n):
        for i in range(n):
            if i == j:
                continue
            matrix[i, j] = perceived[i] + bias[j] + rng.normal(0.0, sigma[j])
    np.clip(matrix, 0.0, None, out=matrix)

    # Budget renormalisation: each rater column sums to ``pool``.
    for j in range(n):
        col_sum = np.nansum(matrix[:, j])
        if col_sum <= 0:
            raise ValueError(
                f"Degenerate synthetic column {j} (sum={col_sum}); "
                f"adjust seed or parameters"
            )
        matrix[:, j] *= pool / col_sum

    students = [
        StudentInfo(name=f"S{i}", email=f"s{i}@synthetic.team", index=i)
        for i in range(n)
    ]

    sm = ScoreMatrix(
        matrix=matrix,
        team_name=f"synthetic-N{n}-seed{seed}",
        question_label=profile,
        year="synthetic",
        semester="-",
        session_number=0,
        students=students,
        excluded_students=[],
    )

    ground_truth = c / float(np.mean(c)) * 10.0

    return SyntheticTeam(
        score_matrix=sm,
        ground_truth=ground_truth,
        profile=profile,
        seed=seed,
        params={**p, "pool": pool, "n": n},
    )


def generate_cohort(
    sizes: tuple[int, ...] = (4, 5, 6),
    teams_per_size: int = 10,
    *,
    base_seed: int = 0,
    profile: str = "reliable",
    **kwargs,
) -> list[SyntheticTeam]:
    """Generate a deterministic cohort across team sizes.

    Seeds are derived from ``base_seed`` so the whole cohort is
    reproducible from a single integer.
    """
    cohort: list[SyntheticTeam] = []
    for s_idx, n in enumerate(sizes):
        for t in range(teams_per_size):
            seed = base_seed + s_idx * 100_000 + t
            cohort.append(
                generate_team(n, seed, profile=profile, **kwargs)
            )
    return cohort
