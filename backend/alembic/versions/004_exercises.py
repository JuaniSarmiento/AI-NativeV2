"""Create exercises table.

Revision ID: 004
Revises: 003
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str = "003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # Create difficulty ENUM — idempotent via PL/pgSQL exception handler
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE operational.exercise_difficulty AS ENUM ('easy', 'medium', 'hard'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    difficulty_enum = postgresql.ENUM(
        "easy", "medium", "hard",
        name="exercise_difficulty",
        schema="operational",
        create_type=False,
    )

    op.create_table(
        "exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("test_cases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="Structured test cases"),
        sa.Column("difficulty", difficulty_enum, nullable=False),
        sa.Column("topic_tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("language", sa.String(50), nullable=False, server_default=sa.text("'python'")),
        sa.Column("starter_code", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("max_attempts", sa.SmallInteger(), nullable=False, server_default=sa.text("10")),
        sa.Column("time_limit_minutes", sa.SmallInteger(), nullable=False, server_default=sa.text("60")),
        sa.Column("order_index", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="operational",
    )

    op.create_index("ix_exercises_course_id", "exercises", ["course_id"], schema="operational")
    op.create_index("ix_exercises_difficulty", "exercises", ["difficulty"], schema="operational")
    op.create_index(
        "ix_exercises_topic_tags_gin",
        "exercises",
        ["topic_tags"],
        schema="operational",
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_exercises_topic_tags_gin", table_name="exercises", schema="operational")
    op.drop_index("ix_exercises_difficulty", table_name="exercises", schema="operational")
    op.drop_index("ix_exercises_course_id", table_name="exercises", schema="operational")
    op.drop_table("exercises", schema="operational")

    postgresql.ENUM(
        "easy", "medium", "hard",
        name="exercise_difficulty",
        schema="operational",
    ).drop(op.get_bind(), checkfirst=True)
