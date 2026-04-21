from __future__ import annotations

import difflib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.features.cognitive.ctr_builder import (
    compute_event_hash,
    compute_genesis_hash,
    verify_chain,
)
from app.features.cognitive.models import CognitiveEvent, CognitiveSession, SessionStatus
from app.features.cognitive.repositories import (
    CognitiveEventRepository,
    CognitiveSessionRepository,
)
from app.features.evaluation.models import CognitiveMetrics, ReasoningRecord
from app.features.evaluation.repositories import (
    CognitiveMetricsRepository,
    ReasoningRecordRepository,
)
from app.features.evaluation.rubric import load_rubric
from app.features.evaluation.service import MetricsEngine
from app.features.submissions.models import CodeSnapshot
from app.features.tutor.repositories import TutorInteractionRepository

logger = get_logger(__name__)


class CognitiveService:
    """Domain service for the Cognitive Trace Record (CTR).

    Owns all business logic for session lifecycle and hash-chained event
    appending. Never imports from FastAPI — it is pure Python domain code.

    The caller (router or background worker) owns the DB transaction:
    this service only calls session.flush() to make IDs visible, never commit().

    CRITICAL INVARIANT: cognitive_events are IMMUTABLE. This service never
    modifies or deletes events once created.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = CognitiveSessionRepository(session)
        self._event_repo = CognitiveEventRepository(session)
        self._metrics_repo = CognitiveMetricsRepository(session)
        self._reasoning_repo = ReasoningRecordRepository(session)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def get_or_create_session(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        commission_id: uuid.UUID,
    ) -> CognitiveSession:
        """Return the existing open session or create a new one.

        If an open session already exists for (student_id, exercise_id),
        it is returned unchanged. Otherwise a new session is created and
        its genesis_hash is computed and persisted.

        Args:
            student_id: UUID of the student.
            exercise_id: UUID of the exercise.
            commission_id: UUID of the commission (denormalised).

        Returns:
            The open CognitiveSession.
        """
        existing = await self._session_repo.get_open_session(student_id, exercise_id)
        if existing is not None:
            logger.debug(
                "Returning existing open cognitive session",
                extra={
                    "session_id": str(existing.id),
                    "student_id": str(student_id),
                    "exercise_id": str(exercise_id),
                },
            )
            return existing

        cognitive_session = CognitiveSession(
            student_id=student_id,
            exercise_id=exercise_id,
            commission_id=commission_id,
            status="open",
        )
        self._session.add(cognitive_session)
        await self._session.flush()  # populate id + started_at from DB defaults

        # Compute genesis hash — requires the server-assigned id and started_at
        cognitive_session.genesis_hash = compute_genesis_hash(
            str(cognitive_session.id),
            cognitive_session.started_at,
        )
        await self._session.flush()

        logger.info(
            "Cognitive session created",
            extra={
                "session_id": str(cognitive_session.id),
                "student_id": str(student_id),
                "exercise_id": str(exercise_id),
                "genesis_hash": cognitive_session.genesis_hash,
            },
        )
        return cognitive_session

    async def close_session(self, session_id: uuid.UUID) -> CognitiveSession:
        """Close an open session by setting closed_at, session_hash, and status.

        The session_hash is the event_hash of the last event in the chain,
        or genesis_hash if no events were ever appended. This seals the chain
        so any future tampering can be detected by comparing session_hash with
        a fresh verify_chain() run.

        Raises:
            NotFoundError: If the session does not exist.
            ValidationError: If the session is already closed or invalidated.
        """
        cognitive_session = await self._session_repo.get_session_with_events(session_id)
        if cognitive_session is None:
            raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

        if cognitive_session.status != "open":
            raise ValidationError(
                message=f"Session {session_id} is already {cognitive_session.status.value}.",
                code="SESSION_NOT_OPEN",
            )

        last_event = await self._event_repo.get_last_event(session_id)
        cognitive_session.closed_at = datetime.now(tz=timezone.utc)
        cognitive_session.session_hash = (
            last_event.event_hash if last_event is not None else cognitive_session.genesis_hash
        )
        cognitive_session.status = "closed"
        await self._session.flush()

        # --- Compute and persist cognitive metrics ---
        try:
            events = await self._event_repo.get_events_by_session(session_id)
            rubric = load_rubric()
            engine = MetricsEngine(rubric)
            result = engine.compute(cognitive_session, events)

            metrics_data = result.metrics.as_dict()
            metrics_obj = CognitiveMetrics(
                session_id=cognitive_session.id,
                **metrics_data,
            )
            self._session.add(metrics_obj)

            # Compute coherence scores (EPIC-20 Fase C)
            from app.features.evaluation.coherence import CoherenceEngine
            coherence_engine = CoherenceEngine(rubric)
            chat_repo = TutorInteractionRepository(self._session)
            chat_msgs = await chat_repo.get_messages_for_cognitive_session(
                student_id=cognitive_session.student_id,
                exercise_id=cognitive_session.exercise_id,
                started_at=cognitive_session.started_at,
                closed_at=cognitive_session.closed_at,
                limit=200,
            )
            _, code_entries = await self.get_code_evolution(session_id, limit=200)

            # B4: LLM-based code-discourse coherence — attempt before falling back to Jaccard
            llm_discourse_score = None
            try:
                from app.features.evaluation.prompts.coherence_evaluation import (
                    COHERENCE_SYSTEM_PROMPT,
                    build_coherence_prompt,
                )
                from app.features.tutor.llm_adapter import ChatMessage as LLMChatMessage
                from app.features.tutor.llm_adapter import MistralAdapter

                if chat_msgs and code_entries:
                    adapter = MistralAdapter()
                    chat_texts = [
                        getattr(m, "content", "")
                        for m in chat_msgs
                        if getattr(m, "role", "") == "user"
                    ]
                    last_code = code_entries[-1].get("code", "") if code_entries else ""
                    if chat_texts and last_code:
                        user_prompt = build_coherence_prompt(chat_texts[-10:], last_code)
                        result_llm = await adapter.complete(
                            messages=[LLMChatMessage(role="user", content=user_prompt)],
                            system_prompt=COHERENCE_SYSTEM_PROMPT,
                            max_tokens=200,
                        )
                        import json as _json
                        from decimal import Decimal as _Decimal

                        parsed = _json.loads(result_llm.text)
                        llm_discourse_score = _Decimal(str(parsed["score"]))
                        logger.info(
                            "LLM coherence evaluation succeeded",
                            extra={
                                "session_id": str(session_id),
                                "llm_score": str(llm_discourse_score),
                                "reasoning": parsed.get("reasoning", ""),
                            },
                        )
            except Exception:
                logger.warning(
                    "LLM coherence evaluation failed — falling back to Jaccard",
                    extra={"session_id": str(session_id)},
                    exc_info=True,
                )

            coherence = coherence_engine.compute(
                events,
                chat_msgs,
                code_entries,
                llm_discourse_score=llm_discourse_score,
            )
            metrics_obj.temporal_coherence_score = coherence.temporal_coherence_score
            metrics_obj.code_discourse_score = coherence.code_discourse_score
            metrics_obj.inter_iteration_score = coherence.inter_iteration_score
            metrics_obj.coherence_anomalies = coherence.coherence_anomalies
            metrics_obj.prompt_type_distribution = coherence.prompt_type_distribution

            # B5: Cross-session inter-iteration coherence
            try:
                from app.features.evaluation.coherence import SessionPattern

                historical = await self._session_repo.get_recent_closed_sessions(
                    cognitive_session.student_id,
                    limit=5,
                    exclude_session_id=session_id,
                )
                if historical:
                    current_pattern = self._extract_session_pattern(events, metrics_obj)
                    hist_patterns: list[SessionPattern] = []
                    for hs in historical:
                        hs_metrics = await self._metrics_repo.get_by_session(hs.id)
                        hs_events = await self._event_repo.get_events_by_session(hs.id)
                        if hs_metrics is not None:
                            hist_patterns.append(
                                self._extract_session_pattern(hs_events, hs_metrics)
                            )
                    if hist_patterns:
                        cross_score = coherence_engine.compute_cross_session(
                            current_pattern, hist_patterns
                        )
                        if cross_score is not None:
                            metrics_obj.inter_iteration_score = cross_score
                            logger.info(
                                "Cross-session coherence computed",
                                extra={
                                    "session_id": str(session_id),
                                    "cross_session_score": str(cross_score),
                                    "historical_sessions": len(hist_patterns),
                                },
                            )
            except Exception:
                logger.warning(
                    "Cross-session coherence failed",
                    extra={"session_id": str(session_id)},
                    exc_info=True,
                )

            # Set n4_final_score on the session
            cognitive_session.n4_final_score = result.evaluation_profile
            await self._session.flush()

            # Persist the reasoning record (hash chain continuation)
            previous_hash = cognitive_session.session_hash or cognitive_session.genesis_hash or ""
            rr_data = engine.create_reasoning_record(
                session_id=cognitive_session.id,
                details=result.reasoning_details,
                previous_hash=previous_hash,
                created_at=result.metrics.computed_at,
            )
            reasoning_record = ReasoningRecord(**rr_data)
            self._session.add(reasoning_record)
            await self._session.flush()

            logger.info(
                "Cognitive metrics computed and persisted",
                extra={
                    "session_id": str(session_id),
                    "risk_level": result.metrics.risk_level,
                    "n1": str(result.metrics.n1_comprehension_score),
                    "n4": str(result.metrics.n4_ai_interaction_score),
                },
            )
        except Exception:
            logger.exception(
                "Failed to compute cognitive metrics — session closed but metrics missing",
                extra={"session_id": str(session_id)},
            )
            # Do NOT re-raise: closing the session is the critical operation.
            # Metrics failure must not roll back the session close.

        logger.info(
            "Cognitive session closed",
            extra={
                "session_id": str(session_id),
                "session_hash": cognitive_session.session_hash,
            },
        )
        return cognitive_session

    # ------------------------------------------------------------------
    # Event appending (IMMUTABLE — no updates after flush)
    # ------------------------------------------------------------------

    async def add_event(
        self,
        session: CognitiveSession,
        event_type: str,
        n4_level: int | None,
        payload: dict,  # type: ignore[type-arg]
        prompt_hash: str = "",
    ) -> CognitiveEvent:
        """Append an immutable event to the hash chain of the given session.

        The new event's previous_hash is the event_hash of the last event
        (or genesis_hash if this is the first event). The event_hash is
        computed at creation time and never modified afterwards.

        n4_level is injected into the payload under the key "n4_level" so
        downstream consumers can query the level without re-classifying.

        prompt_hash, when provided, is included in the hash computation (V2
        formula) and stored in the enriched payload for future chain verification.

        Raises:
            ValidationError: If the session is not open.
        """
        if session.status != "open":
            raise ValidationError(
                message=f"Cannot add event to session {session.id}: status is {session.status.value}.",
                code="SESSION_NOT_OPEN",
            )

        last_event = await self._event_repo.get_last_event(session.id)
        previous_hash = (
            last_event.event_hash if last_event is not None else session.genesis_hash
        )
        if previous_hash is None:
            # Should never happen — genesis_hash is set during get_or_create_session
            raise ValidationError(
                message=f"Session {session.id} has no genesis_hash — cannot compute event hash.",
                code="MISSING_GENESIS_HASH",
            )
        sequence = (last_event.sequence_number + 1) if last_event is not None else 1

        now = datetime.now(tz=timezone.utc)

        # Enrich payload with classifier metadata
        enriched_payload = {**payload}
        if n4_level is not None:
            enriched_payload["n4_level"] = n4_level
        if prompt_hash:
            enriched_payload["prompt_hash"] = prompt_hash

        event_hash = compute_event_hash(
            previous_hash, event_type, enriched_payload, now, prompt_hash=prompt_hash
        )

        event = CognitiveEvent(
            session_id=session.id,
            event_type=event_type,
            sequence_number=sequence,
            payload=enriched_payload,
            n4_level=n4_level,
            previous_hash=previous_hash,
            event_hash=event_hash,
            created_at=now,
        )
        self._session.add(event)
        await self._session.flush()

        logger.debug(
            "Cognitive event appended",
            extra={
                "event_id": str(event.id),
                "session_id": str(session.id),
                "event_type": event_type,
                "sequence_number": sequence,
                "n4_level": n4_level,
            },
        )
        return event

    # ------------------------------------------------------------------
    # Chain verification
    # ------------------------------------------------------------------

    async def verify_session(self, session_id: uuid.UUID) -> dict:  # type: ignore[type-arg]
        """Verify the hash chain integrity of a session.

        Recalculates all event hashes from genesis_hash forward and
        compares them with the stored values.

        Raises:
            NotFoundError: If the session does not exist.

        Returns:
            dict from ctr_builder.verify_chain() with keys:
              valid, events_checked, failed_at_sequence, expected_hash, actual_hash.
        """
        cognitive_session = await self._session_repo.get_session_with_events(session_id)
        if cognitive_session is None:
            raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

        if cognitive_session.genesis_hash is None:
            return {
                "valid": False,
                "events_checked": None,
                "failed_at_sequence": None,
                "expected_hash": None,
                "actual_hash": None,
            }

        events = await self._event_repo.get_events_by_session(session_id)
        chain_version = getattr(cognitive_session, "chain_version", 1)
        return verify_chain(
            cognitive_session.genesis_hash, events, chain_version=chain_version
        )

    # ------------------------------------------------------------------
    # Trace / Timeline / Code Evolution (EPIC-16)
    # ------------------------------------------------------------------

    async def get_timeline(
        self,
        session_id: uuid.UUID,
    ) -> tuple[CognitiveSession, list[CognitiveEvent]]:
        """Return session + its events in chronological order."""
        cognitive_session = await self._session_repo.get_session_with_events(session_id)
        if cognitive_session is None:
            raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

        raw_events = getattr(cognitive_session, "events", []) or []
        events: list[CognitiveEvent] = list(raw_events)
        return cognitive_session, events

    def _compute_unified_diff(
        self,
        previous_code: str,
        current_code: str,
        *,
        from_label: str,
        to_label: str,
        max_lines: int = 5000,
        max_chars: int = 200_000,
    ) -> str | None:
        diff_iter = difflib.unified_diff(
            previous_code.splitlines(),
            current_code.splitlines(),
            fromfile=from_label,
            tofile=to_label,
            lineterm="",
        )
        lines = list(diff_iter)
        if not lines:
            return None

        if len(lines) > max_lines:
            lines = lines[:max_lines] + ["... [diff truncated]"]

        diff_text = "\n".join(lines)
        if len(diff_text) > max_chars:
            diff_text = diff_text[:max_chars] + "\n... [diff truncated]"
        return diff_text

    async def get_code_evolution(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 200,
    ) -> tuple[CognitiveSession, list[dict[str, Any]]]:
        """Return code snapshots for the session with diffs between consecutive snapshots."""
        cognitive_session, _events = await self.get_timeline(session_id)

        end_at = cognitive_session.closed_at or datetime.now(tz=timezone.utc)
        stmt = (
            select(CodeSnapshot)
            .where(
                CodeSnapshot.student_id == cognitive_session.student_id,
                CodeSnapshot.exercise_id == cognitive_session.exercise_id,
                CodeSnapshot.snapshot_at >= cognitive_session.started_at,
                CodeSnapshot.snapshot_at <= end_at,
            )
            .order_by(asc(CodeSnapshot.snapshot_at))
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        snapshots: list[CodeSnapshot] = list(rows)

        entries: list[dict[str, Any]] = []
        prev: CodeSnapshot | None = None
        for snap in snapshots:
            diff_text = None
            if prev is not None:
                diff_text = self._compute_unified_diff(
                    prev.code,
                    snap.code,
                    from_label=str(prev.id),
                    to_label=str(snap.id),
                )

            entries.append(
                {
                    "snapshot_id": str(snap.id),
                    "code": snap.code,
                    "snapshot_at": snap.snapshot_at,
                    "previous_snapshot_id": str(prev.id) if prev is not None else None,
                    "previous_snapshot_at": prev.snapshot_at if prev is not None else None,
                    "diff_unified": diff_text,
                }
            )
            prev = snap

        return cognitive_session, entries

    async def get_trace(
        self,
        session_id: uuid.UUID,
        *,
        snapshots_limit: int = 200,
        messages_limit: int = 200,
    ) -> dict[str, Any]:
        """Return the full trace bundle used by the docente UI."""
        cognitive_session, events = await self.get_timeline(session_id)

        # Metrics are only present once the session has been closed.
        metrics = await self._metrics_repo.get_by_session(session_id)

        # Chat messages are stored in operational.tutor_interactions.
        # The tutor uses its own session_id (not cognitive_session.id), so we
        # correlate by student_id + exercise_id + time window.
        chat_repo = TutorInteractionRepository(self._session)
        chat = await chat_repo.get_messages_for_cognitive_session(
            student_id=cognitive_session.student_id,
            exercise_id=cognitive_session.exercise_id,
            started_at=cognitive_session.started_at,
            closed_at=cognitive_session.closed_at,
            limit=messages_limit,
        )

        # Snapshots are stored in operational.code_snapshots.
        _session2, code_evolution = await self.get_code_evolution(
            session_id, limit=snapshots_limit
        )

        chain_version = getattr(cognitive_session, "chain_version", 1)
        verification = (
            verify_chain(
                cognitive_session.genesis_hash, events, chain_version=chain_version
            )
            if cognitive_session.genesis_hash is not None
            else None
        )

        return {
            "session": cognitive_session,
            "events": events,
            "code_evolution": code_evolution,
            "chat": chat,
            "metrics": metrics,
            "verification": verification,
        }

    # ------------------------------------------------------------------
    # B5 — Session pattern extraction helper
    # ------------------------------------------------------------------

    def _extract_session_pattern(
        self,
        events: list[Any],
        metrics: Any,
    ) -> "SessionPattern":
        """Extract a SessionPattern from a session's events and metrics.

        This is a pure helper (no I/O) used both for the current session
        and for historical sessions during cross-session scoring.

        Args:
            events:  List of CognitiveEvent ORM instances ordered by
                     sequence_number ASC.
            metrics: CognitiveMetrics ORM instance (may be partially
                     populated for the current session).

        Returns:
            SessionPattern with normalised ratios.
        """
        from app.features.evaluation.coherence import SessionPattern

        total = len(events)

        # N1 ratio: events flagged at n4_level == 1 / total events
        n1_count = sum(1 for e in events if getattr(e, "n4_level", None) == 1)
        n1_ratio = n1_count / total if total > 0 else 0.0

        # N3 ratio: events flagged at n4_level == 3 / total events
        n3_count = sum(1 for e in events if getattr(e, "n4_level", None) == 3)
        n3_ratio = n3_count / total if total > 0 else 0.0

        # Exploratory prompt ratio
        tutor_events = [e for e in events if e.event_type == "tutor.question_asked"]
        if tutor_events:
            exploratory_count = sum(
                1
                for e in tutor_events
                if isinstance(e.payload, dict) and e.payload.get("prompt_type") == "exploratory"
            )
            exploratory_prompt_ratio = exploratory_count / len(tutor_events)
        else:
            exploratory_prompt_ratio = 0.0

        # Post-tutor verification: any code.run after a tutor.response_received
        tutor_resp_events = [e for e in events if e.event_type == "tutor.response_received"]
        run_events = [e for e in events if e.event_type == "code.run"]
        has_post_tutor_verification = False
        if tutor_resp_events and run_events:
            resp_seqs = [getattr(e, "sequence_number", 0) for e in tutor_resp_events]
            run_seqs = [getattr(e, "sequence_number", 0) for e in run_events]
            has_post_tutor_verification = any(
                rs > rsp for rs in run_seqs for rsp in resp_seqs
            )

        # Qe score from metrics (may be Decimal or None)
        qe_raw = getattr(metrics, "qe_score", None)
        qe_score = float(qe_raw) if qe_raw is not None else None

        return SessionPattern(
            n1_ratio=n1_ratio,
            n3_ratio=n3_ratio,
            exploratory_prompt_ratio=exploratory_prompt_ratio,
            has_post_tutor_verification=has_post_tutor_verification,
            qe_score=qe_score,
        )

    # ------------------------------------------------------------------
    # Stale session cleanup
    # ------------------------------------------------------------------

    async def close_stale_sessions(self, timeout_minutes: int = 30) -> int:
        """Close all open sessions with no activity for longer than timeout_minutes.

        Returns the number of sessions that were closed.
        """
        stale = await self._session_repo.get_stale_sessions(timeout_minutes)
        closed_count = 0
        for s in stale:
            try:
                await self.close_session(s.id)
                closed_count += 1
            except Exception:
                logger.exception(
                    "Failed to close stale session",
                    extra={"session_id": str(s.id)},
                )
        if closed_count:
            logger.info(
                "Stale sessions closed",
                extra={"count": closed_count, "timeout_minutes": timeout_minutes},
            )
        return closed_count
