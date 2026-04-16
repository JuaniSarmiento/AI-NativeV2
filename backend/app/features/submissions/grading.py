"""AI-assisted grading service for activity submissions.

Evaluates ALL exercises in an activity submission at once, producing
a general score + individual exercise scores + feedback.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.submissions.models import (
    ActivitySubmission,
    Submission,
    SubmissionStatus,
)
from app.features.tutor.llm_adapter import ChatMessage, LLMAdapter
from app.shared.models.exercise import Exercise

logger = logging.getLogger(__name__)

_GRADING_SYSTEM_PROMPT = """Sos un evaluador de ejercicios de programacion universitaria (UTN).
Tu tarea es evaluar TODOS los ejercicios de una actividad enviada por un alumno.

Responde EXCLUSIVAMENTE en formato JSON con esta estructura:
{
  "general_score": <numero entre 0 y 100 — nota general de la actividad>,
  "general_feedback": "<evaluacion general de la actividad en español, 2-4 oraciones>",
  "exercises": [
    {
      "exercise_id": "<id del ejercicio>",
      "score": <numero entre 0 y 100>,
      "feedback": "<feedback especifico de este ejercicio, 1-2 oraciones>",
      "strengths": ["<aspecto positivo>"],
      "improvements": ["<mejora sugerida>"]
    }
  ]
}

Criterios por ejercicio:
- Correctitud: el codigo resuelve el problema planteado
- Calidad: buenas practicas, nombres claros, estructura
- Completitud: manejo de casos borde
- Score 0-20: codigo vacio o no intenta resolver
- Score 20-50: intenta pero errores graves
- Score 50-75: funciona parcialmente
- Score 75-100: funciona correctamente con buena calidad

La nota general es un promedio ponderado considerando la dificultad de cada ejercicio.
Se justo pero exigente. Explicale al alumno POR QUE recibe cada nota."""


class GradingService:
    def __init__(self, session: AsyncSession, llm: LLMAdapter) -> None:
        self._session = session
        self._llm = llm

    async def evaluate_activity_submission(
        self, activity_submission_id: uuid.UUID
    ) -> dict:
        """Evaluate ALL exercises in an activity submission with AI.

        Returns dict with general_score, general_feedback, and per-exercise evaluations.
        Does NOT persist — the docente must confirm first.
        """
        stmt = (
            select(ActivitySubmission)
            .where(ActivitySubmission.id == activity_submission_id)
            .options(
                selectinload(ActivitySubmission.submissions).selectinload(Submission.exercise),
                selectinload(ActivitySubmission.student),
            )
        )
        result = await self._session.execute(stmt)
        activity_sub = result.scalar_one_or_none()

        if activity_sub is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(resource="ActivitySubmission", identifier=str(activity_submission_id))

        prompt = self._build_activity_prompt(activity_sub)
        messages = [ChatMessage(role="user", content=prompt)]
        response = await self._llm.complete(
            messages, _GRADING_SYSTEM_PROMPT, max_tokens=2048
        )

        parsed = self._parse_activity_response(response.text, activity_sub)

        logger.info(
            "AI activity grading completed",
            extra={
                "activity_submission_id": str(activity_submission_id),
                "general_score": parsed.get("general_score"),
            },
        )

        return parsed

    async def confirm_activity_grade(
        self,
        activity_submission_id: uuid.UUID,
        general_score: float,
        general_feedback: str,
        exercise_grades: list[dict],
    ) -> ActivitySubmission:
        """Docente confirms the AI grade for the whole activity."""
        stmt = (
            select(ActivitySubmission)
            .where(ActivitySubmission.id == activity_submission_id)
            .options(selectinload(ActivitySubmission.submissions))
        )
        result = await self._session.execute(stmt)
        activity_sub = result.scalar_one_or_none()

        if activity_sub is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(resource="ActivitySubmission", identifier=str(activity_submission_id))

        now = datetime.now(tz=timezone.utc)

        # Update individual exercise grades
        sub_map = {str(s.id): s for s in activity_sub.submissions}
        for eg in exercise_grades:
            sub = sub_map.get(eg["submission_id"])
            if sub:
                sub.score = Decimal(str(round(eg["score"], 2)))
                sub.feedback = eg.get("feedback", "")
                sub.status = SubmissionStatus.evaluated
                sub.evaluated_at = now

        # Update activity-level grade
        activity_sub.total_score = Decimal(str(round(general_score, 2)))
        activity_sub.status = SubmissionStatus.evaluated

        await self._session.flush()
        return activity_sub

    @staticmethod
    def _build_activity_prompt(activity_sub: ActivitySubmission) -> str:
        parts = ["# Actividad enviada por el alumno\n"]

        for i, sub in enumerate(activity_sub.submissions, 1):
            ex = sub.exercise
            parts.append(f"## Ejercicio {i}: {ex.title}")
            parts.append(f"**Enunciado:** {ex.description}")
            if ex.rubric:
                parts.append(f"**Rubrica:** {ex.rubric}")
            diff = ex.difficulty.value if hasattr(ex.difficulty, 'value') else str(ex.difficulty)
            parts.append(f"**Dificultad:** {diff}")
            parts.append(f"**exercise_id:** {ex.id}")
            parts.append(f"**Codigo del alumno:**\n```\n{sub.code}\n```")
            parts.append("")

        parts.append("Evalua TODOS los ejercicios y devuelve el JSON con nota general y por ejercicio.")
        return "\n".join(parts)

    @staticmethod
    def _parse_activity_response(text: str, activity_sub: ActivitySubmission) -> dict:
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)

        try:
            data = json.loads(text.strip())

            exercises = []
            for ex_eval in data.get("exercises", []):
                exercises.append({
                    "exercise_id": str(ex_eval.get("exercise_id", "")),
                    "score": max(0, min(100, float(ex_eval.get("score", 0)))),
                    "feedback": str(ex_eval.get("feedback", "")),
                    "strengths": ex_eval.get("strengths", []),
                    "improvements": ex_eval.get("improvements", []),
                })

            # Map exercise_id to submission_id for frontend
            ex_to_sub = {}
            for sub in activity_sub.submissions:
                ex_to_sub[str(sub.exercise_id)] = str(sub.id)

            for ex in exercises:
                ex["submission_id"] = ex_to_sub.get(ex["exercise_id"], "")
                # Add exercise title
                for sub in activity_sub.submissions:
                    if str(sub.exercise_id) == ex["exercise_id"]:
                        ex["exercise_title"] = sub.exercise.title
                        break

            return {
                "activity_submission_id": str(activity_sub.id),
                "general_score": max(0, min(100, float(data.get("general_score", 0)))),
                "general_feedback": str(data.get("general_feedback", "Sin feedback")),
                "exercises": exercises,
            }

        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Failed to parse activity grading response", extra={"raw": text[:200]})
            return {
                "activity_submission_id": str(activity_sub.id),
                "general_score": 0,
                "general_feedback": text[:500] if text else "Error al evaluar con IA",
                "exercises": [],
            }
