from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.core.llm import LLMAdapter


SYSTEM_PROMPT = """\
Sos un asistente pedagógico que genera informes cognitivos para docentes universitarios \
de programación. Recibís un análisis estructurado (JSON) del proceso cognitivo de un alumno \
en una actividad y debés generar un informe en Markdown en español.

REGLAS ESTRICTAS:
1. SOLO podés citar datos, métricas y evidencia que estén PRESENTES en el JSON de entrada.
2. NUNCA inventés datos, scores, citas de chat, o evidencia que no aparezca en el input.
3. Si un campo es null o está vacío, decí "sin datos suficientes", no inventés un valor.
4. Usá un tono objetivo, profesional y pedagógico. No uses jerga informal.
5. No menciones que recibiste un JSON. Escribí como si fuera tu propio análisis.

ESTRUCTURA OBLIGATORIA del informe (usá estos headers exactos):

## Resumen Ejecutivo
2-3 oraciones con la evaluación general del alumno en la actividad.

## Fortalezas
Lista con viñetas. Cada fortaleza con su evidencia concreta del JSON.

## Áreas de Mejora
Lista con viñetas. Cada área con evidencia y por qué es importante mejorarla.

## Evolución Observada
Descripción de cómo cambió el rendimiento entre sesiones (si hay datos). Si no hay evolución, indicalo.

## Recomendaciones Pedagógicas
3-5 recomendaciones concretas y accionables para el docente sobre cómo guiar al alumno.\
"""


def _decimal_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


async def generate_narrative(
    adapter: LLMAdapter,
    structured_analysis: dict[str, Any],
) -> str:
    analysis_json = json.dumps(structured_analysis, indent=2, ensure_ascii=False, default=_decimal_default)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Generá el informe cognitivo para este alumno:\n\n```json\n{analysis_json}\n```"},
    ]

    return await adapter.generate(messages, temperature=0.3, max_tokens=2048)
