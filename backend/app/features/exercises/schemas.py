from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.shared.models.exercise import ExerciseDifficulty


# ---------------------------------------------------------------------------
# Test cases validation
# ---------------------------------------------------------------------------

class TestCase(BaseModel):
    id: str
    description: str
    input: str
    expected_output: str
    is_hidden: bool = False
    weight: float = 1.0


class TestCaseSet(BaseModel):
    language: str = "python"
    timeout_ms: int = 10000
    memory_limit_mb: int = 128
    cases: list[TestCase] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class ExerciseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    test_cases: TestCaseSet
    difficulty: ExerciseDifficulty
    topic_tags: list[str] = []
    language: str = "python"
    starter_code: str = ""
    max_attempts: int = Field(10, ge=1, le=100)
    time_limit_minutes: int = Field(60, ge=5, le=480)
    order_index: int = 0


class ExerciseUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    test_cases: TestCaseSet | None = None
    difficulty: ExerciseDifficulty | None = None
    topic_tags: list[str] | None = None
    language: str | None = None
    starter_code: str | None = None
    max_attempts: int | None = Field(None, ge=1, le=100)
    time_limit_minutes: int | None = Field(None, ge=5, le=480)
    order_index: int | None = None


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str
    test_cases: dict  # type: ignore[type-arg]
    difficulty: ExerciseDifficulty
    topic_tags: list[str]
    language: str
    starter_code: str
    max_attempts: int
    time_limit_minutes: int
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("id", "course_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


class ExerciseSummaryResponse(BaseModel):
    """Lightweight exercise for list views — omits description and test_cases."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    difficulty: ExerciseDifficulty
    topic_tags: list[str]
    language: str
    order_index: int

    @field_serializer("id", "course_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)
