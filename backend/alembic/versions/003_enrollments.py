"""Create enrollments table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "commission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.commissions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.UniqueConstraint(
            "student_id",
            "commission_id",
            name="uq_enrollments_student_commission",
        ),
        schema="operational",
    )
    op.create_index(
        "ix_enrollments_student_id",
        "enrollments",
        ["student_id"],
        schema="operational",
    )
    op.create_index(
        "ix_enrollments_commission_id",
        "enrollments",
        ["commission_id"],
        schema="operational",
    )


def downgrade() -> None:
    op.drop_index("ix_enrollments_commission_id", table_name="enrollments", schema="operational")
    op.drop_index("ix_enrollments_student_id", table_name="enrollments", schema="operational")
    op.drop_table("enrollments", schema="operational")
