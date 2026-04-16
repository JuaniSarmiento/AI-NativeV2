from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.evaluation.schemas import CognitiveMetricsResponse


class CognitiveEventResponse(BaseModel):
    """Read schema for a single CTR event.

    UUIDs are serialised as strings at the API boundary.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    sequence_number: int
    payload: dict  # type: ignore[type-arg]
    previous_hash: str
    event_hash: str
    created_at: datetime

    @classmethod
    def from_orm(cls, obj: object) -> "CognitiveEventResponse":
        return cls(
            id=str(getattr(obj, "id")),
            event_type=getattr(obj, "event_type"),
            sequence_number=getattr(obj, "sequence_number"),
            payload=getattr(obj, "payload"),
            previous_hash=getattr(obj, "previous_hash"),
            event_hash=getattr(obj, "event_hash"),
            created_at=getattr(obj, "created_at"),
        )


class CognitiveSessionResponse(BaseModel):
    """Read schema for a full cognitive session including its events."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    exercise_id: str
    commission_id: str
    started_at: datetime
    closed_at: datetime | None
    genesis_hash: str | None
    session_hash: str | None
    status: str
    events: list[CognitiveEventResponse] = []

    @classmethod
    def from_orm(cls, obj: object) -> "CognitiveSessionResponse":
        raw_events = getattr(obj, "events", []) or []
        return cls(
            id=str(getattr(obj, "id")),
            student_id=str(getattr(obj, "student_id")),
            exercise_id=str(getattr(obj, "exercise_id")),
            commission_id=str(getattr(obj, "commission_id")),
            started_at=getattr(obj, "started_at"),
            closed_at=getattr(obj, "closed_at", None),
            genesis_hash=getattr(obj, "genesis_hash", None),
            session_hash=getattr(obj, "session_hash", None),
            status=getattr(obj, "status").value
            if hasattr(getattr(obj, "status"), "value")
            else str(getattr(obj, "status")),
            events=[CognitiveEventResponse.from_orm(e) for e in raw_events],
        )


class VerifyResponse(BaseModel):
    """Response schema for the chain verification endpoint."""

    valid: bool
    events_checked: int | None = None
    failed_at_sequence: int | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None


class CognitiveSessionDataWrapper(BaseModel):
    """Data wrapper for single session responses."""

    session: CognitiveSessionResponse


class CognitiveSessionStandardResponse(BaseModel):
    """Standard envelope for a single cognitive session."""

    status: str = "ok"
    data: CognitiveSessionDataWrapper
    meta: dict | None = None  # type: ignore[type-arg]
    errors: list = []  # type: ignore[type-arg]


class VerifyStandardResponse(BaseModel):
    """Standard envelope for chain verification results."""

    status: str = "ok"
    data: VerifyResponse
    meta: dict | None = None  # type: ignore[type-arg]
    errors: list = []  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# EPIC-16 — Trace, Timeline, Code Evolution, Sessions List
# ---------------------------------------------------------------------------


class SessionListItem(BaseModel):
    """Lightweight session DTO for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    exercise_id: str
    commission_id: str
    started_at: datetime
    closed_at: datetime | None = None
    status: str

    @classmethod
    def from_orm(cls, obj: object) -> "SessionListItem":
        status_val = getattr(obj, "status")
        return cls(
            id=str(getattr(obj, "id")),
            student_id=str(getattr(obj, "student_id")),
            exercise_id=str(getattr(obj, "exercise_id")),
            commission_id=str(getattr(obj, "commission_id")),
            started_at=getattr(obj, "started_at"),
            closed_at=getattr(obj, "closed_at", None),
            status=status_val.value if hasattr(status_val, "value") else str(status_val),
        )


class SessionListMeta(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 1


class SessionListResponse(BaseModel):
    status: str = "ok"
    data: list[SessionListItem] = []
    meta: SessionListMeta = SessionListMeta()
    errors: list = []  # type: ignore[type-arg]


class TraceChatMessageResponse(BaseModel):
    """Chat message DTO for trace views (docente/admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    n4_level: int | None = None
    tokens_used: int | None = None
    model_version: str | None = None
    prompt_hash: str
    created_at: datetime

    @classmethod
    def from_orm(cls, obj: object) -> "TraceChatMessageResponse":
        role_val = getattr(obj, "role")
        return cls(
            id=str(getattr(obj, "id")),
            session_id=str(getattr(obj, "session_id")),
            role=role_val.value if hasattr(role_val, "value") else str(role_val),
            content=getattr(obj, "content"),
            n4_level=getattr(obj, "n4_level", None),
            tokens_used=getattr(obj, "tokens_used", None),
            model_version=getattr(obj, "model_version", None),
            prompt_hash=getattr(obj, "prompt_hash"),
            created_at=getattr(obj, "created_at"),
        )


class TraceResponse(BaseModel):
    """Unified trace payload — session + timeline + code + chat + metrics."""

    session: CognitiveSessionResponse
    timeline: list[TimelineEventResponse] = []
    code_evolution: list[CodeSnapshotEntry] = []
    chat: list[TraceChatMessageResponse] = []
    metrics: CognitiveMetricsResponse | None = None
    verification: VerifyResponse | None = None


class TraceStandardResponse(BaseModel):
    status: str = "ok"
    data: TraceResponse
    meta: dict | None = None  # type: ignore[type-arg]
    errors: list = []  # type: ignore[type-arg]


class TimelineEventResponse(BaseModel):
    """Single event in the timeline with N4 level extracted."""

    id: str
    event_type: str
    sequence_number: int
    n4_level: int | None = None
    payload: dict  # type: ignore[type-arg]
    created_at: datetime

    @classmethod
    def from_orm(cls, obj: object) -> "TimelineEventResponse":
        payload = getattr(obj, "payload", {}) or {}
        n4 = payload.get("n4_level") if isinstance(payload, dict) else None
        return cls(
            id=str(getattr(obj, "id")),
            event_type=getattr(obj, "event_type"),
            sequence_number=getattr(obj, "sequence_number"),
            n4_level=int(n4) if n4 is not None else None,
            payload=payload,
            created_at=getattr(obj, "created_at"),
        )


class TimelineResponse(BaseModel):
    status: str = "ok"
    data: list[TimelineEventResponse] = []
    meta: SessionListMeta = SessionListMeta()
    errors: list = []  # type: ignore[type-arg]


class CodeSnapshotEntry(BaseModel):
    """A single code snapshot in the evolution (docente/admin)."""

    snapshot_id: str
    code: str
    snapshot_at: datetime
    previous_snapshot_id: str | None = None
    previous_snapshot_at: datetime | None = None
    diff_unified: str | None = None


class CodeEvolutionResponse(BaseModel):
    status: str = "ok"
    data: list[CodeSnapshotEntry] = []
    meta: dict | None = None  # type: ignore[type-arg]
    errors: list = []  # type: ignore[type-arg]
