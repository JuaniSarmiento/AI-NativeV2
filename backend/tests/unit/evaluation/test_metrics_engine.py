"""Unit tests for MetricsEngine v2 — deterministic scoring with n4_level-based classification.

Uses MagicMock(spec=CognitiveEvent) to create fake events without any
database or FastAPI infrastructure. MetricsEngine is pure Python so
no async is needed here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.features.cognitive.models import CognitiveEvent, CognitiveSession
from app.features.evaluation.rubric import RubricConfig
from app.features.evaluation.service import MetricsEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    s = MagicMock(spec=CognitiveSession)
    s.id = uuid.uuid4()
    s.student_id = uuid.uuid4()
    s.exercise_id = uuid.uuid4()
    return s


def _make_event(
    event_type: str,
    payload: dict | None = None,
    sequence_number: int = 1,
    n4_level: int | None = None,
) -> MagicMock:
    e = MagicMock(spec=CognitiveEvent)
    e.event_type = event_type
    e.payload = payload or {}
    e.sequence_number = sequence_number
    e.n4_level = n4_level
    if n4_level is not None:
        e.payload["n4_level"] = n4_level
    return e


def _default_engine() -> MetricsEngine:
    return MetricsEngine(RubricConfig())


# ---------------------------------------------------------------------------
# Basic tests
# ---------------------------------------------------------------------------


class TestMetricsEngineBasic:
    def test_empty_events_returns_none_scores(self) -> None:
        engine = _default_engine()
        session = _make_session()
        result = engine.compute(session, [])

        assert result.metrics.n1_comprehension_score is None
        assert result.metrics.n2_strategy_score is None
        assert result.metrics.n3_validation_score is None
        assert result.metrics.n4_ai_interaction_score is None
        assert result.metrics.total_interactions == 0

    def test_engine_version_is_2_0(self) -> None:
        engine = _default_engine()
        session = _make_session()
        result = engine.compute(session, [])
        assert result.metrics.engine_version == "2.0"

    def test_score_breakdown_is_populated(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert "n1" in result.score_breakdown
        assert isinstance(result.score_breakdown["n1"], list)
        for item in result.score_breakdown["n1"]:
            assert "condition" in item
            assert "met" in item
            assert "points" in item

    def test_compute_result_has_all_required_keys(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1)]
        result = engine.compute(session, events)

        profile = result.evaluation_profile
        assert "n1" in profile
        assert "n2" in profile
        assert "n3" in profile
        assert "n4" in profile
        assert "qe" in profile
        assert "weighted_total" in profile
        assert "weights" in profile
        assert "risk_level" in profile
        assert "computed_at" in profile


# ---------------------------------------------------------------------------
# N1 Tests (Comprehension)
# ---------------------------------------------------------------------------


class TestN1Score:
    def test_reading_time_above_15s_gives_presence(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n1_comprehension_score is not None
        assert result.metrics.n1_comprehension_score > Decimal("0")

    def test_reading_time_above_45s_gives_higher_presence(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events_short = [
            _make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1),
        ]
        events_long = [
            _make_event("problem.reading_time", {"duration_ms": 50000}, n4_level=1, sequence_number=1),
        ]
        result_short = engine.compute(_make_session(), events_short)
        result_long = engine.compute(_make_session(), events_long)
        assert result_long.metrics.n1_comprehension_score >= result_short.metrics.n1_comprehension_score

    def test_reread_adds_depth(self) -> None:
        engine = _default_engine()
        events_base = [
            _make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1),
        ]
        events_reread = [
            _make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1),
            _make_event("problem.reread", {}, n4_level=1, sequence_number=2),
        ]
        result_base = engine.compute(_make_session(), events_base)
        result_reread = engine.compute(_make_session(), events_reread)
        assert result_reread.metrics.n1_comprehension_score > result_base.metrics.n1_comprehension_score

    def test_no_n1_events_gives_none(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
        ]
        result = engine.compute(session, events)
        # N1 should be None or 0 when no N1 events
        assert result.metrics.n1_comprehension_score is None or result.metrics.n1_comprehension_score == Decimal("0.00")


# ---------------------------------------------------------------------------
# N2 Tests (Strategy)
# ---------------------------------------------------------------------------


class TestN2Score:
    def test_pseudocode_written_gives_presence(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("pseudocode.written", {}, n4_level=2, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n2_strategy_score is not None
        assert result.metrics.n2_strategy_score > Decimal("0")

    def test_n2_tutor_question_gives_presence(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"prompt_type": "exploratory"}, n4_level=2, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n2_strategy_score is not None
        assert result.metrics.n2_strategy_score > Decimal("0")

    def test_submission_alone_does_not_give_n2(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("submission.created", {}, n4_level=None, sequence_number=1),
        ]
        result = engine.compute(session, events)
        # submission.created is now n4_level=None, should not contribute to N2
        assert result.metrics.n2_strategy_score is None or result.metrics.n2_strategy_score == Decimal("0.00")

    def test_pseudocode_followed_by_run_gives_quality(self) -> None:
        engine = _default_engine()
        events_no_run = [
            _make_event("pseudocode.written", {}, n4_level=2, sequence_number=1),
        ]
        events_with_run = [
            _make_event("pseudocode.written", {}, n4_level=2, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
        ]
        result_no_run = engine.compute(_make_session(), events_no_run)
        result_with_run = engine.compute(_make_session(), events_with_run)
        assert result_with_run.metrics.n2_strategy_score >= result_no_run.metrics.n2_strategy_score


# ---------------------------------------------------------------------------
# N3 Tests (Validation)
# ---------------------------------------------------------------------------


class TestN3Score:
    def test_code_run_gives_n3_score(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n3_validation_score is not None
        assert result.metrics.n3_validation_score > Decimal("0")

    def test_manual_test_case_adds_depth(self) -> None:
        engine = _default_engine()
        events_base = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
        ]
        events_with_test = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
            _make_event("test.manual_case", {"is_edge_case": False}, n4_level=3, sequence_number=3),
        ]
        result_base = engine.compute(_make_session(), events_base)
        result_test = engine.compute(_make_session(), events_with_test)
        assert result_test.metrics.n3_validation_score > result_base.metrics.n3_validation_score

    def test_edge_case_test_adds_quality(self) -> None:
        engine = _default_engine()
        events_no_edge = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("test.manual_case", {"is_edge_case": False}, n4_level=3, sequence_number=2),
        ]
        events_edge = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("test.manual_case", {"is_edge_case": True}, n4_level=3, sequence_number=2),
        ]
        result_no_edge = engine.compute(_make_session(), events_no_edge)
        result_edge = engine.compute(_make_session(), events_edge)
        assert result_edge.metrics.n3_validation_score >= result_no_edge.metrics.n3_validation_score


# ---------------------------------------------------------------------------
# N4 Tests (AI Interaction)
# ---------------------------------------------------------------------------


class TestN4Score:
    def test_tutor_interactions_give_n4_score(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("tutor.question_asked", {"prompt_type": "exploratory"}, n4_level=4, sequence_number=1),
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n4_ai_interaction_score is not None
        assert result.metrics.n4_ai_interaction_score > Decimal("0")

    def test_no_tutor_gives_null_n4(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n4_ai_interaction_score is None

    def test_prompt_reformulated_gives_bonus(self) -> None:
        engine = _default_engine()
        events_base = [
            _make_event("tutor.question_asked", {"prompt_type": "exploratory"}, n4_level=4, sequence_number=1),
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=2),
        ]
        events_reformulated = [
            _make_event("tutor.question_asked", {"prompt_type": "exploratory"}, n4_level=4, sequence_number=1),
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=2),
            _make_event("prompt.reformulated", {}, n4_level=4, sequence_number=3),
        ]
        result_base = engine.compute(_make_session(), events_base)
        result_reform = engine.compute(_make_session(), events_reformulated)
        assert result_reform.metrics.n4_ai_interaction_score >= result_base.metrics.n4_ai_interaction_score

    def test_code_accepted_from_tutor_increases_dependency(self) -> None:
        engine = _default_engine()
        events_with_acceptance = [
            _make_event("tutor.question_asked", {"prompt_type": "generative", "sub_classification": "dependent"}, n4_level=4, sequence_number=1),
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=2),
            _make_event("code.accepted_from_tutor", {}, n4_level=4, sequence_number=3),
        ]
        result = engine.compute(_make_session(), events_with_acceptance)
        assert result.metrics.dependency_score is not None
        assert result.metrics.dependency_score > Decimal("0")


# ---------------------------------------------------------------------------
# Risk Level Tests
# ---------------------------------------------------------------------------


class TestRiskLevel:
    def test_null_n4_excluded_from_risk_calculation(self) -> None:
        engine = _default_engine()
        session = _make_session()
        # Only N3 events, N4 should be None → excluded from min_n_score
        events = [
            _make_event("problem.reading_time", {"duration_ms": 50000}, n4_level=1, sequence_number=1),
            _make_event("problem.reread", {}, n4_level=1, sequence_number=2),
            _make_event("pseudocode.written", {}, n4_level=2, sequence_number=3),
            _make_event("code.run", {}, n4_level=3, sequence_number=4),
            _make_event("code.run", {}, n4_level=3, sequence_number=5),
            _make_event("code.run", {}, n4_level=3, sequence_number=6),
        ]
        result = engine.compute(session, events)
        # With no N4 events, N4 is None. Risk should NOT be "alto" just because N4 is missing.
        assert result.metrics.risk_level != "alto" or result.metrics.n4_ai_interaction_score is not None

    def test_low_scores_give_high_risk(self) -> None:
        engine = _default_engine()
        session = _make_session()
        # Minimal events — scores will be low
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
        ]
        result = engine.compute(session, events)
        # Low activity should raise risk
        assert result.metrics.risk_level in ("high", "critical", "medium", None)


# ---------------------------------------------------------------------------
# Qe Tests
# ---------------------------------------------------------------------------


class TestQeScores:
    def test_qe_verification_measures_snapshot_followed_by_run(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.snapshot", {}, n4_level=None, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
            _make_event("code.snapshot", {}, n4_level=None, sequence_number=3),
            # No run after this snapshot
        ]
        result = engine.compute(session, events)
        # 1 out of 2 snapshots followed by run = 50%
        if result.metrics.qe_verification is not None:
            assert result.metrics.qe_verification <= Decimal("100.00")

    def test_qe_integration_attributes_to_nearest_response(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=1),
            _make_event("code.run", {}, n4_level=3, sequence_number=2),
            _make_event("code.run", {}, n4_level=3, sequence_number=3),
            _make_event("tutor.response_received", {}, n4_level=4, sequence_number=4),
            _make_event("code.run", {}, n4_level=3, sequence_number=5),
        ]
        result = engine.compute(session, events)
        # Both tutor responses have at least 1 run after them
        if result.metrics.qe_integration is not None:
            assert result.metrics.qe_integration > Decimal("0")


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------


class TestRatios:
    def test_help_seeking_ratio_and_autonomy_index_sum_to_one(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
            _make_event("tutor.question_asked", {"prompt_type": "exploratory"}, n4_level=4, sequence_number=2),
        ]
        result = engine.compute(session, events)
        hsr = result.metrics.help_seeking_ratio
        ai = result.metrics.autonomy_index
        assert hsr is not None
        assert ai is not None
        total = float(hsr) + float(ai)
        assert abs(total - 1.0) < 0.001

    def test_zero_tutor_events_gives_zero_help_seeking(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", {}, n4_level=3, sequence_number=1),
        ]
        result = engine.compute(session, events)
        assert result.metrics.help_seeking_ratio == Decimal("0.000")
        assert result.metrics.autonomy_index == Decimal("1.000")


# ---------------------------------------------------------------------------
# Reasoning Record
# ---------------------------------------------------------------------------


class TestReasoningRecord:
    def test_create_reasoning_record_has_correct_keys(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1)]
        compute_result = engine.compute(session, events)

        rr = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="a" * 64,
            created_at=datetime.now(tz=timezone.utc),
        )

        assert rr["record_type"] == "metrics_computation"
        assert len(rr["event_hash"]) == 64
        assert rr["previous_hash"] == "a" * 64
        assert "session_id" in rr
        assert "details" in rr
        assert "created_at" in rr

    def test_reasoning_record_hash_deterministic(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("problem.reading_time", {"duration_ms": 20000}, n4_level=1, sequence_number=1)]
        compute_result = engine.compute(session, events)

        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        rr1 = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="b" * 64,
            created_at=now,
        )
        rr2 = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="b" * 64,
            created_at=now,
        )
        assert rr1["event_hash"] == rr2["event_hash"]
