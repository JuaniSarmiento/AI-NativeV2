from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    evaluated = "evaluated"


class ActivitySubmission(Base):
    """A student's submission of an entire activity (all exercises at once).

    Schema: operational.
    """

    __tablename__ = "activity_submissions"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("operational.activities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("operational.users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", schema="operational"),
        nullable=False, default=SubmissionStatus.pending, server_default=text("'pending'"),
    )
    total_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="Set by AI evaluator",
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    activity: Mapped["Activity"] = relationship("Activity", foreign_keys=[activity_id])
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="activity_submission",
    )
    reflection: Mapped["Reflection | None"] = relationship(
        "Reflection", back_populates="activity_submission", uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ActivitySubmission id={self.id} attempt={self.attempt_number} status={self.status.value}>"


class Submission(Base):
    """A student's code submission for a single exercise within an activity.

    Schema: operational.
    """

    __tablename__ = "submissions"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("operational.users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("operational.exercises.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    activity_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("operational.activity_submissions.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", schema="operational", create_type=False),
        nullable=False, default=SubmissionStatus.pending, server_default=text("'pending'"),
    )
    score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="Set by AI evaluator",
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI evaluation feedback")
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    exercise: Mapped["Exercise"] = relationship("Exercise", foreign_keys=[exercise_id])
    activity_submission: Mapped["ActivitySubmission | None"] = relationship(
        "ActivitySubmission", back_populates="submissions",
    )

    def __repr__(self) -> str:
        return f"<Submission id={self.id} exercise={self.exercise_id} status={self.status.value}>"


class CodeSnapshot(Base):
    """Immutable snapshot of student code at a point in time.

    Evidence of cognitive process. NEVER updated or deleted.
    Schema: operational.
    """

    __tablename__ = "code_snapshots"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CodeSnapshot id={self.id} exercise={self.exercise_id}>"


class Reflection(Base):
    """Student's post-exercise reflection linked one-to-one with an ActivitySubmission.

    Captures difficulty perception, strategy description, AI usage evaluation,
    what the student would change, and confidence level — all used by the
    Cognitive Trace Engine (Fase 3) to assess N3/N4 indicators.

    Schema: operational.
    """

    __tablename__ = "reflections"
    __table_args__ = (
        CheckConstraint("difficulty_perception BETWEEN 1 AND 5", name="ck_reflections_difficulty_range"),
        CheckConstraint("confidence_level BETWEEN 1 AND 5", name="ck_reflections_confidence_range"),
        UniqueConstraint("activity_submission_id", name="uq_reflections_activity_submission_id"),
        {"schema": "operational"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    activity_submission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.activity_submissions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    difficulty_perception: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="1 (very easy) to 5 (very hard)",
    )
    strategy_description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Free-text description of the strategy used",
    )
    ai_usage_evaluation: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Student's self-evaluation of AI usage during the exercise",
    )
    what_would_change: Mapped[str] = mapped_column(
        Text, nullable=False, comment="What the student would do differently next time",
    )
    confidence_level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="1 (not confident) to 5 (very confident)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    activity_submission: Mapped["ActivitySubmission"] = relationship(
        "ActivitySubmission", back_populates="reflection",
    )
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<Reflection id={self.id} "
            f"activity_submission={self.activity_submission_id} "
            f"difficulty={self.difficulty_perception}>"
        )
