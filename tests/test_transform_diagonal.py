"""Diagonal-handling contract for the attack transforms (handoff-11 A4).

A transform models a change in how a rater rates *other people*. Unless the
attack is explicitly about the self-allocation, the diagonal (self-score) must
pass through unchanged. These tests exercise the CS399 form (populated diagonal,
as in the real corpus) — the path that WebPA, which reads self-scores, is
sensitive to and where the pre-handoff-11 code silently damaged the diagonal.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.attacks.synthetic import generate_team
from src.attacks.transforms import (
    single_outlier,
    targeted_downvote,
    uniform_inflation,
    zero_self,
)


def _cs399(n: int, seed: int):
    """A team in CS399 form: 10*N budget per rater, self-score populated."""
    return generate_team(n, seed, include_self=True).score_matrix


# Every transform, as a single-argument callable, for parametrised sweeps.
ALL_TRANSFORMS = {
    "uniform_inflation": uniform_inflation,
    "zero_self_full": lambda sm: zero_self(sm, full=True),
    "zero_self_partial": lambda sm: zero_self(sm, full=False),
    "targeted_downvote": targeted_downvote,
    "single_outlier": lambda sm: single_outlier(sm, rng=np.random.default_rng(0)),
}


class TestSingleOutlierDiagonal:
    def test_preserves_self_score_exactly(self):
        sm = _cs399(6, 3)
        before_diag = np.diag(sm.matrix).copy()
        atk = single_outlier(sm, outlier=2, rng=np.random.default_rng(0))
        np.testing.assert_array_equal(np.diag(atk.matrix), before_diag)

    def test_offdiagonal_nansum_conserved(self):
        sm = _cs399(6, 3)
        j = 2
        off = [i for i in range(6) if i != j]
        before = float(np.nansum(sm.matrix[off, j]))
        atk = single_outlier(sm, outlier=j, rng=np.random.default_rng(1))
        after = float(np.nansum(atk.matrix[off, j]))
        assert after == pytest.approx(before)

    def test_seed_reproducible_cs399(self):
        sm = _cs399(5, 4)
        a = single_outlier(sm, rng=np.random.default_rng(7)).matrix
        b = single_outlier(sm, rng=np.random.default_rng(7)).matrix
        np.testing.assert_array_equal(a, b)


class TestZeroSelfDiagonal:
    def test_awards_self_zero_when_present(self):
        # CS399 form: the colluders' self-scores are set to exactly 0.
        sm = _cs399(5, 8)
        atk = zero_self(sm, full=True)
        assert np.allclose(np.diag(atk.matrix), 0.0)

    def test_offdiagonal_inflated_not_diagonal(self):
        sm = _cs399(5, 8)
        j = 0
        off = [i for i in range(5) if i != j]
        before_off = sm.matrix[off, j].copy()
        atk = zero_self(sm, full=True).matrix
        assert np.all(atk[off, j] > before_off)   # peers inflated
        assert atk[j, j] == 0.0                    # self zeroed, not inflated

    def test_leaves_absent_self_score_nan(self):
        # Self-excluded synthetic form (diagonal NaN): nothing to zero.
        sm = generate_team(5, 8).score_matrix   # include_self=False
        atk = zero_self(sm, full=True).matrix
        assert np.all(np.isnan(np.diag(atk)))


class TestNoTransformDamagesDiagonal:
    @pytest.mark.parametrize("name", list(ALL_TRANSFORMS))
    def test_no_finite_diagonal_becomes_nan(self, name):
        # zero_self sets the diagonal to a finite 0 (documented); no transform
        # may turn a finite self-score into NaN.
        sm = _cs399(6, 5)
        finite_before = np.isfinite(np.diag(sm.matrix))
        atk = ALL_TRANSFORMS[name](sm).matrix
        finite_after = np.isfinite(np.diag(atk))
        assert np.all(finite_after[finite_before]), (
            f"{name} introduced a NaN into a previously-finite diagonal slot")

    @pytest.mark.parametrize("name", list(ALL_TRANSFORMS))
    def test_nonsubmitter_column_stays_all_nan(self, name):
        # A non-submitter (all-NaN column) is not a rater and must be untouched.
        sm = _cs399(6, 5)
        m = sm.matrix.copy()
        m[:, 4] = np.nan
        sm = sm.model_copy(update={"matrix": m})
        atk = ALL_TRANSFORMS[name](sm).matrix
        assert np.all(np.isnan(atk[:, 4]))
