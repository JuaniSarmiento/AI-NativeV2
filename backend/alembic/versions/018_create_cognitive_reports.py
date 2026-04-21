"""Create cognitive_reports table.

Revision ID: 018
Revises: 017
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cognitive_reports",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("activity_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("commission_id", UUID(as_uuid=True), nullable=False),
        sa.Column("generated_by", UUID(as_uuid=True), nullable=False),
        sa.Column("structured_analysis", JSONB, nullable=False),
        sa.Column("data_hash", sa.String(64), nullable=False),
        sa.Column("narrative_md", sa.Text, nullable=False),
        sa.Column("llm_provider", sa.String(20), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "activity_id", "data_hash", name="uq_cognitive_reports_student_activity_hash"),
        schema="cognitive",
    )
    op.create_index(
        "ix_cognitive_reports_student_activity",
        "cognitive_reports",
        ["student_id", "activity_id"],
        schema="cognitive",
    )


def downgrade() -> None:
    op.drop_index("ix_cognitive_reports_student_activity", table_name="cognitive_reports", schema="cognitive")
    op.drop_table("cognitive_reports", schema="cognitive")
