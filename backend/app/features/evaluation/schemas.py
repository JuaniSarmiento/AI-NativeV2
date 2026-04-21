"""Pydantic v2 DTOs for the Cognitive Metrics / Evaluation Engine API.

All UUIDs serialised as str at the API boundary.
All Decimal values serialised as float for JSON compatibility.

The standard response envelope is:
  { "status": "ok"|"error", "data": {...}, "meta": {...}, "errors": [...] }

IMPORTANT: Anti-gaming rule — StudentProgressResponse does NOT expose
dependency_score, risk_level, or help_seeking_ratio to prevent gaming.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base DTOs
# ---------------------------------------------------------------------------


class CognitiveMetricsResponse(BaseModel):
    """Read DTO for a CognitiveMetrics row.

    Intended for docente/admin endpoints — includes all fields including
    risk classification and dependency scores.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    n1_comprehension_score: float | None = None
    n2_strategy_score: float | None = None
    n3_validation_score: float | None = None
    n4_ai_interaction_score: float | None = None
    total_interactions: int = 0
    help_seeking_ratio: float | None = None
    autonomy_index: float | None = None
    qe_score: float | None = None
    qe_quality_prompt: float | None = None
    qe_critical_evaluation: float | None = None
    qe_integration: float | None = None
    qe_verification: float | None = None
    dependency_score: float | None = None
    reflection_score: float | None = None
    success_efficiency: float | None = None
    risk_level: str | None = None
    computed_at: datetime | None = None
    created_at: datetime
    # Coherence scores (EPIC-20 Fase C)
    temporal_coherence_score: float | None = None
    code_discourse_score: float | None = None
    inter_iteration_score: float | None = None
    coherence_anomalies: dict | None = None
    prompt_type_distribution: dict | None = None

    @classmethod
    def from_orm(cls, obj: object) -> "CognitiveMetricsResponse":
        def _f(val: Any) -> float | None:
            return float(val) if val is not None else None

        return cls(
            id=str(getattr(obj, "id")),
            session_id=str(getattr(obj, "session_id")),
            n1_comprehension_score=_f(getattr(obj, "n1_comprehension_score", None)),
            n2_strategy_score=_f(getattr(obj, "n2_strategy_score", None)),
            n3_validation_score=_f(getattr(obj, "n3_validation_score", None)),
            n4_ai_interaction_score=_f(getattr(obj, "n4_ai_interaction_score", None)),
            total_interactions=getattr(obj, "total_interactions", 0),
            help_seeking_ratio=_f(getattr(obj, "help_seeking_ratio", None)),
            autonomy_index=_f(getattr(obj, "autonomy_index", None)),
            qe_score=_f(getattr(obj, "qe_score", None)),
            qe_quality_prompt=_f(getattr(obj, "qe_quality_prompt", None)),
            qe_critical_evaluation=_f(getattr(obj, "qe_critical_evaluation", None)),
            qe_integration=_f(getattr(obj, "qe_integration", None)),
            qe_verification=_f(getattr(obj, "qe_verification", None)),
            dependency_score=_f(getattr(obj, "dependency_score", None)),
            reflection_score=_f(getattr(obj, "reflection_score", None)),
            success_efficiency=_f(getattr(obj, "success_efficiency", None)),
            risk_level=getattr(obj, "risk_level", None),
            computed_at=getattr(obj, "computed_at", None),
            created_at=getattr(obj, "created_at"),
            # Coherence scores (EPIC-20 Fase C)
            temporal_coherence_score=_f(getattr(obj, "temporal_coherence_score", None)),
            code_discourse_score=_f(getattr(obj, "code_discourse_score", None)),
            inter_iteration_score=_f(getattr(obj, "inter_iteration_score", None)),
            coherence_anomalies=getattr(obj, "coherence_anomalies", None),
            prompt_type_distribution=getattr(obj, "prompt_type_distribution", None),
        )


# ---------------------------------------------------------------------------
# Student-safe DTO (anti-gaming — no risk/dependency exposure)
# ---------------------------------------------------------------------------


class StudentProgressItem(BaseModel):
    """Per-session progress snapshot for a student.

    Intentionally omits dependency_score, risk_level, and help_seeking_ratio
    to prevent gaming the evaluation system.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    exercise_id: str
    n1_comprehension_score: float | None = None
    n2_strategy_score: float | None = None
    n3_validation_score: float | None = None
    n4_ai_interaction_score: float | None = None
    qe_score: float | None = None
    autonomy_index: float | None = None
    success_efficiency: float | None = None
    computed_at: datetime | None = None


class StudentProgressResponse(BaseModel):
    """Aggregated progress for the currently authenticated student.

    Provides evolution across sessions without exposing audit-level fields.
    """

    sessions: list[StudentProgressItem] = Field(default_factory=list)
    session_count: int = 0
    avg_n1: float | None = None
    avg_n2: float | None = None
    avg_n3: float | None = None
    avg_n4: float | None = None
    avg_qe: float | None = None


# ---------------------------------------------------------------------------
# Teacher / admin DTOs
# ---------------------------------------------------------------------------


class StudentSummary(BaseModel):
    """Brief cognitive profile for one student in a commission dashboard."""

    student_id: str
    student_name: str | None = None
    student_email: str | None = None
    session_count: int = 0
    latest_n1: float | None = None
    latest_n2: float | None = None
    latest_n3: float | None = None
    latest_n4: float | None = None
    latest_qe: float | None = None
    latest_risk_level: str | None = None
    avg_dependency: float | None = None
    # Coherence and appropriation fields (EPIC-20 Fase C)
    latest_temporal_coherence: float | None = None
    latest_code_discourse: float | None = None
    latest_inter_iteration: float | None = None
    latest_appropriation_type: str | None = None  # delegacion | superficial | reflexiva | autonomo
    latest_score_breakdown: dict | None = None


class DashboardResponse(BaseModel):
    """Commission-level aggregated dashboard for docente/admin."""

    commission_id: str
    exercise_id: str | None = None
    student_count: int = 0
    avg_n1: float | None = None
    avg_n2: float | None = None
    avg_n3: float | None = None
    avg_n4: float | None = None
    avg_qe: float | None = None
    avg_dependency: float | None = None
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    students: list[StudentSummary] = Field(default_factory=list)


class StudentProfileResponse(BaseModel):
    """Detailed cognitive profile for a specific student — for docente/admin."""

    student_id: str
    metrics: list[CognitiveMetricsResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 1


# ---------------------------------------------------------------------------
# Standard envelope wrappers
# ---------------------------------------------------------------------------


class MetaBlock(BaseModel):
    """Standard meta block for list responses."""

    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 1


class MetricsStandardResponse(BaseModel):
    """Standard envelope: single CognitiveMetrics."""

    status: str = "ok"
    data: CognitiveMetricsResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class DashboardStandardResponse(BaseModel):
    """Standard envelope: commission dashboard."""

    status: str = "ok"
    data: DashboardResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class StudentProfileStandardResponse(BaseModel):
    """Standard envelope: student profile (docente view)."""

    status: str = "ok"
    data: StudentProfileResponse
    meta: MetaBlock = Field(default_factory=MetaBlock)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class StudentProgressStandardResponse(BaseModel):
    """Standard envelope: student progress (alumno view)."""

    status: str = "ok"
    data: StudentProgressResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Evolution endpoint DTOs (Task 6.6)
# ---------------------------------------------------------------------------


class EvolutionItem(BaseModel):
    """One session entry in a student's cognitive evolution over time."""

    session_id: str
    exercise_id: str
    exercise_title: str | None = None
    started_at: datetime
    n1: float | None = None
    n2: float | None = None
    n3: float | None = None
    n4: float | None = None
    qe: float | None = None
    risk_level: str | None = None


class EvolutionResponse(BaseModel):
    """List of cognitive snapshots ordered by session start time."""

    student_id: str
    commission_id: str
    items: list[EvolutionItem] = Field(default_factory=list)


class EvolutionStandardResponse(BaseModel):
    """Standard envelope: student cognitive evolution."""

    status: str = "ok"
    data: EvolutionResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
