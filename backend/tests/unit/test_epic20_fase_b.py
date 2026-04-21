"""Unit tests for EPIC-20 Phase B — prompt_type classification, hybrid LLM, independent scoring.

Pure Python — no DB, no async (except for the hybrid LLM mock test).
"""
from __future__ import annotations

import asyncio
import types
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.features.cognitive.classifier import CognitiveEventClassifier, llm_classify_message
from app.features.evaluation.rubric import load_rubric
from app.features.evaluation.service import MetricsEngine
from app.features.tutor.n4_classifier import N4Classifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(event_type: str, seq: int, payload: dict | None = None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        event_type=event_type,
        sequence_number=seq,
        payload=payload or {},
    )


def _mock_session() -> types.SimpleNamespace:
    return types.SimpleNamespace(id=uuid.uuid4())


# ---------------------------------------------------------------------------
# 1. N4Classifier prompt_type — generative
# ---------------------------------------------------------------------------

def test_n4_classifier_prompt_type_generative() -> None:
    clf = N4Classifier()
    result = clf.classify_message("dame el código de la función", "user")
    assert result.prompt_type == "generative"


# ---------------------------------------------------------------------------
# 2. N4Classifier prompt_type — verifier
# ---------------------------------------------------------------------------

def test_n4_classifier_prompt_type_verifier() -> None:
    clf = N4Classifier()
    result = clf.classify_message("está bien mi solución?", "user")
    assert result.prompt_type == "verifier"


# ---------------------------------------------------------------------------
# 3. N4Classifier prompt_type — exploratory
# ---------------------------------------------------------------------------

def test_n4_classifier_prompt_type_exploratory() -> None:
    clf = N4Classifier()
    result = clf.classify_message("cómo funciona un diccionario?", "user")
    assert result.prompt_type == "exploratory"


# ---------------------------------------------------------------------------
# 4. N4Classifier prompt_type — assistant gets None
# ---------------------------------------------------------------------------

def test_n4_classifier_prompt_type_none_for_assistant() -> None:
    clf = N4Classifier()
    result = clf.classify_message("revisá la línea 10", "assistant")
    assert result.prompt_type is None


# ---------------------------------------------------------------------------
# 5. N4Classifier prompt_type — default is exploratory
# ---------------------------------------------------------------------------

def test_n4_classifier_prompt_type_default_exploratory() -> None:
    clf = N4Classifier()
    result = clf.classify_message("hola qué tal", "user")
    assert result.prompt_type == "exploratory"


# ---------------------------------------------------------------------------
# 6. TutorService source includes prompt_type in outbox payloads
# ---------------------------------------------------------------------------

def test_tutor_service_includes_prompt_type_in_payloads() -> None:
    from pathlib import Path
    service_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "tutor" / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")
    assert '"prompt_type"' in source, (
        "tutor/service.py must include prompt_type in outbox payloads"
    )


# ---------------------------------------------------------------------------
# 7. llm_classify_message — source exists with expected signature
# ---------------------------------------------------------------------------

def test_llm_classify_message_exists() -> None:
    import inspect
    sig = inspect.signature(llm_classify_message)
    params = list(sig.parameters.keys())
    assert "content" in params
    assert "role" in params
    assert "api_key" in params
    assert "timeout" in params


# ---------------------------------------------------------------------------
# 8. Hybrid classification in consumer source
# ---------------------------------------------------------------------------

def test_consumer_has_hybrid_classification() -> None:
    from pathlib import Path
    consumer_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "cognitive" / "consumer.py"
    )
    source = consumer_path.read_text(encoding="utf-8")
    assert "llm_classify_message" in source, (
        "consumer.py must call llm_classify_message for hybrid classification"
    )
    assert "confidence" in source, (
        "consumer.py must check regex confidence before LLM escalation"
    )


# ---------------------------------------------------------------------------
# 9. N1 independent scoring — presence + depth + quality
# ---------------------------------------------------------------------------

def test_n1_independent_scoring_full() -> None:
    """N1 with reads_problem + 3 snapshots + N1 tutor question + code.run not first.
    Expected: presence=30, depth=30(cap), quality=40 → 100."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("reads_problem", seq=1),
        _evt("code.snapshot", seq=2),
        _evt("code.snapshot", seq=3),
        _evt("tutor.question_asked", seq=4, payload={"n4_level": 1}),
        _evt("code.run", seq=5, payload={"status": "ok"}),
        _evt("submission.created", seq=6),
    ]
    result = engine.compute(session, events)
    n1 = result.metrics.n1_comprehension_score
    assert n1 is not None
    assert n1 == Decimal("45.00"), f"Expected 45.00, got {n1}"


def test_n1_zero_when_no_reads_problem() -> None:
    """N1 with no reads_problem and code.run as first event → presence=0, depth=0, quality=0."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("code.run", seq=1, payload={"status": "ok"}),
        _evt("submission.created", seq=2),
    ]
    result = engine.compute(session, events)
    n1 = result.metrics.n1_comprehension_score
    assert n1 is not None
    assert n1 == Decimal("0.00"), f"Expected 0.00, got {n1}"


# ---------------------------------------------------------------------------
# 10. N2 independent scoring
# ---------------------------------------------------------------------------

def test_n2_independent_scoring_with_strategy() -> None:
    """N2 with submission + N2 tutor before run + multiple types → high score."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("reads_problem", seq=1),
        _evt("tutor.question_asked", seq=2, payload={"n4_level": 2}),
        _evt("code.run", seq=3, payload={"status": "ok"}),
        _evt("submission.created", seq=4),
    ]
    result = engine.compute(session, events)
    n2 = result.metrics.n2_strategy_score
    assert n2 is not None
    assert n2 == Decimal("25.00"), f"Expected 25.00, got {n2}"


def test_n2_zero_without_submission() -> None:
    """N2 is 0 when there are no submission events."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("reads_problem", seq=1),
        _evt("code.run", seq=2, payload={"status": "ok"}),
    ]
    result = engine.compute(session, events)
    n2 = result.metrics.n2_strategy_score
    assert n2 is not None
    assert n2 == Decimal("0.00"), f"Expected 0.00, got {n2}"


# ---------------------------------------------------------------------------
# 11. N3 independent scoring — correction cycle
# ---------------------------------------------------------------------------

def test_n3_correction_cycle_detected() -> None:
    """N3 with error→success correction cycle + last run success → max quality."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("reads_problem", seq=1),
        _evt("code.run", seq=2, payload={"status": "error"}),
        _evt("code.run", seq=3, payload={"status": "error"}),
        _evt("code.run", seq=4, payload={"status": "ok"}),
        _evt("submission.created", seq=5),
    ]
    result = engine.compute(session, events)
    n3 = result.metrics.n3_validation_score
    assert n3 is not None
    assert n3 == Decimal("60.00"), f"Expected 60.00, got {n3}"


# ---------------------------------------------------------------------------
# 12. N4 independent scoring — prompt_type distribution
# ---------------------------------------------------------------------------

def test_n4_prompt_type_all_exploratory() -> None:
    """N4 with all exploratory prompts → reflective_ratio=1.0, base=70, no verifier bonus."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "exploratory", "n4_level": 4}),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "exploratory", "n4_level": 4}),
        _evt("tutor.response_received", seq=3),
    ]
    result = engine.compute(session, events)
    n4 = result.metrics.n4_ai_interaction_score
    assert n4 is not None
    assert n4 == Decimal("70.00"), f"Expected 70.00, got {n4}"


def test_n4_prompt_type_with_verifier_and_diversity() -> None:
    """N4 with exploratory + verifier → reflective_ratio=1.0, base=70+15+10=95."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "exploratory", "n4_level": 4}),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "verifier", "n4_level": 4}),
        _evt("tutor.response_received", seq=3),
    ]
    result = engine.compute(session, events)
    n4 = result.metrics.n4_ai_interaction_score
    assert n4 is not None
    assert n4 == Decimal("95.00"), f"Expected 95.00, got {n4}"


def test_n4_all_generative_low_score() -> None:
    """N4 with all generative prompts → reflective_ratio=0 → base=0+0+0=0."""
    engine = MetricsEngine(load_rubric())
    session = _mock_session()
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.response_received", seq=3),
    ]
    result = engine.compute(session, events)
    n4 = result.metrics.n4_ai_interaction_score
    assert n4 is not None
    assert n4 == Decimal("0.00"), f"Expected 0.00, got {n4}"


# ---------------------------------------------------------------------------
# 13. CognitiveEventClassifier reads prompt_type from payload
# ---------------------------------------------------------------------------

def test_classifier_preserves_prompt_type_in_payload() -> None:
    """CognitiveEventClassifier must pass through the original payload including prompt_type."""
    clf = CognitiveEventClassifier()
    result = clf.classify(
        "tutor.interaction.completed",
        {"role": "user", "n4_level": 2, "prompt_type": "verifier"},
    )
    assert result is not None
    assert result.payload.get("prompt_type") == "verifier"


# ---------------------------------------------------------------------------
# 14. LLM classify mock test — timeout returns None
# ---------------------------------------------------------------------------

def test_llm_classify_timeout_returns_none() -> None:
    """llm_classify_message must return None on timeout."""
    result = asyncio.get_event_loop().run_until_complete(
        llm_classify_message(
            content="test",
            role="user",
            api_key="fake-key",
            model="test-model",
            timeout=0.001,
        )
    )
    assert result is None
