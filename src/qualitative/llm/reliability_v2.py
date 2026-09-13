"""Workstream 3 read-out: did the gate+follow-up rewrite fix the two weak fields?

Two things, both over output/qualitative/llm/marks_v2/ (119 teams x 3 shuffled runs):

  1. Reliability. Reconstruct the v1 3-way labels (conflict_handling, trajectory)
     from v2's gate+follow-up, then compute run-to-run agreement (teams where all 3
     runs are unanimous). Compared head-to-head against the same measure recomputed
     on the frozen v1 marks/ — the numbers to beat are 55% and 72%.

  2. Quote check. Every v2 answer carries a verbatim journal quote. String-match each
     quote back to the team's blob and report the quote-not-found rate — a direct
     hallucination signal.

    python3 -m src.qualitative.llm.reliability_v2

Analysis only — reads existing marks, calls no model. Writes a summary JSON next to
the v2 marks.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from . import blobs, marking, marking_v2

_V1 = marking._OUT
_V2 = marking_v2._OUT
_SUMMARY = _V2 / "reliability_v2_summary.json"


# ---- loading ---------------------------------------------------------------

def _load(dirpath) -> dict[tuple[str, str], list[dict]]:
    """(cohort, team) -> run records sorted by run index."""
    teams: dict[tuple[str, str], list[dict]] = {}
    for f in sorted(dirpath.glob("*_r*.json")):
        d = json.loads(f.read_text())
        teams.setdefault((d["cohort"], d["team_label"]), []).append(d)
    for recs in teams.values():
        recs.sort(key=lambda r: r["run"])
    return teams


# ---- reconstruct v1 labels from v2 gate+follow-up --------------------------

def reconstruct(marks: dict) -> tuple[str | None, str | None]:
    """v2 marks -> (conflict_handling, trajectory) in v1's 3-way vocabulary."""
    ch = "none" if not marks.get("open_conflict") else marks.get("conflict_outcome")
    tj = "stable" if not marks.get("notable_change") else marks.get("change_direction")
    return ch, tj


# ---- reliability -----------------------------------------------------------

def _agreement(values: list) -> tuple[bool, tuple]:
    """Unanimous iff all 3 runs equal and none missing. Returns (unanimous, sorted-pair)."""
    unanimous = len(set(values)) == 1 and all(v is not None for v in values)
    return unanimous, tuple(sorted({str(v) for v in values}))


def _field_reliability(teams: dict, extract) -> dict:
    """extract(record) -> the field value; report unanimous rate + dominant split."""
    n, unanimous, splits = 0, 0, Counter()
    for recs in teams.values():
        if len(recs) < 2:  # need >=2 runs to talk about agreement
            continue
        n += 1
        vals = [extract(r) for r in recs]
        ok, pair = _agreement(vals)
        if ok:
            unanimous += 1
        else:
            splits[pair] += 1
    top = splits.most_common(3)
    return {
        "n_teams": n,
        "unanimous": unanimous,
        "pct": round(100 * unanimous / n, 1) if n else 0.0,
        "top_splits": [{"pair": " / ".join(p), "count": c} for p, c in top],
    }


def reliability_report() -> dict:
    v1, v2 = _load(_V1), _load(_V2)
    out: dict = {"v1_frozen": {}, "v2_reworded": {}, "v2_gates": {}}

    # v1 as frozen: the categorical marks straight off the frozen instrument.
    out["v1_frozen"]["conflict_handling"] = _field_reliability(
        v1, lambda r: r["marks"].get("conflict_handling"))
    out["v1_frozen"]["trajectory"] = _field_reliability(
        v1, lambda r: r["marks"].get("trajectory"))

    # v2 reconstructed into the same 3-way vocabulary (apples-to-apples).
    out["v2_reworded"]["conflict_handling"] = _field_reliability(
        v2, lambda r: reconstruct(r["marks"])[0])
    out["v2_reworded"]["trajectory"] = _field_reliability(
        v2, lambda r: reconstruct(r["marks"])[1])

    # the raw gates, to show the yes/no decision itself is reliable.
    out["v2_gates"]["open_conflict"] = _field_reliability(
        v2, lambda r: r["marks"].get("open_conflict"))
    out["v2_gates"]["notable_change"] = _field_reliability(
        v2, lambda r: r["marks"].get("notable_change"))
    return out


# ---- quote check (hallucination signal) ------------------------------------

_WS = re.compile(r"\s+")
_SMART = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                        "–": "-", "—": "-"})


def _norm(s: str) -> str:
    # Strip ALL whitespace (not just collapse) so the match is whitespace-insensitive:
    # the model sometimes returns quotes with spaces dropped or line-breaks added, and
    # PDF extraction varies — none of which is a hallucination. This makes the
    # not-found rate a truer (tighter) upper bound on real fabrication.
    return _WS.sub("", s.translate(_SMART).lower())


def quote_report(*, min_len: int = 8) -> dict:
    """Fraction of non-empty quotes that are NOT verbatim substrings of the blob."""
    v2 = _load(_V2)
    per_field: dict[str, Counter] = {k: Counter() for k in marking_v2.FIELDS}
    misses: list[dict] = []
    total = found = checked = trivial = empty = 0
    for (cohort, team), recs in v2.items():
        blobs_by_run = {r["run"]: _norm(blobs.build_blob(cohort, team, seed=r["run"])) for r in recs}
        for r in recs:
            hay = blobs_by_run[r["run"]]
            for field, q in r.get("quotes", {}).items():
                q = (q or "").strip()
                total += 1
                if not q:
                    empty += 1
                    continue
                if len(q) < min_len:  # too short to verify meaningfully
                    trivial += 1
                    continue
                checked += 1
                per_field[field]["checked"] += 1
                if _norm(q) in hay:
                    found += 1
                    per_field[field]["found"] += 1
                else:
                    per_field[field]["missing"] += 1
                    if len(misses) < 40:  # keep a sample for eyeballing
                        misses.append({"cohort": cohort, "team": team, "run": r["run"],
                                       "field": field, "quote": q[:160]})
    return {
        "quotes_total": total,
        "empty": empty,
        "trivial_skipped": trivial,
        "checked": checked,
        "found": found,
        "not_found": checked - found,
        "not_found_pct": round(100 * (checked - found) / checked, 1) if checked else 0.0,
        "per_field": {k: dict(v) for k, v in per_field.items()},
        "sample_misses": misses,
    }


# ---- report ----------------------------------------------------------------

def _print_reliability(rel: dict) -> None:
    print("\n== Reliability (run-to-run unanimous over 3 shuffled runs) ==")
    print(f"{'field':<20}{'v1 frozen':>14}{'v2 reworded':>14}")
    for field in ("conflict_handling", "trajectory"):
        a = rel["v1_frozen"][field]
        b = rel["v2_reworded"][field]
        print(f"{field:<20}{a['pct']:>12}% {b['pct']:>12}% "
              f"  ({a['unanimous']}/{a['n_teams']} -> {b['unanimous']}/{b['n_teams']})")
    print("\n  gates (the yes/no decision itself):")
    for g, s in rel["v2_gates"].items():
        print(f"    {g:<18}{s['pct']:>6}%  ({s['unanimous']}/{s['n_teams']})")
    for field in ("conflict_handling", "trajectory"):
        sp = rel["v2_reworded"][field]["top_splits"]
        if sp:
            top = ", ".join(f"{s['pair']} ({s['count']})" for s in sp)
            print(f"  v2 {field} residual splits: {top}")


def _print_quotes(q: dict) -> None:
    print("\n== Quote check (verbatim match back to journals) ==")
    print(f"  quotes total {q['quotes_total']} | empty {q['empty']} | "
          f"too-short skipped {q['trivial_skipped']} | verified {q['checked']}")
    print(f"  NOT FOUND: {q['not_found']}/{q['checked']}  = {q['not_found_pct']}%  "
          f"(hallucination signal)")
    for field, s in q["per_field"].items():
        if s.get("checked"):
            miss = s.get("missing", 0)
            print(f"    {field:<18}{miss}/{s['checked']} not found")


def main() -> None:
    rel = reliability_report()
    quotes = quote_report()
    _print_reliability(rel)
    _print_quotes(quotes)
    _V2.mkdir(parents=True, exist_ok=True)
    _SUMMARY.write_text(json.dumps({"reliability": rel, "quotes": quotes}, indent=2))
    print(f"\nwrote {_SUMMARY}")


if __name__ == "__main__":
    main()
