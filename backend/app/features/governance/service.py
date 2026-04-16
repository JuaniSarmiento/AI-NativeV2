from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.governance.models import GovernanceEvent
from app.features.governance.repositories import GovernanceEventRepository
from app.shared.models.event_outbox import EventOutbox

logger = get_logger(__name__)


class GovernanceService:
    """Manages governance event recording and retrieval.

    This service is pure Python — no FastAPI imports.  It is instantiated
    with an ``AsyncSession`` and creates its own repository internally.

    All mutation methods ``flush()`` but never ``commit()`` — transaction
    lifecycle is the caller's responsibility (Unit of Work pattern).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceEventRepository(session)

    # ------------------------------------------------------------------
    # Generic record
    # ------------------------------------------------------------------

    async def record_event(
        self,
        *,
        event_type: str,
        actor_id: uuid.UUID,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        details: dict,  # type: ignore[type-arg]
    ) -> GovernanceEvent:
        """Persist a governance event and flush within the current transaction.

        Args:
            event_type: Dot-namespaced type, e.g. ``"prompt.created"``.
            actor_id: UUID of the user or system principal that triggered the event.
            target_type: Optional label for the target entity type.
            target_id: Optional UUID of the target entity.
            details: Arbitrary JSON-serialisable payload.

        Returns:
            The persisted :class:`GovernanceEvent` instance.
        """
        event = GovernanceEvent(
            event_type=event_type,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
        self._session.add(event)
        await self._session.flush()

        logger.info(
            "Governance event recorded",
            extra={
                "event_type": event_type,
                "actor_id": str(actor_id),
                "target_type": target_type,
                "target_id": str(target_id) if target_id else None,
            },
        )
        return event

    # ------------------------------------------------------------------
    # Domain-specific convenience methods
    # ------------------------------------------------------------------

    async def record_guardrail_violation(
        self,
        *,
        student_id: uuid.UUID,
        interaction_id: uuid.UUID,
        exercise_id: uuid.UUID,
        session_id: uuid.UUID,
        violation_type: str | None,
        violation_details: str | None,
    ) -> GovernanceEvent:
        """Record a guardrail violation event and emit an outbox event.

        The actor is the student whose message triggered the violation.
        The target is the assistant interaction that violated the guardrail.

        Also emits a ``governance.flag.raised`` outbox event so downstream
        consumers (e.g. teacher alerts, analytics) can react asynchronously.
        """
        details = {
            "violation_type": violation_type,
            "violation_details": violation_details,
            "exercise_id": str(exercise_id),
            "session_id": str(session_id),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        event = await self.record_event(
            event_type="guardrail.triggered",
            actor_id=student_id,
            target_type="interaction",
            target_id=interaction_id,
            details=details,
        )

        # Emit outbox event for async consumers
        self._session.add(EventOutbox(
            event_type="governance.flag.raised",
            payload={
                "governance_event_id": str(event.id),
                "student_id": str(student_id),
                "interaction_id": str(interaction_id),
                "exercise_id": str(exercise_id),
                "session_id": str(session_id),
                "violation_type": violation_type,
                "violation_details": violation_details,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        ))
        await self._session.flush()

        logger.warning(
            "Guardrail violation governance event raised",
            extra={
                "student_id": str(student_id),
                "interaction_id": str(interaction_id),
                "violation_type": violation_type,
            },
        )
        return event

    async def record_prompt_created(
        self,
        *,
        prompt_id: uuid.UUID,
        name: str,
        version: str,
        sha256_hash: str,
        created_by: uuid.UUID,
    ) -> GovernanceEvent:
        """Record a governance event when a new system prompt is created.

        Args:
            prompt_id: UUID of the newly created prompt.
            name: Human-readable name of the prompt.
            version: Semantic version string (e.g. ``"1.0.0"``).
            sha256_hash: SHA-256 hash of the prompt content.
            created_by: UUID of the admin that created the prompt.
        """
        return await self.record_event(
            event_type="prompt.created",
            actor_id=created_by,
            target_type="prompt",
            target_id=prompt_id,
            details={
                "name": name,
                "version": version,
                "sha256_hash": sha256_hash,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    async def record_prompt_activated(
        self,
        *,
        prompt_id: uuid.UUID,
        name: str,
        old_hash: str | None,
        new_hash: str,
        actor_id: uuid.UUID,
    ) -> GovernanceEvent:
        """Record a governance event when a system prompt is activated.

        Captures the old and new hashes to support cryptographic audit trails.

        Args:
            prompt_id: UUID of the prompt being activated.
            name: Human-readable name of the prompt.
            old_hash: SHA-256 hash of the previously active prompt (``None`` if none).
            new_hash: SHA-256 hash of the newly activated prompt.
            actor_id: UUID of the admin that performed the activation.
        """
        return await self.record_event(
            event_type="prompt.activated",
            actor_id=actor_id,
            target_type="prompt",
            target_id=prompt_id,
            details={
                "name": name,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    async def record_prompt_deactivated(
        self,
        *,
        prompt_id: uuid.UUID,
        name: str,
        sha256_hash: str,
        actor_id: uuid.UUID,
    ) -> GovernanceEvent:
        """Record a governance event when a system prompt is deactivated."""
        return await self.record_event(
            event_type="prompt.deactivated",
            actor_id=actor_id,
            target_type="prompt",
            target_id=prompt_id,
            details={
                "name": name,
                "sha256_hash": sha256_hash,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def list_events(
        self,
        page: int = 1,
        per_page: int = 20,
        event_type: str | None = None,
    ) -> tuple[list[GovernanceEvent], int]:
        """Return paginated governance events.

        Args:
            page: 1-based page number.
            per_page: Maximum items per page.
            event_type: Optional exact match filter on ``event_type``.

        Returns:
            A tuple of (items, total_count).
        """
        return await self._repo.list_events(
            page=page,
            per_page=per_page,
            event_type=event_type,
        )
