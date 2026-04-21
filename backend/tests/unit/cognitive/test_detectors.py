"""Unit tests for synthetic event detectors (pseudocode, manual test, tutor acceptance)."""
from __future__ import annotations

import pytest

from app.features.cognitive.detectors import (
    ManualTestCaseDetector,
    PseudocodeDetector,
    TutorCodeAcceptanceDetector,
)


# ---------------------------------------------------------------------------
# PseudocodeDetector
# ---------------------------------------------------------------------------


class TestPseudocodeDetector:
    def setup_method(self) -> None:
        self.detector = PseudocodeDetector()

    def test_detects_consecutive_control_flow_comments(self) -> None:
        code = """# if the number is positive
# then add to sum
# else skip it
# return the sum
x = 0
"""
        result = self.detector.detect({"code": code})
        assert result is not None
        assert result.event_type == "pseudocode.written"
        assert result.payload["consecutive_control_flow_comments"] >= 3

    def test_detects_high_comment_ratio(self) -> None:
        code = """# step 1: read input
# step 2: validate
# step 3: compute
# step 4: output
x = 1
"""
        result = self.detector.detect({"code": code})
        assert result is not None
        assert result.payload["comment_ratio"] > 0.5

    def test_ignores_normal_code_with_few_comments(self) -> None:
        code = """x = int(input())
y = x * 2
# print result
print(y)
"""
        result = self.detector.detect({"code": code})
        assert result is None

    def test_ignores_empty_code(self) -> None:
        result = self.detector.detect({"code": ""})
        assert result is None

    def test_ignores_missing_code_field(self) -> None:
        result = self.detector.detect({})
        assert result is None

    def test_python_hash_comments(self) -> None:
        code = """# while there are elements
# for each element check if prime
# if prime add to list
result = []
"""
        result = self.detector.detect({"code": code})
        assert result is not None

    def test_js_slash_comments(self) -> None:
        code = """// if user is logged in
// then redirect to dashboard
// else show login form
const x = 1;
"""
        result = self.detector.detect({"code": code})
        assert result is not None


# ---------------------------------------------------------------------------
# ManualTestCaseDetector
# ---------------------------------------------------------------------------


class TestManualTestCaseDetector:
    def setup_method(self) -> None:
        self.detector = ManualTestCaseDetector()

    def test_detects_assert_statements(self) -> None:
        code = """def suma(a, b):
    return a + b

assert suma(1, 2) == 3
assert suma(0, 0) == 0
assert suma(-1, 1) == 0
"""
        result = self.detector.detect({"code": code})
        assert result is not None
        assert result.event_type == "test.manual_case"
        assert result.payload["assert_count"] >= 2

    def test_detects_print_test_patterns(self) -> None:
        code = """def factorial(n):
    if n <= 1: return 1
    return n * factorial(n-1)

print(factorial(5) == 120)
print(factorial(0) == 1)
"""
        result = self.detector.detect({"code": code})
        assert result is not None
        assert result.payload["print_test_count"] >= 2

    def test_detects_edge_case_with_boundary_values(self) -> None:
        code = """assert func(0) == 0
assert func(-1) == -1
assert func(999999) > 0
"""
        result = self.detector.detect({"code": code})
        assert result is not None
        assert result.payload["is_edge_case"] is True

    def test_ignores_single_assert(self) -> None:
        code = """x = 5
assert x == 5
print("done")
"""
        result = self.detector.detect({"code": code})
        assert result is None

    def test_filters_exercise_examples(self) -> None:
        code = """assert suma(2, 3) == 5
assert suma(1, 1) == 2
"""
        result = self.detector.detect({
            "code": code,
            "exercise_examples": ["2", "3", "5", "1", "2"],
        })
        # Should filter out asserts using only example values
        assert result is None

    def test_ignores_empty_code(self) -> None:
        result = self.detector.detect({"code": ""})
        assert result is None


# ---------------------------------------------------------------------------
# TutorCodeAcceptanceDetector
# ---------------------------------------------------------------------------


class TestTutorCodeAcceptanceDetector:
    def setup_method(self) -> None:
        self.detector = TutorCodeAcceptanceDetector()

    def test_detects_high_similarity_with_tutor_code(self) -> None:
        tutor_code = "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"
        snapshot_code = "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"

        result = self.detector.detect(
            payload={"code": snapshot_code, "timestamp": "2026-04-20T10:00:30+00:00"},
            recent_tutor_responses=[
                {"content": f"Podrias usar recursion:\n```python\n{tutor_code}\n```", "id": "msg-1", "timestamp": "2026-04-20T10:00:00+00:00"},
            ],
            recent_events=[],
        )
        assert result is not None
        assert result.event_type == "code.accepted_from_tutor"
        assert result.payload["similarity_ratio"] > 0.6
        assert result.payload["detection_method"] == "lcs_similarity"

    def test_suppressed_by_clipboard_event(self) -> None:
        tutor_code = "def hello():\n    print('world')"
        snapshot_code = "def hello():\n    print('world')"

        result = self.detector.detect(
            payload={"code": snapshot_code, "timestamp": "2026-04-20T10:00:30+00:00"},
            recent_tutor_responses=[
                {"content": f"```python\n{tutor_code}\n```", "id": "msg-1"},
            ],
            recent_events=[
                {"event_type": "clipboard.copy", "timestamp": "2026-04-20T10:00:15+00:00"},
            ],
        )
        assert result is None

    def test_low_similarity_not_detected(self) -> None:
        result = self.detector.detect(
            payload={"code": "x = 1\ny = 2\nprint(x + y)", "timestamp": "2026-04-20T10:00:30+00:00"},
            recent_tutor_responses=[
                {"content": "```python\ndef complex_function(a, b, c):\n    return a * b + c\n```", "id": "msg-1"},
            ],
            recent_events=[],
        )
        assert result is None

    def test_too_short_code_ignored(self) -> None:
        result = self.detector.detect(
            payload={"code": "x=1", "timestamp": "2026-04-20T10:00:30+00:00"},
            recent_tutor_responses=[
                {"content": "```python\nx=1\n```", "id": "msg-1"},
            ],
            recent_events=[],
        )
        assert result is None

    def test_prefers_diff_over_full_code(self) -> None:
        tutor_code = "result = sum(range(10))"
        result = self.detector.detect(
            payload={
                "code": "x = 1\nresult = sum(range(10))\nprint(result)",
                "diff": "result = sum(range(10))",
                "timestamp": "2026-04-20T10:00:30+00:00",
            },
            recent_tutor_responses=[
                {"content": f"```python\n{tutor_code}\n```", "id": "msg-1"},
            ],
            recent_events=[],
        )
        assert result is not None
