"""RQ3-EXT Step 1 — lock the partition with a finite mixture model (BIC/ICL).

Analysis only — does NOT change the pipeline. Reuses the Bundle loader from
src.dynamics.validity (identical standardised 24-feature matrix, n=417).

Fits Gaussian mixture models for k = 1..8 (full + diagonal covariance,
n_init=10, seeded) and reports BIC and ICL alongside the existing
bootstrap-stability evidence, per notes/classification-research.md §4 step 1:
"Re-confirm k=2 and k=4 with stability + a mixture model (BIC/ICL). Report
both." ICL = BIC + 2 * total assignment entropy (Biernacki, Celeux & Govaert
2000) — penalises overlapping components that BIC rewards, so it is the
conservative criterion; the memo warns BIC over-splits under uncertainty.

Also cross-tabulates the GMM hard assignments against (a) the AA k=4
archetype labels (argmax load, seeded refit identical to validity Task A)
and (b) the binary Typical/Anomalous flag, via adjusted Rand index.

Finally writes the archetype exemplar set for the hand-labelling calibration
step (notes/labelling-rubric.md): top-loading teams per AA k=4 archetype.

Run:
    python3 -m src.dynamics.mixture

Outputs (all under output/dynamics/):
    gmm_model_selection.csv   BIC/ICL per (k, covariance_type), full + clean-only
    gmm_vs_aa_crosstab.csv    hard-assignment cross-tabs + ARI scores
    archetype_exemplars.csv   top-8 teams per AA k=4 archetype (calibration set)
    aa_k4_assignments.csv     per-matrix argmax archetype + aligned load weights
                              (the hand-labelling sampler's canonical input — see
                              src/labelling/; persisted so nothing downstream has
                              to re-run the AA refit)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture

from src.dynamics.archetypes import fit_aa
from src.dynamics.validity import Bundle, load, _quiet

OUT = Path("output/dynamics")
ASSIGNMENTS = OUT / "aa_k4_assignments.csv"
SEED = 42
KS = list(range(1, 9))
COV_TYPES = ("full", "diag")
REG_COVAR = 1e-4  # triad census is compositional -> raw covariance near-singular
N_EXEMPLARS = 8


def _icl(gmm: GaussianMixture, X: np.ndarray) -> float:
    """ICL = BIC + 2 * total assignment entropy (lower is better)."""
    tau = gmm.predict_proba(X)
    ent = float(-np.sum(tau * np.log(np.clip(tau, 1e-300, None))))
    return float(gmm.bic(X)) + 2.0 * ent


def model_selection(b: Bundle) -> pd.DataFrame:
    rows = []
    subsets = {"full_n417": np.ones(len(b.delta), dtype=bool),
               "clean_n217": ~b.degenerate}
    for subset_name, mask in subsets.items():
        X = b.Xz[mask]
        for cov in COV_TYPES:
            for k in KS:
                gmm = GaussianMixture(
                    n_components=k, covariance_type=cov,
                    reg_covar=REG_COVAR, n_init=10, random_state=SEED,
                ).fit(X)
                rows.append({
                    "subset": subset_name, "covariance": cov, "k": k,
                    "bic": round(float(gmm.bic(X)), 1),
                    "icl": round(_icl(gmm, X), 1),
                    "loglik": round(float(gmm.score(X)) * len(X), 1),
                    "converged": bool(gmm.converged_),
                })
    df = pd.DataFrame(rows)
    for crit in ("bic", "icl"):
        df[f"best_{crit}"] = False
        for (s, c), grp in df.groupby(["subset", "covariance"]):
            df.loc[grp[crit].idxmin(), f"best_{crit}"] = True
    return df


def aa_k4_labels(b: Bundle) -> tuple[np.ndarray, np.ndarray]:
    """Refit AA k=4 (same seed/pipeline as validity Task A) -> argmax labels.

    Returns (labels aligned to the published A0..A3 order, weights matrix).
    Alignment: match refit archetypes to k4_archetypes.csv rows by load count
    (71/172/40/134 are distinct); assert the counts reproduce exactly.
    """
    _, weights, _ = _quiet(fit_aa, b.Xz, 4, random_state=SEED)
    raw = np.argmax(weights, axis=1)
    counts = np.bincount(raw, minlength=4)
    published = pd.read_csv(OUT / "k4_archetypes.csv")
    pub_counts = published["load_count"].values
    # cost matrix: |count difference| -> optimal one-to-one match
    cost = np.abs(counts[:, None] - pub_counts[None, :])
    ri, ci = linear_sum_assignment(cost)
    assert cost[ri, ci].sum() == 0, (
        f"refit AA k=4 loads {counts.tolist()} do not reproduce published "
        f"loads {pub_counts.tolist()} — check seed/pipeline")
    remap = dict(zip(ri, ci))
    labels = np.array([remap[x] for x in raw])
    return labels, weights


def crosstabs(b: Bundle, aa_labels: np.ndarray) -> pd.DataFrame:
    rows = []
    X = b.Xz
    for cov in COV_TYPES:
        for k in (2, 4):
            gmm = GaussianMixture(n_components=k, covariance_type=cov,
                                  reg_covar=REG_COVAR, n_init=10,
                                  random_state=SEED).fit(X)
            g = gmm.predict(X)
            ari_aa = adjusted_rand_score(aa_labels, g)
            ari_flag = adjusted_rand_score(
                (b.flag == "Anomalous").astype(int), g)
            ct = pd.crosstab(pd.Series(aa_labels, name="aa_k4"),
                             pd.Series(g, name="gmm"))
            rows.append({
                "covariance": cov, "k": k,
                "ari_vs_aa_k4": round(ari_aa, 3),
                "ari_vs_binary_flag": round(ari_flag, 3),
                "gmm_sizes": "/".join(str(int(x)) for x in np.bincount(g, minlength=k)),
                "crosstab_vs_aa_k4": ct.values.tolist(),
            })
    return pd.DataFrame(rows)


def clean_crosstab(b: Bundle, aa_labels: np.ndarray) -> pd.DataFrame:
    """GMM on clean rows only vs AA k=4 labels restricted to clean rows.

    Hypothesis: AA k=4 = {flat/degenerate mode A1} + 3 substantive groups.
    If so, removing the degenerate mass should leave a 3-component structure
    that maps onto the non-A1 archetypes.
    """
    clean = ~b.degenerate
    X = b.Xz[clean]
    al = aa_labels[clean]
    rows = []
    for k in (2, 3, 4):
        gmm = GaussianMixture(n_components=k, covariance_type="full",
                              reg_covar=REG_COVAR, n_init=10,
                              random_state=SEED).fit(X)
        g = gmm.predict(X)
        rows.append({
            "k": k,
            "ari_vs_aa_k4_clean": round(adjusted_rand_score(al, g), 3),
            "gmm_sizes": "/".join(str(int(x)) for x in np.bincount(g, minlength=k)),
            "aa_label_sizes_clean": "/".join(
                str(int(x)) for x in np.bincount(al, minlength=4)),
            "crosstab": pd.crosstab(pd.Series(al, name="aa"),
                                    pd.Series(g, name="gmm")).values.tolist(),
        })
    return pd.DataFrame(rows)


def _col_for_pub(weights: np.ndarray) -> dict[int, int]:
    """Map published archetype a (A0..A3) -> its column in the refit weights.

    Same load-count matching used everywhere in this module: the four loads
    71/172/40/134 are distinct, so the optimal assignment is exact.
    """
    published = pd.read_csv(OUT / "k4_archetypes.csv")
    raw_counts = np.bincount(np.argmax(weights, axis=1), minlength=4)
    cost = np.abs(raw_counts[:, None] - published["load_count"].values[None, :])
    ri, ci = linear_sum_assignment(cost)
    return {c: r for r, c in zip(ri, ci)}


def assignments(b: Bundle, aa_labels: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    """Per-matrix archetype + aligned convex load weights, keyed for joining.

    One row per rating matrix (n=417): the three identity keys the rest of the
    pipeline uses, the argmax archetype (A0..A3, published order), the binary
    Typical/Anomalous flag, the degenerate flag, and the four load weights in
    published-archetype order. This is the file src/labelling/sample.py reads so
    it never has to re-run the AA refit.
    """
    col = _col_for_pub(weights)
    df = b.fm[["csv_path", "team_name", "question_label"]].copy()
    df["archetype"] = [f"A{a}" for a in aa_labels]
    df["atypicality_flag"] = b.flag
    df["degenerate"] = b.degenerate
    for a in range(4):
        df[f"load_A{a}"] = np.round(weights[:, col[a]], 4)
    return df


def ensure_assignments() -> pd.DataFrame:
    """Return the per-matrix AA k=4 assignment table, generating it if absent.

    Persist-once / read-thereafter: the first call runs the seeded AA refit and
    writes aa_k4_assignments.csv; every later call (and every sample.py run) just
    reads the CSV. Delete the file to force a regeneration.
    """
    if ASSIGNMENTS.exists():
        return pd.read_csv(ASSIGNMENTS)
    b = load()
    labels, weights = aa_k4_labels(b)
    df = assignments(b, labels, weights)
    df.to_csv(ASSIGNMENTS, index=False)
    return df


def exemplars(b: Bundle, aa_labels: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    """Top-N rows per archetype by load weight — hand-labelling calibration set.

    Prefers clean matrices (degenerate rows carry no behavioural signal to
    hand-label); falls back to degenerate only if an archetype has fewer than
    N_EXEMPLARS clean loaders.
    """
    # column j of weights after the same alignment used for labels
    col_for_pub = _col_for_pub(weights)

    frames = []
    for a in range(4):
        w = weights[:, col_for_pub[a]].copy()
        # demote degenerate rows below every clean row, preserving order
        rank = w - b.degenerate.astype(float) * 2.0
        idx = np.argsort(-rank)[:N_EXEMPLARS]
        frames.append(pd.DataFrame({
            "archetype": f"A{a}",
            "csv_path": b.fm["csv_path"].values[idx],
            "team_name": b.fm["team_name"].values[idx],
            "question_label": b.fm["question_label"].values[idx],
            "load_weight": np.round(w[idx], 3),
            "degenerate": b.degenerate[idx],
            "atypicality_flag": b.flag[idx],
            "delta": np.round(b.delta[idx], 3),
        }))
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    b = load()
    print(f"Loaded n={len(b.delta)}, df={b.df} ({b.Xz.shape[1]} standardised features)")

    sel = model_selection(b)
    sel.to_csv(OUT / "gmm_model_selection.csv", index=False)
    for (s, c), grp in sel.groupby(["subset", "covariance"]):
        kb = int(grp.loc[grp["bic"].idxmin(), "k"])
        ki = int(grp.loc[grp["icl"].idxmin(), "k"])
        print(f"{s:>11} | {c:>4} | best-BIC k={kb} | best-ICL k={ki}")

    labels, weights = aa_k4_labels(b)
    print("AA k=4 refit loads:", np.bincount(labels, minlength=4).tolist())

    ct = crosstabs(b, labels)
    ct.to_csv(OUT / "gmm_vs_aa_crosstab.csv", index=False)
    print(ct[["covariance", "k", "ari_vs_aa_k4", "ari_vs_binary_flag", "gmm_sizes"]]
          .to_string(index=False))

    cc = clean_crosstab(b, labels)
    cc.to_csv(OUT / "gmm_clean_crosstab.csv", index=False)
    print(cc[["k", "ari_vs_aa_k4_clean", "gmm_sizes", "aa_label_sizes_clean"]]
          .to_string(index=False))

    ex = exemplars(b, labels, weights)
    ex.to_csv(OUT / "archetype_exemplars.csv", index=False)
    print(f"Wrote {len(ex)} exemplars ({N_EXEMPLARS} per archetype) "
          f"-> archetype_exemplars.csv")

    asg = assignments(b, labels, weights)
    asg.to_csv(ASSIGNMENTS, index=False)
    print(f"Wrote {len(asg)} per-matrix assignments -> aa_k4_assignments.csv")


if __name__ == "__main__":
    main()
