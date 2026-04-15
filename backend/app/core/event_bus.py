from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Stream names and consumer group — one source of truth for all producers
# and consumers in the system.
# ---------------------------------------------------------------------------
STREAMS: dict[str, str] = {
    "events:submissions": "group:submissions",
    "events:tutor": "group:tutor",
    "events:code": "group:code",
    "events:cognitive": "group:cognitive",
}

_MAX_BACKOFF_SECONDS = 60.0
_INITIAL_BACKOFF_SECONDS = 1.0
_READ_BLOCK_MS = 5_000  # block for 5 s waiting for new messages


class EventBus:
    """Thin wrapper around Redis Streams for inter-phase event delivery.

    Each phase publishes domain events via ``publish()`` and subscribes to
    events from other phases via ``subscribe()``.  The outbox worker is the
    primary publisher — application code should write to the outbox table
    rather than calling ``publish()`` directly so that publication is atomic
    with the originating DB transaction.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: Redis | None = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the async Redis client."""
        self._client = aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("EventBus connected", extra={"redis_url": self._redis_url})

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("EventBus connection closed")

    @property
    def client(self) -> Redis:  # type: ignore[type-arg]
        if self._client is None:
            raise RuntimeError(
                "EventBus is not connected. Call `await event_bus.connect()` first."
            )
        return self._client

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(
        self,
        stream: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        source: str = "unknown",
    ) -> str:
        """Append an event to a Redis Stream and return the generated entry ID.

        The published message follows the standard payload structure:
        ``event_id``, ``event_type``, ``timestamp``, ``source``, ``data``.

        Args:
            stream: Target stream name (e.g. ``'events:submissions'``).
            event_type: Dot-namespaced event type (e.g. ``'submission.created'``).
            payload: Arbitrary JSON-serialisable dict (stored as ``data``).
            source: Producing service/phase identifier.

        Returns:
            The Redis entry ID (``'<ms>-<seq>'``).
        """
        event_id = str(uuid.uuid4())
        entry_id: str = await self.client.xadd(
            stream,
            {
                "event_id": event_id,
                "event_type": event_type,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "source": source,
                "data": json.dumps(payload),
            },
        )
        logger.debug(
            "Event published",
            extra={"stream": stream, "event_type": event_type, "entry_id": entry_id},
        )
        return entry_id

    # ------------------------------------------------------------------
    # Subscribing
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        stream: str,
        group: str,
        consumer: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Consume messages from a Redis Stream with at-least-once delivery.

        Runs forever in the calling coroutine — intended to be started as a
        background task.  Uses ``XREADGROUP`` so multiple consumers in the
        same group share the load without duplicate processing.

        Reconnects with exponential backoff on ``ConnectionError``.

        Args:
            stream: Source stream name.
            group: Consumer group name.
            consumer: Unique consumer identifier within the group.
            callback: Async function called for each message.  Must be
                idempotent because delivery can happen more than once after
                a consumer crash.
        """
        backoff = _INITIAL_BACKOFF_SECONDS

        while True:
            try:
                results = await self.client.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream: ">"},
                    block=_READ_BLOCK_MS,
                    count=10,
                )
                if not results:
                    backoff = _INITIAL_BACKOFF_SECONDS
                    continue

                for _stream_name, messages in results:
                    for entry_id, fields in messages:
                        try:
                            await callback({"entry_id": entry_id, **fields})
                            await self.client.xack(stream, group, entry_id)
                            backoff = _INITIAL_BACKOFF_SECONDS
                        except Exception:
                            logger.exception(
                                "Callback failed for event",
                                extra={"stream": stream, "entry_id": entry_id},
                            )
                            # Message stays in PEL — a separate recovery worker
                            # can re-claim it with XCLAIM after a timeout.

            except RedisConnectionError:
                logger.warning(
                    "Redis connection lost in subscriber — retrying",
                    extra={"stream": stream, "backoff_s": backoff},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
            except asyncio.CancelledError:
                logger.info(
                    "Subscriber cancelled", extra={"stream": stream, "group": group}
                )
                return

    # ------------------------------------------------------------------
    # Stream initialisation
    # ------------------------------------------------------------------

    async def initialize_streams(self) -> None:
        """Idempotently create all streams and consumer groups.

        Uses ``XGROUP CREATE ... MKSTREAM`` so the stream is created if it
        does not yet exist.  ``BUSYGROUP`` errors (group already exists) are
        silently swallowed — safe to call on every startup.
        """
        for stream, group in STREAMS.items():
            try:
                await self.client.xgroup_create(
                    name=stream,
                    groupname=group,
                    id="0",
                    mkstream=True,
                )
                logger.info(
                    "Stream and consumer group initialised",
                    extra={"stream": stream, "group": group},
                )
            except Exception as exc:
                if "BUSYGROUP" in str(exc):
                    logger.debug(
                        "Consumer group already exists — skipping",
                        extra={"stream": stream, "group": group},
                    )
                else:
                    logger.exception(
                        "Failed to initialise stream",
                        extra={"stream": stream, "group": group},
                    )
                    raise
