"""CSV parser for peer-assessment feedback files.

Reads COMPSCI 399 peer feedback CSVs and constructs validated ScoreMatrix
objects for each (team, point-distribution question) combination.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

import numpy as np

from .schemas import ScoreMatrix, StudentInfo

logger = logging.getLogger(__name__)

# Matches questions like "Distribute a total of 60 points..."
_POINT_DIST_PATTERN = re.compile(r"Distribute a total of", re.IGNORECASE)

# Derives a short label from question text
_LABEL_PATTERNS = [
    (re.compile(r"source code", re.IGNORECASE), "source code"),
    (re.compile(r"group report", re.IGNORECASE), "group report"),
    (re.compile(r"showcase poster", re.IGNORECASE), "showcase poster"),
]


def parse_session(
    filepath: str | Path,
) -> dict[tuple[str, str], ScoreMatrix]:
    """Parse a peer-feedback CSV into ScoreMatrix objects.

    Args:
        filepath: Path to a COMPSCI 399 peer feedback CSV file.

    Returns:
        Dict keyed by (team_name, question_label) → ScoreMatrix.
    """
    filepath = Path(filepath)
    lines = filepath.read_text(encoding="utf-8-sig").splitlines()

    # Extract session metadata from first two lines
    year, semester, session_number = _extract_session_metadata(lines)

    # Split into question blocks
    question_blocks = _split_question_blocks(lines)

    result: dict[tuple[str, str], ScoreMatrix] = {}

    for q_text, block_lines in question_blocks:
        if not _POINT_DIST_PATTERN.search(q_text):
            continue

        label = _derive_question_label(q_text)
        summary_totals = _extract_summary_totals(block_lines)
        directed_rows = _extract_directed_data(block_lines)

        team_matrices = _build_matrices(
            directed_rows=directed_rows,
            summary_totals=summary_totals,
            team_meta=dict(
                question_label=label,
                year=year,
                semester=semester,
                session_number=session_number,
            ),
        )

        for (team_name, _label), sm in team_matrices.items():
            result[(team_name, _label)] = sm

    return result


def _extract_session_metadata(lines: list[str]) -> tuple[str, str, int]:
    """Extract year, semester, session number from CSV header lines."""
    # Line 0: "Course,COMPSCI399-S1-2024"
    # Line 1: "Session Name,Peer Feedback Session 4 - S1, 2024"
    course_line = lines[0] if lines else ""
    session_line = lines[1] if len(lines) > 1 else ""

    year_match = re.search(r"(\d{4})", course_line)
    year = year_match.group(1) if year_match else ""

    sem_match = re.search(r"(S\d)", course_line)
    semester = sem_match.group(1) if sem_match else ""

    num_match = re.search(r"Session\s+(\d+)", session_line)
    session_number = int(num_match.group(1)) if num_match else 0

    return year, semester, session_number


def _split_question_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split CSV lines into (question_text, block_lines) tuples."""
    question_starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^Question \d+,", stripped):
            # Extract question text (everything after "Question N,")
            q_text = stripped.split(",", 1)[1] if "," in stripped else ""
            question_starts.append((i, q_text))

    blocks = []
    for idx, (start, q_text) in enumerate(question_starts):
        end = question_starts[idx + 1][0] if idx + 1 < len(question_starts) else len(lines)
        blocks.append((q_text, lines[start:end]))

    return blocks


def _derive_question_label(question_text: str) -> str:
    """Derive a short label from the full question text."""
    for pattern, label in _LABEL_PATTERNS:
        if pattern.search(question_text):
            return label
    return question_text[:50]


def _extract_summary_totals(
    block_lines: list[str],
) -> dict[str, float]:
    """Extract Total Points per student from the Summary Statistics section.

    Returns dict mapping recipient_email → total_points.
    """
    totals: dict[str, float] = {}

    # Find "Summary Statistics" line
    summary_start = None
    directed_start = None
    for i, line in enumerate(block_lines):
        if "Summary Statistics" in line:
            summary_start = i
        if "Giver's Name" in line:
            directed_start = i
            break

    if summary_start is None or directed_start is None:
        return totals

    # Parse summary rows between header and directed section
    # Header: Team,Recipient,Recipient Email,Total Points,Average Points,Points Received
    header_line_idx = None
    for i in range(summary_start, directed_start):
        if "Total Points" in block_lines[i]:
            header_line_idx = i
            break

    if header_line_idx is None:
        return totals

    reader = csv.reader(block_lines[header_line_idx + 1 : directed_start])
    for row in reader:
        if len(row) < 4 or not row[0].strip():
            continue
        email = row[2].strip()
        try:
            total = float(row[3].strip())
            totals[email] = total
        except (ValueError, IndexError):
            continue

    return totals


def _extract_directed_data(
    block_lines: list[str],
) -> list[tuple[str, str, str, str, str, float]]:
    """Extract directed giver→recipient scores from the directed data section.

    Returns list of (team, giver_name, giver_email, recip_name, recip_email, score).
    """
    # Find "Giver's Name" header
    directed_start = None
    for i, line in enumerate(block_lines):
        if "Giver's Name" in line:
            directed_start = i
            break

    if directed_start is None:
        return []

    rows: list[tuple[str, str, str, str, str, float]] = []
    reader = csv.reader(block_lines[directed_start + 1 :])

    for row in reader:
        if len(row) < 7 or not row[0].strip():
            continue

        team = row[0].strip()
        giver_name = row[1].strip()
        giver_email = row[2].strip()
        recip_name = row[4].strip()
        recip_email = row[5].strip()
        score_str = row[6].strip()

        if score_str in ("No Response", "Not Submitted", "N/A", ""):
            rows.append((team, giver_name, giver_email, recip_name, recip_email, float("nan")))
            continue

        try:
            score = float(score_str)
        except ValueError:
            # Non-numeric (e.g., Q1's "Equal share + 5%") — skip
            continue

        rows.append((team, giver_name, giver_email, recip_name, recip_email, score))

    return rows


def _build_matrices(
    directed_rows: list[tuple[str, str, str, str, str, float]],
    summary_totals: dict[str, float],
    team_meta: dict,
) -> dict[tuple[str, str], ScoreMatrix]:
    """Group directed rows by team and construct ScoreMatrix objects."""
    # Group rows by team
    teams: dict[str, list[tuple[str, str, str, str, float]]] = {}
    for team, giver_name, giver_email, recip_name, recip_email, score in directed_rows:
        teams.setdefault(team, []).append(
            (giver_name, giver_email, recip_name, recip_email, score)
        )

    result: dict[tuple[str, str], ScoreMatrix] = {}
    label = team_meta["question_label"]

    for team_name, rows in teams.items():
        sm = _build_team_matrix(team_name, rows, summary_totals, team_meta)
        if sm is not None:
            result[(team_name, label)] = sm

    return result


def _build_team_matrix(
    team_name: str,
    rows: list[tuple[str, str, str, str, float]],
    summary_totals: dict[str, float],
    team_meta: dict,
) -> ScoreMatrix | None:
    """Build a ScoreMatrix for a single team.

    All students (including non-submitters) are kept in the N×N matrix.
    Non-submitter columns contain NaN to faithfully represent missing data.
    Each model decides how to handle NaN values.
    Teams with ≥50% non-submitters are dropped entirely.
    """
    # Collect all unique students (by email) and identify non-submitters
    all_emails: set[str] = set()
    email_to_name: dict[str, str] = {}

    for giver_name, giver_email, recip_name, recip_email, score in rows:
        all_emails.add(giver_email)
        all_emails.add(recip_email)
        email_to_name[giver_email] = giver_name
        email_to_name[recip_email] = recip_name

    # Identify non-submitting raters: all their scores are NaN
    giver_scores: dict[str, list[float]] = {}
    for _, giver_email, _, _, score in rows:
        giver_scores.setdefault(giver_email, []).append(score)

    non_submitters: set[str] = set()
    for email, scores in giver_scores.items():
        if all(np.isnan(s) for s in scores):
            non_submitters.add(email)
            logger.warning(
                "Non-submitting rater %s (%s) in team '%s' — column will be NaN",
                email_to_name.get(email, "?"),
                email,
                team_name,
            )

    total_students = len(all_emails)
    n_missing = len(non_submitters)

    # Drop team if ≥50% missing
    if total_students > 0 and n_missing / total_students >= 0.5:
        logger.warning(
            "Dropping team '%s': %d/%d raters missing (≥50%%)",
            team_name,
            n_missing,
            total_students,
        )
        return None

    # Build student list with ALL students, sorted by email
    all_sorted_emails = sorted(all_emails)
    n = len(all_sorted_emails)
    email_to_idx = {e: i for i, e in enumerate(all_sorted_emails)}

    students = [
        StudentInfo(name=email_to_name.get(e, ""), email=e, index=i)
        for i, e in enumerate(all_sorted_emails)
    ]

    excluded = [
        StudentInfo(
            name=email_to_name.get(e, ""),
            email=e,
            index=email_to_idx[e],
        )
        for e in sorted(non_submitters)
    ]

    # Build N×N matrix: NaN for non-submitter columns, real values elsewhere
    matrix = np.full((n, n), np.nan, dtype=float)
    for _, giver_email, _, recip_email, score in rows:
        j = email_to_idx.get(giver_email)
        i = email_to_idx.get(recip_email)
        if i is None or j is None:
            continue
        if giver_email in non_submitters:
            # Column stays NaN — faithfully represents "No Response"
            continue
        if np.isnan(score):
            continue
        matrix[i][j] = score

    # Point total validation (only for submitters — non-submitter columns are NaN)
    submitter_indices = [
        email_to_idx[e] for e in all_sorted_emails if e not in non_submitters
    ]
    col_sums = np.nansum(matrix[:, submitter_indices], axis=0)
    median_sum = float(np.median(col_sums))
    for idx, j in enumerate(submitter_indices):
        email = all_sorted_emails[j]
        if abs(col_sums[idx] - median_sum) > 1.0:
            logger.warning(
                "Point total mismatch for rater %s in team '%s': "
                "expected ~%.0f (team median), got %.0f",
                email,
                team_name,
                median_sum,
                col_sums[idx],
            )

    # Cross-check with summary stats (row sums, NaN-aware)
    for i, email in enumerate(all_sorted_emails):
        row_sum = float(np.nansum(matrix[i, :]))
        if email in summary_totals:
            expected_total = summary_totals[email]
            if abs(row_sum - expected_total) > 1.0:
                logger.warning(
                    "Summary cross-check mismatch for %s in team '%s': "
                    "matrix row sum=%.1f, summary Total Points=%.1f",
                    email,
                    team_name,
                    row_sum,
                    expected_total,
                )

    sm = ScoreMatrix(
        matrix=matrix,
        team_name=team_name,
        question_label=team_meta["question_label"],
        year=team_meta["year"],
        semester=team_meta["semester"],
        session_number=team_meta["session_number"],
        students=students,
        excluded_students=excluded,
    )

    return sm
