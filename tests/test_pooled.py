"""Tests for the pooled team-level cascade (handoff-11 B).

Guards: the B1 refactor did not move the 4c faction test; the pooled lane reads
an N=4 team the per-matrix lane cannot (the contribution); reproducibility; and
graceful handling of a team with a single readable question.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.attacks.synthetic import generate_team
from src.dynamics2 import contested, gates, pooled, ranks


def _team_items(n: int, seed: int, contributions=None, *, nq: int = 3, profile="reliable"):
    """nq question-matrices for one team (same members, independent noise)."""
    items = []
    for q in range(nq):
        t = generate_team(n, seed + 1000 * q, profile=profile,
                          contributions=contributions, include_self=True, mu0=10.0)
        emails = [s.email for s in t.score_matrix.students]
        items.append((emails, ranks.prepare_matrix(t.score_matrix)))
    return items


class TestPoolingPrimitiveRefactor:
    def test_pooled_tau_matrix_matches_contested_usage(self):
        # contested.py imports the same primitive; the two must be identical.
        assert contested.pooled_tau_matrix is pooled.pooled_tau_matrix

    def test_faction_test_still_runs_on_pooled_primitive(self):
        items = _team_items(5, 1)
        row = contested.pooled_faction_test(items, key=("csv", "team"), n_perm=50)
        assert row.n_raters >= 0
        assert row.category in {"too few raters", "unstructured", "lone deviant",
                                "structured"}


class TestN4Contribution:
    def test_pooled_reads_n4_freerider_that_permatrix_cannot(self):
        # THE contribution: an N=4 team is Silent-incomparable per matrix (raters
        # share only 2 recipients < 3), but pooling 3 questions clears the bar and
        # a large planted free-rider is recovered.
        c = np.array([2.0, 10.0, 10.0, 10.0])   # member 0 is a stark free-rider
        items = _team_items(4, 700, contributions=c)

        # Per-matrix: every N=4 question is structurally incomparable.
        per_matrix_states = [gates.classify_matrix(mat, ("k", str(qi), "q"), n_perm=200).state
                             for qi, (_, mat) in enumerate(items)]
        assert all(s == gates.SILENT_INCOMPARABLE for s in per_matrix_states)

        # Pooled: comparable, and reads a bottom standout on member 0.
        ps = pooled.classify_team(items, key=("k", "team"), n_perm=500)
        assert np.isfinite(ps.mean_tau)          # the bar is cleared by pooling
        cons = pooled.pooled_consensus(items)
        bottom = min(cons, key=cons.get)
        assert bottom == items[0][0][0]          # member 0 has the lowest consensus


class TestPooledNullCalibration:
    def test_even_team_is_not_a_standout(self):
        # A genuinely equal team must not be flagged as a standout by the pooled lane.
        items = _team_items(6, 21, contributions=np.full(6, 10.0))
        ps = pooled.classify_team(items, key=("k", "even"), n_perm=500)
        assert ps.state not in {gates.ONE_AT_BOTTOM, gates.ONE_AT_TOP, gates.BOTH_ENDS}


class TestReproducibility:
    def test_same_key_same_state(self):
        items = _team_items(5, 5, contributions=np.array([3.0, 10, 10, 10, 10]))
        a = pooled.classify_team(items, key=("k", "t"), n_perm=300)
        b = pooled.classify_team(items, key=("k", "t"), n_perm=300)
        assert (a.state, a.p_tau, a.p_bot) == (b.state, b.p_tau, b.p_bot)


class TestDegenerateInputs:
    def test_single_readable_question_does_not_crash(self):
        # Two flat (unreadable) questions + one real one: falls back sanely.
        good = _team_items(5, 9, contributions=np.array([3.0, 10, 10, 10, 10]), nq=1)[0]
        flat_mat = np.full((5, 5), 5.0)
        np.fill_diagonal(flat_mat, np.nan)
        emails = good[0]
        items = [good, (emails, flat_mat), (emails, flat_mat.copy())]
        ps = pooled.classify_team(items, key=("k", "t"), n_perm=200)
        assert ps.state in {gates.SILENT_FLAT, gates.SILENT_LONE,
                            gates.SILENT_INCOMPARABLE, gates.CONTESTED,
                            gates.NO_STANDOUT, gates.ONE_AT_BOTTOM,
                            gates.ONE_AT_TOP, gates.BOTH_ENDS}

    def test_all_flat_team_is_silent(self):
        flat = np.full((5, 5), 5.0)
        np.fill_diagonal(flat, np.nan)
        emails = [f"s{i}@synthetic.team" for i in range(5)]
        items = [(emails, flat.copy()) for _ in range(3)]
        ps = pooled.classify_team(items, key=("k", "flat"), n_perm=100)
        assert ps.state == gates.SILENT_FLAT
