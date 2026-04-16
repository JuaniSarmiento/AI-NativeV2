from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Mapping: raw event_type → (canonical_ctr_type, n4_level)
#
# n4_level is None for lifecycle events that don't map directly to an
# N1-N4 observation level (session open/close, etc.).
# ---------------------------------------------------------------------------
_EVENT_TYPE_MAPPING: dict[str, tuple[str, int | None]] = {
    "reads_problem": ("reads_problem", 1),
    "code.executed": ("code.run", 3),
    "code.execution.failed": ("code.run", 3),
    "code.snapshot.captured": ("code.snapshot", 1),
    "exercise.submitted": ("submission.created", 2),
    "tutor.session.started": ("session.started", None),
    "tutor.session.ended": ("session.closed", None),
    "reflection.submitted": ("reflection.submitted", 1),
}


@dataclass
class ClassifiedEvent:
    """The result of classifying a raw event into a canonical CTR event.

    Attributes:
        event_type: Canonical CTR event type string.
        n4_level: Observation level 1-4, or None for lifecycle events.
        payload: Original payload dict, potentially enriched with classifier metadata.
    """

    event_type: str
    n4_level: int | None
    payload: dict  # type: ignore[type-arg]


class CognitiveEventClassifier:
    """Classifies raw domain events into canonical CTR events with N4 levels.

    Unknown event types return None — the consumer silently discards them.
    This is intentional: not every system event is a cognitive signal.

    tutor.interaction.completed is handled specially because it carries two
    distinct cognitive signals depending on the message role:
      - role=user → student is asking a question (N4 — AI interaction)
      - role=assistant → student is receiving a response (N4 — AI interaction)
    """

    def classify(
        self, raw_event_type: str, payload: dict  # type: ignore[type-arg]
    ) -> ClassifiedEvent | None:
        """Classify a raw event into a CTR ClassifiedEvent.

        Args:
            raw_event_type: The event_type string from the Redis stream message.
            payload: The event payload dict.

        Returns:
            A ClassifiedEvent, or None if the event type is unknown or
            should not be recorded in the CTR.
        """
        # Special case: tutor interaction is split by role
        if raw_event_type == "tutor.interaction.completed":
            role = payload.get("role", "user")
            if role == "assistant":
                return ClassifiedEvent(
                    event_type="tutor.response_received",
                    n4_level=4,
                    payload=payload,
                )
            return ClassifiedEvent(
                event_type="tutor.question_asked",
                n4_level=4,
                payload=payload,
            )

        mapping = _EVENT_TYPE_MAPPING.get(raw_event_type)
        if mapping is None:
            return None

        canonical_type, n4_level = mapping
        return ClassifiedEvent(
            event_type=canonical_type,
            n4_level=n4_level,
            payload=payload,
        )
