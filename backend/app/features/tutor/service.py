from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.governance.service import GovernanceService
from app.features.tutor.adversarial import AdversarialResult, get_adversarial_detector
from app.features.tutor.context_builder import ContextBuilder
from app.features.tutor.guardrails import GuardrailResult, GuardrailsProcessor
from app.features.tutor.llm_adapter import ChatMessage, LLMAdapter
from app.features.tutor.models import InteractionRole, TutorInteraction, TutorSystemPrompt
from app.features.tutor.n4_classifier import N4Classifier, N4ClassificationResult
from app.features.tutor.rate_limiter import RateLimitResult, TutorRateLimiter
from app.features.tutor.reformulation_detector import ReformulationDetector
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
    n4_level: int | None
    sub_classification: str | None


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
        commission_id = await self._resolve_commission_id(student_id, exercise_id)

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

        # Classify user message by N4 level
        classifier = N4Classifier()
        user_classification = classifier.classify_message(message, "user")
        user_interaction.n4_level = user_classification.n4_level
        await self._session.flush()

        # Detect prompt reformulation (compare with recent user messages)
        await self._detect_reformulation(
            message=message,
            student_id=student_id,
            exercise_id=exercise_id,
            session_id=session_id,
            commission_id=commission_id,
        )

        # Adversarial check — must occur BEFORE the LLM call
        adversarial_result = get_adversarial_detector().check(
            message, str(session_id)
        )
        if adversarial_result.is_adversarial:
            standard_msg = get_adversarial_detector().standard_response()
            now_ts = datetime.now(tz=timezone.utc).isoformat()

            # Persist the adversarial assistant response
            adversarial_interaction = TutorInteraction(
                session_id=session_id,
                student_id=student_id,
                exercise_id=exercise_id,
                role=InteractionRole.assistant,
                content=standard_msg,
                prompt_hash=prompt.sha256_hash,
            )
            self._session.add(adversarial_interaction)
            await self._session.flush()

            # Emit CTR event for adversarial detection
            self._session.add(EventOutbox(
                event_type="adversarial.detected",
                payload={
                    "interaction_id": str(adversarial_interaction.id),
                    "student_id": str(student_id),
                    "exercise_id": str(exercise_id),
                    "session_id": str(session_id),
                    "commission_id": commission_id,
                    "category": adversarial_result.category,
                    "attempt_number": adversarial_result.attempt_number,
                    "timestamp": now_ts,
                },
            ))
            await self._session.flush()

            # Governance escalation on 3+ attempts
            if adversarial_result.should_escalate:
                governance = GovernanceService(self._session)
                await governance.record_guardrail_violation(
                    student_id=student_id,
                    interaction_id=adversarial_interaction.id,
                    exercise_id=exercise_id,
                    session_id=session_id,
                    violation_type="adversarial.escalation",
                    violation_details=(
                        f"Adversarial attempt #{adversarial_result.attempt_number} "
                        f"in session {session_id} — category: {adversarial_result.category}"
                    ),
                )
                logger.warning(
                    "Adversarial escalation recorded to governance",
                    extra={
                        "student_id": str(student_id),
                        "session_id": str(session_id),
                        "attempt_number": adversarial_result.attempt_number,
                    },
                )

            self._last_chat_result = ChatResult(
                assistant_text=standard_msg,
                interaction_id=adversarial_interaction.id,
                guardrail_result=GuardrailResult.ok(),
                tokens_used=None,
                n4_level=None,
                sub_classification=None,
            )
            yield standard_msg
            return

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

        # Classify assistant message by N4 level
        assistant_classification = classifier.classify_message(assistant_text, "assistant")
        assistant_interaction.n4_level = assistant_classification.n4_level
        await self._session.flush()

        tokens_used = usage.output_tokens if usage else None

        now_ts = datetime.now(tz=timezone.utc).isoformat()

        # Outbox event for the user turn
        self._session.add(EventOutbox(
            event_type="tutor.interaction.completed",
            payload={
                "interaction_id": str(user_interaction.id),
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "commission_id": commission_id,
                "role": "user",
                "content": message,
                "n4_level": user_classification.n4_level,
                "n4_sub_classification": user_classification.sub_classification,
                "prompt_type": user_classification.prompt_type,
                "prompt_hash": prompt.sha256_hash,
                "timestamp": now_ts,
            },
        ))

        # Outbox event for the assistant turn
        self._session.add(EventOutbox(
            event_type="tutor.interaction.completed",
            payload={
                "interaction_id": str(assistant_interaction.id),
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "commission_id": commission_id,
                "role": "assistant",
                "n4_level": assistant_classification.n4_level,
                "n4_sub_classification": assistant_classification.sub_classification,
                "prompt_type": None,
                "prompt_hash": prompt.sha256_hash,
                "tokens_used": tokens_used,
                "guardrail_violation": guardrail_result.violation_type,
                "timestamp": now_ts,
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

            # Record governance event for the violation
            governance = GovernanceService(self._session)
            await governance.record_guardrail_violation(
                student_id=student_id,
                interaction_id=assistant_interaction.id,
                exercise_id=exercise_id,
                session_id=session_id,
                violation_type=guardrail_result.violation_type,
                violation_details=guardrail_result.violation_details,
            )

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
            n4_level=assistant_classification.n4_level,
            sub_classification=assistant_classification.sub_classification,
        )

    async def start_session(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
    ) -> uuid.UUID:
        """Create a new logical session and emit start event."""
        session_id = uuid.uuid4()
        commission_id = await self._resolve_commission_id(student_id, exercise_id)

        self._session.add(EventOutbox(
            event_type="tutor.session.started",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "commission_id": commission_id,
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
        commission_id = await self._resolve_commission_id(student_id, exercise_id)
        self._session.add(EventOutbox(
            event_type="tutor.session.ended",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "commission_id": commission_id,
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

    async def _detect_reformulation(
        self,
        message: str,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        session_id: uuid.UUID,
        commission_id: str,
    ) -> None:
        """Check if the user message is a reformulation of a recent prompt."""
        try:
            recent = await self._interaction_repo.get_session_messages(session_id, limit=10)
            recent_user_msgs = [
                {
                    "content": i.content,
                    "timestamp": i.created_at.isoformat() if i.created_at else "",
                    "interaction_id": str(i.id),
                }
                for i in recent
                if i.role == InteractionRole.user
            ]
            now_ts = datetime.now(tz=timezone.utc).isoformat()
            detector = ReformulationDetector()
            result = detector.detect(message, now_ts, recent_user_msgs)
            if result is not None:
                self._session.add(EventOutbox(
                    event_type="prompt.reformulated",
                    payload={
                        "student_id": str(student_id),
                        "exercise_id": str(exercise_id),
                        "session_id": str(session_id),
                        "commission_id": commission_id,
                        **result,
                        "timestamp": now_ts,
                    },
                ))
                await self._session.flush()
                logger.debug(
                    "Prompt reformulation detected",
                    extra={"similarity": result.get("similarity_score"), "student_id": str(student_id)},
                )
        except Exception:
            logger.exception("Failed to detect prompt reformulation")

    async def _get_active_prompt(self) -> TutorSystemPrompt:
        if self._active_prompt is None:
            self._active_prompt = await self._prompt_repo.get_active_prompt()
        return self._active_prompt

    async def _resolve_commission_id(
        self, student_id: uuid.UUID, exercise_id: uuid.UUID
    ) -> str:
        """Resolve commission_id from student enrollment for the exercise's course."""
        from sqlalchemy import select
        from app.shared.models.enrollment import Enrollment
        from app.shared.models.commission import Commission
        from app.shared.models.exercise import Exercise

        try:
            ex_result = await self._session.execute(
                select(Exercise).where(Exercise.id == exercise_id)
            )
            exercise = ex_result.scalar_one_or_none()
            if exercise is None:
                return "00000000-0000-0000-0000-000000000000"

            enr_result = await self._session.execute(
                select(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.is_active.is_(True),
                )
            )
            for enr in enr_result.scalars().all():
                comm_result = await self._session.execute(
                    select(Commission).where(
                        Commission.id == enr.commission_id,
                        Commission.course_id == exercise.course_id,
                    )
                )
                if comm_result.scalar_one_or_none():
                    return str(enr.commission_id)
        except Exception:
            pass
        return "00000000-0000-0000-0000-000000000000"
