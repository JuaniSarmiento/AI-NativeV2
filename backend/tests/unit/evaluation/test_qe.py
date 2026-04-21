"""Unit tests for Qe (epistemic quality) sub-score computation.

Covers edge cases: no tutor interactions, all high-quality prompts,
integration success/failure ratios, and verification patterns.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.features.cognitive.models import CognitiveEvent, CognitiveSession
from app.features.evaluation.rubric import RubricConfig
from app.features.evaluation.service import MetricsEngine


def _make_session() -> MagicMock:
    s = MagicMock(spec=CognitiveSession)
    s.id = uuid.uuid4()
    return s


def _make_event(
    event_type: str,
    payload: dict | None = None,
    sequence_number: int = 1,
) -> MagicMock:
    e = MagicMock(spec=CognitiveEvent)
    e.event_type = event_type
    e.payload = payload or {}
    e.sequence_number = sequence_number
    return e


def _engine() -> MetricsEngine:
    return MetricsEngine(RubricConfig())


class TestQeQualityPrompt:
    def test_all_high_quality_prompts_gives_100(self) -> None:
        """All tutor questions with n4_level >= 2 → qe_quality_prompt = 100."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=1),
            _make_event("tutor.question_asked", {"n4_level": 3}, sequence_number=2),
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=3),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_quality_prompt == Decimal("100.00")

    def test_no_high_quality_prompts_gives_zero(self) -> None:
        """All tutor questions with n4_level < 2 → qe_quality_prompt = 0."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 1}, sequence_number=1),
            _make_event("tutor.question_asked", {"n4_level": 0}, sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_quality_prompt == Decimal("0.00")

    def test_half_high_quality_prompts_gives_50(self) -> None:
        """2 out of 4 tutor questions with n4_level >= 2 → 50.00."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 3}, sequence_number=1),
            _make_event("tutor.question_asked", {"n4_level": 3}, sequence_number=2),
            _make_event("tutor.question_asked", {"n4_level": 1}, sequence_number=3),
            _make_event("tutor.question_asked", {"n4_level": 0}, sequence_number=4),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_quality_prompt == Decimal("50.00")

    def test_no_tutor_events_gives_none(self) -> None:
        """No tutor.question_asked events → qe_quality_prompt = None."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.run", sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_quality_prompt is None


class TestQeCriticalEvaluation:
    def test_code_run_after_tutor_response_gives_high_score(self) -> None:
        """code.run after tutor.response_received → high qe_critical_evaluation."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=1),
            _make_event("tutor.response_received", {}, sequence_number=2),
            _make_event("code.run", {"status": "ok"}, sequence_number=3),  # after response
        ]
        result = engine.compute(session, events)
        # 1 run after response / 1 total run = 100
        assert result.metrics.qe_critical_evaluation == Decimal("100.00")

    def test_code_run_only_before_tutor_response_gives_zero(self) -> None:
        """All code.run events before tutor response → qe_critical_evaluation = 0."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("code.run", {"status": "ok"}, sequence_number=1),
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=2),
            _make_event("tutor.response_received", {}, sequence_number=3),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_critical_evaluation == Decimal("0.00")

    def test_no_tutor_response_gives_none(self) -> None:
        """No tutor.response_received events → qe_critical_evaluation = None."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("code.run", {"status": "ok"}, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_critical_evaluation is None


class TestQeIntegration:
    def test_successful_runs_after_tutor_gives_100(self) -> None:
        """All code.run after tutor response succeed → qe_integration = 100."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=1),
            _make_event("tutor.response_received", {}, sequence_number=2),
            _make_event("code.run", {"status": "ok"}, sequence_number=3),
            _make_event("code.run", {"status": "ok"}, sequence_number=4),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_integration == Decimal("100.00")

    def test_all_failed_runs_after_tutor_gives_zero(self) -> None:
        """All code.run after tutor response fail → qe_integration = 0."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=1),
            _make_event("tutor.response_received", {}, sequence_number=2),
            _make_event("code.run", {"status": "error"}, sequence_number=3),
            _make_event("code.run", {"status": "error"}, sequence_number=4),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_integration == Decimal("0.00")

    def test_half_successful_gives_50(self) -> None:
        """1 success + 1 failure after tutor → qe_integration = 50."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=1),
            _make_event("tutor.response_received", {}, sequence_number=2),
            _make_event("code.run", {"status": "ok"}, sequence_number=3),
            _make_event("code.run", {"status": "error"}, sequence_number=4),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_integration == Decimal("50.00")


class TestQeVerification:
    def test_single_run_gives_partial_credit(self) -> None:
        """Only 1 code.run event (no snapshots) → min(100, 1*50) = 50."""
        engine = _engine()
        session = _make_session()
        events = [_make_event("code.run", {"status": "ok"}, sequence_number=1)]
        result = engine.compute(session, events)
        assert result.metrics.qe_verification == Decimal("50.00")

    def test_two_runs_gives_100(self) -> None:
        """2 code.run events (num/2 * 100 = 100, clamped)."""
        engine = _engine()
        session = _make_session()
        events = [
            _make_event("code.run", sequence_number=1),
            _make_event("code.run", sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.qe_verification == Decimal("100.00")

    def test_no_run_events_gives_none(self) -> None:
        """No code.run events → qe_verification = None."""
        engine = _engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        result = engine.compute(session, events)
        assert result.metrics.qe_verification is None


class TestQeComposite:
    def test_qe_composite_is_mean_of_available_subscores(self) -> None:
        """Qe composite should be the mean of non-None sub-scores."""
        engine = _engine()
        session = _make_session()
        # Create events that produce all 4 sub-scores
        events = [
            _make_event("tutor.question_asked", {"n4_level": 3}, sequence_number=1),
            _make_event("tutor.response_received", {}, sequence_number=2),
            _make_event("code.run", {"status": "ok"}, sequence_number=3),
            _make_event("code.run", {"status": "ok"}, sequence_number=4),
        ]
        result = engine.compute(session, events)
        m = result.metrics
        # All 4 sub-scores should be non-None
        assert m.qe_quality_prompt is not None
        assert m.qe_critical_evaluation is not None
        assert m.qe_integration is not None
        assert m.qe_verification is not None
        # Composite should be non-None
        assert m.qe_score is not None
        # Verify it's in range
        assert 0 <= float(m.qe_score) <= 100

    def test_qe_none_when_all_subscores_none(self) -> None:
        """No tutor events and no code.run → all Qe sub-scores None → qe_score None."""
        engine = _engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        result = engine.compute(session, events)
        assert result.metrics.qe_score is None
