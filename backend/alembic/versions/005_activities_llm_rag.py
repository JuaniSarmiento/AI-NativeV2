"""Create activities, llm_configs, document_chunks tables. Add activity_id to exercises.

Revision ID: 005
Revises: 004
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ENUMs — idempotent
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE operational.activity_status AS ENUM ('draft', 'published'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE operational.llm_provider AS ENUM ('openai', 'anthropic'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    # Activities table
    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt_used", sa.Text(), nullable=True),
        sa.Column("status", postgresql.ENUM("draft", "published", name="activity_status", schema="operational", create_type=False), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="operational",
    )
    op.create_index("ix_activities_course_id", "activities", ["course_id"], schema="operational")
    op.create_index("ix_activities_created_by", "activities", ["created_by"], schema="operational")

    # LLM configs table
    op.create_table(
        "llm_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", postgresql.ENUM("openai", "anthropic", name="llm_provider", schema="operational", create_type=False), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False, server_default=sa.text("'gpt-4o-mini'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", name="uq_llm_configs_user_id"),
        schema="operational",
    )
    op.create_index("ix_llm_configs_user_id", "llm_configs", ["user_id"], schema="operational")

    # Document chunks table (RAG) — embedding column added via raw SQL for pgvector
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="operational",
    )
    op.execute("ALTER TABLE operational.document_chunks ADD COLUMN embedding vector(1536)")
    op.create_index("ix_document_chunks_source_file", "document_chunks", ["source_file"], schema="operational")
    op.create_index("ix_document_chunks_topic", "document_chunks", ["topic"], schema="operational")

    # Add activity_id to exercises
    op.add_column(
        "exercises",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational.activities.id", ondelete="SET NULL"), nullable=True),
        schema="operational",
    )
    op.create_index("ix_exercises_activity_id", "exercises", ["activity_id"], schema="operational")


def downgrade() -> None:
    op.drop_index("ix_exercises_activity_id", table_name="exercises", schema="operational")
    op.drop_column("exercises", "activity_id", schema="operational")

    op.drop_index("ix_document_chunks_topic", table_name="document_chunks", schema="operational")
    op.drop_index("ix_document_chunks_source_file", table_name="document_chunks", schema="operational")
    op.drop_table("document_chunks", schema="operational")

    op.drop_index("ix_llm_configs_user_id", table_name="llm_configs", schema="operational")
    op.drop_table("llm_configs", schema="operational")

    op.drop_index("ix_activities_created_by", table_name="activities", schema="operational")
    op.drop_index("ix_activities_course_id", table_name="activities", schema="operational")
    op.drop_table("activities", schema="operational")

    op.execute("DROP TYPE IF EXISTS operational.llm_provider CASCADE")
    op.execute("DROP TYPE IF EXISTS operational.activity_status CASCADE")
