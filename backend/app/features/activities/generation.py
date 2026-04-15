"""Activity generation service — combines RAG + LLM to create activities."""
from __future__ import annotations

import json
import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.llm import get_adapter
from app.core.llm.prompts import ACTIVITY_GENERATION_SYSTEM, ACTIVITY_GENERATION_USER
from app.core.rag.search import search_chunks_by_text
from app.features.activities.services import ActivityService, LLMConfigService
from app.shared.models.activity import Activity
from app.shared.models.exercise import Exercise

logger = logging.getLogger(__name__)


class ActivityGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._llm_config_service = LLMConfigService(session)
        self._activity_service = ActivityService(session)

    async def generate(
        self,
        user_id: uuid.UUID,
        course_id: uuid.UUID,
        prompt: str,
    ) -> Activity:
        # 1. Get docente's LLM config
        config = await self._llm_config_service.get(user_id)
        if config is None:
            raise ValidationError(
                message="No tenes una API key configurada. Anda a Configuracion para agregarla."
            )

        api_key = self._llm_config_service.decrypt_key(config)
        adapter = get_adapter(config.provider.value, api_key, config.model_name)

        # 2. RAG — search relevant chunks
        chunks = await search_chunks_by_text(self._session, prompt, top_k=8)
        context = "\n\n---\n\n".join(
            f"[{c.topic} — {c.source_file}]\n{c.content}" for c in chunks
        )
        if not context:
            context = "(No se encontro material relevante. Genera ejercicios basicos de Python.)"

        # 3. Build prompt
        user_message = ACTIVITY_GENERATION_USER.format(context=context, prompt=prompt)
        messages = [
            {"role": "system", "content": ACTIVITY_GENERATION_SYSTEM},
            {"role": "user", "content": user_message},
        ]

        # 4. Call LLM
        logger.info("Generating activity for user=%s prompt=%r", user_id, prompt[:80])
        try:
            raw_response = await adapter.generate(messages, temperature=0.7, max_tokens=8192)
        except Exception as exc:
            error_msg = str(exc)[:300]
            if "401" in error_msg or "Unauthorized" in error_msg or "auth" in error_msg.lower():
                raise ValidationError(
                    message="Tu API key es invalida o expiro. Revisala en Configuracion."
                ) from exc
            if "429" in error_msg or "rate" in error_msg.lower():
                raise ValidationError(
                    message="Se excedio el limite de requests de tu proveedor. Espera un momento e intenta de nuevo."
                ) from exc
            if "insufficient" in error_msg.lower() or "quota" in error_msg.lower():
                raise ValidationError(
                    message="Tu cuenta no tiene credito suficiente. Revisa tu plan en el proveedor."
                ) from exc
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "ReadTimeout" in error_msg:
                raise ValidationError(
                    message="La IA tardo demasiado en responder. Intenta con menos ejercicios o una instruccion mas corta."
                ) from exc
            raise ValidationError(
                message=f"Error al conectar con el proveedor de IA: {error_msg}"
            ) from exc

        # 5. Parse JSON from response
        parsed = self._parse_response(raw_response)

        # 6. Create Activity + Exercises (draft)
        activity = await self._activity_service.create(
            course_id=course_id,
            created_by=user_id,
            title=parsed.get("title", "Actividad generada"),
            description=parsed.get("description"),
            prompt_used=prompt,
        )

        exercises_data = parsed.get("exercises", [])
        for i, ex_data in enumerate(exercises_data):
            exercise = Exercise(
                course_id=course_id,
                activity_id=activity.id,
                title=ex_data.get("title", f"Ejercicio {i + 1}"),
                description=ex_data.get("description", ""),
                test_cases=ex_data.get("test_cases", {
                    "language": "python",
                    "timeout_ms": 10000,
                    "memory_limit_mb": 128,
                    "cases": [],
                }),
                difficulty=ex_data.get("difficulty", "medium"),
                topic_tags=ex_data.get("topic_tags", []),
                starter_code=ex_data.get("starter_code", ""),
                rubric=ex_data.get("rubric"),
                language="python",
                order_index=i,
                is_active=False,  # Draft — activated on publish
            )
            self._session.add(exercise)

        await self._session.flush()

        # Reload with exercises
        return await self._activity_service.get(activity.id)

    def _parse_response(self, raw: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks and truncation."""
        logger.debug("Raw LLM response length: %d chars", len(raw))

        # Try to find JSON in code block (greedy — get the largest block)
        json_match = re.search(r"```(?:json)?\s*\n(.*)\n```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        # Try to find raw JSON object
        brace_start = raw.find("{")
        brace_end = raw.rfind("}") + 1
        if brace_start >= 0 and brace_end > brace_start:
            raw = raw[brace_start:brace_end]

        # First attempt — clean parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Second attempt — fix truncated JSON by closing open brackets
        truncated = raw.rstrip()
        # Count open brackets
        open_brackets = truncated.count("[") - truncated.count("]")
        open_braces = truncated.count("{") - truncated.count("}")

        if open_brackets > 0 or open_braces > 0:
            # Try to close truncated JSON
            fixed = truncated
            # Remove trailing comma if any
            fixed = fixed.rstrip().rstrip(",")
            fixed += "]" * open_brackets
            fixed += "}" * open_braces
            try:
                result = json.loads(fixed)
                logger.warning("Fixed truncated JSON response (added %d ] and %d })", open_brackets, open_braces)
                return result
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse LLM response as JSON. First 500 chars: %s", raw[:500])
        raise ValidationError(
            message="La IA genero una respuesta incompleta (posiblemente se corto). Intenta con menos ejercicios o una instruccion mas corta."
        )
