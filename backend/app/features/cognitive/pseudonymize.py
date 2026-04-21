from __future__ import annotations

import hashlib
from typing import Any

from app.config import get_settings


# Fields whose string value is replaced with the literal "[REDACTED]"
_SENSITIVE_TEXT_FIELDS = frozenset({
    "message_content",
    "tutor_response",
    "content",
    "student_message",
    "assistant_message",
})

# Fields whose string value is replaced with a structural summary
_SENSITIVE_CODE_FIELDS = frozenset({
    "code",
    "snapshot_content",
    "pseudocode_content",
})


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *payload* with sensitive fields redacted.

    Text fields listed in ``_SENSITIVE_TEXT_FIELDS`` are replaced with the
    string ``"[REDACTED]"``.  Code fields listed in ``_SENSITIVE_CODE_FIELDS``
    are replaced with ``{"line_count": N}`` where N is the number of source
    lines, preserving structural information without exposing content.

    Non-sensitive keys are copied verbatim.  Nested dicts are NOT recursed —
    only top-level keys are checked.
    """
    scrubbed: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _SENSITIVE_TEXT_FIELDS and isinstance(value, str):
            scrubbed[key] = "[REDACTED]"
        elif key in _SENSITIVE_CODE_FIELDS and isinstance(value, str):
            line_count = len(value.splitlines()) if value else 0
            scrubbed[key] = {"line_count": line_count}
        else:
            scrubbed[key] = value
    return scrubbed


def pseudonymize_student_id(student_id: str, salt: str | None = None) -> str:
    """Return a deterministic SHA-256 pseudonym for *student_id*.

    The pseudonym is computed as ``SHA256(student_id + ":" + salt)`` and
    returned as a lowercase hex digest.  Using a per-deployment salt stored
    in settings ensures that pseudonyms cannot be reversed by an external
    party who does not know the salt.

    Args:
        student_id: The raw student UUID string to pseudonymize.
        salt: Optional override salt.  Defaults to ``settings.pseudonymization_salt``.

    Returns:
        64-character lowercase hex string.
    """
    if salt is None:
        salt = get_settings().pseudonymization_salt
    data = f"{student_id}:{salt}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
