from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.core.event_bus import EventBus
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.outbox_worker import OutboxWorker
from app.shared.db.session import get_engine, get_session_factory

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons shared across the lifespan
# ---------------------------------------------------------------------------
_event_bus: EventBus | None = None
_outbox_task: asyncio.Task[None] | None = None


def get_event_bus() -> EventBus:
    if _event_bus is None:
        raise RuntimeError("EventBus not initialised — app startup not complete.")
    return _event_bus


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _event_bus, _outbox_task  # noqa: PLW0603

    settings = get_settings()
    logger.info(
        "Starting AI-Native backend",
        extra={"env": settings.app_env, "debug": settings.debug},
    )

    # --- DB: warm up the connection pool ---
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    logger.info("Database connection pool ready")

    # --- Redis: connect and initialise streams ---
    _event_bus = EventBus(redis_url=settings.redis_url)
    await _event_bus.connect()
    await _event_bus.initialize_streams()

    # --- Outbox worker ---
    worker = OutboxWorker(
        session_factory=get_session_factory(),
        event_bus=_event_bus,
    )
    _outbox_task = asyncio.create_task(worker.run(interval=5.0))
    logger.info("OutboxWorker task started")

    yield

    # --- Shutdown ---
    logger.info("Shutting down AI-Native backend")

    if _outbox_task is not None:
        _outbox_task.cancel()
        try:
            await _outbox_task
        except asyncio.CancelledError:
            pass

    if _event_bus is not None:
        await _event_bus.close()

    await engine.dispose()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI-Native — Plataforma Pedagógica UTN FRM",
        description=(
            "Backend para el sistema de tutoría socrática con IA, "
            "registro cognitivo (CTR) y evaluación N4."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # --- Rate Limiting ---
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],
        storage_uri=settings.redis_url,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    _register_exception_handlers(app)

    # --- Routers ---
    _register_routers(app)

    return app


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

_DOMAIN_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    ConflictError: status.HTTP_409_CONFLICT,
}


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:
        http_status = _DOMAIN_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        error_detail: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if isinstance(exc, ValidationError) and exc.field:
            error_detail["field"] = exc.field
        logger.warning(
            "Domain error",
            extra={
                "error_code": exc.code,
                "http_status": http_status,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=http_status,
            content={
                "status": "error",
                "data": {},
                "meta": {},
                "errors": [error_detail],
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            extra={"path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "data": {},
                "meta": {},
                "errors": [
                    {"code": "INTERNAL_ERROR", "message": "An internal server error occurred."}
                ],
            },
        )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------


def _register_routers(app: FastAPI) -> None:
    # Health check (no auth required)
    from fastapi import APIRouter

    health_router = APIRouter(tags=["system"])

    @health_router.get("/health", summary="Health check")
    async def health_check() -> dict:
        return {"status": "ok"}

    @health_router.get("/api/v1/health/full", summary="Full health check")
    async def health_full() -> JSONResponse:
        checks: dict[str, str] = {}
        all_ok = True

        # DB check
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
            all_ok = False

        # Redis check
        try:
            import redis.asyncio as aioredis

            settings = get_settings()
            r = aioredis.from_url(settings.redis_url)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            all_ok = False

        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "error", "data": checks},
        )

    app.include_router(health_router)

    # Feature routers
    from app.features.auth.router import router as auth_router
    from app.features.courses.router import router as courses_router
    from app.features.exercises.router import router as exercises_router
    from app.features.activities.router import router as activities_router
    from app.features.sandbox.router import router as sandbox_router
    from app.features.submissions.router import router as submissions_router
    from app.features.tutor.router import router as tutor_router

    app.include_router(auth_router)
    app.include_router(courses_router)
    app.include_router(exercises_router)
    app.include_router(activities_router)
    app.include_router(sandbox_router)
    app.include_router(submissions_router)
    app.include_router(tutor_router)
