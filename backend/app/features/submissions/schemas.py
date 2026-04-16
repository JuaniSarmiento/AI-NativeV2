from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

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
    student_name: str = ""
    attempt_number: int
    status: str
    total_score: Decimal | None
    submitted_at: datetime
    submissions: list[SubmissionResponse] = []

    @field_serializer("id", "activity_id", "student_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


class CreateReflectionRequest(BaseModel):
    """Request body for submitting a post-exercise reflection."""

    difficulty_perception: Annotated[int, Field(ge=1, le=5)]
    strategy_description: Annotated[str, Field(min_length=10, max_length=5000)]
    ai_usage_evaluation: Annotated[str, Field(min_length=10, max_length=5000)]
    what_would_change: Annotated[str, Field(min_length=10, max_length=5000)]
    confidence_level: Annotated[int, Field(ge=1, le=5)]


class ReflectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_submission_id: uuid.UUID
    student_id: uuid.UUID
    difficulty_perception: int
    strategy_description: str
    ai_usage_evaluation: str
    what_would_change: str
    confidence_level: int
    created_at: datetime

    @field_serializer("id", "activity_submission_id", "student_id")
    @classmethod
    def serialize_uuids(cls, v: uuid.UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# Grading — AI evaluation
# ---------------------------------------------------------------------------


class ExerciseEvaluation(BaseModel):
    """AI evaluation for a single exercise within an activity."""

    submission_id: str
    exercise_id: str
    exercise_title: str = ""
    score: float
    feedback: str
    strengths: list[str] = []
    improvements: list[str] = []


class ActivityEvaluationResponse(BaseModel):
    """AI-generated evaluation of the complete activity."""

    activity_submission_id: str
    general_score: float
    general_feedback: str
    exercises: list[ExerciseEvaluation] = []


class ExerciseGradeItem(BaseModel):
    submission_id: str
    score: float = Field(ge=0, le=100)
    feedback: str = ""


class ConfirmActivityGradeRequest(BaseModel):
    """Docente confirms the whole activity grade."""

    general_score: float = Field(ge=0, le=100)
    general_feedback: str = Field(min_length=1, max_length=5000)
    exercises: list[ExerciseGradeItem] = []
