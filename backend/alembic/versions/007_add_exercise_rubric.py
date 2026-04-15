"""Add rubric field to exercises.

Revision ID: 007
Revises: 006
Create Date: 2026-04-14 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str = "006"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("rubric", sa.Text(), nullable=True, comment="Evaluation rubric for AI grading"),
        schema="operational",
    )


def downgrade() -> None:
    op.drop_column("exercises", "rubric", schema="operational")
