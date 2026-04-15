## Context

EPIC-06 dejó ejercicios funcionando (modelo, CRUD, RBAC). Los PDFs y notebooks de Programación I de la UTN están en `knowledge-base/prog1-docs/` con 34 archivos organizados por tema: Secuenciales, Condicionales, Repetitivas, Funciones/Listas/Tuplas/Sets/Diccionarios, Manejo de archivos, Manejo de errores, Recursividad, Git. El contenido incluye TPs con ejercicios de ejemplo, notebooks con teoría y código, apuntes de cátedra.

## Goals / Non-Goals

**Goals:**
- Activity como entidad (draft → published) que agrupa ejercicios generados
- API key storage seguro por docente (encriptada con Fernet)
- RAG pipeline: PDF/ipynb → text chunks → embeddings → vector search
- Chat endpoint: docente envía instrucción, recibe actividad generada
- UI: config API key, chat de generación, revisión/edición de actividad draft
- Los 34 archivos de Prog I pre-procesados al iniciar

**Non-Goals:**
- No implementar streaming del LLM en esta EPIC (respuesta completa)
- No implementar upload de PDFs por el docente (los PDFs son pre-cargados)
- No implementar fine-tuning ni training
- No soportar imágenes/diagramas de los PDFs (solo texto)

## Decisions

### D1: pgvector sobre ChromaDB

Usamos `pgvector` como extensión de PostgreSQL para almacenar embeddings. Razón: ya tenemos PostgreSQL, no agregamos otro servicio. Los embeddings se generan con el modelo del docente (via su API key) y se cachean en la tabla `document_chunks`.

**Alternativa descartada**: ChromaDB en disco. Descartada porque agrega un servicio más y complica el deploy. pgvector es una extensión nativa.

**Nota**: para los embeddings del RAG pre-procesado (global) usamos un embedding model default. Para la generación usamos la API key del docente.

### D2: Procesamiento de docs como script de inicialización

Un script `backend/app/core/rag/ingest.py` procesa todos los PDFs/ipynbs en `knowledge-base/prog1-docs/`, los chunkea (500 tokens con overlap de 50), genera embeddings, y los guarda en `document_chunks`. Se corre una vez al deployar via `make ingest`.

### D3: Multi-proveedor LLM con adapter pattern

`backend/app/core/llm/` con un `LLMAdapter` protocol y implementaciones para OpenAI y Anthropic. El docente configura proveedor + API key. El servicio de generación usa el adapter que corresponda.

```python
class LLMAdapter(Protocol):
    async def generate(self, messages: list[dict], **kwargs) -> str: ...

class OpenAIAdapter(LLMAdapter): ...
class AnthropicAdapter(LLMAdapter): ...
```

### D4: Activity como draft con ejercicios generados

Cuando la IA genera, crea una Activity en estado `draft` con N ejercicios asociados (también en estado draft/is_active=False). El docente revisa, edita lo que quiera, y publica (estado → `published`, ejercicios → is_active=True). Esto respeta la regla de que la IA propone, el docente decide.

### D5: Prompt engineering para generación

El prompt del generador incluye:
1. System prompt con instrucciones de formato (JSON estructurado con title, description, test_cases, etc.)
2. Contexto RAG: chunks relevantes de los docs de Prog I
3. Instrucción del docente (lo que escribió en el chat)

El output del LLM se parsea como JSON y se convierte en ejercicios.

### D6: API key encriptada con Fernet

`LLMConfig.api_key` se encripta con `cryptography.fernet.Fernet` usando `SECRET_KEY` como base. Se desencripta solo al momento de usarla. Nunca se retorna en plaintext al frontend.

## Risks / Trade-offs

- **[Risk] LLM genera test cases incorrectos** → Mitigation: el docente SIEMPRE revisa antes de publicar. Nunca se publica automáticamente.
- **[Risk] pgvector requiere extensión instalada** → Mitigation: agregar `CREATE EXTENSION IF NOT EXISTS vector` en la migración. Docker image de PostgreSQL 16 la incluye.
- **[Risk] Embeddings globales vs por-docente** → Mitigation: embeddings globales para los docs de Prog I (se generan una vez con un modelo default). La generación de actividades usa la API key del docente.
- **[Risk] PDFs con tablas/imágenes pierden contexto** → Mitigation: aceptable para Prog I — el contenido es mayormente texto y código. Notebooks se parsean celda por celda preservando código.
