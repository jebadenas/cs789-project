"""Reflection-template classification (handoff-6, Task 3).

Classifies each cohort's journal template by the shared boilerplate that recurs
across many students — the assignment's section headings and question stems, not
any individual's answer. Also reports whether a cohort's template explicitly
prompts for *team dynamics*, and (for the cohort that does) whether that prompt
is spread evenly across the semester or introduced late.

Consumed by ``audit.py`` (§9 of the linkage report). Reads only recurring lines,
never individual entries, so it exposes no personal content.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pandas as pd

from src.qualitative.ingest import ENTRIES_PARQUET

# Words that mark an explicit team-dynamics prompt (vs individual reflection).
_TEAM_WORDS = ("team", "dynamic", "teammate", "conflict", "collaborat",
               "group member")
# The specific dynamics section seen in 2024_s1.
_DYNAMICS_PHRASE = "assessment of team"

DYN_ASSIGN = Path("output/dynamics/aa_k4_assignments.csv")
_COHORT_RE = re.compile(r"S(?P<sem>\d)-(?P<year>\d{4})")
_ARCHETYPES = ("A0", "A1", "A2", "A3")


def recurring_lines(texts, min_share: float = 0.25,
                    lo: int = 8, hi: int = 120) -> tuple[list[tuple[str, float]], int]:
    """Lines appearing (normalised) in >= ``min_share`` of ``texts``.

    Length-bounded so we catch section headings / question stems, not whole
    copied paragraphs. Returns (sorted [line, share], n_docs).
    """
    doc_count: Counter = Counter()
    n = 0
    for t in texts:
        n += 1
        seen = set()
        for line in t.splitlines():
            s = re.sub(r"\s+", " ", line.strip()).lower()
            if lo <= len(s) <= hi:
                seen.add(s)
        doc_count.update(seen)
    lines = [(l, c / n) for l, c in doc_count.items() if n and c / n >= min_share]
    lines.sort(key=lambda x: -x[1])
    return lines, n


def classify_templates(parquet: Path = ENTRIES_PARQUET) -> dict:
    """Per-cohort template: recurring lines + whether it prompts team dynamics."""
    df = pd.read_parquet(parquet, columns=["cohort", "extract_status", "text"])
    ok = df[df["extract_status"] == "ok"]
    out: dict[str, dict] = {}
    for cohort in sorted(ok["cohort"].unique()):
        lines, n = recurring_lines(ok[ok["cohort"] == cohort]["text"])
        team_prompts = [l for l, _ in lines if any(w in l for w in _TEAM_WORDS)]
        out[cohort] = {
            "n": n, "lines": lines, "team_prompts": team_prompts,
            "has_team_prompt": bool(team_prompts),
        }
    return out


def dynamics_by_index(parquet: Path = ENTRIES_PARQUET, cohort: str = "2024_s1",
                      phrase: str = _DYNAMICS_PHRASE) -> dict[int, tuple[int, float]]:
    """journal_index -> (n_ok_entries, % containing the dynamics prompt).

    Tells apart "students skip a stable section" from "the section was introduced
    mid-semester" (rising share by index).
    """
    df = pd.read_parquet(parquet, columns=["cohort", "journal_index",
                                           "extract_status", "text"])
    ok = df[(df["cohort"] == cohort) & (df["extract_status"] == "ok")]
    rows: dict[int, tuple[int, float]] = {}
    for idx in sorted(ok["journal_index"].dropna().unique()):
        g = ok[ok["journal_index"] == idx]
        share = g["text"].str.lower().str.contains(phrase, regex=False).mean()
        rows[int(idx)] = (len(g), round(100 * float(share), 1))
    return rows


def archetype_derivation_stats() -> dict:
    """Mean-load argmax vs majority-vote team-archetype comparison (reportable).

    Self-contained (reads the persisted AA k=4 refit directly) to avoid a circular
    import with ``sample.py``.
    """
    if not DYN_ASSIGN.exists():
        return {}
    aa = pd.read_csv(DYN_ASSIGN)
    n = ties = unanimous = agree = 0
    for _, grp in aa.groupby(["csv_path", "team_name"]):
        loads = {a: grp[f"load_{a}"].mean() for a in _ARCHETYPES}
        meanload = max(loads, key=loads.get)
        modes = grp["archetype"].mode()
        majority = modes.iloc[0] if len(modes) == 1 else "Mixed"
        n += 1
        ties += len(modes) > 1
        unanimous += grp["archetype"].nunique() == 1
        agree += meanload == majority
    return {"n_teams": n, "majority_ties": ties, "majority_unanimous": unanimous,
            "meanload_eq_majority": agree}
