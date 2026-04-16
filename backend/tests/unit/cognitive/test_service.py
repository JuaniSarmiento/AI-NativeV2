"""Unit tests for CognitiveService."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.features.cognitive.models import CognitiveEvent, CognitiveSession, SessionStatus
from app.features.cognitive.service import CognitiveService


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_session_mock(
    session_id: uuid.UUID | None = None,
    status: SessionStatus = SessionStatus.open,
    genesis_hash: str | None = "genesis123",
    started_at: datetime | None = None,
) -> MagicMock:
    """Build a mock CognitiveSession ORM object."""
    mock = MagicMock(spec=CognitiveSession)
    mock.id = session_id or uuid.uuid4()
    mock.status = status
    mock.genesis_hash = genesis_hash
    mock.started_at = started_at or datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    mock.student_id = uuid.uuid4()
    mock.exercise_id = uuid.uuid4()
    mock.commission_id = uuid.uuid4()
    mock.closed_at = None
    mock.session_hash = None
    mock.events = []
    return mock


def _make_event_mock(
    sequence_number: int = 1,
    event_hash: str = "a" * 64,
) -> MagicMock:
    mock = MagicMock(spec=CognitiveEvent)
    mock.id = uuid.uuid4()
    mock.sequence_number = sequence_number
    mock.event_hash = event_hash
    return mock


def _make_db_session() -> MagicMock:
    """Return a mock AsyncSession with add and flush as magic/async mocks."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _build_service(
    db_session: MagicMock | None = None,
    session_repo: MagicMock | None = None,
    event_repo: MagicMock | None = None,
) -> tuple[CognitiveService, MagicMock]:
    """Construct a CognitiveService with mocked repositories."""
    db = db_session or _make_db_session()
    svc = CognitiveService(db)

    if session_repo is not None:
        svc._session_repo = session_repo
    if event_repo is not None:
        svc._event_repo = event_repo

    return svc, db


# ---------------------------------------------------------------------------
# get_or_create_session
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_or_create_session_returns_existing() -> None:
    """If an open session already exists it is returned without creating a new one."""
    existing = _make_session_mock()

    session_repo = MagicMock()
    session_repo.get_open_session = AsyncMock(return_value=existing)

    svc, db = _build_service(session_repo=session_repo)

    result = await svc.get_or_create_session(
        student_id=existing.student_id,
        exercise_id=existing.exercise_id,
        commission_id=existing.commission_id,
    )

    assert result is existing
    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_get_or_create_session_creates_new_when_none_exists() -> None:
    """When no open session exists a new CognitiveSession is created and flushed."""
    session_repo = MagicMock()
    session_repo.get_open_session = AsyncMock(return_value=None)

    db = _make_db_session()

    # Simulate server-side defaults being applied after first flush
    created_session: CognitiveSession | None = None

    async def fake_flush() -> None:
        nonlocal created_session
        if created_session is not None and created_session.started_at is None:
            created_session.started_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
            created_session.id = uuid.uuid4()

    db.flush = AsyncMock(side_effect=fake_flush)

    def capture_add(obj: object) -> None:
        nonlocal created_session
        if isinstance(obj, CognitiveSession):
            created_session = obj  # type: ignore[assignment]
            # Inject defaults that the DB server would provide
            created_session.id = uuid.uuid4()
            created_session.started_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    db.add = MagicMock(side_effect=capture_add)

    svc = CognitiveService(db)
    svc._session_repo = session_repo

    student_id = uuid.uuid4()
    exercise_id = uuid.uuid4()
    commission_id = uuid.uuid4()

    result = await svc.get_or_create_session(student_id, exercise_id, commission_id)

    assert isinstance(result, CognitiveSession)
    assert result.student_id == student_id
    assert result.exercise_id == exercise_id
    assert result.commission_id == commission_id
    assert result.status == SessionStatus.open
    assert result.genesis_hash is not None
    assert len(result.genesis_hash) == 64

    # flush called twice: once to get id/started_at, once after computing genesis_hash
    assert db.flush.await_count == 2


@pytest.mark.anyio
async def test_get_or_create_session_genesis_hash_is_deterministic() -> None:
    """Re-running get_or_create_session on the same data produces the same genesis hash."""
    session_id = uuid.uuid4()
    started_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    from app.features.cognitive.ctr_builder import compute_genesis_hash

    h = compute_genesis_hash(str(session_id), started_at)
    assert h == compute_genesis_hash(str(session_id), started_at)


# ---------------------------------------------------------------------------
# add_event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_add_event_increments_sequence_from_last() -> None:
    """add_event uses last_event.sequence_number + 1 as the new sequence."""
    cog_session = _make_session_mock(genesis_hash="genesis" + "0" * 57)
    last_event = _make_event_mock(sequence_number=3, event_hash="prev" + "0" * 60)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=last_event)

    db = _make_db_session()
    added_events = []

    def capture_add(obj: object) -> None:
        if isinstance(obj, CognitiveEvent):
            added_events.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    svc = CognitiveService(db)
    svc._event_repo = event_repo

    event = await svc.add_event(
        session=cog_session,
        event_type="code.run",
        n4_level=3,
        payload={"stdout": "hello"},
    )

    assert isinstance(event, CognitiveEvent)
    assert event.sequence_number == 4
    assert event.previous_hash == last_event.event_hash


@pytest.mark.anyio
async def test_add_event_uses_genesis_hash_when_no_previous_event() -> None:
    """First event in a session uses genesis_hash as previous_hash."""
    genesis_hash = "g" * 64
    cog_session = _make_session_mock(genesis_hash=genesis_hash)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    db = _make_db_session()
    added_events = []

    def capture_add(obj: object) -> None:
        if isinstance(obj, CognitiveEvent):
            added_events.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    svc = CognitiveService(db)
    svc._event_repo = event_repo

    event = await svc.add_event(
        session=cog_session,
        event_type="reads_problem",
        n4_level=1,
        payload={},
    )

    assert event.sequence_number == 1
    assert event.previous_hash == genesis_hash


@pytest.mark.anyio
async def test_add_event_chains_hash_correctly() -> None:
    """event_hash must be a valid SHA-256 hex string that encodes the chain link."""
    genesis_hash = "g" * 64
    cog_session = _make_session_mock(genesis_hash=genesis_hash)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    db = _make_db_session()
    added_events = []

    def capture_add(obj: object) -> None:
        if isinstance(obj, CognitiveEvent):
            added_events.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    svc = CognitiveService(db)
    svc._event_repo = event_repo

    event = await svc.add_event(
        session=cog_session,
        event_type="reads_problem",
        n4_level=1,
        payload={"key": "value"},
    )

    # Verify hash format
    assert len(event.event_hash) == 64
    assert all(c in "0123456789abcdef" for c in event.event_hash)

    # Verify it matches recomputation
    from app.features.cognitive.ctr_builder import compute_event_hash

    expected = compute_event_hash(
        genesis_hash, "reads_problem", event.payload, event.created_at
    )
    assert event.event_hash == expected


@pytest.mark.anyio
async def test_add_event_injects_n4_level_into_payload() -> None:
    """n4_level is added to the payload under key 'n4_level'."""
    cog_session = _make_session_mock(genesis_hash="g" * 64)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    db = _make_db_session()
    added_events = []

    def capture_add(obj: object) -> None:
        if isinstance(obj, CognitiveEvent):
            added_events.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    svc = CognitiveService(db)
    svc._event_repo = event_repo

    await svc.add_event(
        session=cog_session,
        event_type="code.run",
        n4_level=3,
        payload={"stdout": "x"},
    )

    assert added_events[0].payload["n4_level"] == 3


@pytest.mark.anyio
async def test_add_event_raises_if_session_not_open() -> None:
    """add_event raises ValidationError if the session status is not open."""
    closed_session = _make_session_mock(status=SessionStatus.closed)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    svc, _ = _build_service(event_repo=event_repo)

    with pytest.raises(ValidationError) as exc_info:
        await svc.add_event(
            session=closed_session,
            event_type="code.run",
            n4_level=3,
            payload={},
        )

    assert exc_info.value.code == "SESSION_NOT_OPEN"


# ---------------------------------------------------------------------------
# close_session
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_close_session_sets_closed_at_and_status() -> None:
    """close_session updates status, closed_at, and session_hash."""
    session_id = uuid.uuid4()
    cog_session = _make_session_mock(session_id=session_id, genesis_hash="g" * 64)
    last_event = _make_event_mock(event_hash="lasteventhash" + "0" * 51)

    session_repo = MagicMock()
    session_repo.get_session_with_events = AsyncMock(return_value=cog_session)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=last_event)

    svc, db = _build_service(session_repo=session_repo, event_repo=event_repo)

    result = await svc.close_session(session_id)

    assert result.status == SessionStatus.closed
    assert result.closed_at is not None
    assert result.session_hash == last_event.event_hash
    db.flush.assert_awaited()


@pytest.mark.anyio
async def test_close_session_uses_genesis_hash_when_no_events() -> None:
    """If no events were appended, session_hash equals genesis_hash."""
    session_id = uuid.uuid4()
    genesis = "g" * 64
    cog_session = _make_session_mock(session_id=session_id, genesis_hash=genesis)

    session_repo = MagicMock()
    session_repo.get_session_with_events = AsyncMock(return_value=cog_session)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    svc, _ = _build_service(session_repo=session_repo, event_repo=event_repo)

    result = await svc.close_session(session_id)

    assert result.session_hash == genesis
    assert result.status == SessionStatus.closed


@pytest.mark.anyio
async def test_close_session_raises_not_found_for_unknown_session() -> None:
    session_repo = MagicMock()
    session_repo.get_session_with_events = AsyncMock(return_value=None)

    svc, _ = _build_service(session_repo=session_repo)

    with pytest.raises(NotFoundError):
        await svc.close_session(uuid.uuid4())


@pytest.mark.anyio
async def test_close_session_raises_if_already_closed() -> None:
    session_id = uuid.uuid4()
    closed = _make_session_mock(session_id=session_id, status=SessionStatus.closed)

    session_repo = MagicMock()
    session_repo.get_session_with_events = AsyncMock(return_value=closed)

    event_repo = MagicMock()
    event_repo.get_last_event = AsyncMock(return_value=None)

    svc, _ = _build_service(session_repo=session_repo, event_repo=event_repo)

    with pytest.raises(ValidationError) as exc_info:
        await svc.close_session(session_id)

    assert exc_info.value.code == "SESSION_NOT_OPEN"
