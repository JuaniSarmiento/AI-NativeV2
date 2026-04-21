from __future__ import annotations

import hashlib
import json
from datetime import datetime


def compute_genesis_hash(session_id: str, started_at: datetime) -> str:
    """Compute the genesis hash that anchors the CTR hash chain.

    The genesis hash is deterministic: given the same session_id and
    started_at timestamp, it always produces the same result.

    Formula: SHA-256("GENESIS:" + session_id + ":" + started_at_iso)

    Args:
        session_id: String representation of the session UUID.
        started_at: Timezone-aware datetime of session creation.

    Returns:
        64-character lowercase hex string.
    """
    data = f"GENESIS:{session_id}:{started_at.isoformat()}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_event_hash(
    previous_hash: str,
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    timestamp: datetime,
    *,
    prompt_hash: str = "",
) -> str:
    """Compute the hash for a single CTR event (V2 formula).

    Each event's hash incorporates the previous hash, making the chain
    tamper-evident: modifying any event invalidates all subsequent hashes.

    V2 Formula: SHA-256(previous_hash + ":" + event_type + ":" + json(payload)
                         + ":" + timestamp_iso + ":" + prompt_hash)

    Payload is serialized with sort_keys=True and default=str to ensure
    determinism regardless of insertion order or non-JSON-native types.

    Args:
        previous_hash: The event_hash of the preceding event, or genesis_hash for sequence 1.
        event_type: Canonical CTR event type string.
        payload: Event payload dict (must be JSON-serialisable after str coercion).
        timestamp: The event's created_at timestamp (timezone-aware).
        prompt_hash: SHA-256 of the active system prompt (default "").
            When empty, the trailing colon is still appended (V2 differs from V1).

    Returns:
        64-character lowercase hex string.
    """
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    data = f"{previous_hash}:{event_type}:{payload_str}:{timestamp.isoformat()}:{prompt_hash}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_event_hash_v1(
    previous_hash: str,
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    timestamp: datetime,
) -> str:
    """Compute the hash for a CTR event using the original V1 formula.

    Preserved for verifying chains that were created before chain_version=2.
    Do NOT use this for new events — use compute_event_hash() instead.

    V1 Formula: SHA-256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso)

    Args:
        previous_hash: The event_hash of the preceding event, or genesis_hash for sequence 1.
        event_type: Canonical CTR event type string.
        payload: Event payload dict (must be JSON-serialisable after str coercion).
        timestamp: The event's created_at timestamp (timezone-aware).

    Returns:
        64-character lowercase hex string.
    """
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    data = f"{previous_hash}:{event_type}:{payload_str}:{timestamp.isoformat()}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def verify_chain(
    genesis_hash: str,
    events: list,  # list of CognitiveEvent ORM objects
    *,
    chain_version: int = 1,
) -> dict:  # type: ignore[type-arg]
    """Verify the integrity of a CTR hash chain.

    Recalculates every event hash and compares it against the stored value.
    Returns on the first mismatch, reporting which sequence number failed.

    Args:
        genesis_hash: The session's genesis_hash (chain anchor).
        events: Ordered list of CognitiveEvent objects (ascending sequence_number).
        chain_version: Formula version used when the chain was built.
            1 = original formula (no prompt_hash).
            2 = V2 formula (includes prompt_hash extracted from event payload).

    Returns:
        dict with keys:
          - valid (bool): True if all hashes match.
          - events_checked (int | None): Number of events verified when valid.
          - failed_at_sequence (int | None): sequence_number of the first bad event.
          - expected_hash (str | None): Recalculated hash for the failing event.
          - actual_hash (str | None): Stored hash for the failing event.
    """
    expected_previous = genesis_hash
    for event in events:
        if chain_version >= 2:
            ph = event.payload.get("prompt_hash", "") if event.payload else ""
            recalculated = compute_event_hash(
                expected_previous,
                event.event_type,
                event.payload,
                event.created_at,
                prompt_hash=ph,
            )
        else:
            recalculated = compute_event_hash_v1(
                expected_previous,
                event.event_type,
                event.payload,
                event.created_at,
            )
        if recalculated != event.event_hash:
            return {
                "valid": False,
                "events_checked": None,
                "failed_at_sequence": event.sequence_number,
                "expected_hash": recalculated,
                "actual_hash": event.event_hash,
            }
        expected_previous = event.event_hash

    return {
        "valid": True,
        "events_checked": len(events),
        "failed_at_sequence": None,
        "expected_hash": None,
        "actual_hash": None,
    }
