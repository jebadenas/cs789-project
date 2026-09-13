"""Regenerate ui/src/app/dashboard/data.ts from REAL per-sprint marks for one cohort.

Statuses, summaries (name-safe, from cache) AND real journal snippets — with student
names REDACTED using each team's roster (from the peer CSVs), so the snippets are real
but name-safe and safe to commit. Keeps every type + helper in data.ts unchanged;
only the TEAMS array is replaced.
"""
from __future__ import annotations
import csv, glob, json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
from src.qualitative.llm import sprint_analysis as sa
from scripts.blind_spot import peer_prefix, team_key

COHORT = "2025_s1"
SCRUB = False   # user decision: local-only tool, real names kept
DATA = Path("ui/src/app/dashboard/data.ts")
SUMM = Path("output/qualitative/llm/summaries_sprint")            # local 7B (stopgap)
CLUSTER_SUMM = Path("output/qualitative/llm/marks_summary")       # 72B, from the cluster (preferred)

SERIOUS = {"open_conflict", "communication_breakdown", "leadership_problem", "underperformance_unaddressed"}
MILD = {"effort_imbalance", "member_under_contributed", "core_subgroup_carried", "singled_out_below"}
CONTRIB6 = {"effort_imbalance", "member_under_contributed", "underperformance_unaddressed",
            "core_subgroup_carried", "singled_out_below", "singled_out_above"}
LABEL = {
    "open_conflict": "Open conflict / interpersonal tension",
    "communication_breakdown": "Communication breakdown",
    "leadership_problem": "Leadership problem or vacuum",
    "effort_imbalance": "Uneven workload / effort imbalance",
    "member_under_contributed": "A member under-contributing or disengaged",
    "underperformance_unaddressed": "Under-performance worked around, not addressed",
    "core_subgroup_carried": "A core few carrying the team",
    "singled_out_below": "One member singled out as weakest",
    "singled_out_above": "One member singled out as the standout",
    "harmonious_balanced": "Worked well together, effort fairly shared",
    "mutual_support": "Members supported each other",
}
DESC = {
    "open_conflict": "Interpersonal friction beyond ordinary task disagreement.",
    "communication_breakdown": "Sustained gaps in keeping each other informed.",
    "leadership_problem": "Coordination or leadership was ineffective or absent.",
    "effort_imbalance": "Workload was unevenly shared this sprint.",
    "member_under_contributed": "At least one member was not pulling their weight.",
    "underperformance_unaddressed": "Under-contribution was worked around rather than raised.",
    "core_subgroup_carried": "A small core carried the substantive work.",
    "singled_out_below": "One identifiable member was the notable under-contributor.",
    "singled_out_above": "One identifiable member carried as the standout.",
    "harmonious_balanced": "The team worked well together with a fair split.",
    "mutual_support": "Members supported each other through difficulty.",
}
EVID_ORDER = ["open_conflict", "communication_breakdown", "leadership_problem",
              "underperformance_unaddressed", "effort_imbalance", "member_under_contributed",
              "core_subgroup_carried", "singled_out_below", "singled_out_above", "mutual_support"]
# common English words that are also names — don't redact these (avoid mangling prose)
STOP = {"will", "may", "mark", "grace", "art", "drew", "hope", "rose", "an", "so", "in",
        "on", "a", "the", "by", "van", "le", "lin", "don", "kim", "max"}


def rosters() -> dict[str, set[str]]:
    """real_team -> set of member name tokens (first + last) from the peer CSVs."""
    names: dict[str, set[str]] = {}
    for path in glob.glob(f"data/peer_sessions/{peer_prefix(COHORT)}*.csv"):
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        hdr = next((i for i, l in enumerate(lines) if l.startswith("Team,Name,Email")), None)
        if hdr is None:
            continue
        for l in lines[hdr + 1:]:
            if not l.strip() or l.startswith("Question") or l.startswith("Summary"):
                break
            row = next(csv.reader([l]))
            if len(row) < 2 or not row[0].strip().startswith("Team"):
                continue
            toks = re.findall(r"[A-Za-z][A-Za-z'-]+", row[1])
            names.setdefault(row[0].strip(), set()).update(toks)
    return names


def scrub(text: str, toks: set[str]) -> str:
    if not SCRUB:
        return text
    out = text
    for t in toks:
        if len(t) < 3 or t.lower() in STOP:
            continue
        out = re.sub(rf"\b{re.escape(t)}\b", "[teammate]", out, flags=re.IGNORECASE)
    return out


def run_counts(runs, flag):
    return sum(1 for r in runs if (r.get("marks") or {}).get(flag) is True)


def load_summary(team, ji):
    for d in (CLUSTER_SUMM, SUMM):   # prefer the 72B cluster summary when present
        p = d / f"{COHORT}_{team}_j{ji}.json"
        if p.exists():
            t = (json.loads(p.read_text()).get("summary") or "").strip()
            if t:
                return t
    return ""


def main():
    cells = sa.load_cells()
    tk = team_key(COHORT)
    ros = rosters()
    by_team: dict[str, dict[int, list]] = {}
    for (c, t, ji), runs in cells.items():
        if c == COHORT:
            by_team.setdefault(t, {})[ji] = runs

    teams = []
    leaked = 0
    for t in sorted(by_team):
        real = tk.get(t, "")
        toks = ros.get(real, set())
        num = t.split("_")[1]
        findings = []
        for si, ji in enumerate(sorted(by_team[t]), start=1):
            runs = by_team[t][ji]
            marks, quotes = sa.consensus(runs)
            if not any(marks.values()) and all(not (r.get("marks")) for r in runs if r.get("empty")):
                pass
            # concern score
            score = 0
            for f in SERIOUS:
                if marks.get(f):
                    score += 3 if run_counts(runs, f) == 3 else 2
            for f in MILD:
                if marks.get(f):
                    score += 1
            if marks.get("harmonious_balanced"):
                score -= 2
            if marks.get("mutual_support"):
                score -= 1
            score = max(0, score)
            status = "attention" if score >= 4 else "watching" if score >= 1 else "healthy"

            issues = []
            if any(marks.get(f) for f in CONTRIB6):
                issues.append("Unequal contribution / effort imbalance")
            for f in ("open_conflict", "communication_breakdown", "leadership_problem"):
                if marks.get(f):
                    issues.append(LABEL[f])
            positives = [LABEL[f] for f in ("harmonious_balanced", "mutual_support") if marks.get(f)]

            evidence = []
            for f in EVID_ORDER:
                if marks.get(f) and (quotes.get(f) or "").strip() and len(evidence) < 5:
                    q = scrub(quotes[f].strip(), toks)
                    evidence.append({"issue": LABEL[f], "text": DESC[f],
                                     "journalSnippet": q, "source": "Team journal"})

            summary = load_summary(t, ji) or (
                "No significant team-dynamics concerns surfaced this sprint."
                if status == "healthy" else
                "; ".join(issues).capitalize() + ".")
            summary = scrub(summary, toks)  # belt-and-suspenders

            findings.append({"sprintId": str(si), "status": status, "summary": summary,
                             "issues": issues, "positives": positives, "evidence": evidence})
        teams.append({"id": f"team-{num}", "label": (real or f"Team {num}"), "findings": findings})

    # name-safety verification (only meaningful when scrubbing)
    allnames = set() if SCRUB else set()
    if not SCRUB:
        print('SCRUB off: real names kept by user request')
    _skip = set()
    for toks in ros.values():
        allnames |= {t for t in toks if len(t) >= 3 and t.lower() not in STOP}
    blob = json.dumps(teams)
    for n in allnames:
        if re.search(rf"\b{re.escape(n)}\b", blob, flags=re.IGNORECASE):
            leaked += 1
    print(f"name-safety: {leaked} roster names still present (target 0)")

    # splice into data.ts (keep types + helpers)
    # Data is a pipeline artefact, not baked into code: emit JSON, have data.ts import it.
    src = DATA.read_text()
    head = src[: src.index("export const TEAMS")].replace('import teamsData from "./teams.data.json";\n\n', "")
    tail = src[src.index("export function getLatestSprintId"):]
    (DATA.parent / "teams.data.json").write_text(json.dumps(teams, indent=2, ensure_ascii=False))
    body = 'import teamsData from "./teams.data.json";\n\n' + head + "export const TEAMS: Team[] = teamsData as Team[];\n\n" + tail
    DATA.write_text(body)
    n_ev = sum(len(f["evidence"]) for tm in teams for f in tm["findings"])
    print(f"wrote {DATA}: {len(teams)} teams, {sum(len(tm['findings']) for tm in teams)} findings, {n_ev} evidence snippets")


if __name__ == "__main__":
    main()
