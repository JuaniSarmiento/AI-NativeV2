"""Create users, courses, and commissions tables.

Revision ID: 002
Revises: 001
Create Date: 2026-04-13 00:00:00.000000 UTC
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ---------------------------------------------------------------------------
revision: str = "002"
down_revision: str = "001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create user_role ENUM type in operational schema
    # ------------------------------------------------------------------
    user_role = postgresql.ENUM(
        "alumno", "docente", "admin",
        name="user_role",
        schema="operational",
    )
    # NOTE: the ENUM is created implicitly when creating the `users` table
    # (via SQLAlchemy's DDL hooks). Avoid creating it twice.

    # ------------------------------------------------------------------
    # 2. Create users table
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            user_role,
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="operational",
    )
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        schema="operational",
    )

    # ------------------------------------------------------------------
    # 3. Create courses table
    # ------------------------------------------------------------------
    op.create_table(
        "courses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "topic_taxonomy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Hierarchical topic tree for the course",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="operational",
    )

    # ------------------------------------------------------------------
    # 4. Create commissions table
    # ------------------------------------------------------------------
    op.create_table(
        "commissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.courses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "teacher_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("semester", sa.SmallInteger(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="operational",
    )
    op.create_index(
        "ix_commissions_course_id",
        "commissions",
        ["course_id"],
        schema="operational",
    )
    op.create_index(
        "ix_commissions_teacher_id",
        "commissions",
        ["teacher_id"],
        schema="operational",
    )


def downgrade() -> None:
    op.drop_index("ix_commissions_teacher_id", table_name="commissions", schema="operational")
    op.drop_index("ix_commissions_course_id", table_name="commissions", schema="operational")
    op.drop_table("commissions", schema="operational")

    op.drop_table("courses", schema="operational")

    op.drop_index("ix_users_email", table_name="users", schema="operational")
    op.drop_table("users", schema="operational")

    # Drop the ENUM type
    postgresql.ENUM(
        "alumno", "docente", "admin",
        name="user_role",
        schema="operational",
    ).drop(op.get_bind(), checkfirst=True)
