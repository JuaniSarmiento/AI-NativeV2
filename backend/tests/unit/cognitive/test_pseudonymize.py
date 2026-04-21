"""Unit tests for cognitive pseudonymize utilities."""
from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest

from app.features.cognitive.pseudonymize import pseudonymize_student_id, scrub_payload


# ---------------------------------------------------------------------------
# scrub_payload
# ---------------------------------------------------------------------------


def test_scrub_payload_redacts_message_content():
    payload = {"message_content": "My solution is x = 5", "event_type": "tutor.message"}
    result = scrub_payload(payload)
    assert result["message_content"] == "[REDACTED]"
    assert result["event_type"] == "tutor.message"


def test_scrub_payload_redacts_tutor_response():
    payload = {"tutor_response": "Have you considered using a loop?"}
    result = scrub_payload(payload)
    assert result["tutor_response"] == "[REDACTED]"


def test_scrub_payload_redacts_content_field():
    payload = {"content": "Some message text here"}
    result = scrub_payload(payload)
    assert result["content"] == "[REDACTED]"


def test_scrub_payload_redacts_student_message():
    payload = {"student_message": "How do I fix this bug?"}
    result = scrub_payload(payload)
    assert result["student_message"] == "[REDACTED]"


def test_scrub_payload_redacts_assistant_message():
    payload = {"assistant_message": "Think about what the loop invariant should be."}
    result = scrub_payload(payload)
    assert result["assistant_message"] == "[REDACTED]"


def test_scrub_payload_replaces_code_with_line_count():
    code = "def foo():\n    x = 1\n    return x\n"
    payload = {"code": code, "language": "python"}
    result = scrub_payload(payload)
    assert result["code"] == {"line_count": 3}
    assert result["language"] == "python"


def test_scrub_payload_replaces_snapshot_content_with_line_count():
    code = "line1\nline2\nline3\nline4\nline5"
    payload = {"snapshot_content": code}
    result = scrub_payload(payload)
    assert result["snapshot_content"] == {"line_count": 5}


def test_scrub_payload_replaces_pseudocode_content():
    pseudocode = "FOR i IN range\n  DO thing\n"
    payload = {"pseudocode_content": pseudocode}
    result = scrub_payload(payload)
    assert result["pseudocode_content"] == {"line_count": 2}


def test_scrub_payload_empty_code_gives_zero_lines():
    payload = {"code": ""}
    result = scrub_payload(payload)
    assert result["code"] == {"line_count": 0}


def test_scrub_payload_preserves_non_sensitive_fields():
    payload = {
        "event_type": "code.run",
        "sequence_number": 5,
        "n4_level": 2,
        "duration_ms": 450,
        "success": True,
    }
    result = scrub_payload(payload)
    assert result == payload


def test_scrub_payload_empty_dict():
    assert scrub_payload({}) == {}


def test_scrub_payload_non_string_sensitive_field_preserved():
    """Non-string values for sensitive field names are passed through unchanged."""
    payload = {"message_content": 42, "code": None}
    result = scrub_payload(payload)
    # Non-string values are not matched by the isinstance checks
    assert result["message_content"] == 42
    assert result["code"] is None


# ---------------------------------------------------------------------------
# pseudonymize_student_id
# ---------------------------------------------------------------------------


def test_pseudonymize_student_id_is_deterministic():
    sid = "550e8400-e29b-41d4-a716-446655440000"
    salt = "test-salt"
    result1 = pseudonymize_student_id(sid, salt=salt)
    result2 = pseudonymize_student_id(sid, salt=salt)
    assert result1 == result2


def test_pseudonymize_student_id_correct_hash():
    sid = "550e8400-e29b-41d4-a716-446655440000"
    salt = "test-salt"
    expected = hashlib.sha256(f"{sid}:{salt}".encode("utf-8")).hexdigest()
    assert pseudonymize_student_id(sid, salt=salt) == expected


def test_pseudonymize_student_id_different_salt_produces_different_hash():
    sid = "550e8400-e29b-41d4-a716-446655440000"
    hash1 = pseudonymize_student_id(sid, salt="salt-a")
    hash2 = pseudonymize_student_id(sid, salt="salt-b")
    assert hash1 != hash2


def test_pseudonymize_student_id_different_ids_produce_different_hashes():
    salt = "fixed-salt"
    hash1 = pseudonymize_student_id("id-one", salt=salt)
    hash2 = pseudonymize_student_id("id-two", salt=salt)
    assert hash1 != hash2


def test_pseudonymize_student_id_output_is_64_hex_chars():
    result = pseudonymize_student_id("any-id", salt="any-salt")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_pseudonymize_student_id_uses_settings_salt_by_default():
    """When no explicit salt is passed, the settings salt is used."""
    sid = "some-student-id"
    settings_salt = "settings-derived-salt"
    expected = hashlib.sha256(f"{sid}:{settings_salt}".encode("utf-8")).hexdigest()

    with patch("app.features.cognitive.pseudonymize.get_settings") as mock_settings:
        mock_settings.return_value.pseudonymization_salt = settings_salt
        result = pseudonymize_student_id(sid)

    assert result == expected
