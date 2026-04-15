from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.event_bus import EventBus
from app.core.logging import get_logger
from app.shared.models.event_outbox import EventOutbox

logger = get_logger(__name__)

_MAX_RETRIES = 5

# Mapping from event_type prefix → Redis stream name
_STREAM_ROUTING: dict[str, str] = {
    "submission": "events:submissions",
    "tutor": "events:tutor",
    "code": "events:code",
    "cognitive": "events:cognitive",
}


def _route_event(event_type: str) -> str | None:
    """Return the Redis stream for *event_type* based on its dot-prefix.

    Returns ``None`` for unknown prefixes — the worker logs a warning and
    marks the row as ``failed`` rather than retrying forever.
    """
    prefix = event_type.split(".")[0]
    return _STREAM_ROUTING.get(prefix)


class OutboxWorker:
    """Polls the ``event_outbox`` table and forwards events to Redis Streams.

    Transaction safety guarantees:
    - Reads rows in ``pending`` status with ``FOR UPDATE SKIP LOCKED`` so
      multiple workers can run without stepping on each other.
    - Each row is updated atomically after publish — no event is lost even
      if the process dies mid-loop.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus

    async def process_pending(self) -> None:
        """Read and publish one batch of pending outbox events."""
        async with self._session_factory() as session:
            async with session.begin():
                rows = (
                    await session.execute(
                        select(EventOutbox)
                        .where(EventOutbox.status == "pending")
                        .order_by(EventOutbox.created_at)
                        .limit(50)
                        .with_for_update(skip_locked=True)
                    )
                ).scalars().all()

                if not rows:
                    return

                for event in rows:
                    stream = _route_event(event.event_type)
                    if stream is None:
                        logger.warning(
                            "Unknown event_type prefix — marking as failed",
                            extra={
                                "event_id": str(event.id),
                                "event_type": event.event_type,
                            },
                        )
                        event.status = "failed"
                        event.retry_count = _MAX_RETRIES + 1
                        continue

                    try:
                        await self._event_bus.publish(
                            stream=stream,
                            event_type=event.event_type,
                            payload={
                                "outbox_id": str(event.id),
                                **event.payload,
                            },
                            source="outbox-worker",
                        )
                        event.status = "processed"
                        event.processed_at = datetime.now(tz=timezone.utc)
                        logger.info(
                            "Outbox event published",
                            extra={
                                "event_id": str(event.id),
                                "event_type": event.event_type,
                                "stream": stream,
                            },
                        )
                    except Exception:
                        event.retry_count = (event.retry_count or 0) + 1
                        if event.retry_count > _MAX_RETRIES:
                            event.status = "failed"
                            logger.error(
                                "Outbox event exceeded max retries — marked as failed",
                                extra={
                                    "event_id": str(event.id),
                                    "event_type": event.event_type,
                                    "retry_count": event.retry_count,
                                },
                            )
                        else:
                            logger.warning(
                                "Failed to publish outbox event — will retry",
                                extra={
                                    "event_id": str(event.id),
                                    "event_type": event.event_type,
                                    "retry_count": event.retry_count,
                                },
                            )

    async def run(self, interval: float = 5.0) -> None:
        """Poll ``process_pending`` in a loop at *interval* seconds.

        Designed to be launched as a background asyncio task during app
        startup and cancelled gracefully on shutdown.
        """
        logger.info("OutboxWorker started", extra={"interval_s": interval})
        while True:
            try:
                await self.process_pending()
            except asyncio.CancelledError:
                logger.info("OutboxWorker cancelled — shutting down")
                return
            except Exception:
                logger.exception("Unexpected error in OutboxWorker.process_pending")
            await asyncio.sleep(interval)
