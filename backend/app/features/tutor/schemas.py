from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# WebSocket — incoming messages (client → server)
# ---------------------------------------------------------------------------


class ChatMessageIn(BaseModel):
    type: Literal["chat.message"]
    content: str
    exercise_id: str


class PingIn(BaseModel):
    type: Literal["ping"]


WSMessageIn = Annotated[
    Union[ChatMessageIn, PingIn],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# WebSocket — outgoing messages (server → client)
# ---------------------------------------------------------------------------


class ConnectedOut(BaseModel):
    type: Literal["connected"] = "connected"


class ChatTokenOut(BaseModel):
    type: Literal["chat.token"] = "chat.token"
    content: str


class ChatDoneOut(BaseModel):
    type: Literal["chat.done"] = "chat.done"
    interaction_id: str


class ChatErrorOut(BaseModel):
    type: Literal["chat.error"] = "chat.error"
    code: str
    message: str
    reset_at: str | None = None


class RateLimitOut(BaseModel):
    type: Literal["rate_limit"] = "rate_limit"
    remaining: int
    reset_at: str


class PongOut(BaseModel):
    type: Literal["pong"] = "pong"


class ChatGuardrailOut(BaseModel):
    type: Literal["chat.guardrail"] = "chat.guardrail"
    violation_type: str
    corrective_message: str


# ---------------------------------------------------------------------------
# REST — responses
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    tokens_used: int | None = None
    created_at: datetime


class MessagesListResponse(BaseModel):
    status: str = "ok"
    data: list[MessageResponse]
    meta: dict | None = None  # type: ignore[type-arg]
