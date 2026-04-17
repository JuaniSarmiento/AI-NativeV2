"""Unit tests for EPIC-20 Phase C — CoherenceEngine and integration.

Pure Python — no DB, no async. CoherenceEngine is infrastructure-free.
"""
from __future__ import annotations

import types
import uuid
from decimal import Decimal
from pathlib import Path

from app.features.evaluation.coherence import CoherenceEngine, CoherenceResult
from app.features.evaluation.rubric import load_rubric


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(event_type: str, seq: int, payload: dict | None = None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        event_type=event_type,
        sequence_number=seq,
        payload=payload or {},
    )


def _chat_msg(content: str, role: str = "user") -> types.SimpleNamespace:
    return types.SimpleNamespace(content=content, role=role)


def _snap(snapshot_id: str, code: str, diff: str | None = None) -> dict:
    from datetime import datetime, timezone
    return {
        "snapshot_id": snapshot_id,
        "code": code,
        "snapshot_at": datetime.now(tz=timezone.utc),
        "previous_snapshot_id": None,
        "previous_snapshot_at": None,
        "diff_unified": diff,
    }


# ---------------------------------------------------------------------------
# 1. Temporal coherence — no anomalies → 100
# ---------------------------------------------------------------------------

def test_temporal_coherence_no_anomalies() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("reads_problem", seq=1),
        _evt("code.run", seq=2, payload={"status": "ok"}),
        _evt("submission.created", seq=3),
    ]
    result = engine.compute(events, [], [])
    assert result.temporal_coherence_score == Decimal("100.00")
    assert result.coherence_anomalies["anomalies"] == []


# ---------------------------------------------------------------------------
# 2. Temporal coherence — solution_without_comprehension
# ---------------------------------------------------------------------------

def test_temporal_solution_without_comprehension() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("code.run", seq=1, payload={"status": "ok"}),
        _evt("submission.created", seq=2),
    ]
    result = engine.compute(events, [], [])
    assert "solution_without_comprehension" in result.coherence_anomalies["anomalies"]
    assert result.temporal_coherence_score <= Decimal("75.00")


# ---------------------------------------------------------------------------
# 3. Temporal coherence — pure_delegation (>60% generative)
# ---------------------------------------------------------------------------

def test_temporal_pure_delegation() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("reads_problem", seq=1),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.question_asked", seq=3, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.question_asked", seq=4, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.question_asked", seq=5, payload={"prompt_type": "exploratory", "n4_level": 4}),
        _evt("submission.created", seq=6),
    ]
    result = engine.compute(events, [], [])
    assert "pure_delegation" in result.coherence_anomalies["anomalies"]
    assert result.temporal_coherence_score <= Decimal("75.00")


# ---------------------------------------------------------------------------
# 4. Temporal coherence — n4_without_n1
# ---------------------------------------------------------------------------

def test_temporal_n4_without_n1() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "exploratory", "n4_level": 4}),
        _evt("tutor.response_received", seq=2),
        _evt("submission.created", seq=3),
    ]
    result = engine.compute(events, [], [])
    assert "n4_without_n1" in result.coherence_anomalies["anomalies"]


# ---------------------------------------------------------------------------
# 5. Temporal coherence — all three anomalies stacked
# ---------------------------------------------------------------------------

def test_temporal_all_anomalies_stacked() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "generative", "n4_level": 4}),
        _evt("submission.created", seq=3),
    ]
    result = engine.compute(events, [], [])
    anomalies = result.coherence_anomalies["anomalies"]
    assert "solution_without_comprehension" in anomalies
    assert "pure_delegation" in anomalies
    assert "n4_without_n1" in anomalies
    assert result.temporal_coherence_score == Decimal("25.00")


# ---------------------------------------------------------------------------
# 6. Code-discourse coherence — overlapping keywords
# ---------------------------------------------------------------------------

def test_code_discourse_with_overlap() -> None:
    engine = CoherenceEngine(load_rubric())
    chat = [
        _chat_msg("estoy usando una función recursiva para fibonacci"),
    ]
    snaps = [
        _snap("s1", "def fib(n): pass", None),
        _snap("s2", "def fibonacci(n):\n  return n", "+def fibonacci(n):\n+  return n"),
    ]
    result = engine.compute([], chat, snaps)
    assert result.code_discourse_score is not None
    assert result.code_discourse_score > Decimal("0.00")


# ---------------------------------------------------------------------------
# 7. Code-discourse coherence — no chat → None
# ---------------------------------------------------------------------------

def test_code_discourse_no_chat_returns_none() -> None:
    engine = CoherenceEngine(load_rubric())
    snaps = [_snap("s1", "code", "+line")]
    result = engine.compute([], [], snaps)
    assert result.code_discourse_score is None


# ---------------------------------------------------------------------------
# 8. Code-discourse coherence — no diffs → None
# ---------------------------------------------------------------------------

def test_code_discourse_no_diffs_returns_none() -> None:
    engine = CoherenceEngine(load_rubric())
    chat = [_chat_msg("hola mundo")]
    snaps = [_snap("s1", "code", None)]
    result = engine.compute([], chat, snaps)
    assert result.code_discourse_score is None


# ---------------------------------------------------------------------------
# 9. Inter-iteration — no large diffs → 100
# ---------------------------------------------------------------------------

def test_inter_iteration_no_large_diffs() -> None:
    engine = CoherenceEngine(load_rubric())
    small_diff = "\n".join([f"+line{i}" for i in range(10)])
    snaps = [
        _snap("s1", "code", None),
        _snap("s2", "more code", small_diff),
    ]
    result = engine.compute([], [], snaps)
    assert result.inter_iteration_score == Decimal("100.00")


# ---------------------------------------------------------------------------
# 10. Inter-iteration — large diff → uncritical_integration anomaly
# ---------------------------------------------------------------------------

def test_inter_iteration_large_diff_anomaly() -> None:
    engine = CoherenceEngine(load_rubric())
    large_diff = "\n".join([f"+line{i}" for i in range(60)])
    snaps = [
        _snap("s1", "code", None),
        _snap("s2", "lots of code", large_diff),
    ]
    result = engine.compute([], [], snaps)
    assert "uncritical_integration" in result.coherence_anomalies["anomalies"]
    assert result.inter_iteration_score <= Decimal("70.00")


# ---------------------------------------------------------------------------
# 11. Inter-iteration — no snapshots → None
# ---------------------------------------------------------------------------

def test_inter_iteration_no_snapshots() -> None:
    engine = CoherenceEngine(load_rubric())
    result = engine.compute([], [], [])
    assert result.inter_iteration_score is None


# ---------------------------------------------------------------------------
# 12. Prompt type distribution
# ---------------------------------------------------------------------------

def test_prompt_type_distribution() -> None:
    engine = CoherenceEngine(load_rubric())
    events = [
        _evt("tutor.question_asked", seq=1, payload={"prompt_type": "exploratory"}),
        _evt("tutor.question_asked", seq=2, payload={"prompt_type": "verifier"}),
        _evt("tutor.question_asked", seq=3, payload={"prompt_type": "generative"}),
        _evt("tutor.question_asked", seq=4, payload={"prompt_type": "exploratory"}),
        _evt("reads_problem", seq=5),
    ]
    result = engine.compute(events, [], [])
    dist = result.prompt_type_distribution
    assert dist["exploratory"] == 2
    assert dist["verifier"] == 1
    assert dist["generative"] == 1


# ---------------------------------------------------------------------------
# 13. Model has 5 new columns
# ---------------------------------------------------------------------------

def test_cognitive_metrics_model_has_coherence_columns() -> None:
    from app.features.evaluation.models import CognitiveMetrics
    for col_name in (
        "temporal_coherence_score",
        "code_discourse_score",
        "inter_iteration_score",
        "coherence_anomalies",
        "prompt_type_distribution",
    ):
        assert hasattr(CognitiveMetrics, col_name), f"CognitiveMetrics missing column: {col_name}"


# ---------------------------------------------------------------------------
# 14. Schema includes coherence fields
# ---------------------------------------------------------------------------

def test_schema_includes_coherence_fields() -> None:
    from app.features.evaluation.schemas import CognitiveMetricsResponse
    fields = CognitiveMetricsResponse.model_fields
    for f in (
        "temporal_coherence_score",
        "code_discourse_score",
        "inter_iteration_score",
        "coherence_anomalies",
        "prompt_type_distribution",
    ):
        assert f in fields, f"CognitiveMetricsResponse missing field: {f}"


# ---------------------------------------------------------------------------
# 15. Integration in close_session source
# ---------------------------------------------------------------------------

def test_close_session_calls_coherence_engine() -> None:
    service_path = (
        Path(__file__).resolve().parents[2]
        / "app" / "features" / "cognitive" / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")
    assert "CoherenceEngine" in source
    assert "temporal_coherence_score" in source
    assert "code_discourse_score" in source
    assert "inter_iteration_score" in source
    assert "coherence_anomalies" in source
    assert "prompt_type_distribution" in source


# ---------------------------------------------------------------------------
# 16. Migration file exists
# ---------------------------------------------------------------------------

def test_migration_015_exists() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic" / "versions" / "015_add_coherence_columns.py"
    )
    assert migration_path.exists(), "Alembic migration 015 not found"
    source = migration_path.read_text(encoding="utf-8")
    assert "temporal_coherence_score" in source
    assert 'schema="cognitive"' in source


# ---------------------------------------------------------------------------
# 17. Empty events → graceful Nones
# ---------------------------------------------------------------------------

def test_coherence_empty_events_graceful() -> None:
    engine = CoherenceEngine(load_rubric())
    result = engine.compute([], [], [])
    assert result.temporal_coherence_score is None
    assert result.code_discourse_score is None
    assert result.inter_iteration_score is None
    assert result.coherence_anomalies["anomalies"] == []
    assert result.prompt_type_distribution == {"exploratory": 0, "verifier": 0, "generative": 0}
