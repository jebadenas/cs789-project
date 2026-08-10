"""RQ1 attacks under the absolute vs relative view (handoff-9b, Tasks 3 & 4).

Cross-model Δ is blind to uniform level shifts by construction, so it cannot see
an *inflationary* attack — whole-team zero-self collusion raises everyone's
institutional weight with no loser. Here we report every attack transform × model
under two lenses:

- **relative** — mean |Δ| after putting both clean and attacked weights on a
  common team mean of 10 (does it change *who gets what*?);
- **absolute** — the change in the team-mean ``baseline_cs399`` weight and each
  student's absolute weight (does it change the *level* everyone receives?).

Transforms are then classified **redistributive** (relative change, has a loser)
vs **inflationary** (level change, no loser, invisible relatively). The advanced
models self-normalise to mean 10, so their absolute team-mean change is ~0 —
structural immunity to inflation the relative view cannot express.

Task 4 asks whether an inflationary attack is *detectable*: the attack signature
(N=5 → 12.50, N=6 → 12.00) overlaps the natural range of observed team means, so
we report the overlap honestly rather than manufacturing a detector.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.attacks.transforms import (
    single_outlier, targeted_downvote, uniform_inflation, zero_self,
)
from src.batch_runner import MODELS
from src.dynamics2.dataio import load_matrices
from src.models.baseline import baseline_cs399

DETERMINISTIC = {
    "uniform-inflation": uniform_inflation,
    "zero-self-full": lambda sm: zero_self(sm, full=True),
    "zero-self-partial": lambda sm: zero_self(sm, full=False),
    "targeted-downvote": targeted_downvote,
}
# cs399 is the absolute/institutional model; the registry adds the mean-10 models.
MODELS_ABS = {"cs399": baseline_cs399, **MODELS}


def _metrics(before: np.ndarray, after: np.ndarray) -> dict | None:
    mask = ~(np.isnan(before) | np.isnan(after))
    if mask.sum() < 2:
        return None
    b, a = before[mask], after[mask]
    mb, ma = b.mean(), a.mean()
    if mb == 0 or ma == 0:
        return None
    bn, an = b / mb * 10.0, a / ma * 10.0  # strip level → relative standing
    return {
        "abs_teammean_delta": float(ma - mb),
        "abs_teammean_pct": float((ma - mb) / mb * 100.0),
        "abs_student_delta": float(np.mean(np.abs(a - b))),
        "rel_delta": float(np.mean(np.abs(an - bn))),
    }


def _stochastic_metrics(sm, fn, n_perms: int, seed: int) -> dict | None:
    try:
        base = fn(sm).iwf_vector
    except Exception:
        return None
    seeds = np.random.SeedSequence(seed).spawn(n_perms)
    acc: list[dict] = []
    for ss in seeds:
        rng = np.random.default_rng(ss)
        try:
            after = fn(single_outlier(sm, rng=rng)).iwf_vector
        except Exception:
            continue
        m = _metrics(base, after)
        if m is not None:
            acc.append(m)
    if not acc:
        return None
    return {k: float(np.mean([d[k] for d in acc])) for k in acc[0]}


def absolute_vs_relative(n_perms: int = 100, seed: int = 0) -> pd.DataFrame:
    """Per-(attack, model) absolute and relative effects, averaged over matrices."""
    records = load_matrices()
    acc: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        for model_name, fn in MODELS_ABS.items():
            try:
                base = fn(rec.sm).iwf_vector
            except Exception:
                continue
            for atk_name, transform in DETERMINISTIC.items():
                try:
                    m = _metrics(base, fn(transform(rec.sm)).iwf_vector)
                except Exception:
                    m = None
                if m is not None:
                    acc.setdefault((atk_name, model_name), []).append(m)
            m = _stochastic_metrics(rec.sm, fn, n_perms, seed)
            if m is not None:
                acc.setdefault(("single-outlier", model_name), []).append(m)

    rows = []
    for (atk, model), ms in acc.items():
        row = {"attack": atk, "model": model, "n": len(ms)}
        for k in ("abs_teammean_delta", "abs_teammean_pct", "abs_student_delta", "rel_delta"):
            row[k] = float(np.mean([d[k] for d in ms]))
        row["abs_teammean_pct_absmean"] = float(np.mean([abs(d["abs_teammean_pct"]) for d in ms]))
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(["attack", "model"]).reset_index(drop=True)

    # Classify each transform from the cs399 (absolute-meaningful) view.
    cls = {}
    for atk in df["attack"].unique():
        r = df[(df.attack == atk) & (df.model == "cs399")]
        if r.empty:
            cls[atk] = "unknown"
            continue
        abs_pct = float(r["abs_teammean_pct_absmean"].iloc[0])
        rel = float(r["rel_delta"].iloc[0])
        cls[atk] = "inflationary" if (abs_pct > 5.0 and rel < abs_pct / 10.0) else "redistributive"
    df["transform_class"] = df["attack"].map(cls)
    return df


def detectability(n_bins: int = 20) -> tuple[pd.DataFrame, dict]:
    """Task 4: observed team-mean cs399 vs attack-implied values; low self-alloc."""
    records = load_matrices()
    rows = []
    for rec in records:
        m = rec.sm.matrix.astype(float)
        n = m.shape[0]
        cs = baseline_cs399(rec.sm).iwf_vector
        team_mean = float(np.nanmean(cs))
        colsum = np.nansum(m, axis=0)
        diag = np.array([m[j, j] for j in range(n)], dtype=float)
        active = colsum > 0
        self_alloc = float(np.nanmean(diag[active] / colsum[active])) if active.any() else np.nan
        implied = {5: 12.5, 6: 12.0}.get(n, 10.0 * n / (n - 1))
        rows.append({"csv_path": rec.csv_path, "team_name": rec.team_name,
                    "question_label": rec.question_label, "N": n,
                    "team_mean_cs399": team_mean, "mean_self_alloc": self_alloc,
                    "attack_implied_mean": implied,
                    "exceeds_implied": team_mean >= implied})
    df = pd.DataFrame(rows)

    # Detectability summary: at a threshold = the attack-implied mean, how many
    # clean teams already exceed it (false positives)?
    summary = {}
    for n in sorted(df["N"].unique()):
        sub = df[df["N"] == n]
        implied = float(sub["attack_implied_mean"].iloc[0])
        summary[f"N={n}"] = {
            "n_teams": int(len(sub)),
            "implied_mean": implied,
            "observed_max": float(sub["team_mean_cs399"].max()),
            "n_exceed_implied_naturally": int((sub["team_mean_cs399"] >= implied).sum()),
            "n_above_10_5": int((sub["team_mean_cs399"] > 10.5).sum()),
            "mean_self_alloc_median": float(sub["mean_self_alloc"].median()),
            "neutral_self_alloc": 1.0 / n,
        }
    return df, summary
