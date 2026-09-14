"""Compare v1 vs v2 per-sprint marks: reliability + validity proxies.

v1 (marks_sprint) fired a flag on a majority vote and attached whatever quote the
model gave — reliable marks, but the quote often didn't support the flag. v2
(marks_sprint_v2) is evidence-grounded: a flag fires only with a directly-supporting
verbatim quote. This script quantifies the difference.

All metrics are objective/offline. A true "does the quote support the flag?" score
needs a judge, so this reports strong PROXIES and can export a sample for manual (or
LLM-as-judge) review:
  - fired-flag counts (v2 should fire fewer, esp. concern flags on weak signal)
  - reliability: run-to-run unanimous agreement per flag
  - quote instability: % of fired flags whose runs give >1 distinct quote
  - quote traceability: % of cited quotes found verbatim in a member's journal
  - concern-with-positive-quote rate: crude mismatch proxy (lower is better)

    python3 scripts/compare_v1_v2.py [--cohort 2025_s1] [--sample 40]
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.qualitative.llm import blobs, sprint_analysis as sa

CONCERN = {"effort_imbalance", "member_under_contributed", "underperformance_unaddressed",
           "core_subgroup_carried", "singled_out_below", "open_conflict",
           "communication_breakdown", "leadership_problem"}
POS_WORDS = re.compile(
    r"\b(happy|grateful|great|good relationship|well together|supported|enjoy|"
    r"smoothly|no (major )?issues|fair|effective|balanced)\b", re.I)

def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def member_index(cohort: str) -> dict:
    df = blobs._entries(cohort)
    idx: dict = {}
    for _, r in df.iterrows():
        idx.setdefault((r["team_label"], int(r["journal_index"])), {})[r["member_label"]] = _norm(r["text"])
    return idx


def traceable(text: str, per: dict, W: int = 30, S: int = 12) -> bool:
    nq = _norm(text)
    if not nq:
        return False
    if len(nq) < W:
        return any(nq in t for t in per.values())
    win = [nq[i:i + W] for i in range(0, len(nq) - W + 1, S)]
    return any(sum(1 for w in win if w in t) >= 0.6 * len(win) for t in per.values())


def analyse(marks_dir, cohort: str, sample_rows: list | None = None, tag: str = "") -> dict | None:
    cells = {k: v for k, v in sa.load_cells(marks_dir).items() if k[0] == cohort}
    if not cells:
        return None
    midx = member_index(cohort)
    per_flag = {k: {"fired": 0, "unan": 0, "n": 0} for k in sa.ITEMS}
    fired = instab = instab_den = q_total = q_trace = concern_fired = concern_pos = 0
    for (c, t, ji), runs in cells.items():
        ne = [r for r in runs if r.get("marks")]
        if len(ne) < 2:
            continue
        marks, _ = sa.consensus(runs)
        per = midx.get((t, ji), {})
        for k in sa.ITEMS:
            vals = [bool(r["marks"].get(k)) for r in ne]
            per_flag[k]["n"] += 1
            if len(set(vals)) == 1:
                per_flag[k]["unan"] += 1
            if not marks.get(k):
                continue
            per_flag[k]["fired"] += 1
            fired += 1
            cq = [it["text"] for r in ne if r["marks"].get(k) for it in sa.quote_items(r, k)]
            distinct = {_norm(x) for x in cq} - {""}
            instab_den += 1
            if len(distinct) > 1:
                instab += 1
            for qt in cq:
                q_total += 1
                if traceable(qt, per):
                    q_trace += 1
            if k in CONCERN:
                concern_fired += 1
                if any(POS_WORDS.search(qt) for qt in cq):
                    concern_pos += 1
                    if sample_rows is not None:
                        sample_rows.append({"marks": tag, "team": t, "sprint": ji, "flag": k,
                                            "quote": (cq[0] if cq else "")[:200]})
    for s in per_flag.values():
        s["reliab"] = round(100 * s["unan"] / s["n"], 1) if s["n"] else 0.0
    return {
        "cells": len({(c, t, ji) for (c, t, ji) in cells}),
        "fired": fired,
        "instab_pct": round(100 * instab / instab_den, 1) if instab_den else 0.0,
        "trace_pct": round(100 * q_trace / q_total, 1) if q_total else 0.0,
        "q_total": q_total,
        "concern_pos_pct": round(100 * concern_pos / concern_fired, 1) if concern_fired else 0.0,
        "concern_fired": concern_fired,
        "per_flag": per_flag,
    }


def _fmt(v1, v2, key):
    a = v1[key] if v1 else "—"
    b = v2[key] if v2 else "—"
    return f"{a!s:>10}{b!s:>10}"


def main() -> None:
    argv = sys.argv[1:]
    cohort = next((argv[i + 1] for i, a in enumerate(argv) if a == "--cohort"), "2025_s1")
    n_sample = int(next((argv[i + 1] for i, a in enumerate(argv) if a == "--sample"), "0"))
    sample: list = [] if n_sample else None

    v1 = analyse(sa._MARKS, cohort, sample, "v1")
    v2 = analyse(sa._MARKS_V2, cohort, sample, "v2")

    print(f"\n=== v1 vs v2 per-sprint marks — {cohort} ===")
    if not v1:
        print("no v1 marks found."); return
    if not v2:
        print("no v2 marks yet (run sprint_v2 first) — showing v1 only.\n")
    print(f"{'metric':<34}{'v1':>10}{'v2':>10}")
    print(f"{'cells':<34}{_fmt(v1, v2, 'cells')}")
    print(f"{'flags fired (consensus)':<34}{_fmt(v1, v2, 'fired')}")
    print(f"{'concern flags fired':<34}{_fmt(v1, v2, 'concern_fired')}")
    print(f"{'quote instability % (lower=better)':<34}{_fmt(v1, v2, 'instab_pct')}")
    print(f"{'quote traceability % (higher=better)':<34}{_fmt(v1, v2, 'trace_pct')}")
    print(f"{'concern w/ positive quote % (lower)':<34}{_fmt(v1, v2, 'concern_pos_pct')}")

    print(f"\n{'flag':<28}{'v1 fired':>9}{'v2 fired':>9}{'v1 reliab':>11}{'v2 reliab':>11}")
    for k in sa.ITEMS:
        a = v1["per_flag"][k]
        b = v2["per_flag"][k] if v2 else None
        print(f"{k:<28}{a['fired']:>9}{(b['fired'] if b else '—'):>9}"
              f"{a['reliab']:>10}%{(str(b['reliab']) + '%' if b else '—'):>11}")

    if sample is not None and sample:
        out = blobs._REPO / "output/qualitative/llm/validity_sample.csv"
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["marks", "team", "sprint", "flag", "quote"])
            w.writeheader()
            w.writerows(sample[:n_sample * 2])
        print(f"\nwrote {len(sample[:n_sample*2])} concern-with-positive-quote examples to {out} for manual review")


if __name__ == "__main__":
    main()
