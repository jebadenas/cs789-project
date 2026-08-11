"""Synthetic validation of the triage cascade (handoff-10).

On real data the cascade's sorting has no answer key. Here we build one: generate
teams with a **known planted state** (via the PG1 generator in
``src.attacks.synthetic``, extended to the CS399 form — 10·N points per rater
including self, diagonal populated), run the unmodified ``dynamics2`` cascade, and
measure how often the planted state is recovered.

The cascade itself is the thing under test and is **not** modified here.

Planted states (ground truth) and the generator recipe for each:

    Even                 all contributions equal; reliable raters
    One at bottom        one member reduced by a controlled gap δ
    One at top           one member raised by δ
    Both ends            one raised, one lowered
    Contested            two camps that rank each other differently (per-rater
                         perception), not merely high noise
    Disengaged           equal contributions, lazy raters (central_pull)
    Non-differentiating  raters emit a flat allocation regardless of contribution
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.attacks.synthetic import SyntheticTeam, generate_team
from src.dynamics2 import gates, ranks

MU0 = 10.0
SIZES = (4, 5, 6)

# Recovered-state canonical groups (Silent variants collapsed for the cross-tab).
SILENT = {gates.SILENT_FLAT, gates.SILENT_LONE, gates.SILENT_INCOMPARABLE}
STANDOUTS = {gates.ONE_AT_BOTTOM, gates.ONE_AT_TOP, gates.BOTH_ENDS}


# --------------------------------------------------------------------------- #
# Planters — each returns a SyntheticTeam in CS399 form with a known state
# --------------------------------------------------------------------------- #

def _team(n: int, seed: int, contributions=None, *, profile="reliable",
          perceived=None, **kw) -> SyntheticTeam:
    return generate_team(n, seed, profile=profile, contributions=contributions,
                         perceived=perceived, include_self=True, mu0=MU0, **kw)


def plant_even(n: int, seed: int, profile: str = "reliable", delta: float = 0.0) -> SyntheticTeam:
    return _team(n, seed, np.full(n, MU0), profile=profile)


def plant_one_at_bottom(n: int, seed: int, profile: str = "reliable",
                        delta: float = 5.0, target: int = 0) -> SyntheticTeam:
    c = np.full(n, MU0)
    c[target] = MU0 - delta
    return _team(n, seed, c, profile=profile)


def plant_one_at_top(n: int, seed: int, profile: str = "reliable",
                     delta: float = 5.0, target: int = 0) -> SyntheticTeam:
    c = np.full(n, MU0)
    c[target] = MU0 + delta
    return _team(n, seed, c, profile=profile)


def plant_both_ends(n: int, seed: int, profile: str = "reliable",
                    delta: float = 5.0) -> SyntheticTeam:
    c = np.full(n, MU0)
    c[0] = MU0 - delta
    c[-1] = MU0 + delta
    return _team(n, seed, c, profile=profile)


def plant_contested(n: int, seed: int, profile: str = "reliable",
                    delta: float = 4.0) -> SyntheticTeam:
    """Two camps that systematically rank each other differently.

    Rater j perceives members of *their own* camp as high (MU0+δ) and the other
    camp as low (MU0−δ). Within-camp raters agree; cross-camp raters invert →
    mean pairwise τ collapses and Gate B should fire.
    """
    half = n // 2
    camp = np.array([0] * half + [1] * (n - half))
    perceived = np.empty((n, n))
    for j in range(n):
        for i in range(n):
            perceived[i, j] = MU0 + delta if camp[i] == camp[j] else MU0 - delta
    return _team(n, seed, np.full(n, MU0), profile=profile, perceived=perceived)


def plant_disengaged(n: int, seed: int, profile: str = "lazy",
                     delta: float = 0.0) -> SyntheticTeam:
    # Equal contributions, lazy raters (central_pull compresses expressed spread).
    return _team(n, seed, np.full(n, MU0), profile="lazy")


def plant_non_differentiating(n: int, seed: int, profile: str = "reliable",
                              delta: float = 0.0) -> SyntheticTeam:
    # Raters give an identical allocation to everyone regardless of contribution:
    # constant perception + no observation noise + no bias → an exactly flat
    # matrix → zero qualifying raters → Silent-flat.
    perceived = np.full((n, n), MU0)
    return _team(n, seed, np.full(n, MU0), profile="reliable",
                 perceived=perceived, obs_sd=0.0, bias_sd=0.0)


PLANTERS = {
    "Even": plant_even,
    "One at bottom": plant_one_at_bottom,
    "One at top": plant_one_at_top,
    "Both ends": plant_both_ends,
    "Contested": plant_contested,
    "Disengaged": plant_disengaged,
    "Non-differentiating": plant_non_differentiating,
}

# The state the cascade *should* return, and the acceptable (non-error) set.
EXPECTED = {
    "Even": gates.NO_STANDOUT,
    "One at bottom": gates.ONE_AT_BOTTOM,
    "One at top": gates.ONE_AT_TOP,
    "Both ends": gates.BOTH_ENDS,
    "Contested": gates.CONTESTED,
    "Disengaged": "Silent",
    "Non-differentiating": gates.SILENT_FLAT,
}


# --------------------------------------------------------------------------- #
# Classification of a generated team
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Recovered:
    state: str
    bottom_member: int          # consensus argmin (implicated low member), or -1
    top_member: int             # consensus argmax, or -1
    n_raters: int


def classify_team(team: SyntheticTeam, planted: str, n_perm: int = 1000) -> Recovered:
    """Run the unmodified cascade; also identify the implicated member(s)."""
    sm = team.score_matrix
    mat = ranks.prepare_matrix(sm)
    key = (sm.team_name, planted, sm.question_label, str(team.seed))
    row = gates.classify_matrix(mat, key, n_perm=n_perm)

    cons = ranks.consensus_vector(mat)
    finite = np.isfinite(cons)
    bottom = int(np.nanargmin(np.where(finite, cons, np.nan))) if finite.any() else -1
    top = int(np.nanargmax(np.where(finite, cons, np.nan))) if finite.any() else -1
    return Recovered(row.state, bottom, top, row.n_raters)


def canonical(state: str) -> str:
    """Collapse the three Silent variants for cross-tab reporting."""
    return "Silent" if state in SILENT else state


# --------------------------------------------------------------------------- #
# Wilson score interval
# --------------------------------------------------------------------------- #

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, lo, hi) Wilson score interval for k successes in n trials."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


# --------------------------------------------------------------------------- #
# Runs (Tasks 2–6). Each returns a DataFrame; the CLI writes them out.
# --------------------------------------------------------------------------- #

import sys
from pathlib import Path

import pandas as pd

from src.dynamics2.dataio import load_matrices

OUT = Path("output") / "dynamics2" / "validation"


def _planted_target(planted: str, n: int, rep: int) -> int:
    """The implicated member the generator plants (spread across positions)."""
    if planted in ("One at bottom", "One at top"):
        return rep % n
    return -1


def _make(planted: str, n: int, seed: int, rep: int, delta: float,
          profile: str | None = None):
    fn = PLANTERS[planted]
    kw = {"delta": delta}
    if profile is not None:
        kw["profile"] = profile
    tgt = _planted_target(planted, n, rep)
    if tgt >= 0:
        kw["target"] = tgt
    return fn(n, seed, **kw), tgt


def run_confusion(replicates: int, n_perm: int, delta: float = 7.0,
                  base_seed: int = 700_000, progress: bool = True) -> pd.DataFrame:
    """Task 2/5: planted × recovered over all states and sizes (natural profile)."""
    rows = []
    planter_names = list(PLANTERS)
    for planted in PLANTERS:
        for n in SIZES:
            for rep in range(replicates):
                # Deterministic seed (NOT hash() — that is salted per process).
                seed = base_seed + planter_names.index(planted) * 10_000 + n * 1000 + rep
                team, tgt = _make(planted, n, seed, rep, delta)
                r = classify_team(team, planted, n_perm=n_perm)
                member_ok = _member_correct(planted, r, tgt, n)
                rows.append({
                    "planted": planted, "N": n, "seed": seed, "rep": rep,
                    "recovered": r.state, "recovered_group": canonical(r.state),
                    "n_raters": r.n_raters, "planted_target": tgt,
                    "bottom_member": r.bottom_member, "top_member": r.top_member,
                    "state_correct": canonical(r.state) == canonical(EXPECTED[planted])
                    if EXPECTED[planted] != "Silent" else r.state in SILENT,
                    "member_correct": member_ok,
                })
        if progress:
            print(f"  confusion: {planted} done", file=sys.stderr, flush=True)
    return pd.DataFrame(rows)


def _member_correct(planted: str, r: Recovered, target: int, n: int) -> bool | None:
    if planted == "One at bottom":
        return r.state == gates.ONE_AT_BOTTOM and r.bottom_member == target
    if planted == "One at top":
        return r.state == gates.ONE_AT_TOP and r.top_member == target
    if planted == "Both ends":
        return r.state == gates.BOTH_ENDS and r.bottom_member == 0 and r.top_member == n - 1
    return None


def run_lazy_test(replicates: int, n_perm: int, base_seed: int = 800_000) -> pd.DataFrame:
    """Task 3: equal contributions, reliable vs lazy — can the cascade separate them?"""
    rows = []
    for arm, profile in (("cohesive (reliable)", "reliable"), ("disengaged (lazy)", "lazy")):
        for n in SIZES:
            for rep in range(replicates):
                seed = base_seed + rep + n * 1000
                team = plant_even(n, seed, profile=profile)
                r = classify_team(team, "Even", n_perm=n_perm)
                rows.append({"arm": arm, "profile": profile, "N": n, "seed": seed,
                            "recovered": r.state, "recovered_group": canonical(r.state),
                            "mean_tau": ranks.mean_pairwise_tau(ranks.prepare_matrix(team.score_matrix)),
                            "n_raters": r.n_raters})
    return pd.DataFrame(rows)


def run_power_curve(replicates: int, n_perm: int, deltas=(0, 1, 2, 3, 4, 5, 6, 8),
                    profiles=("reliable", "lazy"), base_seed: int = 900_000) -> pd.DataFrame:
    """Task 4: proportion of planted low-contributors detected as a standout, by δ."""
    rows = []
    for profile in profiles:
        for n in SIZES:
            for delta in deltas:
                detected = 0
                for rep in range(replicates):
                    seed = base_seed + rep + int(delta * 10) * 7 + n * 1000
                    team = plant_one_at_bottom(n, seed, profile=profile,
                                               delta=float(delta), target=rep % n)
                    r = classify_team(team, "One at bottom", n_perm=n_perm)
                    if r.state == gates.ONE_AT_BOTTOM and r.bottom_member == rep % n:
                        detected += 1
                p, lo, hi = wilson(detected, replicates)
                rows.append({"profile": profile, "N": n, "delta": delta,
                            "detected": detected, "n": replicates,
                            "rate": p, "wilson_lo": lo, "wilson_hi": hi})
        print(f"  power curve: {profile} done", file=sys.stderr, flush=True)
    return pd.DataFrame(rows)


def run_robustness(replicates: int, n_perm: int, delta: float = 7.0,
                   profiles=("reliable", "noisy", "lazy", "biased"),
                   sizes=(5, 6), base_seed: int = 950_000) -> pd.DataFrame:
    """Task 5: how free-rider recall / Even-FP / Contested recall degrade by rater
    profile. Restricted to N∈{5,6} (N=4 is structurally blind)."""
    rows = []
    for profile in profiles:
        for n in sizes:
            fr = fr_member = fp = ct = 0
            for rep in range(replicates):
                sd = base_seed + rep + n * 1000
                tgt = rep % n
                rb = classify_team(plant_one_at_bottom(n, sd, profile=profile,
                                   delta=delta, target=tgt), "One at bottom", n_perm=n_perm)
                fr += rb.state == gates.ONE_AT_BOTTOM
                fr_member += rb.state == gates.ONE_AT_BOTTOM and rb.bottom_member == tgt
                ev = classify_team(plant_even(n, sd + 7, profile=profile), "Even", n_perm=n_perm)
                fp += ev.state in STANDOUTS
                cc = classify_team(plant_contested(n, sd + 13, profile=profile),
                                   "Contested", n_perm=n_perm)
                ct += cc.state == gates.CONTESTED
            for label, k in (("free-rider recall", fr_member),
                             ("Even false-positive", fp),
                             ("Contested recall", ct)):
                p, lo, hi = wilson(k, replicates)
                rows.append({"profile": profile, "N": n, "metric": label,
                            "k": k, "n": replicates, "rate": p,
                            "wilson_lo": lo, "wilson_hi": hi})
        print(f"  robustness: {profile} done", file=sys.stderr, flush=True)
    return pd.DataFrame(rows)


def run_realism(n_perm: int, base_seed: int = 600_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Task 6: compare the synthetic *generator* to the real corpus on dynamics2
    observables.

    Uses **natural** synthetic teams — random contributions, reliable raters, in
    CS399 form — at the real N distribution, NOT the deliberately-extreme planted
    states. This asks whether the generator itself is realistic; it is NOT tuned
    to the real data (that would make the validation circular), so any gap is
    reported, not closed.
    """
    real = load_matrices()
    real_rows = _observables([(r.sm, r.key) for r in real], "real", n_perm)

    # Natural synthetic corpus at the real N counts (reliable, random contribs).
    n_counts = {}
    for r in real:
        n_counts[r.sm.matrix.shape[0]] = n_counts.get(r.sm.matrix.shape[0], 0) + 1
    syn = []
    for n, cnt in n_counts.items():
        if n < 4:
            continue
        for k in range(cnt):
            team = generate_team(n, base_seed + n * 10_000 + k,
                                 profile="reliable", include_self=True)
            syn.append((team.score_matrix, (team.score_matrix.team_name, "natural", str(k))))
    syn_rows = _observables(syn, "synthetic", n_perm)

    comp = pd.concat([real_rows, syn_rows], ignore_index=True)
    # Summary: state proportions, coverage, mean-τ, qualifying-rater fraction.
    summ = []
    for src in ("real", "synthetic"):
        sub = comp[comp.source == src]
        summ.append({
            "source": src, "n": len(sub),
            "coverage_tau": float(sub["tau_computable"].mean()),
            "mean_tau_median": float(sub["mean_tau"].dropna().median()),
            "qualifying_frac_mean": float(sub["qualifying_frac"].mean()),
            "pct_silent": float((sub["state_group"] == "Silent").mean()),
            "pct_contested": float((sub["state_group"] == gates.CONTESTED).mean()),
            "pct_standout": float(sub["state_group"].isin(STANDOUTS).mean()),
        })
    return comp, pd.DataFrame(summ)


def _observables(items, source: str, n_perm: int) -> pd.DataFrame:
    rows = []
    for sm, key in items:
        mat = ranks.prepare_matrix(sm)
        n = mat.shape[0]
        qual = int(ranks.qualifying_raters(mat).sum())
        mt = ranks.mean_pairwise_tau(mat)
        row = gates.classify_matrix(mat, tuple(str(x) for x in key), n_perm=n_perm)
        rows.append({"source": source, "N": n, "n_raters": qual,
                    "qualifying_frac": qual / n if n else np.nan,
                    "tau_computable": np.isfinite(mt), "mean_tau": mt,
                    "state": row.state, "state_group": canonical(row.state)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Headline metrics + CLI
# --------------------------------------------------------------------------- #

def headline_metrics(conf: pd.DataFrame) -> pd.DataFrame:
    """The three decision-relevant numbers, overall and per team size (Wilson CIs).

    Per-N matters because N=4 is structurally blind (raters share only 2 common
    recipients, below the ≥3 needed for a pairwise τ), so pooling hides it.
    """
    rows = []

    def _wil(sub, hit_mask, label, extra="", N="all"):
        k = int(hit_mask.sum()); n = int(len(sub))
        p, lo, hi = wilson(k, n)
        rows.append({"metric": label, "N": N, "k": k, "n": n, "rate": p,
                    "wilson_lo": lo, "wilson_hi": hi, "note": extra})

    def _by_n(planted, hit_fn, label, extra=""):
        sub = conf[conf.planted == planted]
        _wil(sub, hit_fn(sub), label, extra)
        for N in SIZES:
            s = sub[sub.N == N]
            _wil(s, hit_fn(s), label, extra, N=N)

    _by_n("One at bottom", lambda s: s.recovered == gates.ONE_AT_BOTTOM,
          "free-rider state recall")
    _by_n("One at bottom", lambda s: s.member_correct == True,  # noqa: E712
          "free-rider member+state recall")
    _by_n("Even", lambda s: s.recovered.isin(STANDOUTS),
          "Even false-positive (standout) rate", "governs deployment safety")
    _by_n("Contested", lambda s: s.recovered == gates.CONTESTED,
          "Contested recall (Gate B fires)", "decision-relevant for the faction null")
    return pd.DataFrame(rows)


def _write(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / name, index=False)
    print(f"  Saved {OUT / name} ({len(df)} rows)", flush=True)


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv and not argv[0].startswith("-") else "all"
    n_perm = int(argv[argv.index("--n-perm") + 1]) if "--n-perm" in argv else 500
    reps = int(argv[argv.index("--reps") + 1]) if "--reps" in argv else 50
    OUT.mkdir(parents=True, exist_ok=True)

    if cmd in ("confusion", "all"):
        conf = run_confusion(reps, n_perm)
        _write(conf, "confusion_raw.csv")
        ct = pd.crosstab(conf["planted"], conf["recovered_group"])
        _write(ct.reset_index(), "confusion_matrix.csv")
        hm = headline_metrics(conf)
        _write(hm, "headline_metrics.csv")
        print(hm.to_string(index=False), flush=True)
    if cmd in ("lazy", "all"):
        lz = run_lazy_test(reps, n_perm)
        _write(lz, "lazy_test.csv")
        print(pd.crosstab(lz["arm"], lz["recovered_group"]).to_string(), flush=True)
    if cmd in ("power", "all"):
        pc = run_power_curve(min(reps, 30), n_perm)
        _write(pc, "power_curve.csv")
        _print_thresholds(pc)
    if cmd in ("robustness", "all"):
        rb = run_robustness(min(reps, 40), n_perm)
        _write(rb, "robustness.csv")
        print(rb.pivot_table(index="profile", columns=["metric", "N"], values="rate").round(2).to_string(), flush=True)
    if cmd in ("realism", "all"):
        comp, summ = run_realism(n_perm)
        _write(comp, "realism_permatrix.csv")
        _write(summ, "realism_summary.csv")
        print(summ.to_string(index=False), flush=True)

    print(f"\nDone. Validation artefacts in {OUT}/", flush=True)


def _print_thresholds(pc: pd.DataFrame) -> None:
    for (profile, n), g in pc.groupby(["profile", "N"]):
        g = g.sort_values("delta")
        d50 = _cross(g, 0.5); d80 = _cross(g, 0.8)
        print(f"  {profile:8s} N={n}: δ@50%={d50}  δ@80%={d80}", flush=True)


def _cross(g: pd.DataFrame, level: float):
    hit = g[g["rate"] >= level]
    return float(hit["delta"].iloc[0]) if len(hit) else float("nan")


if __name__ == "__main__":
    main()

