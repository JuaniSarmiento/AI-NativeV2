## ADDED Requirements

### Requirement: Document processing pipeline
The system SHALL process PDF and ipynb files from `knowledge-base/prog1-docs/` into text chunks stored in a `document_chunks` table with fields: id (UUID PK), source_file (VARCHAR), topic (VARCHAR — inferred from folder name), chunk_index (INT), content (TEXT), embedding (vector(1536) via pgvector), created_at.

#### Scenario: PDF is chunked and embedded
- **WHEN** the ingest script processes a PDF
- **THEN** the content SHALL be split into chunks of ~500 tokens with 50 token overlap, each stored with its embedding

#### Scenario: Notebook is parsed preserving code
- **WHEN** the ingest script processes a .ipynb file
- **THEN** both markdown and code cells SHALL be extracted and chunked

### Requirement: Semantic search over document chunks
The system SHALL provide a function `search_chunks(query: str, top_k: int) -> list[DocumentChunk]` that finds the most relevant chunks using cosine similarity on pgvector.

#### Scenario: Relevant chunks returned
- **WHEN** search_chunks("condicionales anidados", top_k=5) is called
- **THEN** the results SHALL include chunks from the Condicionales folder documents

### Requirement: pgvector extension
The system SHALL use pgvector as PostgreSQL extension for vector storage and similarity search. The migration SHALL include `CREATE EXTENSION IF NOT EXISTS vector`.

#### Scenario: Extension created idempotently
- **WHEN** the migration runs
- **THEN** the vector extension SHALL be available without error even if it already exists
