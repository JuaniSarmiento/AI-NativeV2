"""ContextBuilder — composes the dynamic system prompt for the tutor.

Loads exercise metadata, the student's latest code snapshot, and renders
them into a base prompt template using str.format() placeholders.
"""
from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.features.submissions.models import CodeSnapshot
from app.shared.models.exercise import Exercise

logger = get_logger(__name__)

_CODE_TRUNCATE_LIMIT = 2000
_TRUNCATION_PREFIX = "[...codigo truncado...]\n"

# Placeholder names that must exist in SOCRATIC_PROMPT_V2 template
_REQUIRED_PLACEHOLDERS = (
    "{exercise_title}",
    "{exercise_description}",
    "{exercise_difficulty}",
    "{exercise_topics}",
    "{exercise_language}",
    "{student_code}",
)


class ContextBuilder:
    """Builds the fully composed system prompt for a tutor interaction.

    Does NOT hold state between calls — all data is fetched fresh each time
    so the prompt reflects the latest exercise state and student code.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_prompt(
        self,
        *,
        exercise_id: uuid.UUID,
        student_id: uuid.UUID,
        base_prompt_template: str,
    ) -> str:
        """Render *base_prompt_template* with dynamic exercise + student context.

        Args:
            exercise_id: ID of the exercise being solved.
            student_id: ID of the student chatting with the tutor.
            base_prompt_template: The raw system prompt with ``{placeholder}``
                slots as defined in ``SOCRATIC_PROMPT_V2``.

        Returns:
            A fully rendered string ready to pass to the LLM.

        Raises:
            NotFoundError: when the exercise does not exist.
        """
        exercise = await self._load_exercise(exercise_id)
        student_code = await self._load_student_code(student_id, exercise_id, exercise)

        replacements = self._build_replacements(exercise, student_code)

        # If the template has an {exercise_rubric} placeholder, handle it
        # conditionally: fill it if rubric exists, otherwise strip the section.
        if "{exercise_rubric}" in base_prompt_template:
            if exercise.rubric:
                replacements["exercise_rubric"] = exercise.rubric
            else:
                # Remove the rubric section entirely — strip placeholder and any
                # surrounding newlines to avoid blank lines in the final prompt.
                base_prompt_template = _remove_rubric_section(base_prompt_template)

        # Same for activity context placeholders
        if "{activity_title}" in base_prompt_template:
            activity = getattr(exercise, "activity", None)
            if activity is not None:
                replacements["activity_title"] = activity.title
                replacements["activity_description"] = activity.description or ""
            else:
                base_prompt_template = _remove_activity_section(base_prompt_template)

        try:
            composed = base_prompt_template.format(**replacements)
        except KeyError as exc:
            logger.warning(
                "Prompt template has unknown placeholder",
                extra={"placeholder": str(exc), "exercise_id": str(exercise_id)},
            )
            # Fallback: return template with as many substitutions as we can
            composed = _safe_format(base_prompt_template, replacements)

        logger.debug(
            "Composed prompt",
            extra={
                "exercise_id": str(exercise_id),
                "student_id": str(student_id),
                "prompt_length": len(composed),
                "has_rubric": exercise.rubric is not None,
                "has_activity": getattr(exercise, "activity", None) is not None,
                "student_code_source": (
                    "snapshot" if student_code != "El alumno aun no ha escrito codigo"
                    and student_code != _truncate_code(exercise.starter_code or "")
                    else "starter_code" if (exercise.starter_code or "").strip()
                    else "none"
                ),
            },
        )
        return composed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_exercise(self, exercise_id: uuid.UUID) -> Exercise:
        result = await self._session.execute(
            select(Exercise)
            .where(Exercise.id == exercise_id)
            .options(selectinload(Exercise.activity))
        )
        exercise = result.scalar_one_or_none()
        if exercise is None:
            raise NotFoundError(f"Exercise {exercise_id} not found")
        return exercise

    async def _load_student_code(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        exercise: Exercise,
    ) -> str:
        result = await self._session.execute(
            select(CodeSnapshot)
            .where(
                CodeSnapshot.student_id == student_id,
                CodeSnapshot.exercise_id == exercise_id,
            )
            .order_by(desc(CodeSnapshot.snapshot_at))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot is not None:
            return _truncate_code(snapshot.code)

        # No snapshot — fall back to starter code
        starter = exercise.starter_code or ""
        if starter.strip():
            return _truncate_code(starter)

        return "El alumno aun no ha escrito codigo"

    def _build_replacements(self, exercise: Exercise, student_code: str) -> dict[str, str]:
        topics = ", ".join(exercise.topic_tags) if exercise.topic_tags else "sin clasificar"
        return {
            "exercise_title": exercise.title,
            "exercise_description": exercise.description or "",
            "exercise_difficulty": exercise.difficulty.value if exercise.difficulty else "sin especificar",
            "exercise_topics": topics,
            "exercise_language": exercise.language or "Python",
            "student_code": student_code,
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _truncate_code(code: str) -> str:
    """Return code truncated to the last ``_CODE_TRUNCATE_LIMIT`` chars."""
    if len(code) <= _CODE_TRUNCATE_LIMIT:
        return code
    truncated = code[-_CODE_TRUNCATE_LIMIT:]
    return _TRUNCATION_PREFIX + truncated


def _remove_rubric_section(template: str) -> str:
    """Remove the rubric section block from the template string.

    Looks for patterns like::

        ### Rúbrica del ejercicio
        {exercise_rubric}

    and strips them (including surrounding blank lines).
    """
    import re

    # Try to remove the whole header + placeholder block
    pattern = r"\n?#{1,4}[^\n]*r[uú]brica[^\n]*\n\{exercise_rubric\}\n?"
    cleaned = re.sub(pattern, "\n", template, flags=re.IGNORECASE)
    # Fallback: just remove the bare placeholder
    cleaned = cleaned.replace("{exercise_rubric}", "")
    return cleaned


def _remove_activity_section(template: str) -> str:
    """Remove the activity section block from the template string."""
    import re

    pattern = (
        r"\n?#{1,4}[^\n]*actividad[^\n]*\n"
        r"\{activity_title\}[^\n]*\n?"
        r"(\{activity_description\})?\n?"
    )
    cleaned = re.sub(pattern, "\n", template, flags=re.IGNORECASE)
    cleaned = cleaned.replace("{activity_title}", "").replace("{activity_description}", "")
    return cleaned


def _safe_format(template: str, replacements: dict[str, str]) -> str:
    """Apply only known replacements, leave unknown placeholders as-is."""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{key}}}", value)
    return result
