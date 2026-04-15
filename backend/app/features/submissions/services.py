from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.features.submissions.models import (
    ActivitySubmission,
    CodeSnapshot,
    Submission,
    SubmissionStatus,
)
from app.shared.models.activity import Activity, ActivityStatus
from app.shared.models.event_outbox import EventOutbox
from app.shared.models.exercise import Exercise


class SubmissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def submit_activity(
        self,
        activity_id: uuid.UUID,
        student_id: uuid.UUID,
        exercises_code: list[dict],
    ) -> ActivitySubmission:
        # Verify activity exists and is published
        result = await self._session.execute(
            select(Activity)
            .where(Activity.id == activity_id, Activity.is_active.is_(True))
            .options(selectinload(Activity.exercises))
        )
        activity = result.scalar_one_or_none()
        if activity is None:
            raise NotFoundError(resource="Activity", identifier=str(activity_id))
        if activity.status != ActivityStatus.published:
            raise ValidationError(message="La actividad no esta publicada.")

        active_exercises = [e for e in activity.exercises if e.is_active]
        exercise_ids = {str(e.id) for e in active_exercises}

        # Validate all exercises have code
        submitted_ids = {str(ec["exercise_id"]) for ec in exercises_code}
        missing = exercise_ids - submitted_ids
        if missing:
            raise ValidationError(message=f"Faltan ejercicios: {len(missing)} ejercicios sin codigo.")

        # Calculate attempt number
        count_result = await self._session.execute(
            select(func.count())
            .select_from(ActivitySubmission)
            .where(
                ActivitySubmission.activity_id == activity_id,
                ActivitySubmission.student_id == student_id,
            )
        )
        prev_attempts = count_result.scalar_one()
        attempt = prev_attempts + 1

        # Create activity submission
        activity_sub = ActivitySubmission(
            activity_id=activity_id,
            student_id=student_id,
            attempt_number=attempt,
        )
        self._session.add(activity_sub)
        await self._session.flush()

        # Create individual submissions + events
        for ec in exercises_code:
            ex_id = uuid.UUID(str(ec["exercise_id"]))
            submission = Submission(
                student_id=student_id,
                exercise_id=ex_id,
                activity_submission_id=activity_sub.id,
                code=ec["code"],
                attempt_number=attempt,
            )
            self._session.add(submission)

            # Emit event
            event = EventOutbox(
                event_type="exercise.submitted",
                payload={
                    "student_id": str(student_id),
                    "exercise_id": str(ex_id),
                    "activity_id": str(activity_id),
                    "attempt_number": attempt,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                },
            )
            self._session.add(event)

        await self._session.flush()
        return activity_sub

    async def list_student_submissions(
        self,
        activity_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> list[ActivitySubmission]:
        result = await self._session.execute(
            select(ActivitySubmission)
            .where(
                ActivitySubmission.activity_id == activity_id,
                ActivitySubmission.student_id == student_id,
            )
            .options(selectinload(ActivitySubmission.submissions))
            .order_by(ActivitySubmission.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def list_all_submissions(
        self,
        activity_id: uuid.UUID,
    ) -> list[ActivitySubmission]:
        result = await self._session.execute(
            select(ActivitySubmission)
            .where(ActivitySubmission.activity_id == activity_id)
            .options(
                selectinload(ActivitySubmission.submissions),
                selectinload(ActivitySubmission.student),
            )
            .order_by(ActivitySubmission.submitted_at.desc())
        )
        return list(result.scalars().all())


class SnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        code: str,
    ) -> CodeSnapshot:
        snapshot = CodeSnapshot(
            student_id=student_id,
            exercise_id=exercise_id,
            code=code,
        )
        self._session.add(snapshot)

        event = EventOutbox(
            event_type="code.snapshot.captured",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "snapshot_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        self._session.add(event)

        await self._session.flush()
        return snapshot
