from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.dev",
            "password": "securepass123",
            "full_name": "Test User",
            "role": "alumno",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ok"
    assert body["data"]["email"] == "newuser@test.dev"
    assert body["data"]["role"] == "alumno"
    assert "password" not in body["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "dupe@test.dev",
        "password": "securepass123",
        "full_name": "First User",
        "role": "alumno",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@test.dev",
            "password": "securepass123",
            "full_name": "Login User",
            "role": "docente",
        },
    )

    # Login
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.dev", "password": "securepass123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == "login@test.dev"
    assert body["data"]["user"]["role"] == "docente"

    # Check refresh cookie was set
    assert "refresh_token" in res.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "noone@test.dev", "password": "wrongpass"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient) -> None:
    # Register + login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@test.dev",
            "password": "securepass123",
            "full_name": "Refresh User",
            "role": "alumno",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@test.dev", "password": "securepass123"},
    )
    assert login_res.status_code == 200

    # Refresh — the cookie should be sent automatically by httpx
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    body = refresh_res.json()
    assert "access_token" in body["data"]


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    # Try to hit logout without auth
    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 401
