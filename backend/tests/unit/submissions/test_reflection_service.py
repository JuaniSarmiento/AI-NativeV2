"""Unit tests for ReflectionService (EPIC-12 — Post-exercise reflection).

All tests mock the AsyncSession to avoid requiring a live database.
The session.execute mock uses side_effect lists so callers get distinct
results per call (first for ActivitySubmission lookup, second for duplicate check).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.features.submissions.models import ActivitySubmission, Reflection
from app.features.submissions.services import ReflectionService
from app.shared.models.event_outbox import EventOutbox


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STUDENT_ID = uuid.uuid4()
OTHER_STUDENT_ID = uuid.uuid4()
ACTIVITY_SUBMISSION_ID = uuid.uuid4()

VALID_DATA = {
    "difficulty_perception": 3,
    "strategy_description": "Usé un enfoque iterativo para resolver el problema.",
    "ai_usage_evaluation": "Consulté la IA para entender el enunciado, no para el código.",
    "what_would_change": "Planificaría mejor la estructura antes de escribir código.",
    "confidence_level": 4,
}


def _make_activity_submission(student_id: uuid.UUID = STUDENT_ID) -> MagicMock:
    sub = MagicMock(spec=ActivitySubmission)
    sub.id = ACTIVITY_SUBMISSION_ID
    sub.student_id = student_id
    sub.activity_id = uuid.uuid4()
    sub.attempt_number = 1
    return sub


def _make_reflection() -> MagicMock:
    ref = MagicMock(spec=Reflection)
    ref.id = uuid.uuid4()
    ref.activity_submission_id = ACTIVITY_SUBMISSION_ID
    ref.student_id = STUDENT_ID
    ref.difficulty_perception = VALID_DATA["difficulty_perception"]
    ref.strategy_description = VALID_DATA["strategy_description"]
    ref.ai_usage_evaluation = VALID_DATA["ai_usage_evaluation"]
    ref.what_would_change = VALID_DATA["what_would_change"]
    ref.confidence_level = VALID_DATA["confidence_level"]
    ref.created_at = datetime.now(tz=timezone.utc)
    return ref


def _mock_scalar_result(value) -> MagicMock:
    """Return a mock that mimics .scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def service(mock_session: AsyncMock) -> ReflectionService:
    return ReflectionService(mock_session)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_reflection_success(service: ReflectionService, mock_session: AsyncMock) -> None:
    """Happy path: reflection is created, event is emitted, flush is called twice."""
    activity_sub = _make_activity_submission()

    # First execute: fetch ActivitySubmission → returns the submission
    # Second execute: check for existing Reflection → returns None (no duplicate)
    mock_session.execute.side_effect = [
        _mock_scalar_result(activity_sub),
        _mock_scalar_result(None),
    ]

    reflection = await service.create_reflection(
        activity_submission_id=ACTIVITY_SUBMISSION_ID,
        student_id=STUDENT_ID,
        data=VALID_DATA,
    )

    assert reflection.activity_submission_id == ACTIVITY_SUBMISSION_ID
    assert reflection.student_id == STUDENT_ID
    assert reflection.difficulty_perception == VALID_DATA["difficulty_perception"]
    assert reflection.confidence_level == VALID_DATA["confidence_level"]

    # session.add should be called twice: Reflection + EventOutbox
    assert mock_session.add.call_count == 2
    added_objects = [c.args[0] for c in mock_session.add.call_args_list]
    assert any(isinstance(obj, Reflection) for obj in added_objects)
    assert any(isinstance(obj, EventOutbox) for obj in added_objects)

    # flush called twice
    assert mock_session.flush.await_count == 2


@pytest.mark.anyio
async def test_create_reflection_event_emitted(service: ReflectionService, mock_session: AsyncMock) -> None:
    """The emitted EventOutbox has the correct event_type and payload fields."""
    activity_sub = _make_activity_submission()
    mock_session.execute.side_effect = [
        _mock_scalar_result(activity_sub),
        _mock_scalar_result(None),
    ]

    await service.create_reflection(
        activity_submission_id=ACTIVITY_SUBMISSION_ID,
        student_id=STUDENT_ID,
        data=VALID_DATA,
    )

    added_objects = [c.args[0] for c in mock_session.add.call_args_list]
    outbox_events = [obj for obj in added_objects if isinstance(obj, EventOutbox)]
    assert len(outbox_events) == 1

    event = outbox_events[0]
    assert event.event_type == "reflection.submitted"
    assert event.payload["student_id"] == str(STUDENT_ID)
    assert event.payload["activity_submission_id"] == str(ACTIVITY_SUBMISSION_ID)
    assert event.payload["difficulty_perception"] == VALID_DATA["difficulty_perception"]
    assert event.payload["confidence_level"] == VALID_DATA["confidence_level"]
    assert "timestamp" in event.payload


@pytest.mark.anyio
async def test_create_reflection_duplicate_rejected(service: ReflectionService, mock_session: AsyncMock) -> None:
    """ConflictError is raised when a reflection already exists for the submission."""
    activity_sub = _make_activity_submission()
    existing_reflection = _make_reflection()

    mock_session.execute.side_effect = [
        _mock_scalar_result(activity_sub),
        _mock_scalar_result(existing_reflection),  # duplicate found
    ]

    with pytest.raises(ConflictError) as exc_info:
        await service.create_reflection(
            activity_submission_id=ACTIVITY_SUBMISSION_ID,
            student_id=STUDENT_ID,
            data=VALID_DATA,
        )

    assert exc_info.value.code == "REFLECTION_ALREADY_EXISTS"
    # Nothing should have been added to the session
    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_create_reflection_wrong_student(service: ReflectionService, mock_session: AsyncMock) -> None:
    """AuthorizationError is raised when the student does not own the submission."""
    activity_sub = _make_activity_submission(student_id=OTHER_STUDENT_ID)

    mock_session.execute.side_effect = [
        _mock_scalar_result(activity_sub),
    ]

    with pytest.raises(AuthorizationError):
        await service.create_reflection(
            activity_submission_id=ACTIVITY_SUBMISSION_ID,
            student_id=STUDENT_ID,  # different from OTHER_STUDENT_ID
            data=VALID_DATA,
        )

    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_create_reflection_submission_not_found(service: ReflectionService, mock_session: AsyncMock) -> None:
    """NotFoundError is raised when the ActivitySubmission does not exist."""
    mock_session.execute.side_effect = [
        _mock_scalar_result(None),  # submission not found
    ]

    with pytest.raises(NotFoundError) as exc_info:
        await service.create_reflection(
            activity_submission_id=ACTIVITY_SUBMISSION_ID,
            student_id=STUDENT_ID,
            data=VALID_DATA,
        )

    assert "ActivitySubmission" in exc_info.value.message
    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_get_reflection_exists(service: ReflectionService, mock_session: AsyncMock) -> None:
    """get_reflection returns the Reflection when it exists."""
    reflection = _make_reflection()
    mock_session.execute.return_value = _mock_scalar_result(reflection)

    result = await service.get_reflection(ACTIVITY_SUBMISSION_ID)

    assert result is reflection
    assert result.activity_submission_id == ACTIVITY_SUBMISSION_ID


@pytest.mark.anyio
async def test_get_reflection_not_found(service: ReflectionService, mock_session: AsyncMock) -> None:
    """get_reflection returns None when no reflection exists."""
    mock_session.execute.return_value = _mock_scalar_result(None)

    result = await service.get_reflection(ACTIVITY_SUBMISSION_ID)

    assert result is None
