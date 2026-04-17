"""Add coherence score columns to cognitive_metrics for EPIC-20 Fase C.

Revision ID: 015
Revises: 014
Create Date: 2026-04-17 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: str = "014"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "cognitive_metrics",
        sa.Column(
            "temporal_coherence_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Temporal coherence of N-level event sequences 0-100",
        ),
        schema="cognitive",
    )
    op.add_column(
        "cognitive_metrics",
        sa.Column(
            "code_discourse_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Coherence between chat discourse and code changes 0-100",
        ),
        schema="cognitive",
    )
    op.add_column(
        "cognitive_metrics",
        sa.Column(
            "inter_iteration_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Consistency across code iterations 0-100",
        ),
        schema="cognitive",
    )
    op.add_column(
        "cognitive_metrics",
        sa.Column(
            "coherence_anomalies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Detected anomaly patterns: solution_without_comprehension, pure_delegation, etc.",
        ),
        schema="cognitive",
    )
    op.add_column(
        "cognitive_metrics",
        sa.Column(
            "prompt_type_distribution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Distribution of prompt types: {exploratory: N, verifier: N, generative: N}",
        ),
        schema="cognitive",
    )


def downgrade() -> None:
    op.drop_column("cognitive_metrics", "prompt_type_distribution", schema="cognitive")
    op.drop_column("cognitive_metrics", "coherence_anomalies", schema="cognitive")
    op.drop_column("cognitive_metrics", "inter_iteration_score", schema="cognitive")
    op.drop_column("cognitive_metrics", "code_discourse_score", schema="cognitive")
    op.drop_column("cognitive_metrics", "temporal_coherence_score", schema="cognitive")
