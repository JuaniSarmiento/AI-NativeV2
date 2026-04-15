from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class Enrollment(Base):
    """Links a student (User) to a commission.

    Schema: operational.
    Unique constraint: one enrollment per (student, commission).
    """

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "commission_id", name="uq_enrollments_student_commission"),
        {"schema": "operational"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.commissions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relationships
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    commission: Mapped["Commission"] = relationship("Commission", foreign_keys=[commission_id])

    def __repr__(self) -> str:
        return f"<Enrollment id={self.id} student={self.student_id} commission={self.commission_id}>"
