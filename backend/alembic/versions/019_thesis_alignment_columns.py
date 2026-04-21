"""Add chain_version to cognitive_sessions and prompt versioning fields to tutor_system_prompts.

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # B3: chain_version on cognitive_sessions (default 1 for existing, 2 for new via app)
    op.add_column(
        "cognitive_sessions",
        sa.Column(
            "chain_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Hash chain formula version: 1=original, 2=includes prompt_hash",
        ),
        schema="cognitive",
    )

    # B7: semantic versioning fields on tutor_system_prompts (governance schema)
    op.add_column(
        "tutor_system_prompts",
        sa.Column(
            "change_type",
            sa.String(10),
            nullable=True,
            comment="Semantic version change type: major, minor, or patch",
        ),
        schema="governance",
    )
    op.add_column(
        "tutor_system_prompts",
        sa.Column(
            "change_justification",
            sa.String(),
            nullable=True,
            comment="Justification for the prompt version change",
        ),
        schema="governance",
    )


def downgrade() -> None:
    op.drop_column("tutor_system_prompts", "change_justification", schema="governance")
    op.drop_column("tutor_system_prompts", "change_type", schema="governance")
    op.drop_column("cognitive_sessions", "chain_version", schema="cognitive")
