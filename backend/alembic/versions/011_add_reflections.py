"""Add reflections table for post-exercise student reflection (EPIC-12).

Revision ID: 011
Revises: 010
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "011"
down_revision: str = "010"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "reflections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "activity_submission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.activity_submissions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "difficulty_perception",
            sa.SmallInteger(),
            nullable=False,
            comment="1 (very easy) to 5 (very hard)",
        ),
        sa.Column(
            "strategy_description",
            sa.Text(),
            nullable=False,
            comment="Free-text description of the strategy used",
        ),
        sa.Column(
            "ai_usage_evaluation",
            sa.Text(),
            nullable=False,
            comment="Student's self-evaluation of AI usage during the exercise",
        ),
        sa.Column(
            "what_would_change",
            sa.Text(),
            nullable=False,
            comment="What the student would do differently next time",
        ),
        sa.Column(
            "confidence_level",
            sa.SmallInteger(),
            nullable=False,
            comment="1 (not confident) to 5 (very confident)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "difficulty_perception BETWEEN 1 AND 5",
            name="ck_reflections_difficulty_range",
        ),
        sa.CheckConstraint(
            "confidence_level BETWEEN 1 AND 5",
            name="ck_reflections_confidence_range",
        ),
        sa.UniqueConstraint(
            "activity_submission_id",
            name="uq_reflections_activity_submission_id",
        ),
        schema="operational",
    )

    op.create_index(
        "ix_reflections_student_id",
        "reflections",
        ["student_id"],
        schema="operational",
    )
    op.create_index(
        "ix_reflections_activity_submission_id",
        "reflections",
        ["activity_submission_id"],
        schema="operational",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reflections_activity_submission_id",
        table_name="reflections",
        schema="operational",
    )
    op.drop_index(
        "ix_reflections_student_id",
        table_name="reflections",
        schema="operational",
    )
    op.drop_table("reflections", schema="operational")
