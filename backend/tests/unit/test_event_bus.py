"""Unit tests for EventBus.

These tests mock the Redis client — no real Redis instance required.
Integration tests that hit a live Redis belong in tests/integration/.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.event_bus import STREAMS, EventBus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bus(redis_url: str = "redis://localhost:6379/0") -> EventBus:
    return EventBus(redis_url=redis_url)


# ---------------------------------------------------------------------------
# connect / close
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_connect_creates_client() -> None:
    """EventBus.connect() should initialise the internal Redis client."""
    bus = _make_bus()
    mock_redis = AsyncMock()

    with patch("app.core.event_bus.aioredis.from_url", return_value=mock_redis):
        await bus.connect()

    assert bus._client is mock_redis


@pytest.mark.anyio
async def test_close_calls_aclose() -> None:
    """EventBus.close() should call aclose on the client and clear the ref."""
    bus = _make_bus()
    mock_redis = AsyncMock()
    bus._client = mock_redis

    await bus.close()

    mock_redis.aclose.assert_awaited_once()
    assert bus._client is None


@pytest.mark.anyio
async def test_client_property_raises_when_not_connected() -> None:
    """Accessing .client before connect() should raise RuntimeError."""
    bus = _make_bus()
    with pytest.raises(RuntimeError, match="not connected"):
        _ = bus.client


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_publish_adds_to_stream() -> None:
    """publish() should call XADD on the Redis client and return the entry ID."""
    bus = _make_bus()
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234567890-0")
    bus._client = mock_redis

    entry_id = await bus.publish(
        stream="events:submissions",
        event_type="submission.created",
        payload={"submission_id": "abc-123", "student_id": "stu-999"},
    )

    assert entry_id == "1234567890-0"
    mock_redis.xadd.assert_awaited_once()

    call_args = mock_redis.xadd.call_args
    assert call_args.args[0] == "events:submissions"
    fields: dict[str, Any] = call_args.args[1]
    assert fields["event_type"] == "submission.created"
    import json
    data = json.loads(fields["data"])
    assert data["submission_id"] == "abc-123"


# ---------------------------------------------------------------------------
# initialize_streams
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_initialize_streams_creates_all_groups() -> None:
    """initialize_streams() should call XGROUP CREATE for each defined stream."""
    bus = _make_bus()
    mock_redis = AsyncMock()
    mock_redis.xgroup_create = AsyncMock(return_value="OK")
    bus._client = mock_redis

    await bus.initialize_streams()

    assert mock_redis.xgroup_create.await_count == len(STREAMS)

    created_streams = {
        call.kwargs["name"] for call in mock_redis.xgroup_create.call_args_list
    }
    assert created_streams == set(STREAMS.keys())


@pytest.mark.anyio
async def test_initialize_streams_ignores_busygroup() -> None:
    """BUSYGROUP error (group already exists) must be silently swallowed."""
    bus = _make_bus()
    mock_redis = AsyncMock()
    mock_redis.xgroup_create = AsyncMock(
        side_effect=Exception("BUSYGROUP Consumer Group name already exists")
    )
    bus._client = mock_redis

    # Should NOT raise
    await bus.initialize_streams()


@pytest.mark.anyio
async def test_initialize_streams_propagates_other_errors() -> None:
    """Errors other than BUSYGROUP must propagate so startup fails visibly."""
    bus = _make_bus()
    mock_redis = AsyncMock()
    mock_redis.xgroup_create = AsyncMock(
        side_effect=Exception("WRONGTYPE Operation against a key")
    )
    bus._client = mock_redis

    with pytest.raises(Exception, match="WRONGTYPE"):
        await bus.initialize_streams()
