from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.features.auth.dependencies import CurrentUser
from app.features.sandbox.engine import SandboxService
from app.features.sandbox.schemas import RunCodeRequest, RunCodeResponse
from app.shared.db.session import get_async_session
from app.shared.models.commission import Commission
from app.shared.models.enrollment import Enrollment
from app.shared.models.event_outbox import EventOutbox
from app.shared.models.exercise import Exercise
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/api/v1/student", tags=["sandbox"])


async def _verify_enrollment(
    session: AsyncSession,
    student_id: uuid.UUID,
    exercise: Exercise,
) -> None:
    result = await session.execute(
        select(Enrollment)
        .join(Commission, Commission.id == Enrollment.commission_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.is_active.is_(True),
            Commission.course_id == exercise.course_id,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise AuthorizationError(
            message="No estas inscripto en el curso de este ejercicio."
        )


@router.post("/exercises/{exercise_id}/run")
async def run_code(
    exercise_id: uuid.UUID,
    body: RunCodeRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Execute student code and return terminal output only.

    Test case evaluation is NOT shown to the student — that happens
    at submission time via AI grading (future EPIC).
    """
    # Fetch exercise
    result = await session.execute(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.is_active.is_(True))
    )
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise NotFoundError(resource="Exercise", identifier=str(exercise_id))

    # Verify enrollment
    await _verify_enrollment(session, current_user.id, exercise)

    # Execute code — terminal mode only (no test case evaluation)
    sandbox = SandboxService()
    exec_result = sandbox.execute(body.code, stdin_data=body.stdin or "")

    # Emit event
    event_type = "code.executed" if exec_result.status == "ok" else "code.execution.failed"
    outbox_event = EventOutbox(
        event_type=event_type,
        payload={
            "student_id": str(current_user.id),
            "exercise_id": str(exercise_id),
            "course_id": str(exercise.course_id),
            "code": body.code[:5000],
            "language": "python",
            "stdout": exec_result.stdout[:2000],
            "stderr": exec_result.stderr[:2000],
            "exit_code": exec_result.exit_code,
            "execution_time_ms": exec_result.runtime_ms,
            "status": exec_result.status,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
    )
    session.add(outbox_event)
    await session.commit()

    return StandardResponse(
        data=RunCodeResponse(
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
            exit_code=exec_result.exit_code,
            runtime_ms=exec_result.runtime_ms,
            status=exec_result.status,
        ),
    ).model_dump()
