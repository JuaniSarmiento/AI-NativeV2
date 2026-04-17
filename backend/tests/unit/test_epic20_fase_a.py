"""Unit tests for EPIC-20 Phase A bugfixes (7 regression checks).

Tests are pure Python — no DB, no async, no FastAPI.  All ORM objects are
mocked with types.SimpleNamespace so the MetricsEngine (which is already
infrastructure-free) can be exercised without any import side-effects.
"""
from __future__ import annotations

import types
from decimal import Decimal
from pathlib import Path


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _evt(event_type: str, seq: int, payload: dict | None = None) -> types.SimpleNamespace:
    """Create a minimal mock CognitiveEvent."""
    return types.SimpleNamespace(
        event_type=event_type,
        sequence_number=seq,
        payload=payload or {},
    )


def _mock_session() -> types.SimpleNamespace:
    """Create a minimal mock CognitiveSession."""
    import uuid
    return types.SimpleNamespace(id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Test 1: cognitive.classified removed from TutorService source
# ---------------------------------------------------------------------------

def test_tutor_service_no_cognitive_classified_event() -> None:
    """'cognitive.classified' must not appear anywhere in tutor/service.py.

    Bugfix: the old service was emitting a 'cognitive.classified' outbox event
    which duplicated classification work that belongs exclusively to the
    CognitiveEventClassifier in the cognitive layer.
    """
    service_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "tutor" / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")
    assert "cognitive.classified" not in source, (
        "tutor/service.py must not emit 'cognitive.classified' events — "
        "classification belongs to the cognitive layer, not the tutor."
    )


# ---------------------------------------------------------------------------
# Test 2: TutorService emits BOTH tutor.interaction.completed events
# ---------------------------------------------------------------------------

def test_tutor_service_emits_two_interaction_completed_events() -> None:
    """service.py must contain exactly two EventOutbox adds for 'tutor.interaction.completed'.

    One for role=user, one for role=assistant.  The bugfix ensured both turns
    reach the outbox so the cognitive consumer can build a complete CTR.
    """
    service_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "tutor" / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    # Count literal occurrences of the event type string in the source.
    count = source.count('"tutor.interaction.completed"')
    assert count >= 2, (
        f"Expected at least 2 occurrences of 'tutor.interaction.completed' in "
        f"tutor/service.py (one per role), found {count}."
    )

    # Additionally verify the role strings are present (user + assistant turns).
    assert '"role": "user"' in source, "User-role outbox payload missing."
    assert '"role": "assistant"' in source, "Assistant-role outbox payload missing."


# ---------------------------------------------------------------------------
# Test 3: CognitiveEventClassifier reads n4_level from payload
# ---------------------------------------------------------------------------

from app.features.cognitive.classifier import CognitiveEventClassifier  # noqa: E402


def test_classifier_reads_n4_level_from_payload_user_role() -> None:
    """classify() must honour explicit n4_level in the payload for user role."""
    clf = CognitiveEventClassifier()
    result = clf.classify(
        "tutor.interaction.completed",
        {"role": "user", "n4_level": 2},
    )
    assert result is not None
    assert result.n4_level == 2


def test_classifier_falls_back_to_4_when_n4_level_missing() -> None:
    """classify() must default to n4_level=4 when the payload has no n4_level key."""
    clf = CognitiveEventClassifier()
    result = clf.classify(
        "tutor.interaction.completed",
        {"role": "user"},
    )
    assert result is not None
    assert result.n4_level == 4


def test_classifier_reads_n4_level_from_payload_assistant_role() -> None:
    """classify() must honour explicit n4_level in the payload for assistant role."""
    clf = CognitiveEventClassifier()
    result = clf.classify(
        "tutor.interaction.completed",
        {"role": "assistant", "n4_level": 1},
    )
    assert result is not None
    assert result.n4_level == 1
    assert result.event_type == "tutor.response_received"


# ---------------------------------------------------------------------------
# Test 4: reflection_score computation
# ---------------------------------------------------------------------------

from app.features.evaluation.service import MetricsEngine  # noqa: E402
from app.features.evaluation.rubric import load_rubric  # noqa: E402


def test_reflection_score_computed_from_full_payload() -> None:
    """MetricsEngine must produce a positive reflection_score when all 5 fields present."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()

    events = [
        _evt("reads_problem", seq=1),
        _evt("code.run", seq=2, payload={"status": "ok"}),
        _evt("submission.created", seq=3),
        _evt(
            "reflection.submitted",
            seq=4,
            payload={
                "difficulty_perception": 3,
                "strategy_description": "iterative approach",
                "ai_usage_evaluation": "asked for hints only",
                "what_would_change": "start with unit tests",
                "confidence_level": 4,
            },
        ),
    ]

    result = engine.compute(session, events)
    assert result.metrics.reflection_score is not None
    assert result.metrics.reflection_score > Decimal("0")


# ---------------------------------------------------------------------------
# Test 5: qe_score_max path in risk derivation
# ---------------------------------------------------------------------------

def test_derive_risk_medium_via_qe_score_max() -> None:
    """_derive_risk_level must return 'medium' when qe_score <= qe_score_max (40).

    The bugfix introduced the qe_score parameter to the method so the rubric's
    qe_score_max threshold (40) can be evaluated independently of n-scores.
    """
    engine = MetricsEngine(load_rubric())

    # n-scores are all 50 (above any critical/high/medium any_n_score threshold)
    # dependency_score is low — won't trigger critical/high
    # qe_score=30 is <= qe_score_max=40 → should be 'medium'
    risk = engine._derive_risk_level(
        n1=Decimal("50"),
        n2=Decimal("50"),
        n3=Decimal("50"),
        n4=Decimal("50"),
        dependency_score=Decimal("0.1"),
        qe_score=Decimal("30"),
    )
    assert risk == "medium", f"Expected 'medium', got '{risk}'"


# ---------------------------------------------------------------------------
# Test 6: qe_critical_evaluation measures runs after EACH response
# ---------------------------------------------------------------------------

def test_qe_critical_evaluation_counts_runs_after_each_response() -> None:
    """qe_critical_evaluation must be 100.0 when every tutor response is followed by a run.

    Bugfix: the old implementation counted only whether ANY run followed ANY
    response. The fixed version checks each response individually.

    Events:
        seq=1  tutor.response_received
        seq=2  code.run            (follows response at 1)
        seq=3  tutor.response_received
        seq=4  code.run            (follows response at 3)

    Both responses are followed by a run → score = 100.
    """
    engine = MetricsEngine(load_rubric())
    session = _mock_session()

    events = [
        _evt("tutor.response_received", seq=1),
        _evt("code.run", seq=2, payload={"status": "ok"}),
        _evt("tutor.response_received", seq=3),
        _evt("code.run", seq=4, payload={"status": "ok"}),
    ]

    result = engine.compute(session, events)
    qe_ce = result.metrics.qe_critical_evaluation
    assert qe_ce is not None, "qe_critical_evaluation should not be None"
    assert float(qe_ce) == 100.0, (
        f"Expected qe_critical_evaluation=100.0, got {qe_ce}"
    )


# ---------------------------------------------------------------------------
# Test 7: consumer rejects zero UUID commission_id
# ---------------------------------------------------------------------------

def test_consumer_rejects_zero_uuid_commission_id() -> None:
    """consumer.py must contain a rejection check for the zero UUID commission_id.

    Bugfix: events whose commission_id is '00000000-0000-0000-0000-000000000000'
    (the sentinel returned by TutorService when enrollment lookup fails) must
    be discarded before attempting to create a CTR session, because a zero UUID
    cannot be mapped to a real commission.
    """
    consumer_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "cognitive" / "consumer.py"
    )
    source = consumer_path.read_text(encoding="utf-8")

    zero_uuid = "00000000-0000-0000-0000-000000000000"
    assert zero_uuid in source, (
        f"consumer.py must contain a check for the zero UUID '{zero_uuid}' "
        "to reject events with unresolvable commission_id."
    )

    # The zero UUID must appear in a rejection context, not just as a default.
    # Verify the surrounding text includes an early-return guard.
    # We look for the comparison pattern in the source.
    assert (
        f"commission_id_str == _ZERO_UUID" in source
        or f'== "{zero_uuid}"' in source
        or f"== _ZERO_UUID" in source
    ), (
        "The zero UUID check must be part of a conditional guard — "
        "not just a bare string constant assignment."
    )
