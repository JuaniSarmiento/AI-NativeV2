"""Unit tests for CTR hash chain builder (ctr_builder.py)."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.features.cognitive.ctr_builder import (
    compute_event_hash,
    compute_event_hash_v1,
    compute_genesis_hash,
    verify_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_event(
    sequence_number: int,
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    previous_hash: str,
    created_at: datetime,
) -> MagicMock:
    """Build a lightweight mock that looks like a CognitiveEvent ORM object.

    Uses the V1 formula so that existing verify_chain() calls with the default
    chain_version=1 continue to pass.
    """
    event_hash = compute_event_hash_v1(previous_hash, event_type, payload, created_at)
    mock = MagicMock()
    mock.sequence_number = sequence_number
    mock.event_type = event_type
    mock.payload = payload
    mock.previous_hash = previous_hash
    mock.event_hash = event_hash
    mock.created_at = created_at
    return mock


# ---------------------------------------------------------------------------
# compute_genesis_hash
# ---------------------------------------------------------------------------


def test_genesis_hash_is_deterministic() -> None:
    """Same inputs must always produce the same genesis hash."""
    session_id = str(uuid.uuid4())
    started_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    h1 = compute_genesis_hash(session_id, started_at)
    h2 = compute_genesis_hash(session_id, started_at)

    assert h1 == h2


def test_genesis_hash_is_64_hex_chars() -> None:
    """SHA-256 output is always 64 lowercase hex characters."""
    h = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_genesis_hash_different_for_different_session_ids() -> None:
    started_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    h1 = compute_genesis_hash(str(uuid.uuid4()), started_at)
    h2 = compute_genesis_hash(str(uuid.uuid4()), started_at)
    assert h1 != h2


def test_genesis_hash_different_for_different_timestamps() -> None:
    session_id = str(uuid.uuid4())
    h1 = compute_genesis_hash(session_id, datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc))
    h2 = compute_genesis_hash(session_id, datetime(2026, 4, 14, 12, 0, 1, tzinfo=timezone.utc))
    assert h1 != h2


def test_genesis_hash_formula() -> None:
    """Verify the exact SHA-256 formula: 'GENESIS:' + session_id + ':' + iso."""
    session_id = "test-session-123"
    started_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    expected_data = f"GENESIS:{session_id}:{started_at.isoformat()}"
    expected_hash = hashlib.sha256(expected_data.encode("utf-8")).hexdigest()
    assert compute_genesis_hash(session_id, started_at) == expected_hash


# ---------------------------------------------------------------------------
# compute_event_hash
# ---------------------------------------------------------------------------


def test_event_hash_is_deterministic() -> None:
    """Same inputs produce the same event hash."""
    previous_hash = "a" * 64
    payload = {"key": "value", "num": 42}
    ts = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    h1 = compute_event_hash(previous_hash, "code.run", payload, ts)
    h2 = compute_event_hash(previous_hash, "code.run", payload, ts)

    assert h1 == h2


def test_event_hash_depends_on_previous_hash() -> None:
    """Changing previous_hash produces a different event hash."""
    payload = {"key": "value"}
    ts = _utcnow()

    h1 = compute_event_hash("a" * 64, "reads_problem", payload, ts)
    h2 = compute_event_hash("b" * 64, "reads_problem", payload, ts)

    assert h1 != h2


def test_event_hash_depends_on_event_type() -> None:
    previous_hash = "a" * 64
    payload = {}
    ts = _utcnow()

    h1 = compute_event_hash(previous_hash, "reads_problem", payload, ts)
    h2 = compute_event_hash(previous_hash, "code.run", payload, ts)

    assert h1 != h2


def test_event_hash_depends_on_payload() -> None:
    previous_hash = "a" * 64
    ts = _utcnow()

    h1 = compute_event_hash(previous_hash, "reads_problem", {"a": 1}, ts)
    h2 = compute_event_hash(previous_hash, "reads_problem", {"a": 2}, ts)

    assert h1 != h2


def test_event_hash_payload_key_order_independent() -> None:
    """sort_keys=True ensures payload dict order does not affect hash."""
    previous_hash = "a" * 64
    ts = _utcnow()
    event_type = "code.run"

    h1 = compute_event_hash(previous_hash, event_type, {"b": 2, "a": 1}, ts)
    h2 = compute_event_hash(previous_hash, event_type, {"a": 1, "b": 2}, ts)

    assert h1 == h2


def test_event_hash_chains_correctly() -> None:
    """hash(n) incorporates hash(n-1) — changing any event breaks the chain."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ts1 = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 14, 12, 1, 0, tzinfo=timezone.utc)

    hash1 = compute_event_hash(genesis, "reads_problem", {}, ts1)
    hash2_with_hash1 = compute_event_hash(hash1, "code.run", {}, ts2)

    # If we use a different hash1 as input for event 2, we get a different hash2
    hash2_with_wrong_prev = compute_event_hash("x" * 64, "code.run", {}, ts2)

    assert hash2_with_hash1 != hash2_with_wrong_prev


# ---------------------------------------------------------------------------
# verify_chain
# ---------------------------------------------------------------------------


def _build_chain(
    genesis_hash: str, specs: list[tuple[str, dict]]  # type: ignore[type-arg]
) -> list[MagicMock]:
    """Build a list of mock events forming a valid chain."""
    events = []
    prev_hash = genesis_hash
    for i, (event_type, payload) in enumerate(specs, start=1):
        ts = datetime(2026, 4, 14, 12, i, 0, tzinfo=timezone.utc)
        event = _make_event(i, event_type, payload, prev_hash, ts)
        events.append(event)
        prev_hash = event.event_hash
    return events


def test_verify_chain_valid_empty_events() -> None:
    """A session with no events is valid — chain is just the genesis hash."""
    result = verify_chain("a" * 64, [])
    assert result["valid"] is True
    assert result["events_checked"] == 0


def test_verify_chain_valid_single_event() -> None:
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    events = _build_chain(genesis, [("reads_problem", {})])
    result = verify_chain(genesis, events)
    assert result["valid"] is True
    assert result["events_checked"] == 1


def test_verify_chain_valid_multiple_events() -> None:
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    specs = [
        ("reads_problem", {}),
        ("code.run", {"stdout": "hello"}),
        ("submission.created", {"submission_id": "abc"}),
    ]
    events = _build_chain(genesis, specs)
    result = verify_chain(genesis, events)
    assert result["valid"] is True
    assert result["events_checked"] == 3


def test_verify_chain_tampered_payload_fails() -> None:
    """Modifying payload on any event invalidates it and all subsequent hashes."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    specs = [
        ("reads_problem", {"a": 1}),
        ("code.run", {"b": 2}),
        ("submission.created", {"c": 3}),
    ]
    events = _build_chain(genesis, specs)

    # Tamper event 2's payload in place
    events[1].payload = {"b": 99}

    result = verify_chain(genesis, events)
    assert result["valid"] is False
    assert result["failed_at_sequence"] == 2


def test_verify_chain_tampered_first_event_fails_at_sequence_1() -> None:
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    events = _build_chain(genesis, [("reads_problem", {"orig": True})])
    events[0].payload = {"orig": False}

    result = verify_chain(genesis, events)
    assert result["valid"] is False
    assert result["failed_at_sequence"] == 1


def test_verify_chain_tampered_event_hash_directly() -> None:
    """Setting a wrong stored hash directly causes mismatch at that event."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    events = _build_chain(genesis, [("reads_problem", {}), ("code.run", {})])
    events[0].event_hash = "bad" + "0" * 61  # corrupt stored hash for event 1

    result = verify_chain(genesis, events)
    assert result["valid"] is False
    assert result["failed_at_sequence"] == 1
    assert result["expected_hash"] is not None
    assert result["actual_hash"] == "bad" + "0" * 61


def test_verify_chain_returns_expected_and_actual_on_failure() -> None:
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ts = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    events = _build_chain(genesis, [("reads_problem", {})])

    original_hash = events[0].event_hash
    events[0].event_hash = "z" * 64  # force mismatch

    result = verify_chain(genesis, events)
    assert result["valid"] is False
    assert result["actual_hash"] == "z" * 64
    assert result["expected_hash"] == original_hash


# ---------------------------------------------------------------------------
# session_hash should equal last event_hash
# ---------------------------------------------------------------------------


def test_session_hash_equals_last_event_hash() -> None:
    """The session_hash sealed at close must equal the last event's event_hash."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    events = _build_chain(
        genesis,
        [
            ("reads_problem", {}),
            ("code.run", {}),
            ("submission.created", {}),
        ],
    )
    # Simulate what close_session does
    last_event_hash = events[-1].event_hash
    simulated_session_hash = last_event_hash

    # Verify chain should still pass
    result = verify_chain(genesis, events)
    assert result["valid"] is True
    # And the sealed hash is the final link
    assert simulated_session_hash == events[-1].event_hash


# ---------------------------------------------------------------------------
# V1 / V2 hash formula distinction (Task 1.7)
# ---------------------------------------------------------------------------


def test_v1_hash_matches_original_formula() -> None:
    """compute_event_hash_v1 must reproduce the exact pre-V2 formula."""
    previous_hash = "a" * 64
    event_type = "reads_problem"
    payload = {"key": "value"}
    ts = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)

    payload_str = json.dumps(payload, sort_keys=True, default=str)
    expected_data = f"{previous_hash}:{event_type}:{payload_str}:{ts.isoformat()}"
    expected_hash = hashlib.sha256(expected_data.encode("utf-8")).hexdigest()

    assert compute_event_hash_v1(previous_hash, event_type, payload, ts) == expected_hash


def test_v2_hash_includes_prompt_hash() -> None:
    """compute_event_hash with a non-empty prompt_hash differs from V1."""
    previous_hash = "a" * 64
    event_type = "reads_problem"
    payload = {"key": "value"}
    ts = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)
    ph = "p" * 64

    h_v1 = compute_event_hash_v1(previous_hash, event_type, payload, ts)
    h_v2 = compute_event_hash(previous_hash, event_type, payload, ts, prompt_hash=ph)

    assert h_v1 != h_v2


def test_v2_with_empty_prompt_hash_differs_from_v1() -> None:
    """V2 with empty prompt_hash still differs from V1 due to trailing colon."""
    previous_hash = "a" * 64
    event_type = "code.run"
    payload = {}
    ts = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)

    h_v1 = compute_event_hash_v1(previous_hash, event_type, payload, ts)
    h_v2 = compute_event_hash(previous_hash, event_type, payload, ts, prompt_hash="")

    assert h_v1 != h_v2


def _make_event_v1(
    sequence_number: int,
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    previous_hash: str,
    created_at: datetime,
) -> MagicMock:
    """Build a mock CognitiveEvent whose hash was computed with V1 formula."""
    event_hash = compute_event_hash_v1(previous_hash, event_type, payload, created_at)
    mock = MagicMock()
    mock.sequence_number = sequence_number
    mock.event_type = event_type
    mock.payload = payload
    mock.previous_hash = previous_hash
    mock.event_hash = event_hash
    mock.created_at = created_at
    return mock


def _make_event_v2(
    sequence_number: int,
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    previous_hash: str,
    created_at: datetime,
    prompt_hash: str = "",
) -> MagicMock:
    """Build a mock CognitiveEvent whose hash was computed with V2 formula."""
    enriched = {**payload}
    if prompt_hash:
        enriched["prompt_hash"] = prompt_hash
    event_hash = compute_event_hash(
        previous_hash, event_type, enriched, created_at, prompt_hash=prompt_hash
    )
    mock = MagicMock()
    mock.sequence_number = sequence_number
    mock.event_type = event_type
    mock.payload = enriched
    mock.previous_hash = previous_hash
    mock.event_hash = event_hash
    mock.created_at = created_at
    return mock


def test_verify_chain_v1_uses_v1_formula() -> None:
    """verify_chain with chain_version=1 validates a chain built with V1 hashes."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ts1 = datetime(2026, 4, 21, 10, 1, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 21, 10, 2, 0, tzinfo=timezone.utc)

    e1 = _make_event_v1(1, "reads_problem", {}, genesis, ts1)
    e2 = _make_event_v1(2, "code.run", {"stdout": "ok"}, e1.event_hash, ts2)

    result = verify_chain(genesis, [e1, e2], chain_version=1)
    assert result["valid"] is True
    assert result["events_checked"] == 2


def test_verify_chain_v2_uses_v2_formula() -> None:
    """verify_chain with chain_version=2 validates a chain built with V2 hashes."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ph = "c" * 64
    ts1 = datetime(2026, 4, 21, 10, 1, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 21, 10, 2, 0, tzinfo=timezone.utc)

    e1 = _make_event_v2(1, "reads_problem", {}, genesis, ts1, prompt_hash=ph)
    e2 = _make_event_v2(2, "code.run", {}, e1.event_hash, ts2, prompt_hash=ph)

    result = verify_chain(genesis, [e1, e2], chain_version=2)
    assert result["valid"] is True
    assert result["events_checked"] == 2


def test_verify_chain_v1_rejects_v2_hashes() -> None:
    """A V1 verifier rejects a chain that was built with the V2 formula."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ph = "d" * 64
    ts = datetime(2026, 4, 21, 10, 1, 0, tzinfo=timezone.utc)

    e1 = _make_event_v2(1, "reads_problem", {}, genesis, ts, prompt_hash=ph)

    result = verify_chain(genesis, [e1], chain_version=1)
    assert result["valid"] is False
    assert result["failed_at_sequence"] == 1


def test_verify_chain_v2_rejects_v1_hashes() -> None:
    """A V2 verifier rejects a chain that was built with the V1 formula."""
    genesis = compute_genesis_hash(str(uuid.uuid4()), _utcnow())
    ts = datetime(2026, 4, 21, 10, 1, 0, tzinfo=timezone.utc)

    e1 = _make_event_v1(1, "reads_problem", {}, genesis, ts)

    result = verify_chain(genesis, [e1], chain_version=2)
    assert result["valid"] is False
    assert result["failed_at_sequence"] == 1
