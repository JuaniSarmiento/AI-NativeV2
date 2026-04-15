"""GuardrailsProcessor — post-LLM response analysis for the socratic tutor.

Detects responses that violate pedagogical constraints:
- excessive_code: too many lines of code across all fenced blocks
- direct_solution: complete function/class definitions inside code blocks
- non_socratic: code blocks present but no guiding questions in the response
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

_DEFAULT_MAX_CODE_LINES = 5

# Regex to extract fenced code blocks (``` ... ```)
_FENCED_CODE_BLOCK_RE = re.compile(
    r"```[^\n]*\n(.*?)```",
    re.DOTALL,
)

# Detects a complete Python function definition inside a code block:
# starts with "def <name>(...)" on one line and has at least one non-empty
# indented body line (to exclude stubs like `def foo(): ...` on a single line)
_FUNCTION_DEF_RE = re.compile(
    r"^\s*def\s+\w+\s*\(.*?\)\s*(?:->.*?)?:\s*\n(\s+\S)",
    re.MULTILINE,
)

# Detects a complete class definition — "class Foo:" followed by an indented body
_CLASS_DEF_RE = re.compile(
    r"^\s*class\s+\w+.*?:\s*\n(\s+\S)",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Data class for results
# ---------------------------------------------------------------------------


@dataclass
class GuardrailResult:
    """Outcome of a guardrail analysis pass."""

    has_violation: bool
    violation_type: str | None = field(default=None)
    violation_details: str | None = field(default=None)
    corrective_message: str | None = field(default=None)

    @classmethod
    def ok(cls) -> "GuardrailResult":
        return cls(has_violation=False)

    @classmethod
    def violation(
        cls,
        violation_type: str,
        violation_details: str,
        corrective_message: str,
    ) -> "GuardrailResult":
        return cls(
            has_violation=True,
            violation_type=violation_type,
            violation_details=violation_details,
            corrective_message=corrective_message,
        )


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class GuardrailsProcessor:
    """Analyses an LLM response string and returns a :class:`GuardrailResult`.

    Rules are evaluated in priority order:
    1. excessive_code
    2. direct_solution
    3. non_socratic

    The first detected violation is returned.
    """

    def __init__(self, guardrails_config: dict | None = None) -> None:  # type: ignore[type-arg]
        config = guardrails_config or {}
        self._max_code_lines: int = int(
            config.get("max_code_lines", _DEFAULT_MAX_CODE_LINES)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, response_text: str) -> GuardrailResult:
        """Analyse *response_text* and return a :class:`GuardrailResult`.

        Returns :py:meth:`GuardrailResult.ok` when no violation is detected.
        """
        if not response_text or not response_text.strip():
            return GuardrailResult.ok()

        code_blocks = _extract_code_blocks(response_text)

        result = self._check_excessive_code(code_blocks)
        if result.has_violation:
            logger.warning(
                "Guardrail violation: excessive_code",
                extra={"details": result.violation_details},
            )
            return result

        result = self._check_direct_solution(code_blocks)
        if result.has_violation:
            logger.warning(
                "Guardrail violation: direct_solution",
                extra={"details": result.violation_details},
            )
            return result

        result = self._check_non_socratic(response_text, code_blocks)
        if result.has_violation:
            logger.warning(
                "Guardrail violation: non_socratic",
                extra={"details": result.violation_details},
            )
            return result

        return GuardrailResult.ok()

    # ------------------------------------------------------------------
    # Detection rules
    # ------------------------------------------------------------------

    def _check_excessive_code(self, code_blocks: list[str]) -> GuardrailResult:
        """Rule 1 — total lines of code across all blocks exceeds threshold."""
        if not code_blocks:
            return GuardrailResult.ok()

        total_lines = sum(
            _count_non_empty_lines(block) for block in code_blocks
        )
        if total_lines > self._max_code_lines:
            return GuardrailResult.violation(
                violation_type="excessive_code",
                violation_details=(
                    f"Total code lines: {total_lines}, limit: {self._max_code_lines}"
                ),
                corrective_message=self._generate_corrective("excessive_code"),
            )
        return GuardrailResult.ok()

    def _check_direct_solution(self, code_blocks: list[str]) -> GuardrailResult:
        """Rule 2 — complete function or class definition inside code blocks."""
        if not code_blocks:
            return GuardrailResult.ok()

        combined = "\n".join(code_blocks)

        if _FUNCTION_DEF_RE.search(combined):
            return GuardrailResult.violation(
                violation_type="direct_solution",
                violation_details="Complete function definition detected in code block",
                corrective_message=self._generate_corrective("direct_solution"),
            )

        if _CLASS_DEF_RE.search(combined):
            return GuardrailResult.violation(
                violation_type="direct_solution",
                violation_details="Complete class definition detected in code block",
                corrective_message=self._generate_corrective("direct_solution"),
            )

        return GuardrailResult.ok()

    def _check_non_socratic(
        self, response_text: str, code_blocks: list[str]
    ) -> GuardrailResult:
        """Rule 3 — code blocks present but no interrogative sentences outside code."""
        if not code_blocks:
            return GuardrailResult.ok()

        non_code_text = _strip_code_blocks(response_text)
        has_question = "?" in non_code_text

        if not has_question:
            return GuardrailResult.violation(
                violation_type="non_socratic",
                violation_details=(
                    "Response contains code but no guiding question was found"
                ),
                corrective_message=self._generate_corrective("non_socratic"),
            )

        return GuardrailResult.ok()

    # ------------------------------------------------------------------
    # Corrective messages
    # ------------------------------------------------------------------

    def _generate_corrective(self, violation_type: str) -> str:
        messages: dict[str, str] = {
            "excessive_code": (
                "Mi respuesta fue demasiado detallada en código. "
                "Mejor te pregunto: ¿qué parte de este problema es la que todavía no terminás de entender? "
                "Arranquemos por ahí."
            ),
            "direct_solution": (
                "Me fui al frente con código — eso no ayuda al proceso de aprendizaje. "
                "Pensemos juntos: ¿cuál sería el primer paso para resolver esto? "
                "¿Qué información tenés disponible y qué necesitás calcular?"
            ),
            "non_socratic": (
                "Quiero asegurarme de que estás construyendo el razonamiento, no solo copiando. "
                "¿Podés explicarme qué hace cada parte del código que te mostré? "
                "¿Tiene sentido para vos o hay algo que no queda claro?"
            ),
        }
        return messages.get(
            violation_type,
            "¿Qué parte del problema te genera más dudas en este momento?",
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_code_blocks(text: str) -> list[str]:
    """Return the raw content of every fenced code block in *text*."""
    return _FENCED_CODE_BLOCK_RE.findall(text)


def _strip_code_blocks(text: str) -> str:
    """Return *text* with all fenced code blocks removed."""
    return _FENCED_CODE_BLOCK_RE.sub("", text)


def _count_non_empty_lines(code: str) -> int:
    """Count non-empty, non-whitespace-only lines in a code string."""
    return sum(1 for line in code.splitlines() if line.strip())
