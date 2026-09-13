"""Downstream read-out for the per-sprint marks (marks_sprint/, 3 shuffled runs).

Three jobs, all offline (no model calls except the summariser):
  1. consensus per (team, sprint) — majority-of-3 per flag + a representative quote;
  2. per-flag per-sprint RELIABILITY — run-to-run agreement, so we know which flags are
     trustworthy enough to USE (thin single-sprint text may be less reliable than the
     whole-project run, so we measure rather than assume);
  3. name-safe per-sprint SUMMARIES — generated from the fired flag *labels* only (never
     the raw journal), so no student names leak.

    python3 -m src.qualitative.llm.sprint_analysis            # print reliability report
    python3 -m src.qualitative.llm.sprint_analysis --summarize [--model qwen2.5:7b]
"""

from __future__ import annotations

import json
from collections import defaultdict

from . import blobs, marking_sprint

_MARKS = marking_sprint._OUT
_SUMM = blobs._REPO / "output/qualitative/llm/summaries_sprint"
ITEMS = marking_sprint.ITEMS  # the 11 v1 binaries

# name-free human labels + the contribution cluster tag (collapsed downstream, per the
# study design: capture the 4 separately, treat as one at analysis/display time)
LABELS = {
    "effort_imbalance": "uneven workload",
    "member_under_contributed": "a member under-contributing",
    "underperformance_unaddressed": "under-performance worked around, not addressed",
    "core_subgroup_carried": "a small core carrying the team",
    "singled_out_below": "one member singled out as weakest",
    "singled_out_above": "one member singled out as the standout",
    "open_conflict": "open conflict / interpersonal tension",
    "communication_breakdown": "communication breakdown",
    "harmonious_balanced": "worked well together, effort fair",
    "leadership_problem": "leadership problem or vacuum",
    "mutual_support": "members supported each other",
}
CONTRIB = {"effort_imbalance", "member_under_contributed", "underperformance_unaddressed",
           "core_subgroup_carried", "singled_out_below", "singled_out_above"}


# ---- loading + consensus ---------------------------------------------------

def load_cells() -> dict[tuple, list[dict]]:
    """(cohort, team, journal_index) -> run records sorted by run."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for f in sorted(_MARKS.glob("*_r*.json")):
        d = json.loads(f.read_text())
        cells[(d["cohort"], d["team_label"], d["journal_index"])].append(d)
    for recs in cells.values():
        recs.sort(key=lambda r: r.get("run", 0))
    return cells


def consensus(runs: list[dict]) -> tuple[dict, dict]:
    """Majority-of-3 per flag; a representative quote from a run that fired it."""
    nonempty = [r for r in runs if r.get("marks")]
    marks, quotes = {}, {}
    for k in ITEMS:
        tc = sum(1 for r in nonempty if r["marks"].get(k) is True)
        marks[k] = tc >= 2 if len(nonempty) >= 2 else tc >= 1
        if marks[k]:
            for r in nonempty:
                if r["marks"].get(k) and (r.get("quotes") or {}).get(k):
                    quotes[k] = r["quotes"][k]
                    break
    return marks, quotes


# ---- reliability -----------------------------------------------------------

def reliability_report() -> dict:
    """Per-flag run-to-run agreement across cells with >=2 non-empty runs."""
    cells = load_cells()
    per_flag = {k: {"n": 0, "unanimous": 0, "fired": 0} for k in ITEMS}
    n_cells = 0
    for recs in cells.values():
        ne = [r for r in recs if r.get("marks")]
        if len(ne) < 2:
            continue
        n_cells += 1
        for k in ITEMS:
            vals = [bool(r["marks"].get(k)) for r in ne]
            per_flag[k]["n"] += 1
            if len(set(vals)) == 1:
                per_flag[k]["unanimous"] += 1
            if sum(vals) >= (len(vals) / 2):
                per_flag[k]["fired"] += 1
    for k, s in per_flag.items():
        s["pct"] = round(100 * s["unanimous"] / s["n"], 1) if s["n"] else 0.0
        s["base_rate"] = round(100 * s["fired"] / s["n"], 1) if s["n"] else 0.0
    return {"n_cells": n_cells, "per_flag": per_flag}


def _print_reliability(rep: dict) -> None:
    print(f"\n== Per-sprint reliability — {rep['n_cells']} cells with >=2 runs ==")
    print(f"{'flag':<30}{'agree%':>8}{'base%':>8}   (base% = how often it fires)")
    for k in sorted(ITEMS, key=lambda k: -rep['per_flag'][k]['pct']):
        s = rep['per_flag'][k]
        tag = " [contrib cluster]" if k in CONTRIB else ""
        print(f"{k:<30}{s['pct']:>7}%{s['base_rate']:>7}%{tag}")
    print("\nNote: a rare flag scores high 'agree%' trivially (mostly-false) — read it "
          "alongside base%. Use flags that are both reliable AND actually fire.")


# ---- name-safe per-sprint summaries ---------------------------------------

SUMM_SYSTEM = (
    "You write a one-to-two sentence, factual summary of how a student team did in ONE "
    "sprint, for a course coordinator, based ONLY on the coded findings given. Do not "
    "invent anything. NEVER use individual people's names — say 'a member', 'one member', "
    "'the team'. Output only the summary."
)


def generate_summaries(model: str = "qwen2.5:7b", force: bool = False) -> None:
    from .model import call_model
    _SUMM.mkdir(parents=True, exist_ok=True)
    cells = load_cells()
    items = sorted(cells.items())
    for i, ((c, t, ji), runs) in enumerate(items, 1):
        out = _SUMM / f"{c}_{t}_j{ji}.json"
        if out.exists() and not force:
            continue
        marks, _ = consensus(runs)
        fired = [LABELS[k] for k in ITEMS if marks.get(k)]
        if not fired:
            prompt = ("This sprint's journals were coded and NO team-dynamics issues were "
                      "found. In one sentence, say the team looked fine this sprint.")
        else:
            prompt = ("Coded findings for one team in one sprint:\n- "
                      + "\n- ".join(fired) +
                      "\n\nWrite a 1-2 sentence summary of this team's dynamic this sprint, "
                      "based only on these findings.")
        try:
            text = call_model(prompt, system=SUMM_SYSTEM, temperature=0.3,
                              max_tokens=160, model=model).strip()
        except Exception as e:
            print(f"  [{i}/{len(items)}] {c} {t} j{ji} FAILED: {type(e).__name__}", flush=True)
            continue
        out.write_text(json.dumps({"cohort": c, "team_label": t, "journal_index": ji,
                                   "model": model, "summary": text}, indent=2))
        print(f"  [{i}/{len(items)}] {c} {t} j{ji} OK", flush=True)


def main() -> None:
    import sys
    argv = sys.argv[1:]
    if "--summarize" in argv:
        model = next((argv[i + 1] for i, a in enumerate(argv) if a == "--model"), "qwen2.5:7b")
        generate_summaries(model=model, force="--force" in argv)
    _print_reliability(reliability_report())


if __name__ == "__main__":
    main()
