"""Add gemini to llm_provider enum.

Revision ID: 016
Revises: 015
Create Date: 2026-04-17 00:00:00.000000 UTC
"""
from __future__ import annotations

from alembic import op

revision: str = "016"
down_revision: str = "015"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction block on older
    # PostgreSQL versions, but as of PG 12 it works inside transactions too.
    op.execute("ALTER TYPE operational.llm_provider ADD VALUE IF NOT EXISTS 'gemini'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from ENUMs.
    # This is a forward-only migration.
    pass
