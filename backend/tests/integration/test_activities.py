from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _get_docente_token(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "doc-act@test.dev", "password": "securepass123", "full_name": "Doc Activity", "role": "docente"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "doc-act@test.dev", "password": "securepass123"},
    )
    return res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_save_and_get_llm_config(client: AsyncClient) -> None:
    token = await _get_docente_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Save config
    save_res = await client.put(
        "/api/v1/settings/llm",
        json={"provider": "openai", "api_key": "sk-test-key-12345", "model_name": "gpt-4o-mini"},
        headers=headers,
    )
    assert save_res.status_code == 200
    body = save_res.json()
    assert body["data"]["provider"] == "openai"
    assert body["data"]["model_name"] == "gpt-4o-mini"
    assert "api_key" not in body["data"]  # Key never returned

    # Get config
    get_res = await client.get("/api/v1/settings/llm", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["has_key"] is True


@pytest.mark.asyncio
async def test_list_activities_empty(client: AsyncClient) -> None:
    token = await _get_docente_token(client)
    res = await client.get(
        "/api/v1/activities",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["data"] == []
