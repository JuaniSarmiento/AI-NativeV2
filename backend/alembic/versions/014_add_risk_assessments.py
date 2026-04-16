"""Add risk_assessments table for EPIC-15.

Revision ID: 014
Revises: 013
Create Date: 2026-04-16 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str = "013"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "risk_assessments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Student user ID — no FK, lives in operational schema",
        ),
        sa.Column(
            "commission_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Commission ID — no FK, lives in operational schema",
        ),
        sa.Column(
            "risk_level",
            sa.String(20),
            nullable=False,
            comment="Risk classification: low, medium, high, critical",
        ),
        sa.Column(
            "risk_factors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Factor name → {score, ...details} dict",
        ),
        sa.Column(
            "recommendation",
            sa.Text(),
            nullable=True,
            comment="Human-readable recommendation for the docente (Spanish)",
        ),
        sa.Column(
            "triggered_by",
            sa.String(20),
            nullable=False,
            comment="automatic, manual, or threshold",
        ),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "acknowledged_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Docente who acknowledged this alert — no FK",
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="analytics",
    )

    op.create_index(
        "ix_risk_assessments_student_id",
        "risk_assessments",
        ["student_id"],
        schema="analytics",
    )
    op.create_index(
        "ix_risk_assessments_commission_id",
        "risk_assessments",
        ["commission_id"],
        schema="analytics",
    )
    op.create_index(
        "ix_risk_assessments_risk_level",
        "risk_assessments",
        ["risk_level"],
        schema="analytics",
    )
    # Idempotency (one assessment per student/commission/day) is enforced at
    # the application layer in RiskAssessmentRepository.upsert_daily().
    # A functional unique index on (assessed_at::date) is not possible because
    # the date cast depends on timezone and is not IMMUTABLE in PostgreSQL.


def downgrade() -> None:
    op.drop_index(
        "ix_risk_assessments_risk_level",
        table_name="risk_assessments",
        schema="analytics",
    )
    op.drop_index(
        "ix_risk_assessments_commission_id",
        table_name="risk_assessments",
        schema="analytics",
    )
    op.drop_index(
        "ix_risk_assessments_student_id",
        table_name="risk_assessments",
        schema="analytics",
    )
    op.drop_table("risk_assessments", schema="analytics")
