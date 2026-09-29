"""Per-sprint blind-spot analysis: where journals and peer scores diverge.

Three analyses, all at the (team, sprint) cell level:

  1. BLIND-SPOT 2×2  — peer contribution even × journal non-contribution flag fired.
     The headline: ~65% of journal-flagged cells are peer-invisible.
  2. PER-FLAG BREAKDOWN — which dynamics the peers miss (and which they don't),
     per-flag asymmetry (journal-only vs peer-only), and co-firing with positives.
  3. PREDICTIVE — does a blind-spot cell at sprint k predict a peer decline at k+1?
     Per-flag predictive odds ratios.

Plus a MAPPING CHECK (peer contribution × journal contribution flag) as a sanity
check on the Session k ↔ Journal (k+1) mapping.

Mapping: journal_index j → peer Session (j−1).
Peer "even" = every member's perceived contribution (PC) >= TH (100 = equal share).

    python3 -m scripts.blind_spot           # full report
    python3 -m scripts.blind_spot --th 90   # try a stricter threshold
    python3 -m scripts.blind_spot --gee     # include GEE clustered model
"""
from __future__ import annotations

import argparse
import csv
import glob
import sys
from collections import Counter, defaultdict

sys.path.insert(0, ".")
from src.qualitative.llm import sprint_analysis as sa, blobs

NONCONTRIB = {"open_conflict", "communication_breakdown", "leadership_problem"}
CONTRIB = {"effort_imbalance", "member_under_contributed"}
CONTRIB_BROAD = {
    "effort_imbalance", "member_under_contributed", "underperformance_unaddressed",
    "core_subgroup_carried", "singled_out_below", "singled_out_above",
}
ALL_NEG = {f for f in sa.LABELS if f not in ("harmonious_balanced", "mutual_support")}


# ---- peer-data helpers (shared) -----------------------------------------

def _peer_prefix(cohort: str) -> str:
    year, sem = cohort.split("_")
    return f"COMPSCI399-S{sem[1]}-{year}_Peer_Session"


def _contribution_block(path: str) -> dict[str, list[float]]:
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    hdr = next((i for i, l in enumerate(lines) if l.startswith("Team,Name,Email")), None)
    if hdr is None:
        return {}
    out: dict[str, list[float]] = {}
    for l in lines[hdr + 1:]:
        if not l.strip() or l.startswith("Question") or l.startswith("Summary"):
            break
        row = next(csv.reader([l]))
        if len(row) < 5 or not row[0].strip().startswith("Team"):
            continue
        try:
            pc = float(row[4])
        except ValueError:
            continue
        out.setdefault(row[0].strip(), []).append(pc)
    return out


def _peer_by_session(cohort: str) -> dict[int, dict[str, float]]:
    """session_num -> {real_team: min PC}."""
    res = {}
    for path in sorted(glob.glob(f"data/peer_sessions/{_peer_prefix(cohort)}*.csv")):
        n = int(path.rsplit("Session", 1)[1].split(".")[0])
        block = _contribution_block(path)
        res[n] = {t: min(v) for t, v in block.items() if v}
    return res


def _team_key(cohort: str) -> dict[str, str]:
    f = f"output/qualitative/reader/team_key_{cohort}.csv"
    return {
        r["team_label"]: r["real_team"].strip()
        for r in csv.DictReader(open(f, encoding="utf-8", errors="replace"))
    }


# ---- load all cells with peer + journal data ----------------------------

def load_matched_cells(th: int) -> list[dict]:
    """Return one record per (cohort, team, sprint) with peer and journal data."""
    cells = sa.load_cells()
    out = []
    for cohort in blobs.PROMPTED:
        tk = _team_key(cohort)
        peer = _peer_by_session(cohort)
        for (c, t, ji), runs in cells.items():
            if c != cohort:
                continue
            session = ji - 1
            real = tk.get(t)
            if real is None or session not in peer or real not in peer[session]:
                continue
            minpc = peer[session][real]
            marks, _ = sa.consensus(runs)
            out.append({
                "cohort": cohort, "team": t, "real_team": real,
                "journal_index": ji, "session": session,
                "minpc": minpc, "peer_fine": minpc >= th,
                "marks": marks,
            })
    return out


# ---- analysis 1: headline 2×2 ------------------------------------------

def report_headline(recs: list[dict]) -> None:
    bs = Counter()  # (peer_fine, journal_noncontrib)
    per_cohort: Counter = Counter()
    for r in recs:
        j_nc = any(r["marks"].get(k) for k in NONCONTRIB)
        bs[(r["peer_fine"], j_nc)] += 1
        if r["peer_fine"] and j_nc:
            per_cohort[r["cohort"]] += 1

    print("=" * 72)
    print("1. BLIND SPOT: peer contribution even × journal conflict/comms/leadership")
    print("=" * 72)
    print(f"                              journal FLAGGED   journal clean")
    print(f"  peer even (fine)               {bs[(True,True)]:^7}        {bs[(True,False)]:^5}   <- BLIND SPOT = {bs[(True,True)]}")
    print(f"  peer flags freeloader          {bs[(False,True)]:^7}        {bs[(False,False)]:^5}")
    tot_jflag = bs[(True, True)] + bs[(False, True)]
    if tot_jflag:
        print(f"  -> of {tot_jflag} journal-flagged cells, {bs[(True,True)]} ({100*bs[(True,True)]/tot_jflag:.0f}%) are peer-invisible")
    print(f"  by cohort: {dict(per_cohort)}")


# ---- analysis 2: per-flag breakdown ------------------------------------

def report_per_flag(recs: list[dict]) -> None:
    from scipy.stats import fisher_exact

    print()
    print("=" * 72)
    print("2a. PER-FLAG BLIND-SPOT RATE (flag fires AND peer fine)")
    print("=" * 72)
    per_flag: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in recs:
        for f in sa.LABELS:
            if r["marks"].get(f):
                per_flag[f][1] += 1
                if r["peer_fine"]:
                    per_flag[f][0] += 1

    print(f"  {'flag':35s} {'peer-fine':>9s} {'total':>6s} {'rate':>6s}")
    for f in sorted(per_flag, key=lambda x: per_flag[x][0] / max(per_flag[x][1], 1), reverse=True):
        fine, tot = per_flag[f]
        print(f"  {f:35s} {fine:9d} {tot:6d}  {100*fine/tot:5.1f}%")

    # per non-contrib flag asymmetry
    print()
    print("=" * 72)
    print("2b. ASYMMETRY per non-contribution flag (journal-only vs peer-only)")
    print("=" * 72)
    for flag in sorted(NONCONTRIB):
        both = jonly = ponly = neither = 0
        for r in recs:
            j_fires = r["marks"].get(flag, False)
            peer_low = not r["peer_fine"]
            if j_fires and peer_low:
                both += 1
            elif j_fires:
                jonly += 1
            elif peer_low:
                ponly += 1
            else:
                neither += 1
        total = both + jonly + ponly + neither
        print(f"\n  {flag}:")
        print(f"    Both flag:      {both:4d}  ({100*both/total:.1f}%)")
        print(f"    Journal only:   {jonly:4d}  ({100*jonly/total:.1f}%)  <- blind spot")
        print(f"    Peer only:      {ponly:4d}  ({100*ponly/total:.1f}%)")
        print(f"    Neither:        {neither:4d}  ({100*neither/total:.1f}%)")
        if jonly + both:
            print(f"    When journal flags: {100*jonly/(jonly+both):.0f}% peer-invisible")

    # positive co-firing in blind-spot cells
    print()
    print("=" * 72)
    print("2c. POSITIVE FLAGS in blind-spot cells (peer fine + non-contrib flag)")
    print("=" * 72)
    bs_harm = bs_mut = bs_tot = 0
    for r in recs:
        if not r["peer_fine"]:
            continue
        if not any(r["marks"].get(k) for k in NONCONTRIB):
            continue
        bs_tot += 1
        if r["marks"].get("harmonious_balanced"):
            bs_harm += 1
        if r["marks"].get("mutual_support"):
            bs_mut += 1
    if bs_tot:
        print(f"  Blind-spot cells:          {bs_tot}")
        print(f"  Also harmonious_balanced:  {bs_harm} ({100*bs_harm/bs_tot:.0f}%)")
        print(f"  Also mutual_support:       {bs_mut} ({100*bs_mut/bs_tot:.0f}%)")


# ---- analysis 3: predictive power ---------------------------------------

def report_predictive(recs: list[dict], th: int) -> None:
    from scipy.stats import fisher_exact

    # build per-team timelines
    team_tl: dict[tuple, list[dict]] = defaultdict(list)
    for r in recs:
        team_tl[(r["cohort"], r["real_team"])].append(r)
    for v in team_tl.values():
        v.sort(key=lambda r: r["session"])

    # sprint k -> k+1: blind-spot flag predicts peer decline
    fd = fs = nd = ns = 0
    for traj in team_tl.values():
        for i in range(len(traj) - 1):
            r_now, r_next = traj[i], traj[i + 1]
            if not r_now["peer_fine"]:
                continue
            has_nc = any(r_now["marks"].get(k) for k in NONCONTRIB)
            drops = r_next["minpc"] < th
            if has_nc and drops:
                fd += 1
            elif has_nc:
                fs += 1
            elif drops:
                nd += 1
            else:
                ns += 1

    print()
    print("=" * 72)
    print("3a. PREDICTIVE: blind-spot cell at sprint k → peer decline at k+1")
    print("=" * 72)
    tot_bs = fd + fs
    tot_nobs = nd + ns
    if tot_bs:
        odds, p = fisher_exact([[fd, fs], [nd, ns]], alternative="greater")
        print(f"  Blind-spot -> next drops:  {fd:4d}   stays fine: {fs:4d}   rate: {100*fd/tot_bs:.0f}%")
        print(f"  No flag    -> next drops:  {nd:4d}   stays fine: {ns:4d}   rate: {100*nd/tot_nobs:.0f}%  (base)")
        print(f"  Odds ratio: {odds:.2f}   Fisher exact p = {p:.4f}")

    # per-flag predictive
    print()
    print("=" * 72)
    print("3b. PER-FLAG PREDICTIVE (sprint k flag + peer fine → peer decline k+1)")
    print("=" * 72)
    print(f"  {'flag':35s} {'fire→drop':>9s} {'fire→ok':>7s} {'rate':>6s}  {'base':>6s}  {'OR':>6s}  {'p':>8s}")
    for flag in sorted(ALL_NEG):
        f_d = f_s = n_d = n_s = 0
        for traj in team_tl.values():
            for i in range(len(traj) - 1):
                r_now, r_next = traj[i], traj[i + 1]
                if not r_now["peer_fine"]:
                    continue
                fires = r_now["marks"].get(flag, False)
                drops = r_next["minpc"] < th
                if fires and drops:
                    f_d += 1
                elif fires:
                    f_s += 1
                elif drops:
                    n_d += 1
                else:
                    n_s += 1
        tot_f = f_d + f_s
        tot_n = n_d + n_s
        if tot_f < 5:
            continue
        rate = f_d / tot_f if tot_f else 0
        base = n_d / tot_n if tot_n else 0
        odds, p = fisher_exact([[f_d, f_s], [n_d, n_s]], alternative="greater")
        sig = "*" if p < 0.05 else " "
        print(f"  {flag:35s} {f_d:9d} {f_s:7d}  {100*rate:5.1f}%  {100*base:5.1f}%  {odds:5.2f}  {p:7.4f}{sig}")

    # early -> late trajectory
    print()
    print("=" * 72)
    print("3c. TRAJECTORY: early blind-spot → late peer outcome")
    print("=" * 72)
    ebs_d = ebs_s = nebs_d = nebs_s = 0
    for traj in team_tl.values():
        if len(traj) < 2:
            continue
        mid = max(len(traj) // 2, 1)
        early, late = traj[:mid], traj[mid:]
        if not late:
            continue
        early_has_bs = any(
            any(r["marks"].get(k) for k in NONCONTRIB) and r["peer_fine"]
            for r in early
        )
        late_has_low = any(r["minpc"] < th for r in late)
        if early_has_bs:
            if late_has_low:
                ebs_d += 1
            else:
                ebs_s += 1
        else:
            if late_has_low:
                nebs_d += 1
            else:
                nebs_s += 1

    tot_ebs = ebs_d + ebs_s
    tot_nebs = nebs_d + nebs_s
    if tot_ebs and tot_nebs:
        odds, p = fisher_exact([[ebs_d, ebs_s], [nebs_d, nebs_s]], alternative="greater")
        print(f"  Early BS → later decline: {ebs_d}/{tot_ebs} ({100*ebs_d/tot_ebs:.0f}%)")
        print(f"  No early BS → later decline: {nebs_d}/{tot_nebs} ({100*nebs_d/tot_nebs:.0f}%)")
        print(f"  Odds ratio: {odds:.2f}   Fisher exact p = {p:.4f}")


# ---- analysis 4: GEE clustered model ------------------------------------

def report_gee(recs: list[dict], th: int) -> None:
    import pandas as pd
    import numpy as np
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.cov_struct import Exchangeable
    from scipy.stats import norm

    team_tl: dict[tuple, list[dict]] = defaultdict(list)
    for r in recs:
        team_tl[(r["cohort"], r["real_team"])].append(r)
    for v in team_tl.values():
        v.sort(key=lambda r: r["session"])

    rows = []
    for (cohort, real), traj in team_tl.items():
        for i in range(len(traj) - 1):
            r_now, r_next = traj[i], traj[i + 1]
            if r_now["minpc"] < th:
                continue
            rows.append({
                "team": f"{cohort}_{real}",
                "blind_spot": int(any(r_now["marks"].get(k) for k in NONCONTRIB)),
                "leadership": int(r_now["marks"].get("leadership_problem", False)),
                "comms": int(r_now["marks"].get("communication_breakdown", False)),
                "conflict": int(r_now["marks"].get("open_conflict", False)),
                "decline": int(r_next["minpc"] < th),
                "session": r_now["session"],
            })

    df = pd.DataFrame(rows).sort_values(["team", "session"])

    print()
    print("=" * 72)
    print("4. GEE (exchangeable, team clusters) — accounts for non-independence")
    print("=" * 72)
    print(f"  Transitions: {len(df)}, teams: {df['team'].nunique()}")

    gee = GEE.from_formula(
        "decline ~ blind_spot", groups="team", data=df,
        family=Binomial(), cov_struct=Exchangeable(),
    ).fit()
    coef = gee.params["blind_spot"]
    se = gee.bse["blind_spot"]
    z = coef / se
    p_one = norm.sf(z)
    print(f"\n  blind_spot: coef={coef:.3f}, OR={np.exp(coef):.2f}, "
          f"robust SE={se:.3f}, z={z:.2f}")
    print(f"  p (two-sided)={gee.pvalues['blind_spot']:.4f}, p (one-sided)={p_one:.4f}")
    print(f"  within-team correlation: {gee.cov_struct.summary()}")

    gee2 = GEE.from_formula(
        "decline ~ leadership + comms + conflict", groups="team", data=df,
        family=Binomial(), cov_struct=Exchangeable(),
    ).fit()
    print(f"\n  Per-flag GEE:")
    for var in ["leadership", "comms", "conflict"]:
        or_val = np.exp(gee2.params[var])
        print(f"    {var:20s} OR={or_val:.2f}, p={gee2.pvalues[var]:.4f}")


# ---- mapping check (same as before) ------------------------------------

def report_mapping_check(recs: list[dict]) -> None:
    mp: Counter = Counter()
    for r in recs:
        peer_low = not r["peer_fine"]
        j_contrib = any(r["marks"].get(k) for k in CONTRIB)
        mp[(peer_low, j_contrib)] += 1

    a, b, c2, d = mp[(True, True)], mp[(True, False)], mp[(False, True)], mp[(False, False)]
    print()
    print("=" * 72)
    print("MAPPING CHECK: same construct (contribution) at the mapped timepoint")
    print("=" * 72)
    print(f"                              journal imbalance   journal ok")
    print(f"  peer low PC                    {a:^7}         {b:^5}")
    print(f"  peer even PC                   {c2:^7}         {d:^5}")
    if a + c2:
        print(f"  when journals say imbalance, peer also low: {a}/{a+c2} ({100*a/(a+c2):.0f}%)")
    if a + b:
        print(f"  when peer says low, journals also imbalance: {a}/{a+b} ({100*a/(a+b):.0f}%)")
    agree = (a + d) / (a + b + c2 + d) if (a + b + c2 + d) else 0
    print(f"  overall agreement on contribution: {100*agree:.0f}%")


# ---- main ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--th", type=int, default=85, help="PC threshold for 'peer fine' (default 85)")
    parser.add_argument("--gee", action="store_true", help="include GEE clustered model (needs statsmodels)")
    args = parser.parse_args()

    print(f"Blind-spot analysis  |  TH={args.th}  |  mapping: session = journal_index − 1\n")
    recs = load_matched_cells(args.th)
    n_total = len(sa.load_cells())
    print(f"Cells matched (peer + journal): {len(recs)} / {n_total}")

    report_headline(recs)
    report_per_flag(recs)
    report_predictive(recs, args.th)
    if args.gee:
        report_gee(recs, args.th)
    report_mapping_check(recs)


if __name__ == "__main__":
    main()
