from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class RiskAssessment(Base):
    """Risk assessment for a student within a commission.

    Schema: analytics — owned by Fase 3.

    Tracks accumulated risk factors (dependency, disengagement, stagnation)
    detected by the RiskWorker. One assessment per student/commission/day
    (enforced by unique constraint for idempotency).

    risk_level and triggered_by use String types (not PostgreSQL ENUM)
    to avoid DuplicateObjectError on repeated schema creation.
    """

    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_risk_assessments_student_id", "student_id"),
        Index("ix_risk_assessments_commission_id", "commission_id"),
        Index("ix_risk_assessments_risk_level", "risk_level"),
        # Idempotency (one per student/commission/day) enforced at application
        # layer in RiskAssessmentRepository.upsert_daily().
        {"schema": "analytics"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Student user ID — no FK, lives in operational schema",
    )
    commission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Commission ID — no FK, lives in operational schema",
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Risk classification: low, medium, high, critical",
    )
    risk_factors: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Factor name → {score, ...details} dict",
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable recommendation for the docente (Spanish)",
    )
    triggered_by: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="automatic, manual, or threshold",
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="Docente who acknowledged this alert — no FK",
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<RiskAssessment id={self.id} student={self.student_id} "
            f"commission={self.commission_id} risk={self.risk_level}>"
        )
