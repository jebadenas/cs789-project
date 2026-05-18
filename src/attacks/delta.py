"""Attack Delta metric and the single-outlier Monte-Carlo harness.

Attack Delta (proposal §3.4): the mean absolute difference between a
model's IWF vector under an attack and its IWF vector on the unmodified
scores. Smaller ⇒ more robust.

The single-outlier attack (#4) is stochastic, so it is evaluated by Monte
Carlo: many seeded permutations, reporting the Attack Delta distribution
and — for PeerRank/PeerHITS — convergence behaviour under perturbation
(RQ2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from src.attacks.transforms import single_outlier
from src.models.types import ModelResult
from src.parsing.schemas import ScoreMatrix

ModelFn = Callable[[ScoreMatrix], ModelResult]


def attack_delta(unattacked: ModelResult, attacked: ModelResult) -> float:
    """Mean absolute IWF difference (attacked vs unattacked), NaN-aware.

    Positions where either vector is NaN are skipped. Returns NaN if no
    position is comparable.
    """
    a = np.asarray(unattacked.iwf_vector, dtype=float)
    b = np.asarray(attacked.iwf_vector, dtype=float)
    if a.shape != b.shape:
        raise ValueError(
            f"IWF length mismatch: {a.shape} vs {b.shape}"
        )
    mask = ~(np.isnan(a) | np.isnan(b))
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(a[mask] - b[mask])))


@dataclass(frozen=True)
class MonteCarloResult:
    """Attack Delta distribution over single-outlier permutations."""

    model_name: str
    n_perms: int
    deltas: np.ndarray
    mean: float
    std: float
    min: float
    max: float
    # Iterative-model convergence under perturbation (RQ2).
    nonconverged: int = 0
    mean_iterations: float | None = None
    max_iterations: int | None = None

    @property
    def converged_all(self) -> bool:
        return self.nonconverged == 0


def monte_carlo_single_outlier(
    sm: ScoreMatrix,
    model_fn: ModelFn,
    *,
    n_perms: int = 100,
    seed: int = 0,
) -> MonteCarloResult:
    """Run the single-outlier attack ``n_perms`` times under one model.

    Each permutation draws a fresh outlier rater and a fresh permutation
    from a seeded child RNG, so the whole run is reproducible from
    ``seed``. Returns the Attack Delta distribution and convergence stats.
    """
    base = model_fn(sm)
    model_name = base.model_name
    seeds = np.random.SeedSequence(seed).spawn(n_perms)

    deltas = np.empty(n_perms, dtype=float)
    iters: list[int] = []
    nonconverged = 0

    for k, ss in enumerate(seeds):
        rng = np.random.default_rng(ss)
        attacked_sm = single_outlier(sm, rng=rng)
        res = model_fn(attacked_sm)
        deltas[k] = attack_delta(base, res)
        if res.iterations is not None:
            iters.append(res.iterations)
        if res.converged is False:
            nonconverged += 1

    return MonteCarloResult(
        model_name=model_name,
        n_perms=n_perms,
        deltas=deltas,
        mean=float(np.nanmean(deltas)),
        std=float(np.nanstd(deltas)),
        min=float(np.nanmin(deltas)),
        max=float(np.nanmax(deltas)),
        nonconverged=nonconverged,
        mean_iterations=float(np.mean(iters)) if iters else None,
        max_iterations=int(np.max(iters)) if iters else None,
    )
