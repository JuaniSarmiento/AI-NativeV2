## Why

Los docentes necesitan crear actividades (conjuntos de ejercicios) alineadas al material de la cátedra. Hacerlo manualmente es tedioso — definir enunciados, test cases, starter code, dificultad. Con un RAG sobre la documentación oficial de Programación I (PDFs, notebooks) y la API key del docente, la IA puede generar actividades contextualizadas que el docente revisa y publica.

## What Changes

### Backend
- Modelo `Activity` (agrupación de ejercicios con estado draft/published)
- Modelo `LLMConfig` para API keys por docente (encriptada)
- Pipeline RAG: procesamiento de PDFs/notebooks → chunks → embeddings → vector store
- Servicio de generación: docente envía prompt → RAG busca contexto relevante → LLM genera actividad con ejercicios
- Endpoints: CRUD actividades, chat para generación, config LLM
- Los PDFs de Prog I se procesan al deployar (pre-cargados, globales)

### Frontend
- Settings: configuración de API key del proveedor LLM
- Chat de generación: interfaz donde el docente describe la actividad que quiere
- Vista de actividad generada: lista de ejercicios draft que el docente puede editar y publicar
- Integración con el ABM de ejercicios existente

## Capabilities

### New Capabilities
- `activity-model`: Modelo Activity (draft/published) + relación con ejercicios, migración Alembic
- `llm-config`: Almacenamiento seguro de API keys por docente, soporte multi-proveedor (OpenAI, Anthropic, etc.)
- `rag-pipeline`: Procesamiento de documentos (PDF, ipynb) → chunks → embeddings → búsqueda semántica
- `activity-generation`: Servicio que combina RAG + LLM para generar actividades con ejercicios
- `activity-chat-ui`: Interfaz de chat para que el docente describa la actividad y vea la generación

### Modified Capabilities
- `monorepo-structure`: Se agregan features/activities backend y frontend, rag/ pipeline

## Impact

- **Backend**: `backend/app/features/activities/`, `backend/app/core/rag/`, `backend/app/core/llm/`
- **Frontend**: `frontend/src/features/activities/`
- **Database**: Tablas `activities`, `llm_configs` en schema operational
- **Infra**: Vector store (ChromaDB embeddings en disco o pgvector)
- **Datos**: 34 archivos de Prog I procesados como knowledge base
- **Dependencias nuevas**: `langchain`, `chromadb` o `pgvector`, `PyPDF2`, `nbformat`
