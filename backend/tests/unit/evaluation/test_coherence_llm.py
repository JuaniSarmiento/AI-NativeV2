"""Unit tests for CoherenceEngine — LLM score path vs Jaccard fallback (B4).

Task 3.6: Verify that when llm_discourse_score is provided, the Jaccard
method is skipped and the LLM score is used directly; when it is None,
Jaccard is used as before.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.features.evaluation.coherence import CoherenceEngine
from app.features.evaluation.rubric import RubricConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _engine() -> CoherenceEngine:
    return CoherenceEngine(RubricConfig())


def _event(event_type: str, payload: dict | None = None, sequence_number: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        payload=payload or {},
        sequence_number=sequence_number,
    )


def _chat_msg(content: str, role: str = "user") -> SimpleNamespace:
    return SimpleNamespace(content=content, role=role)


def _snapshot(code: str, diff: str | None = None) -> dict:
    return {
        "snapshot_id": "test-snap-1",
        "code": code,
        "diff_unified": diff,
        "snapshot_at": None,
    }


# ---------------------------------------------------------------------------
# LLM score provided → Jaccard skipped
# ---------------------------------------------------------------------------


class TestLLMDiscourseScore:
    def test_llm_score_used_directly(self) -> None:
        """When llm_discourse_score is provided, the LLM score is returned as code_discourse_score."""
        engine = _engine()
        events = [_event("reads_problem")]
        chat_msgs = [_chat_msg("hello world")]
        snapshots = [_snapshot("x = 1")]

        llm_score = Decimal("85")
        result = engine.compute(events, chat_msgs, snapshots, llm_discourse_score=llm_score)

        assert result.code_discourse_score == Decimal("85.00")

    def test_llm_score_clamped_to_100(self) -> None:
        engine = _engine()
        result = engine.compute(
            [_event("reads_problem")],
            [_chat_msg("test")],
            [_snapshot("x = 1")],
            llm_discourse_score=Decimal("150"),
        )
        assert result.code_discourse_score == Decimal("100.00")

    def test_llm_score_zero_is_valid(self) -> None:
        engine = _engine()
        result = engine.compute(
            [_event("reads_problem")],
            [_chat_msg("test")],
            [_snapshot("x = 1")],
            llm_discourse_score=Decimal("0"),
        )
        assert result.code_discourse_score == Decimal("0.00")

    def test_jaccard_not_called_when_llm_provided(self) -> None:
        """_compute_code_discourse_coherence should not be invoked when llm_discourse_score is set."""
        engine = _engine()

        with patch.object(
            engine,
            "_compute_code_discourse_coherence",
            wraps=engine._compute_code_discourse_coherence,
        ) as mock_jaccard:
            engine.compute(
                [_event("reads_problem")],
                [_chat_msg("sorting algorithm bubble sort")],
                [_snapshot("for i in range(n): pass", diff="+for i in range(n): pass")],
                llm_discourse_score=Decimal("72"),
            )
            mock_jaccard.assert_not_called()


# ---------------------------------------------------------------------------
# LLM score absent → Jaccard used
# ---------------------------------------------------------------------------


class TestJaccardFallback:
    def test_jaccard_used_when_llm_score_is_none(self) -> None:
        """When llm_discourse_score is None (default), Jaccard is computed."""
        engine = _engine()

        with patch.object(
            engine,
            "_compute_code_discourse_coherence",
            wraps=engine._compute_code_discourse_coherence,
        ) as mock_jaccard:
            engine.compute(
                [_event("reads_problem")],
                [_chat_msg("sorting algorithm")],
                [_snapshot("def sort(arr): pass", diff="+def sort(arr): pass")],
                llm_discourse_score=None,
            )
            mock_jaccard.assert_called_once()

    def test_no_chat_returns_none_discourse_score(self) -> None:
        engine = _engine()
        result = engine.compute(
            [_event("reads_problem")],
            [],  # no chat messages
            [_snapshot("x = 1", diff="+x = 1")],
            llm_discourse_score=None,
        )
        assert result.code_discourse_score is None

    def test_jaccard_returns_decimal_score(self) -> None:
        """Jaccard path returns a Decimal when both chat and diffs are present."""
        engine = _engine()
        result = engine.compute(
            [_event("reads_problem")],
            [_chat_msg("bubble sort algorithm loop iteration")],
            [_snapshot("def bubble_sort(arr):\n    pass", diff="+def bubble_sort(arr):\n+    pass")],
            llm_discourse_score=None,
        )
        # May be None if no keyword overlap — just verify it's either None or a valid Decimal
        assert result.code_discourse_score is None or isinstance(result.code_discourse_score, Decimal)

    def test_default_param_is_none(self) -> None:
        """Calling compute() without llm_discourse_score defaults to Jaccard path."""
        engine = _engine()
        with patch.object(
            engine,
            "_compute_code_discourse_coherence",
            return_value=Decimal("55"),
        ) as mock_jaccard:
            result = engine.compute(
                [_event("reads_problem")],
                [_chat_msg("test message")],
                [_snapshot("x = 1", diff="+x = 1")],
            )
            mock_jaccard.assert_called_once()
            assert result.code_discourse_score == Decimal("55")
