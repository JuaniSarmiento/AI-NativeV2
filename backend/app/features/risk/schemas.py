"""Pydantic v2 DTOs for Risk Assessment API.

Standard response envelope: { status, data, meta, errors }
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    commission_id: str
    risk_level: str
    risk_factors: dict[str, Any]
    recommendation: str | None = None
    triggered_by: str
    assessed_at: datetime
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


class MetaBlock(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 1


class RiskAssessmentListResponse(BaseModel):
    status: str = "ok"
    data: list[RiskAssessmentResponse] = Field(default_factory=list)
    meta: MetaBlock = Field(default_factory=MetaBlock)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class RiskAssessmentStandardResponse(BaseModel):
    status: str = "ok"
    data: RiskAssessmentResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class AssessCommissionResponse(BaseModel):
    status: str = "ok"
    data: dict[str, int] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
