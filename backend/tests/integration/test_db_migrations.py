from __future__ import annotations

import sqlalchemy as sa
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_operational_schema_tables_exist(db_session: AsyncSession) -> None:
    """Smoke test that EPIC-02 migrations create the operational base tables."""

    async def _has_table(schema: str, table: str) -> bool:
        stmt = sa.text(
            """
            select 1
            from information_schema.tables
            where table_schema = :schema and table_name = :table
            limit 1
            """
        )
        result = await db_session.execute(stmt, {"schema": schema, "table": table})
        return result.scalar_one_or_none() is not None

    assert await _has_table("operational", "event_outbox")
    assert await _has_table("operational", "users")
    assert await _has_table("operational", "courses")
    assert await _has_table("operational", "commissions")
