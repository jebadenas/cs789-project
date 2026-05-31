"""Research-validity checks on the RQ3 dynamics results (handoff-2).

Analysis only — does NOT change the pipeline. Reconstructs the exact
standardised feature matrix the dynamics pipeline produced (from the saved
output/dynamics CSVs), then runs the requested check. Each subcommand writes
a deliverable CSV under output/dynamics/ and prints a verdict.

Run:
    python3 -m src.dynamics.validity check   # sanity: reproduce headline numbers
    python3 -m src.dynamics.validity a        # k=4 null comparison + archetypes
    python3 -m src.dynamics.validity b        # team-level RQ3 recompute
    python3 -m src.dynamics.validity c        # circularity / partial correlation
    python3 -m src.dynamics.validity d        # assortativity conditioning
    python3 -m src.dynamics.validity e        # exclusion-consistency audit
"""

from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, pearsonr, mannwhitneyu, ttest_ind, t as t_dist
from sklearn.preprocessing import StandardScaler

from src.dynamics.archetypes import fit_aa, sweep_archetypes
from src.dynamics.classifier import (
    atypicality_scores, chi_square_flag, fit_precision,
)
from src.dynamics.features import FEATURE_NAMES
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics

OUT = Path("output/dynamics")
DATA_DIR = Path("data")
ALPHA = 0.05


@dataclass
class Bundle:
    fm: pd.DataFrame            # feature_matrix.csv (raw 25 features + delta + keys)
    cls: pd.DataFrame           # classifications.csv (atypicality, flag, degenerate)
    X_raw: np.ndarray           # (n, 25) imputed raw features
    Xz: np.ndarray              # (n, p) standardised, zero-var dropped
    feat_names: list[str]       # names kept in Xz
    scaler: StandardScaler
    precision: np.ndarray
    centroid: np.ndarray
    dist: np.ndarray            # Mahalanobis distance (atypicality)
    dist2: np.ndarray           # squared
    flag: np.ndarray            # Typical / Anomalous
    cutoff: float
    df: int
    degenerate: np.ndarray      # bool
    delta: np.ndarray


def load() -> Bundle:
    fm = pd.read_csv(OUT / "feature_matrix.csv")
    cls = pd.read_csv(OUT / "classifications.csv")
    # The two files are written in the same row order by the pipeline; verify.
    assert len(fm) == len(cls), "feature_matrix / classifications length mismatch"
    if not np.allclose(fm["delta"].values, cls["delta"].values, atol=1e-6):
        # fall back to an explicit merge on the keys
        keys = ["csv_path", "team_name", "question_label"]
        cls = fm[keys].merge(cls, on=keys, how="left")

    X_raw = fm[FEATURE_NAMES].values.astype(float)
    scaler = StandardScaler().fit(X_raw)
    X_scaled = scaler.transform(X_raw)
    mask = scaler.var_ > 1e-10
    Xz = X_scaled[:, mask]
    feat_names = [n for n, k in zip(FEATURE_NAMES, mask) if k]

    degenerate = cls["degenerate"].values.astype(bool)
    delta = fm["delta"].values.astype(float)
    clean = ~degenerate

    precision = fit_precision(Xz)
    centroid = Xz[clean].mean(axis=0)
    dist, dist2 = atypicality_scores(Xz, precision, centroid=centroid)
    df = int(Xz.shape[1])
    flag, cutoff = chi_square_flag(dist2, df=df, alpha=ALPHA)

    return Bundle(fm, cls, X_raw, Xz, feat_names, scaler, precision, centroid,
                  dist, dist2, flag, cutoff, df, degenerate, delta)


def _quiet(fn, *a, **k):
    """Run fn while swallowing its stdout (AA sweep is chatty)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def _partial_p(r: float, n: int, n_controls: int) -> float:
    df = n - 2 - n_controls
    if df <= 0 or abs(r) >= 1:
        return float("nan")
    t = r * np.sqrt(df / (1 - r ** 2))
    return float(2 * t_dist.sf(abs(t), df))


# ---------------------------------------------------------------------------
# check — reproduce the headline numbers so the rest can be trusted
# ---------------------------------------------------------------------------
def cmd_check(b: Bundle) -> None:
    clean = ~b.degenerate
    r_clean, p_clean = pearsonr(b.dist[clean], b.delta[clean])
    r_full, p_full = pearsonr(b.dist, b.delta)
    n_anom = int((b.flag == "Anomalous").sum())
    print(f"n={len(b.fm)}  clean={int(clean.sum())}  df={b.df}  cutoff={b.cutoff:.2f}")
    print(f"atypicality–Δ  full : r={r_full:+.3f} (n={len(b.delta)})")
    print(f"atypicality–Δ  clean: r={r_clean:+.3f} (n={int(clean.sum())})")
    print(f"Anomalous flags: {n_anom}")
    # cross-check against saved atypicality column
    if "atypicality" in b.cls:
        max_diff = float(np.max(np.abs(b.dist - b.cls["atypicality"].values)))
        print(f"max |reconstructed - saved atypicality| = {max_diff:.2e}")


# ---------------------------------------------------------------------------
# A — structureless-null comparison for the k=4 stability bump
# ---------------------------------------------------------------------------
def cmd_a(b: Bundle, n_nulls: int = 30, n_bootstrap: int = 50) -> None:
    import time
    ks = list(range(2, 9))

    # Observed stability: reuse the saved sweep (identical pipeline).
    stab = pd.read_csv(OUT / "archetype_stability.csv").set_index("k")
    observed = {k: float(stab.loc[k, "bootstrap_stability"]) for k in ks}

    # Null: independently permute each standardised feature column (preserves
    # per-feature marginals, destroys joint structure). Run the identical
    # AA + bootstrap-stability pipeline on each null draw.
    print(f"Running {n_nulls} structureless-null draws "
          f"(k=2..8, n_bootstrap={n_bootstrap})...", flush=True)
    null_stab = {k: [] for k in ks}
    t0 = time.time()
    for d in range(n_nulls):
        rng = np.random.default_rng(1000 + d)
        Xn = np.column_stack([rng.permutation(b.Xz[:, j])
                              for j in range(b.Xz.shape[1])])
        res = _quiet(sweep_archetypes, Xn, range(2, 9),
                     n_bootstrap=n_bootstrap)
        for r in res:
            null_stab[r.k].append(r.bootstrap_stability)
        el = time.time() - t0
        print(f"  {d + 1}/{n_nulls}  ({el:.0f}s, {el/(d+1):.1f}s/draw)", flush=True)

    rows = []
    for k in ks:
        arr = np.array(null_stab[k])
        rows.append({
            "k": k,
            "observed_stability": round(observed[k], 4),
            "null_mean": round(float(arr.mean()), 4),
            "null_sd": round(float(arr.std()), 4),
            "obs_minus_null": round(observed[k] - float(arr.mean()), 4),
            "obs_z_vs_null": round((observed[k] - arr.mean()) / (arr.std() + 1e-9), 2),
        })
    df_out = pd.DataFrame(rows)
    path = OUT / "k_null_comparison.csv"
    df_out.to_csv(path, index=False)
    print("\n" + df_out.to_string(index=False))

    # Inspect the k=4 archetypes on the real data.
    Z, S, _ = _quiet(fit_aa, b.Xz, 4)
    Z_raw = b.scaler.inverse_transform(
        _unmask(Z, b.scaler, b.feat_names))
    loads = S.argmax(axis=1)
    load_counts = {int(a): int((loads == a).sum()) for a in range(4)}
    # pairwise distance between archetypes (standardised space)
    pdist = np.array([[np.linalg.norm(Z[i] - Z[j]) for j in range(4)]
                      for i in range(4)])
    arch_df = pd.DataFrame(Z_raw, columns=FEATURE_NAMES)
    arch_df.insert(0, "load_count", [load_counts[i] for i in range(4)])
    arch_df.insert(0, "archetype", [f"A{i}" for i in range(4)])
    arch_path = OUT / "k4_archetypes.csv"
    arch_df.to_csv(arch_path, index=False)

    print(f"\nk=4 load counts: {load_counts}")
    print("k=4 pairwise archetype distance (standardised):")
    print(np.round(pdist, 2))
    key = [n for n in ["non_submitter_frac", "mean_self_share", "mean_rater_std",
                       "gini_in_degree", "reciprocity", "assortativity"]
           if n in FEATURE_NAMES]
    print("\nk=4 archetypes (raw scale, selected features):")
    print(arch_df[["archetype", "load_count"] + key].to_string(index=False))

    min_off = pdist[~np.eye(4, dtype=bool)].min()
    print(f"\n  Saved {path} and {arch_path}")
    print(f"  min off-diagonal archetype distance = {min_off:.2f}")
    _verdict_a(df_out, load_counts, min_off)


def _unmask(Z_nz, scaler, feat_names):
    """Pad zero-var-dropped archetypes back to full feature dim for inverse_transform."""
    full = np.zeros((Z_nz.shape[0], len(FEATURE_NAMES)))
    idx = [FEATURE_NAMES.index(n) for n in feat_names]
    full[:, idx] = Z_nz
    return full


def _verdict_a(df_out, load_counts, min_off):
    k4_obs = float(df_out.loc[df_out.k == 4, "observed_stability"].iloc[0])
    k4_null = float(df_out.loc[df_out.k == 4, "null_mean"].iloc[0])
    null_bumps = k4_null > df_out.loc[df_out.k == 3, "null_mean"].iloc[0]
    empty = any(c <= 2 for c in load_counts.values())
    print("\nVERDICT (A):")
    if null_bumps and (k4_obs - k4_null) < 0.15:
        print("  ARTEFACT — the structureless null reproduces the k=4 bump; the "
              "rebound reflects feature-space symmetry, not genuine groups.")
    elif empty or min_off < 1.0:
        print("  ARTEFACT — k=4 archetypes are near-duplicate/near-empty; not "
              "four substantive groups.")
    else:
        print("  POSSIBLY GENUINE — null is flat at k=4 but real data bumps and "
              "archetypes are distinct/populated. Reconsider binary framing.")


# ---------------------------------------------------------------------------
# B — team-level RQ3 recompute
# ---------------------------------------------------------------------------
def cmd_b(b: Bundle) -> None:
    df = b.fm[["csv_path", "team_name", "question_label"]].copy()
    df["atypicality"] = b.dist
    df["delta"] = b.delta
    df["flag"] = b.flag
    df["degenerate"] = b.degenerate
    clean = df[~df["degenerate"]].copy()

    n_rows = len(clean)
    clean["team_id"] = clean["csv_path"] + " :: " + clean["team_name"]
    per_team = clean.groupby("team_id")
    n_teams = per_team.ngroups
    rows_per_team = per_team.size()

    print(f"clean matrices (rows): {n_rows}")
    print(f"distinct teams:        {n_teams}")
    print(f"rows-per-team: mean={rows_per_team.mean():.2f} "
          f"min={rows_per_team.min()} max={rows_per_team.max()}")
    print("rows-per-team distribution: "
          f"{rows_per_team.value_counts().sort_index().to_dict()}")

    # Row-level (headline) for reference
    r_row, p_row = pearsonr(clean["atypicality"], clean["delta"])

    # Team-level aggregation
    agg = per_team.agg(
        mean_atyp=("atypicality", "mean"),
        mean_delta=("delta", "mean"),
        n_anom=("flag", lambda s: (s == "Anomalous").sum()),
        n=("flag", "size"),
    ).reset_index()
    agg["team_flag"] = np.where(agg["n_anom"] >= agg["n"] / 2,
                                "Anomalous", "Typical")
    r_team, p_team = pearsonr(agg["mean_atyp"], agg["mean_delta"])

    a = agg.loc[agg.team_flag == "Anomalous", "mean_delta"]
    t = agg.loc[agg.team_flag == "Typical", "mean_delta"]
    welch_t, welch_p = ttest_ind(a, t, equal_var=False)
    mw_u, mw_p = mannwhitneyu(a, t, alternative="two-sided")

    print(f"\nrow-level  atypicality–Δ: r={r_row:+.3f} p={p_row:.2e} n={n_rows}")
    print(f"team-level atypicality–Δ: r={r_team:+.3f} p={p_team:.2e} n={n_teams}")
    print(f"\nteam-level group contrast (majority-vote flag):")
    print(f"  Anomalous n={len(a)} meanΔ={a.mean():.3f} | "
          f"Typical n={len(t)} meanΔ={t.mean():.3f}")
    print(f"  Welch p={welch_p:.2e}  Mann-Whitney p={mw_p:.2e}")

    summary = pd.DataFrame([
        {"level": "row", "r": r_row, "p": p_row, "n": n_rows,
         "anom_n": int((clean.flag == "Anomalous").sum()),
         "anom_meanD": clean.loc[clean.flag == "Anomalous", "delta"].mean(),
         "typ_meanD": clean.loc[clean.flag == "Typical", "delta"].mean(),
         "welch_p": np.nan, "mw_p": np.nan},
        {"level": "team", "r": r_team, "p": p_team, "n": n_teams,
         "anom_n": len(a), "anom_meanD": a.mean(), "typ_meanD": t.mean(),
         "welch_p": welch_p, "mw_p": mw_p},
    ])
    path = OUT / "rq3_team_level.csv"
    summary.to_csv(path, index=False)
    print(f"\n  Saved {path}")
    print("\nVERDICT (B):")
    survives = (p_team < 0.05) and (mw_p < 0.05)
    print(f"  {'SURVIVES' if survives else 'WEAKENS'} at the honest sample size "
          f"(n_teams={n_teams}): team-level r={r_team:+.3f} (p={p_team:.2e}), "
          f"contrast MW p={mw_p:.2e}.")


# ---------------------------------------------------------------------------
# C — circularity / partial correlation
# ---------------------------------------------------------------------------
def cmd_c(b: Bundle) -> None:
    clean = ~b.degenerate
    delta = b.delta[clean]
    atyp = b.dist[clean]

    # Per-feature correlation with Δ (raw features, clean rows)
    rows = []
    for j, name in enumerate(FEATURE_NAMES):
        col = b.X_raw[clean, j]
        if np.std(col) < 1e-12:
            r, p = float("nan"), float("nan")
        else:
            r, p = pearsonr(col, delta)
        rows.append({"feature": name, "pearson_r": round(r, 4),
                     "abs_r": round(abs(r), 4) if r == r else np.nan,
                     "p_value": p})
    feat_df = pd.DataFrame(rows).sort_values("abs_r", ascending=False)

    # Low-level controls both atypicality and Δ plausibly share
    controls = _low_level_controls(b)[clean]
    ctrl_names = ["mean_rater_std", "mean_self_share", "n_raters", "team_size"]

    raw_r, raw_p = pearsonr(atyp, delta)
    pr, ppart = _partial_correlation(atyp, delta, controls)

    print("Top features by |corr with Δ| (clean):")
    print(feat_df.head(10).to_string(index=False))
    print(f"\nraw atypicality–Δ:     r={raw_r:+.3f} p={raw_p:.2e}")
    print(f"partial (control {ctrl_names}):")
    print(f"                       r={pr:+.3f} p={ppart:.2e}")

    out = feat_df.copy()
    meta = pd.DataFrame([
        {"feature": "__RAW_atypicality_delta__", "pearson_r": round(raw_r, 4),
         "abs_r": np.nan, "p_value": raw_p},
        {"feature": "__PARTIAL_atypicality_delta__", "pearson_r": round(pr, 4),
         "abs_r": np.nan, "p_value": ppart},
    ])
    out = pd.concat([meta, out], ignore_index=True)
    path = OUT / "rq3_partial_correlation.csv"
    out.to_csv(path, index=False)
    print(f"\n  Saved {path}")
    print("\nVERDICT (C):")
    if abs(pr) < 0.1 or ppart > 0.05:
        print("  SHARED-VARIANCE — partial correlation collapses; atypicality and "
              "manipulability both reflect the same structural irregularity.")
    elif abs(pr) < abs(raw_r) * 0.6:
        print(f"  PARTLY SHARED — partial r={pr:+.3f} is attenuated vs raw "
              f"{raw_r:+.3f} but survives; report both, soften the causal claim.")
    else:
        print(f"  INDEPENDENT — partial r={pr:+.3f} holds up; atypicality carries "
              "information beyond shared low-level structure.")


def _low_level_controls(b: Bundle) -> np.ndarray:
    """(n,4): mean_rater_std, mean_self_share, n_raters, team_size."""
    mrs = b.X_raw[:, FEATURE_NAMES.index("mean_rater_std")]
    mss = b.X_raw[:, FEATURE_NAMES.index("mean_self_share")]
    sizes = _matrix_sizes(b.fm)
    return np.column_stack([mrs, mss, sizes["n_raters"], sizes["team_size"]])


def _matrix_sizes(fm: pd.DataFrame) -> pd.DataFrame:
    """Recover team_size and n_raters per matrix by re-parsing the CSVs."""
    lookup: dict[tuple, tuple[int, int]] = {}
    for csv_path in discover_csvs(DATA_DIR):
        matrices, _ = parse_session_with_diagnostics(csv_path)
        for (team, label), sm in matrices.items():
            n = len(sm.students)
            A = sm.matrix
            n_raters = 0
            for j in range(n):
                peer = np.delete(A[:, j], j)
                if not np.all(np.isnan(peer)):
                    n_raters += 1
            lookup[(str(csv_path), team, label)] = (n, n_raters)
    team_size, n_raters = [], []
    for _, row in fm.iterrows():
        key = (row["csv_path"], row["team_name"], row["question_label"])
        n, nr = lookup.get(key, (np.nan, np.nan))
        team_size.append(n)
        n_raters.append(nr)
    return pd.DataFrame({"team_size": team_size, "n_raters": n_raters})


def _partial_correlation(x, y, Z):
    """Partial corr of x,y controlling for columns of Z (residualisation)."""
    Z1 = np.column_stack([np.ones(len(x)), Z])
    bx, *_ = np.linalg.lstsq(Z1, x, rcond=None)
    by, *_ = np.linalg.lstsq(Z1, y, rcond=None)
    rx = x - Z1 @ bx
    ry = y - Z1 @ by
    r, _ = pearsonr(rx, ry)
    return r, _partial_p(r, len(x), Z.shape[1])


# ---------------------------------------------------------------------------
# D — assortativity conditioning of the Mahalanobis metric
# ---------------------------------------------------------------------------
def cmd_d(b: Bundle) -> None:
    from sklearn.covariance import LedoitWolf

    if "assortativity" not in FEATURE_NAMES:
        print("assortativity has been dropped from the feature set — "
              "task D (its conditioning check) is no longer applicable.")
        return
    j_as = FEATURE_NAMES.index("assortativity")
    raw_as = b.X_raw[:, j_as]
    print(f"assortativity (raw): var={raw_as.var():.5f} "
          f"range=[{raw_as.min():.4f}, {raw_as.max():.4f}] "
          f"n_unique={len(np.unique(raw_as))}")

    sample_cov = np.cov(b.Xz, rowvar=False)
    lw = LedoitWolf().fit(b.Xz)
    print(f"\nsample covariance (standardised, {b.Xz.shape[1]}x{b.Xz.shape[1]}):")
    print(f"  rank={np.linalg.matrix_rank(sample_cov)}/{sample_cov.shape[0]}  "
          f"cond={np.linalg.cond(sample_cov):.1f}")
    print(f"Ledoit-Wolf shrinkage APPLIED: shrinkage={lw.shrinkage_:.4f}")
    print(f"  shrunk covariance cond={np.linalg.cond(lw.covariance_):.1f} "
          f"(this is what Mahalanobis uses)")

    # Per-feature contribution to d^2 for the 64 Anomalous flags.
    anom_idx = np.where(b.flag == "Anomalous")[0]
    dom_counts = np.zeros(b.Xz.shape[1], dtype=int)
    for i in anom_idx:
        diff = b.Xz[i] - b.centroid
        contrib = diff * (b.precision @ diff)   # sums to d^2
        dom_counts[int(np.argmax(contrib))] += 1
    as_pos = b.feat_names.index("assortativity") if "assortativity" in b.feat_names else None
    as_dom = int(dom_counts[as_pos]) if as_pos is not None else 0

    order = np.argsort(dom_counts)[::-1]
    print(f"\nDominant feature among {len(anom_idx)} Anomalous flags "
          f"(largest d² contribution):")
    for r in order[:6]:
        if dom_counts[r]:
            print(f"  {b.feat_names[r]:20s} {dom_counts[r]}")
    print(f"assortativity dominates {as_dom}/{len(anom_idx)} flags")

    out = pd.DataFrame([{
        "assortativity_var": round(float(raw_as.var()), 5),
        "assortativity_min": round(float(raw_as.min()), 4),
        "assortativity_max": round(float(raw_as.max()), 4),
        "sample_cov_rank": int(np.linalg.matrix_rank(sample_cov)),
        "sample_cov_cond": round(float(np.linalg.cond(sample_cov)), 1),
        "ledoitwolf_shrinkage": round(float(lw.shrinkage_), 4),
        "shrunk_cov_cond": round(float(np.linalg.cond(lw.covariance_)), 1),
        "n_anomalous": len(anom_idx),
        "assortativity_flag_dominance": as_dom,
    }])
    path = OUT / "feature_conditioning.csv"
    out.to_csv(path, index=False)
    print(f"\n  Saved {path}")
    print("\nVERDICT (D):")
    ill = np.linalg.cond(lw.covariance_) > 100
    dominates = as_dom > 0.1 * len(anom_idx)
    if ill or dominates:
        print("  DROP TO 24 — assortativity ill-conditions the metric or drives "
              "flags; re-derive χ² cutoff at df=24 and re-run RQ3.")
    else:
        print("  KEEP 25 — Ledoit-Wolf shrinkage keeps the metric well-conditioned "
              f"(cond={np.linalg.cond(lw.covariance_):.1f}) and assortativity "
              f"dominates {as_dom} flags. The keep-25 decision stands.")


# ---------------------------------------------------------------------------
# E — exclusion-consistency audit
# ---------------------------------------------------------------------------
def cmd_e(b: Bundle) -> None:
    from src.batch_runner import MODELS

    clean_keys = set()
    df = b.fm[["csv_path", "team_name", "question_label"]].copy()
    df["degenerate"] = b.degenerate
    for _, row in df[~df.degenerate].iterrows():
        clean_keys.add((row["csv_path"], row["team_name"], row["question_label"]))

    peerrank_models = ["peerrank-impute", "peerrank-exclude"]
    failures: dict[str, list] = {m: [] for m in MODELS}
    for csv_path in discover_csvs(DATA_DIR):
        matrices, _ = parse_session_with_diagnostics(csv_path)
        for (team, label), sm in matrices.items():
            key = (str(csv_path), team, label)
            is_clean = key in clean_keys
            for mname, fn in MODELS.items():
                try:
                    fn(sm)
                except Exception as exc:
                    failures[mname].append({
                        "csv": Path(csv_path).name, "team": team,
                        "question": label, "clean": is_clean,
                        "error": type(exc).__name__,
                    })

    print("Per-model base-matrix failures (all 417):")
    for m in MODELS:
        n = len(failures[m])
        nclean = sum(f["clean"] for f in failures[m])
        print(f"  {m:18s} {n} fail  ({nclean} of them in the clean set)")

    # Distinct failing matrices and which models each affects
    allf = []
    for m, lst in failures.items():
        for f in lst:
            allf.append({**f, "model": m})
    fdf = pd.DataFrame(allf)
    print()
    if len(fdf):
        grp = fdf.groupby(["csv", "team", "question", "clean"])["model"].apply(
            lambda s: ", ".join(sorted(s)))
        for (csv, team, q, clean), models in grp.items():
            print(f"  [{'CLEAN' if clean else 'degen'}] {team} / {q} "
                  f"({csv[:30]}…) → fails: {models}")

    path = OUT / "exclusion_audit.csv"
    fdf.to_csv(path, index=False)
    n_clean_peerrank = len({(f["csv"], f["team"], f["question"])
                            for m in peerrank_models for f in failures[m]
                            if f["clean"]})
    print(f"\n  Saved {path}")
    print(f"\nConsistency: {n_clean_peerrank} CLEAN matrices fail a PeerRank "
          f"variant → RQ1 PeerRank n = 217 - (per-attack failures).")
    _write_exclusion_note(failures, n_clean_peerrank)


def _write_exclusion_note(failures, n_clean_peerrank):
    """Append a consistency note to the dissertation RESULTS_LOG.md."""
    log = Path.home() / ("Library/Mobile Documents/com~apple~CloudDocs/Uni/"
                         "2026 S1/COMPSCI 789/results/RESULTS_LOG.md")
    if not log.exists():
        print(f"  (RESULTS_LOG.md not found at {log}; skipping note)")
        return
    lines = ["", "## 2026-05-31 — all-zero-rater exclusion audit (handoff-2 Task E)",
             "", "Distinct matrices where a model errors on an all-zero-rater "
             "submission (showcase-poster question):"]
    seen = {}
    for m, lst in failures.items():
        for f in lst:
            k = (f["csv"], f["team"], f["question"])
            seen.setdefault(k, set()).add(m)
            seen[k].add("__clean__" if f["clean"] else "__degen__")
    for k, ms in sorted(seen.items()):
        clean = "__clean__" in ms
        mods = sorted(x for x in ms if not x.startswith("__"))
        lines.append(f"- {k[1]} / {k[2]} ({k[0]}) — "
                     f"{'CLEAN' if clean else 'degenerate'} — fails: {', '.join(mods)}")
    lines += [
        "",
        f"Consistency: {n_clean_peerrank} CLEAN matrix(es) trigger a PeerRank "
        "error. RQ1 reports PeerRank n<217 per attack (one base failure removes "
        "the team from that model's aggregate; some attacked variants add more). "
        "RQ3 keeps the full 217 clean set: a PeerRank failure only drops that "
        "model from the per-student Δ (Δ averages the ≥2 models that succeed — "
        "baseline/WebPA/PeerHITS), so the matrix is never silently zero-filled. "
        "No matrix is imputed in one analysis and dropped in another.", ""]
    with open(log, "a") as f:
        f.write("\n".join(lines))
    print(f"  Appended consistency note to {log.name}")


COMMANDS = {"check": cmd_check, "a": cmd_a, "b": cmd_b,
            "c": cmd_c, "d": cmd_d, "e": cmd_e}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd not in COMMANDS:
        print(f"Unknown command {cmd!r}. Choose from {list(COMMANDS)}")
        sys.exit(1)
    b = load()
    if cmd == "a":
        n_nulls = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        n_boot = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        cmd_a(b, n_nulls=n_nulls, n_bootstrap=n_boot)
    else:
        COMMANDS[cmd](b)


if __name__ == "__main__":
    main()
