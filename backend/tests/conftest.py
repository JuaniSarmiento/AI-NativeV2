from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Test DATABASE_URL — uses a separate _test database to avoid clobbering dev data.
# Override via TEST_DATABASE_URL environment variable.
# ---------------------------------------------------------------------------


def _derive_test_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    db_name = parts.path.lstrip("/") or "ainative"
    if not db_name.endswith("_test"):
        db_name = f"{db_name}_test"
    return urlunsplit((parts.scheme, parts.netloc, f"/{db_name}", parts.query, parts.fragment))


_DEFAULT_TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://ainative:ainative@localhost:5432/ainative",
    ),
)

if "TEST_DATABASE_URL" not in os.environ:
    _DEFAULT_TEST_DB = _derive_test_database_url(_DEFAULT_TEST_DB)


_SCHEMAS = ("operational", "cognitive", "governance", "analytics")


# ---------------------------------------------------------------------------
# Async engine & session factory scoped to the test session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Force AnyIO tests to run on asyncio only.

    This project uses asyncio (FastAPI + SQLAlchemy async). Running the same
    tests under Trio provides little value and complicates fixture scoping.
    """

    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _DEFAULT_TEST_DB


@pytest.fixture(scope="session")
def test_engine(test_database_url: str):  # type: ignore[no-untyped-def]
    """Create a fresh async engine for the test database.

    The schema is created by running Alembic migrations so tests validate the
    production migration path (not Base.metadata.create_all()).
    """
    engine = create_async_engine(
        test_database_url,
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool,
    )

    async def _reset_db() -> None:
        async with engine.begin() as conn:
            for schema in _SCHEMAS:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"DROP SCHEMA IF EXISTS {schema} CASCADE"
                    )
                )
            # Drop alembic_version so migrations re-run from scratch
            await conn.execute(
                __import__("sqlalchemy").text(
                    "DROP TABLE IF EXISTS public.alembic_version"
                )
            )
            # Drop orphaned ENUMs that may linger in public schema
            for enum_name in ("user_role", "exercise_difficulty", "activity_status", "llm_provider"):
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"DROP TYPE IF EXISTS {enum_name} CASCADE"
                    )
                )

    # Ensure a clean slate in case a previous test run crashed mid-setup.
    asyncio.run(_reset_db())

    # Apply Alembic migrations to the test database.
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))

    previous_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if previous_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_db_url

    yield engine

    # Teardown — drop all schemas after the test session
    async def _teardown() -> None:
        async with engine.begin() as conn:
            for schema in _SCHEMAS:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"DROP SCHEMA IF EXISTS {schema} CASCADE"
                    )
                )
        await engine.dispose()

    asyncio.run(_teardown())


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[no-untyped-def]
    """Provide a per-test AsyncSession that is rolled back after each test.

    Uses a connection-level transaction + savepoint pattern so that
    session.commit() inside application code only commits the savepoint,
    not the outer transaction. The outer transaction is always rolled back.
    """
    conn = await test_engine.connect()
    trans = await conn.begin()

    session = AsyncSession(bind=conn, expire_on_commit=False)

    # Use nested transactions (savepoints) so session.commit()
    # inside endpoint code doesn't close the outer transaction.
    nested = await conn.begin_nested()

    @sa.event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(session_sync, transaction):  # type: ignore[no-untyped-def]
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = conn.sync_connection.begin_nested()  # type: ignore[union-attr]

    yield session

    await session.close()
    await trans.rollback()
    await conn.close()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient pointed at the FastAPI app.

    Overrides the ``get_async_session`` dependency so every request in the
    test uses the same savepoint-backed session — data is rolled back after each test.
    """
    import redis.asyncio as aioredis
    from app.main import create_app
    from app.shared.db.session import get_async_session
    from app.features.auth.dependencies import get_redis

    app = create_app()

    # Override DB session
    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override Redis — fresh connection per test, properly closed
    test_redis = aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )

    async def _override_redis() -> aioredis.Redis:
        return test_redis

    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_redis] = _override_redis

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac

    await test_redis.aclose()
