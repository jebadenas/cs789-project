"""Regenerate ui/src/app/dashboard/data.ts from REAL per-sprint marks for one cohort.

Statuses, summaries (name-safe, from cache) AND real journal snippets — with student
names REDACTED using each team's roster (from the peer CSVs), so the snippets are real
but name-safe and safe to commit. Keeps every type + helper in data.ts unchanged;
only the TEAMS array is replaced.
"""
from __future__ import annotations
import csv, functools, glob, json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
from src.qualitative.llm import sprint_analysis as sa
from src.qualitative.llm import blobs
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
              "core_subgroup_carried", "singled_out_below", "singled_out_above",
              "mutual_support", "harmonious_balanced"]
POSITIVE = {"mutual_support", "harmonious_balanced"}
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


# --- (#1) resegment glued text ------------------------------------------------
# A minority of journals (~3.6% of 2025_s1 entries) were extracted with spaces
# lost inside a passage ("Forexample,myPRfor..."). The model quoted that broken
# text faithfully. Re-insert spaces for DISPLAY using a wordlist + DP (favour
# long dictionary words). The proper fix is repairing the source before the
# re-run; this just keeps the dashboard readable meanwhile.
@functools.lru_cache(maxsize=1)
def _wordset() -> set[str]:
    ws: set[str] = set()
    for p in ("/usr/share/dict/words", "/usr/dict/words"):
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                ws = {w.strip().lower() for w in fh if w.strip()}
            break
        except OSError:
            continue
    ws |= {"a", "i"}  # single-letter words the list may omit
    return ws


def _split_glued(token: str) -> str:
    """Split one alphabetic glued run into space-separated dictionary words."""
    words = _wordset()
    low = token.lower()
    n = len(low)
    NEG = float("-inf")
    best = [0.0] + [NEG] * n          # best[i] = score of low[:i]
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - 18), i):
            seg = low[j:i]
            score = len(seg) ** 2 if seg in words else -len(seg)  # reward long real words
            if best[j] + score > best[i]:
                best[i] = best[j] + score
                back[i] = j
    # reconstruct, preserving the ORIGINAL casing
    pieces, i = [], n
    while i > 0:
        j = back[i]
        pieces.append(token[j:i])
        i = j
    return " ".join(reversed(pieces))


def resegment(text: str) -> str:
    if not text:
        return text
    def fix(m: "re.Match[str]") -> str:
        run = m.group(0)
        # only touch long runs that aren't already a real word
        if len(run) < 18 or run.lower() in _wordset():
            return run
        return _split_glued(run)
    return re.sub(r"[A-Za-z]{18,}", fix, text)


# --- (#5) recover which member a quote came from ------------------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def member_text_index(cohort: str):
    """(team_label, journal_index) -> {member_label: normalised journal text}."""
    df = blobs._entries(cohort)
    idx: dict[tuple[str, int], dict[str, str]] = {}
    for _, r in df.iterrows():
        idx.setdefault((r["team_label"], int(r["journal_index"])), {})[r["member_label"]] = _norm(r["text"])
    return idx


def quote_author(quote: str, per_member: dict[str, str]) -> str:
    """Match a quote back to the member whose journal contains it (blinded label)."""
    nq = _norm(quote)[:60]
    if not nq:
        return ""
    owners = [m for m, t in per_member.items() if nq in t]
    return f"Member {owners[0]}" if len(owners) == 1 else ""


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
    mtext = member_text_index(COHORT)   # (team, sprint) -> {member: journal text} for attribution
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

            per_member = mtext.get((t, ji), {})
            nonempty = [r for r in runs if r.get("marks")]
            evidence = []
            for f in EVID_ORDER:
                if not marks.get(f) or len(evidence) >= 6:
                    continue
                # (#6) gather DISTINCT quotes the fired runs gave for this flag.
                # Runs often return overlapping quotes; collapse by substring so we
                # don't show the same sentence twice — keep the longest variant.
                raws: list[str] = []
                for r in nonempty:
                    if not r["marks"].get(f):
                        continue
                    q = ((r.get("quotes") or {}).get(f) or "").strip()
                    if q:
                        raws.append(q)
                kept: list[str] = []
                for q in sorted(set(raws), key=len, reverse=True):  # longest first
                    nq = _norm(q)
                    if any(nq in _norm(k) for k in kept):           # already covered
                        continue
                    kept.append(q)
                qlist = []
                for q in kept:
                    q = resegment(scrub(q, toks))                    # (#1) fix glued text, (name-safe)
                    author = quote_author(q, per_member)             # (#5) whose journal it's from
                    qlist.append({"text": q, "author": author} if author else {"text": q})
                if not qlist:
                    continue
                evidence.append({"issue": LABEL[f], "text": DESC[f],
                                 "positive": f in POSITIVE,
                                 "quotes": qlist[:3],          # cap snippets per flag
                                 "journalSnippet": qlist[0]["text"],  # back-compat
                                 "source": "Team journal"})

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
