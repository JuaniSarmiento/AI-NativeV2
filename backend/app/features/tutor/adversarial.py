"""AdversarialDetector — pre-LLM guard for the socratic tutor.

Detects adversarial student messages before they reach the language model:
- jailbreak:   attempts to override system instructions
- malicious:   requests for harmful code or bypass techniques
- persuasion:  social-engineering to extract direct answers

All categories use both Spanish (voseo-aware) and English patterns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdversarialResult:
    is_adversarial: bool
    category: str | None = None
    matched_pattern: str | None = None
    attempt_number: int = 0
    should_escalate: bool = False

    @classmethod
    def clean(cls) -> AdversarialResult:
        return cls(is_adversarial=False)

    @classmethod
    def detected(
        cls, category: str, matched_pattern: str, attempt_number: int
    ) -> AdversarialResult:
        return cls(
            is_adversarial=True,
            category=category,
            matched_pattern=matched_pattern,
            attempt_number=attempt_number,
            should_escalate=attempt_number >= 3,
        )


# ---------------------------------------------------------------------------
# Pattern sets — Spanish (voseo) + English
# ---------------------------------------------------------------------------

_JAILBREAK_PATTERNS = [
    r"(?i)olvid[aá]\s+(tus|las)\s+(instrucciones|reglas)",
    r"(?i)ignor[aá]\s+(tus|las)\s+(instrucciones|reglas)",
    r"(?i)sos\s+un\s+asistente\s+normal",
    r"(?i)act\s+as\s+(a\s+)?(?!tutor)",
    r"(?i)you\s+are\s+now\s+(?!a tutor)",
    r"(?i)forget\s+(?:your|all|previous|all\s+previous)\s+(instructions|rules|guidelines)",
    r"(?i)ignore\s+(?:your|all|previous|all\s+previous)\s+(instructions|rules|guidelines)",
    r"(?i)\bDAN\b",
    r"(?i)do\s+anything\s+now",
    r"(?i)jailbreak",
    r"(?i)nuevo\s+modo",
    r"(?i)modo\s+desarrollador",
]

_MALICIOUS_PATTERNS = [
    r"(?i)hac[eé]\s+(un\s+)?(virus|malware|ransomware|troyano)",
    r"(?i)sql\s+injection",
    r"(?i)hack(ear|e[aá])",
    r"(?i)exploit",
    r"(?i)hacer?\s+trampa",
    r"(?i)bypass\s+(security|auth)",
    r"(?i)c[oó]digo\s+malicioso",
]

_PERSUASION_PATTERNS = [
    r"(?i)el\s+prof(e|esor)\s+me\s+dijo\s+que",
    r"(?i)tengo\s+examen\s+(ahora|ya|en\s+\d)",
    r"(?i)es\s+urgente.*dame\s+(la\s+)?respuesta",
    r"(?i)dame\s+(la\s+)?soluci[oó]n\s+(completa|directa|entera)",
    r"(?i)necesito\s+la\s+respuesta\s+(ya|ahora|urgente)",
    r"(?i)the\s+teacher\s+(said|told)\s+(?:me\s+(?:to|that|I\s+could|you\s+could)|me\b)",
    r"(?i)the\s+teacher\s+said\s+I",
    r"(?i)just\s+give\s+me\s+the\s+(answer|solution|code)",
]

_STANDARD_RESPONSE = (
    "Entiendo tu urgencia, pero mi rol es ayudarte a pensar el problema. "
    "¿Qué parte del ejercicio te está trabando?"
)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class AdversarialDetector:
    """Detects adversarial student behavior before messages reach the LLM.

    Maintains a per-session attempt counter in memory. The counter persists
    for the lifetime of the detector instance (typically a module-level
    singleton), so a single student session accumulates across chat turns.
    """

    def __init__(self) -> None:
        self._session_attempts: dict[str, int] = {}
        # Pre-compile all patterns tagged with their category
        self._compiled: list[tuple[str, re.Pattern[str]]] = []
        for pattern_str in _JAILBREAK_PATTERNS:
            self._compiled.append(("jailbreak", re.compile(pattern_str)))
        for pattern_str in _MALICIOUS_PATTERNS:
            self._compiled.append(("malicious", re.compile(pattern_str)))
        for pattern_str in _PERSUASION_PATTERNS:
            self._compiled.append(("persuasion", re.compile(pattern_str)))

    def check(self, message: str, session_id: str) -> AdversarialResult:
        """Evaluate *message* against all pattern sets.

        Returns :py:meth:`AdversarialResult.clean` when safe, or
        :py:meth:`AdversarialResult.detected` on first match found.
        Attempt counter for *session_id* is incremented on every detection.
        """
        for category, pattern in self._compiled:
            if pattern.search(message):
                count = self._session_attempts.get(session_id, 0) + 1
                self._session_attempts[session_id] = count
                logger.warning(
                    "Adversarial message detected",
                    extra={
                        "category": category,
                        "session_id": session_id,
                        "attempt_number": count,
                    },
                )
                return AdversarialResult.detected(
                    category=category,
                    matched_pattern=pattern.pattern,
                    attempt_number=count,
                )
        return AdversarialResult.clean()

    def reset_session(self, session_id: str) -> None:
        """Clear the attempt counter for *session_id* (e.g. on session close)."""
        self._session_attempts.pop(session_id, None)

    @staticmethod
    def standard_response() -> str:
        """Return the canonical safe reply for adversarial messages."""
        return _STANDARD_RESPONSE


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all service instances in a process
# ---------------------------------------------------------------------------

_detector: AdversarialDetector | None = None


def get_adversarial_detector() -> AdversarialDetector:
    """Return the process-level singleton :class:`AdversarialDetector`."""
    global _detector
    if _detector is None:
        _detector = AdversarialDetector()
    return _detector
