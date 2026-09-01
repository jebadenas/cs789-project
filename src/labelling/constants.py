"""Shared constants for the labelling package — pure data, ZERO imports.

Deliberately dependency-free so the analysis scripts (summary.py) can import the
taxonomy without transitively pulling in src.dynamics (via sample.py -> mixture).
Keeping this a leaf module is what lets summary.py stay provably archetype-blind.
"""

from __future__ import annotations

# The three peer-assessment questions each team answers, in canonical order.
QUESTIONS: tuple[str, ...] = ("source code", "group report", "showcase poster")

# Operative taxonomy (rubric §7): 5 substantive labels + Unclassified. Collusive
# was dropped — not reliably separable from Cohesive on the matrix alone without
# journals. See docs/labelling-design.md §labelling-ux.
VALID_LABELS: list[str] = [
    "Cohesive", "Dominant", "Free-rider", "Conflict", "Disengaged",
    "Unclassified",
]

# Descriptive signal hints shown as REFERENCE in the UI (not a decision tree —
# a forced sequence would anchor raters and inflate κ).
LABEL_HINTS: dict[str, str] = {
    "Cohesive": "Contributions seen as roughly even; nobody singled out. "
                "In-degree bars similar; no dark or bright row.",
    "Dominant": "One person rated well ABOVE the rest. One bright row / one "
                "tall in-degree bar.",
    "Free-rider": "One person rated well BELOW the rest (may be a non-submitter "
                  "= grey column). One dark row / one short bar.",
    "Conflict": "One-directional negativity or factions. Asymmetry: A rates B "
                "high but B rates A low; bimodal inflows.",
    "Disengaged": "Everyone rates everyone (near-)identically — no signal. The "
                  "matrix is basically one flat colour.",
    "Unclassified": "Doesn't clearly fit, or the evidence conflicts. Use it "
                    "honestly rather than forcing a label.",
}

# Per-question label columns on the entry sheet (filled only when a team's three
# assessments clearly disagree). Order matches QUESTIONS.
PER_QUESTION_COLS: list[str] = [f"primary_{q.replace(' ', '_')}" for q in QUESTIONS]

# Full column contract for a filled entry sheet (UI export + paper template).
SHEET_COLUMNS: list[str] = (
    ["card_id", "primary_label", "secondary_label", "confidence"]
    + PER_QUESTION_COLS + ["notes"]
)
