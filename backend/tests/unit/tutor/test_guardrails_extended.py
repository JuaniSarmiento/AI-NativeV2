"""Unit tests for GP3 and GP5 audit-only guardrails in GuardrailsProcessor.

GP3: verify the tutor response references the student's actual code identifiers.
GP5: verify debugging responses include a concrete test-case suggestion.

Both checks are AUDIT ONLY — they log but never block. We use caplog to
verify the audit events fire (or don't fire) as expected.
"""
from __future__ import annotations

import logging

import pytest

from app.features.tutor.guardrails import GuardrailsProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _processor(config: dict | None = None) -> GuardrailsProcessor:
    return GuardrailsProcessor(config)


def _code_block(code: str, lang: str = "python") -> str:
    return f"```{lang}\n{code}\n```"


# ---------------------------------------------------------------------------
# GP3 — code reference audit
# ---------------------------------------------------------------------------


STUDENT_CODE_WITH_VARS = """\
def calcular_promedio(lista_numeros):
    total = sum(lista_numeros)
    cantidad = len(lista_numeros)
    return total / cantidad
"""


def test_gp3_no_log_when_response_references_student_identifier(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3: response mentions 'lista_numeros' → no audit log expected."""
    response = (
        "¿Qué pasa si `lista_numeros` está vacía? "
        "¿Qué valor retornaría `total` en ese caso?"
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(
            response, student_code=STUDENT_CODE_WITH_VARS
        )
    assert result.has_violation is False
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    assert len(gp3_logs) == 0


def test_gp3_logs_when_response_does_not_reference_student_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3: response mentions no student identifiers → audit log emitted."""
    response = (
        "Pensá en los casos borde de tu solución. "
        "¿Qué pasa con el valor de retorno cuando la entrada es inválida?"
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(
            response, student_code=STUDENT_CODE_WITH_VARS
        )
    assert result.has_violation is False
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    assert len(gp3_logs) == 1
    assert "does not reference" in gp3_logs[0].getMessage()


def test_gp3_skipped_when_student_code_is_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3: no student_code provided → audit check skipped entirely."""
    response = "¿Qué estructura de datos te parece más adecuada aquí?"
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor().analyze(response, student_code=None)
    assert result.has_violation is False
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    assert len(gp3_logs) == 0


def test_gp3_skipped_when_student_code_has_no_meaningful_identifiers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3: student code with only keywords/short names → no identifiers to check."""
    trivial_code = "if x:\n    pass\nfor i in y:\n    print(i)"
    response = "No hay variables sustantivas que referenciar."
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        _processor().analyze(response, student_code=trivial_code)
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    assert len(gp3_logs) == 0


def test_gp3_case_insensitive_matching(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3: identifier matching is case-insensitive."""
    student_code = "def calcular_suma(valores):\n    return sum(valores)"
    response = "¿Qué hace CALCULAR_SUMA cuando recibe VALORES vacíos?"
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        _processor({"max_code_lines": 100}).analyze(
            response, student_code=student_code
        )
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    assert len(gp3_logs) == 0


def test_gp3_does_not_block_response(caplog: pytest.LogCaptureFixture) -> None:
    """GP3 audit firing must never return a violation — response passes through."""
    response = "Buena pregunta, pensá en los casos borde."
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(
            response, student_code=STUDENT_CODE_WITH_VARS
        )
    # Even if GP3 fires, the result must be ok (not a blocking violation)
    assert result.has_violation is False
    assert result.violation_type is None


# ---------------------------------------------------------------------------
# GP5 — test suggestion audit
# ---------------------------------------------------------------------------


def test_gp5_no_log_when_debugging_response_has_concrete_example(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP5: debugging response includes 'probá con [1, 2, 3]' → no log."""
    response = (
        "Hay un error en tu implementación. "
        "Probá con [1, 2, 3] para ver si el resultado esperado coincide."
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(response)
    assert result.has_violation is False
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp5_logs) == 0


def test_gp5_no_log_when_debugging_response_uses_por_ejemplo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP5: 'por ejemplo' counts as a test suggestion."""
    response = (
        "Tu función tiene un bug. Por ejemplo, ¿qué devuelve "
        "cuando la lista tiene un solo elemento?"
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        _processor({"max_code_lines": 100}).analyze(response)
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp5_logs) == 0


def test_gp5_no_log_when_debugging_response_uses_que_pasa_si(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP5: 'qué pasa si' counts as a test suggestion."""
    response = "Hay un traceback. ¿Qué pasa si le pasás una lista vacía?"
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        _processor({"max_code_lines": 100}).analyze(response)
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp5_logs) == 0


def test_gp5_logs_when_debugging_response_lacks_test_suggestion(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP5: debugging response without test suggestion → audit log emitted."""
    response = (
        "Tu programa tiene un error. Revisá la lógica de tu condición "
        "y asegurate de manejar el caso vacío."
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(response)
    assert result.has_violation is False
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp5_logs) == 1
    assert "lacks concrete test suggestion" in gp5_logs[0].getMessage()


def test_gp5_skipped_when_response_is_not_debugging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP5: no debugging indicators → check skipped entirely, no log."""
    response = (
        "La recursión funciona dividiendo el problema en subproblemas. "
        "¿Qué sería el caso base en tu problema?"
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        _processor().analyze(response)
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp5_logs) == 0


def test_gp5_does_not_block_response(caplog: pytest.LogCaptureFixture) -> None:
    """GP5 audit firing must never return a blocking violation."""
    debugging_response = "Tu código tiene un bug, revisá la condición de salida."
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(debugging_response)
    assert result.has_violation is False
    assert result.violation_type is None


# ---------------------------------------------------------------------------
# Interaction between GP3, GP5, and blocking guardrails
# ---------------------------------------------------------------------------


def test_blocking_violation_takes_priority_over_gp3_gp5(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When a blocking violation fires, GP3/GP5 audits are never reached."""
    # 6 lines of code → excessive_code violation fires first
    code = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6"
    response = (
        f"Acá hay un error:\n{_code_block(code)}\n"
        "Revisá la lógica sin sugerencias concretas."
    )
    student_code = "def mi_funcion(lista_valores):\n    return None"
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor().analyze(response, student_code=student_code)
    assert result.has_violation is True
    assert result.violation_type == "excessive_code"
    # GP3/GP5 should NOT have run
    audit_logs = [
        r for r in caplog.records if "GP3" in r.getMessage() or "GP5" in r.getMessage()
    ]
    assert len(audit_logs) == 0


def test_both_gp3_and_gp5_can_fire_together(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GP3 and GP5 can both log in the same response."""
    student_code = "def ordenar_lista(elementos):\n    pass"
    # Response mentions debugging but no test suggestion, and no student identifier
    response = (
        "Tu programa tiene un bug. "
        "Revisá el flujo de control de la función."
    )
    with caplog.at_level(logging.INFO, logger="app.features.tutor.guardrails"):
        result = _processor({"max_code_lines": 100}).analyze(
            response, student_code=student_code
        )
    assert result.has_violation is False
    gp3_logs = [r for r in caplog.records if "GP3" in r.getMessage()]
    gp5_logs = [r for r in caplog.records if "GP5" in r.getMessage()]
    assert len(gp3_logs) == 1
    assert len(gp5_logs) == 1
