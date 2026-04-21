"""Repositories for CognitiveMetrics and ReasoningRecord.

IMPORTANT: Repositories NEVER call session.commit(). The caller's
Unit of Work or transaction context owns commits.

ReasoningRecordRepository intentionally omits update/delete methods
because reasoning records are IMMUTABLE evidence — modifying them
would break the hash chain audit trail.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.evaluation.models import CognitiveMetrics, ReasoningRecord
from app.shared.repositories.base import BaseRepository


class CognitiveMetricsRepository(BaseRepository[CognitiveMetrics]):
    """Repository for CognitiveMetrics persistence.

    Provides session-scoped and student-scoped lookups, plus commission-level
    aggregate queries. All queries stay within the cognitive schema — no
    cross-schema JOINs are performed here.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CognitiveMetrics)

    async def get_by_session(
        self, session_id: uuid.UUID
    ) -> CognitiveMetrics | None:
        """Return the CognitiveMetrics for a specific session, or None."""
        stmt = select(CognitiveMetrics).where(
            CognitiveMetrics.session_id == session_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_student(
        self,
        student_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CognitiveMetrics], int]:
        """Return paginated CognitiveMetrics for all sessions of a student.

        The join is within the cognitive schema only (cognitive_metrics →
        cognitive_sessions). student_id is denormalised on cognitive_sessions.
        """
        from app.features.cognitive.models import CognitiveSession

        base_stmt = (
            select(CognitiveMetrics)
            .join(
                CognitiveSession,
                CognitiveMetrics.session_id == CognitiveSession.id,
            )
            .where(CognitiveSession.student_id == student_id)
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base_stmt
            .order_by(CognitiveMetrics.computed_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_commission_aggregates(
        self,
        commission_id: uuid.UUID,
        exercise_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Return AVG scores, risk level distribution, and student count for a commission.

        Uses DISTINCT ON (student_id) ORDER BY computed_at DESC to get the latest
        metrics per student, then averages over those latest rows. This avoids
        inflating scores from students with many sessions.
        """
        from app.features.cognitive.models import CognitiveSession
        from sqlalchemy import text
        from sqlalchemy.dialects.postgresql import aggregate_order_by

        # Subquery: latest metrics per student
        latest_sub = (
            select(
                CognitiveMetrics.id.label("metrics_id"),
                CognitiveSession.student_id.label("student_id"),
            )
            .join(
                CognitiveSession,
                CognitiveMetrics.session_id == CognitiveSession.id,
            )
            .where(CognitiveSession.commission_id == commission_id)
            .distinct(CognitiveSession.student_id)
            .order_by(CognitiveSession.student_id, CognitiveMetrics.computed_at.desc())
        )
        if exercise_id is not None:
            latest_sub = latest_sub.where(CognitiveSession.exercise_id == exercise_id)

        latest_sub = latest_sub.subquery("latest_per_student")

        # Aggregate over the latest metrics only
        agg_stmt = select(
            func.avg(CognitiveMetrics.n1_comprehension_score).label("avg_n1"),
            func.avg(CognitiveMetrics.n2_strategy_score).label("avg_n2"),
            func.avg(CognitiveMetrics.n3_validation_score).label("avg_n3"),
            func.avg(CognitiveMetrics.n4_ai_interaction_score).label("avg_n4"),
            func.avg(CognitiveMetrics.qe_score).label("avg_qe"),
            func.avg(CognitiveMetrics.dependency_score).label("avg_dependency"),
            func.count(latest_sub.c.student_id).label("student_count"),
        ).select_from(
            CognitiveMetrics.__table__.join(
                latest_sub,
                CognitiveMetrics.__table__.c.id == latest_sub.c.metrics_id,
            )
        )

        agg_result = (await self._session.execute(agg_stmt)).one_or_none()

        # Risk level distribution (also from latest per student)
        risk_stmt = select(
            CognitiveMetrics.risk_level,
            func.count(CognitiveMetrics.id).label("count"),
        ).select_from(
            CognitiveMetrics.__table__.join(
                latest_sub,
                CognitiveMetrics.__table__.c.id == latest_sub.c.metrics_id,
            )
        ).group_by(CognitiveMetrics.risk_level)

        risk_rows = (await self._session.execute(risk_stmt)).all()
        risk_distribution = {row.risk_level or "unknown": row.count for row in risk_rows}

        def _f(val: Any) -> float | None:
            return float(val) if val is not None else None

        return {
            "avg_n1": _f(agg_result.avg_n1) if agg_result else None,
            "avg_n2": _f(agg_result.avg_n2) if agg_result else None,
            "avg_n3": _f(agg_result.avg_n3) if agg_result else None,
            "avg_n4": _f(agg_result.avg_n4) if agg_result else None,
            "avg_qe": _f(agg_result.avg_qe) if agg_result else None,
            "avg_dependency": _f(agg_result.avg_dependency) if agg_result else None,
            "student_count": agg_result.student_count if agg_result else 0,
            "risk_distribution": risk_distribution,
        }


class ReasoningRecordRepository(BaseRepository[ReasoningRecord]):
    """Read-only repository for ReasoningRecord.

    ReasoningRecords are IMMUTABLE evidence — this repository provides
    only creation and reads. No update or delete methods are defined.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReasoningRecord)

    async def get_by_session(
        self, session_id: uuid.UUID
    ) -> list[ReasoningRecord]:
        """Return all reasoning records for a session ordered by created_at ASC."""
        stmt = (
            select(ReasoningRecord)
            .where(ReasoningRecord.session_id == session_id)
            .order_by(ReasoningRecord.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # NOTE: update() and soft_delete() from BaseRepository are intentionally
    # NOT overridden or called — the immutability contract is enforced by
    # convention, not by code (we cannot prevent DB-level direct writes anyway).
