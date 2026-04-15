from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.tutor.context_builder import ContextBuilder
from app.features.tutor.guardrails import GuardrailResult, GuardrailsProcessor
from app.features.tutor.llm_adapter import ChatMessage, LLMAdapter
from app.features.tutor.models import InteractionRole, TutorInteraction, TutorSystemPrompt
from app.features.tutor.rate_limiter import RateLimitResult, TutorRateLimiter
from app.features.tutor.repositories import TutorInteractionRepository, TutorPromptRepository
from app.shared.models.event_outbox import EventOutbox

logger = get_logger(__name__)


@dataclass
class ChatResult:
    """Accumulated result available after a :py:meth:`TutorService.chat` iteration."""

    assistant_text: str
    interaction_id: uuid.UUID
    guardrail_result: GuardrailResult
    tokens_used: int | None


class TutorService:
    """Orchestrates the tutor chat flow.

    Validates rate limits, builds a contextual prompt, calls the LLM,
    runs guardrails on the response, persists interactions, and emits
    outbox events.

    Usage::

        service = TutorService(session, llm_adapter, rate_limiter, context_builder)
        async for token in service.chat(...):
            await send(token)
        result = service.last_chat_result  # available after iteration
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_adapter: LLMAdapter,
        rate_limiter: TutorRateLimiter,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._session = session
        self._llm = llm_adapter
        self._rate_limiter = rate_limiter
        self._interaction_repo = TutorInteractionRepository(session)
        self._prompt_repo = TutorPromptRepository(session)
        self._context_builder = context_builder or ContextBuilder(session)
        self._active_prompt: TutorSystemPrompt | None = None
        self._last_chat_result: ChatResult | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def last_chat_result(self) -> ChatResult | None:
        """Result of the most recent :py:meth:`chat` call.

        Only populated *after* the generator returned by ``chat()`` has been
        fully exhausted.
        """
        return self._last_chat_result

    async def check_rate_limit(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
    ) -> RateLimitResult:
        return await self._rate_limiter.check(student_id, exercise_id)

    async def chat(
        self,
        *,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        session_id: uuid.UUID,
        message: str,
    ) -> AsyncIterator[str]:
        """Stream a tutor response, persist both turns, run guardrails, emit events.

        Yields LLM tokens as they arrive.  After the generator is exhausted,
        ``self.last_chat_result`` holds the full :class:`ChatResult`.
        """
        self._last_chat_result = None
        prompt = await self._get_active_prompt()

        # Build context-aware system prompt
        composed_prompt = await self._context_builder.build_prompt(
            exercise_id=exercise_id,
            student_id=student_id,
            base_prompt_template=prompt.content,
        )

        # Persist user message
        user_interaction = TutorInteraction(
            session_id=session_id,
            student_id=student_id,
            exercise_id=exercise_id,
            role=InteractionRole.user,
            content=message,
            prompt_hash=prompt.sha256_hash,
        )
        self._session.add(user_interaction)
        await self._session.flush()

        # Build message history for context (last 10 turns)
        history = await self._interaction_repo.get_session_messages(
            session_id, limit=10,
        )
        llm_messages = [
            ChatMessage(role=i.role.value, content=i.content) for i in history
        ]

        # Stream LLM response
        full_response: list[str] = []
        async for token in self._llm.stream_response(
            llm_messages, composed_prompt,
        ):
            full_response.append(token)
            yield token

        assistant_text = "".join(full_response)
        usage = self._llm.last_usage

        # Run guardrails on the completed response
        guardrails_processor = GuardrailsProcessor(prompt.guardrails_config)
        guardrail_result = guardrails_processor.analyze(assistant_text)

        # Persist assistant message
        assistant_interaction = TutorInteraction(
            session_id=session_id,
            student_id=student_id,
            exercise_id=exercise_id,
            role=InteractionRole.assistant,
            content=assistant_text,
            tokens_used=usage.output_tokens if usage else None,
            model_version=self._llm.model_name,
            prompt_hash=prompt.sha256_hash,
        )
        self._session.add(assistant_interaction)
        await self._session.flush()

        tokens_used = usage.output_tokens if usage else None

        # Outbox event for the completed assistant turn
        self._session.add(EventOutbox(
            event_type="tutor.interaction.completed",
            payload={
                "interaction_id": str(assistant_interaction.id),
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "role": "assistant",
                "n4_classification": None,
                "prompt_hash": prompt.sha256_hash,
                "tokens_used": tokens_used,
                "guardrail_violation": guardrail_result.violation_type,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        ))
        await self._session.flush()

        # Emit guardrail event when a violation was detected
        if guardrail_result.has_violation:
            self._session.add(EventOutbox(
                event_type="guardrail.triggered",
                payload={
                    "interaction_id": str(assistant_interaction.id),
                    "student_id": str(student_id),
                    "exercise_id": str(exercise_id),
                    "session_id": str(session_id),
                    "violation_type": guardrail_result.violation_type,
                    "violation_details": guardrail_result.violation_details,
                    "prompt_hash": prompt.sha256_hash,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                },
            ))
            await self._session.flush()

            logger.warning(
                "Guardrail violation emitted to outbox",
                extra={
                    "violation_type": guardrail_result.violation_type,
                    "student_id": str(student_id),
                    "exercise_id": str(exercise_id),
                },
            )

        self._last_chat_result = ChatResult(
            assistant_text=assistant_text,
            interaction_id=assistant_interaction.id,
            guardrail_result=guardrail_result,
            tokens_used=tokens_used,
        )

    async def start_session(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
    ) -> uuid.UUID:
        """Create a new logical session and emit start event."""
        session_id = uuid.uuid4()

        self._session.add(EventOutbox(
            event_type="tutor.session.started",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        ))
        await self._session.flush()

        logger.info(
            "Tutor session started",
            extra={"student_id": str(student_id), "session_id": str(session_id)},
        )
        return session_id

    async def end_session(
        self,
        *,
        session_id: uuid.UUID,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        message_count: int,
    ) -> None:
        """Emit session ended event."""
        self._session.add(EventOutbox(
            event_type="tutor.session.ended",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "message_count": message_count,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        ))
        await self._session.flush()

        logger.info(
            "Tutor session ended",
            extra={"session_id": str(session_id), "message_count": message_count},
        )

    async def get_messages(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[TutorInteraction]:
        return await self._interaction_repo.get_latest_session_messages(
            student_id, exercise_id, limit=limit,
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _get_active_prompt(self) -> TutorSystemPrompt:
        if self._active_prompt is None:
            self._active_prompt = await self._prompt_repo.get_active_prompt()
        return self._active_prompt
