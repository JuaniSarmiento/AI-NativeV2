from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Lowercase and split on non-word boundaries, discard short tokens."""
    return [w for w in re.split(r"\W+", text.lower()) if len(w) > 2]


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _tf_idf(tokens: list[str], df: dict[str, int], n_docs: int) -> dict[str, float]:
    """Compute TF-IDF vector for a single document."""
    tf = Counter(tokens)
    total = len(tokens) if tokens else 1
    vec: dict[str, float] = {}
    for term, count in tf.items():
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        vec[term] = (count / total) * idf
    return vec


class ReformulationDetector:
    """Detects when a student reformulates a previous prompt.

    Uses TF-IDF cosine similarity within a 90-second window.
    A reformulation is detected when:
    - Similarity > 0.4
    - The new message is longer or more specific (more tokens)
    - Within a 90-second window of the previous message

    Pure Python, no async, no DB access.
    """

    SIMILARITY_THRESHOLD = 0.4
    TIME_WINDOW_SECONDS = 90

    def detect(
        self,
        current_message: str,
        current_timestamp_iso: str,
        recent_user_messages: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Check if current_message is a reformulation of a recent user message.

        Args:
            current_message: The new user message text.
            current_timestamp_iso: ISO-8601 timestamp of the current message.
            recent_user_messages: List of dicts with keys: content, timestamp.
                Expected to be ordered oldest-first.

        Returns:
            A payload dict for the prompt.reformulated event, or None.
        """
        if not current_message or not recent_user_messages:
            return None

        current_tokens = _tokenize(current_message)
        if len(current_tokens) < 3:
            return None

        from datetime import datetime, timezone

        try:
            current_ts = datetime.fromisoformat(current_timestamp_iso)
            if current_ts.tzinfo is None:
                current_ts = current_ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

        all_docs_tokens = [current_tokens]
        candidate_messages = []

        for msg in recent_user_messages:
            content = msg.get("content", "")
            ts_str = msg.get("timestamp", "")
            if not content or not ts_str:
                continue
            try:
                msg_ts = datetime.fromisoformat(ts_str)
                if msg_ts.tzinfo is None:
                    msg_ts = msg_ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            delta = (current_ts - msg_ts).total_seconds()
            if delta < 0 or delta > self.TIME_WINDOW_SECONDS:
                continue

            tokens = _tokenize(content)
            if len(tokens) < 3:
                continue

            all_docs_tokens.append(tokens)
            candidate_messages.append((msg, tokens, delta))

        if not candidate_messages:
            return None

        # Build document frequency across all docs in the comparison set
        n_docs = len(all_docs_tokens)
        df: dict[str, int] = {}
        for doc_tokens in all_docs_tokens:
            for term in set(doc_tokens):
                df[term] = df.get(term, 0) + 1

        current_vec = _tf_idf(current_tokens, df, n_docs)

        best_sim = 0.0
        best_msg: dict[str, Any] | None = None

        for msg, tokens, delta in candidate_messages:
            msg_vec = _tf_idf(tokens, df, n_docs)
            sim = _cosine_similarity(current_vec, msg_vec)

            # Must be more specific: current message should have equal or more tokens
            if sim > best_sim and len(current_tokens) >= len(tokens):
                best_sim = sim
                best_msg = msg

        if best_sim < self.SIMILARITY_THRESHOLD or best_msg is None:
            return None

        return {
            "similarity_score": round(best_sim, 4),
            "original_message_id": best_msg.get("id") or best_msg.get("interaction_id"),
            "current_length": len(current_message),
            "original_length": len(best_msg.get("content", "")),
            "detection_method": "tfidf_cosine",
        }
