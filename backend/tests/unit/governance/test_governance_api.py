"""Unit tests for the governance API endpoint.

These tests use FastAPI's TestClient with dependency overrides so they run
without a real database or Redis connection.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.features.governance.models import GovernanceEvent
from app.features.governance.router import get_governance_service, router
from app.features.governance.service import GovernanceService
from app.shared.models.user import User, UserRole

# Type alias for test mocks
_UserLike = MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_governance_event(event_type: str = "prompt.created") -> MagicMock:
    """Return a MagicMock that quacks like a GovernanceEvent ORM instance."""
    event = MagicMock(spec=GovernanceEvent)
    event.id = uuid.uuid4()
    event.event_type = event_type
    event.actor_id = uuid.uuid4()
    event.target_type = "prompt"
    event.target_id = uuid.uuid4()
    event.details = {"version": "1.0.0"}
    event.created_at = datetime.now(tz=timezone.utc)
    return event


def _make_user(role: str = "admin") -> MagicMock:
    """Return a MagicMock that quacks like a User ORM instance."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role}@test.dev"
    user.full_name = f"Test {role.capitalize()}"
    user.role = UserRole(role)
    user.is_active = True
    return user


def _build_test_app(
    governance_service: GovernanceService,
    current_user: User,
) -> FastAPI:
    """Build a minimal FastAPI app with the governance router and overrides."""
    from app.features.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(router)

    # Override DB session → not needed (service is fully mocked)
    # Override auth → return our test user
    async def _fake_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = _fake_current_user

    # Override the service factory
    def _fake_service() -> GovernanceService:
        return governance_service

    app.dependency_overrides[get_governance_service] = _fake_service

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_service(
    items: list[GovernanceEvent],
    total: int,
) -> GovernanceService:
    service = MagicMock(spec=GovernanceService)
    service.list_events = AsyncMock(return_value=(items, total))
    return service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_can_list_events() -> None:
    """GET /api/v1/governance/events returns 200 with events for admin."""
    events = [_make_governance_event("prompt.created")]
    service = _make_service(events, 1)
    admin = _make_user("admin")
    app = _build_test_app(service, admin)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/governance/events")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["data"]) == 1
    assert body["data"][0]["event_type"] == "prompt.created"
    assert body["meta"]["total"] == 1
    assert body["meta"]["page"] == 1


@pytest.mark.anyio
async def test_non_admin_denied() -> None:
    """GET /api/v1/governance/events returns 403 for non-admin roles."""
    from app.core.exceptions import AuthorizationError
    from app.features.auth.dependencies import get_current_user

    # Build app with a docente user
    docente = _make_user("docente")
    service = _make_service([], 0)

    app = FastAPI()
    app.include_router(router)

    # Register the domain error handler so 403 is returned correctly
    from fastapi import Request, status
    from fastapi.responses import JSONResponse
    from app.core.exceptions import DomainError, AuthorizationError

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": "error", "errors": [{"code": exc.code, "message": exc.message}]},
        )

    async def _fake_current_user() -> User:
        return docente

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_governance_service] = lambda: service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/governance/events")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_filter_by_event_type() -> None:
    """GET /api/v1/governance/events?event_type=guardrail.triggered filters correctly."""
    events = [_make_governance_event("guardrail.triggered")]
    service = _make_service(events, 1)
    admin = _make_user("admin")
    app = _build_test_app(service, admin)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/governance/events",
            params={"event_type": "guardrail.triggered"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["event_type"] == "guardrail.triggered"

    # Verify the service was called with the correct filter
    service.list_events.assert_awaited_once_with(
        page=1,
        per_page=20,
        event_type="guardrail.triggered",
    )


@pytest.mark.anyio
async def test_empty_list_returns_meta() -> None:
    """GET /api/v1/governance/events with no events returns empty data with meta."""
    service = _make_service([], 0)
    admin = _make_user("admin")
    app = _build_test_app(service, admin)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/governance/events")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"] == []
    assert body["meta"]["total"] == 0
    assert body["meta"]["total_pages"] == 1  # ceil(0/20) = 0, but we clamp to 1


@pytest.mark.anyio
async def test_pagination_params_passed_to_service() -> None:
    """Query params page and per_page are forwarded to the service."""
    service = _make_service([], 0)
    admin = _make_user("admin")
    app = _build_test_app(service, admin)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get(
            "/api/v1/governance/events",
            params={"page": 3, "per_page": 10},
        )

    service.list_events.assert_awaited_once_with(
        page=3,
        per_page=10,
        event_type=None,
    )
