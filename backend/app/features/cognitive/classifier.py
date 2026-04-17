from __future__ import annotations

import asyncio
import json as _json
import logging
from dataclasses import dataclass

_classifier_logger = logging.getLogger(__name__)

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
        # Special case: tutor interaction is split by role.
        # Read the fine-grained n4_level from the payload (set by N4Classifier
        # in TutorService); fall back to 4 for legacy events without it.
        if raw_event_type == "tutor.interaction.completed":
            role = payload.get("role", "user")
            n4_from_payload = payload.get("n4_level")
            n4_level = int(n4_from_payload) if n4_from_payload is not None else 4
            if role == "assistant":
                return ClassifiedEvent(
                    event_type="tutor.response_received",
                    n4_level=n4_level,
                    payload=payload,
                )
            return ClassifiedEvent(
                event_type="tutor.question_asked",
                n4_level=n4_level,
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


# ---------------------------------------------------------------------------
# LLM-based hybrid classifier
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = (
    "Classify this student message. "
    'Respond ONLY with JSON: {"n4_level": 1-4, "prompt_type": "exploratory"|"verifier"|"generative"}. '
    "N1=comprehension, N2=strategy, N3=validation, N4=AI-metacognition."
)


async def llm_classify_message(
    content: str,
    role: str,
    api_key: str,
    model: str = "mistral-small-latest",
    timeout: float = 3.0,
) -> tuple[int, str | None] | None:
    """Classify a message using the LLM.

    Uses Mistral to classify the cognitive level and prompt type with
    higher accuracy than regex patterns, particularly for ambiguous messages.

    Args:
        content: The raw message text to classify.
        role: The message role ('user' or 'assistant').
        api_key: Mistral API key.
        model: Mistral model name.
        timeout: Maximum seconds to wait for the LLM response.

    Returns:
        A tuple of (n4_level, prompt_type) on success, or None on any
        failure (timeout, parse error, API error, etc.).
    """
    try:
        from mistralai.client import Mistral  # type: ignore[import-untyped]

        client = Mistral(api_key=api_key)

        async def _call() -> tuple[int, str | None]:
            response = await client.chat.complete_async(
                model=model,
                messages=[
                    {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=64,
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()
            parsed = _json.loads(raw_text)
            n4_level = int(parsed.get("n4_level", 1))
            n4_level = max(1, min(4, n4_level))
            prompt_type_raw = parsed.get("prompt_type")
            if role == "assistant":
                prompt_type = None
            elif prompt_type_raw in ("exploratory", "verifier", "generative"):
                prompt_type = prompt_type_raw
            else:
                prompt_type = "exploratory"
            return n4_level, prompt_type

        return await asyncio.wait_for(_call(), timeout=timeout)

    except asyncio.TimeoutError:
        _classifier_logger.warning(
            "LLM classification timed out",
            extra={"timeout": timeout, "role": role},
        )
        return None
    except _json.JSONDecodeError as exc:
        _classifier_logger.warning(
            "LLM classification returned invalid JSON",
            extra={"error": str(exc), "role": role},
        )
        return None
    except Exception as exc:
        _classifier_logger.warning(
            "LLM classification failed",
            extra={"error": str(exc), "role": role},
        )
        return None
