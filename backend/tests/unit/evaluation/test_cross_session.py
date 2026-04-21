"""Unit tests for CoherenceEngine.compute_cross_session() (B5).

Task 4.6: Test cases:
  - First session (empty historical) → None
  - 3 prior sessions with improving pattern → score > 50
  - Regression detected (lower n3_ratio) → penalised
  - Full improvement → 100
  - Full regression → 0
  - Mixed improvements/regressions → intermediate score
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.features.evaluation.coherence import CoherenceEngine, SessionPattern
from app.features.evaluation.rubric import RubricConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _engine() -> CoherenceEngine:
    return CoherenceEngine(RubricConfig())


def _pattern(
    n1_ratio: float = 0.3,
    n3_ratio: float = 0.2,
    exploratory_prompt_ratio: float = 0.6,
    has_post_tutor_verification: bool = True,
    qe_score: float | None = 75.0,
) -> SessionPattern:
    return SessionPattern(
        n1_ratio=n1_ratio,
        n3_ratio=n3_ratio,
        exploratory_prompt_ratio=exploratory_prompt_ratio,
        has_post_tutor_verification=has_post_tutor_verification,
        qe_score=qe_score,
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCrossSessionEdgeCases:
    def test_no_historical_returns_none(self) -> None:
        """First session has no history — should return None."""
        engine = _engine()
        current = _pattern()
        result = engine.compute_cross_session(current, [])
        assert result is None

    def test_single_historical_session(self) -> None:
        """Works with a single prior session."""
        engine = _engine()
        current = _pattern()
        historical = [_pattern()]
        result = engine.compute_cross_session(current, historical)
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")

    def test_five_historical_sessions(self) -> None:
        """Works with 5 prior sessions (the max)."""
        engine = _engine()
        current = _pattern()
        historical = [_pattern() for _ in range(5)]
        result = engine.compute_cross_session(current, historical)
        assert result is not None


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------


class TestCrossSessionRegression:
    def test_lower_n3_ratio_penalised(self) -> None:
        """If current n3_ratio is below historical mean, score should be lower than baseline."""
        engine = _engine()
        # Historical: consistently good n3_ratio
        historical = [
            _pattern(n3_ratio=0.4),
            _pattern(n3_ratio=0.4),
            _pattern(n3_ratio=0.4),
        ]
        # Current: n3 regresses, everything else matches
        current_regression = _pattern(n3_ratio=0.1)
        current_stable = _pattern(n3_ratio=0.4)

        score_regression = engine.compute_cross_session(current_regression, historical)
        score_stable = engine.compute_cross_session(current_stable, historical)

        assert score_regression is not None
        assert score_stable is not None
        assert score_regression < score_stable

    def test_full_regression_score_is_zero(self) -> None:
        """All four dimensions regress → score approaches 0."""
        engine = _engine()
        historical = [
            _pattern(n1_ratio=0.5, n3_ratio=0.5, exploratory_prompt_ratio=0.8, has_post_tutor_verification=True),
            _pattern(n1_ratio=0.5, n3_ratio=0.5, exploratory_prompt_ratio=0.8, has_post_tutor_verification=True),
        ]
        current = _pattern(
            n1_ratio=0.0,
            n3_ratio=0.0,
            exploratory_prompt_ratio=0.0,
            has_post_tutor_verification=False,
        )
        result = engine.compute_cross_session(current, historical)
        assert result is not None
        # base 50 - 4*12.5 = 0
        assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# Improvement
# ---------------------------------------------------------------------------


class TestCrossSessionImprovement:
    def test_full_improvement_score_is_100(self) -> None:
        """All four dimensions improve → score is 100.

        Historical must have has_post_tutor_verification=True for the verification
        dimension to grant a bonus when current maintains it.
        """
        engine = _engine()
        # Historical: poor engagement but DID have post-tutor verification
        historical = [
            _pattern(n1_ratio=0.1, n3_ratio=0.1, exploratory_prompt_ratio=0.1, has_post_tutor_verification=True),
        ]
        current = _pattern(
            n1_ratio=0.9,
            n3_ratio=0.9,
            exploratory_prompt_ratio=0.9,
            has_post_tutor_verification=True,
        )
        result = engine.compute_cross_session(current, historical)
        assert result is not None
        # n1 up, n3 up, exploratory up → +12.5 each; verification maintained → +12.5
        # base 50 + 4*12.5 = 100
        assert result == Decimal("100.00")

    def test_equal_pattern_returns_100(self) -> None:
        """When current exactly matches historical mean, all dimensions 'maintained'."""
        engine = _engine()
        p = _pattern(n1_ratio=0.3, n3_ratio=0.3, exploratory_prompt_ratio=0.5, has_post_tutor_verification=True)
        historical = [p, p, p]
        result = engine.compute_cross_session(p, historical)
        assert result is not None
        # All >= comparisons pass → 50 + 4*12.5 = 100
        assert result == Decimal("100.00")


# ---------------------------------------------------------------------------
# Mixed outcomes
# ---------------------------------------------------------------------------


class TestCrossSessionMixed:
    def test_two_improved_two_regressed(self) -> None:
        """Two dimensions improve, two regress → score == 50 (base, no net change)."""
        engine = _engine()
        historical = [
            _pattern(n1_ratio=0.3, n3_ratio=0.3, exploratory_prompt_ratio=0.5, has_post_tutor_verification=True),
        ]
        # n1 up, exploratory up; n3 down, verification down
        current = _pattern(
            n1_ratio=0.5,
            n3_ratio=0.1,
            exploratory_prompt_ratio=0.9,
            has_post_tutor_verification=False,
        )
        result = engine.compute_cross_session(current, historical)
        assert result is not None
        # +12.5 +12.5 -12.5 -12.5 → 50
        assert result == Decimal("50.00")

    def test_no_historical_verification_no_bonus_or_penalty(self) -> None:
        """When historical sessions never had post-tutor verification, no penalty if current lacks it."""
        engine = _engine()
        historical = [
            _pattern(n1_ratio=0.3, n3_ratio=0.3, exploratory_prompt_ratio=0.5, has_post_tutor_verification=False),
            _pattern(n1_ratio=0.3, n3_ratio=0.3, exploratory_prompt_ratio=0.5, has_post_tutor_verification=False),
        ]
        current = _pattern(
            n1_ratio=0.3,
            n3_ratio=0.3,
            exploratory_prompt_ratio=0.5,
            has_post_tutor_verification=False,
        )
        result = engine.compute_cross_session(current, historical)
        assert result is not None
        # n1/n3/exploratory all maintained (+12.5 each), verification: no history no penalty
        # 50 + 12.5 + 12.5 + 12.5 = 87.5
        assert result == Decimal("87.50")

    def test_result_clamped_to_0_100(self) -> None:
        """Score never exceeds 100 or goes below 0."""
        engine = _engine()
        historical = [_pattern()]
        current = _pattern(n1_ratio=10.0, n3_ratio=10.0, exploratory_prompt_ratio=10.0)

        result = engine.compute_cross_session(current, historical)
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")
