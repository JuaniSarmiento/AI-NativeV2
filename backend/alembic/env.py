from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Logging setup from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import Base and ALL models so metadata is populated for autogenerate.
# New models MUST be imported here, otherwise Alembic cannot see them.
# ---------------------------------------------------------------------------
from app.shared.db.base import Base  # noqa: E402

# Operational schema models
from app.shared.models.commission import Commission  # noqa: E402, F401
from app.shared.models.course import Course  # noqa: E402, F401
from app.shared.models.event_outbox import EventOutbox  # noqa: E402, F401
from app.shared.models.user import User  # noqa: E402, F401
from app.shared.models.user import User  # noqa: E402, F401
from app.shared.models.course import Course  # noqa: E402, F401
from app.shared.models.commission import Commission  # noqa: E402, F401

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Read DATABASE_URL from environment — never from alembic.ini
# ---------------------------------------------------------------------------


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Export it before running Alembic commands."
        )
    return url


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout instead of executing against a live DB.
    Useful for generating SQL scripts for DBA review.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        # Render item counts for batch operations (useful for large tables)
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async DB engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no connection pooling during migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point — selects offline or online mode based on Alembic context."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
