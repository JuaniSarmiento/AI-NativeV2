"""Unit tests for GuardrailsProcessor."""
from __future__ import annotations

import pytest

from app.features.tutor.guardrails import GuardrailResult, GuardrailsProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _code_block(code: str, lang: str = "python") -> str:
    return f"```{lang}\n{code}\n```"


def _processor(config: dict | None = None) -> GuardrailsProcessor:  # type: ignore[type-arg]
    return GuardrailsProcessor(config)


# ---------------------------------------------------------------------------
# Rule 1 — excessive_code
# ---------------------------------------------------------------------------


def test_excessive_code_detected() -> None:
    """6 lines of code in a single block → violation."""
    code = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6"
    response = f"Mirá esto:\n{_code_block(code)}\n¿Qué notás?"
    result = _processor().analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"


def test_code_within_limit_no_violation() -> None:
    """5 lines of code → no violation (at limit)."""
    code = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5"
    response = f"Considerá esto:\n{_code_block(code)}\n¿Qué hace cada línea?"
    result = _processor().analyze(response)
    assert result.has_violation is False


def test_multiple_blocks_summed_over_limit() -> None:
    """Two blocks of 3 lines each → total 6 lines → violation."""
    block1 = _code_block("a = 1\nb = 2\nc = 3")
    block2 = _code_block("x = 4\ny = 5\nz = 6")
    response = f"Primero:\n{block1}\nDespués:\n{block2}\n¿Qué diferencias ves?"
    result = _processor().analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"


def test_multiple_blocks_summed_within_limit() -> None:
    """Two blocks of 2 lines each → total 4 lines → no violation."""
    block1 = _code_block("a = 1\nb = 2")
    block2 = _code_block("x = 3\ny = 4")
    response = f"Mirá:\n{block1}\ny esto:\n{block2}\n¿Qué notás?"
    result = _processor().analyze(response)
    assert result.has_violation is False


def test_empty_lines_in_code_block_not_counted() -> None:
    """Empty lines inside code blocks don't count toward the limit."""
    code = "a = 1\n\nb = 2\n\nc = 3\n\nd = 4\n\ne = 5"  # 5 non-empty + 4 empty
    response = f"Ejemplo:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor().analyze(response)
    assert result.has_violation is False


def test_custom_threshold_three_lines() -> None:
    """Config with max_code_lines=3: 4 lines → violation."""
    code = "a = 1\nb = 2\nc = 3\nd = 4"
    response = f"Acá:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor({"max_code_lines": 3}).analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"


def test_custom_threshold_three_lines_at_limit() -> None:
    """Config with max_code_lines=3: 3 lines → no violation."""
    code = "a = 1\nb = 2\nc = 3"
    response = f"Acá:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor({"max_code_lines": 3}).analyze(response)
    assert result.has_violation is False


def test_no_config_uses_defaults() -> None:
    """None config → default max_code_lines=5."""
    code = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5"
    response = f"Ejemplo:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor(None).analyze(response)
    assert result.has_violation is False


# ---------------------------------------------------------------------------
# Rule 2 — direct_solution
# ---------------------------------------------------------------------------


def test_direct_solution_function_detected() -> None:
    """Complete def with indented body → direct_solution violation."""
    code = "def suma(lst):\n    total = 0\n    for x in lst:\n        total += x\n    return total"
    response = f"Podría ser así:\n{_code_block(code)}\n¿Qué notás?"
    result = _processor().analyze(response)
    assert result.has_violation is True
    assert result.violation_type in ("excessive_code", "direct_solution")


def test_direct_solution_function_multi_line_body_explicit() -> None:
    """Ensure direct_solution is detected when under line threshold."""
    code = "def f(x):\n    return x + 1"
    response = f"Mirá:\n{_code_block(code)}\n¿Podés adaptarlo?"
    result = _processor({"max_code_lines": 10}).analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "direct_solution"


def test_direct_solution_class_detected() -> None:
    """Complete class definition with indented body → direct_solution violation."""
    code = "class Nodo:\n    def __init__(self, val):\n        self.val = val"
    response = f"Podría estructurarse así:\n{_code_block(code)}\n¿Qué rol tiene `__init__`?"
    result = _processor({"max_code_lines": 20}).analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "direct_solution"


def test_partial_code_no_violation() -> None:
    """Pseudocode / incomplete snippet without full function definition → ok."""
    code = "# iterá sobre la lista\nfor item in lista:\n    ..."
    response = f"Pensalo así:\n{_code_block(code)}\n¿Por qué iterar?"
    result = _processor({"max_code_lines": 10}).analyze(response)
    assert result.has_violation is False


def test_function_stub_no_body_no_violation() -> None:
    """A function stub (no body lines) should not trigger direct_solution."""
    # A one-liner stub like "def foo(): ..." doesn't have an indented body line
    code = "def suma(lst): ..."
    response = f"Algo así:\n{_code_block(code)}\n¿Cómo completarías el cuerpo?"
    result = _processor({"max_code_lines": 10}).analyze(response)
    assert result.has_violation is False


# ---------------------------------------------------------------------------
# Rule 3 — non_socratic
# ---------------------------------------------------------------------------


def test_non_socratic_detected() -> None:
    """Code present but zero question marks in non-code text → non_socratic."""
    code = "total = sum(lista)"
    response = f"Podés usar sum directamente.\n{_code_block(code)}\nEso resuelve el problema."
    result = _processor({"max_code_lines": 10}).analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "non_socratic"


def test_socratic_ok_question_present() -> None:
    """Code present AND at least one question mark → no non_socratic violation."""
    code = "total = sum(lista)"
    response = f"¿Sabías que Python tiene una función built-in?\n{_code_block(code)}\n¿Qué hace `sum`?"
    result = _processor({"max_code_lines": 10}).analyze(response)
    assert result.has_violation is False


def test_no_code_blocks_non_socratic_not_triggered() -> None:
    """Without any code blocks, non_socratic is not triggered even without ?"""
    response = "La recursión implica que una función se llame a sí misma. Tené cuidado con el caso base."
    result = _processor().analyze(response)
    assert result.has_violation is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_response_ok() -> None:
    result = _processor().analyze("")
    assert result.has_violation is False


def test_whitespace_only_response_ok() -> None:
    result = _processor().analyze("   \n\n  ")
    assert result.has_violation is False


def test_no_code_blocks_ok() -> None:
    response = "Pensá en qué estructura de datos te conviene usar. ¿Qué operaciones necesitás?"
    result = _processor().analyze(response)
    assert result.has_violation is False


def test_violation_type_priority_excessive_before_direct_solution() -> None:
    """When both excessive_code and direct_solution would fire, excessive_code wins."""
    # 6-line complete function
    code = (
        "def f(x):\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    d = 4\n"
        "    return a + b + c + d + x"
    )
    response = f"Así:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor().analyze(response)
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"


def test_corrective_message_is_spanish() -> None:
    """Corrective messages must be non-empty and in Spanish (check for common words)."""
    code = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6"
    response = f"Mirá:\n{_code_block(code)}\n¿Qué hace?"
    result = _processor().analyze(response)
    assert result.corrective_message is not None
    assert len(result.corrective_message) > 10
    # Spanish indicator words
    assert any(
        word in result.corrective_message.lower()
        for word in ["qué", "que", "pregunto", "te", "la", "el", "de"]
    )


def test_guardrail_result_ok_factory() -> None:
    result = GuardrailResult.ok()
    assert result.has_violation is False
    assert result.violation_type is None
    assert result.corrective_message is None


def test_guardrail_result_violation_factory() -> None:
    result = GuardrailResult.violation("excessive_code", "6 lines", "Rewrite")
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"
    assert result.violation_details == "6 lines"
    assert result.corrective_message == "Rewrite"
