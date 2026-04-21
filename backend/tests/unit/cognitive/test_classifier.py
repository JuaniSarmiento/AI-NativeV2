"""Unit tests for CognitiveEventClassifier."""
from __future__ import annotations

import pytest

from app.features.cognitive.classifier import ClassifiedEvent, CognitiveEventClassifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classifier() -> CognitiveEventClassifier:
    return CognitiveEventClassifier()


def _classify(raw_type: str, payload: dict | None = None) -> ClassifiedEvent | None:
    return _classifier().classify(raw_type, payload or {})


# ---------------------------------------------------------------------------
# Known event types from _EVENT_TYPE_MAPPING
# ---------------------------------------------------------------------------


def test_reads_problem_maps_to_n1() -> None:
    result = _classify("reads_problem")
    assert result is not None
    assert result.event_type == "reads_problem"
    assert result.n4_level == 1


def test_code_executed_maps_to_n3() -> None:
    result = _classify("code.executed", {"stdout": "hello"})
    assert result is not None
    assert result.event_type == "code.run"
    assert result.n4_level == 3


def test_code_execution_failed_maps_to_n3_same_canonical() -> None:
    """code.execution.failed and code.executed both map to code.run at N3."""
    result = _classify("code.execution.failed", {"error": "NameError"})
    assert result is not None
    assert result.event_type == "code.run"
    assert result.n4_level == 3


def test_code_snapshot_captured_maps_to_lifecycle() -> None:
    result = _classify("code.snapshot.captured", {"snapshot": "x = 1"})
    assert result is not None
    assert result.event_type == "code.snapshot"
    assert result.n4_level is None


def test_exercise_submitted_maps_to_lifecycle() -> None:
    result = _classify("exercise.submitted", {"submission_id": "abc"})
    assert result is not None
    assert result.event_type == "submission.created"
    assert result.n4_level is None


def test_tutor_session_started_maps_to_none_level() -> None:
    result = _classify("tutor.session.started")
    assert result is not None
    assert result.event_type == "session.started"
    assert result.n4_level is None


def test_tutor_session_ended_maps_to_none_level() -> None:
    result = _classify("tutor.session.ended")
    assert result is not None
    assert result.event_type == "session.closed"
    assert result.n4_level is None


def test_reflection_submitted_maps_to_lifecycle() -> None:
    result = _classify("reflection.submitted", {"text": "I learned..."})
    assert result is not None
    assert result.event_type == "reflection.submitted"
    assert result.n4_level is None


# ---------------------------------------------------------------------------
# Special case: tutor.interaction.completed split by role
# ---------------------------------------------------------------------------


def test_tutor_interaction_user_role_maps_to_question_asked() -> None:
    """role=user → student is asking → tutor.question_asked at N4."""
    result = _classify("tutor.interaction.completed", {"role": "user", "content": "?"})
    assert result is not None
    assert result.event_type == "tutor.question_asked"
    assert result.n4_level == 4


def test_tutor_interaction_assistant_role_maps_to_response_received() -> None:
    """role=assistant → tutor responding → tutor.response_received at N4."""
    result = _classify(
        "tutor.interaction.completed", {"role": "assistant", "content": "Hint..."}
    )
    assert result is not None
    assert result.event_type == "tutor.response_received"
    assert result.n4_level == 4


def test_tutor_interaction_default_role_is_user() -> None:
    """Missing role key defaults to 'user' → tutor.question_asked."""
    result = _classify("tutor.interaction.completed", {"content": "What?"})
    assert result is not None
    assert result.event_type == "tutor.question_asked"
    assert result.n4_level == 4


# ---------------------------------------------------------------------------
# Unknown event types
# ---------------------------------------------------------------------------


def test_unknown_event_type_returns_none() -> None:
    result = _classify("completely.unknown.event")
    assert result is None


def test_empty_event_type_returns_none() -> None:
    result = _classify("")
    assert result is None


def test_partial_prefix_not_matched() -> None:
    """'code' alone (without a dot suffix) is not in the mapping."""
    result = _classify("code")
    assert result is None


# ---------------------------------------------------------------------------
# Payload passthrough
# ---------------------------------------------------------------------------


def test_classify_preserves_payload() -> None:
    """The original payload is passed through untouched to ClassifiedEvent."""
    payload = {"student_id": "abc", "exercise_id": "xyz", "extra": 42}
    result = _classify("reads_problem", payload)
    assert result is not None
    assert result.payload == payload


def test_classify_tutor_preserves_payload() -> None:
    payload = {"role": "user", "content": "help", "session_id": "sess-1"}
    result = _classify("tutor.interaction.completed", payload)
    assert result is not None
    assert result.payload == payload


# ---------------------------------------------------------------------------
# Auto snapshot event (Task 9.5)
# ---------------------------------------------------------------------------


def test_code_snapshot_auto_maps_correctly() -> None:
    """code.snapshot.auto must map to canonical type 'code.snapshot.auto' with n4_level=None."""
    result = _classify("code.snapshot.auto", {"line_count": 42})
    assert result is not None
    assert result.event_type == "code.snapshot.auto"
    assert result.n4_level is None


def test_code_snapshot_auto_preserves_payload() -> None:
    payload = {"line_count": 15, "trigger": "timer"}
    result = _classify("code.snapshot.auto", payload)
    assert result is not None
    assert result.payload == payload
