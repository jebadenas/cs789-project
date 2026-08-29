"""Step 2 — per-team notes ("map").

Open, free-form observations about one team's dynamics, grounded in its
journals. No fixed checklist, no cascade label. Resumable: one JSON file per
team, already-done teams are skipped, so a killed run just resumes.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import blobs
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/notes"

SYSTEM = (
    "You are a qualitative researcher reading a student team's reflective "
    "journals to characterise its INTERPERSONAL TEAM DYNAMICS — how the members "
    "worked together as people, not what the project produced. Report only what "
    "the journals support; if evidence is thin or absent, say so plainly. Never "
    "invent events, quotes, or names."
)

PROMPT = """Below are one student team's reflective journals, each labelled by
member (A, B, ...) and journal number.

Write concise, grounded notes on this team's INTERPERSONAL DYNAMICS — the working
relationships between the members. Focus only on things like:
- how work and effort were actually shared (balanced, one or two carrying it, or
  someone not contributing)
- conflict, tension, or frustration between members — and whether it was
  addressed or left to fester
- any member singled out by teammates (positively or negatively), and whether the
  others appear to agree
- communication and coordination between members (smooth, or breakdowns, people
  left out of the loop)
- whether the dynamic shifted over time (e.g. early cohesion giving way to
  friction, or a struggling member coming good)

Hard rules:
- Do NOT summarise the project's activities, features, tasks, or weekly progress.
  We do not care what the team built, only how they worked together. Ignore
  technical detail unless it reveals a relationship (e.g. one member repeatedly
  finishing others' work).
- Do NOT organise your answer by week or as a timeline. Write a flat list of
  dynamic observations.
- Stay close to the text and cite the member(s) and journal(s) behind each
  observation. If the evidence is weak, or the team simply seems harmonious with
  little to report, say so — do not invent drama to fill space.

TEAM JOURNALS:
{blob}"""


def run_team(cohort: str, team_label: str, *, num_ctx: int, force: bool = False) -> dict:
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{cohort}_{team_label}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())

    blob = blobs.build_blob(cohort, team_label)
    note = call_model(
        PROMPT.format(blob=blob), system=SYSTEM, temperature=0.2, num_ctx=num_ctx
    )
    rec = {"cohort": cohort, "team_label": team_label, "note": note}
    out.write_text(json.dumps(rec, indent=2))
    return rec
