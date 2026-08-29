"""Assemble one structured, blinded text blob per team.

The blob the model reads carries only pseudonymous ``Member A/B/...`` labels and
the journal index — never real names, team names, or the cascade state. Cascade
state lives in the *metadata* table (for grouping at count-time), never in the
blob.
"""

from __future__ import annotations

import glob
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

PROMPTED = ["2023_s2", "2024_s1", "2024_s2", "2025_s1"]

_REPO = Path(__file__).resolve().parents[3]
_PARQUET = _REPO / "data/journals/processed/entries.parquet"
_READER = _REPO / "output/qualitative/reader"
_STATES = _REPO / "output/dynamics2/pooled/team_states.csv"


def _cohort_of(csv_path: str) -> str:
    m = re.search(r"S(\d)-(\d{4})", csv_path)
    return f"{m.group(2)}_s{m.group(1)}"


@lru_cache(maxsize=1)
def load_team_meta() -> pd.DataFrame:
    """(cohort, team_label) -> real_team + cascade state. Internal only."""
    keys = pd.concat(
        [pd.read_csv(f) for f in glob.glob(str(_READER / "team_key_*.csv"))],
        ignore_index=True,
    )
    keys = keys[keys["cohort"].isin(PROMPTED)]
    states = pd.read_csv(_STATES)
    states["cohort"] = states["csv_path"].map(_cohort_of)
    merged = keys.merge(
        states[["cohort", "team_name", "pooled_state", "anyflag_bucket"]],
        left_on=["cohort", "real_team"],
        right_on=["cohort", "team_name"],
        how="left",
    )
    return merged.set_index(["cohort", "team_label"])


@lru_cache(maxsize=8)
def _entries(cohort: str) -> pd.DataFrame:
    """Batch entries (blinded labels) joined to journal text, one cohort."""
    batch = json.loads((_READER / f"batch_teams_{cohort}.json").read_text())
    ents = pd.DataFrame(batch["entries"])
    ents = ents[ents["extract_status"] == "ok"].copy()
    ents["submission_id"] = ents["submission_id"].astype(str)

    text = pd.read_parquet(_PARQUET, columns=["submission_id", "text"])
    text["submission_id"] = text["submission_id"].astype(str)
    return ents.merge(text, on="submission_id", how="left")


def build_blob(cohort: str, team_label: str) -> str:
    """One structured blob for a team: members A..F, each journal in order."""
    df = _entries(cohort)
    team = df[df["team_label"] == team_label].sort_values(
        ["member_label", "journal_index"]
    )
    parts: list[str] = []
    for _, r in team.iterrows():
        body = (r["text"] or "").strip()
        if not body:
            continue
        parts.append(f"Member {r['member_label']} — Journal {r['journal_index']}:\n{body}")
    return "\n\n".join(parts)


def team_labels(cohort: str) -> list[str]:
    return sorted(_entries(cohort)["team_label"].unique())
