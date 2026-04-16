"""Unit tests for EPIC-16 cognitive trace endpoints.

Tests router functions directly with mocked dependencies.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.cognitive.schemas import (
    SessionListItem,
    TimelineEventResponse,
    CodeSnapshotEntry,
)


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------


class TestSessionListItem:
    def test_from_orm(self) -> None:
        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.student_id = uuid.uuid4()
        obj.exercise_id = uuid.uuid4()
        obj.commission_id = uuid.uuid4()
        obj.started_at = datetime.now(tz=timezone.utc)
        obj.closed_at = None
        obj.status = "closed"

        item = SessionListItem.from_orm(obj)
        assert item.id == str(obj.id)
        assert item.status == "closed"

    def test_from_orm_enum_status(self) -> None:
        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.student_id = uuid.uuid4()
        obj.exercise_id = uuid.uuid4()
        obj.commission_id = uuid.uuid4()
        obj.started_at = datetime.now(tz=timezone.utc)
        obj.closed_at = None

        # Simulate enum-like status
        class FakeEnum:
            value = "open"
        obj.status = FakeEnum()

        item = SessionListItem.from_orm(obj)
        assert item.status == "open"


class TestTimelineEventResponse:
    def test_extracts_n4_level(self) -> None:
        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.event_type = "tutor.question_asked"
        obj.sequence_number = 5
        obj.payload = {"n4_level": 3, "content": "test"}
        obj.created_at = datetime.now(tz=timezone.utc)

        resp = TimelineEventResponse.from_orm(obj)
        assert resp.n4_level == 3
        assert resp.event_type == "tutor.question_asked"

    def test_null_n4_when_absent(self) -> None:
        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.event_type = "reads_problem"
        obj.sequence_number = 1
        obj.payload = {"student_id": "abc"}
        obj.created_at = datetime.now(tz=timezone.utc)

        resp = TimelineEventResponse.from_orm(obj)
        assert resp.n4_level is None

    def test_handles_empty_payload(self) -> None:
        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.event_type = "session.started"
        obj.sequence_number = 0
        obj.payload = {}
        obj.created_at = datetime.now(tz=timezone.utc)

        resp = TimelineEventResponse.from_orm(obj)
        assert resp.n4_level is None


class TestCodeSnapshotEntry:
    def test_serializes(self) -> None:
        entry = CodeSnapshotEntry(
            snapshot_id="abc-123",
            code="print('hello')",
            snapshot_at=datetime.now(tz=timezone.utc),
        )
        assert entry.code == "print('hello')"
        assert entry.snapshot_id == "abc-123"


# ---------------------------------------------------------------------------
# Repository method tests
# ---------------------------------------------------------------------------


class TestSessionsByCommission:
    @pytest.mark.asyncio
    async def test_returns_paginated(self) -> None:
        from app.features.cognitive.repositories import CognitiveSessionRepository
        from app.features.cognitive.models import CognitiveSession

        session = MagicMock()
        commission_id = uuid.uuid4()

        # Mock count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 3

        # Mock items
        items_result = MagicMock()
        s1 = MagicMock(spec=CognitiveSession)
        s2 = MagicMock(spec=CognitiveSession)
        items_result.scalars.return_value.all.return_value = [s1, s2]

        session.execute = AsyncMock(side_effect=[count_result, items_result])

        repo = CognitiveSessionRepository(session)
        items, total = await repo.get_sessions_by_commission(
            commission_id=commission_id, page=1, per_page=2
        )

        assert total == 3
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_applies_student_filter(self) -> None:
        from app.features.cognitive.repositories import CognitiveSessionRepository

        session = MagicMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, items_result])

        repo = CognitiveSessionRepository(session)
        items, total = await repo.get_sessions_by_commission(
            commission_id=uuid.uuid4(),
            student_id=uuid.uuid4(),
        )

        assert total == 0
        assert session.execute.call_count == 2


# ---------------------------------------------------------------------------
# Governance prompts schema tests
# ---------------------------------------------------------------------------


class TestPromptHistoryResponse:
    def test_from_orm_uuid(self) -> None:
        from app.features.governance.schemas import PromptHistoryResponse

        obj = MagicMock()
        obj.id = uuid.uuid4()
        obj.name = "socratic_v2"
        obj.version = "2.0"
        obj.sha256_hash = "abc123def456" * 5
        obj.is_active = True
        obj.created_at = datetime.now(tz=timezone.utc)

        resp = PromptHistoryResponse.from_orm_uuid(obj)
        assert resp.id == str(obj.id)
        assert resp.is_active is True
        assert resp.name == "socratic_v2"
