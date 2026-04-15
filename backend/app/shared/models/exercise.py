from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class ExerciseDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class Exercise(Base):
    """A coding exercise within a course.

    Schema: operational.
    """

    __tablename__ = "exercises"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    test_cases: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Structured test cases: { language, timeout_ms, memory_limit_mb, cases: [...] }",
    )
    difficulty: Mapped[ExerciseDifficulty] = mapped_column(
        Enum(ExerciseDifficulty, name="exercise_difficulty", schema="operational"),
        nullable=False,
    )
    topic_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'::text[]"),
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="python",
        server_default=text("'python'"),
    )
    starter_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    max_attempts: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=10,
        server_default=text("10"),
    )
    time_limit_minutes: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=60,
        server_default=text("60"),
    )
    rubric: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Evaluation rubric for AI grading — criteria, expected approach, common mistakes",
    )
    order_index: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", foreign_keys=[course_id])
    activity: Mapped["Activity | None"] = relationship(
        "Activity", back_populates="exercises", foreign_keys=[activity_id],
    )

    def __repr__(self) -> str:
        return f"<Exercise id={self.id} title={self.title!r} difficulty={self.difficulty.value}>"
