"""Tests for the impartial-share IWF model and the self-inflation attack."""

import numpy as np
import pytest

from src.attacks.transforms import self_inflation, zero_self
from src.models.baseline import baseline_normalised
from src.models.impartial import impartial_share
from src.parsing.schemas import ScoreMatrix, StudentInfo


def _sm(matrix) -> ScoreMatrix:
    matrix = np.asarray(matrix, dtype=float)
    n = matrix.shape[0]
    return ScoreMatrix(
        matrix=matrix,
        team_name="Test Team",
        question_label="test",
        year="2024",
        semester="S1",
        session_number=1,
        students=[
            StudentInfo(name=f"Student {chr(65 + i)}",
                        email=f"s{chr(97 + i)}@test.ac.nz", index=i)
            for i in range(n)
        ],
        excluded_students=[],
    )


def _honest(n: int = 5) -> np.ndarray:
    return np.full((n, n), 10.0)


def _budget_matrix(rng: np.random.Generator, n: int) -> np.ndarray:
    """Random fixed-budget matrix: each rater (column) splits 10·n points."""
    m = rng.dirichlet(np.ones(n), size=n).T * 10 * n
    return np.round(m, 2)


class TestImpartialShare:

    def test_honest_team_is_neutral(self):
        res = impartial_share(_sm(_honest()))
        np.testing.assert_allclose(res.iwf_vector, 10.0)

    @pytest.mark.parametrize("n", [3, 4, 5, 6])
    def test_complete_matrix_mean_is_exactly_ten(self, n):
        rng = np.random.default_rng(n)
        for _ in range(20):
            res = impartial_share(_sm(_budget_matrix(rng, n)))
            assert res.iwf_vector.mean() == pytest.approx(10.0)

    def test_self_score_never_matters(self):
        m = _honest()
        a = impartial_share(_sm(m)).iwf_vector
        m[0, 0] = 99.0
        b = impartial_share(_sm(m)).iwf_vector
        np.testing.assert_allclose(a, b)

    @pytest.mark.parametrize("n", [4, 5, 6])
    def test_impartiality(self, n):
        """Nothing rater j reports can change j's own weight."""
        rng = np.random.default_rng(100 + n)
        for _ in range(50):
            m = _budget_matrix(rng, n)
            j = int(rng.integers(n))
            before = impartial_share(_sm(m)).iwf_vector[j]
            m[:, j] = _budget_matrix(rng, n)[:, j]  # j reports anything
            after = impartial_share(_sm(m)).iwf_vector[j]
            assert after == pytest.approx(before)

    def test_worked_example_self_inflation(self):
        """A gives self 30, peers 5 each (decisions.md 2026-10-11)."""
        m = _honest()
        m[:, 0] = [30, 5, 5, 5, 5]
        imp = impartial_share(_sm(m)).iwf_vector
        base = baseline_normalised(_sm(m)).iwf_vector
        np.testing.assert_allclose(imp, 10.0)
        assert base[0] == pytest.approx(11.111, abs=1e-3)

    def test_zero_self_full_and_partial_have_no_effect(self):
        rng = np.random.default_rng(7)
        sm = _sm(_budget_matrix(rng, 5))
        clean = impartial_share(sm).iwf_vector
        for full in (True, False):
            attacked = impartial_share(zero_self(sm, full=full)).iwf_vector
            np.testing.assert_allclose(attacked, clean)

    def test_non_submitter_is_rated_but_not_a_rater(self):
        m = _honest()
        m[:, 4] = np.nan  # student E submitted nothing
        m[0, 1] = 20.0    # B rates A highly
        res = impartial_share(_sm(m)).iwf_vector
        assert np.isfinite(res).all()
        assert res[0] > res[1]

    def test_rater_giving_peers_zero_is_ignored(self):
        m = _honest()
        m[:, 0] = [50, 0, 0, 0, 0]
        res = impartial_share(_sm(m)).iwf_vector
        np.testing.assert_allclose(res, 10.0)

    def test_student_nobody_rated_gets_nan(self):
        m = _honest(3)
        m[0, 1] = m[0, 2] = np.nan
        res = impartial_share(_sm(m)).iwf_vector
        assert np.isnan(res[0])


class TestSelfInflation:

    def test_budget_conserved_and_self_raised(self):
        rng = np.random.default_rng(3)
        sm = _sm(_budget_matrix(rng, 5))
        out = self_inflation(sm, inflater=2).matrix
        assert np.nansum(out[:, 2]) == pytest.approx(np.nansum(sm.matrix[:, 2]))
        assert out[2, 2] > sm.matrix[2, 2]
        np.testing.assert_array_equal(np.delete(out, 2, axis=1),
                                      np.delete(sm.matrix, 2, axis=1))

    def test_raises_inflater_under_2026_formula_only(self):
        sm = _sm(_honest())
        attacked = self_inflation(sm, inflater=0)
        assert baseline_normalised(attacked).iwf_vector[0] > 10.0
        np.testing.assert_allclose(impartial_share(attacked).iwf_vector, 10.0)

    def test_needs_a_self_score(self):
        m = _honest()
        np.fill_diagonal(m, np.nan)
        with pytest.raises(ValueError):
            self_inflation(_sm(m))
