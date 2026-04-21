from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.features.cognitive.classifier import CognitiveEventClassifier, llm_classify_message
from app.features.cognitive.detectors import (
    ManualTestCaseDetector,
    PseudocodeDetector,
    TutorCodeAcceptanceDetector,
)
from app.features.cognitive.service import CognitiveService
from app.features.tutor.n4_classifier import N4Classifier

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
        api_key: str = "",
        model: str = "mistral-small-latest",
    ) -> None:
        self._redis = redis
        self._session_factory = session_factory
        self._classifier = CognitiveEventClassifier()
        self._n4_classifier = N4Classifier()
        self._pseudocode_detector = PseudocodeDetector()
        self._test_detector = ManualTestCaseDetector()
        self._tutor_acceptance_detector = TutorCodeAcceptanceDetector()
        self._api_key = api_key
        self._model = model
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

        # --- Hybrid LLM classification (optional, only for tutor interactions) ---
        if (
            event_type_raw == "tutor.interaction.completed"
            and self._api_key
            and isinstance(payload.get("content"), str)
        ):
            content = payload["content"]
            role = payload.get("role", "user")
            # Only upgrade if regex confidence is low
            regex_result = self._n4_classifier.classify_message(content, role)
            if regex_result.confidence == "low":
                try:
                    llm_result = await llm_classify_message(
                        content=content,
                        role=role,
                        api_key=self._api_key,
                        model=self._model,
                        timeout=3.0,
                    )
                    if llm_result is not None:
                        llm_level, llm_prompt_type = llm_result
                        classified.n4_level = llm_level
                        if llm_prompt_type is not None:
                            classified.payload = {**classified.payload, "prompt_type": llm_prompt_type}
                        logger.debug(
                            "LLM classification upgraded regex result",
                            extra={
                                "n4_level": llm_level,
                                "prompt_type": llm_prompt_type,
                            },
                        )
                except Exception:
                    logger.warning(
                        "Hybrid LLM classification failed — using regex result",
                        extra={"event_type": event_type_raw},
                    )

        # --- Extract routing keys from payload ---
        student_id_str = payload.get("student_id")
        exercise_id_str = payload.get("exercise_id")
        if not student_id_str or not exercise_id_str:
            logger.warning(
                "CTR event missing student_id or exercise_id — cannot route to session",
                extra={"event_type": event_type_raw, "classified": classified.event_type},
            )
            return

        commission_id_str = payload.get("commission_id")
        _ZERO_UUID = "00000000-0000-0000-0000-000000000000"
        if not commission_id_str or commission_id_str == _ZERO_UUID:
            logger.warning(
                "CTR event has missing or zero commission_id — discarding",
                extra={
                    "event_type": event_type_raw,
                    "student_id": student_id_str,
                    "exercise_id": exercise_id_str,
                    "commission_id": commission_id_str,
                },
            )
            return

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

                # --- Synthetic event detection (post-processing) ---
                await self._emit_synthetic_events(
                    service, cog_session, classified.event_type, classified.payload
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

    # ------------------------------------------------------------------
    # Synthetic event detection
    # ------------------------------------------------------------------

    async def _emit_synthetic_events(
        self,
        service: CognitiveService,
        cog_session: Any,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Run detectors and emit any synthetic events into the CTR."""
        from app.features.cognitive.classifier import CognitiveEventClassifier

        synthetic_events = []

        if event_type == "code.snapshot":
            pseudo = self._pseudocode_detector.detect(payload)
            if pseudo is not None:
                synthetic_events.append(pseudo)

            tutor_resp = self._tutor_acceptance_detector.detect(
                payload,
                recent_tutor_responses=payload.get("_recent_tutor_responses", []),
                recent_events=payload.get("_recent_events", []),
            )
            if tutor_resp is not None:
                synthetic_events.append(tutor_resp)

        elif event_type == "code.run":
            test_case = self._test_detector.detect(payload)
            if test_case is not None:
                synthetic_events.append(test_case)

        classifier = CognitiveEventClassifier()
        for synthetic in synthetic_events:
            classified = classifier.classify(synthetic.event_type, synthetic.payload)
            if classified is None:
                continue
            try:
                await service.add_event(
                    session=cog_session,
                    event_type=classified.event_type,
                    n4_level=classified.n4_level,
                    payload=classified.payload,
                )
                logger.debug(
                    "Synthetic CTR event emitted",
                    extra={
                        "event_type": classified.event_type,
                        "n4_level": classified.n4_level,
                        "session_id": str(cog_session.id),
                    },
                )
            except Exception:
                logger.exception(
                    "Failed to emit synthetic event",
                    extra={
                        "event_type": synthetic.event_type,
                        "session_id": str(cog_session.id),
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
