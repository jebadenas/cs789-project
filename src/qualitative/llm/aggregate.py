"""Step 4 — aggregate per cascade state ("reduce").

Group the per-team notes by cascade state, then for each state read all its
teams' notes together and report the dynamics that RECUR across teams. The model
is deliberately NOT told the state's name — grouping is ours, so the label can't
prime it. Output: one candidate-pattern file per state.
"""

from __future__ import annotations

import json

from . import blobs, notes
from .model import call_model

_OUT = blobs._REPO / "output/qualitative/llm/patterns"

SYSTEM = (
    "You are a qualitative researcher reading many student teams' team-dynamics "
    "notes to find patterns that RECUR across teams. Report only what shows up in "
    "multiple teams; ignore one-off details. Never invent."
)

PROMPT = """Below are short team-dynamics notes for {n} different student teams
(each team separated by a line of dashes). These teams were grouped together
because they share a hidden characteristic — you do NOT need to guess what it is.

Identify the team-dynamics patterns that RECUR across multiple teams here. For
each recurring pattern:
- name it as a short phrase,
- say roughly how common it is (e.g. "most teams", "about half", "a few"),
- describe its flavour in one line, grounded in the notes.

List them from most to least common. Ignore anything that appears in only one team.

TEAM NOTES:
{blob}"""


def group_by_state() -> dict[str, list[dict]]:
    """(pooled_state) -> list of note records. Grouping is internal only."""
    meta = blobs.load_team_meta()
    out: dict[str, list[dict]] = {}
    for f in sorted(notes._OUT.glob("*.json")):
        d = json.loads(f.read_text())
        try:
            state = str(meta.loc[(d["cohort"], d["team_label"]), "pooled_state"])
        except KeyError:
            continue
        out.setdefault(state, []).append(d)
    return out


def run_state(state: str, records: list[dict], *, force: bool = False) -> dict:
    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / f"{state.replace(' ', '_').replace('/', '_')}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    blob = "\n\n----------\n\n".join(r["note"] for r in records)
    patterns = call_model(
        PROMPT.format(n=len(records), blob=blob),
        system=SYSTEM, temperature=0.2, max_tokens=1200,
    )
    rec = {"state": state, "n_teams": len(records), "patterns": patterns}
    out.write_text(json.dumps(rec, indent=2))
    return rec


def run_all(*, force: bool = False) -> None:
    groups = group_by_state()
    print(f"aggregate: {len(groups)} states", flush=True)
    for state, recs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"  {state} ({len(recs)} teams)", flush=True)
        run_state(state, recs, force=force)
    print("aggregate: complete", flush=True)
