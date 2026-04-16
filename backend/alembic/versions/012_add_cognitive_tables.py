"""Add cognitive_sessions and cognitive_events tables for CTR (EPIC-13).

Revision ID: 012
Revises: 011
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str = "011"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:

    # --- cognitive_sessions ---
    op.create_table(
        "cognitive_sessions",
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
            "exercise_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Exercise ID — no FK, lives in operational schema",
        ),
        sa.Column(
            "commission_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Commission ID — denormalized for scoped queries",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "genesis_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 anchor: SHA256('GENESIS:' + session_id + ':' + started_at_iso)",
        ),
        sa.Column(
            "session_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 of the last event when the session closes",
        ),
        sa.Column(
            "n4_final_score",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Evaluation scores N1-N4, set by the Evaluation Engine",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="open",
            comment="Session status: open, closed, invalidated",
        ),
        schema="cognitive",
    )

    op.create_index(
        "ix_cognitive_sessions_student_id",
        "cognitive_sessions",
        ["student_id"],
        schema="cognitive",
    )
    op.create_index(
        "ix_cognitive_sessions_exercise_id",
        "cognitive_sessions",
        ["exercise_id"],
        schema="cognitive",
    )
    op.create_index(
        "ix_cognitive_sessions_status",
        "cognitive_sessions",
        ["status"],
        schema="cognitive",
    )

    # --- cognitive_events ---
    op.create_table(
        "cognitive_events",
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
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Canonical CTR event type",
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            comment="1-based monotonically increasing sequence within the session",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Original event payload, optionally enriched by the classifier",
        ),
        sa.Column(
            "previous_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of the previous event (or genesis_hash for seq 1)",
        ),
        sa.Column(
            "event_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256(previous_hash + event_type + payload + created_at)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "session_id",
            "sequence_number",
            name="uq_cognitive_events_session_sequence",
        ),
        schema="cognitive",
    )

    op.create_index(
        "ix_cognitive_events_session_id",
        "cognitive_events",
        ["session_id"],
        schema="cognitive",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cognitive_events_session_id",
        table_name="cognitive_events",
        schema="cognitive",
    )
    op.drop_table("cognitive_events", schema="cognitive")

    op.drop_index(
        "ix_cognitive_sessions_status",
        table_name="cognitive_sessions",
        schema="cognitive",
    )
    op.drop_index(
        "ix_cognitive_sessions_exercise_id",
        table_name="cognitive_sessions",
        schema="cognitive",
    )
    op.drop_index(
        "ix_cognitive_sessions_student_id",
        table_name="cognitive_sessions",
        schema="cognitive",
    )
    op.drop_table("cognitive_sessions", schema="cognitive")

    op.execute("DROP TYPE IF EXISTS cognitive.session_status")
