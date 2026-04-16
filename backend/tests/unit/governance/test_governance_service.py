"""Unit tests for GovernanceService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.features.governance.models import GovernanceEvent
from app.features.governance.service import GovernanceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    """Return a mock AsyncSession that tracks add() and flush() calls."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_repo(items: list[GovernanceEvent], total: int) -> MagicMock:
    """Return a mock GovernanceEventRepository."""
    repo = MagicMock()
    repo.list_events = AsyncMock(return_value=(items, total))
    return repo


def _make_event(event_type: str = "test.event") -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=event_type,
        actor_id=uuid.uuid4(),
        details={},
    )
    event.id = uuid.uuid4()
    return event


# ---------------------------------------------------------------------------
# test_record_event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_event_creates_governance_event() -> None:
    """record_event adds a GovernanceEvent to the session and flushes."""
    session = _make_session()
    service = GovernanceService(session)

    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    event = await service.record_event(
        event_type="prompt.created",
        actor_id=actor_id,
        target_type="prompt",
        target_id=target_id,
        details={"version": "1.0.0"},
    )

    assert isinstance(event, GovernanceEvent)
    assert event.event_type == "prompt.created"
    assert event.actor_id == actor_id
    assert event.target_type == "prompt"
    assert event.target_id == target_id
    assert event.details == {"version": "1.0.0"}
    session.add.assert_called_once_with(event)
    session.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_record_event_without_target() -> None:
    """record_event works with no target_type or target_id."""
    session = _make_session()
    service = GovernanceService(session)

    event = await service.record_event(
        event_type="system.startup",
        actor_id=uuid.uuid4(),
        details={"message": "system started"},
    )

    assert event.target_type is None
    assert event.target_id is None


# ---------------------------------------------------------------------------
# test_record_guardrail_violation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_guardrail_violation_correct_mapping() -> None:
    """record_guardrail_violation creates a 'guardrail.triggered' event.

    actor_id == student_id, target_type == 'interaction', target_id == interaction_id.
    Also emits an EventOutbox 'governance.flag.raised' event.
    """
    session = _make_session()
    service = GovernanceService(session)

    student_id = uuid.uuid4()
    interaction_id = uuid.uuid4()
    exercise_id = uuid.uuid4()
    session_id = uuid.uuid4()

    event = await service.record_guardrail_violation(
        student_id=student_id,
        interaction_id=interaction_id,
        exercise_id=exercise_id,
        session_id=session_id,
        violation_type="excessive_code",
        violation_details="Total code lines: 10, limit: 5",
    )

    assert event.event_type == "guardrail.triggered"
    assert event.actor_id == student_id
    assert event.target_type == "interaction"
    assert event.target_id == interaction_id
    assert event.details["violation_type"] == "excessive_code"
    assert event.details["violation_details"] == "Total code lines: 10, limit: 5"
    assert str(exercise_id) == event.details["exercise_id"]
    assert str(session_id) == event.details["session_id"]

    # session.add called twice: GovernanceEvent + EventOutbox
    assert session.add.call_count == 2
    # flush called twice: once in record_event, once after adding EventOutbox
    assert session.flush.await_count == 2


# ---------------------------------------------------------------------------
# test_record_prompt_created
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_prompt_created() -> None:
    """record_prompt_created creates a 'prompt.created' governance event."""
    session = _make_session()
    service = GovernanceService(session)

    prompt_id = uuid.uuid4()
    created_by = uuid.uuid4()

    event = await service.record_prompt_created(
        prompt_id=prompt_id,
        name="Socratic Tutor v2",
        version="2.0.0",
        sha256_hash="abc123" * 10,
        created_by=created_by,
    )

    assert event.event_type == "prompt.created"
    assert event.actor_id == created_by
    assert event.target_type == "prompt"
    assert event.target_id == prompt_id
    assert event.details["name"] == "Socratic Tutor v2"
    assert event.details["version"] == "2.0.0"
    assert event.details["sha256_hash"] == "abc123" * 10


# ---------------------------------------------------------------------------
# test_record_prompt_activated
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_prompt_activated() -> None:
    """record_prompt_activated creates a 'prompt.activated' event with hashes."""
    session = _make_session()
    service = GovernanceService(session)

    prompt_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    old_hash = "oldhash" * 9
    new_hash = "newhash" * 9

    event = await service.record_prompt_activated(
        prompt_id=prompt_id,
        name="Socratic Tutor v2",
        old_hash=old_hash,
        new_hash=new_hash,
        actor_id=actor_id,
    )

    assert event.event_type == "prompt.activated"
    assert event.actor_id == actor_id
    assert event.target_id == prompt_id
    assert event.details["old_hash"] == old_hash
    assert event.details["new_hash"] == new_hash


# ---------------------------------------------------------------------------
# test_list_events_with_filter
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_events_with_filter() -> None:
    """list_events delegates to repository with event_type filter."""
    session = _make_session()
    service = GovernanceService(session)

    filtered_event = _make_event("guardrail.triggered")
    mock_repo = _make_repo([filtered_event], 1)

    # Patch the repo on the service instance
    service._repo = mock_repo

    items, total = await service.list_events(
        page=1, per_page=20, event_type="guardrail.triggered"
    )

    mock_repo.list_events.assert_awaited_once_with(
        page=1, per_page=20, event_type="guardrail.triggered"
    )
    assert len(items) == 1
    assert items[0].event_type == "guardrail.triggered"
    assert total == 1


# ---------------------------------------------------------------------------
# test_list_events_pagination
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_events_pagination() -> None:
    """list_events passes page and per_page to the repository correctly."""
    session = _make_session()
    service = GovernanceService(session)

    events = [_make_event(f"prompt.created") for _ in range(5)]
    mock_repo = _make_repo(events, 42)
    service._repo = mock_repo

    items, total = await service.list_events(page=3, per_page=5, event_type=None)

    mock_repo.list_events.assert_awaited_once_with(page=3, per_page=5, event_type=None)
    assert len(items) == 5
    assert total == 42
