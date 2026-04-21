from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Control-flow keywords that are meaningful inside comments to identify
# pseudocode intent.  Kept as a frozenset for O(1) membership tests.
# ---------------------------------------------------------------------------
_CONTROL_FLOW_KEYWORDS: frozenset[str] = frozenset(
    {
        "if",
        "else",
        "while",
        "for",
        "then",
        "return",
        "loop",
        "repeat",
        "until",
        "when",
        "check",
        "verify",
        "iterate",
        "process",
    }
)

# Values that are considered "edge case" / boundary test inputs.
_BOUNDARY_SCALARS: frozenset[str] = frozenset(
    {"0", "-1", "none", "true", "false", '""', "''", "[]", "{}"}
)
_BOUNDARY_LARGE_NUMBER = 999_999

# LCS similarity threshold above which we flag tutor code acceptance.
_LCS_SIMILARITY_THRESHOLD = 0.6

# Seconds window used to check for a preceding clipboard event that would
# explain why the student's snapshot looks like the tutor's code.
_CLIPBOARD_WINDOW_SECONDS = 30


# ---------------------------------------------------------------------------
# Public data contract
# ---------------------------------------------------------------------------


@dataclass
class SyntheticEvent:
    """A synthetic cognitive event emitted by a detector.

    The consumer is responsible for routing this through
    CognitiveService.add_event() so it enters the CTR with proper
    classification and hash-chaining.
    """

    event_type: str
    payload: dict[str, Any]


# ---------------------------------------------------------------------------
# 1. PseudocodeDetector
# ---------------------------------------------------------------------------


class PseudocodeDetector:
    """Detects pseudocode written as comment blocks inside code.snapshot events.

    Triggers when the student's snapshot contains either:
    - 3+ consecutive comment lines that include a control-flow keyword, OR
    - More than 50 % of non-empty lines are comments.

    Pure Python, no async, no DB access.
    """

    # Comment-start markers we recognise (single-line style).
    _SINGLE_LINE_COMMENT_STARTS = ("#", "//", "/*")

    def detect(self, payload: dict[str, Any]) -> SyntheticEvent | None:
        """Analyse a code.snapshot payload.

        Args:
            payload: The raw event payload dict.  Must contain a ``code``
                     string field to be analysed.

        Returns:
            A SyntheticEvent with event_type ``pseudocode.written`` if
            pseudocode is detected, otherwise ``None``.
        """
        code: str = payload.get("code", "")
        if not code or not isinstance(code, str):
            return None

        lines = code.splitlines()
        comment_lines, total_non_empty, consecutive_cf = self._analyse_lines(lines)

        detected = False
        if total_non_empty > 0:
            comment_ratio = comment_lines / total_non_empty
            if consecutive_cf >= 3 or comment_ratio > 0.5:
                detected = True
        else:
            comment_ratio = 0.0

        if not detected:
            return None

        return SyntheticEvent(
            event_type="pseudocode.written",
            payload={
                "detected_from": "code.snapshot",
                "comment_lines": comment_lines,
                "total_lines": total_non_empty,
                "consecutive_control_flow_comments": consecutive_cf,
                "comment_ratio": round(comment_ratio, 4),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyse_lines(
        self, lines: list[str]
    ) -> tuple[int, int, int]:
        """Return (comment_line_count, non_empty_line_count, max_consecutive_cf_comments).

        Handles block comments (``/* … */``) by tracking whether we are
        currently inside an open ``/*`` block.
        """
        comment_lines = 0
        total_non_empty = 0
        current_consecutive_cf = 0
        max_consecutive_cf = 0
        inside_block_comment = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                # Empty lines break consecutive-comment runs.
                current_consecutive_cf = 0
                continue

            total_non_empty += 1

            is_comment, inside_block_comment = self._is_comment_line(
                line, inside_block_comment
            )

            if is_comment:
                comment_lines += 1
                if self._contains_control_flow(line):
                    current_consecutive_cf += 1
                    max_consecutive_cf = max(max_consecutive_cf, current_consecutive_cf)
                else:
                    current_consecutive_cf = 0
            else:
                current_consecutive_cf = 0

        return comment_lines, total_non_empty, max_consecutive_cf

    def _is_comment_line(
        self, line: str, inside_block: bool
    ) -> tuple[bool, bool]:
        """Return (is_comment, updated_inside_block)."""
        # Already inside a block comment — check for close.
        if inside_block:
            if "*/" in line:
                return True, False  # Closing line, still a comment.
            return True, True

        # Opening a new block comment on this line.
        if line.startswith("/*"):
            if "*/" in line[2:]:
                return True, False  # Inline /* … */ — closed on same line.
            return True, True

        # Single-line comment styles.
        if any(line.startswith(m) for m in self._SINGLE_LINE_COMMENT_STARTS):
            return True, False

        return False, False

    @staticmethod
    def _contains_control_flow(line: str) -> bool:
        """Return True if any word in the line is a control-flow keyword."""
        # Lowercase and split on any non-word character.
        words = re.split(r"\W+", line.lower())
        return bool(_CONTROL_FLOW_KEYWORDS.intersection(words))


# ---------------------------------------------------------------------------
# 2. ManualTestCaseDetector
# ---------------------------------------------------------------------------


class ManualTestCaseDetector:
    """Detects manual test cases inside code.run events.

    A manual test case is identified by the presence of:
    - ``assert`` statements whose values differ from provided exercise examples.
    - ``print()`` calls that contain comparison operators or test-like patterns.

    If 2+ such lines are found the event is emitted.

    Pure Python, no async, no DB access.
    """

    # Matches a bare assert with some expression.
    _ASSERT_RE = re.compile(r"^\s*assert\b", re.IGNORECASE)

    # A print() call that looks like it is testing: either contains ==, !=, >=,
    # <= comparisons, or calls a function with a literal argument.
    _PRINT_TEST_RE = re.compile(
        r"""print\s*\(          # print(
            .*?                  # any content
            (?:
                [!=<>]{1,2}      # comparison operator
                |                # OR
                \w+\s*\([^)]*\)  # function call inside
            )
            .*?\)                # closing paren
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def detect(self, payload: dict[str, Any]) -> SyntheticEvent | None:
        """Analyse a code.run payload.

        Args:
            payload: The raw event payload dict.  ``code`` field is required.
                     Optional ``exercise_examples`` is a list of example
                     input/output values to exclude from the assert scan.

        Returns:
            A SyntheticEvent with event_type ``test.manual_case`` if manual
            test patterns are found, otherwise ``None``.
        """
        code: str = payload.get("code", "")
        if not code or not isinstance(code, str):
            return None

        exercise_examples: list[Any] = payload.get("exercise_examples", [])
        example_values: set[str] = {str(e) for e in exercise_examples}

        lines = code.splitlines()
        assert_count = 0
        print_test_count = 0
        is_edge_case = False

        for line in lines:
            stripped = line.strip()

            if self._ASSERT_RE.match(stripped):
                # Skip assertions that only reuse provided example values.
                if not self._line_uses_only_examples(stripped, example_values):
                    assert_count += 1
                    if self._line_has_boundary_value(stripped):
                        is_edge_case = True

            elif self._PRINT_TEST_RE.search(stripped):
                print_test_count += 1
                if self._line_has_boundary_value(stripped):
                    is_edge_case = True

        if assert_count + print_test_count < 2:
            return None

        return SyntheticEvent(
            event_type="test.manual_case",
            payload={
                "detected_from": "code.run",
                "assert_count": assert_count,
                "print_test_count": print_test_count,
                "is_edge_case": is_edge_case,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _line_uses_only_examples(line: str, example_values: set[str]) -> bool:
        """Return True when every literal value in the line is in example_values.

        Only filters when example_values is non-empty, otherwise every assert
        is considered novel.
        """
        if not example_values:
            return False

        # Extract numeric and string literals from the line.
        literals = re.findall(r'"[^"]*"|\'[^\']*\'|\b\d+\b', line)
        if not literals:
            return False

        return all(lit.strip("\"'") in example_values for lit in literals)

    @staticmethod
    def _line_has_boundary_value(line: str) -> bool:
        """Heuristic: return True if the line contains a boundary / edge-case value."""
        line_lower = line.lower()

        # Check symbolic boundary scalars.
        for val in _BOUNDARY_SCALARS:
            # Use word-boundary search to avoid partial matches.
            if re.search(r"(?<!\w)" + re.escape(val) + r"(?!\w)", line_lower):
                return True

        # Check for large integers.
        numbers = re.findall(r"\b\d+\b", line)
        if any(int(n) >= _BOUNDARY_LARGE_NUMBER for n in numbers):
            return True

        return False


# ---------------------------------------------------------------------------
# 3. TutorCodeAcceptanceDetector
# ---------------------------------------------------------------------------


class TutorCodeAcceptanceDetector:
    """Detects when a student copies code from a tutor response without modification.

    Uses Longest Common Subsequence (LCS) at the character level to compare
    the new code snapshot against extracted code blocks from recent tutor
    responses.

    A clipboard event within the preceding 30 seconds is treated as an
    innocent explanation and suppresses the synthetic event.

    Pure Python, no async, no DB access.
    """

    # Regex to extract fenced code blocks (```python ... ```) from tutor messages.
    _FENCED_CODE_RE = re.compile(
        r"```(?:python)?\s*\n(.*?)```",
        re.DOTALL,
    )

    # Regex to extract indented code blocks (4-space or tab indented lines).
    _INDENTED_BLOCK_RE = re.compile(
        r"(?:^(?:    |\t).+$\n?)+",
        re.MULTILINE,
    )

    def detect(
        self,
        payload: dict[str, Any],
        recent_tutor_responses: list[dict[str, Any]],
        recent_events: list[dict[str, Any]],
    ) -> SyntheticEvent | None:
        """Analyse a code.snapshot payload against recent tutor responses.

        Args:
            payload: The raw event payload dict.  Must contain ``code`` (the
                     full snapshot) and optionally ``diff`` (only the changed
                     portion).  The ``timestamp`` ISO-8601 field is used for
                     the clipboard-event window check.
            recent_tutor_responses: List of tutor message dicts, each
                expected to have ``content`` (str) and optionally ``id`` (str)
                and ``timestamp`` (str ISO-8601).
            recent_events: List of recent raw event dicts from the session,
                used to check for preceding clipboard events.  Each dict
                should have ``event_type`` and optionally ``timestamp``.

        Returns:
            A SyntheticEvent with event_type ``code.accepted_from_tutor`` if
            a high-similarity match is found and no clipboard event explains
            it, otherwise ``None``.
        """
        snapshot_text: str = payload.get("diff") or payload.get("code", "")
        if not snapshot_text or not isinstance(snapshot_text, str):
            return None

        snapshot_text = snapshot_text.strip()
        if len(snapshot_text) < 10:
            # Too short to reliably compare.
            return None

        snapshot_ts = self._parse_iso_timestamp(payload.get("timestamp"))

        # Check for a recent clipboard event that would explain the similarity.
        if self._has_recent_clipboard_event(recent_events, snapshot_ts):
            return None

        best_ratio = 0.0
        best_message_id: str | None = None
        best_fragment_len = 0

        for tutor_msg in recent_tutor_responses:
            content: str = tutor_msg.get("content", "")
            if not content or not isinstance(content, str):
                continue

            code_blocks = self._extract_code_blocks(content)
            for block in code_blocks:
                block = block.strip()
                if not block:
                    continue

                ratio = self._lcs_ratio(snapshot_text, block)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_message_id = tutor_msg.get("id") or tutor_msg.get("message_id")
                    best_fragment_len = len(block)

        if best_ratio < _LCS_SIMILARITY_THRESHOLD:
            return None

        return SyntheticEvent(
            event_type="code.accepted_from_tutor",
            payload={
                "detected_from": "code.snapshot",
                "similarity_ratio": round(best_ratio, 4),
                "tutor_message_id": best_message_id,
                "fragment_length": best_fragment_len,
                "detection_method": "lcs_similarity",
            },
        )

    # ------------------------------------------------------------------
    # LCS implementation
    # ------------------------------------------------------------------

    @staticmethod
    def _lcs_ratio(a: str, b: str) -> float:
        """Compute LCS similarity ratio between two strings.

        LCS ratio = len(LCS(a, b)) / max(len(a), len(b))

        Uses the space-optimised two-row DP approach (O(min(|a|,|b|)) space).
        To keep runtime manageable for large inputs, strings are truncated to
        2000 characters before comparison — we care about local structural
        similarity, not full-file equality.
        """
        _MAX = 2000
        a = a[:_MAX]
        b = b[:_MAX]

        if len(a) < len(b):
            a, b = b, a  # Ensure a is the longer string.

        n, m = len(a), len(b)
        if m == 0:
            return 0.0

        previous = [0] * (m + 1)
        current = [0] * (m + 1)

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if a[i - 1] == b[j - 1]:
                    current[j] = previous[j - 1] + 1
                else:
                    current[j] = max(current[j - 1], previous[j])
            previous, current = current, [0] * (m + 1)

        lcs_length = previous[m]
        return lcs_length / max(n, m)

    # ------------------------------------------------------------------
    # Code-block extraction
    # ------------------------------------------------------------------

    def _extract_code_blocks(self, content: str) -> list[str]:
        """Extract code blocks from a tutor response string."""
        blocks: list[str] = []

        # Fenced blocks first (highest confidence).
        fenced = self._FENCED_CODE_RE.findall(content)
        blocks.extend(fenced)

        # If no fenced blocks found, fall back to indented blocks.
        if not blocks:
            indented = self._INDENTED_BLOCK_RE.findall(content)
            blocks.extend(indented)

        return blocks

    # ------------------------------------------------------------------
    # Clipboard / timestamp helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_iso_timestamp(ts: Any) -> datetime | None:
        """Parse an ISO-8601 timestamp string into a timezone-aware datetime."""
        if not ts or not isinstance(ts, str):
            return None
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _has_recent_clipboard_event(
        self,
        recent_events: list[dict[str, Any]],
        snapshot_ts: datetime | None,
    ) -> bool:
        """Return True if a clipboard event occurred within the preceding window.

        When ``snapshot_ts`` is unknown we cannot determine the window, so we
        conservatively return False (i.e. do not suppress the detection).
        """
        if snapshot_ts is None:
            return False

        for event in recent_events:
            event_type = event.get("event_type", "")
            if "clipboard" not in str(event_type).lower():
                continue

            event_ts = self._parse_iso_timestamp(event.get("timestamp"))
            if event_ts is None:
                continue

            delta = (snapshot_ts - event_ts).total_seconds()
            if 0 <= delta <= _CLIPBOARD_WINDOW_SECONDS:
                return True

        return False
