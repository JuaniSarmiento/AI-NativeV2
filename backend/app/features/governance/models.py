from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class GovernanceEvent(Base):
    """Audit log for governance-level events.

    Records prompt lifecycle events (created, activated, deactivated),
    guardrail violations, policy changes, and model swaps.

    Schema: governance — owned exclusively by the governance layer.
    Actor IDs are stored without FK constraints to avoid cross-schema
    dependencies (actor lives in operational.users).
    """

    __tablename__ = "governance_events"
    __table_args__ = (
        Index("ix_governance_events_event_type", "event_type"),
        Index("ix_governance_events_actor_id", "actor_id"),
        {"schema": "governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Dot-namespaced event type, e.g. 'prompt.created', 'guardrail.triggered'",
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="ID of the user or system actor that triggered the event (no FK — cross-schema)",
    )
    target_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Type of the target entity, e.g. 'prompt', 'interaction'",
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="ID of the target entity (no FK — cross-schema)",
    )
    details: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Arbitrary JSON payload with event-specific details",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<GovernanceEvent id={self.id} type={self.event_type!r} actor={self.actor_id}>"
        )
