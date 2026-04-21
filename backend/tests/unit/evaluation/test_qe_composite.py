"""Unit tests for the Qe composite (B9) — weighted N1-N4 average.

Tests cover:
  - All 4 levels present → weighted average
  - Only N4 present → Qe reflects only N4 weight (others treated as 0)
  - No events at all → None
  - Equal weights with scores [100, 0, 50, 75] → expected average
  - _compute_qe_n1, _compute_qe_n2, _compute_qe_n3 individual scoring
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.features.evaluation.rubric import QeWeightsConfig, RubricConfig
from app.features.evaluation.service import MetricsEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rubric(n1: float = 0.25, n2: float = 0.25, n3: float = 0.25, n4: float = 0.25) -> RubricConfig:
    return RubricConfig(qe_weights=QeWeightsConfig(n1=n1, n2=n2, n3=n3, n4=n4))


def _engine(n1: float = 0.25, n2: float = 0.25, n3: float = 0.25, n4: float = 0.25) -> MetricsEngine:
    return MetricsEngine(_make_rubric(n1=n1, n2=n2, n3=n3, n4=n4))


def _event(event_type: str, payload: dict | None = None, sequence_number: int = 1, n4_level: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        payload=payload or {},
        sequence_number=sequence_number,
        n4_level=n4_level,
    )


# ---------------------------------------------------------------------------
# _compute_qe_composite
# ---------------------------------------------------------------------------


class TestQeComposite:
    def test_all_four_levels_present_equal_weights(self) -> None:
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=Decimal("80"),
            qe_n2=Decimal("60"),
            qe_n3=Decimal("40"),
            qe_n4=Decimal("20"),
        )
        assert result is not None
        # (80 + 60 + 40 + 20) / 4 = 50
        assert result == Decimal("50.00")

    def test_only_n4_present_others_none(self) -> None:
        """When N1/N2/N3 are None (treated as 0), score reflects that penalisation."""
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=None,
            qe_n2=None,
            qe_n3=None,
            qe_n4=Decimal("100"),
        )
        assert result is not None
        # (0 + 0 + 0 + 100) * 0.25 / (4 * 0.25) = 25
        assert result == Decimal("25.00")

    def test_all_none_returns_none(self) -> None:
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=None,
            qe_n2=None,
            qe_n3=None,
            qe_n4=None,
        )
        assert result is None

    def test_equal_weights_specific_scores(self) -> None:
        """[100, 0, 50, 75] with equal weights → (100+0+50+75)/4 = 56.25."""
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=Decimal("100"),
            qe_n2=Decimal("0"),
            qe_n3=Decimal("50"),
            qe_n4=Decimal("75"),
        )
        assert result is not None
        assert result == Decimal("56.25")

    def test_custom_weights_favour_n4(self) -> None:
        engine = _engine(n1=0.1, n2=0.1, n3=0.1, n4=0.7)
        result = engine._compute_qe_composite(
            qe_n1=Decimal("0"),
            qe_n2=Decimal("0"),
            qe_n3=Decimal("0"),
            qe_n4=Decimal("100"),
        )
        assert result is not None
        # (0*0.1 + 0*0.1 + 0*0.1 + 100*0.7) / 1.0 = 70
        assert result == Decimal("70.00")

    def test_clamped_to_100(self) -> None:
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=Decimal("100"),
            qe_n2=Decimal("100"),
            qe_n3=Decimal("100"),
            qe_n4=Decimal("100"),
        )
        assert result == Decimal("100.00")

    def test_partial_none_treated_as_zero(self) -> None:
        """N2=None means 0 contribution; total weight still 1.0."""
        engine = _engine()
        result = engine._compute_qe_composite(
            qe_n1=Decimal("100"),
            qe_n2=None,
            qe_n3=Decimal("100"),
            qe_n4=Decimal("100"),
        )
        assert result is not None
        # (100 + 0 + 100 + 100) * 0.25 / 1.0 = 75
        assert result == Decimal("75.00")


# ---------------------------------------------------------------------------
# _compute_qe_n1
# ---------------------------------------------------------------------------


class TestQeN1:
    def test_no_events_returns_none(self) -> None:
        engine = _engine()
        assert engine._compute_qe_n1([]) is None

    def test_adequate_reading_and_reread(self) -> None:
        events = [
            _event("problem.reading_time", payload={"reading_duration_ms": 15000}),
            _event("problem.reread"),
        ]
        result = _engine()._compute_qe_n1(events)
        assert result == Decimal("100.00")

    def test_only_adequate_reading(self) -> None:
        events = [_event("problem.reading_time", payload={"reading_duration_ms": 11000})]
        result = _engine()._compute_qe_n1(events)
        assert result == Decimal("50.00")

    def test_reading_too_short_no_reread(self) -> None:
        events = [_event("problem.reading_time", payload={"reading_duration_ms": 5000})]
        result = _engine()._compute_qe_n1(events)
        assert result == Decimal("0.00")

    def test_only_reread(self) -> None:
        events = [_event("problem.reread")]
        result = _engine()._compute_qe_n1(events)
        assert result == Decimal("50.00")

    def test_no_relevant_events_returns_none(self) -> None:
        events = [_event("code.run", payload={"status": "success"})]
        result = _engine()._compute_qe_n1(events)
        assert result is None


# ---------------------------------------------------------------------------
# _compute_qe_n2
# ---------------------------------------------------------------------------


class TestQeN2:
    def test_no_events_returns_none(self) -> None:
        assert _engine()._compute_qe_n2([]) is None

    def test_pseudocode_only(self) -> None:
        events = [_event("pseudocode.written")]
        assert _engine()._compute_qe_n2(events) == Decimal("70.00")

    def test_planning_question_only(self) -> None:
        events = [
            _event(
                "tutor.question_asked",
                payload={"prompt_type": "exploratory", "n4_level": 1},
                n4_level=1,
            )
        ]
        assert _engine()._compute_qe_n2(events) == Decimal("30.00")

    def test_pseudocode_and_planning_question(self) -> None:
        events = [
            _event("pseudocode.written"),
            _event(
                "tutor.question_asked",
                payload={"prompt_type": "exploratory", "n4_level": 2},
                n4_level=2,
            ),
        ]
        # Clamped at 100
        assert _engine()._compute_qe_n2(events) == Decimal("100.00")

    def test_non_exploratory_tutor_question_not_counted(self) -> None:
        events = [
            _event(
                "tutor.question_asked",
                payload={"prompt_type": "verifier", "n4_level": 2},
                n4_level=2,
            )
        ]
        assert _engine()._compute_qe_n2(events) == Decimal("0.00")

    def test_no_relevant_events_returns_none(self) -> None:
        events = [_event("code.run")]
        assert _engine()._compute_qe_n2(events) is None


# ---------------------------------------------------------------------------
# _compute_qe_n3
# ---------------------------------------------------------------------------


class TestQeN3:
    def test_no_events_returns_none(self) -> None:
        assert _engine()._compute_qe_n3([]) is None

    def test_manual_test_only(self) -> None:
        events = [_event("test.manual_case")]
        result = _engine()._compute_qe_n3(events)
        assert result == Decimal("50.00")

    def test_post_tutor_runs_and_manual_test(self) -> None:
        events = [
            _event("tutor.response_received", sequence_number=1),
            _event("code.run", payload={"status": "success"}, sequence_number=2),
            _event("test.manual_case", sequence_number=3),
        ]
        result = _engine()._compute_qe_n3(events)
        # critical_eval = 100 (1/1 responses followed by run) → 100 * 0.5 = 50
        # manual_test → +50
        # total = 100
        assert result == Decimal("100.00")

    def test_no_manual_test_no_tutor_response_returns_none(self) -> None:
        events = [_event("code.run")]
        assert _engine()._compute_qe_n3(events) is None

    def test_post_tutor_runs_no_manual_test(self) -> None:
        events = [
            _event("tutor.response_received", sequence_number=1),
            _event("code.run", sequence_number=2),
        ]
        result = _engine()._compute_qe_n3(events)
        # critical_eval = 100 → * 0.5 = 50; no manual test
        assert result == Decimal("50.00")
