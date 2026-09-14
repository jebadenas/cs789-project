"""Repair journal text that lost internal spaces during extraction.

A minority of journals (~3.6% of 2025_s1 entries) were extracted with spaces
dropped inside a passage ("Forexample,myPRforlinking..."). The model then quotes
that broken text faithfully, and it is unreadable on the dashboard. This module
re-inserts spaces into long glued runs with a wordlist + dynamic programming
(favouring long dictionary words), leaving normal text untouched.

Applied centrally in blobs._entries so every consumer — the per-sprint marking
blob (and thus the re-run), the dashboard, and the questionnaire — sees repaired
text. Only runs of 18+ letters that aren't already a dictionary word are touched.
"""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=1)
def _wordset() -> frozenset[str]:
    for p in ("/usr/share/dict/words", "/usr/dict/words"):
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                return frozenset({w.strip().lower() for w in fh if w.strip()}) | {"a", "i"}
        except OSError:
            continue
    return frozenset({"a", "i"})


def _split_glued(token: str) -> str:
    """Split one long glued alphabetic run into space-separated dictionary words."""
    words = _wordset()
    low = token.lower()
    n = len(low)
    NEG = float("-inf")
    best = [0.0] + [NEG] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - 18), i):
            seg = low[j:i]
            score = len(seg) ** 2 if seg in words else -len(seg)  # reward long real words
            if best[j] + score > best[i]:
                best[i] = best[j] + score
                back[i] = j
    pieces, i = [], n
    while i > 0:
        j = back[i]
        pieces.append(token[j:i])  # keep original casing
        i = j
    return " ".join(reversed(pieces))


def resegment(text: str) -> str:
    """Re-insert spaces into glued word-runs (18+ letters, not a real word)."""
    if not text:
        return text

    def fix(m: "re.Match[str]") -> str:
        run = m.group(0)
        if len(run) < 18 or run.lower() in _wordset():
            return run
        return _split_glued(run)

    return re.sub(r"[A-Za-z]{18,}", fix, text)


def has_glued(text: str) -> bool:
    """True if the text contains a suspiciously long glued run."""
    return any(len(w) >= 18 and w.lower() not in _wordset()
               for w in re.findall(r"[A-Za-z]{18,}", text or ""))
