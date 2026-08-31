"""Step 6 — blind marking.

Score each team on the frozen checklist (notes/llm-dynamics-checklist-v1.md),
blind to its cascade state, as strict JSON (value + one-line evidence per item).
Run 3x per team with shuffled member labels; majority-of-3 is computed later.
"""

from __future__ import annotations

import json

from . import blobs
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/marks"

# The 13 frozen items.
BINARY = [
    "effort_imbalance", "member_under_contributed", "underperformance_unaddressed",
    "core_subgroup_carried", "singled_out_below", "singled_out_above",
    "open_conflict", "communication_breakdown", "harmonious_balanced",
    "leadership_problem", "mutual_support",
]
CATEGORICAL = {
    "conflict_handling": ["none", "resolved", "festered"],
    "trajectory": ["stable", "deteriorated", "recovered"],
}
ITEMS = BINARY + list(CATEGORICAL)

SYSTEM = (
    "You code a student team's reflective journals against a fixed checklist of "
    "team-dynamics features. Mark strictly from the evidence: mark a feature "
    "present ONLY if the journals support it; if evidence is thin or absent, mark "
    "it not-present — never infer. Output ONLY the requested JSON object."
)

PROMPT = """Read this team's journals and fill the checklist. Mark present ONLY if
the journals support it; otherwise not-present.

Items (true/false unless noted):
- effort_imbalance: workload clearly uneven in AMOUNT (one or two did much more).
- member_under_contributed: >=1 member didn't pull their weight / disengaged.
- underperformance_unaddressed: a weak member was worked AROUND, not confronted
  (about contribution, not conflict; can be true with no open friction).
- core_subgroup_carried: a 2-3 person core did the real work, others peripheral.
- singled_out_below: a SINGLE identifiable member is picked out as THE weakest.
- singled_out_above: a SINGLE identifiable member is picked out as THE carrier/star.
- open_conflict: explicit friction/arguments/tension beyond task disagreement.
- conflict_handling: one of "none" | "resolved" | "festered".
- communication_breakdown: sustained poor communication (not a one-off).
- harmonious_balanced: worked well together, effort fair, no major conflict, whole project.
- leadership_problem: leader ineffective/bypassed, or a leadership vacuum.
- trajectory: one of "stable" | "deteriorated" | "recovered".
- mutual_support: members supported each other through personal difficulty.

Return ONLY a JSON object with exactly these 13 keys. Each value is an object
{{"value": <boolean, or the category string>, "why": "<short evidence citing member/journal>"}}.

TEAM JOURNALS:
{blob}"""


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "y", "1", "present")


def _parse(raw: str) -> tuple[dict, dict]:
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    marks, reasons = {}, {}
    for k in ITEMS:
        v = data.get(k)
        val, why = (v.get("value"), v.get("why", "")) if isinstance(v, dict) else (v, "")
        if k in CATEGORICAL:
            val = str(val).strip().lower()
            val = val if val in CATEGORICAL[k] else None
        else:
            val = _to_bool(val)
        marks[k], reasons[k] = val, why
    return marks, reasons


def run_team(cohort: str, team_label: str, run_idx: int, *, force: bool = False) -> dict:
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{cohort}_{team_label}_r{run_idx}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    blob = blobs.build_blob(cohort, team_label, seed=run_idx)  # shuffled labels per run
    raw = call_model(
        PROMPT.format(blob=blob), system=SYSTEM, temperature=0.2, max_tokens=1600,
        response_format={"type": "json_object"},
    )
    marks, reasons = _parse(raw)
    rec = {"cohort": cohort, "team_label": team_label, "run": run_idx,
           "marks": marks, "reasons": reasons}
    out.write_text(json.dumps(rec, indent=2))
    return rec
