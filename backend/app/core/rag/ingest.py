"""Document ingestion pipeline — processes PDFs and notebooks into chunks.

Usage:
    python -m app.core.rag.ingest

Reads all PDF and ipynb files from knowledge-base/prog1-docs/,
splits them into chunks, and stores them in the document_chunks table.
Embeddings are generated later when an LLM API key is available.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 500  # tokens (approx words)
_CHUNK_OVERLAP = 50
_DOCS_DIR = Path(__file__).resolve().parents[4] / "knowledge-base" / "prog1-docs"


def extract_text_from_pdf(path: Path) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def extract_text_from_notebook(path: Path) -> str:
    import nbformat

    nb = nbformat.read(str(path), as_version=4)
    parts = []
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            parts.append(cell.source)
        elif cell.cell_type == "code":
            parts.append(f"```python\n{cell.source}\n```")
    return "\n\n".join(parts)


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def infer_topic(file_path: Path) -> str:
    relative = file_path.relative_to(_DOCS_DIR)
    parts = relative.parts
    if len(parts) > 1:
        return parts[0]
    return "general"


async def ingest_all() -> None:
    from sqlalchemy import select, text

    # Add backend to path
    backend_dir = str(Path(__file__).resolve().parents[3])
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from app.shared.db.session import get_session_factory

    if not _DOCS_DIR.exists():
        logger.error("Docs directory not found: %s", _DOCS_DIR)
        return

    files = list(_DOCS_DIR.glob("**/*.pdf")) + list(_DOCS_DIR.glob("**/*.ipynb"))
    logger.info("Found %d documents to process in %s", len(files), _DOCS_DIR)

    factory = get_session_factory()

    async with factory() as session:
        # Check if already ingested
        from app.core.rag.models import DocumentChunk

        existing = await session.execute(
            select(DocumentChunk).limit(1)
        )
        if existing.scalar_one_or_none():
            logger.info("Documents already ingested — skipping. Delete document_chunks to re-ingest.")
            return

        total_chunks = 0
        for file_path in files:
            try:
                if file_path.suffix.lower() == ".pdf":
                    content = extract_text_from_pdf(file_path)
                elif file_path.suffix.lower() == ".ipynb":
                    content = extract_text_from_notebook(file_path)
                else:
                    continue

                if not content.strip():
                    logger.warning("Empty content from %s — skipping.", file_path.name)
                    continue

                topic = infer_topic(file_path)
                chunks = chunk_text(content)
                relative_path = str(file_path.relative_to(_DOCS_DIR))

                for idx, chunk_text_content in enumerate(chunks):
                    chunk = DocumentChunk(
                        source_file=relative_path,
                        topic=topic,
                        chunk_index=idx,
                        content=chunk_text_content,
                        embedding=None,  # Generated later with API key
                    )
                    session.add(chunk)

                total_chunks += len(chunks)
                logger.info("Processed %s: %d chunks (topic: %s)", file_path.name, len(chunks), topic)

            except Exception:
                logger.exception("Failed to process %s", file_path.name)

        await session.commit()
        logger.info("Ingestion complete: %d chunks from %d files.", total_chunks, len(files))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    backend_dir = str(Path(__file__).resolve().parents[3])
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    asyncio.run(ingest_all())
