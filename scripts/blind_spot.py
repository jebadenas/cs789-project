"""Per-sprint blind-spot analysis + a session<->sprint mapping sanity-check.

Blind spot (the thesis): peer contribution is even (no freeloader by the numbers) BUT the
journals flag a NON-contribution dynamic (conflict / comms / leadership) at that sprint.

Mapping check: peer scores and journal contribution flags measure the SAME thing, so if
the Session k <-> Sprint k mapping is right they should agree on contribution imbalance.

Unit = (team, sprint). Mapping: journal_index j -> peer Session (j-1)  [sprint k = j=k+1 = session k].
Peer "even" = every member's perceived contribution (PC) >= TH (100 = equal share).
Provisional: TH and the mapping are assumptions to confirm with the coordinator.
"""
from __future__ import annotations
import csv, glob, sys
from collections import Counter
sys.path.insert(0, ".")
from src.qualitative.llm import sprint_analysis as sa, blobs

TH = 85
NONCONTRIB = {"open_conflict", "communication_breakdown", "leadership_problem"}
CONTRIB = {"effort_imbalance", "member_under_contributed"}  # clearest "someone not pulling weight"


def peer_prefix(cohort: str) -> str:
    year, sem = cohort.split("_")            # "2025", "s1"
    return f"COMPSCI399-S{sem[1]}-{year}_Peer_Session"


def contribution_block(path: str) -> dict[str, list[float]]:
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


def peer_by_session(cohort: str) -> dict[int, dict[str, float]]:
    """session_num -> {real_team: min PC}."""
    res = {}
    for path in sorted(glob.glob(f"data/peer_sessions/{peer_prefix(cohort)}*.csv")):
        n = int(path.rsplit("Session", 1)[1].split(".")[0])
        block = contribution_block(path)
        res[n] = {t: min(v) for t, v in block.items() if v}
    return res


def team_key(cohort: str) -> dict[str, str]:
    f = f"output/qualitative/reader/team_key_{cohort}.csv"
    return {r["team_label"]: r["real_team"].strip() for r in csv.DictReader(open(f, encoding="utf-8", errors="replace"))}


def main():
    cells = sa.load_cells()
    # blind-spot 2x2 and mapping-check tallies (overall + per cohort)
    bs = Counter()      # (peer_fine, journal_noncontrib)
    mp = Counter()      # (peer_low, journal_contrib)  -- same-construct agreement
    per_cohort = Counter()
    n_cells = n_nopeer = 0

    for cohort in blobs.PROMPTED:
        tk = team_key(cohort)
        peer = peer_by_session(cohort)
        for (c, t, ji), runs in cells.items():
            if c != cohort:
                continue
            session = ji - 1
            real = tk.get(t)
            if real is None or session not in peer or real not in peer[session]:
                n_nopeer += 1
                continue
            n_cells += 1
            minpc = peer[session][real]
            peer_fine = minpc >= TH
            marks, _ = sa.consensus(runs)
            j_noncontrib = any(marks.get(k) for k in NONCONTRIB)
            j_contrib = any(marks.get(k) for k in CONTRIB)
            bs[(peer_fine, j_noncontrib)] += 1
            mp[(not peer_fine, j_contrib)] += 1   # peer_low = not peer_fine
            if peer_fine and j_noncontrib:
                per_cohort[cohort] += 1

    print(f"cells analysed: {n_cells}  (skipped, no peer match: {n_nopeer})  TH={TH}, mapping session=journal_index-1\n")
    print("== BLIND SPOT (thesis): peer contribution even  x  journal conflict/comms/leadership ==")
    print(f"                              journal FLAGGED   journal clean")
    print(f"  peer even (fine)               {bs[(True,True)]:^7}        {bs[(True,False)]:^5}   <- BLIND SPOT = {bs[(True,True)]}")
    print(f"  peer flags freeloader          {bs[(False,True)]:^7}        {bs[(False,False)]:^5}")
    tot_jflag = bs[(True,True)] + bs[(False,True)]
    if tot_jflag:
        print(f"  -> of {tot_jflag} journal-flagged cells, {bs[(True,True)]} ({100*bs[(True,True)]/tot_jflag:.0f}%) are peer-invisible")
    print("  by cohort (blind-spot cells):", dict(per_cohort))

    print("\n== MAPPING CHECK: same construct (contribution) at the mapped timepoint ==")
    print(f"                              journal imbalance   journal ok")
    print(f"  peer low PC                    {mp[(True,True)]:^7}         {mp[(True,False)]:^5}")
    print(f"  peer even PC                   {mp[(False,True)]:^7}         {mp[(False,False)]:^5}")
    a, b, c2, d = mp[(True,True)], mp[(True,False)], mp[(False,True)], mp[(False,False)]
    if (a+c2): print(f"  when journals say imbalance, peer also low: {a}/{a+c2} ({100*a/(a+c2):.0f}%)")
    if (a+b): print(f"  when peer says low, journals also imbalance: {a}/{a+b} ({100*a/(a+b):.0f}%)")
    agree = (a + d) / (a+b+c2+d) if (a+b+c2+d) else 0
    print(f"  overall agreement on contribution: {100*agree:.0f}%  (low agreement => mapping and/or construct mismatch)")


if __name__ == "__main__":
    main()
