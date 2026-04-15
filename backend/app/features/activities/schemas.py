from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.shared.models.activity import ActivityStatus
from app.shared.models.llm_config import LLMProvider


# ---------------------------------------------------------------------------
# LLM Config
# ---------------------------------------------------------------------------

class LLMConfigRequest(BaseModel):
    provider: LLMProvider
    api_key: str = Field(min_length=1)
    model_name: str = Field(default="gpt-4o-mini", min_length=1, max_length=100)


class LLMConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: LLMProvider
    model_name: str
    has_key: bool = True  # Always true if config exists; key never exposed


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class GenerateActivityRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)
    course_id: uuid.UUID


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str | None
    prompt_used: str | None
    status: ActivityStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("id", "course_id", "created_by")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


class ActivityUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
