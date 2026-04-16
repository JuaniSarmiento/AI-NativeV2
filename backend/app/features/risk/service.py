"""RiskWorker — detects risk factors per student/commission.

Pure domain service. No FastAPI imports. Receives repositories via
constructor injection. All factor detection returns a dict or None.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cognitive.models import CognitiveSession
from app.features.evaluation.models import CognitiveMetrics
from app.features.evaluation.repositories import CognitiveMetricsRepository
from app.features.risk.repositories import RiskAssessmentRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEPENDENCY_THRESHOLD = 0.5
_DEPENDENCY_SESSIONS = 5
_DISENGAGEMENT_MIN_SESSIONS = 2
_DISENGAGEMENT_WINDOW_DAYS = 7
_STAGNATION_MIN_SESSIONS = 3

_FACTOR_LABELS = {
    "dependency": "Dependencia de la IA",
    "disengagement": "Desvinculacion",
    "stagnation": "Estancamiento",
}

_RECOMMENDATIONS = {
    "dependency": (
        "El alumno muestra alta dependencia del tutor IA. "
        "Se recomienda fomentar la resolucion autonoma antes de consultar."
    ),
    "disengagement": (
        "El alumno presenta baja actividad reciente. "
        "Se recomienda contactarlo para verificar su situacion."
    ),
    "stagnation": (
        "Los puntajes del alumno no muestran mejora. "
        "Se recomienda revisar su comprension de los conceptos base."
    ),
}


class RiskWorker:
    """Analyzes accumulated CognitiveMetrics and produces RiskAssessments."""

    def __init__(
        self,
        metrics_repo: CognitiveMetricsRepository,
        risk_repo: RiskAssessmentRepository,
        session: AsyncSession,
    ) -> None:
        self._metrics_repo = metrics_repo
        self._risk_repo = risk_repo
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assess_student(
        self,
        student_id: uuid.UUID,
        commission_id: uuid.UUID,
        triggered_by: str = "automatic",
    ) -> dict[str, Any] | None:
        """Run risk analysis for a single student in a commission.

        Returns the upserted assessment data dict, or None if no
        sessions exist for this student/commission.
        """
        metrics_list = await self._get_student_metrics(student_id, commission_id)
        sessions = await self._get_student_sessions(student_id, commission_id)

        if not sessions:
            return None

        factors: dict[str, Any] = {}

        dep = self._detect_dependency_factor(metrics_list)
        if dep is not None:
            factors["dependency"] = dep

        dis = self._detect_disengagement_factor(sessions)
        if dis is not None:
            factors["disengagement"] = dis

        stag = self._detect_stagnation_factor(metrics_list)
        if stag is not None:
            factors["stagnation"] = stag

        risk_level = self._compute_risk_level(factors)
        recommendation = self._generate_recommendation(factors)

        data = {
            "student_id": student_id,
            "commission_id": commission_id,
            "risk_level": risk_level,
            "risk_factors": factors,
            "recommendation": recommendation,
            "triggered_by": triggered_by,
        }

        await self._risk_repo.upsert_daily(data)

        logger.info(
            "Risk assessed",
            extra={
                "student_id": str(student_id),
                "commission_id": str(commission_id),
                "risk_level": risk_level,
                "factors": list(factors.keys()),
            },
        )

        return data

    async def assess_commission(
        self,
        commission_id: uuid.UUID,
        triggered_by: str = "automatic",
    ) -> int:
        """Run risk analysis for all students in a commission.

        Returns the count of assessments created/updated.
        """
        student_ids = await self._get_commission_student_ids(commission_id)
        count = 0

        for sid in student_ids:
            result = await self.assess_student(sid, commission_id, triggered_by)
            if result is not None:
                count += 1

        logger.info(
            "Commission risk assessment complete",
            extra={
                "commission_id": str(commission_id),
                "assessed_count": count,
                "total_students": len(student_ids),
            },
        )

        return count

    # ------------------------------------------------------------------
    # Factor detection
    # ------------------------------------------------------------------

    def _detect_dependency_factor(
        self, metrics_list: list[CognitiveMetrics]
    ) -> dict[str, Any] | None:
        recent = metrics_list[:_DEPENDENCY_SESSIONS]
        if not recent:
            return None

        scores = [
            float(m.dependency_score)
            for m in recent
            if m.dependency_score is not None
        ]
        if not scores:
            return None

        avg = sum(scores) / len(scores)
        above = sum(1 for s in scores if s > _DEPENDENCY_THRESHOLD)

        if avg <= _DEPENDENCY_THRESHOLD:
            return None

        return {
            "score": round(avg, 3),
            "sessions_above_threshold": above,
            "threshold": _DEPENDENCY_THRESHOLD,
        }

    def _detect_disengagement_factor(
        self, sessions: list[CognitiveSession]
    ) -> dict[str, Any] | None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_DISENGAGEMENT_WINDOW_DAYS)
        recent = [s for s in sessions if s.started_at >= cutoff]
        count = len(recent)

        if count >= _DISENGAGEMENT_MIN_SESSIONS:
            return None

        score = 1.0 - (count / _DISENGAGEMENT_MIN_SESSIONS)
        return {
            "score": round(score, 3),
            "recent_sessions": count,
            "expected_minimum": _DISENGAGEMENT_MIN_SESSIONS,
        }

    def _detect_stagnation_factor(
        self, metrics_list: list[CognitiveMetrics]
    ) -> dict[str, Any] | None:
        recent = metrics_list[:_STAGNATION_MIN_SESSIONS]
        if len(recent) < _STAGNATION_MIN_SESSIONS:
            return None

        def _avg_n(m: CognitiveMetrics) -> float | None:
            scores = [
                float(s)
                for s in [
                    m.n1_comprehension_score,
                    m.n2_strategy_score,
                    m.n3_validation_score,
                    m.n4_ai_interaction_score,
                ]
                if s is not None
            ]
            return sum(scores) / len(scores) if scores else None

        avgs = [_avg_n(m) for m in recent]
        valid = [(i, v) for i, v in enumerate(avgs) if v is not None]
        if len(valid) < 2:
            return None

        # Simple slope: (last - first) / (n-1)
        # recent is ordered newest first, so reverse for chronological
        valid_chrono = list(reversed(valid))
        first_val = valid_chrono[0][1]
        last_val = valid_chrono[-1][1]
        slope = (last_val - first_val) / (len(valid_chrono) - 1)

        if slope >= 0:
            return None

        # Normalize: -50 slope → score 1.0, 0 slope → score 0
        score = min(1.0, abs(slope) / 50.0)
        trend = "declining"

        return {
            "score": round(score, 3),
            "trend": trend,
            "sessions_analyzed": len(recent),
        }

    # ------------------------------------------------------------------
    # Risk level + recommendation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_risk_level(factors: dict[str, Any]) -> str:
        if not factors:
            return "low"

        scores = [f["score"] for f in factors.values()]
        high_scores = [s for s in scores if s >= 0.6]

        if any(s >= 0.8 for s in scores):
            return "critical"
        if len(high_scores) >= 2:
            return "critical"
        if any(s >= 0.6 for s in scores):
            return "high"
        if any(s >= 0.4 for s in scores):
            return "medium"
        return "low"

    @staticmethod
    def _generate_recommendation(factors: dict[str, Any]) -> str | None:
        if not factors:
            return None

        parts = []
        for key in factors:
            if key in _RECOMMENDATIONS:
                parts.append(_RECOMMENDATIONS[key])

        return " ".join(parts) if parts else None

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    async def _get_student_metrics(
        self,
        student_id: uuid.UUID,
        commission_id: uuid.UUID,
    ) -> list[CognitiveMetrics]:
        """Fetch recent CognitiveMetrics for a student in a commission."""
        stmt = (
            select(CognitiveMetrics)
            .join(
                CognitiveSession,
                CognitiveMetrics.session_id == CognitiveSession.id,
            )
            .where(
                CognitiveSession.student_id == student_id,
                CognitiveSession.commission_id == commission_id,
                CognitiveSession.status == "closed",
            )
            .order_by(CognitiveMetrics.computed_at.desc())
            .limit(10)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _get_student_sessions(
        self,
        student_id: uuid.UUID,
        commission_id: uuid.UUID,
    ) -> list[CognitiveSession]:
        """Fetch all sessions for a student in a commission."""
        stmt = (
            select(CognitiveSession)
            .where(
                CognitiveSession.student_id == student_id,
                CognitiveSession.commission_id == commission_id,
            )
            .order_by(CognitiveSession.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _get_commission_student_ids(
        self, commission_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Get distinct student IDs from cognitive sessions for a commission."""
        stmt = (
            select(func.distinct(CognitiveSession.student_id))
            .where(CognitiveSession.commission_id == commission_id)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
