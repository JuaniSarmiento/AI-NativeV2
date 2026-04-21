## Context

El sistema ya cuenta con:
- `CognitiveMetrics` por sesión (N1-N4, Qe, risk_level, coherence scores, anomalías)
- `CognitiveEvent` hash-chained con event_type, payload, n4_level
- `TutorInteraction` con mensajes de chat completos
- `CodeSnapshot` con evolución de código
- AI Gateway (`app/core/llm/`) con adapters para Gemini/Claude/Mistral/OpenAI
- `LLMConfig` por docente con provider + api_key_encrypted + model_name

El docente ya puede ver métricas individuales por sesión en el dashboard, pero no tiene una vista interpretativa agregada por actividad.

## Goals / Non-Goals

**Goals:**
- Generar un informe cognitivo por alumno por actividad con evidencia concreta
- Separar análisis determinista (auditable) de narrativa generativa
- Cachear informes para no regenerar innecesariamente
- Reutilizar el LLM configurado por el docente (su API key)
- UI simple: botón → informe renderizado en Markdown

**Non-Goals:**
- Comparación entre alumnos (v2)
- Informes grupales/de cohorte (v2)
- Generación automática en background al cerrar sesión (v2)
- Exportación a PDF (v2)
- Streaming del informe token a token (v2)

## Decisions

### 1. Dos etapas: Analytical Engine → Narrative Engine

**Decisión**: pipeline de 2 stages con JSON intermedio (`StructuredAnalysis`).

**Alternativas consideradas**:
- Mandar todos los eventos crudos al LLM → costoso, no auditable, contexto enorme
- Solo métricas numéricas al LLM → pierde evidencia concreta

**Rationale**: el JSON intermedio es auditable, cacheable, y reduce tokens enviados al LLM. El analytical engine es puro Python (determinista), el narrative engine solo redacta.

### 2. Endpoint on-demand con cache

**Decisión**: `POST /api/v1/reports/generate` genera sincrónicamente. Si ya existe un informe cacheado con los mismos datos (hash de métricas), lo devuelve sin regenerar.

**Alternativas**:
- Background job → más complejo, el docente quiere ver el informe ahora
- Solo on-demand sin cache → costoso si consulta repetidas veces

**Rationale**: la generación tarda ~3-8s (un LLM call). Es aceptable para on-demand. El cache evita regenerar si no hay datos nuevos.

### 3. Invalidación de cache por data_hash

**Decisión**: el `StructuredAnalysis` se hashea (SHA-256). Si al regenerar el hash coincide con el informe existente, se devuelve el cacheado. Si cambió (nuevas sesiones cerradas), se regenera.

### 4. Estructura del StructuredAnalysis

```json
{
  "student_id": "uuid",
  "activity_id": "uuid",
  "activity_title": "string",
  "student_name": "string",
  "sessions_analyzed": 3,
  "overall_scores": {
    "n1_avg": 0.72,
    "n2_avg": 0.55,
    "n3_avg": 0.68,
    "n4_avg": 0.40,
    "qe_avg": 0.58
  },
  "risk_level": "medium",
  "patterns": [
    {
      "type": "high_ai_dependency",
      "severity": "warning",
      "evidence": "Preguntó al tutor 14 veces antes de escribir código en sesión 2",
      "metric_ref": "n4_ai_interaction_score = 0.35"
    }
  ],
  "strengths": [
    {
      "dimension": "N1",
      "description": "Comprende rápidamente los enunciados",
      "evidence": "Tiempo promedio reads_problem → primer code.edit: 32s (media clase: 95s)"
    }
  ],
  "weaknesses": [
    {
      "dimension": "N3",
      "description": "No verifica output antes de enviar",
      "evidence": "Solo 1 de 5 submissions tuvo test.run previo"
    }
  ],
  "evolution": {
    "trend": "improving",
    "detail": "N2 subió de 0.4 (sesión 1) a 0.7 (sesión 3)"
  },
  "anomalies": []
}
```

### 5. Prompt del Narrative Engine

System prompt fijo + el StructuredAnalysis como user message. El LLM genera Markdown con secciones:
- Resumen ejecutivo (2-3 oraciones)
- Fortalezas (con evidencia)
- Áreas de mejora (con evidencia)
- Evolución observada
- Recomendaciones pedagógicas

### 6. Modelo de persistencia

```sql
CREATE TABLE cognitive.cognitive_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL,
  activity_id UUID NOT NULL,
  commission_id UUID NOT NULL,
  generated_by UUID NOT NULL,  -- docente que pidió el informe
  structured_analysis JSONB NOT NULL,
  data_hash VARCHAR(64) NOT NULL,  -- SHA-256 del structured_analysis
  narrative_md TEXT NOT NULL,
  llm_provider VARCHAR(20) NOT NULL,
  model_used VARCHAR(100) NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(student_id, activity_id, data_hash)
);
```

### 7. Módulo backend

```
app/features/reports/
├── __init__.py
├── router.py          # POST /generate, GET /{id}, GET /by-student
├── schemas.py         # Request/Response DTOs
├── service.py         # Orquesta analytical + narrative
├── analytical.py      # StructuredAnalysis builder (Python puro)
├── narrative.py       # LLM call con prompt
├── models.py          # CognitiveReport SQLAlchemy model
└── repository.py      # CRUD + lookup por hash
```

## Risks / Trade-offs

- **[LLM latency]** → El informe tarda 3-8s. Mitigación: UI muestra spinner + cache evita regenerar.
- **[API key inválida del docente]** → Mitigación: capturar error del adapter y devolver 422 con mensaje claro.
- **[Datos insuficientes]** → Si el alumno no tiene sesiones cerradas, no hay qué analizar. Mitigación: validar upfront y devolver 400.
- **[Costo de tokens]** → El StructuredAnalysis es ~500-1000 tokens + system prompt ~300 tokens. Response ~800 tokens. Total ~2000 tokens por informe. Aceptable.
- **[Alucinación del LLM]** → Mitigación: el LLM solo puede citar evidencia que está en el JSON. El prompt le prohíbe inventar datos.
