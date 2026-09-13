"""Prototype: a coordinator-facing team-health dashboard built from the LLM marks.

For each team, aggregate the 3 shuffled runs (majority vote per flag), compose a
health status + a plain-language summary from the RELIABLE flags, and show every
fired flag with its verbatim journal quote. Output a single self-contained local
HTML file.

PRIVACY: the quotes contain real student names, so the output is written locally and
git-ignored — it must NOT be published or committed without name-scrubbing.

    python3 scripts/build_dashboard.py   ->  prototypes/team_health_dashboard.html
"""

from __future__ import annotations

import collections
import glob
import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKS = REPO / "output/qualitative/llm/marks"
SUMM = REPO / "output/qualitative/llm/summaries"   # LLM-written per-team summaries (cached)
OUT = REPO / "prototypes/team_health_dashboard.html"

# Flags grouped by how they drive the health status. Only the reliable binaries.
SERIOUS = {  # any of these -> At-risk
    "open_conflict": "Open conflict / interpersonal tension",
    "communication_breakdown": "Communication breakdown",
    "leadership_problem": "Leadership problem / vacuum",
    "underperformance_unaddressed": "Under-performance worked around, not addressed",
}
MILD = {  # any of these (and no serious) -> Watch
    "effort_imbalance": "Uneven workload",
    "member_under_contributed": "A member under-contributing",
    "core_subgroup_carried": "Carried by a 2–3 person core",
    "singled_out_below": "One member singled out as weakest",
}
POSITIVE = {
    "harmonious_balanced": "Worked well together, effort fairly shared",
    "mutual_support": "Members supported each other through difficulty",
}

# At-risk = the worst TOP_FRACTION of EACH cohort by concern score (relative, so it
# adapts to how verbose a cohort's journals are), but only teams above MIN_ATRISK so a
# genuinely healthy cohort isn't forced to flag anyone. Tune both here.
TOP_FRACTION = 0.15
MIN_ATRISK = 3


def _majority_bool(vals: list) -> bool:
    return sum(1 for v in vals if v is True) >= (len(vals) / 2)


def _majority_cat(vals: list):
    vals = [v for v in vals if v]
    return collections.Counter(vals).most_common(1)[0][0] if vals else None


def _rep_quote(runs: list[dict], flag: str) -> str:  # representative quote
    for r in runs:
        if r["marks"].get(flag) is True:
            q = (r.get("reasons", {}).get(flag) or "").strip()
            if q:
                return q
    return ""


def load_teams() -> list[dict]:
    by_team: dict[tuple, list[dict]] = {}
    for f in glob.glob(str(MARKS / "*.json")):
        d = json.loads(Path(f).read_text())
        by_team.setdefault((d["cohort"], d["team_label"]), []).append(d)

    # best-effort cascade state (the "peer view") for the blind-spot comparison
    peer_state = {}
    try:
        import sys
        sys.path.insert(0, str(REPO))
        from src.qualitative.llm import blobs
        meta = blobs.load_team_meta()
        for (c, t), row in meta.iterrows():
            peer_state[(c, t)] = str(row.get("pooled_state", ""))
    except Exception:
        pass

    cards = []
    for (cohort, team), runs in sorted(by_team.items()):
        def tcount(flag):  # how many of the 3 runs fired this flag
            return sum(1 for r in runs if r["marks"].get(flag) is True)

        fired_serious, fired_mild, positives, fired = [], [], [], set()
        score = 0
        for flag, label in SERIOUS.items():
            tc = tcount(flag)
            if tc >= 2:  # majority
                fired_serious.append((label, _rep_quote(runs, flag)))
                fired.add(flag)
                score += 3 if tc == 3 else 2   # unanimous flag counts for more
        for flag, label in MILD.items():
            if tcount(flag) >= 2:
                fired_mild.append((label, _rep_quote(runs, flag)))
                fired.add(flag)
                score += 1
        if tcount("harmonious_balanced") >= 2:
            positives.append(POSITIVE["harmonious_balanced"]); fired.add("harmonious_balanced"); score -= 2
        if tcount("mutual_support") >= 2:
            positives.append(POSITIVE["mutual_support"]); fired.add("mutual_support"); score -= 1
        ch = _majority_cat([r["marks"].get("conflict_handling") for r in runs])
        if ch == "festered":
            score += 2   # confirmed-bad conflict outweighs a one-off
            if not any("conflict" in l.lower() for l, _ in fired_serious):
                fired_serious.append(("Conflict left unresolved (festered)", _rep_quote(runs, "open_conflict")))

        score = max(0, score)
        cards.append({
            "cohort": cohort, "team": team, "status": "healthy", "score": score,
            "peer": peer_state.get((cohort, team), ""),
            "serious": fired_serious, "mild": fired_mild, "positives": positives,
            "summary": _load_summary(cohort, team),  # LLM-written, from cache
        })

    # per-cohort relative cut: At-risk = worst TOP_FRACTION of each cohort (above the floor)
    by_c: dict[str, list[dict]] = {}
    for c in cards:
        by_c.setdefault(c["cohort"], []).append(c)
    for ccards in by_c.values():
        ccards.sort(key=lambda c: -c["score"])
        n_at = round(TOP_FRACTION * len(ccards))
        for i, c in enumerate(ccards):
            if i < n_at and c["score"] >= MIN_ATRISK:
                c["status"] = "at-risk"
            else:
                c["status"] = "watch" if c["score"] > 0 else "healthy"

    cards.sort(key=lambda c: -c["score"])  # most troubled first
    return cards


# ---- LLM-written summaries (grounded in each team's own findings) ----------

SUMM_SYSTEM = (
    "You write a brief, factual summary of a student team's dynamic for a course "
    "coordinator, based ONLY on the coded findings you are given. Do not invent "
    "anything that is not in the findings. "
    "NEVER use individual people's names: refer to people generically as 'a member', "
    "'one member', 'a couple of members', or 'the team'. If the findings contain names, "
    "replace them with these generic references. "
    "Write 2–3 plain, readable sentences — no preamble, no bullet points, just the summary."
)


def _findings_text(card: dict) -> str:
    # Labels only — deliberately NOT the quotes. The quotes contain real student names;
    # if we fed them to the summariser the names leak into the prose (they did). The
    # flag labels are name-free, so a summary written from them is anonymous by
    # construction. The verbatim quotes still appear separately on the card as evidence.
    lines = [f"- {label}" for label, _q in card["serious"] + card["mild"]]
    for p in card["positives"]:
        lines.append(f"- positive signal: {p}")
    return "\n".join(lines)


def _summ_path(cohort: str, team: str) -> Path:
    return SUMM / f"{cohort}_{team}.json"


def _load_summary(cohort: str, team: str) -> str:
    p = _summ_path(cohort, team)
    if p.exists():
        return json.loads(p.read_text()).get("summary", "")
    return ""


def generate_summaries(cards: list[dict], model: str, force: bool = False) -> None:
    """Have the LLM write each team's summary from its own findings. Cached + resumable."""
    import sys
    sys.path.insert(0, str(REPO))
    from src.qualitative.llm.model import call_model

    SUMM.mkdir(parents=True, exist_ok=True)
    total = len(cards)
    for i, c in enumerate(cards, 1):
        p = _summ_path(c["cohort"], c["team"])
        if p.exists() and not force:
            c["summary"] = json.loads(p.read_text()).get("summary", "")
            print(f"  [{i}/{total}] {c['cohort']} {c['team']} (cached)", flush=True)
            continue
        findings = _findings_text(c)
        if not findings:
            prompt = ("This team's journals were coded and NO team-dynamics issues were "
                      "detected. In 1–2 sentences, say the team appears to be functioning "
                      "well, without inventing specifics.")
        else:
            prompt = (f"Coded findings for one student team:\n{findings}\n\n"
                      "Write a 2–3 sentence summary of this team's dynamic, based only on "
                      "these findings.")
        try:
            text = call_model(prompt, system=SUMM_SYSTEM, temperature=0.3,
                              max_tokens=220, model=model).strip()
        except Exception as e:
            text = ""
            print(f"  [{i}/{total}] {c['cohort']} {c['team']} FAILED: {type(e).__name__}", flush=True)
        if text:
            p.write_text(json.dumps({"cohort": c["cohort"], "team": c["team"],
                                     "model": model, "summary": text}, indent=2))
            c["summary"] = text
            print(f"  [{i}/{total}] {c['cohort']} {c['team']} ✓", flush=True)


def render(cards: list[dict], title: str, nav: str = "") -> str:
    n = collections.Counter(c["status"] for c in cards)
    esc = html.escape
    card_html = []
    for c in cards:
        flags = ""
        for label, quote in c["serious"] + c["mild"]:
            q = f'<blockquote>“{esc(quote)}”</blockquote>' if quote else ""
            sev = "s" if (label, quote) in c["serious"] else "m"
            flags += f'<div class="flag {sev}"><span class="fl">{esc(label)}</span>{q}</div>'
        pos = ""
        if c["positives"]:
            pos = '<div class="pos">✓ ' + " · ".join(esc(p) for p in c["positives"]) + "</div>"
        peer = f'<span class="peer">peer view: {esc(c["peer"])}</span>' if c["peer"] else ""
        card_html.append(f'''<article class="card {c['status']}" data-status="{c['status']}">
  <header><span class="team">{esc(c['team'].replace('_',' '))}</span>
    <span class="cohort">{esc(c['cohort'])}</span>
    <span class="conc" title="concern score">{c['score']}</span>
    <span class="badge {c['status']}">{c['status'].replace('-',' ')}</span></header>
  {peer}
  <p class="summary">{esc(c['summary'])}</p>
  {flags}{pos}
</article>''')

    return f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root {{ --bg:#f7f7f5; --card:#fff; --line:#e5e5e0; --tx:#222; --mut:#777;
  --risk:#c0392b; --watch:#c78400; --ok:#2e7d46; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:14px/1.5 -apple-system,system-ui,sans-serif; background:var(--bg); color:var(--tx); }}
header.top {{ padding:20px 24px; border-bottom:1px solid var(--line); background:var(--card); position:sticky; top:0; z-index:5; }}
h1 {{ margin:0 0 4px; font-size:19px; }}
.sub {{ color:var(--mut); font-size:13px; }}
.nav {{ margin-bottom:6px; }}
.nav a {{ color:var(--mut); text-decoration:none; font-size:13px; }}
.nav a:hover {{ text-decoration:underline; }}
.controls {{ margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; }}
.controls button {{ border:1px solid var(--line); background:#fff; padding:6px 12px; border-radius:20px; cursor:pointer; font-size:13px; }}
.controls button.on {{ background:var(--tx); color:#fff; border-color:var(--tx); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; padding:20px 24px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--line); border-radius:10px; padding:14px 16px; }}
.card.at-risk {{ border-left-color:var(--risk); }}
.card.watch {{ border-left-color:var(--watch); }}
.card.healthy {{ border-left-color:var(--ok); }}
.card header {{ display:flex; align-items:center; gap:8px; }}
.team {{ font-weight:650; font-size:15px; }}
.cohort {{ color:var(--mut); font-size:12px; }}
.conc {{ margin-left:auto; font-size:12px; font-weight:700; color:var(--mut); background:#f0f0ee; min-width:22px; text-align:center; padding:2px 7px; border-radius:6px; }}
.badge {{ font-size:11px; text-transform:uppercase; letter-spacing:.04em; padding:3px 9px; border-radius:20px; color:#fff; }}
.badge.at-risk {{ background:var(--risk); }} .badge.watch {{ background:var(--watch); }} .badge.healthy {{ background:var(--ok); }}
.peer {{ display:inline-block; margin:6px 0 2px; font-size:11px; color:var(--mut); background:#f0f0ee; padding:2px 8px; border-radius:4px; }}
.summary {{ margin:8px 0 10px; }}
.flag {{ margin:8px 0; }}
.flag .fl {{ font-weight:600; font-size:13px; }}
.flag.s .fl::before {{ content:"● "; color:var(--risk); }}
.flag.m .fl::before {{ content:"● "; color:var(--watch); }}
blockquote {{ margin:4px 0 0; padding:6px 10px; border-left:2px solid var(--line); background:#faf9f7; color:#444; font-size:13px; font-style:italic; border-radius:0 4px 4px 0; }}
.pos {{ margin-top:8px; color:var(--ok); font-size:13px; }}
</style></head><body>
<header class="top">
  {nav}
  <h1>{esc(title)} <span class="sub">— prototype, from journal marks</span></h1>
  <div class="sub">{len(cards)} teams · {n['at-risk']} at-risk · {n['watch']} watch · {n['healthy']} healthy.
     Every flag is grounded in a verbatim journal quote. Auto-summary composed from the reliable flags.</div>
  <div class="controls">
    <button class="on" data-f="all">All ({len(cards)})</button>
    <button data-f="at-risk">At-risk ({n['at-risk']})</button>
    <button data-f="watch">Watch ({n['watch']})</button>
    <button data-f="healthy">Healthy ({n['healthy']})</button>
  </div>
</header>
<div class="grid" id="grid">
{chr(10).join(card_html)}
</div>
<script>
const btns=document.querySelectorAll('.controls button'), cards=document.querySelectorAll('.card');
btns.forEach(b=>b.onclick=()=>{{
  btns.forEach(x=>x.classList.remove('on')); b.classList.add('on');
  const f=b.dataset.f;
  cards.forEach(c=>c.hidden = !(f==='all'||c.dataset.status===f));
}});
</script></body></html>'''


def _index_page(by_cohort: dict) -> str:
    rows = []
    for cohort in sorted(by_cohort):
        cards = by_cohort[cohort]
        n = collections.Counter(c["status"] for c in cards)
        rows.append(f'''<a class="crow" href="dashboard_{cohort}.html">
  <span class="cname">{cohort}</span>
  <span class="cn">{len(cards)} teams</span>
  <span class="pill at-risk">{n['at-risk']} at-risk</span>
  <span class="pill watch">{n['watch']} watch</span>
  <span class="pill healthy">{n['healthy']} healthy</span></a>''')
    return f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Team Health Dashboard — cohorts</title>
<style>
body {{ margin:0; font:14px/1.5 -apple-system,system-ui,sans-serif; background:#f7f7f5; color:#222; }}
.wrap {{ max-width:640px; margin:0 auto; padding:32px 20px; }}
h1 {{ font-size:20px; margin:0 0 4px; }} .sub {{ color:#777; margin-bottom:20px; }}
.crow {{ display:flex; align-items:center; gap:10px; background:#fff; border:1px solid #e5e5e0;
  border-radius:10px; padding:14px 16px; margin-bottom:10px; text-decoration:none; color:#222; }}
.crow:hover {{ border-color:#bbb; }}
.cname {{ font-weight:650; font-size:16px; }} .cn {{ color:#777; margin-right:auto; }}
.pill {{ font-size:12px; padding:2px 9px; border-radius:20px; color:#fff; }}
.pill.at-risk {{ background:#c0392b; }} .pill.watch {{ background:#c78400; }} .pill.healthy {{ background:#2e7d46; }}
</style></head><body><div class="wrap">
<h1>Team Health Dashboard</h1>
<div class="sub">Prototype · per-cohort views · every flag grounded in a verbatim journal quote.</div>
{chr(10).join(rows)}
</div></body></html>'''


def main():
    import sys
    argv = sys.argv[1:]
    summarize = "--summarize" in argv
    force = "--force" in argv
    model = next((a.split("=", 1)[1] for a in argv if a.startswith("--model=")), "qwen2.5:7b")

    cards = load_teams()
    if summarize:
        print(f"generating LLM summaries ({model}) for {len(cards)} teams…", flush=True)
        generate_summaries(cards, model, force=force)

    missing = sum(1 for c in cards if not c["summary"])
    if missing:
        print(f"note: {missing} teams have no summary yet — run with --summarize", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    by_cohort: dict[str, list[dict]] = {}
    for c in cards:
        by_cohort.setdefault(c["cohort"], []).append(c)

    index = OUT.parent / "dashboard_index.html"
    index.write_text(_index_page(by_cohort))
    for cohort, ccards in by_cohort.items():
        nav = '<div class="nav"><a href="dashboard_index.html">← all cohorts</a></div>'
        (OUT.parent / f"dashboard_{cohort}.html").write_text(
            render(ccards, f"{cohort} — Team Health", nav))

    n = collections.Counter(c["status"] for c in cards)
    print(f"wrote {index} + {len(by_cohort)} cohort pages")
    for cohort in sorted(by_cohort):
        cn = collections.Counter(c["status"] for c in by_cohort[cohort])
        print(f"  {cohort}: {len(by_cohort[cohort])} teams — {cn['at-risk']} at-risk, {cn['watch']} watch, {cn['healthy']} healthy")


if __name__ == "__main__":
    main()
