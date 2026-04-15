"""Unit tests for TutorService — mocked LLM adapter and repositories."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.tutor.llm_adapter import ChatMessage, LLMUsage
from app.features.tutor.models import InteractionRole, TutorInteraction, TutorSystemPrompt
from app.features.tutor.rate_limiter import RateLimitResult
from app.features.tutor.service import TutorService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_llm():
    adapter = AsyncMock()
    adapter.model_name = "test-model"
    adapter.last_usage = LLMUsage(input_tokens=100, output_tokens=50)
    return adapter


@pytest.fixture
def mock_rate_limiter():
    limiter = AsyncMock()
    return limiter


@pytest.fixture
def service(mock_session, mock_llm, mock_rate_limiter):
    return TutorService(mock_session, mock_llm, mock_rate_limiter)


async def test_check_rate_limit_delegates(service, mock_rate_limiter):
    student_id = uuid.uuid4()
    exercise_id = uuid.uuid4()
    expected = RateLimitResult(allowed=True, remaining=29, reset_at=datetime.now(tz=timezone.utc))
    mock_rate_limiter.check.return_value = expected

    result = await service.check_rate_limit(student_id, exercise_id)

    mock_rate_limiter.check.assert_awaited_once_with(student_id, exercise_id)
    assert result.allowed is True
    assert result.remaining == 29


async def test_start_session_returns_uuid_and_emits_event(service, mock_session):
    student_id = uuid.uuid4()
    exercise_id = uuid.uuid4()

    session_id = await service.start_session(student_id, exercise_id)

    assert isinstance(session_id, uuid.UUID)
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    outbox_event = mock_session.add.call_args[0][0]
    assert outbox_event.event_type == "tutor.session.started"
    assert outbox_event.payload["student_id"] == str(student_id)


async def test_end_session_emits_event(service, mock_session):
    session_id = uuid.uuid4()
    student_id = uuid.uuid4()
    exercise_id = uuid.uuid4()

    await service.end_session(
        session_id=session_id,
        student_id=student_id,
        exercise_id=exercise_id,
        message_count=5,
    )

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    outbox_event = mock_session.add.call_args[0][0]
    assert outbox_event.event_type == "tutor.session.ended"
    assert outbox_event.payload["message_count"] == 5
