from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class CognitiveReport(Base):
    """AI-generated cognitive report for a student+activity pair.

    Schema: cognitive — owned by Fase 3.
    """

    __tablename__ = "cognitive_reports"
    __table_args__ = (
        UniqueConstraint("student_id", "activity_id", "data_hash", name="uq_cognitive_reports_student_activity_hash"),
        Index("ix_cognitive_reports_student_activity", "student_id", "activity_id"),
        {"schema": "cognitive"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True,
    )
    commission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False,
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False,
    )
    structured_analysis: Mapped[dict] = mapped_column(PG_JSON, nullable=False)
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    narrative_md: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CognitiveReport id={self.id} student={self.student_id} activity={self.activity_id}>"
