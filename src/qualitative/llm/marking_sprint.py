"""Per-sprint coding of the v1 binary checklist (early-warning / dashboard study).

The SAME 11 binary items as the whole-project v1 instrument (``marking.BINARY``), scoped
to a SINGLE sprint's journals — so the per-sprint and whole-project runs are the **same
instrument** and stay comparable (you can even check per-sprint flags aggregate up to the
whole-project flag). The 2 categoricals (conflict_handling, trajectory) are dropped:
unreliable, and per-sprint *change* is meant to come from the SEQUENCE of these binaries,
not a one-shot categorical.

Run **3x per (team, sprint)** with shuffled member labels (as whole-project marking does)
so we can measure per-sprint reliability and only USE the reliable flags downstream. Each
flag carries a verbatim quote (the evidence / "comment").

NB the per-sprint **summary** is NOT produced here: it's generated downstream from the
flag *labels* (never the raw journal) so no student names leak — see
``build_dashboard.generate_summaries``.

Output: output/qualitative/llm/marks_sprint/{cohort}_{team}_j{ji}_r{run}.json (resumable).
"""

from __future__ import annotations

import json

from . import blobs
from .marking import BINARY as ITEMS   # the exact 11 v1 binaries — kept in lockstep
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/marks_sprint"

SYSTEM = (
    "You code ONE sprint of a student team's reflective journals against a fixed checklist "
    "of team-dynamics features. Judge only THIS sprint, strictly from the evidence — mark "
    "a feature present ONLY if the journals support it; if evidence is thin or absent, mark "
    "it not-present, never infer. Every feature marked true carries a verbatim quote from "
    "the journals. Output ONLY the requested JSON object."
)

PROMPT = """The journals below are from ONE sprint of a student team's project. Code the
checklist for THIS sprint only. Mark true ONLY if the journals support it; otherwise false.

Items (true/false), each with a short VERBATIM quote from the journals as evidence:
- effort_imbalance: workload clearly uneven in AMOUNT this sprint (one or two did much more).
- member_under_contributed: >=1 member didn't pull their weight / disengaged this sprint.
- underperformance_unaddressed: an under-contributing member was worked AROUND, not raised
  with them (about contribution, not conflict; can be true with no open friction).
- core_subgroup_carried: a 2-3 person core did the real work this sprint; others peripheral.
- singled_out_below: a SINGLE identifiable member is picked out as THE weakest this sprint.
- singled_out_above: a SINGLE identifiable member is picked out as THE carrier/star this sprint.
- open_conflict: explicit friction, arguments, or interpersonal tension BEYOND ordinary
  task/technical disagreement this sprint.
- communication_breakdown: sustained poor communication this sprint (not a one-off).
- harmonious_balanced: the team worked well together this sprint — effort fair, no
  significant conflict or imbalance.
- leadership_problem: a designated leader ineffective/bypassed, or a leadership/coordination
  vacuum this sprint.
- mutual_support: members supported each other through difficulty this sprint (covering
  tasks, understanding, emotional support).

Return ONLY a JSON object with exactly these 11 keys. Each value is an object
{{"value": <boolean>, "quote": "<verbatim quote from the journals, or \\"\\">"}}.

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
        val, quote = (v.get("value"), v.get("quote", "")) if isinstance(v, dict) else (v, "")
        marks[k], quotes[k] = _to_bool(val), (quote or "")
    return marks, quotes


def run_team_sprint(cohort: str, team_label: str, journal_index: int, run_idx: int, *,
                    model: str | None = None, force: bool = False) -> dict:
    """Code one (team, sprint) for one shuffled run. ``run_idx`` seeds member-label
    shuffling (like whole-project marking) so a mark can't depend on who is "Member A"."""
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
                     max_tokens=1600, model=model, response_format={"type": "json_object"})
    marks, quotes = _parse(raw)
    rec = {"cohort": cohort, "team_label": team_label, "journal_index": journal_index,
           "run": run_idx, "marks": marks, "quotes": quotes}
    out.write_text(json.dumps(rec, indent=2))
    return rec


def sprint_indices(cohort: str) -> list[int]:
    """Work-sprint journal indices for a cohort = all journals except 1 (the intro)."""
    idx = sorted(int(i) for i in blobs._entries(cohort)["journal_index"].unique())
    return [i for i in idx if i != 1]
