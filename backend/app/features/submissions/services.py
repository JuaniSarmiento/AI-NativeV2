from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.features.submissions.models import (
    ActivitySubmission,
    CodeSnapshot,
    Reflection,
    Submission,
    SubmissionStatus,
)
from app.shared.models.activity import Activity, ActivityStatus
from app.shared.models.enrollment import Enrollment
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

        # Resolve commission_id from student's enrollment for this course
        commission_id_str = "00000000-0000-0000-0000-000000000000"
        enrollment_result = await self._session.execute(
            select(Enrollment)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.is_active.is_(True),
            )
        )
        enrollments = list(enrollment_result.scalars().all())
        # Find enrollment whose commission belongs to this course
        if enrollments:
            from app.shared.models.commission import Commission
            for enr in enrollments:
                comm_result = await self._session.execute(
                    select(Commission).where(
                        Commission.id == enr.commission_id,
                        Commission.course_id == activity.course_id,
                    )
                )
                comm = comm_result.scalar_one_or_none()
                if comm:
                    commission_id_str = str(comm.id)
                    break

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
                    "commission_id": commission_id_str,
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


class ReflectionService:
    """Handles creation and retrieval of post-exercise reflections (EPIC-12).

    Enforces the one-to-one constraint with ActivitySubmission programmatically
    before hitting the DB unique constraint, giving callers a clean ConflictError.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_reflection(
        self,
        activity_submission_id: uuid.UUID,
        student_id: uuid.UUID,
        data: dict,
    ) -> Reflection:
        """Create a reflection for an ActivitySubmission.

        Raises:
            NotFoundError: If the activity_submission does not exist.
            AuthorizationError: If student_id does not match the submission owner.
            ConflictError: If a reflection already exists for this submission.
        """
        # 1. Verify activity_submission exists
        result = await self._session.execute(
            select(ActivitySubmission).where(ActivitySubmission.id == activity_submission_id)
        )
        activity_submission = result.scalar_one_or_none()
        if activity_submission is None:
            raise NotFoundError(
                resource="ActivitySubmission",
                identifier=str(activity_submission_id),
            )

        # 2. Verify student_id matches the submission owner
        if activity_submission.student_id != student_id:
            raise AuthorizationError(
                message="No tenés permiso para reflexionar sobre esta submission."
            )

        # 3. Check for existing reflection (programmatic check before DB unique constraint)
        existing_result = await self._session.execute(
            select(Reflection).where(
                Reflection.activity_submission_id == activity_submission_id
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise ConflictError(
                message="Ya existe una reflexión para esta submission.",
                code="REFLECTION_ALREADY_EXISTS",
            )

        # 4. Create the Reflection
        reflection = Reflection(
            activity_submission_id=activity_submission_id,
            student_id=student_id,
            difficulty_perception=data["difficulty_perception"],
            strategy_description=data["strategy_description"],
            ai_usage_evaluation=data["ai_usage_evaluation"],
            what_would_change=data["what_would_change"],
            confidence_level=data["confidence_level"],
        )
        self._session.add(reflection)
        await self._session.flush()

        # 5. Resolve commission_id for cognitive tracing
        reflection_commission_id = "00000000-0000-0000-0000-000000000000"
        try:
            from app.shared.models.commission import Commission
            act_result = await self._session.execute(
                select(ActivitySubmission)
                .where(ActivitySubmission.id == activity_submission_id)
            )
            act_sub = act_result.scalar_one_or_none()
            if act_sub:
                from app.shared.models.activity import Activity
                act_obj_result = await self._session.execute(
                    select(Activity).where(Activity.id == act_sub.activity_id)
                )
                act_obj = act_obj_result.scalar_one_or_none()
                if act_obj:
                    enr_result = await self._session.execute(
                        select(Enrollment)
                        .join(Commission, Commission.id == Enrollment.commission_id)
                        .where(
                            Enrollment.student_id == student_id,
                            Enrollment.is_active.is_(True),
                            Commission.course_id == act_obj.course_id,
                        )
                        .limit(1)
                    )
                    enr = enr_result.scalar_one_or_none()
                    if enr:
                        reflection_commission_id = str(enr.commission_id)
        except Exception:
            pass

        # Emit reflection.submitted event via EventOutbox
        event = EventOutbox(
            event_type="reflection.submitted",
            payload={
                "reflection_id": str(reflection.id),
                "activity_submission_id": str(activity_submission_id),
                "student_id": str(student_id),
                "commission_id": reflection_commission_id,
                "difficulty_perception": reflection.difficulty_perception,
                "confidence_level": reflection.confidence_level,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        self._session.add(event)
        await self._session.flush()

        return reflection

    async def get_reflection(
        self,
        activity_submission_id: uuid.UUID,
    ) -> Reflection | None:
        """Return the reflection for the given ActivitySubmission, or None."""
        result = await self._session.execute(
            select(Reflection)
            .where(Reflection.activity_submission_id == activity_submission_id)
        )
        return result.scalar_one_or_none()


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

        # Resolve commission_id from enrollment
        commission_id_str = "00000000-0000-0000-0000-000000000000"
        try:
            from app.shared.models.commission import Commission
            enr_result = await self._session.execute(
                select(Enrollment)
                .where(Enrollment.student_id == student_id, Enrollment.is_active.is_(True))
            )
            for enr in enr_result.scalars().all():
                ex_result = await self._session.execute(
                    select(Exercise).where(Exercise.id == exercise_id)
                )
                ex = ex_result.scalar_one_or_none()
                if ex:
                    comm_result = await self._session.execute(
                        select(Commission).where(
                            Commission.id == enr.commission_id,
                            Commission.course_id == ex.course_id,
                        )
                    )
                    if comm_result.scalar_one_or_none():
                        commission_id_str = str(enr.commission_id)
                        break
        except Exception:
            pass

        event = EventOutbox(
            event_type="code.snapshot.captured",
            payload={
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "commission_id": commission_id_str,
                "snapshot_id": str(snapshot.id),
                "snapshot_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        self._session.add(event)

        await self._session.flush()
        return snapshot
