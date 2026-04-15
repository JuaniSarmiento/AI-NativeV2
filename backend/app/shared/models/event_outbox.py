from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class EventOutbox(Base):
    """Transactional outbox for reliable event publishing to Redis Streams.

    Events are written atomically within the same DB transaction as the
    business operation that triggered them. The OutboxWorker then reads
    ``pending`` rows and publishes them to the appropriate Redis Stream,
    marking each as ``processed`` on success or incrementing ``retry_count``
    on failure.

    Schema: operational (shared across all phases for event production).
    """

    __tablename__ = "event_outbox"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Dot-namespaced event type, e.g. 'submission.created'",
    )
    payload: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        comment="Arbitrary JSON payload — must be serialisable",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
        comment="pending | processed | failed",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    retry_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    def __repr__(self) -> str:
        return (
            f"<EventOutbox id={self.id} type={self.event_type!r} status={self.status!r}>"
        )
