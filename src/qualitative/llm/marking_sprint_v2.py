"""Per-sprint coding v2 — EVIDENCE-GROUNDED (early-warning / dashboard study).

Same 11 binary items as ``marking_sprint`` (kept in lockstep with the v1
instrument), but redesigned to fix the validity problems found on the v1 marks:

  1. A flag is present ONLY if the model can supply a verbatim quote that DIRECTLY
     supports it. No supporting quote -> the feature is NOT present. This attacks
     the over-firing where a flag fired but the "evidence" contradicted it.
  2. Each flag returns a LIST of supporting quotes (up to 3), each TAGGED with the
     Member it came from (the blinded Member label in the blob) — native support
     for the dashboard's multi-quote, author-attributed evidence.
  3. Tightened definitions for the items the model misread on v1 — notably
     core_subgroup_carried (a mere even frontend/backend split is NOT it).

Run 3x per (team, sprint) with shuffled member labels, as v1 does, so per-sprint
reliability AND validity can be compared against the v1 marks (different output
dir: marks_sprint_v2/).

Output: output/qualitative/llm/marks_sprint_v2/{cohort}_{team}_j{ji}_r{run}.json
"""

from __future__ import annotations

import json

from . import blobs
from .marking import BINARY as ITEMS   # the exact 11 v1 binaries — kept in lockstep
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/marks_sprint_v2"

SYSTEM = (
    "You code ONE sprint of a student team's reflective journals against a fixed "
    "checklist of team-dynamics features, for a course coordinator. Judge only THIS "
    "sprint. A feature is PRESENT only if the journals contain a verbatim quote that "
    "DIRECTLY supports it — if you cannot find such a quote, the feature is NOT present. "
    "Never infer beyond the text, and never mark a feature present on the strength of a "
    "quote that does not actually support it. Output ONLY the requested JSON object."
)

PROMPT = """The journals below are from ONE sprint of a student team, labelled by blinded
Member letter (A, B, ...). Code the checklist for THIS sprint only.

RULES:
- Mark a feature present ONLY if you can quote text that DIRECTLY supports it.
- If the supporting evidence is thin, absent, or only tangential, mark it not-present.
- A positive or neutral quote must NOT be used to support a concern feature.
- Every quote MUST be copied WORD-FOR-WORD from the journals — exact characters, no
  paraphrasing, summarising, correcting, shortening, or joining separate sentences.
  If you cannot copy an exact supporting sentence, the feature is NOT present.
- For each quote, "member" is the letter of the Member whose journal you copied it from
  (the "Member X" heading above that text). It must be one of the letters shown below.

Items:
- effort_imbalance: workload clearly uneven in AMOUNT this sprint (one/two did much more).
  A general "we get along / happy team" statement is NOT evidence of imbalance.
- member_under_contributed: >=1 member did not pull their weight / disengaged this sprint.
- underperformance_unaddressed: an under-contributing member was worked AROUND rather than
  raised with them (about contribution, not conflict; can be true with no open friction).
- core_subgroup_carried: a SMALL core (2-3) did the substantive work while OTHERS were
  peripheral or under-contributed. A simple EVEN split into frontend/backend sub-teams,
  or normal task division, is NOT this — it requires a real imbalance where a few carry.
- singled_out_below: a SINGLE identifiable member is picked out as THE weakest this sprint.
- singled_out_above: a SINGLE identifiable member is picked out as THE carrier/star.
- open_conflict: explicit friction, arguments or interpersonal tension BEYOND ordinary
  task/technical disagreement this sprint.
- communication_breakdown: sustained poor communication this sprint (not a one-off, and
  not merely a technical/design problem).
- harmonious_balanced: the team worked well together this sprint — effort fair, no
  significant conflict or imbalance.
- leadership_problem: a designated leader ineffective/bypassed, or a leadership/
  coordination vacuum this sprint.
- mutual_support: members supported each other through difficulty this sprint.

Return ONLY a JSON object with exactly these 11 keys. Each value is an object:
  {{"value": <boolean>,
    "quotes": [{{"member": "<letter>", "quote": "<exact word-for-word quote copied from that member's journal>"}}]}}
Give 1-3 quotes when present; give an EMPTY list when not present (and then value MUST be false).

TEAM JOURNALS (one sprint):
{blob}"""


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "y", "1", "present")


def _parse(raw: str) -> tuple[dict, dict]:
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    marks, quotes = {}, {}
    for k in ITEMS:
        v = data.get(k)
        if isinstance(v, dict):
            val = _to_bool(v.get("value"))
            qs = v.get("quotes") or []
            clean = []
            for q in qs if isinstance(qs, list) else []:
                if isinstance(q, dict) and (q.get("quote") or "").strip():
                    clean.append({"member": str(q.get("member", "")).strip(),
                                  "quote": q["quote"].strip()})
                elif isinstance(q, str) and q.strip():
                    clean.append({"member": "", "quote": q.strip()})
        else:
            val, clean = _to_bool(v), []
        # evidence-grounding: no supporting quote => not present
        marks[k] = bool(val and clean)
        quotes[k] = clean
    return marks, quotes


def run_team_sprint(cohort: str, team_label: str, journal_index: int, run_idx: int, *,
                    model: str | None = None, force: bool = False) -> dict:
    """Code one (team, sprint) for one shuffled run (``run_idx`` seeds the shuffle)."""
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{cohort}_{team_label}_j{journal_index}_r{run_idx}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    blob = blobs.build_blob(cohort, team_label, seed=run_idx, journal_indices={journal_index})
    if not blob.strip():  # a team may not have submitted this sprint's journal
        rec = {"cohort": cohort, "team_label": team_label, "journal_index": journal_index,
               "run": run_idx, "marks": None, "quotes": None, "empty": True}
        out.write_text(json.dumps(rec, indent=2))
        return rec
    raw = call_model(PROMPT.format(blob=blob), system=SYSTEM, temperature=0.2,
                     max_tokens=2200, model=model, response_format={"type": "json_object"})
    marks, quotes = _parse(raw)
    rec = {"cohort": cohort, "team_label": team_label, "journal_index": journal_index,
           "run": run_idx, "marks": marks, "quotes": quotes}
    out.write_text(json.dumps(rec, indent=2))
    return rec


def sprint_indices(cohort: str) -> list[int]:
    """Work-sprint journal indices for a cohort = all journals except 1 (the intro)."""
    idx = sorted(int(i) for i in blobs._entries(cohort)["journal_index"].unique())
    return [i for i in idx if i != 1]
