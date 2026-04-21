"""Add n4_level column to cognitive_events and score_breakdown to cognitive_metrics.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cognitive_events",
        sa.Column("n4_level", sa.Integer(), nullable=True, comment="N4 observation level 1-4, null for lifecycle events"),
        schema="cognitive",
    )
    op.create_index(
        "ix_cognitive_events_n4_level",
        "cognitive_events",
        ["n4_level"],
        schema="cognitive",
    )

    op.add_column(
        "cognitive_metrics",
        sa.Column("score_breakdown", JSONB(), nullable=True, comment="Per-N condition details"),
        schema="cognitive",
    )
    op.add_column(
        "cognitive_metrics",
        sa.Column("engine_version", sa.String(10), nullable=True, comment="Version of MetricsEngine that produced these scores"),
        schema="cognitive",
    )


def downgrade() -> None:
    op.drop_column("cognitive_metrics", "engine_version", schema="cognitive")
    op.drop_column("cognitive_metrics", "score_breakdown", schema="cognitive")
    op.drop_index("ix_cognitive_events_n4_level", table_name="cognitive_events", schema="cognitive")
    op.drop_column("cognitive_events", "n4_level", schema="cognitive")
