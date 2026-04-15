from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    topic_taxonomy: dict | None = None  # type: ignore[type-arg]


class CourseUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    topic_taxonomy: dict | None = None  # type: ignore[type-arg]


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    topic_taxonomy: dict | None  # type: ignore[type-arg]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("id")
    @classmethod
    def serialize_id(cls, v: uuid.UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# Commission
# ---------------------------------------------------------------------------

class CommissionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    teacher_id: uuid.UUID
    year: int = Field(ge=2020, le=2100)
    semester: int = Field(ge=1, le=2)


class CommissionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    teacher_id: uuid.UUID | None = None
    year: int | None = Field(None, ge=2020, le=2100)
    semester: int | None = Field(None, ge=1, le=2)


class CommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    name: str
    year: int
    semester: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("id", "course_id", "teacher_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    commission_id: uuid.UUID
    enrolled_at: datetime
    is_active: bool

    @field_serializer("id", "student_id", "commission_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


class StudentCourseResponse(BaseModel):
    """Enriched response for a student's enrolled course."""
    course_id: str
    course_name: str
    commission_id: str
    commission_name: str
    teacher_name: str
    year: int
    semester: int
    enrolled_at: datetime
