from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ExerciseCode(BaseModel):
    exercise_id: uuid.UUID
    code: str = Field(min_length=1, max_length=50000)


class SubmitActivityRequest(BaseModel):
    exercises: list[ExerciseCode] = Field(min_length=1)


class SnapshotRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50000)


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    exercise_id: uuid.UUID
    code: str
    status: str
    score: Decimal | None
    feedback: str | None
    attempt_number: int
    submitted_at: datetime
    evaluated_at: datetime | None

    @field_serializer("id", "student_id", "exercise_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


class ActivitySubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_id: uuid.UUID
    student_id: uuid.UUID
    attempt_number: int
    status: str
    total_score: Decimal | None
    submitted_at: datetime
    submissions: list[SubmissionResponse] = []

    @field_serializer("id", "activity_id", "student_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)
