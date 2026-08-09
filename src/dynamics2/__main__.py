"""Rank-based state cascade — RQ3 re-representation (handoff-8).

Additive second dynamics lane. Removes rater effects by transforming each
rater's ratings to within-rater normalised ranks, then runs a three-gate state
cascade whose every threshold is a per-matrix permutation null.

Run:
    python3 -m src.dynamics2                 # full cascade, default n_perm=1000
    python3 -m src.dynamics2 gates --n-perm 200
    python3 -m src.dynamics2 contested
    python3 -m src.dynamics2 crossq

Outputs to output/dynamics2/:
    matrix_states.csv               — one row per team×question: gate cascade state
    contested_factions.csv          — 4a per-matrix two-camp test (Contested only)
    contested_concentration.csv     — 4b per-matrix concentrated-vs-spread test
    contested_factions_pooled.csv   — 4c team-level pooled faction test
    cross_question.csv              — per-team cross-question bottom consistency
    strong_freerider_candidates.csv — join: 3-question agreement + significant gap

All outputs are seeded (BLAKE2b per matrix×statistic) and bit-for-bit
reproducible across runs.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.dynamics2 import contested as contested_mod
from src.dynamics2 import crossq as crossq_mod
from src.dynamics2 import gates as gates_mod
from src.dynamics2 import ranks
from src.dynamics2.dataio import (
    OUTPUT_DIR, MatrixRecord, load_aa_assignments, load_matrices,
)
from src.dynamics2.nulls import DEFAULT_N_PERM

ALPHA = 0.05
STATE_ORDER = [
    gates_mod.SILENT_FLAT, gates_mod.SILENT_LONE, gates_mod.SILENT_INCOMPARABLE,
    gates_mod.CONTESTED, gates_mod.NO_STANDOUT, gates_mod.ONE_AT_BOTTOM,
    gates_mod.ONE_AT_TOP, gates_mod.BOTH_ENDS,
]


# --------------------------------------------------------------------------- #
# Stage runners
# --------------------------------------------------------------------------- #

def run_gates(records: list[MatrixRecord], n_perm: int) -> pd.DataFrame:
    """Gate cascade over every matrix; write matrix_states.csv (with AA join)."""
    print(f"Gate cascade over {len(records)} matrices (n_perm={n_perm})...", flush=True)
    rows = []
    for rec in records:
        mat = ranks.prepare_matrix(rec.sm)
        gr = gates_mod.classify_matrix(mat, rec.key, n_perm=n_perm)
        rows.append({
            "csv_path": rec.csv_path, "team_name": rec.team_name,
            "question_label": rec.question_label,
            "n": gr.n, "n_raters": gr.n_raters, "mean_tau": gr.mean_tau,
            "bot_gap": gr.bot_gap, "top_gap": gr.top_gap,
            "p_tau": gr.p_tau, "p_bot": gr.p_bot, "p_top": gr.p_top,
            "state": gr.state,
        })
    df = pd.DataFrame(rows)

    # Read-only join from the AA pipeline for comparison.
    aa = load_aa_assignments()
    if not aa.empty:
        df = df.merge(
            aa[["csv_path", "team_name", "question_label", "degenerate", "atypicality_flag"]],
            on=["csv_path", "team_name", "question_label"], how="left",
        )
    else:
        df["degenerate"] = np.nan
        df["atypicality_flag"] = np.nan

    _write(df, "matrix_states.csv")

    counts = Counter(df["state"])
    print("  State distribution:", flush=True)
    for s in STATE_ORDER:
        print(f"    {s:24s} {counts.get(s, 0)}", flush=True)
    silent = sum(counts.get(s, 0) for s in
                 (gates_mod.SILENT_FLAT, gates_mod.SILENT_LONE, gates_mod.SILENT_INCOMPARABLE))
    print(f"    {'(Silent total)':24s} {silent}", flush=True)
    if "degenerate" in df and df["degenerate"].notna().any():
        clean = df[df["degenerate"] == False]  # noqa: E712
        cc = Counter(clean["state"])
        print(f"  Clean-only ({len(clean)}): "
              + " · ".join(f"{s}={cc.get(s, 0)}" for s in STATE_ORDER), flush=True)
    return df


def run_contested(records: list[MatrixRecord], states: pd.DataFrame,
                  n_perm: int) -> dict[str, pd.DataFrame]:
    """4a/4b per-matrix + 4c pooled tests over the Contested set."""
    by_key = {rec.key: rec for rec in records}
    contested_keys = [
        (r.csv_path, r.team_name, r.question_label)
        for r in states.itertuples() if r.state == gates_mod.CONTESTED
    ]
    print(f"Contested sub-tests over {len(contested_keys)} matrices "
          f"(n_perm={n_perm})...", flush=True)

    fac_rows, con_rows = [], []
    for key in contested_keys:
        rec = by_key[key]
        mat = ranks.prepare_matrix(rec.sm)
        f = contested_mod.faction_test(mat, key, n_perm=n_perm)
        c = contested_mod.concentration_test(mat, key, n_perm=n_perm)
        base = {"csv_path": key[0], "team_name": key[1], "question_label": key[2]}
        fac_rows.append({**base, "n_raters": f.n_raters, "faction_size": f.faction_size,
                        "modularity": f.modularity, "p_value": f.p_value,
                        "category": f.category})
        con_rows.append({**base, "n_disputed_recipients": c.n_disputed_recipients,
                        "gap": c.gap, "p_value": c.p_value, "verdict": c.verdict})
    fac_df = pd.DataFrame(fac_rows)
    con_df = pd.DataFrame(con_rows)
    _write(fac_df, "contested_factions.csv")
    _write(con_df, "contested_concentration.csv")

    # 4c — pooled, one row per Contested team (pool all its readable questions).
    contested_teams = sorted({(k[0], k[1]) for k in contested_keys})
    teams = crossq_mod.group_by_team(records)
    pool_rows = []
    for csv_path, team_name in contested_teams:
        recs = teams[(csv_path, team_name)]
        items = [([s.email for s in r.sm.students], ranks.prepare_matrix(r.sm)) for r in recs]
        p = contested_mod.pooled_faction_test(items, key=(csv_path, team_name), n_perm=n_perm)
        pool_rows.append({"csv_path": csv_path, "team_name": team_name,
                         "n_raters": p.n_raters, "faction_size": p.faction_size,
                         "modularity": p.modularity, "p_value": p.p_value,
                         "category": p.category})
    pool_df = pd.DataFrame(pool_rows)
    _write(pool_df, "contested_factions_pooled.csv")

    _summarise_factions(fac_df, "per-matrix factions")
    if not con_df.empty:
        print(f"  concentration: {Counter(con_df['verdict'])}", flush=True)
    _summarise_factions(pool_df, "pooled factions")
    _check_faction_trigger(fac_df, pool_df)
    return {"factions": fac_df, "concentration": con_df, "pooled": pool_df}


def run_crossq(records: list[MatrixRecord]) -> pd.DataFrame:
    """Per-team cross-question bottom consistency."""
    teams = crossq_mod.group_by_team(records)
    print(f"Cross-question consistency over {len(teams)} teams...", flush=True)
    rows = []
    for _, recs in sorted(teams.items()):
        cq = crossq_mod.analyse_team(recs)
        rows.append({
            "csv_path": cq.csv_path, "team_name": cq.team_name,
            "n_readable_questions": cq.n_readable_questions,
            "same_bottom_count": cq.same_bottom_count,
            "distinct_bottoms": cq.distinct_bottoms,
            "cross_q_tau": cq.cross_q_tau,
            "bottom_email": cq.bottom_email, "verdict": cq.verdict,
        })
    df = pd.DataFrame(rows)
    _write(df, "cross_question.csv")

    readable = df[df["verdict"] != "insufficient"]
    sb = Counter(readable["same_bottom_count"])
    print(f"  {len(readable)}/{len(df)} teams readable. "
          f"Same bottom on 3q={sb.get(3,0)} · 2q={sb.get(2,0)} · 1q(distinct)={sb.get(1,0)}",
          flush=True)
    valid_tau = readable["cross_q_tau"].dropna()
    if len(valid_tau):
        print(f"  cross-question τ: mean={valid_tau.mean():.3f} median={valid_tau.median():.3f}",
              flush=True)
    return df


def run_freeriders(states: pd.DataFrame, crossq_df: pd.DataFrame) -> pd.DataFrame:
    """Task-6 join: the number that would actually be reported for §5.3.

    Strong candidate = ``same_bottom_count == 3`` (the same student is bottom on
    all three near-independent tasks) AND a significant bottom gap (`p_bot`≤α) on
    at least one of that team's question matrices.
    """
    print("Strong free-rider join...", flush=True)
    sig_bot = states[states["p_bot"] <= ALPHA]
    strong_rows = []
    for cq in crossq_df.itertuples():
        if cq.same_bottom_count != 3:
            continue
        team_matrices = states[(states["csv_path"] == cq.csv_path)
                               & (states["team_name"] == cq.team_name)]
        team_sig = sig_bot[(sig_bot["csv_path"] == cq.csv_path)
                          & (sig_bot["team_name"] == cq.team_name)]
        if team_sig.empty:
            continue
        strong_rows.append({
            "csv_path": cq.csv_path, "team_name": cq.team_name,
            "bottom_email": cq.bottom_email,
            "cross_q_tau": cq.cross_q_tau,
            "n_questions_sig_bot": len(team_sig),
            "sig_bot_questions": "; ".join(sorted(team_sig["question_label"])),
        })
    strong_df = pd.DataFrame(strong_rows)
    _write(strong_df, "strong_freerider_candidates.csv")
    print(f"  STRONG free-rider candidates: {len(strong_df)}", flush=True)

    # Contrast class: task-specific teams with a significant bottom gap on exactly
    # one question — one bad task rather than a standing pattern.
    contrast = 0
    for cq in crossq_df.itertuples():
        if cq.verdict != "task-specific":
            continue
        team_sig = sig_bot[(sig_bot["csv_path"] == cq.csv_path)
                          & (sig_bot["team_name"] == cq.team_name)]
        if len(team_sig) == 1:
            contrast += 1
    print(f"  Contrast (task-specific, exactly one significant bottom): {contrast}", flush=True)
    return strong_df


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _write(df: pd.DataFrame, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    df.to_csv(path, index=False)
    print(f"  Saved {path} ({len(df)} rows)", flush=True)


def _summarise_factions(df: pd.DataFrame, label: str) -> None:
    if df.empty:
        return
    c = Counter(df["category"])
    genuine = int(((df["category"] == "structured")).sum())
    print(f"  {label}: {dict(c)} — genuine multi-person factions (size≥2): {genuine}",
          flush=True)


def _check_faction_trigger(fac_df: pd.DataFrame, pool_df: pd.DataFrame) -> None:
    """Stop-and-report: >3 genuine multi-person factions overturns a headline negative."""
    genuine = 0
    for df in (fac_df, pool_df):
        if not df.empty:
            genuine = max(genuine, int((df["category"] == "structured").sum()))
    if genuine > 3:
        print(f"  *** STOP-AND-REPORT: {genuine} genuine multi-person factions (>3). "
              f"This would overturn a headline negative — do not quietly revise. ***",
              file=sys.stderr, flush=True)


def _parse_n_perm(argv: list[str], default: int = DEFAULT_N_PERM) -> int:
    if "--n-perm" in argv:
        return int(argv[argv.index("--n-perm") + 1])
    return default


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv and not argv[0].startswith("-") else "all"
    n_perm = _parse_n_perm(argv)

    records = load_matrices()
    if len(records) != 417:
        print(f"  Warning: {len(records)} matrices (expected 417) — parsing has "
              f"diverged from the rest of the project.", file=sys.stderr, flush=True)

    if cmd == "gates":
        run_gates(records, n_perm)
    elif cmd == "contested":
        states = _load_states()
        run_contested(records, states, n_perm)
    elif cmd == "crossq":
        run_crossq(records)
    elif cmd in ("all", "freeriders"):
        states = run_gates(records, n_perm)
        run_contested(records, states, n_perm)
        cq = run_crossq(records)
        run_freeriders(states, cq)
    else:
        print(f"Unknown command {cmd!r}. Choose from: gates, contested, crossq, all",
              file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Outputs in {OUTPUT_DIR}/", flush=True)


def _load_states() -> pd.DataFrame:
    path = OUTPUT_DIR / "matrix_states.csv"
    if not path.exists():
        print(f"  {path} not found — run `python3 -m src.dynamics2 gates` first.",
              file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(path)


if __name__ == "__main__":
    main()
