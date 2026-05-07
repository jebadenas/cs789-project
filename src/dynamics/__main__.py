"""Team-dynamics classification pipeline entry point.

Run:
    python3 -m src.dynamics

Outputs to output/dynamics/:
    feature_matrix.csv        — 25-dim feature vector per team-matrix + Δ + dynamic_label
    classifications.csv       — team label + Mahalanobis distances to all 5 archetypes
    delta_by_label.csv        — Δ statistics (mean/std/median/max) per dynamic label
    pca_plot.html             — interactive PCA scatter coloured by Δ
    umap_plot.html            — interactive UMAP scatter coloured by Δ
    archetypes.json           — AA archetype vectors + RSS for each k
    archetype_stability.csv   — RSS elbow + bootstrap stability per k
    rss_plot.html             — archetype count selection chart
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.batch_runner import run_full_dataset
from src.dynamics.archetypes import ArchetypeResult, find_elbow, sweep_archetypes
from src.dynamics.classifier import (
    ARCHETYPE_LABELS,
    build_synthesised_archetypes,
    classify_teams,
    delta_by_label,
    fit_precision,
)
from src.dynamics.features import FEATURE_NAMES, TeamFeatures, extract_features
from src.parsing.discovery import discover_csvs
from src.parsing.parser import parse_session_with_diagnostics


DATA_DIR = Path("data")
OUTPUT_DIR = Path("output") / "dynamics"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Run all IWF models to compute per-team Δ ---
    print("Running IWF models on full dataset...", flush=True)
    batch = run_full_dataset(DATA_DIR)
    deltas = _compute_team_delta(batch)

    # --- Feature extraction ---
    print("Extracting team features...", flush=True)
    features: list[TeamFeatures] = []
    csvs = discover_csvs(DATA_DIR)

    for csv_path in csvs:
        matrices, _ = parse_session_with_diagnostics(csv_path)
        for (team_name, question_label), sm in matrices.items():
            try:
                tf = extract_features(sm, csv_path=str(csv_path), question_label=question_label)
                features.append(tf)
            except Exception as exc:
                print(f"  Warning: {team_name} ({question_label}): {exc}", file=sys.stderr)

    print(f"  {len(features)} team-matrices featurized", flush=True)

    if len(features) < 4:
        print("Too few matrices for analysis. Place CSV files in data/ and retry.", file=sys.stderr)
        sys.exit(1)

    # --- Build and save raw feature matrix ---
    team_keys = [(tf.csv_path, tf.team_name, tf.question_label) for tf in features]
    X_raw = np.array([tf.values for tf in features])

    col_means = np.nanmean(X_raw, axis=0)
    for j in range(X_raw.shape[1]):
        nan_mask = np.isnan(X_raw[:, j])
        if nan_mask.any():
            X_raw[nan_mask, j] = col_means[j]

    delta_vals = np.array([deltas.get(k, 0.0) for k in team_keys])
    labels = [f"{tf.team_name} | {tf.question_label}" for tf in features]

    # --- Standardize for PCA / UMAP / AA / classification ---
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Drop zero-variance features (e.g. assortativity is constant=0 in this dataset).
    # These produce degenerate covariance and overflow in AA / Ledoit-Wolf.
    nonzero_var_mask = scaler.var_ > 1e-10
    X_scaled_nz = X_scaled[:, nonzero_var_mask]
    n_dropped = int((~nonzero_var_mask).sum())
    if n_dropped:
        dropped = [FEATURE_NAMES[i] for i, keep in enumerate(nonzero_var_mask) if not keep]
        print(f"  Dropped {n_dropped} zero-variance feature(s): {dropped}", flush=True)

    # --- Synthesised-archetype Mahalanobis classification ---
    print("Classifying teams via synthesised archetypes...", flush=True)
    _, arch_raw = build_synthesised_archetypes()
    arch_scaled_full = scaler.transform(arch_raw)
    arch_scaled = arch_scaled_full[:, nonzero_var_mask]
    precision = fit_precision(X_scaled_nz)
    classifications = classify_teams(X_scaled_nz, arch_scaled, precision)
    class_labels = [cr.label for cr in classifications]

    # Classification CSV
    dist_cols = {f"dist_{lbl.lower().replace('-', '_').replace(' ', '_')}": [cr.distances[i] for cr in classifications]
                 for i, lbl in enumerate(ARCHETYPE_LABELS)}
    weight_cols = {f"weight_{lbl.lower().replace('-', '_').replace(' ', '_')}": [cr.weights[i] for cr in classifications]
                   for i, lbl in enumerate(ARCHETYPE_LABELS)}
    df_cls = pd.DataFrame({
        "csv_path": [tf.csv_path for tf in features],
        "team_name": [tf.team_name for tf in features],
        "question_label": [tf.question_label for tf in features],
        "dynamic_label": class_labels,
        "delta": delta_vals,
        **dist_cols,
        **weight_cols,
    })
    cls_path = OUTPUT_DIR / "classifications.csv"
    df_cls.to_csv(cls_path, index=False)
    print(f"  Saved {cls_path}", flush=True)

    # Delta-by-label CSV
    label_stats = delta_by_label(class_labels, delta_vals)
    df_delta_label = pd.DataFrame([
        {"label": lbl, **stats}
        for lbl, stats in label_stats.items()
    ])
    delta_label_path = OUTPUT_DIR / "delta_by_label.csv"
    df_delta_label.to_csv(delta_label_path, index=False)
    print(f"  Saved {delta_label_path}", flush=True)

    label_counts = {lbl: class_labels.count(lbl) for lbl in ARCHETYPE_LABELS}
    print(f"  Label distribution: {label_counts}", flush=True)

    for lbl, stats in label_stats.items():
        if stats["count"] > 0:
            print(f"    {lbl:15s}  n={stats['count']:3d}  Δ mean={stats['mean']:.3f}  median={stats['median']:.3f}", flush=True)

    # Feature matrix with label appended
    df_feat = pd.DataFrame(X_raw, columns=FEATURE_NAMES)
    df_feat.insert(0, "question_label", [tf.question_label for tf in features])
    df_feat.insert(0, "team_name", [tf.team_name for tf in features])
    df_feat.insert(0, "csv_path", [tf.csv_path for tf in features])
    df_feat["delta"] = delta_vals
    df_feat["dynamic_label"] = class_labels
    feat_path = OUTPUT_DIR / "feature_matrix.csv"
    df_feat.to_csv(feat_path, index=False)
    print(f"  Saved {feat_path}", flush=True)

    # --- PCA (on non-zero-variance features) ---
    print("Running PCA...", flush=True)
    pca = PCA(n_components=2, random_state=42)
    pca_coords = pca.fit_transform(X_scaled_nz)
    pca_var = pca.explained_variance_ratio_.tolist()
    print(f"  PC1: {pca_var[0]:.1%}, PC2: {pca_var[1]:.1%}", flush=True)

    # --- UMAP ---
    print("Running UMAP...", flush=True)
    try:
        import umap as umap_lib
        reducer = umap_lib.UMAP(n_components=2, random_state=42, n_neighbors=min(15, len(features) - 1), min_dist=0.1)
        umap_coords = reducer.fit_transform(X_scaled_nz)
    except ImportError:
        print("  umap-learn not installed — skipping UMAP (pip install umap-learn)", file=sys.stderr)
        umap_coords = None
        reducer = None

    # --- Archetypal Analysis sweep k=2..8 ---
    print("Fitting archetypes (k=2..8, with bootstrap stability)...", flush=True)
    arch_results = sweep_archetypes(X_scaled_nz, k_range=range(2, 9), n_bootstrap=50)
    best_k = find_elbow(arch_results)
    best_arch = next(r for r in arch_results if r.k == best_k)
    print(f"  RSS elbow: best k={best_k}", flush=True)

    # --- Save archetype artifacts ---
    arch_data = [
        {
            "k": r.k,
            "rss": r.rss,
            "bootstrap_stability": r.bootstrap_stability,
            "archetypes": r.archetypes.tolist(),
            "weights": r.weights.tolist(),
        }
        for r in arch_results
    ]
    arch_path = OUTPUT_DIR / "archetypes.json"
    arch_path.write_text(json.dumps(arch_data, indent=2))
    print(f"  Saved {arch_path}", flush=True)

    stab_df = pd.DataFrame([
        {"k": r.k, "rss": r.rss, "bootstrap_stability": r.bootstrap_stability}
        for r in arch_results
    ])
    stab_path = OUTPUT_DIR / "archetype_stability.csv"
    stab_df.to_csv(stab_path, index=False)
    print(f"  Saved {stab_path}", flush=True)

    # --- Visualisations ---
    print("Generating visualisations...", flush=True)
    from src.visualization.archetype_map import make_pca_plot, make_rss_plot, make_umap_plot

    pca_fig = make_pca_plot(pca_coords, delta_vals, labels, pca_var, best_arch.archetypes, pca)
    pca_path = OUTPUT_DIR / "pca_plot.html"
    pca_fig.write_html(str(pca_path))
    print(f"  Saved {pca_path}", flush=True)

    if umap_coords is not None and reducer is not None:
        umap_fig = make_umap_plot(umap_coords, delta_vals, labels, best_arch.archetypes, reducer)
        umap_path = OUTPUT_DIR / "umap_plot.html"
        umap_fig.write_html(str(umap_path))
        print(f"  Saved {umap_path}", flush=True)

    rss_fig = make_rss_plot(
        k_values=[r.k for r in arch_results],
        rss_values=[r.rss for r in arch_results],
        stabilities=[r.bootstrap_stability for r in arch_results],
        best_k=best_k,
    )
    rss_path = OUTPUT_DIR / "rss_plot.html"
    rss_fig.write_html(str(rss_path))
    print(f"  Saved {rss_path}", flush=True)

    print(f"\nDone. Best k={best_k}. Outputs in {OUTPUT_DIR}/", flush=True)
    print(f"  classifications.csv  — {len(features)} teams labelled", flush=True)
    print(f"  delta_by_label.csv   — Δ stratified by dynamic label", flush=True)


def _compute_team_delta(batch) -> dict[tuple, float]:
    """Per-team mean IWF standard deviation across all 6 models."""
    by_key: dict[tuple, dict[str, np.ndarray]] = {}
    for rec in batch.succeeded:
        key = (rec.csv_path, rec.team_name, rec.question_label)
        by_key.setdefault(key, {})[rec.model_name] = rec.result.iwf_vector

    deltas: dict[tuple, float] = {}
    for key, model_iwfs in by_key.items():
        vecs = list(model_iwfs.values())
        if len(vecs) < 2:
            deltas[key] = 0.0
            continue

        n_students = max(len(v) for v in vecs)
        stds: list[float] = []
        for i in range(n_students):
            vals = [float(v[i]) for v in vecs if i < len(v) and not np.isnan(v[i])]
            if len(vals) >= 2:
                stds.append(float(np.std(vals)))

        deltas[key] = float(np.mean(stds)) if stds else 0.0

    return deltas


if __name__ == "__main__":
    main()
