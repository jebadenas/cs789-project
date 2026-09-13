"""Step 6b — instrument-improvement re-run of the two weak fields (Workstream 3).

Re-asks ONLY the two v1 fields that wobble (conflict_handling 55%, trajectory 72%)
as a reliable **gate** + a **follow-up** asked only when the gate fires — the fix
the reliability diagnosis pointed to (notes/llm-dynamics-checklist-v2.md).

  Conflict:   open_conflict (gate) --> conflict_outcome (resolved/festered)
  Trajectory: notable_change (gate) --> change_direction (deteriorated/recovered)

Each answer carries a VERBATIM journal quote so the evidence can be string-matched
back to the source (hallucination check). Same protocol as marking.py: 119 teams,
3 shuffled runs, blind to cascade state. v1 stays frozen; this is a separate
instrument, written to its own directory.
"""

from __future__ import annotations

import json

from . import blobs
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/marks_v2"

# The two gates (binary) and their follow-up categoricals.
GATES = ["open_conflict", "notable_change"]
FOLLOWUPS = {
    "conflict_outcome": ["resolved", "festered"],   # asked only if open_conflict
    "change_direction": ["deteriorated", "recovered"],  # asked only if notable_change
}
# Which gate unlocks which follow-up.
GATE_OF = {"conflict_outcome": "open_conflict", "change_direction": "notable_change"}
FIELDS = GATES + list(FOLLOWUPS)

SYSTEM = (
    "You code a student team's reflective journals against a small set of "
    "team-dynamics questions. Mark strictly from the evidence: answer from what the "
    "journals actually say, never infer. Every answer must carry a VERBATIM quote "
    "copied word-for-word from the journals as its evidence (empty string only when "
    "the answer is a 'no'/'not-applicable' with nothing to cite). Output ONLY the "
    "requested JSON object."
)

PROMPT = """Read this team's journals and answer the questions below. Answer strictly
from what the journals say — never infer. Each answer carries a "quote" field: copy a
short VERBATIM span (word-for-word) from the journals that supports your answer.

Conflict (a gate, then a follow-up):
- open_conflict: true/false. Was there explicit friction, arguments, or interpersonal
  tension BEYOND ordinary task/technical disagreement? Routine "we disagreed about
  the tech stack then moved on" is task disagreement -> false. Only real interpersonal
  friction is true.
- conflict_outcome: "resolved" or "festered" -- ANSWER ONLY IF open_conflict is true;
  otherwise use null. resolved = the team worked through it and it stopped affecting
  them; festered = it stayed unresolved and kept affecting the team.

Trajectory (a gate, then a follow-up):
- notable_change: true/false. Did the team's functioning MATERIALLY change over the
  project -- a genuine downturn (crisis, breakdown, serious sustained dip) or a genuine
  turnaround? A minor sprint hiccup, a single rough week, or ordinary deadline pressure
  the team handled does NOT count -> that is false (a stable team).
- change_direction: "deteriorated" or "recovered" -- ANSWER ONLY IF notable_change is
  true; otherwise use null. deteriorated = the team ended in a worse place; recovered =
  a real rough patch that genuinely turned around.

Return ONLY a JSON object with exactly these 4 keys: open_conflict, conflict_outcome,
notable_change, change_direction. Each value is an object
{{"value": <boolean, or the category string, or null>, "quote": "<verbatim span from the journals, or \\"\\">"}}.

TEAM JOURNALS:
{blob}"""


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "y", "1", "present")


def _parse(raw: str) -> tuple[dict, dict]:
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    marks, quotes = {}, {}
    for k in FIELDS:
        v = data.get(k)
        val, quote = (v.get("value"), v.get("quote", "")) if isinstance(v, dict) else (v, "")
        if k in GATES:
            val = _to_bool(val)
        else:  # follow-up categorical: valid only if its gate fired, else None
            val = str(val).strip().lower()
            val = val if val in FOLLOWUPS[k] else None
        marks[k], quotes[k] = val, (quote or "")
    # Enforce the gate logic regardless of what the model returned.
    for fu, gate in GATE_OF.items():
        if not marks[gate]:
            marks[fu] = None
    return marks, quotes


def run_team(cohort: str, team_label: str, run_idx: int, *, force: bool = False) -> dict:
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{cohort}_{team_label}_r{run_idx}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    blob = blobs.build_blob(cohort, team_label, seed=run_idx)  # shuffled labels per run
    raw = call_model(
        PROMPT.format(blob=blob), system=SYSTEM, temperature=0.2, max_tokens=1200,
        response_format={"type": "json_object"},
    )
    marks, quotes = _parse(raw)
    rec = {"cohort": cohort, "team_label": team_label, "run": run_idx,
           "marks": marks, "quotes": quotes}
    out.write_text(json.dumps(rec, indent=2))
    return rec
