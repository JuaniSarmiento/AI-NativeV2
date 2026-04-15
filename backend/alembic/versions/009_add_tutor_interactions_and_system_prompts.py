"""Add tutor_interactions and tutor_system_prompts tables.

Revision ID: 009
Revises: 008
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "009"
down_revision: str = "008"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Create interaction_role enum in operational schema
    # -------------------------------------------------------------------------
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE operational.interaction_role AS ENUM ('user', 'assistant'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    # -------------------------------------------------------------------------
    # governance.tutor_system_prompts
    # -------------------------------------------------------------------------
    op.create_table(
        "tutor_system_prompts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sha256_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of content — auto-computed",
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("guardrails_config", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Admin user ID — no FK cross-schema",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="governance",
    )
    op.create_index(
        "uq_tutor_system_prompts_sha256",
        "tutor_system_prompts",
        ["sha256_hash"],
        unique=True,
        schema="governance",
    )

    # -------------------------------------------------------------------------
    # operational.tutor_interactions
    # -------------------------------------------------------------------------
    op.create_table(
        "tutor_interactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.exercises.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(
                "user",
                "assistant",
                name="interaction_role",
                schema="operational",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "n4_level",
            sa.SmallInteger(),
            nullable=True,
            comment="N4 classification (1-4), set by EPIC-11 classifier",
        ),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column(
            "prompt_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of the system prompt active at interaction time",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "n4_level IS NULL OR (n4_level >= 1 AND n4_level <= 4)",
            name="n4_level_range",
        ),
        schema="operational",
    )
    op.create_index(
        "ix_tutor_interactions_student_id",
        "tutor_interactions",
        ["student_id"],
        schema="operational",
    )
    op.create_index(
        "ix_tutor_interactions_exercise_id",
        "tutor_interactions",
        ["exercise_id"],
        schema="operational",
    )
    op.create_index(
        "ix_tutor_interactions_session_id",
        "tutor_interactions",
        ["session_id"],
        schema="operational",
    )


def downgrade() -> None:
    op.drop_table("tutor_interactions", schema="operational")
    op.drop_table("tutor_system_prompts", schema="governance")
    op.execute("DROP TYPE IF EXISTS operational.interaction_role CASCADE")
