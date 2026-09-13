"""Per-(team, sprint) SUMMARY on the 72B — same model/provenance as the marks.

A 2-3 sentence synopsis of how a team functioned in ONE sprint, written by the 72B from
that sprint's journals (a separate, cheaper pass than re-running the marking). Feeds the
dashboard's per-sprint summary. Output:
output/qualitative/llm/marks_summary/{cohort}_{team}_j{ji}.json (resumable).
"""
from __future__ import annotations

import json

from . import blobs
from .marking_sprint import sprint_indices  # re-export the same sprint set
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/marks_summary"

SYSTEM = (
    "You summarise how a student team did in ONE sprint, for a course coordinator, from "
    "their reflective journals. Write 2-3 plain, factual sentences grounded in the journals "
    "- collaboration and workload, any conflict / communication / leadership issues, and "
    "positives. Output ONLY the summary text."
)
PROMPT = """The journals below are from ONE sprint of a student team's project. In 2-3
sentences, summarise how the team functioned this sprint. Base it only on the journals.

TEAM JOURNALS (one sprint):
{blob}"""


def run_team_sprint(cohort: str, team_label: str, journal_index: int, *,
                    model: str | None = None, force: bool = False) -> dict:
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{cohort}_{team_label}_j{journal_index}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    blob = blobs.build_blob(cohort, team_label, journal_indices={journal_index})
    if not blob.strip():
        rec = {"cohort": cohort, "team_label": team_label, "journal_index": journal_index,
               "summary": "", "empty": True}
    else:
        text = call_model(PROMPT.format(blob=blob), system=SYSTEM, temperature=0.3,
                          max_tokens=220, model=model)
        rec = {"cohort": cohort, "team_label": team_label, "journal_index": journal_index,
               "summary": text.strip()}
    out.write_text(json.dumps(rec, indent=2))
    return rec

__all__ = ["run_team_sprint", "sprint_indices", "_OUT"]
