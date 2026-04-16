from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.features.cognitive.classifier import CognitiveEventClassifier
from app.features.cognitive.service import CognitiveService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Streams consumed by the cognitive worker.
# The worker reads from submissions, tutor, and code streams — all three
# can carry events that need CTR recording.
# ---------------------------------------------------------------------------
_STREAMS = ["events:submissions", "events:tutor", "events:code"]
_CONSUMER_GROUP = "cognitive-group"
_CONSUMER_NAME = "cognitive-worker-1"
_BLOCK_MS = 5_000  # 5 seconds blocking read
_ERROR_BACKOFF_SECONDS = 5.0
_TIMEOUT_CHECK_INTERVAL_SECONDS = 300  # 5 minutes


class CognitiveEventConsumer:
    """Background worker that reads events from Redis Streams and builds the CTR.

    Pattern mirrors OutboxWorker: asyncio task started in app lifespan,
    cancelled on shutdown. Uses XREADGROUP for at-least-once delivery with
    consumer groups so multiple workers could share load in future.

    A separate asyncio task (_timeout_checker) runs in parallel to close
    sessions with no activity for >30 minutes.
    """

    def __init__(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._redis = redis
        self._session_factory = session_factory
        self._classifier = CognitiveEventClassifier()
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Ensure consumer groups exist on all streams, then poll forever."""
        await self._ensure_consumer_groups()
        self._running = True
        logger.info(
            "CognitiveEventConsumer started",
            extra={"streams": _STREAMS, "group": _CONSUMER_GROUP},
        )
        while self._running:
            try:
                await self._poll()
            except asyncio.CancelledError:
                logger.info("CognitiveEventConsumer cancelled — shutting down")
                return
            except Exception:
                logger.exception("Unexpected error in CognitiveEventConsumer._poll")
                await asyncio.sleep(_ERROR_BACKOFF_SECONDS)

    async def stop(self) -> None:
        """Signal the consumer to stop after the current poll finishes."""
        self._running = False

    # ------------------------------------------------------------------
    # Stream initialisation
    # ------------------------------------------------------------------

    async def _ensure_consumer_groups(self) -> None:
        """Create consumer groups on all streams idempotently (MKSTREAM)."""
        for stream in _STREAMS:
            try:
                await self._redis.xgroup_create(
                    name=stream,
                    groupname=_CONSUMER_GROUP,
                    id="0",
                    mkstream=True,
                )
                logger.debug(
                    "Consumer group created",
                    extra={"stream": stream, "group": _CONSUMER_GROUP},
                )
            except Exception as exc:
                if "BUSYGROUP" in str(exc):
                    logger.debug(
                        "Consumer group already exists",
                        extra={"stream": stream, "group": _CONSUMER_GROUP},
                    )
                else:
                    logger.exception(
                        "Failed to create consumer group",
                        extra={"stream": stream, "group": _CONSUMER_GROUP},
                    )

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _poll(self) -> None:
        """Read one batch from all streams with XREADGROUP."""
        streams_arg = {s: ">" for s in _STREAMS}
        try:
            results = await self._redis.xreadgroup(
                groupname=_CONSUMER_GROUP,
                consumername=_CONSUMER_NAME,
                streams=streams_arg,
                count=10,
                block=_BLOCK_MS,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("XREADGROUP failed")
            await asyncio.sleep(_ERROR_BACKOFF_SECONDS)
            return

        if not results:
            return

        for stream_name, messages in results:
            stream_str = (
                stream_name.decode() if isinstance(stream_name, bytes) else stream_name
            )
            for msg_id, fields in messages:
                try:
                    await self._process_event(fields)
                    await self._redis.xack(stream_str, _CONSUMER_GROUP, msg_id)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Failed to process cognitive event",
                        extra={"stream": stream_str, "msg_id": msg_id},
                    )
                    # Message stays in the PEL for manual recovery or XCLAIM.

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    async def _process_event(self, fields: dict[Any, Any]) -> None:
        """Parse, classify, and persist one stream message as a CTR event."""
        # --- Decode raw bytes from Redis ---
        event_type_raw = fields.get(b"event_type") or fields.get("event_type", "")
        if isinstance(event_type_raw, bytes):
            event_type_raw = event_type_raw.decode()

        # EventBus wraps payloads inside a "data" JSON string
        data_raw = fields.get(b"data") or fields.get("data", "{}")
        if isinstance(data_raw, bytes):
            data_raw = data_raw.decode()

        try:
            payload: dict[str, Any] = json.loads(data_raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Malformed payload in stream message",
                extra={"event_type": event_type_raw},
            )
            return

        # --- Classify ---
        classified = self._classifier.classify(event_type_raw, payload)
        if classified is None:
            logger.debug(
                "Unknown event type — skipping CTR recording",
                extra={"event_type": event_type_raw},
            )
            return

        # --- Extract routing keys from payload ---
        student_id_str = payload.get("student_id")
        exercise_id_str = payload.get("exercise_id")
        if not student_id_str or not exercise_id_str:
            logger.warning(
                "CTR event missing student_id or exercise_id — cannot route to session",
                extra={"event_type": event_type_raw, "classified": classified.event_type},
            )
            return

        commission_id_str = payload.get(
            "commission_id", "00000000-0000-0000-0000-000000000000"
        )

        try:
            student_id = uuid.UUID(student_id_str)
            exercise_id = uuid.UUID(exercise_id_str)
            commission_id = uuid.UUID(commission_id_str)
        except (ValueError, AttributeError):
            logger.warning(
                "CTR event has non-UUID student_id/exercise_id/commission_id",
                extra={
                    "event_type": event_type_raw,
                    "student_id": student_id_str,
                    "exercise_id": exercise_id_str,
                },
            )
            return

        # --- Persist in a single transaction ---
        async with self._session_factory() as session:
            async with session.begin():
                service = CognitiveService(session)

                cog_session = await service.get_or_create_session(
                    student_id=student_id,
                    exercise_id=exercise_id,
                    commission_id=commission_id,
                )

                await service.add_event(
                    session=cog_session,
                    event_type=classified.event_type,
                    n4_level=classified.n4_level,
                    payload=classified.payload,
                )

                # Auto-close triggers — only on submission (session.closed just records the event)
                if classified.event_type == "submission.created":
                    try:
                        await service.close_session(cog_session.id)
                    except Exception:
                        logger.exception(
                            "Failed to auto-close cognitive session",
                            extra={
                                "session_id": str(cog_session.id),
                                "trigger_event": classified.event_type,
                            },
                        )

        logger.debug(
            "CTR event persisted",
            extra={
                "classified_type": classified.event_type,
                "n4_level": classified.n4_level,
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
            },
        )


# ---------------------------------------------------------------------------
# Session timeout checker — runs as a separate asyncio task
# ---------------------------------------------------------------------------


async def run_timeout_checker(
    session_factory: async_sessionmaker[AsyncSession],
    interval_seconds: int = _TIMEOUT_CHECK_INTERVAL_SECONDS,
    timeout_minutes: int = 30,
) -> None:
    """Periodically close cognitive sessions with no activity for >timeout_minutes.

    Designed to be launched as a background asyncio task alongside the
    CognitiveEventConsumer. Runs every interval_seconds (default 5 minutes).
    """
    logger.info(
        "CognitiveSessionTimeoutChecker started",
        extra={
            "interval_s": interval_seconds,
            "timeout_minutes": timeout_minutes,
        },
    )
    while True:
        try:
            async with session_factory() as session:
                async with session.begin():
                    service = CognitiveService(session)
                    closed = await service.close_stale_sessions(
                        timeout_minutes=timeout_minutes
                    )
                    if closed > 0:
                        logger.info(
                            "Stale cognitive sessions auto-closed",
                            extra={"count": closed},
                        )
        except asyncio.CancelledError:
            logger.info("CognitiveSessionTimeoutChecker cancelled — shutting down")
            return
        except Exception:
            logger.exception("Error in CognitiveSessionTimeoutChecker")

        await asyncio.sleep(interval_seconds)
