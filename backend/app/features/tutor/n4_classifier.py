"""N4 Classifier — heuristic classification of tutor interactions by cognitive level.

The N4 model describes four levels of student cognitive engagement:

- N1 — Comprensión: student is still understanding the problem statement or basic concepts.
- N2 — Estrategia: student is planning an approach or selecting data structures/algorithms.
- N3 — Validación: student is debugging, testing, or verifying their solution.
- N4 — Interacción IA: student is reflecting metacognitively or evaluating solution quality.

Sub-classifications provide additional signal:
- "critical":    student is stuck and can't make progress.
- "dependent":   student needs external confirmation for every step.
- "exploratory": student is actively constructing knowledge (default).

Patterns are in Spanish because all student interactions are in Spanish.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class N4ClassificationResult:
    """Result of a single message classification."""

    n4_level: int
    """Cognitive level 1–4 (N1 to N4)."""

    sub_classification: str
    """One of: 'critical', 'dependent', 'exploratory'."""

    confidence: str
    """One of: 'high', 'medium', 'low'."""


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# ---- User patterns ----

_USER_N4_PATTERNS = re.compile(
    r"(?:"
    r"esta bien mi soluci[oó]n"
    r"|hay forma (m[aá]s )?(mejor|eficiente)"
    r"|qu[eé] opin[aá]s"
    r"|es eficiente"
    r"|me convence"
    r"|se puede mejorar"
    r"|cu[aá]l es la diferencia entre"
    r"|es la mejor forma"
    r"|vale la pena"
    r"|complejidad"
    r")",
    re.IGNORECASE,
)

_USER_N3_PATTERNS = re.compile(
    r"(?:"
    r"por qu[eé] (me |te |le )?da error"
    r"|no funciona"
    r"|el test falla"
    r"|da un resultado distinto"
    r"|me tira"
    r"|traceback"
    r"|exception"
    r"|el output es"
    r"|resultado incorrecto"
    r"|no me da"
    r"|falla"
    r"|error en"
    r"|stacktrace"
    r"|por qu[eé] sale"
    r"|no compila"
    r")",
    re.IGNORECASE,
)

_USER_N2_PATTERNS = re.compile(
    r"(?:"
    r"c[oó]mo hago para"
    r"|qu[eé] estructura (uso|usar[ií]a)"
    r"|deb[eé]r[ií]a usar"
    r"|mi idea es"
    r"|se me ocurre"
    r"|podr[ií]a (hacer|usar)"
    r"|qu[eé] pasa si uso"
    r"|for o while"
    r"|lista o diccionario"
    r"|c[uú]ando usar"
    r"|qu[eé] conviene"
    r"|algoritmo"
    r"|planificar"
    r"|ordenar"
    r"|recorrer"
    r")",
    re.IGNORECASE,
)

_USER_N1_PATTERNS = re.compile(
    r"(?:"
    r"no entiendo"
    r"|qu[eé] tengo que hacer"
    r"|qu[eé] significa"
    r"|no s[eé] por d[oó]nde empezar"
    r"|c[oó]mo funciona"
    r"|qu[eé] es un"
    r"|para qu[eé] sirve"
    r"|no s[eé] qu[eé] es"
    r"|no entend[ií]"
    r"|no comprendo"
    r"|me pod[eé]s explicar"
    r"|qu[eé] quiere decir"
    r")",
    re.IGNORECASE,
)

# ---- Assistant patterns ----

_ASSISTANT_N4_PATTERNS = re.compile(
    r"(?:"
    r"la calidad de tu soluci[oó]n"
    r"|pensar cr[ií]ticamente"
    r"|reflexion[aá]"
    r"|qu[eé] ventajas"
    r"|qu[eé] desventajas"
    r"|comparando"
    r"|complejidad"
    r"|es m[aá]s eficiente"
    r"|cu[aá]l preferir[ií]as"
    r")",
    re.IGNORECASE,
)

_ASSISTANT_N3_PATTERNS = re.compile(
    r"(?:"
    r"ese error (se produce|ocurre)"
    r"|el traceback"
    r"|revis[aá] la l[ií]nea"
    r"|el valor de"
    r"|agreg[aá] un print"
    r"|qu[eé] valor ten[eé]s en"
    r"|verific[aá]"
    r"|el test espera"
    r"|compar[aá] el output"
    r"|debug"
    r")",
    re.IGNORECASE,
)

_ASSISTANT_N2_PATTERNS = re.compile(
    r"(?:"
    r"qu[eé] estructura"
    r"|c[oó]mo planificar[ií]as"
    r"|qu[eé] pasos"
    r"|el algoritmo"
    r"|considerando"
    r"|una opci[oó]n ser[ií]a"
    r"|podr[ií]as usar"
    r"|qu[eé] operaciones"
    r")",
    re.IGNORECASE,
)

_ASSISTANT_N1_PATTERNS = re.compile(
    r"(?:"
    r"empecemos por entender"
    r"|el problema pide"
    r"|primero aclaremos"
    r"|en otras palabras"
    r"|lo que necesit[aá]s"
    r"|la consigna dice"
    r"|antes de (escribir|codear|programar)"
    r"|entend[eé]s lo que"
    r"|qu[eé] datos ten[eé]s"
    r")",
    re.IGNORECASE,
)

# ---- Sub-classification patterns ----

_SUB_CRITICAL_PATTERNS = re.compile(
    r"(?:"
    r"no puedo"
    r"|estoy trabado"
    r"|no avanzo"
    r"|no s[eé] nada"
    r"|\bayuda\b"
    r"|no s[eé] c[oó]mo"
    r"|me rindo"
    r"|no llego"
    r"|bloqueado"
    r")",
    re.IGNORECASE,
)

_SUB_DEPENDENT_PATTERNS = re.compile(
    r"(?:"
    r"est[aá] bien\?"
    r"|es correcto\?"
    r"|confirma"
    r"|dec[ií]me que hacer"
    r"|hac[eé] vos"
    r"|est[aá] mal\?"
    r"|aprueba"
    r"|verify"
    r"|check"
    r"|lo hice bien\?"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class N4Classifier:
    """Heuristic classifier for tutor interaction messages.

    Patterns are evaluated in priority order (N4 → N3 → N2 → N1) because
    higher levels are more specific and less likely to produce false positives.

    Usage::

        classifier = N4Classifier()
        result = classifier.classify_message("no entiendo el problema", "user")
        # result.n4_level == 1, result.sub_classification == "exploratory"
    """

    def classify_message(self, content: str, role: str) -> N4ClassificationResult:
        """Classify a single message by N4 cognitive level.

        Args:
            content: The raw message text.
            role: Either ``"user"`` or ``"assistant"``.

        Returns:
            A :class:`N4ClassificationResult` with level, sub-classification,
            and confidence.
        """
        if role == "user":
            n4_level, confidence = self._classify_user(content)
        else:
            n4_level, confidence = self._classify_assistant(content)

        sub_classification = self._classify_sub(content)

        logger.debug(
            "N4 classification",
            extra={
                "role": role,
                "n4_level": n4_level,
                "sub_classification": sub_classification,
                "confidence": confidence,
            },
        )

        return N4ClassificationResult(
            n4_level=n4_level,
            sub_classification=sub_classification,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Private classification logic
    # ------------------------------------------------------------------

    def _classify_user(self, content: str) -> tuple[int, str]:
        """Classify a user message. Returns (n4_level, confidence)."""
        if _USER_N4_PATTERNS.search(content):
            return 4, "high"
        if _USER_N3_PATTERNS.search(content):
            return 3, "high"
        if _USER_N2_PATTERNS.search(content):
            return 2, "high"
        if _USER_N1_PATTERNS.search(content):
            return 1, "high"
        # Default: N1 with low confidence
        return 1, "low"

    def _classify_assistant(self, content: str) -> tuple[int, str]:
        """Classify an assistant message. Returns (n4_level, confidence)."""
        if _ASSISTANT_N4_PATTERNS.search(content):
            return 4, "high"
        if _ASSISTANT_N3_PATTERNS.search(content):
            return 3, "high"
        if _ASSISTANT_N2_PATTERNS.search(content):
            return 2, "high"
        if _ASSISTANT_N1_PATTERNS.search(content):
            return 1, "high"
        # Default: N1 with low confidence
        return 1, "low"

    def _classify_sub(self, content: str) -> str:
        """Determine sub-classification from message content."""
        if _SUB_CRITICAL_PATTERNS.search(content):
            return "critical"
        if _SUB_DEPENDENT_PATTERNS.search(content):
            return "dependent"
        return "exploratory"
