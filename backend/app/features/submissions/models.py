from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    Text,
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
