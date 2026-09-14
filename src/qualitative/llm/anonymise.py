"""Pseudonymise real journal text for the tutor QUESTIONNAIRE.

The dashboard is a local coordinator tool and shows real names; the questionnaire
is shown to external tutors, so every real name must be replaced with a stable,
blinded label. This module maps each teammate's real name to their ``Member X``
label (consistent across the whole case) using the anon_id crosswalk + peer
roster, then rewrites journal text and quotes:

  - a teammate's own name / name tokens  -> that member's "Member X" label
  - any other roster name that leaks in   -> "[teammate]"

So a reader can still follow "Member C did X, then Member A ..." without ever
seeing a real name.
"""

from __future__ import annotations

import csv
import glob
import re
from functools import lru_cache
from itertools import permutations

import pandas as pd

from . import blobs

_CROSSWALK = blobs._REPO / "data/journals/crosswalk/name_to_anon.csv"

# first names that are also ordinary words — never blanket-replace these as names
_STOP = {"will", "may", "mark", "grace", "art", "drew", "hope", "rose", "an", "so",
         "in", "on", "a", "the", "by", "van", "le", "lin", "don", "kim", "max", "ivy",
         "sunny", "summer", "faith", "joy", "angel"}


def _peer_prefix(cohort: str) -> str:
    year, sem = cohort.split("_s")
    return f"COMPSCI399-S{sem}-{year}"


@lru_cache(maxsize=8)
def _team_key(cohort: str) -> dict[str, str]:
    """blinded team_label -> real team name (from the reader crosswalk)."""
    for f in glob.glob(str(blobs._READER / f"team_key_{cohort}*.csv")):
        df = pd.read_csv(f)
        return dict(zip(df["team_label"], df["real_team"]))
    return {}


@lru_cache(maxsize=8)
def _full_rosters(cohort: str) -> dict[str, set[str]]:
    """real_team -> set of full member names from the peer CSVs."""
    out: dict[str, set[str]] = {}
    for path in glob.glob(f"{blobs._REPO}/data/peer_sessions/{_peer_prefix(cohort)}*.csv"):
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        hdr = next((i for i, l in enumerate(lines) if l.startswith("Team,Name,Email")), None)
        if hdr is None:
            continue
        for l in lines[hdr + 1:]:
            if not l.strip() or l.startswith("Question") or l.startswith("Summary"):
                break
            row = next(csv.reader([l]))
            if len(row) < 2 or not row[0].strip().startswith("Team"):
                continue
            out.setdefault(row[0].strip(), set()).add(row[1].strip())
    return out


def _split(name: str) -> list[str]:
    """All alphabetic name parts (incl. short ones like 'Hu', 'Ji') — for matching."""
    return [t for t in re.split(r"[\s,]+", name) if t.isalpha()]


def _keys(name: str) -> list[str]:
    """Name parts safe to use as replacement keys — drop short/ambiguous ones."""
    return [t for t in _split(name) if len(t) >= 3 and t.lower() not in _STOP]


@lru_cache(maxsize=8)
def token_to_member(cohort: str) -> dict[str, dict[str, str]]:
    """team_label -> {lowercased name token -> 'Member X'} for that team's members.

    Built by joining journal entries (anon_id + member_label) to the crosswalk
    (anon_id -> normalised_name), then matching each member to their proper peer
    roster name so we catch first name, last name and full name.
    """
    ent = blobs._entries(cohort)[["team_label", "member_label", "anon_id"]].drop_duplicates()
    cx = pd.read_csv(_CROSSWALK)
    cx = cx[cx["cohort"] == cohort][["anon_id", "normalised_name"]]
    merged = ent.merge(cx, on="anon_id", how="left")
    tk = _team_key(cohort)
    rosters = _full_rosters(cohort)

    out: dict[str, dict[str, str]] = {}
    for _, r in merged.iterrows():
        team_label, member_label = r["team_label"], r["member_label"]
        normalised = re.sub(r"[^a-z]", "", (r["normalised_name"] or "").lower())
        roster = rosters.get(tk.get(team_label, ""), set())
        # find this member's proper roster name by matching the normalised form
        # (match on ALL tokens incl. short last names like 'Hu'/'Ji')
        proper = None
        for fn in roster:
            toks = _split(fn)
            if len(toks) <= 4 and any(
                re.sub(r"[^a-z]", "", "".join(p).lower()) == normalised
                for p in permutations(toks)
            ):
                proper = fn
                break
        label = f"Member {member_label}"
        mapping = out.setdefault(team_label, {})
        for tok in _keys(proper or r["normalised_name"] or ""):
            mapping[tok.lower()] = label
    return out


# identifying strings that aren't names: emails and UoA UPIs (e.g. "ezhe473")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_UPI = re.compile(r"\b[a-z]{2,5}\d{3,4}\b", re.IGNORECASE)  # UoA UPI: letters+3-4 digits


def anonymise(text: str, cohort: str, team_label: str) -> str:
    """Replace this team's real names with stable 'Member X' labels; blank others.

    Also strips emails and UoA UPIs, which identify a student but aren't names.
    """
    if not text:
        return text
    mapping = token_to_member(cohort).get(team_label, {})
    out = _EMAIL.sub("[email]", text)
    out = _UPI.sub("[id]", out)
    # 1) known teammates -> their Member label (longest tokens first, word-boundary)
    for tok in sorted(mapping, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(tok)}\b", mapping[tok], out, flags=re.IGNORECASE)
    # 2) own-team names we couldn't attribute to a member -> generic placeholder
    #    (guarantees no own-team name leaks even when the crosswalk match failed)
    own = _roster_tokens(cohort).get(team_label, set()) - set(mapping)
    for tok in sorted(own, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(tok)}\b", "[teammate]", out, flags=re.IGNORECASE)
    # 3) other teams' names that leak in (rarer) -> placeholder; len>=4 to limit
    #    over-redaction of short tokens that double as ordinary words
    others: set[str] = set()
    for tl, toks in _roster_tokens(cohort).items():
        if tl != team_label:
            others |= {t for t in toks if len(t) >= 4}
    for tok in sorted(others - set(mapping) - own, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(tok)}\b", "[teammate]", out, flags=re.IGNORECASE)
    return out


@lru_cache(maxsize=8)
def _roster_tokens(cohort: str) -> dict[str, set[str]]:
    """team_label -> all real name tokens (>=3) for that team, straight from the roster."""
    tk = _team_key(cohort)
    rosters = _full_rosters(cohort)
    out: dict[str, set[str]] = {}
    for team_label, real in tk.items():
        toks: set[str] = set()
        for fn in rosters.get(real, set()):
            toks |= {t.lower() for t in _keys(fn)}
        out[team_label] = toks
    return out


def leaked_names(text: str, cohort: str, team_label: str) -> list[str]:
    """Any of THIS team's real name tokens still present (independent verification)."""
    toks = _roster_tokens(cohort).get(team_label, set())
    return [tok for tok in toks if re.search(rf"\b{re.escape(tok)}\b", text, flags=re.IGNORECASE)]
