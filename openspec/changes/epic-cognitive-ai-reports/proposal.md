## Why

El dashboard cognitivo actual muestra métricas numéricas (N1-N4, Qe, risk_level) pero no ofrece una interpretación pedagógica accionable. El docente debe interpretar manualmente decenas de datos por alumno. Un sistema de informes automatizados que separe **análisis estadístico** (determinista, auditable) de **narrativa generativa** (LLM del docente) permite entregar un informe por alumno por actividad con evidencia concreta y lenguaje natural.

## What Changes

- Nuevo **Analytical Engine** (Python puro): agrega los datos de todas las sesiones cognitivas de un alumno en una actividad, detecta patrones, calcula estadísticas comparativas y extrae evidencia concreta (citas de chat, timestamps, secuencias de eventos).
- Nuevo **Narrative Engine**: toma el JSON estructurado del analytical engine y lo pasa al LLM del docente (vía AI Gateway existente) para generar un informe en Markdown con secciones estandarizadas.
- Nuevo **endpoint REST** `POST /api/v1/reports/generate` que dispara la generación y `GET /api/v1/reports/{report_id}` que devuelve el informe.
- Modelo de persistencia `CognitiveReport` en schema `cognitive` para cachear informes generados.
- **UI en dashboard docente**: vista actividad → lista de alumnos → botón "Ver Informe" → informe renderizado.

## Capabilities

### New Capabilities
- `cognitive-report-engine`: Motor analítico que procesa CTR events + metrics y produce un StructuredAnalysis JSON por alumno por actividad.
- `cognitive-report-narrative`: Servicio que recibe StructuredAnalysis y genera informe Markdown vía LLM del docente.
- `cognitive-report-api`: Endpoints REST para generar y consultar informes.
- `cognitive-report-frontend`: UI para visualizar informes desde el dashboard docente.

### Modified Capabilities
- `teacher-dashboard-frontend`: Agrega acceso a informes desde la vista de actividad/alumnos.

## Impact

- **Backend**: nuevo módulo `app/features/reports/` con engine, service, router, models, schemas.
- **Frontend**: nueva vista/componente de informe en `features/teacher/reports/`.
- **DB**: nueva tabla `cognitive.cognitive_reports` (id, student_id, activity_id, commission_id, structured_analysis JSON, narrative_md TEXT, generated_at, llm_provider, model_used).
- **Dependencias**: reutiliza `app/core/llm/` (AI Gateway) y `LLMConfig` del docente. Sin dependencias nuevas.
- **APIs afectadas**: ninguna existente cambia; solo se agregan nuevos endpoints.
