from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_full_returns_ok(client: AsyncClient) -> None:
    res = await client.get("/api/v1/health/full")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["data"]["database"] == "ok"
