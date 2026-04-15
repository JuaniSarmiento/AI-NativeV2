"""Integration tests for the tutor REST fallback endpoint."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


async def test_messages_endpoint_requires_auth(client: AsyncClient):
    exercise_id = uuid.uuid4()
    response = await client.get(f"/api/v1/tutor/sessions/{exercise_id}/messages")
    assert response.status_code == 401


async def test_messages_endpoint_rejects_docente(client: AsyncClient):
    """Docentes should not access the student tutor messages endpoint."""
    token = create_access_token(uuid.uuid4(), "docente")
    exercise_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/tutor/sessions/{exercise_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
