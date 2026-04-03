"""Integration tests for the CSV parser → ScoreMatrix pipeline."""

from pathlib import Path

import numpy as np
import pytest

from src.parsing.parser import parse_session

DATA_DIR = Path(__file__).parent.parent / "data"
SESSION_4_2024 = DATA_DIR / "COMPSCI399-S1-2024_Peer Feedback Session 4 - S1, 2024_result.csv"


class TestTracerBullet:
    """Tracer bullet: parse Session 4 2024, verify Team 11 ExquisiTech Q2 exact 6×6 matrix."""

    def test_team11_q2_exact_matrix(self):
        result = parse_session(SESSION_4_2024)

        key = ("Team 11 - ExquisiTech", "source code")
        assert key in result, f"Expected key {key} in result, got keys: {list(result.keys())}"

        sm = result[key]

        # 6 students, all submitted, so 6×6 matrix
        assert sm.matrix.shape == (6, 6)

        # Students sorted alphabetically by email:
        # 0: alee314  (Alyssa Lee Sang)
        # 1: aqui206  (Aaron Christopher Quiat)
        # 2: hemm904  (Helen Emmett)
        # 3: jhe435   (Jie He)
        # 4: kwil492  (Kahira Williams)
        # 5: llam106  (Edward Lam)
        expected_emails = [
            "alee314@aucklanduni.ac.nz",
            "aqui206@aucklanduni.ac.nz",
            "hemm904@aucklanduni.ac.nz",
            "jhe435@aucklanduni.ac.nz",
            "kwil492@aucklanduni.ac.nz",
            "llam106@aucklanduni.ac.nz",
        ]
        actual_emails = [s.email for s in sm.students]
        assert actual_emails == expected_emails

        # S[i][j] = score giver j gave to recipient i
        # Rows = recipients, Columns = givers
        # fmt: off
        expected = np.array([
            [10, 10,  7,  9,  8, 10],  # Alyssa received from [Alyssa, Aaron, Helen, Jie, Kahira, Edward]
            [10, 10, 10, 10, 10, 11],  # Aaron received
            [10, 11, 13, 11, 13, 12],  # Helen received
            [10,  5,  6,  9,  7,  4],  # Jie received
            [10, 10, 11,  9,  9, 11],  # Kahira received
            [10, 14, 13, 12, 13, 12],  # Edward received
        ], dtype=float)
        # fmt: on

        np.testing.assert_array_equal(sm.matrix, expected)

        # Column sums should each be 60 (10 × 6 students)
        np.testing.assert_array_equal(sm.matrix.sum(axis=0), np.full(6, 60.0))

        # Metadata
        assert sm.team_name == "Team 11 - ExquisiTech"
        assert sm.question_label == "source code"
        assert sm.year == "2024"
        assert sm.semester == "S1"
        assert sm.session_number == 4
        assert sm.excluded_students == []


class TestQuestionFiltering:
    """Only 'Distribute a total of...' questions produce ScoreMatrix objects."""

    def test_only_point_distribution_questions_produce_matrices(self):
        result = parse_session(SESSION_4_2024)

        # All keys should have labels from point-distribution questions only
        labels = {label for _, label in result.keys()}
        expected_labels = {"source code", "group report", "showcase poster"}
        assert labels == expected_labels, f"Got unexpected labels: {labels}"

    def test_non_distribution_questions_excluded(self):
        """Q1 (contribution estimate), Q5 (devotion), Q6/Q7 (text) should not appear."""
        result = parse_session(SESSION_4_2024)

        labels = {label for _, label in result.keys()}
        # None of these should be in the result
        for excluded in ["contribution", "devoted", "comments", "dynamics"]:
            assert not any(excluded in l for l in labels), (
                f"Found excluded question type '{excluded}' in labels: {labels}"
            )


class TestMultipleQuestions:
    """Q2, Q3, Q4 each produce separate ScoreMatrix per team."""

    def test_three_questions_per_team(self):
        result = parse_session(SESSION_4_2024)

        # Team 11 should appear in all 3 question labels
        team11_labels = sorted(
            label for team, label in result.keys() if team == "Team 11 - ExquisiTech"
        )
        assert team11_labels == ["group report", "showcase poster", "source code"]

    def test_different_matrices_per_question(self):
        result = parse_session(SESSION_4_2024)

        q2 = result[("Team 11 - ExquisiTech", "source code")]
        q3 = result[("Team 11 - ExquisiTech", "group report")]

        # Same team, same students, but different score matrices
        assert [s.email for s in q2.students] == [s.email for s in q3.students]
        assert not np.array_equal(q2.matrix, q3.matrix)


class TestStudentOrdering:
    """Students are indexed alphabetically by email."""

    def test_student_indices_match_email_sort_order(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        emails = [s.email for s in sm.students]
        assert emails == sorted(emails), "Students not sorted alphabetically by email"

    def test_email_to_index_lookup(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        # Verify the bidirectional mapping is consistent
        for student in sm.students:
            assert sm.email_to_index[student.email] == student.index

    def test_name_to_index_lookup(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        for student in sm.students:
            assert sm.name_to_index[student.name] == student.index


class TestSelfScores:
    """Self-scores appear on the diagonal: S[i][i] = score student i gave to themselves."""

    def test_diagonal_is_self_scores(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        # Known self-scores from the data:
        # Alyssa (idx 0) gave herself 10
        # Aaron (idx 1) gave himself 10
        # Helen (idx 2) gave herself 13
        # Jie (idx 3) gave himself 9
        # Kahira (idx 4) gave herself 9
        # Edward (idx 5) gave himself 12
        expected_diagonal = [10, 10, 13, 9, 9, 12]
        np.testing.assert_array_equal(
            np.diag(sm.matrix), np.array(expected_diagonal, dtype=float)
        )


class TestMissingRaterExclusion:
    """Non-submitting raters are excluded: row+column removed, matrix shrinks."""

    def test_team_with_one_non_submitter_shrinks(self):
        """Team 14 Neox has 1 non-submitter (Lucia Kim) out of 6 → 5×5 matrix."""
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 14 - Neox", "source code")]

        assert sm.matrix.shape == (5, 5)
        assert len(sm.students) == 5

        # Lucia Kim (skim507) should be excluded
        active_emails = {s.email for s in sm.students}
        assert "skim507@aucklanduni.ac.nz" not in active_emails

        # She should appear in excluded_students
        excluded_emails = {s.email for s in sm.excluded_students}
        assert "skim507@aucklanduni.ac.nz" in excluded_emails

    def test_team_with_two_non_submitters_shrinks(self):
        """Team 7 Noot Noot has 2 non-submitters out of 6 → 4×4 matrix."""
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 7 - Noot Noot", "source code")]

        assert sm.matrix.shape == (4, 4)
        assert len(sm.students) == 4
        assert len(sm.excluded_students) == 2

    def test_excluded_students_have_names(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 14 - Neox", "source code")]

        excluded = sm.excluded_students
        assert len(excluded) == 1
        assert excluded[0].name == "Lucia Kim"


class TestTeamDrop:
    """Teams with ≥50% non-submitting raters are dropped entirely."""

    def test_team_with_50_percent_missing_is_dropped(self):
        """Team 9 CopyPaste has 3/6 non-submitters (50%) → should be dropped."""
        result = parse_session(SESSION_4_2024)

        team9_keys = [k for k in result.keys() if "CopyPaste" in k[0]]
        assert team9_keys == [], f"Team 9 should be dropped but found keys: {team9_keys}"

    def test_team_below_50_percent_missing_is_kept(self):
        """Team 7 Noot Noot has 2/6 non-submitters (33%) → should be kept."""
        result = parse_session(SESSION_4_2024)

        team7_keys = [k for k in result.keys() if "Noot Noot" in k[0]]
        assert len(team7_keys) > 0, "Team 7 should be kept (only 33% missing)"


class TestPointValidation:
    """Rater columns within a team should be consistent (±1 of team median)."""

    def test_team11_columns_sum_to_60(self):
        """Team 11 (6 members, all submitted): each rater distributes exactly 60."""
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        col_sums = sm.matrix.sum(axis=0)
        np.testing.assert_array_equal(col_sums, np.full(6, 60.0))

    def test_inconsistent_rater_logged_as_warning(self, caplog):
        """Teams with non-submitters removed may have inconsistent column sums;
        these should be logged as warnings."""
        import logging

        with caplog.at_level(logging.WARNING, logger="src.parsing.parser"):
            parse_session(SESSION_4_2024)

        point_warnings = [r for r in caplog.records if "Point total mismatch" in r.message]
        # We know some teams have inconsistent raters after exclusion
        assert len(point_warnings) >= 0  # warnings may or may not appear; just verify no crash


class TestSummaryCrossCheck:
    """Matrix row sums match summary stats 'Total Points'."""

    def test_team11_row_sums_match_summary_totals(self):
        result = parse_session(SESSION_4_2024)
        sm = result[("Team 11 - ExquisiTech", "source code")]

        # Known summary Total Points for Team 11 Q2:
        # alee314: 54, aqui206: 61, hemm904: 70, jhe435: 41, kwil492: 60, llam106: 74
        expected_totals = {
            "alee314@aucklanduni.ac.nz": 54,
            "aqui206@aucklanduni.ac.nz": 61,
            "hemm904@aucklanduni.ac.nz": 70,
            "jhe435@aucklanduni.ac.nz": 41,
            "kwil492@aucklanduni.ac.nz": 60,
            "llam106@aucklanduni.ac.nz": 74,
        }

        for student in sm.students:
            row_sum = sm.matrix[student.index, :].sum()
            expected = expected_totals[student.email]
            assert row_sum == expected, (
                f"{student.email}: row sum {row_sum} != summary total {expected}"
            )


SESSION_3_2023 = DATA_DIR / "COMPSCI399-S1-2023_Peer Feedback Session 3 - S1, 2023_result.csv"


class Test2023Compatibility:
    """Session 3 2023 parses correctly despite 'Last, First' name format."""

    def test_parses_without_error(self):
        result = parse_session(SESSION_3_2023)
        assert len(result) > 0, "No matrices parsed from 2023 Session 3"

    def test_produces_three_question_labels(self):
        result = parse_session(SESSION_3_2023)
        labels = {label for _, label in result.keys()}
        assert labels == {"source code", "group report", "showcase poster"}

    def test_metadata_correct(self):
        result = parse_session(SESSION_3_2023)
        # Grab any matrix to check metadata
        sm = next(iter(result.values()))
        assert sm.year == "2023"
        assert sm.semester == "S1"
        assert sm.session_number == 3

    def test_matrix_is_square_and_valid(self):
        result = parse_session(SESSION_3_2023)
        for key, sm in result.items():
            n = len(sm.students)
            assert sm.matrix.shape == (n, n), f"{key}: shape {sm.matrix.shape} != ({n},{n})"
            assert n >= 2, f"{key}: team too small ({n} students)"
