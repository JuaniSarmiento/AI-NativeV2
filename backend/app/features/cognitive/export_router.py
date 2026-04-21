from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.auth.dependencies import require_role
from app.features.cognitive.models import CognitiveEvent, CognitiveSession
from app.features.cognitive.pseudonymize import pseudonymize_student_id, scrub_payload
from app.features.evaluation.models import CognitiveMetrics
from app.shared.db.session import get_async_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/export", tags=["admin-export"])


@router.get("/cognitive-data")
async def export_cognitive_data(
    session: AsyncSession = Depends(get_async_session),
    _user=require_role("admin"),
    commission_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    student_id: uuid.UUID | None = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    pseudonymize: bool = Query(False),
) -> Any:
    """Export cognitive session data for research analysis.

    Returns closed sessions with their N1-N4 metrics and CTR event lists.
    When ``pseudonymize=true`` student IDs are SHA-256 hashed and sensitive
    payload fields are scrubbed before the response is sent.

    Requires: admin role.
    """
    stmt = (
        select(CognitiveSession)
        .where(CognitiveSession.status == "closed")
        .order_by(CognitiveSession.closed_at.desc())
    )

    if commission_id is not None:
        stmt = stmt.where(CognitiveSession.commission_id == commission_id)
    if student_id is not None:
        stmt = stmt.where(CognitiveSession.student_id == student_id)
    if date_from is not None:
        stmt = stmt.where(
            CognitiveSession.closed_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to is not None:
        stmt = stmt.where(
            CognitiveSession.closed_at <= datetime.combine(date_to, datetime.max.time())
        )

    result = await session.execute(stmt)
    sessions = list(result.scalars().all())

    export_data: list[dict[str, Any]] = []

    for cs in sessions:
        # Fetch metrics (1:1)
        metrics_result = await session.execute(
            select(CognitiveMetrics).where(CognitiveMetrics.session_id == cs.id)
        )
        metrics = metrics_result.scalar_one_or_none()

        # Fetch events ordered by sequence
        events_result = await session.execute(
            select(CognitiveEvent)
            .where(CognitiveEvent.session_id == cs.id)
            .order_by(CognitiveEvent.sequence_number)
        )
        events = list(events_result.scalars().all())

        sid = str(cs.student_id)
        if pseudonymize:
            sid = pseudonymize_student_id(sid)

        session_data: dict[str, Any] = {
            "session_id": str(cs.id),
            "student_id": sid,
            "exercise_id": str(cs.exercise_id),
            "commission_id": str(cs.commission_id),
            "started_at": cs.started_at.isoformat() if cs.started_at else None,
            "closed_at": cs.closed_at.isoformat() if cs.closed_at else None,
        }

        if metrics is not None:
            session_data.update({
                "n1_score": float(metrics.n1_comprehension_score) if metrics.n1_comprehension_score is not None else None,
                "n2_score": float(metrics.n2_strategy_score) if metrics.n2_strategy_score is not None else None,
                "n3_score": float(metrics.n3_validation_score) if metrics.n3_validation_score is not None else None,
                "n4_score": float(metrics.n4_ai_interaction_score) if metrics.n4_ai_interaction_score is not None else None,
                "qe_score": float(metrics.qe_score) if metrics.qe_score is not None else None,
                "temporal_coherence": float(metrics.temporal_coherence_score) if metrics.temporal_coherence_score is not None else None,
                "code_discourse": float(metrics.code_discourse_score) if metrics.code_discourse_score is not None else None,
                "inter_iteration": float(metrics.inter_iteration_score) if metrics.inter_iteration_score is not None else None,
            })

        event_list: list[dict[str, Any]] = []
        for ev in events:
            ev_data: dict[str, Any] = {
                "event_type": ev.event_type,
                "sequence_number": ev.sequence_number,
                "n4_level": ev.n4_level,
                "created_at": ev.created_at.isoformat(),
            }
            if pseudonymize:
                ev_data["payload"] = scrub_payload(ev.payload) if ev.payload else {}
            else:
                ev_data["payload"] = ev.payload or {}
            event_list.append(ev_data)

        session_data["events"] = event_list
        export_data.append(session_data)

    meta: dict[str, Any] = {
        "total_sessions": len(export_data),
        "is_pseudonymized": pseudonymize,
        "exported_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        "Research export generated",
        extra={
            "total_sessions": len(export_data),
            "pseudonymized": pseudonymize,
            "format": format,
        },
    )

    if format == "csv":
        return _build_csv_response(export_data, meta)

    return {"status": "ok", "meta": meta, "data": export_data}


def _build_csv_response(
    data: list[dict[str, Any]],
    meta: dict[str, Any],
) -> StreamingResponse:
    """Build a streaming CSV response — one row per session, events as count.

    Event-level detail is intentionally omitted from CSV to keep the file
    flat and importable into standard statistical tools (R, SPSS, Excel).
    Use the JSON format for full event-level analysis.
    """
    output = io.StringIO()

    if not data:
        output.write("No data\n")
    else:
        fields = [
            "session_id",
            "student_id",
            "exercise_id",
            "commission_id",
            "started_at",
            "closed_at",
            "n1_score",
            "n2_score",
            "n3_score",
            "n4_score",
            "qe_score",
            "temporal_coherence",
            "code_discourse",
            "inter_iteration",
            "event_count",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            csv_row: dict[str, Any] = {k: row.get(k) for k in fields if k != "event_count"}
            csv_row["event_count"] = len(row.get("events", []))
            writer.writerow(csv_row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=cognitive-data.csv",
            "X-Total-Sessions": str(meta["total_sessions"]),
            "X-Pseudonymized": str(meta["is_pseudonymized"]).lower(),
        },
    )
