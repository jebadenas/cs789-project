"""Audit-fix regeneration and before/after comparison (handoff-9, Tasks 5/7/8).

Writes to the parallel path ``output/audit_fix/`` (and, for the attack-by-state
tables the handoff names explicitly, ``output/attacks/attack_by_state*.csv``),
leaving all pre-fix outputs untouched.

Run:
    python3 -m src.audit            # everything (delta+rq3+by-state, then attacks)
    python3 -m src.audit delta      # Δ + RQ3 + Δ-by-state only (fast)
    python3 -m src.audit attacks    # per-matrix attack-by-state only (slow)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.audit import absolute as absmod
from src.audit import attacks_by_state as ab
from src.audit import regen
from src.dynamics2.dataio import OUTPUT_DIR as DYN2_OUT

OUT = Path("output") / "audit_fix"
ATTACK_OUT = Path("output") / "attacks"
STATE_ORDER_FULL = [
    "Silent-flat", "Silent-lone-dissenter", "Silent-incomparable",
    "Contested", "No standout", "One at bottom", "One at top", "Both ends",
]


def _states() -> pd.DataFrame:
    path = DYN2_OUT / "matrix_states.csv"
    if not path.exists():
        sys.exit(f"{path} not found — run `python3 -m src.dynamics2 gates` first.")
    return pd.read_csv(path)


def _write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"  Saved {path} ({len(df)} rows)", flush=True)


# --------------------------------------------------------------------------- #
# Δ + RQ3 + Δ-by-state
# --------------------------------------------------------------------------- #

def run_delta() -> dict:
    print("Computing pre/post cross-model Δ (only baseline changed)...", flush=True)
    pre_reg, post_reg = regen._registries()
    pre_map = regen.matrix_deltas(pre_reg)
    post_map = regen.matrix_deltas(post_reg)

    b = regen.load()
    pre_arr = regen._delta_array(pre_map, b.fm)
    post_arr = regen._delta_array(post_map, b.fm)

    # Task 1 record: WebPA↔baseline correlation, and per-model team means (Task 2).
    diag = _model_diagnostics()
    _write(diag, OUT / "model_diagnostics.csv")

    # RQ3 before/after (Task 5.3).
    rq3 = pd.DataFrame([regen.rq3_stats(b, pre_arr, "pre-fix"),
                        regen.rq3_stats(b, post_arr, "post-fix")])
    _write(rq3, OUT / "rq3_before_after.csv")
    print("  RQ3 raw atyp–Δ  pre=%+.3f post=%+.3f | partial pre=%+.3f post=%+.3f"
          % (rq3.raw_atyp_delta_r[0], rq3.raw_atyp_delta_r[1],
             rq3.partial_atyp_delta_r[0], rq3.partial_atyp_delta_r[1]), flush=True)

    # Δ-by-state before/after (Task 8) + the ordering stop-trigger.
    states = _states()
    pre_bs = regen.delta_by_state(pre_map, states).rename(
        columns={"n": "n", "mean": "pre_mean", "median": "pre_median"})
    post_bs = regen.delta_by_state(post_map, states).rename(
        columns={"mean": "post_mean", "median": "post_median"})
    bs = pre_bs.merge(post_bs[["state", "post_mean", "post_median"]], on="state")
    bs["state"] = pd.Categorical(bs["state"], STATE_ORDER_FULL, ordered=True)
    bs = bs.sort_values("state")
    _write(bs, OUT / "delta_by_state.csv")

    _check_ordering(pre_map, post_map, states)

    # Kruskal–Wallis with and without Silent, pre and post (Task 8).
    stats_rows = []
    pairwise_frames = []
    for label, dmap in (("pre-fix", pre_map), ("post-fix", post_map)):
        for excl in (False, True):
            s = regen.state_group_test(dmap, states, exclude_silent=excl)
            stats_rows.append({"variant": label, "silent_excluded": excl,
                               "H": s["H"], "p": s["p"], "n": s["n"], "k": s["k"],
                               "epsilon_squared": s["epsilon_squared"]})
            if excl:
                pw = pd.DataFrame(s["pairwise"])
                pw.insert(0, "variant", label)
                pairwise_frames.append(pw)
    _write(pd.DataFrame(stats_rows), OUT / "delta_by_state_stats.csv")
    _write(pd.concat(pairwise_frames, ignore_index=True),
           OUT / "delta_by_state_pairwise.csv")

    return {"pre_map": pre_map, "post_map": post_map}


def _model_diagnostics() -> pd.DataFrame:
    """WebPA↔baseline correlation (Task 1) + per-model team means (Task 2)."""
    from src.models.baseline import baseline_average
    from src.models.peerhits_exclude import peerhits_exclude
    from src.models.peerrank_exclude import peerrank_exclude
    from src.models.webpa import webpa
    from src.dynamics2.dataio import load_matrices

    per_matrix_r = []
    means = {"baseline": [], "webpa": [], "peerrank-exclude": [], "peerhits-exclude": []}
    for rec in load_matrices():
        w = webpa(rec.sm).iwf_vector
        bl = baseline_average(rec.sm).iwf_vector
        mask = ~(np.isnan(w) | np.isnan(bl))
        if mask.sum() >= 3 and np.std(w[mask]) > 0 and np.std(bl[mask]) > 0:
            per_matrix_r.append(np.corrcoef(w[mask], bl[mask])[0, 1])
        means["webpa"].append(np.nanmean(w))
        means["baseline"].append(np.nanmean(bl))
        try:
            means["peerrank-exclude"].append(np.nanmean(peerrank_exclude(rec.sm).iwf_vector))
        except Exception:
            pass
        means["peerhits-exclude"].append(np.nanmean(peerhits_exclude(rec.sm).iwf_vector))

    rows = [{"metric": "webpa_baseline_corr_mean", "value": float(np.mean(per_matrix_r))},
            {"metric": "webpa_baseline_corr_median", "value": float(np.median(per_matrix_r))}]
    for k, v in means.items():
        rows.append({"metric": f"team_mean_{k}_min", "value": float(np.nanmin(v))})
        rows.append({"metric": f"team_mean_{k}_max", "value": float(np.nanmax(v))})
    return pd.DataFrame(rows)


def _check_ordering(pre_map: dict, post_map: dict, states: pd.DataFrame) -> None:
    pre = regen.delta_by_state(pre_map, states).sort_values("median")["state"].tolist()
    post = regen.delta_by_state(post_map, states).sort_values("median")["state"].tolist()
    if pre == post:
        print("  Δ-by-state median ordering UNCHANGED after fix (stop-trigger clear).",
              flush=True)
    else:
        print("  *** STOP-AND-REPORT: Δ-by-state median ordering CHANGED ***",
              file=sys.stderr, flush=True)
        print(f"    pre : {pre}", file=sys.stderr, flush=True)
        print(f"    post: {post}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Attack-by-state
# --------------------------------------------------------------------------- #

def run_attacks(n_perms: int = 100) -> None:
    print(f"Running attacks per matrix (all 417, n_perms={n_perms})...", flush=True)
    states = _states()
    rows = ab.attack_rows_per_matrix(n_perms=n_perms)
    rows = ab.join_state(rows, states)
    _write(rows, ATTACK_OUT / "attack_by_state_permatrix.csv")

    by_state = ab.attack_by_state(rows)
    _write(by_state, ATTACK_OUT / "attack_by_state.csv")

    # Task 8: does attack Δ vary by state once Silent is excluded? Per model, test
    # each matrix's mean attack Δ (pooled over attacks) across states, with the
    # same Kruskal–Wallis + effect-size machinery used for cross-model Δ.
    key_cols = ["csv_path", "team_name", "question_label"]
    stat_rows = []
    for model in sorted(rows["model"].dropna().unique()):
        sub = rows[(rows["model"] == model) & rows["delta"].notna()]
        agg = sub.groupby(key_cols)["delta"].mean()
        dmap = {k: float(v) for k, v in agg.items()}
        sub_states = states[states.set_index(key_cols).index.isin(dmap)].copy()
        for excl in (False, True):
            try:
                s = regen.state_group_test(dmap, sub_states, exclude_silent=excl)
                stat_rows.append({"model": model, "silent_excluded": excl,
                                  "H": s["H"], "p": s["p"], "n": s["n"], "k": s["k"],
                                  "epsilon_squared": s["epsilon_squared"]})
            except Exception:
                stat_rows.append({"model": model, "silent_excluded": excl,
                                  "H": np.nan, "p": np.nan, "n": np.nan, "k": np.nan,
                                  "epsilon_squared": np.nan})
    _write(pd.DataFrame(stat_rows), OUT / "attack_by_state_stats.csv")


def run_absolute(n_perms: int = 100) -> None:
    """Tasks 3 & 4: RQ1 attacks under absolute vs relative views + detectability."""
    print("Absolute-vs-relative attack analysis (handoff-9b Tasks 3/4)...", flush=True)
    avr = absmod.absolute_vs_relative(n_perms=n_perms)
    _write(avr, ATTACK_OUT / "attack_absolute_vs_relative.csv")

    # Headline verification: zero-self-full under cs399.
    zs = avr[(avr.attack == "zero-self-full") & (avr.model == "cs399")]
    if not zs.empty:
        print(f"  zero-self-full cs399: abs team-mean {zs.abs_teammean_pct.iloc[0]:+.2f}% "
              f"| relative Δ {zs.rel_delta.iloc[0]:.4f}  (expect ~+22%, ~0)", flush=True)
    for atk in avr["attack"].unique():
        cls = avr[avr.attack == atk]["transform_class"].iloc[0]
        print(f"    {atk:18s} → {cls}", flush=True)

    det_df, det_summary = absmod.detectability()
    _write(det_df, OUT / "inflation_detectability_permatrix.csv")
    _write(pd.DataFrame(det_summary).T.reset_index().rename(columns={"index": "group"}),
           OUT / "inflation_detectability.csv")
    for grp, s in det_summary.items():
        print(f"  {grp}: implied {s['implied_mean']:.2f}, "
              f"{s['n_exceed_implied_naturally']}/{s['n_teams']} teams already ≥ implied; "
              f"observed max {s['observed_max']:.2f}", flush=True)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd in ("delta", "all"):
        run_delta()
    if cmd in ("absolute", "all"):
        run_absolute()
    if cmd in ("attacks", "all"):
        run_attacks()
    print(f"\nDone. Comparison artefacts in {OUT}/ and {ATTACK_OUT}/attack_*.csv",
          flush=True)


if __name__ == "__main__":
    main()
