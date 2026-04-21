"""Unit tests for research export utilities — CSV builder and pseudonymize integration."""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any

import pytest

from app.features.cognitive.export_router import _build_csv_response
from app.features.cognitive.pseudonymize import pseudonymize_student_id, scrub_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_body(streaming_response) -> str:
    """Collect all content from a StreamingResponse body_iterator (async)."""
    parts = []
    async for chunk in streaming_response.body_iterator:
        if isinstance(chunk, bytes):
            parts.append(chunk.decode("utf-8"))
        else:
            parts.append(str(chunk))
    return "".join(parts)


async def _read_csv(streaming_response) -> list[dict[str, str]]:
    """Collect all content from a StreamingResponse and parse as CSV."""
    content = await _collect_body(streaming_response)
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def _make_session(
    *,
    session_id: str | None = None,
    student_id: str | None = None,
    exercise_id: str | None = None,
    commission_id: str | None = None,
    n1_score: float = 75.0,
    event_count: int = 3,
) -> dict[str, Any]:
    return {
        "session_id": session_id or str(uuid.uuid4()),
        "student_id": student_id or str(uuid.uuid4()),
        "exercise_id": exercise_id or str(uuid.uuid4()),
        "commission_id": commission_id or str(uuid.uuid4()),
        "started_at": "2026-01-01T10:00:00",
        "closed_at": "2026-01-01T11:00:00",
        "n1_score": n1_score,
        "n2_score": 80.0,
        "n3_score": 60.0,
        "n4_score": 70.0,
        "qe_score": 72.5,
        "temporal_coherence": 65.0,
        "code_discourse": 55.0,
        "inter_iteration": 50.0,
        "events": [{"event_type": "code.run"} for _ in range(event_count)],
    }


_META: dict[str, Any] = {
    "total_sessions": 1,
    "is_pseudonymized": False,
    "exported_at": "2026-01-01T12:00:00",
}


# ---------------------------------------------------------------------------
# _build_csv_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_csv_response_empty_data():
    response = _build_csv_response([], _META)
    content = await _collect_body(response)
    assert "No data" in content


@pytest.mark.asyncio
async def test_build_csv_response_single_row_has_correct_headers():
    data = [_make_session()]
    response = _build_csv_response(data, _META)
    content = await _collect_body(response)
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []
    assert "session_id" in headers
    assert "student_id" in headers
    assert "n1_score" in headers
    assert "event_count" in headers


@pytest.mark.asyncio
async def test_build_csv_response_event_count_correct():
    data = [_make_session(event_count=5)]
    response = _build_csv_response(data, _META)
    rows = await _read_csv(response)
    assert len(rows) == 1
    assert rows[0]["event_count"] == "5"


@pytest.mark.asyncio
async def test_build_csv_response_multiple_rows():
    data = [_make_session(), _make_session(), _make_session()]
    response = _build_csv_response(data, _META)
    rows = await _read_csv(response)
    assert len(rows) == 3


def test_build_csv_response_content_type():
    response = _build_csv_response([_make_session()], _META)
    assert response.media_type == "text/csv"


def test_build_csv_response_content_disposition_header():
    response = _build_csv_response([_make_session()], _META)
    assert "attachment" in response.headers["content-disposition"]
    assert "cognitive-data.csv" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_build_csv_response_scores_are_preserved():
    sid = str(uuid.uuid4())
    data = [_make_session(student_id=sid, n1_score=88.5)]
    response = _build_csv_response(data, _META)
    rows = await _read_csv(response)
    assert rows[0]["n1_score"] == "88.5"
    assert rows[0]["student_id"] == sid


# ---------------------------------------------------------------------------
# scrub_payload integration — verifying it works with real export payloads
# ---------------------------------------------------------------------------


def test_scrub_payload_in_export_context():
    """Simulate the payload scrubbing that happens during a pseudonymized export."""
    raw_payload = {
        "message_content": "What does the for loop do here?",
        "code": "for i in range(10):\n    print(i)\n",
        "event_type": "tutor.question_asked",
        "duration_ms": 1200,
    }
    scrubbed = scrub_payload(raw_payload)
    assert scrubbed["message_content"] == "[REDACTED]"
    assert scrubbed["code"] == {"line_count": 2}
    assert scrubbed["event_type"] == "tutor.question_asked"
    assert scrubbed["duration_ms"] == 1200


# ---------------------------------------------------------------------------
# pseudonymize_student_id integration — verifying consistency in export rows
# ---------------------------------------------------------------------------


def test_pseudonymize_student_id_consistent_across_sessions():
    """Same student in multiple sessions must produce the same pseudonym."""
    salt = "export-test-salt"
    sid = "abc123-student"
    pseudo1 = pseudonymize_student_id(sid, salt=salt)
    pseudo2 = pseudonymize_student_id(sid, salt=salt)
    assert pseudo1 == pseudo2


def test_pseudonymize_student_id_different_students_differ():
    """Different students must not collide."""
    salt = "export-test-salt"
    p1 = pseudonymize_student_id("student-A", salt=salt)
    p2 = pseudonymize_student_id("student-B", salt=salt)
    assert p1 != p2
