from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GenerateReportRequest(BaseModel):
    student_id: uuid.UUID
    activity_id: uuid.UUID
    commission_id: uuid.UUID


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    activity_id: str
    commission_id: str
    structured_analysis: dict[str, Any]
    narrative_md: str
    llm_provider: str
    model_used: str
    generated_at: datetime

    @classmethod
    def from_orm(cls, obj: Any) -> "ReportResponse":
        return cls(
            id=str(obj.id),
            student_id=str(obj.student_id),
            activity_id=str(obj.activity_id),
            commission_id=str(obj.commission_id),
            structured_analysis=obj.structured_analysis,
            narrative_md=obj.narrative_md,
            llm_provider=obj.llm_provider,
            model_used=obj.model_used,
            generated_at=obj.generated_at,
        )


class ReportStandardResponse(BaseModel):
    status: str = "ok"
    data: ReportResponse | None = None
