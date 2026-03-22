import csv
import re
from pathlib import Path
from typing import Optional

from src.schemas import Session, Question, NumericRecord, TextRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_numeric(value: str) -> Optional[float]:
    """Convert a cell to float, returning None for missing/invalid values."""
    v = value.strip()
    if v in ("", "Not Submitted", "N/A", "No Response"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _extract_year(course: str) -> str:
    match = re.search(r"(\d{4})", course)
    return match.group(1) if match else "unknown"


def _extract_session_number(session_name: str) -> int:
    match = re.search(r"Session\s+(\d+)", session_name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _extract_semester(session_name: str) -> str:
    match = re.search(r"(S\d)", session_name)
    return match.group(1) if match else "S1"


def _is_text_question(header_row: list[str]) -> bool:
    return "Feedback" in header_row or "feedback" in (c.lower() for c in header_row)


# ---------------------------------------------------------------------------
# Row parsers
# ---------------------------------------------------------------------------

def _parse_numeric_row(row: list[str]) -> Optional[NumericRecord]:
    if len(row) < 5:
        return None
    return NumericRecord(
        team=row[0].strip(),
        name=row[1].strip(),
        email=row[2].strip(),
        claimed_contribution=_parse_numeric(row[3]),
        perceived_contribution=_parse_numeric(row[4]),
        ratings_received=[_parse_numeric(v) for v in row[5:] if v.strip() != ""],
    )


def _parse_text_row(row: list[str]) -> Optional[TextRecord]:
    row = row + [""] * (8 - len(row))
    giver_name = row[1].strip()
    feedback = row[6].strip()
    if not giver_name and not feedback:
        return None
    return TextRecord(
        team=row[0].strip(),
        giver_name=giver_name,
        giver_email=row[2].strip(),
        recipient_team=row[3].strip(),
        recipient_name=row[4].strip(),
        recipient_email=row[5].strip(),
        feedback=feedback,
        givers_comment=row[7].strip(),
    )


# ---------------------------------------------------------------------------
# Question block parser
# ---------------------------------------------------------------------------

def _parse_question_block(block: list[list[str]]) -> Question:
    q_match = re.match(r"Question\s+(\d+)", block[0][0].strip(), re.IGNORECASE)
    q_number = int(q_match.group(1)) if q_match else 0
    q_text = block[0][1].strip() if len(block[0]) > 1 else ""

    header_row_idx = None
    for i in range(1, len(block)):
        cell = block[i][0].strip() if block[i] else ""
        if cell in ("", "Summary Statistics") or cell.startswith('"') or cell.startswith("In the"):
            continue
        if cell.lower() == "team":
            header_row_idx = i
            break

    if header_row_idx is None:
        return Question(number=q_number, text=q_text, question_type="numeric")

    header = block[header_row_idx]
    is_text = _is_text_question(header)
    question = Question(
        number=q_number,
        text=q_text,
        question_type="text" if is_text else "numeric",
    )

    for row in block[header_row_idx + 1:]:
        if not row or all(c.strip() == "" for c in row):
            continue
        record = _parse_text_row(row) if is_text else _parse_numeric_row(row)
        if record is not None:
            question.records.append(record)

    return question


# ---------------------------------------------------------------------------
# Session parser
# ---------------------------------------------------------------------------

def load_session(filepath: str | Path) -> Session:
    """Parse a single peer-feedback CSV into a Session object."""
    filepath = Path(filepath)

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        raw = f.read()

    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = list(csv.reader(raw.splitlines()))

    course = lines[0][1].strip() if len(lines[0]) > 1 else ""
    session_name = lines[1][1].strip() if len(lines[1]) > 1 else ""

    session = Session(
        course=course,
        name=session_name,
        year=_extract_year(course),
        number=_extract_session_number(session_name),
        semester=_extract_semester(session_name),
    )

    question_starts = [
        i for i, row in enumerate(lines)
        if row and re.match(r"^Question\s+\d+$", row[0].strip(), re.IGNORECASE)
    ]

    for idx, start in enumerate(question_starts):
        end = question_starts[idx + 1] if idx + 1 < len(question_starts) else len(lines)
        question = _parse_question_block(lines[start:end])
        session.questions[question.number] = question

    return session