from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base

# pgvector column type — imported after extension is created
from pgvector.sqlalchemy import Vector


class DocumentChunk(Base):
    """A chunk of text from a course document, with its embedding for RAG.

    Schema: operational.
    """

    __tablename__ = "document_chunks"
    __table_args__ = {"schema": "operational"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_file: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True,
        comment="Relative path to the source document",
    )
    topic: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Topic inferred from folder name (e.g. Condicionales, Funciones)",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    embedding = mapped_column(
        Vector(1536), nullable=True,
        comment="OpenAI text-embedding-3-small compatible (1536 dims)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk file={self.source_file!r} topic={self.topic!r} idx={self.chunk_index}>"
