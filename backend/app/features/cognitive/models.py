from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class SessionStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    invalidated = "invalidated"


class CognitiveSession(Base):
    """Tracks a single student's cognitive engagement with one exercise.

    Schema: cognitive — owned exclusively by Fase 3.

    student_id, exercise_id, and commission_id are stored without FK
    constraints to avoid cross-schema dependencies (those entities live in
    the operational schema).  The hash chain starts with genesis_hash and
    advances with every CognitiveEvent appended to this session.
    """

    __tablename__ = "cognitive_sessions"
    __table_args__ = (
        Index("ix_cognitive_sessions_student_id", "student_id"),
        Index("ix_cognitive_sessions_exercise_id", "exercise_id"),
        Index("ix_cognitive_sessions_status", "status"),
        {"schema": "cognitive"},
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
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Exercise ID — no FK, lives in operational schema",
    )
    commission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Commission ID — denormalized for scoped queries without cross-schema joins",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    genesis_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 anchor for the hash chain: SHA256('GENESIS:' + session_id + ':' + started_at_iso)",
    )
    session_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 of the last event when the session closes — seals the chain",
    )
    n4_final_score: Mapped[dict | None] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=True,
        comment="Evaluation scores for N1-N4 levels, set by the Evaluation Engine",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default=text("'open'"),
    )

    # Relationships
    events: Mapped[list[CognitiveEvent]] = relationship(
        "CognitiveEvent",
        back_populates="session",
        order_by="CognitiveEvent.sequence_number",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CognitiveSession id={self.id} student={self.student_id} "
            f"exercise={self.exercise_id} status={self.status}>"
        )


class CognitiveEvent(Base):
    """A single immutable event in the CTR hash chain.

    Schema: cognitive — owned exclusively by Fase 3.

    CRITICAL: cognitive_events are IMMUTABLE after creation.  There is no
    updated_at column, no soft-delete, and no UPDATE operations.
    The hash chain guarantees tamper-evidence: any modification breaks
    verify_chain() because recalculated hashes will not match stored ones.
    """

    __tablename__ = "cognitive_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence_number",
            name="uq_cognitive_events_session_sequence",
        ),
        Index("ix_cognitive_events_session_id", "session_id"),
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
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Canonical CTR event type, e.g. 'reads_problem', 'code.run', 'tutor.question_asked'",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1-based monotonically increasing sequence within the session",
    )
    payload: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Original event payload, optionally enriched by the classifier",
    )
    previous_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of the previous event (or genesis_hash for sequence 1)",
    )
    event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256(previous_hash + ':' + event_type + ':' + json(payload) + ':' + created_at_iso)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship
    session: Mapped[CognitiveSession] = relationship(
        "CognitiveSession",
        back_populates="events",
    )

    def __repr__(self) -> str:
        return (
            f"<CognitiveEvent id={self.id} session={self.session_id} "
            f"seq={self.sequence_number} type={self.event_type!r}>"
        )
