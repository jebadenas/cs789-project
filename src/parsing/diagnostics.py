"""Structured parse diagnostics for peer-assessment CSV files.

Captures events that the parser detects (non-submitters, excluded teams,
point mismatches) as data rather than log messages, enabling downstream
reporting and aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DiagnosticEvent(str, Enum):
    """Types of parse diagnostic events."""

    RATER_MISSING = "rater_missing"
    TEAM_EXCLUDED = "team_excluded"
    POINT_TOTAL_MISMATCH = "point_total_mismatch"
    SUMMARY_CROSS_CHECK = "summary_cross_check"


@dataclass(frozen=True)
class ParseDiagnostic:
    """A single diagnostic event from parsing a CSV file."""

    csv_path: str
    team_name: str
    question_label: str
    event: DiagnosticEvent
    detail: str
    student_name: str = ""
    student_email: str = ""


@dataclass
class DiagnosticCollector:
    """Accumulates ParseDiagnostic events during a parse run."""

    diagnostics: list[ParseDiagnostic] = field(default_factory=list)

    def add(
        self,
        csv_path: str | Path,
        team_name: str,
        question_label: str,
        event: DiagnosticEvent,
        detail: str,
        student_name: str = "",
        student_email: str = "",
    ) -> None:
        self.diagnostics.append(
            ParseDiagnostic(
                csv_path=str(csv_path),
                team_name=team_name,
                question_label=question_label,
                event=event,
                detail=detail,
                student_name=student_name,
                student_email=student_email,
            )
        )

    def by_event(self, event: DiagnosticEvent) -> list[ParseDiagnostic]:
        """Filter diagnostics by event type."""
        return [d for d in self.diagnostics if d.event == event]

    @property
    def excluded_teams(self) -> list[ParseDiagnostic]:
        return self.by_event(DiagnosticEvent.TEAM_EXCLUDED)

    @property
    def missing_raters(self) -> list[ParseDiagnostic]:
        return self.by_event(DiagnosticEvent.RATER_MISSING)
