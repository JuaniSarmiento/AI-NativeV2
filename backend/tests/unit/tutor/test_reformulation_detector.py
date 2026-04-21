"""Unit tests for prompt reformulation TF-IDF detection."""
from __future__ import annotations

import pytest

from app.features.tutor.reformulation_detector import ReformulationDetector


class TestReformulationDetector:
    def setup_method(self) -> None:
        self.detector = ReformulationDetector()

    def test_detects_reformulation_of_similar_message(self) -> None:
        current = "como puedo resolver este problema usando recursion necesito entender como funciona el caso base y como se reduce el problema"
        recent = [
            {
                "content": "como puedo resolver este problema usando recursion",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "interaction_id": "msg-1",
            },
        ]
        result = self.detector.detect(
            current, "2026-04-20T10:01:00+00:00", recent
        )
        assert result is not None
        assert result["similarity_score"] > 0.4
        assert result["detection_method"] == "tfidf_cosine"

    def test_does_not_detect_unrelated_messages(self) -> None:
        current = "Que es una variable en Python?"
        recent = [
            {
                "content": "Como funciona la herencia en Java?",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "interaction_id": "msg-1",
            },
        ]
        result = self.detector.detect(
            current, "2026-04-20T10:01:00+00:00", recent
        )
        assert result is None

    def test_respects_time_window(self) -> None:
        current = "Como resuelvo este problema con recursion de forma eficiente?"
        recent = [
            {
                "content": "Como resuelvo esto con recursion?",
                "timestamp": "2026-04-20T09:50:00+00:00",  # 11 minutes ago
                "interaction_id": "msg-1",
            },
        ]
        result = self.detector.detect(
            current, "2026-04-20T10:01:00+00:00", recent
        )
        assert result is None

    def test_requires_current_to_be_longer_or_equal(self) -> None:
        # Shorter reformulation should not trigger
        current = "recursion?"
        recent = [
            {
                "content": "Como puedo resolver este ejercicio usando el concepto de recursion en programacion?",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "interaction_id": "msg-1",
            },
        ]
        result = self.detector.detect(
            current, "2026-04-20T10:01:00+00:00", recent
        )
        assert result is None

    def test_ignores_very_short_messages(self) -> None:
        result = self.detector.detect(
            "hola", "2026-04-20T10:01:00+00:00",
            [{"content": "hola que tal", "timestamp": "2026-04-20T10:00:00+00:00"}],
        )
        assert result is None

    def test_returns_none_for_empty_recent(self) -> None:
        result = self.detector.detect(
            "Como resuelvo esto?", "2026-04-20T10:01:00+00:00", []
        )
        assert result is None
