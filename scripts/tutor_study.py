"""Analyse the tutor validation study (2026_s2, journal 3, 3-flag instrument).

Joins each tutor's exported answers to the questionnaire build they used
(``survey/src/app/cases.data.json``, the 2026-09-24 build) and reports:

1. Completeness: answers received vs cases/snippets assigned, per tutor.
2. Snippet classification (Part 2), on the tool's flagged snippets:
   agreement = the tool's flag is among the tutor's picks; "none" = tutor says
   the passage shows no problem; "can't tell". Per flag, with 95% CIs.
3. Controls, reported separately: obvious-flag controls (agreement) and benign
   controls (share the tutor marked "none").
4. Tool flag x tutor label table (what tutors picked instead).
5. Team triage (Part 1, done before seeing any flags) against what the tool
   raised for that team.
6. How concentrated the flagged snippets are across teams.

Snippets are clustered within teams, so CIs are a team-level cluster bootstrap
(resample teams, keep each team's snippets together). Wilson intervals are given
too for comparison.

Output is aggregate only: no passages, names or free-text comments.

Run from the repo checkout that holds the (gitignored) data:
    python3 path/to/scripts/tutor_study.py [--responses data/study/responses]
        [--cases survey/src/app/cases.data.json] [--out output/qualitative/study]
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

FLAGS = ["conflict", "unequal_contribution", "coordination"]
TRIAGE = ["fine", "watch", "step_in"]
BOOT = 10_000
SEED = 789


def snippet_kind(sid: str) -> str:
    if sid.endswith("-ctrl-obvious"):
        return "obvious"
    if sid.endswith("-ctrl-benign"):
        return "benign"
    return "flagged"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def cluster_boot(rows: list[tuple[str, bool]], b: int = BOOT) -> tuple[float, float]:
    """95% CI for a proportion, resampling teams (rows = (team, hit))."""
    by_team: dict[str, list[bool]] = defaultdict(list)
    for team, hit in rows:
        by_team[team].append(hit)
    teams = list(by_team)
    if not teams:
        return (float("nan"), float("nan"))
    rng = random.Random(SEED)
    stats = []
    for _ in range(b):
        sample = [rng.choice(teams) for _ in teams]
        k = sum(sum(by_team[t]) for t in sample)
        n = sum(len(by_team[t]) for t in sample)
        stats.append(k / n)
    stats.sort()
    return (stats[int(0.025 * b)], stats[int(0.975 * b) - 1])


def prop(rows: list[tuple[str, bool]]) -> dict:
    k, n = sum(h for _, h in rows), len(rows)
    lo, hi = cluster_boot(rows)
    wl, wh = wilson(k, n)
    return {"k": k, "n": n, "p": k / n if n else float("nan"),
            "boot_lo": lo, "boot_hi": hi, "wilson_lo": wl, "wilson_hi": wh,
            "teams": len({t for t, _ in rows})}


def fmt(r: dict) -> str:
    if not r["n"]:
        return "n=0"
    return (f"{r['k']}/{r['n']} = {100 * r['p']:.0f}% "
            f"(team-bootstrap 95% CI {100 * r['boot_lo']:.0f}-{100 * r['boot_hi']:.0f}%; "
            f"{r['teams']} teams)")


def load(responses: Path, cases_path: Path):
    cases = json.loads(cases_path.read_text())
    snip, case_info = {}, {}
    for c in cases:
        flags = sorted({s["toolFlag"] for s in c.get("snippets", [])
                        if not s["isControl"] and s["toolFlag"]})
        case_info[c["id"]] = {"team": c["team"], "tutor": c.get("tutor"), "flags": flags,
                              "n_flagged": sum(1 for s in c.get("snippets", [])
                                               if not s["isControl"])}
        for s in c.get("snippets", []):
            snip[s["id"]] = {"tool": s["toolFlag"], "control": s["isControl"],
                             "kind": snippet_kind(s["id"]), "team": c["team"],
                             "case": c["id"], "tutor": c.get("tutor")}
    answers, triage = [], []
    for d in sorted(p for p in responses.iterdir() if p.is_dir()):
        p2 = json.loads((d / "part2-snippets.json").read_text())["data"]
        p1 = json.loads((d / "part1-triage.json").read_text())["data"]
        for a in p2:
            s = snip.get(a["snippetId"])
            if s is None:
                raise SystemExit(f"{d.name}: snippet {a['snippetId']} not in cases file")
            answers.append({**s, "id": a["snippetId"], "rater": d.name,
                            "labels": set(a["labels"])})
        for a in p1:
            info = case_info.get(a["caseId"])
            if info is None:
                raise SystemExit(f"{d.name}: case {a['caseId']} not in cases file")
            triage.append({**info, "case": a["caseId"], "rater": d.name,
                           "response": a["response"]})
    return cases, snip, case_info, answers, triage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", type=Path, default=Path("data/study/responses"))
    ap.add_argument("--cases", type=Path, default=Path("survey/src/app/cases.data.json"))
    ap.add_argument("--out", type=Path, default=Path("output/qualitative/study"))
    args = ap.parse_args()

    cases, snip, case_info, answers, triage = load(args.responses, args.cases)
    out: list[str] = []
    res: dict = {}
    p = out.append

    # 1. completeness ---------------------------------------------------------
    raters = sorted({a["rater"] for a in answers} | {t["rater"] for t in triage})
    p("# Tutor validation study: results\n")
    p(f"Raters with exports: {len(raters)}. Cases file: {len(cases)} cases, "
      f"{len(snip)} snippets.\n")
    p("## 1. Completeness\n")
    p("| Rater | Cases answered | Snippets answered | Snippets in their teams |")
    p("|---|---|---|---|")
    snip_by_team = Counter(s["team"] for s in snip.values())
    for r in raters:
        teams = {t["team"] for t in triage if t["rater"] == r}
        p(f"| {r} | {sum(t['rater'] == r for t in triage)} | "
          f"{sum(a['rater'] == r for a in answers)} | "
          f"{sum(snip_by_team[t] for t in teams)} |")
    res["n_triage"], res["n_snippet_answers"] = len(triage), len(answers)
    p(f"\nTotal: {len(triage)} team triage answers, {len(answers)} snippet answers.\n")

    # 2. flagged snippets -----------------------------------------------------
    flagged = [a for a in answers if a["kind"] == "flagged"]
    p("## 2. Tool-flagged snippets (Part 2, tool's label hidden)\n")
    agree = [(a["team"], a["tool"] in a["labels"]) for a in flagged]
    none_ = [(a["team"], "none" in a["labels"]) for a in flagged]
    cant = [(a["team"], "cant_tell" in a["labels"]) for a in flagged]
    res["flagged"] = {"agree": prop(agree), "none": prop(none_), "cant_tell": prop(cant)}
    p(f"- Tutor picked the tool's flag: {fmt(res['flagged']['agree'])}")
    p(f"- Tutor said no problem (\"none\"): {fmt(res['flagged']['none'])}")
    p(f"- Can't tell: {fmt(res['flagged']['cant_tell'])}")
    anyp = [(a["team"], bool(a["labels"] & set(FLAGS))) for a in flagged]
    res["flagged"]["any_problem"] = prop(anyp)
    p(f"- Tutor picked any of the three problems (not necessarily the tool's): "
      f"{fmt(res['flagged']['any_problem'])}")
    exact = [(a["team"], a["labels"] == {a["tool"]}) for a in flagged]
    p(f"- Tutor picked the tool's flag and nothing else: {fmt(prop(exact))}\n")
    res["by_rater"] = {}
    for r in raters:
        sub = [x for x in flagged if x["rater"] == r]
        k = sum(x["tool"] in x["labels"] for x in sub)
        res["by_rater"][r] = {"k": k, "n": len(sub)}
    p("- Agreement by tutor: " + ", ".join(
        f"{v['k']}/{v['n']}" for v in res["by_rater"].values()) +
      " (tutors anonymised in reporting)\n")
    p("| Tool flag | Snippets | Tutor agreed | Tutor said none |")
    p("|---|---|---|---|")
    res["by_flag"] = {}
    for f in FLAGS:
        sub = [a for a in flagged if a["tool"] == f]
        ag = prop([(a["team"], f in a["labels"]) for a in sub])
        no = prop([(a["team"], "none" in a["labels"]) for a in sub])
        res["by_flag"][f] = {"agree": ag, "none": no}
        p(f"| {f} | {len(sub)} | {fmt(ag)} | {fmt(no)} |")
    p("")

    # 3. controls -------------------------------------------------------------
    p("## 3. Controls (reported separately)\n")
    obv = [a for a in answers if a["kind"] == "obvious"]
    ben = [a for a in answers if a["kind"] == "benign"]
    res["obvious"] = prop([(a["team"], a["tool"] in a["labels"]) for a in obv])
    res["obvious_none"] = prop([(a["team"], "none" in a["labels"]) for a in obv])
    res["benign_none"] = prop([(a["team"], a["labels"] == {"none"}) for a in ben])
    res["benign_any_problem"] = prop([(a["team"], bool(a["labels"] & set(FLAGS)))
                                      for a in ben])
    p(f"- Obvious-flag controls (all 3 runs agreed): tutor picked the flag "
      f"{fmt(res['obvious'])}; said none {fmt(res['obvious_none'])}")
    p(f"- Benign controls (never flagged): tutor said none only "
      f"{fmt(res['benign_none'])}; picked a problem {fmt(res['benign_any_problem'])}\n")

    # 4. confusion ------------------------------------------------------------
    p("## 4. Tool flag x tutor labels (flagged snippets; multi-select, so rows can sum >100%)\n")
    cols = FLAGS + ["none", "cant_tell"]
    p("| Tool flag | n | " + " | ".join(cols) + " |")
    p("|---|---|" + "---|" * len(cols))
    res["confusion"] = {}
    for f in FLAGS:
        sub = [a for a in flagged if a["tool"] == f]
        row = {c: sum(c in a["labels"] for a in sub) for c in cols}
        res["confusion"][f] = row
        p(f"| {f} | {len(sub)} | " + " | ".join(
            f"{row[c]} ({100 * row[c] / len(sub):.0f}%)" if sub else "0" for c in cols) + " |")
    p("")

    # 5. triage ---------------------------------------------------------------
    p("## 5. Team triage (Part 1, before any flags were shown)\n")
    p("| Tutor's call | Teams | Tool raised >=1 flag | Mean flagged snippets |")
    p("|---|---|---|---|")
    res["triage"] = {}
    for r in TRIAGE:
        sub = [t for t in triage if t["response"] == r]
        anyf = sum(1 for t in sub if t["flags"])
        mean = sum(t["n_flagged"] for t in sub) / len(sub) if sub else float("nan")
        res["triage"][r] = {"teams": len(sub), "tool_any": anyf, "mean_flagged": mean}
        p(f"| {r} | {len(sub)} | {anyf} | {mean:.1f} |")
    concern = [t for t in triage if t["response"] in ("watch", "step_in")]
    fine = [t for t in triage if t["response"] == "fine"]
    a = sum(1 for t in concern if t["flags"]); b = len(concern) - a
    c = sum(1 for t in fine if t["flags"]); d = len(fine) - c
    res["triage_2x2"] = {"concern_flag": a, "concern_noflag": b,
                         "fine_flag": c, "fine_noflag": d}
    p(f"\n2x2: tutor concerned (watch/step in) & tool flagged = {a}; concerned & not flagged "
      f"= {b}; fine & flagged = {c}; fine & not flagged = {d}.")
    try:
        from scipy.stats import fisher_exact, mannwhitneyu
        orr, pf = fisher_exact([[a, b], [c, d]])
        u = mannwhitneyu([t["n_flagged"] for t in concern], [t["n_flagged"] for t in fine],
                         alternative="two-sided")
        res["triage_fisher_p"], res["triage_mwu_p"] = pf, u.pvalue
        p(f"Fisher exact p = {pf:.3f}. Flagged-snippet count, concerned vs fine teams: "
          f"Mann-Whitney p = {u.pvalue:.3f}. (Descriptive: {len(triage)} teams.)")
    except ImportError:
        p("(scipy not installed: tests skipped)")
    p("")

    # 6. concentration ----------------------------------------------------------
    all_flagged = sum(1 for c in case_info.values() if c["flags"])
    res["cohort_teams_flagged"] = {"k": all_flagged, "n": len(case_info)}
    p(f"Across the whole cohort the tool raised at least one flag for {all_flagged} of "
      f"{len(case_info)} teams.\n")
    p("## 6. Concentration of flagged snippets\n")
    per_team = Counter(a["team"] for a in flagged)
    teams_answered = {t["team"] for t in triage}
    counts = sorted((per_team.get(t, 0) for t in teams_answered), reverse=True)
    top2 = sum(counts[:2]) / sum(counts) if sum(counts) else float("nan")
    zero = sum(1 for x in counts if x == 0)
    res["concentration"] = {"teams": len(counts), "zero_flag_teams": zero,
                            "top2_share": top2, "counts": counts}
    p(f"Of {len(counts)} teams, {zero} had no flagged snippets. Flagged snippets per team "
      f"(sorted): {counts}. The two teams with the most flags hold {100 * top2:.0f}% of them.")
    by_rater_top = []
    for r in raters:
        rc = sorted((per_team.get(t["team"], 0) for t in triage if t["rater"] == r),
                    reverse=True)
        if sum(rc):
            by_rater_top.append(sum(rc[:2]) / sum(rc))
    if by_rater_top:
        p(f"Within each tutor's own teams, the top two teams hold "
          f"{100 * min(by_rater_top):.0f}-{100 * max(by_rater_top):.0f}% of that tutor's "
          f"flagged snippets.")

    p("\n## Notes\n")
    p("- Each tutor rated only their own teams, so there is no tutor-tutor overlap and no "
      "human agreement ceiling.")
    p("- Tutors are not ground truth; agreement here means a second reader saw the same thing.")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tutor_study_results.md").write_text("\n".join(out) + "\n")
    (args.out / "tutor_study_results.json").write_text(json.dumps(res, indent=2, default=str))
    print("\n".join(out))


if __name__ == "__main__":
    main()
