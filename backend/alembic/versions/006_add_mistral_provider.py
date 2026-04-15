"""Add mistral to llm_provider enum.

Revision ID: 006
Revises: 005
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

from alembic import op

revision: str = "006"
down_revision: str = "005"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE operational.llm_provider ADD VALUE IF NOT EXISTS 'mistral'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from ENUMs.
    # This is a forward-only migration.
    pass
