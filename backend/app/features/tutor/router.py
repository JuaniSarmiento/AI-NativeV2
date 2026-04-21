from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.core.security import validate_ws_token
from app.config import get_settings
from app.features.auth.dependencies import CurrentUser, RedisClient, get_redis, require_role
from app.features.tutor.llm_adapter import (
    AnthropicAdapter,
    FallbackLLMAdapter,
    LLMAdapter,
    LLMError,
    MistralAdapter,
)
from app.features.tutor.rate_limiter import TutorRateLimiter
from app.features.tutor.context_builder import ContextBuilder
from app.features.tutor.schemas import (
    ChatDoneOut,
    ChatErrorOut,
    ChatGuardrailOut,
    ChatMessageIn,
    ChatTokenOut,
    ConnectedOut,
    MessageResponse,
    MessagesListResponse,
    PongOut,
    RateLimitOut,
)
from app.features.tutor.service import TutorService
from app.shared.db.session import get_async_session

logger = get_logger(__name__)

router = APIRouter(tags=["tutor"])

_WS_TIMEOUT_SECONDS = 60.0


def _create_llm_adapter() -> LLMAdapter:
    settings = get_settings()
    provider = settings.tutor_llm_provider
    if provider == "mistral":
        primary: LLMAdapter = MistralAdapter()
    else:
        primary = AnthropicAdapter()

    if settings.tutor_llm_fallback:
        secondary: LLMAdapter = AnthropicAdapter() if provider == "mistral" else MistralAdapter()
        return FallbackLLMAdapter(primary, secondary)
    return primary


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/tutor/chat")
async def tutor_chat_ws(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """WebSocket endpoint for real-time tutor chat with streaming."""
    # --- Auth handshake ---
    redis = await get_redis()
    try:
        payload = await validate_ws_token(token, redis)
    except AuthenticationError:
        await websocket.close(code=4401, reason="Invalid token")
        return

    if payload.get("role") != "alumno":
        await websocket.close(code=4403, reason="Forbidden")
        return

    student_id = uuid.UUID(payload["sub"])
    await websocket.accept()

    # Send connected confirmation
    await _send_json(websocket, ConnectedOut())

    # --- Session state ---
    session_id: uuid.UUID | None = None
    current_exercise_id: uuid.UUID | None = None
    message_count = 0
    llm_adapter = _create_llm_adapter()
    rate_limiter = TutorRateLimiter(redis)

    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_WS_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=4408, reason="Timeout")
                return

            # Parse message
            try:
                import json
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                await _send_json(websocket, ChatErrorOut(
                    code="INVALID_JSON", message="Invalid JSON",
                ))
                continue

            msg_type = data.get("type")

            # --- Ping/Pong ---
            if msg_type == "ping":
                await _send_json(websocket, PongOut())
                continue

            # --- Chat message ---
            if msg_type == "chat.message":
                try:
                    msg = ChatMessageIn(**data)
                except PydanticValidationError:
                    await _send_json(websocket, ChatErrorOut(
                        code="INVALID_MESSAGE", message="Invalid message format",
                    ))
                    continue

                if not msg.content.strip():
                    await _send_json(websocket, ChatErrorOut(
                        code="EMPTY_MESSAGE", message="El mensaje no puede estar vacío",
                    ))
                    continue

                try:
                    exercise_id = uuid.UUID(msg.exercise_id)
                except ValueError:
                    await _send_json(websocket, ChatErrorOut(
                        code="INVALID_EXERCISE", message="exercise_id inválido",
                    ))
                    continue

                # Get a fresh session for this interaction
                from app.shared.db.session import get_session_factory
                factory = get_session_factory()
                async with factory() as db_session:
                    async with db_session.begin():
                        context_builder = ContextBuilder(db_session)
                        service = TutorService(db_session, llm_adapter, rate_limiter, context_builder)

                        # Rate limit check
                        rl_result = await service.check_rate_limit(student_id, exercise_id)
                        if not rl_result.allowed:
                            await _send_json(websocket, ChatErrorOut(
                                code="RATE_LIMITED",
                                message="Alcanzaste el límite de mensajes por hora para este ejercicio",
                                reset_at=rl_result.reset_at.isoformat(),
                            ))
                            continue

                        # Start session on first message or exercise change
                        if session_id is None or current_exercise_id != exercise_id:
                            session_id = await service.start_session(student_id, exercise_id)
                            current_exercise_id = exercise_id
                            message_count = 0

                        # Stream response
                        try:
                            async for token_text in service.chat(
                                student_id=student_id,
                                exercise_id=exercise_id,
                                session_id=session_id,
                                message=msg.content,
                            ):
                                await _send_json(websocket, ChatTokenOut(content=token_text))

                            message_count += 1

                            # Use last_chat_result for interaction_id — avoids extra DB query
                            chat_result = service.last_chat_result
                            interaction_id = str(chat_result.interaction_id) if chat_result else "unknown"

                            await _send_json(websocket, ChatDoneOut(
                                interaction_id=interaction_id,
                            ))

                            # Notify client of guardrail violation if detected
                            if chat_result and chat_result.guardrail_result.has_violation:
                                await _send_json(websocket, ChatGuardrailOut(
                                    violation_type=chat_result.guardrail_result.violation_type or "unknown",
                                    corrective_message=chat_result.guardrail_result.corrective_message or "",
                                ))

                        except NotFoundError:
                            await _send_json(websocket, ChatErrorOut(
                                code="INVALID_EXERCISE",
                                message="El ejercicio no existe o no está disponible",
                            ))
                            continue

                        except LLMError as exc:
                            await _send_json(websocket, ChatErrorOut(
                                code=exc.code, message=exc.message,
                            ))
                            continue

                    # Rate limit info
                    await _send_json(websocket, RateLimitOut(
                        remaining=rl_result.remaining,
                        reset_at=rl_result.reset_at.isoformat(),
                    ))

                continue

            # Unknown message type
            await _send_json(websocket, ChatErrorOut(
                code="UNKNOWN_TYPE", message=f"Unknown message type: {msg_type}",
            ))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"student_id": str(student_id)})
    except Exception:
        logger.exception("Unexpected error in WebSocket handler")
    finally:
        # End session if one was started
        if session_id is not None and current_exercise_id is not None:
            try:
                from app.shared.db.session import get_session_factory
                factory = get_session_factory()
                async with factory() as db_session:
                    async with db_session.begin():
                        service = TutorService(db_session, llm_adapter, rate_limiter)
                        await service.end_session(
                            session_id=session_id,
                            student_id=student_id,
                            exercise_id=current_exercise_id,
                            message_count=message_count,
                        )
            except Exception:
                logger.exception("Failed to emit session.ended event")


# ---------------------------------------------------------------------------
# REST fallback — message history
# ---------------------------------------------------------------------------


@router.get("/api/v1/tutor/sessions/{exercise_id}/messages")
async def get_session_messages(
    exercise_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    _user=require_role("alumno"),
) -> MessagesListResponse:
    """Return the last 50 messages of the most recent session for this exercise."""
    llm_adapter = _create_llm_adapter()
    rate_limiter = TutorRateLimiter(await get_redis())
    service = TutorService(session, llm_adapter, rate_limiter)

    messages = await service.get_messages(current_user.id, exercise_id, limit=50)

    return MessagesListResponse(
        data=[
            MessageResponse(
                id=str(m.id),
                session_id=str(m.session_id),
                role=m.role.value,
                content=m.content,
                tokens_used=m.tokens_used,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


# ---------------------------------------------------------------------------
# REST — teacher access to student chat (EPIC-17)
# ---------------------------------------------------------------------------


@router.get("/api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages")
async def get_teacher_student_messages(
    student_id: uuid.UUID,
    exercise_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _user=require_role("docente", "admin"),
) -> MessagesListResponse:
    """Return the last 50 messages of a student's session — for docente/admin trace view."""
    llm_adapter = _create_llm_adapter()
    rate_limiter = TutorRateLimiter(await get_redis())
    service = TutorService(session, llm_adapter, rate_limiter)

    messages = await service.get_messages(student_id, exercise_id, limit=50)

    return MessagesListResponse(
        data=[
            MessageResponse(
                id=str(m.id),
                session_id=str(m.session_id),
                role=m.role.value,
                content=m.content,
                tokens_used=m.tokens_used,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _send_json(ws: WebSocket, msg: Any) -> None:
    await ws.send_text(msg.model_dump_json())
