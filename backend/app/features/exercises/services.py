from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.features.exercises.repositories import ExerciseRepository
from app.features.exercises.schemas import TestCaseSet
from app.shared.models.event_outbox import EventOutbox
from app.shared.models.exercise import Exercise, ExerciseDifficulty


class ExerciseService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ExerciseRepository(session)
        self._session = session

    async def create(self, course_id: uuid.UUID, data: dict[str, Any]) -> Exercise:
        # Validate test_cases structure
        if "test_cases" in data:
            self._validate_test_cases(data["test_cases"])
            # Convert Pydantic model to dict for JSONB storage
            if isinstance(data["test_cases"], TestCaseSet):
                data["test_cases"] = data["test_cases"].model_dump()

        data["course_id"] = course_id
        return await self._repo.create(data)

    async def get(self, exercise_id: uuid.UUID) -> Exercise:
        return await self._repo.get_by_id(exercise_id)

    async def get_for_student(
        self,
        exercise_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> Exercise:
        """Get exercise detail and emit reads_problem event for cognitive tracing."""
        exercise = await self._repo.get_by_id(exercise_id)

        # Emit reads_problem event
        outbox_event = EventOutbox(
            event_type="reads_problem",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "course_id": str(exercise.course_id),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        self._session.add(outbox_event)
        await self._session.flush()

        return exercise

    async def list_by_course(
        self,
        course_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        difficulty: ExerciseDifficulty | None = None,
        topic: str | None = None,
    ) -> tuple[list[Exercise], int]:
        return await self._repo.list_by_course(
            course_id, page=page, per_page=per_page, difficulty=difficulty, topic=topic,
        )

    async def list_for_student(
        self,
        student_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        difficulty: ExerciseDifficulty | None = None,
        topic: str | None = None,
    ) -> tuple[list[Exercise], int]:
        return await self._repo.list_for_student(
            student_id, page=page, per_page=per_page, difficulty=difficulty, topic=topic,
        )

    async def update(self, exercise_id: uuid.UUID, data: dict[str, Any]) -> Exercise:
        if "test_cases" in data and data["test_cases"] is not None:
            self._validate_test_cases(data["test_cases"])
            if isinstance(data["test_cases"], TestCaseSet):
                data["test_cases"] = data["test_cases"].model_dump()
        return await self._repo.update(exercise_id, data)

    async def delete(self, exercise_id: uuid.UUID) -> Exercise:
        return await self._repo.soft_delete(exercise_id)

    def _validate_test_cases(self, test_cases: Any) -> None:
        """Validate test_cases structure via Pydantic."""
        if isinstance(test_cases, TestCaseSet):
            return  # Already validated
        if isinstance(test_cases, dict):
            try:
                TestCaseSet.model_validate(test_cases)
            except Exception as exc:
                raise ValidationError(
                    message=f"Invalid test_cases structure: {exc}",
                    field="test_cases",
                ) from exc
        else:
            raise ValidationError(message="test_cases must be a valid object", field="test_cases")
