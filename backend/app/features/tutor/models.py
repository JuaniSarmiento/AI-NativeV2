from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class InteractionRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class TutorInteraction(Base):
    """A single chat turn between student and tutor.

    Each interaction records the message content, the active prompt hash
    for cryptographic reconstruction, and an optional N4 classification
    (set later by EPIC-11 classifier).

    Schema: operational.
    """

    __tablename__ = "tutor_interactions"
    __table_args__ = (
        CheckConstraint(
            "n4_level IS NULL OR (n4_level >= 1 AND n4_level <= 4)",
            name="n4_level_range",
        ),
        {"schema": "operational"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Logical correlation with cognitive_sessions.id — no FK cross-schema",
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[InteractionRole] = mapped_column(
        Enum(InteractionRole, name="interaction_role", schema="operational"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    n4_level: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="N4 classification (1-4), set by EPIC-11 classifier",
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of the system prompt active at interaction time",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<TutorInteraction id={self.id} role={self.role.value} exercise={self.exercise_id}>"


class TutorSystemPrompt(Base):
    """Versioned system prompt for the tutor.

    SHA-256 hash is auto-computed from content. Only one prompt can be
    active at a time.

    Schema: governance.
    """

    __tablename__ = "tutor_system_prompts"
    __table_args__ = {"schema": "governance"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 of content — auto-computed",
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    guardrails_config: Mapped[dict | None] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Admin user ID — no FK cross-schema, validated in service layer",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<TutorSystemPrompt id={self.id} name={self.name!r} active={self.is_active}>"
