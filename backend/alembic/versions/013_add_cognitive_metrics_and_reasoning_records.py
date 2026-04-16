"""Add cognitive_metrics and reasoning_records tables for EPIC-14.

Revision ID: 013
Revises: 012
Create Date: 2026-04-15 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: str = "012"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:

    # --- cognitive_metrics ---
    op.create_table(
        "cognitive_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "cognitive.cognitive_sessions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        # N1-N4 scores
        sa.Column(
            "n1_comprehension_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="N1 comprehension score 0-100",
        ),
        sa.Column(
            "n2_strategy_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="N2 strategy score 0-100",
        ),
        sa.Column(
            "n3_validation_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="N3 validation score 0-100",
        ),
        sa.Column(
            "n4_ai_interaction_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="N4 AI interaction quality score 0-100",
        ),
        # Interaction ratios
        sa.Column(
            "total_interactions",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total number of CTR events in the session",
        ),
        sa.Column(
            "help_seeking_ratio",
            sa.Numeric(4, 3),
            nullable=True,
            comment="Fraction of events that are tutor interactions (0-1)",
        ),
        sa.Column(
            "autonomy_index",
            sa.Numeric(4, 3),
            nullable=True,
            comment="1 - help_seeking_ratio",
        ),
        # Qe sub-scores
        sa.Column(
            "qe_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Composite epistemic quality score 0-100",
        ),
        sa.Column(
            "qe_quality_prompt",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Quality of prompts sent to tutor 0-100",
        ),
        sa.Column(
            "qe_critical_evaluation",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Critical evaluation of tutor responses 0-100",
        ),
        sa.Column(
            "qe_integration",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Successful integration of tutor guidance 0-100",
        ),
        sa.Column(
            "qe_verification",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Verification of code changes 0-100",
        ),
        # Dependency and reflection
        sa.Column(
            "dependency_score",
            sa.Numeric(4, 3),
            nullable=True,
            comment="Fraction of AI interactions classified as dependent (0-1)",
        ),
        sa.Column(
            "reflection_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Post-exercise reflection quality 0-100",
        ),
        sa.Column(
            "success_efficiency",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Successful runs / total runs * 100",
        ),
        # Risk
        sa.Column(
            "risk_level",
            sa.String(20),
            nullable=True,
            comment="Risk classification: critical, high, medium, low",
        ),
        # Audit
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When MetricsEngine produced this record",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("session_id", name="uq_cognitive_metrics_session_id"),
        schema="cognitive",
    )

    op.create_index(
        "ix_cognitive_metrics_session_id",
        "cognitive_metrics",
        ["session_id"],
        unique=True,
        schema="cognitive",
    )
    op.create_index(
        "ix_cognitive_metrics_risk_level",
        "cognitive_metrics",
        ["risk_level"],
        schema="cognitive",
    )

    # --- reasoning_records ---
    op.create_table(
        "reasoning_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "cognitive.cognitive_sessions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "record_type",
            sa.String(50),
            nullable=False,
            comment="Type of reasoning record, e.g. 'metrics_computation'",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Full computation summary produced by MetricsEngine",
        ),
        sa.Column(
            "previous_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of the previous reasoning record",
        ),
        sa.Column(
            "event_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256(previous_hash + record_type + json(details) + created_at_iso)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="cognitive",
    )

    op.create_index(
        "ix_reasoning_records_session_id",
        "reasoning_records",
        ["session_id"],
        schema="cognitive",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reasoning_records_session_id",
        table_name="reasoning_records",
        schema="cognitive",
    )
    op.drop_table("reasoning_records", schema="cognitive")

    op.drop_index(
        "ix_cognitive_metrics_risk_level",
        table_name="cognitive_metrics",
        schema="cognitive",
    )
    op.drop_index(
        "ix_cognitive_metrics_session_id",
        table_name="cognitive_metrics",
        schema="cognitive",
    )
    op.drop_table("cognitive_metrics", schema="cognitive")
