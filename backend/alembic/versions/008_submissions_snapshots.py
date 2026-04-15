"""Create submissions, code_snapshots, activity_submissions tables.

Revision ID: 008
Revises: 007
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "008"
down_revision: str = "007"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE operational.submission_status AS ENUM ('pending', 'evaluated'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    # Activity submissions
    op.create_table(
        "activity_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.activities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_number", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", postgresql.ENUM("pending", "evaluated", name="submission_status", schema="operational", create_type=False), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="operational",
    )
    op.create_index("ix_activity_submissions_activity_id", "activity_submissions", ["activity_id"], schema="operational")
    op.create_index("ix_activity_submissions_student_id", "activity_submissions", ["student_id"], schema="operational")

    # Submissions (per exercise)
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.exercises.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activity_submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.activity_submissions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "evaluated", name="submission_status", schema="operational", create_type=False), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        schema="operational",
    )
    op.create_index("ix_submissions_student_id", "submissions", ["student_id"], schema="operational")
    op.create_index("ix_submissions_exercise_id", "submissions", ["exercise_id"], schema="operational")
    op.create_index("ix_submissions_activity_submission_id", "submissions", ["activity_submission_id"], schema="operational")

    # Code snapshots (immutable)
    op.create_table(
        "code_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="operational",
    )
    op.create_index("ix_code_snapshots_student_id", "code_snapshots", ["student_id"], schema="operational")
    op.create_index("ix_code_snapshots_exercise_id", "code_snapshots", ["exercise_id"], schema="operational")


def downgrade() -> None:
    op.drop_table("code_snapshots", schema="operational")
    op.drop_table("submissions", schema="operational")
    op.drop_table("activity_submissions", schema="operational")
    op.execute("DROP TYPE IF EXISTS operational.submission_status CASCADE")
