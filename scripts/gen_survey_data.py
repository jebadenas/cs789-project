"""Generate ANONYMISED real cases for the tutor questionnaire (survey app).

Unlike the dashboard (local, real names), the questionnaire is shown to external
tutors, so every case is fully blinded: members are 'Member A/B/…' and all real
names inside the journal text and quotes are replaced with the matching member
label (or '[teammate]') via src.qualitative.llm.anonymise.

Each case = one (team, sprint):
  - journals: every member's full journal for that sprint, anonymised;
  - snippets: the distinct flagged quotes (from the 3-run consensus), anonymised.

Output: survey/src/app/cases.data.json (gitignored — real journal content), and
splices survey/src/app/data.ts to import it. Case SELECTION for the actual study
is a design-time choice; this emits the whole eligible pool to curate from.

    python3 scripts/gen_survey_data.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.qualitative.llm import anonymise as an
from src.qualitative.llm import blobs, sprint_analysis as sa

COHORT = "2025_s1"
DATA = Path("survey/src/app/data.ts")
OUT = DATA.parent / "cases.data.json"

# flag -> the questionnaire's label id (matches LABEL_OPTIONS in data.ts)
EVID_ORDER = ["open_conflict", "communication_breakdown", "leadership_problem",
              "underperformance_unaddressed", "effort_imbalance", "member_under_contributed",
              "core_subgroup_carried", "singled_out_below", "singled_out_above",
              "mutual_support", "harmonious_balanced"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def member_journals(cohort: str, team_label: str, ji: int) -> list[dict]:
    """Every member's full journal for one sprint, anonymised, as {member, text}."""
    df = blobs._entries(cohort)
    rows = df[(df["team_label"] == team_label) & (df["journal_index"] == ji)]
    out = []
    for _, r in rows.sort_values("member_label").iterrows():
        text = (r["text"] or "").strip()
        if not text:
            continue
        out.append({"member": f"Member {r['member_label']}",
                    "text": an.anonymise(text, cohort, team_label)})
    return out


def case_snippets(cohort: str, team_label: str, ji: int, runs) -> list[dict]:
    """Distinct flagged quotes for one sprint, anonymised, as {id, text}."""
    marks, _ = sa.consensus(runs)
    nonempty = [r for r in runs if r.get("marks")]
    snippets, seen = [], []
    for f in EVID_ORDER:
        if not marks.get(f):
            continue
        raws = sorted({(r.get("quotes") or {}).get(f, "").strip()
                       for r in nonempty if r["marks"].get(f) and (r.get("quotes") or {}).get(f)},
                      key=len, reverse=True)
        for q in raws:
            nq = _norm(q)
            if not nq or any(nq in s for s in seen):
                continue
            seen.append(nq)
            snippets.append(an.anonymise(q, cohort, team_label))
    return [{"id": f"{team_label}-j{ji}-s{i}", "text": t} for i, t in enumerate(snippets, 1)]


def main() -> None:
    cells = sa.load_cells()
    by_team: dict[str, dict[int, list]] = {}
    for (c, t, ji), runs in cells.items():
        if c == COHORT:
            by_team.setdefault(t, {})[ji] = runs

    cases, leaks = [], 0
    for t in sorted(by_team):
        for ji in sorted(by_team[t]):
            journals = member_journals(COHORT, t, ji)
            if not journals:
                continue
            snippets = case_snippets(COHORT, t, ji, by_team[t][ji])
            case_id = f"{t}-j{ji}"
            cases.append({"id": case_id, "journals": journals, "snippets": snippets})
            # verification: nothing this team's roster leaks through
            blob = json.dumps(journals) + json.dumps(snippets)
            if an.leaked_names(blob, COHORT, t):
                leaks += 1
    print(f"anonymisation: {leaks} cases with a residual own-team name (target 0)")

    OUT.write_text(json.dumps(cases, indent=2, ensure_ascii=False))

    # splice data.ts: keep types + options + helpers, swap the CASES array for an import
    src = DATA.read_text()
    src = src.replace('import casesData from "./cases.data.json";\n\n', "")
    # idempotent: match either the literal array OR an already-spliced import line
    m = re.search(
        r"export const CASES: CaseData\[\] = (?:casesData as CaseData\[\];|\[.*?\n\];)\n",
        src, flags=re.DOTALL)
    if not m:
        raise SystemExit("could not find the CASES declaration to splice in data.ts")
    replacement = ('import casesData from "./cases.data.json";\n\n'
                   + src[: m.start()]
                   + "export const CASES: CaseData[] = casesData as CaseData[];\n"
                   + src[m.end():])
    DATA.write_text(replacement)
    n_snip = sum(len(c["snippets"]) for c in cases)
    print(f"wrote {OUT}: {len(cases)} cases, {n_snip} snippets; spliced {DATA}")


if __name__ == "__main__":
    main()
