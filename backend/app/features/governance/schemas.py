from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GovernanceEventResponse(BaseModel):
    """Read schema for a single governance event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    actor_id: str
    target_type: str | None
    target_id: str | None
    details: dict  # type: ignore[type-arg]
    created_at: datetime

    @classmethod
    def from_orm_uuid(cls, obj: object) -> "GovernanceEventResponse":
        """Convert UUID fields to str at the boundary."""
        import uuid as _uuid
        data = {
            "id": str(getattr(obj, "id")),
            "event_type": getattr(obj, "event_type"),
            "actor_id": str(getattr(obj, "actor_id")),
            "target_type": getattr(obj, "target_type"),
            "target_id": (
                str(getattr(obj, "target_id"))
                if getattr(obj, "target_id") is not None
                else None
            ),
            "details": getattr(obj, "details"),
            "created_at": getattr(obj, "created_at"),
        }
        return cls(**data)


class GovernanceEventsMeta(BaseModel):
    """Pagination metadata for governance events list."""

    page: int
    per_page: int
    total: int
    total_pages: int


class GovernanceEventsListResponse(BaseModel):
    """Response envelope for paginated governance events."""

    status: str = "ok"
    data: list[GovernanceEventResponse]
    meta: GovernanceEventsMeta | None = None


# ---------------------------------------------------------------------------
# EPIC-16 — Prompt History
# ---------------------------------------------------------------------------


class PromptHistoryResponse(BaseModel):
    """Read DTO for a TutorSystemPrompt in governance context."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    sha256_hash: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_orm_uuid(cls, obj: object) -> "PromptHistoryResponse":
        return cls(
            id=str(getattr(obj, "id")),
            name=getattr(obj, "name"),
            version=getattr(obj, "version"),
            sha256_hash=getattr(obj, "sha256_hash"),
            is_active=getattr(obj, "is_active"),
            created_at=getattr(obj, "created_at"),
        )


class PromptHistoryListResponse(BaseModel):
    status: str = "ok"
    data: list[PromptHistoryResponse] = Field(default_factory=list)
    meta: GovernanceEventsMeta | None = None
