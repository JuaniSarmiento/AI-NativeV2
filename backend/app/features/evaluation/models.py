from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class CognitiveMetrics(Base):
    """Computed N1-N4 cognitive metrics for a closed CognitiveSession.

    Schema: cognitive — owned exclusively by Fase 3.

    1:1 with CognitiveSession. Created by MetricsEngine when a session
    is closed. Immutable in spirit — never updated, only ever inserted once.

    All score columns use NUMERIC types (not FLOAT) to ensure exact decimal
    representation when storing evaluation scores.

    risk_level uses String(20), NOT a PostgreSQL ENUM, to avoid
    DuplicateObjectError when the schema is created multiple times (e.g. in
    tests or after a failed migration rollback).
    """

    __tablename__ = "cognitive_metrics"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_cognitive_metrics_session_id"),
        Index("ix_cognitive_metrics_session_id", "session_id", unique=True),
        Index("ix_cognitive_metrics_risk_level", "risk_level"),
        {"schema": "cognitive"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cognitive.cognitive_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # --- N1-N4 raw scores (0-100 range) ---
    n1_comprehension_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="N1 comprehension score 0-100",
    )
    n2_strategy_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="N2 strategy score 0-100",
    )
    n3_validation_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="N3 validation score 0-100",
    )
    n4_ai_interaction_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="N4 AI interaction quality score 0-100",
    )

    # --- Interaction ratios ---
    total_interactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total number of CTR events in the session",
    )
    help_seeking_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="Fraction of events that are tutor interactions (0-1)",
    )
    autonomy_index: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="1 - help_seeking_ratio",
    )

    # --- Qe (epistemic quality) composite and sub-scores ---
    qe_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Composite epistemic quality score 0-100",
    )
    qe_quality_prompt: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Quality of prompts sent to tutor 0-100",
    )
    qe_critical_evaluation: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Degree to which student evaluated tutor responses critically 0-100",
    )
    qe_integration: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Successful code integration after tutor guidance 0-100",
    )
    qe_verification: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Degree to which student verified code changes 0-100",
    )

    # --- Dependency and reflection ---
    dependency_score: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="Fraction of AI interactions classified as dependent (0-1)",
    )
    reflection_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Post-exercise reflection quality 0-100 (placeholder for Fase 3 expansion)",
    )
    success_efficiency: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Successful code runs / total code runs ratio * 100",
    )

    # --- Coherence scores (Fase C — EPIC-20) ---
    temporal_coherence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Temporal coherence of N-level event sequences 0-100",
    )
    code_discourse_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Coherence between chat discourse and code changes 0-100",
    )
    inter_iteration_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Consistency across code iterations 0-100",
    )
    coherence_anomalies: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detected anomaly patterns: solution_without_comprehension, pure_delegation, etc.",
    )
    prompt_type_distribution: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Distribution of prompt types: {exploratory: N, verifier: N, generative: N}",
    )

    # --- Risk classification ---
    risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Risk classification: critical, high, medium, low",
    )

    # --- Audit ---
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the MetricsEngine produced this record",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship (read-only — no cascade writes)
    session: Mapped["CognitiveSession"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CognitiveSession",
        foreign_keys=[session_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CognitiveMetrics id={self.id} session={self.session_id} "
            f"risk={self.risk_level}>"
        )


class ReasoningRecord(Base):
    """Immutable audit record of a MetricsEngine computation.

    Schema: cognitive — owned exclusively by Fase 3.

    CRITICAL: ReasoningRecords are IMMUTABLE after creation.
    No update or delete methods exist on the repository.
    The hash chain (previous_hash → event_hash) allows cross-referencing
    with the CognitiveEvent chain to detect tampering.

    record_type uses String(50), NOT a PostgreSQL ENUM, to avoid
    DuplicateObjectError on repeated schema creation.
    """

    __tablename__ = "reasoning_records"
    __table_args__ = (
        Index("ix_reasoning_records_session_id", "session_id"),
        {"schema": "cognitive"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cognitive.cognitive_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    record_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of reasoning record, e.g. 'metrics_computation', 'risk_assessment'",
    )
    details: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Full computation summary produced by MetricsEngine",
    )
    previous_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of the previous reasoning record (or session genesis_hash)",
    )
    event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256(previous_hash + record_type + json(details) + created_at_iso)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<ReasoningRecord id={self.id} session={self.session_id} "
            f"type={self.record_type!r}>"
        )
