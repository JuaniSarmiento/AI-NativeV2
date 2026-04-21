from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
from app.core.llm import get_adapter
from app.features.activities.services import LLMConfigService
from app.features.reports.analytical import (
    InsufficientDataError,
    build_structured_analysis,
    compute_data_hash,
)
from app.features.reports.models import CognitiveReport
from app.features.reports.narrative import generate_narrative
from app.features.reports.repository import CognitiveReportRepository
from app.shared.models.activity import Activity
from app.shared.models.llm_config import LLMConfig
from app.shared.models.user import User


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session
        self._repo = CognitiveReportRepository(session)
        self._llm_config_service = LLMConfigService(session)

    async def generate_report(
        self,
        student_id: uuid.UUID,
        activity_id: uuid.UUID,
        commission_id: uuid.UUID,
        requested_by: uuid.UUID,
    ) -> CognitiveReport:
        llm_config = await self._llm_config_service.get(requested_by)
        if llm_config is None:
            raise ValidationError(
                "Necesitás configurar una API key de LLM para generar informes. "
                "Andá a Configuración → API Key."
            )

        student = (await self._db.execute(
            select(User).where(User.id == student_id)
        )).scalar_one_or_none()
        if not student:
            raise NotFoundError(resource="User", identifier=str(student_id))

        activity = (await self._db.execute(
            select(Activity).where(Activity.id == activity_id)
        )).scalar_one_or_none()
        if not activity:
            raise NotFoundError(resource="Activity", identifier=str(activity_id))

        try:
            analysis = await build_structured_analysis(
                db=self._db,
                student_id=student_id,
                activity_id=activity_id,
                student_name=student.full_name,
                activity_title=activity.title,
            )
        except InsufficientDataError as e:
            raise ValidationError(str(e))

        data_hash = compute_data_hash(analysis)

        cached = await self._repo.get_by_hash(student_id, activity_id, data_hash)
        if cached is not None:
            return cached

        api_key = self._llm_config_service.decrypt_key(llm_config)
        adapter = get_adapter(
            provider=llm_config.provider.value,
            api_key=api_key,
            model_name=llm_config.model_name,
        )

        try:
            narrative_md = await generate_narrative(adapter, analysis)
        except Exception as exc:
            logger.error("LLM call failed during report generation: %s", exc)
            raise ValidationError(
                "El proveedor de LLM no está disponible en este momento. "
                "Intentá de nuevo en unos minutos."
            )

        report = CognitiveReport(
            student_id=student_id,
            activity_id=activity_id,
            commission_id=commission_id,
            generated_by=requested_by,
            structured_analysis=analysis,
            data_hash=data_hash,
            narrative_md=narrative_md,
            llm_provider=llm_config.provider.value,
            model_used=llm_config.model_name,
        )
        self._db.add(report)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            cached = await self._repo.get_by_hash(student_id, activity_id, data_hash)
            if cached is not None:
                return cached
            raise
        return report

    async def get_report(self, report_id: uuid.UUID) -> CognitiveReport:
        report = await self._repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError(resource="CognitiveReport", identifier=str(report_id))
        return report

    async def get_latest_report(
        self,
        student_id: uuid.UUID,
        activity_id: uuid.UUID,
    ) -> CognitiveReport | None:
        return await self._repo.get_latest(student_id, activity_id)
