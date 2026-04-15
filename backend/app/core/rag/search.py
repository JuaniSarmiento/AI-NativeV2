"""Semantic search over document chunks using pgvector cosine similarity."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag.models import DocumentChunk


async def search_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    *,
    top_k: int = 5,
    topic: str | None = None,
) -> list[DocumentChunk]:
    """Find the most relevant document chunks by cosine similarity.

    Args:
        session: Active database session.
        query_embedding: The embedding vector for the search query (1536 dims).
        top_k: Number of results to return.
        topic: Optional topic filter (e.g. "Condicionales").

    Returns:
        List of DocumentChunk ordered by similarity (most similar first).
    """
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    if topic:
        stmt = text(
            "SELECT id, source_file, topic, chunk_index, content, created_at "
            "FROM operational.document_chunks "
            "WHERE embedding IS NOT NULL AND topic = :topic "
            "ORDER BY embedding <=> :embedding "
            "LIMIT :limit"
        )
        result = await session.execute(
            stmt, {"embedding": embedding_str, "topic": topic, "limit": top_k}
        )
    else:
        stmt = text(
            "SELECT id, source_file, topic, chunk_index, content, created_at "
            "FROM operational.document_chunks "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> :embedding "
            "LIMIT :limit"
        )
        result = await session.execute(
            stmt, {"embedding": embedding_str, "limit": top_k}
        )

    rows = result.fetchall()
    chunks = []
    for row in rows:
        chunk = DocumentChunk(
            id=row.id,
            source_file=row.source_file,
            topic=row.topic,
            chunk_index=row.chunk_index,
            content=row.content,
        )
        chunks.append(chunk)

    return chunks


async def search_chunks_by_text(
    session: AsyncSession,
    query: str,
    *,
    top_k: int = 5,
    topic: str | None = None,
) -> list[DocumentChunk]:
    """Fallback text search using ILIKE when embeddings are not available."""
    words = query.split()[:5]
    conditions = " AND ".join(f"content ILIKE '%{w}%'" for w in words if w)

    sql = (
        f"SELECT id, source_file, topic, chunk_index, content, created_at "
        f"FROM operational.document_chunks "
        f"WHERE {conditions} "
    )
    if topic:
        sql += f"AND topic = '{topic}' "
    sql += f"LIMIT {top_k}"

    result = await session.execute(text(sql))
    rows = result.fetchall()
    chunks = []
    for row in rows:
        chunk = DocumentChunk(
            id=row.id,
            source_file=row.source_file,
            topic=row.topic,
            chunk_index=row.chunk_index,
            content=row.content,
        )
        chunks.append(chunk)

    return chunks
