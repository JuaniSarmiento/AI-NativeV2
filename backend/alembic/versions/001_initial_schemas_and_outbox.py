"""Create initial schemas and event_outbox table.

Revision ID: 001
Revises: (none)
Create Date: 2026-04-13 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ---------------------------------------------------------------------------
revision: str = "001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None
# ---------------------------------------------------------------------------

_SCHEMAS = ("operational", "cognitive", "governance", "analytics")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create PostgreSQL schemas — each phase owns its schema.
    # ------------------------------------------------------------------
    for schema in _SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ------------------------------------------------------------------
    # 2. Create event_outbox in the operational schema.
    #    The outbox is the backbone of the inter-phase event bus.
    # ------------------------------------------------------------------
    op.create_table(
        "event_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Dot-namespaced event type, e.g. 'submission.created'",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Arbitrary JSON payload",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="pending | processed | failed",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "retry_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="operational",
    )

    # Indexes — status + created_at for the outbox worker poll query
    op.create_index(
        "ix_event_outbox_status",
        "event_outbox",
        ["status"],
        schema="operational",
    )
    op.create_index(
        "ix_event_outbox_event_type",
        "event_outbox",
        ["event_type"],
        schema="operational",
    )
    op.create_index(
        "ix_event_outbox_created_at_status",
        "event_outbox",
        ["created_at", "status"],
        schema="operational",
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(
        "ix_event_outbox_created_at_status",
        table_name="event_outbox",
        schema="operational",
    )
    op.drop_index(
        "ix_event_outbox_event_type",
        table_name="event_outbox",
        schema="operational",
    )
    op.drop_index(
        "ix_event_outbox_status",
        table_name="event_outbox",
        schema="operational",
    )

    op.drop_table("event_outbox", schema="operational")

    # Drop schemas in reverse dependency order
    for schema in reversed(_SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
