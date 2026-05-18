"""Attack runner — attacks × 6 models × (real clean + synthetic).

Applies each attack to every input matrix, runs all six IWF models on the
clean and attacked versions, and records the Attack Delta. The four
deterministic attacks (#1–3 + zero-self full/partial) are run once each;
the stochastic single-outlier attack (#4) is run by Monte Carlo.

Model registry and parsing are reused from the existing pipeline so
attack results sit on the same six models as the rest of the project.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from src.attacks.delta import MonteCarloResult, attack_delta, monte_carlo_single_outlier
from src.attacks.synthetic import SyntheticTeam
from src.attacks.transforms import (
    targeted_downvote,
    uniform_inflation,
    zero_self,
)
from src.batch_runner import MODELS
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics
from src.parsing.schemas import ScoreMatrix

# Deterministic attacks: name → ScoreMatrix transform.
DETERMINISTIC_ATTACKS: dict[str, Callable[[ScoreMatrix], ScoreMatrix]] = {
    "uniform-inflation": uniform_inflation,
    "zero-self-full": lambda sm: zero_self(sm, full=True),
    "zero-self-partial": lambda sm: zero_self(sm, full=False),
    "targeted-downvote": targeted_downvote,
}
SINGLE_OUTLIER = "single-outlier"


@dataclass(frozen=True)
class AttackRecord:
    """One (source, attack, model) Attack Delta result."""

    source: str
    """``real`` or ``synthetic``."""
    team: str
    attack: str
    model_name: str
    delta: Optional[float] = None
    error: Optional[str] = None
    # Single-outlier Monte-Carlo extras.
    mc: Optional[MonteCarloResult] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass
class AttackBatch:
    records: list[AttackRecord] = field(default_factory=list)
    real_matrix_count: int = 0
    synthetic_team_count: int = 0

    @property
    def succeeded(self) -> list[AttackRecord]:
        return [r for r in self.records if r.succeeded]

    def aggregate(
        self, source: str | None = None
    ) -> dict[tuple[str, str], dict]:
        """Mean Attack Delta per (attack, model).

        Args:
            source: if given (``real`` / ``synthetic``), restrict to that
                input source; otherwise pool both.

        For ``single-outlier`` the per-record value is the Monte-Carlo
        mean; the aggregate also carries the pooled MC std for error bars.
        """
        buckets: dict[tuple[str, str], list[float]] = {}
        mc_std: dict[tuple[str, str], list[float]] = {}
        for r in self.succeeded:
            if source is not None and r.source != source:
                continue
            if r.delta is None or np.isnan(r.delta):
                continue
            key = (r.attack, r.model_name)
            buckets.setdefault(key, []).append(r.delta)
            if r.mc is not None:
                mc_std.setdefault(key, []).append(r.mc.std)

        out: dict[tuple[str, str], dict] = {}
        for key, vals in buckets.items():
            out[key] = {
                "mean_delta": float(np.mean(vals)),
                "n": len(vals),
                "mc_std": (
                    float(np.mean(mc_std[key])) if key in mc_std else None
                ),
            }
        return out


def _eval(
    source: str,
    team: str,
    clean: ScoreMatrix,
    model_names: list[str],
    n_perms: int,
    seed: int,
) -> list[AttackRecord]:
    records: list[AttackRecord] = []

    for model_name in model_names:
        model_fn = MODELS[model_name]
        try:
            base = model_fn(clean)
        except Exception as exc:  # degenerate matrix etc. — record, skip
            records.append(AttackRecord(
                source, team, "(baseline)", model_name,
                error=f"{type(exc).__name__}: {exc}",
            ))
            continue

        for attack_name, transform in DETERMINISTIC_ATTACKS.items():
            try:
                attacked = transform(clean)
                res = model_fn(attacked)
                records.append(AttackRecord(
                    source, team, attack_name, model_name,
                    delta=attack_delta(base, res),
                ))
            except Exception as exc:
                records.append(AttackRecord(
                    source, team, attack_name, model_name,
                    error=f"{type(exc).__name__}: {exc}",
                ))

        try:
            mc = monte_carlo_single_outlier(
                clean, model_fn, n_perms=n_perms, seed=seed,
            )
            records.append(AttackRecord(
                source, team, SINGLE_OUTLIER, model_name,
                delta=mc.mean, mc=mc,
            ))
        except Exception as exc:
            records.append(AttackRecord(
                source, team, SINGLE_OUTLIER, model_name,
                error=f"{type(exc).__name__}: {exc}",
            ))

    return records


def run_attacks(
    *,
    real_dir: Path | None = None,
    synthetic: list[SyntheticTeam] | None = None,
    model_names: list[str] | None = None,
    n_perms: int = 100,
    seed: int = 0,
    progress: bool = True,
) -> AttackBatch:
    """Run all attacks across real and/or synthetic matrices.

    Args:
        real_dir: directory of CSVs; each parsed matrix is attacked.
        synthetic: pre-generated synthetic teams to attack.
        model_names: subset of the 6 models (default all).
        n_perms: single-outlier Monte-Carlo permutations per (team, model).
        seed: Monte-Carlo seed (reproducible).
        progress: print progress to stderr.

    Returns:
        AttackBatch with all records.
    """
    model_names = model_names or list(MODELS.keys())
    unknown = [m for m in model_names if m not in MODELS]
    if unknown:
        raise ValueError(f"Unknown model(s): {', '.join(unknown)}")
    if real_dir is None and not synthetic:
        raise ValueError("Provide real_dir, synthetic teams, or both")

    batch = AttackBatch()

    if real_dir is not None:
        csvs = discover_csvs(real_dir)
        if not csvs:
            raise FileNotFoundError(f"No CSV files found in {real_dir}")
        for idx, csv_path in enumerate(csvs):
            if progress:
                print(f"  real [{idx + 1}/{len(csvs)}] {csv_path.name}",
                      file=sys.stderr, flush=True)
            matrices, _ = parse_session_with_diagnostics(csv_path)
            batch.real_matrix_count += len(matrices)
            for (team, label), sm in sorted(matrices.items()):
                batch.records.extend(_eval(
                    "real", f"{team} / {label}", sm,
                    model_names, n_perms, seed,
                ))

    if synthetic:
        batch.synthetic_team_count = len(synthetic)
        for idx, st in enumerate(synthetic):
            if progress and idx % 10 == 0:
                print(f"  synthetic [{idx + 1}/{len(synthetic)}]",
                      file=sys.stderr, flush=True)
            batch.records.extend(_eval(
                "synthetic", st.score_matrix.team_name, st.score_matrix,
                model_names, n_perms, seed,
            ))

    if progress:
        ok = len(batch.succeeded)
        print(f"  attacks done: {ok}/{len(batch.records)} records ok",
              file=sys.stderr)

    return batch
