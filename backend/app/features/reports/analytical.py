from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cognitive.models import CognitiveEvent, CognitiveSession
from app.features.evaluation.models import CognitiveMetrics
from app.shared.models.exercise import Exercise


class InsufficientDataError(Exception):
    pass


def _decimal_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _avg(values: list[Decimal | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


async def build_structured_analysis(
    db: AsyncSession,
    student_id: uuid.UUID,
    activity_id: uuid.UUID,
    student_name: str | None = None,
    activity_title: str | None = None,
) -> dict[str, Any]:
    """Build the StructuredAnalysis JSON for a student+activity pair.

    Raises InsufficientDataError if no closed sessions exist.
    """
    exercise_ids_result = await db.execute(
        select(Exercise.id).where(Exercise.activity_id == activity_id)
    )
    exercise_ids = [row[0] for row in exercise_ids_result.all()]

    if not exercise_ids:
        raise InsufficientDataError("La actividad no tiene ejercicios asociados")

    sessions_result = await db.execute(
        select(CognitiveSession).where(
            CognitiveSession.student_id == student_id,
            CognitiveSession.exercise_id.in_(exercise_ids),
            CognitiveSession.status == "closed",
        )
    )
    sessions = list(sessions_result.scalars().all())

    if not sessions:
        raise InsufficientDataError("No hay sesiones cerradas para analizar")

    session_ids = [s.id for s in sessions]

    metrics_result = await db.execute(
        select(CognitiveMetrics).where(
            CognitiveMetrics.session_id.in_(session_ids)
        )
    )
    all_metrics = list(metrics_result.scalars().all())

    events_result = await db.execute(
        select(CognitiveEvent)
        .where(CognitiveEvent.session_id.in_(session_ids))
        .order_by(CognitiveEvent.session_id, CognitiveEvent.sequence_number)
    )
    all_events = list(events_result.scalars().all())

    overall_scores = {
        "n1_avg": _avg([m.n1_comprehension_score for m in all_metrics]),
        "n2_avg": _avg([m.n2_strategy_score for m in all_metrics]),
        "n3_avg": _avg([m.n3_validation_score for m in all_metrics]),
        "n4_avg": _avg([m.n4_ai_interaction_score for m in all_metrics]),
        "qe_avg": _avg([m.qe_score for m in all_metrics]),
    }

    risk_levels = [m.risk_level for m in all_metrics if m.risk_level]
    risk_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    overall_risk = min(risk_levels, key=lambda r: risk_priority.get(r, 99)) if risk_levels else None

    patterns = _detect_patterns(all_events, all_metrics, sessions)
    strengths = _extract_strengths(overall_scores, all_metrics)
    weaknesses = _extract_weaknesses(overall_scores, all_metrics)
    evolution = _compute_evolution(all_metrics, sessions)
    anomalies = _extract_anomalies(all_metrics)

    analysis: dict[str, Any] = {
        "student_id": str(student_id),
        "activity_id": str(activity_id),
        "activity_title": activity_title or "",
        "student_name": student_name or "",
        "sessions_analyzed": len(sessions),
        "overall_scores": overall_scores,
        "risk_level": overall_risk,
        "patterns": patterns,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "evolution": evolution,
        "anomalies": anomalies,
    }

    return analysis


def compute_data_hash(analysis: dict[str, Any]) -> str:
    canonical = json.dumps(analysis, sort_keys=True, default=_decimal_default)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _detect_patterns(
    events: list[CognitiveEvent],
    metrics: list[CognitiveMetrics],
    sessions: list[CognitiveSession],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []

    events_by_session: dict[uuid.UUID, list[CognitiveEvent]] = {}
    for e in events:
        events_by_session.setdefault(e.session_id, []).append(e)

    for sid, session_events in events_by_session.items():
        tutor_questions = [e for e in session_events if e.event_type == "tutor.question_asked"]
        code_edits = [e for e in session_events if e.event_type in ("code.edit", "code.snapshot")]

        if len(tutor_questions) > 8 and code_edits:
            first_code = code_edits[0].sequence_number
            questions_before_code = [q for q in tutor_questions if q.sequence_number < first_code]
            if len(questions_before_code) > 6:
                patterns.append({
                    "type": "high_ai_dependency",
                    "severity": "warning",
                    "evidence": f"Preguntó al tutor {len(questions_before_code)} veces antes de escribir código",
                    "metric_ref": f"total tutor questions: {len(tutor_questions)}",
                })

        submissions = [e for e in session_events if e.event_type == "code.submission"]
        runs = [e for e in session_events if e.event_type in ("code.run", "test.run")]
        if submissions and not runs:
            patterns.append({
                "type": "low_validation",
                "severity": "warning",
                "evidence": "Envió código sin ejecutarlo ni testearlo previamente",
                "metric_ref": f"submissions: {len(submissions)}, runs previos: 0",
            })

        tutor_copies = [e for e in session_events if e.event_type == "code.accepted_from_tutor"]
        if len(tutor_copies) >= 3:
            patterns.append({
                "type": "tutor_copy_paste",
                "severity": "warning",
                "evidence": f"Copió código del tutor {len(tutor_copies)} veces sin modificación",
                "metric_ref": f"code.accepted_from_tutor events: {len(tutor_copies)}",
            })

    avg_dep = _avg([m.dependency_score for m in metrics])
    if avg_dep is not None and avg_dep > 0.6:
        patterns.append({
            "type": "overall_high_dependency",
            "severity": "critical" if avg_dep > 0.8 else "warning",
            "evidence": f"Dependency score promedio: {avg_dep:.2f} (umbral: 0.6)",
            "metric_ref": f"dependency_score avg: {avg_dep}",
        })

    return patterns


def _extract_strengths(
    scores: dict[str, float | None],
    metrics: list[CognitiveMetrics],
) -> list[dict[str, str]]:
    strengths: list[dict[str, str]] = []
    dimension_map = {
        "n1_avg": ("N1 — Comprensión", "Demuestra buena comprensión de los problemas"),
        "n2_avg": ("N2 — Estrategia", "Planifica bien sus soluciones"),
        "n3_avg": ("N3 — Validación", "Verifica y corrige su código activamente"),
        "n4_avg": ("N4 — Interacción IA", "Usa la IA de forma crítica y productiva"),
        "qe_avg": ("Qe — Calidad Epistémica", "Calidad epistémica alta en sus interacciones"),
    }

    for key, (dimension, description) in dimension_map.items():
        val = scores.get(key)
        if val is not None and val >= 70:
            strengths.append({
                "dimension": dimension,
                "description": description,
                "evidence": f"Promedio: {val:.1f}/100 en {len(metrics)} sesiones",
            })

    return strengths


def _extract_weaknesses(
    scores: dict[str, float | None],
    metrics: list[CognitiveMetrics],
) -> list[dict[str, str]]:
    weaknesses: list[dict[str, str]] = []
    dimension_map = {
        "n1_avg": ("N1 — Comprensión", "Dificultad para comprender los enunciados"),
        "n2_avg": ("N2 — Estrategia", "No planifica antes de codificar"),
        "n3_avg": ("N3 — Validación", "No verifica ni testea su código"),
        "n4_avg": ("N4 — Interacción IA", "Usa la IA como oráculo, sin pensamiento crítico"),
        "qe_avg": ("Qe — Calidad Epistémica", "Calidad epistémica baja en interacciones con IA"),
    }

    for key, (dimension, description) in dimension_map.items():
        val = scores.get(key)
        if val is not None and val < 50:
            weaknesses.append({
                "dimension": dimension,
                "description": description,
                "evidence": f"Promedio: {val:.1f}/100 en {len(metrics)} sesiones",
            })

    return weaknesses


def _compute_evolution(
    metrics: list[CognitiveMetrics],
    sessions: list[CognitiveSession],
) -> dict[str, Any]:
    if len(metrics) < 2:
        return {"trend": "insufficient_data", "detail": "Se necesitan al menos 2 sesiones para ver evolución"}

    session_order = {s.id: s.started_at for s in sessions}
    sorted_metrics = sorted(metrics, key=lambda m: session_order.get(m.session_id, m.created_at))

    first = sorted_metrics[0]
    last = sorted_metrics[-1]

    changes: list[str] = []
    for attr, label in [
        ("n1_comprehension_score", "N1"),
        ("n2_strategy_score", "N2"),
        ("n3_validation_score", "N3"),
        ("n4_ai_interaction_score", "N4"),
    ]:
        v_first = getattr(first, attr)
        v_last = getattr(last, attr)
        if v_first is not None and v_last is not None:
            diff = float(v_last) - float(v_first)
            if abs(diff) >= 10:
                direction = "subió" if diff > 0 else "bajó"
                changes.append(f"{label} {direction} de {float(v_first):.0f} a {float(v_last):.0f}")

    if not changes:
        trend = "stable"
        detail = "Sin cambios significativos entre sesiones"
    else:
        improving = sum(1 for c in changes if "subió" in c)
        declining = sum(1 for c in changes if "bajó" in c)
        if improving > declining:
            trend = "improving"
        elif declining > improving:
            trend = "declining"
        else:
            trend = "mixed"
        detail = "; ".join(changes)

    return {"trend": trend, "detail": detail}


def _extract_anomalies(metrics: list[CognitiveMetrics]) -> list[dict[str, str]]:
    anomalies: list[dict[str, str]] = []
    for m in metrics:
        if m.coherence_anomalies and isinstance(m.coherence_anomalies, dict):
            raw_anomalies = m.coherence_anomalies.get("anomalies", [])
            for a in raw_anomalies:
                if isinstance(a, str):
                    anomalies.append({"type": a, "session_id": str(m.session_id)})
                elif isinstance(a, dict):
                    anomalies.append({
                        "type": a.get("type", "unknown"),
                        "detail": a.get("detail", ""),
                        "session_id": str(m.session_id),
                    })
    return anomalies
