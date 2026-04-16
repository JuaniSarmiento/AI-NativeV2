"""Add governance_events table.

Revision ID: 010
Revises: 009
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "010"
down_revision: str = "009"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Dot-namespaced event type, e.g. 'prompt.created', 'guardrail.triggered'",
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="ID of the user or system actor (no FK — cross-schema)",
        ),
        sa.Column(
            "target_type",
            sa.String(100),
            nullable=True,
            comment="Type of the target entity, e.g. 'prompt', 'interaction'",
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="ID of the target entity (no FK — cross-schema)",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Arbitrary JSON payload with event-specific details",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="governance",
    )

    op.create_index(
        "ix_governance_events_event_type",
        "governance_events",
        ["event_type"],
        schema="governance",
    )
    op.create_index(
        "ix_governance_events_actor_id",
        "governance_events",
        ["actor_id"],
        schema="governance",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_governance_events_actor_id",
        table_name="governance_events",
        schema="governance",
    )
    op.drop_index(
        "ix_governance_events_event_type",
        table_name="governance_events",
        schema="governance",
    )
    op.drop_table("governance_events", schema="governance")
