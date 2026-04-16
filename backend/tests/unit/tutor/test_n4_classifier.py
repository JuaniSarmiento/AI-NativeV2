"""Unit tests for N4Classifier — heuristic classification of tutor interactions."""
from __future__ import annotations

import pytest

from app.features.tutor.n4_classifier import N4Classifier, N4ClassificationResult


@pytest.fixture
def classifier() -> N4Classifier:
    return N4Classifier()


# ---------------------------------------------------------------------------
# User message — level classification
# ---------------------------------------------------------------------------


def test_user_n1_comprehension(classifier: N4Classifier) -> None:
    """'no entiendo que tengo que hacer' → N1."""
    result = classifier.classify_message("no entiendo que tengo que hacer", "user")
    assert result.n4_level == 1


def test_user_n2_strategy(classifier: N4Classifier) -> None:
    """'como hago para recorrer la lista' → N2."""
    result = classifier.classify_message("como hago para recorrer la lista", "user")
    assert result.n4_level == 2


def test_user_n3_validation(classifier: N4Classifier) -> None:
    """'por que me da error en la linea 5' → N3."""
    result = classifier.classify_message("por que me da error en la linea 5", "user")
    assert result.n4_level == 3


def test_user_n4_metacognitive(classifier: N4Classifier) -> None:
    """'esta bien mi solucion o hay forma mejor' → N4."""
    result = classifier.classify_message(
        "esta bien mi solucion o hay forma mejor", "user"
    )
    assert result.n4_level == 4


def test_user_default_n1(classifier: N4Classifier) -> None:
    """Message with no matching patterns defaults to N1."""
    result = classifier.classify_message("hola", "user")
    assert result.n4_level == 1


def test_user_n1_confidence_high_on_match(classifier: N4Classifier) -> None:
    """Explicit N1 pattern match → high confidence."""
    result = classifier.classify_message("no entiendo este concepto", "user")
    assert result.n4_level == 1
    assert result.confidence == "high"


def test_user_default_n1_confidence_low(classifier: N4Classifier) -> None:
    """No pattern match → N1 with low confidence."""
    result = classifier.classify_message("hola", "user")
    assert result.n4_level == 1
    assert result.confidence == "low"


def test_user_n3_traceback(classifier: N4Classifier) -> None:
    """Message containing 'traceback' → N3."""
    result = classifier.classify_message(
        "me aparece un traceback que no entiendo", "user"
    )
    assert result.n4_level == 3


def test_user_n2_data_structure(classifier: N4Classifier) -> None:
    """'deberia usar lista o diccionario' → N2."""
    result = classifier.classify_message(
        "deberia usar lista o diccionario para esto", "user"
    )
    assert result.n4_level == 2


def test_user_n4_efficiency(classifier: N4Classifier) -> None:
    """'es eficiente mi solucion' → N4."""
    result = classifier.classify_message("es eficiente mi solucion?", "user")
    assert result.n4_level == 4


# ---------------------------------------------------------------------------
# Assistant message — level classification
# ---------------------------------------------------------------------------


def test_assistant_n1(classifier: N4Classifier) -> None:
    """Assistant explaining the problem statement → N1."""
    result = classifier.classify_message(
        "Empecemos por entender el problema antes de escribir código", "assistant"
    )
    assert result.n4_level == 1


def test_assistant_n3(classifier: N4Classifier) -> None:
    """Assistant addressing an error → N3."""
    result = classifier.classify_message(
        "Ese error se produce porque intentás acceder a un índice fuera de rango",
        "assistant",
    )
    assert result.n4_level == 3


def test_assistant_default_n1(classifier: N4Classifier) -> None:
    """Assistant message with no matching pattern → N1."""
    result = classifier.classify_message("Interesante observación.", "assistant")
    assert result.n4_level == 1


# ---------------------------------------------------------------------------
# Sub-classification
# ---------------------------------------------------------------------------


def test_sub_critical(classifier: N4Classifier) -> None:
    """'no puedo avanzar estoy trabado' → sub='critical'."""
    result = classifier.classify_message(
        "no puedo avanzar estoy trabado con esto", "user"
    )
    assert result.sub_classification == "critical"


def test_sub_dependent(classifier: N4Classifier) -> None:
    """'esta bien lo que hice? confirma' → sub='dependent'."""
    result = classifier.classify_message(
        "esta bien lo que hice? confirma por favor", "user"
    )
    assert result.sub_classification == "dependent"


def test_sub_exploratory(classifier: N4Classifier) -> None:
    """'que pasa si uso un diccionario' → sub='exploratory' (no critical/dependent)."""
    result = classifier.classify_message(
        "que pasa si uso un diccionario en vez de una lista", "user"
    )
    assert result.sub_classification == "exploratory"


def test_sub_critical_takes_priority_over_dependent(classifier: N4Classifier) -> None:
    """When both critical and dependent signals are present, critical wins."""
    result = classifier.classify_message(
        "no puedo, esta bien lo que hice? ayuda", "user"
    )
    # _SUB_CRITICAL_PATTERNS is checked first
    assert result.sub_classification == "critical"


def test_result_is_dataclass(classifier: N4Classifier) -> None:
    """classify_message always returns an N4ClassificationResult."""
    result = classifier.classify_message("hola", "user")
    assert isinstance(result, N4ClassificationResult)
    assert result.n4_level in (1, 2, 3, 4)
    assert result.sub_classification in ("critical", "dependent", "exploratory")
    assert result.confidence in ("high", "medium", "low")
