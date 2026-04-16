## Context

EPICs 08-15 construyeron toda la data pipeline: code snapshots, tutor chat, CTR events con hash chain, metricas cognitivas N1-N4, y risk assessments. Todo se persiste pero no se visualiza de forma integrada. El docente necesita una herramienta para reconstruir visualmente el proceso cognitivo del alumno.

Endpoints existentes que consumimos:
- `GET /api/v1/cognitive/sessions/{id}` — session + events (EPIC-13)
- `GET /api/v1/cognitive/sessions/{id}/verify` — hash chain verification (EPIC-13)
- `GET /api/v1/cognitive/sessions/{id}/metrics` — N1-N4 scores (EPIC-14)
- `GET /api/v1/tutor/sessions/{exercise_id}/messages` — chat history (EPIC-09)
- `GET /api/v1/governance/events` — governance events (EPIC-11)

Endpoints que FALTAN y hay que crear:
- Traza unificada (merge de events + snapshots + chat + metrics en un solo payload)
- Timeline cronologico (events ordenados con metadata de N4)
- Code evolution con diffs entre snapshots
- Prompt history para governance

## Goals / Non-Goals

**Goals:**
- Docente puede ver timeline visual completo de un alumno en un ejercicio
- Color-coding por nivel N1-N4 (azul, verde, naranja, violeta)
- Diffs de codigo entre snapshots sucesivos
- Chat del tutor integrado en la traza
- Verificacion visual de integridad del hash chain
- Vista agregada de patrones por ejercicio a nivel clase
- Reportes de governance funcionales

**Non-Goals:**
- Edicion o modificacion de la traza (es read-only por definicion — inmutabilidad del CTR)
- Real-time updates de la traza (es retrospectiva, no live)
- Exportacion a PDF o CSV (EPIC futura)
- Comparacion side-by-side de dos alumnos (EPIC futura)
- Monaco editor o editor interactivo — solo visualizacion de diffs

## Decisions

### D1: Endpoint de traza unificada en vez de N+1 calls del frontend

Un solo endpoint `/api/v1/cognitive/sessions/{id}/trace` que devuelve events + metrics + session metadata en un payload unificado. El frontend necesitaria hacer 3-4 calls separados de otra forma. Las tutor_interactions y code_snapshots se obtienen via REST a sus endpoints existentes desde el FRONTEND (no desde el backend), respetando la regla de cross-schema access.

**Alternativa descartada**: Backend fetch cross-schema — viola la regla de ownership.

### D2: Diffs computados en el frontend, no en el backend

Los code snapshots se envian como texto plano. El diff se computa en el frontend usando una lib de diff (diff-match-patch o similar liviana). Esto evita agregar logica de diffing en el backend y permite al frontend controlar la presentacion.

**Alternativa descartada**: Backend diff — agrega dependencia, complejidad, y el frontend ya tiene todo lo necesario.

### D3: Feature folders separados por dominio visual

- `features/teacher/trace/` — traza cognitiva de una sesion
- `features/teacher/patterns/` — patrones a nivel ejercicio/clase
- `features/teacher/governance/` — reportes de governance

No todo en un mega-folder. Cada uno tiene su store, tipos y componentes.

### D4: Zustand store por vista, no store global de traza

Cada vista tiene su store acotado. El trace store carga los datos cuando se navega a la traza y los libera al salir. No se acumula estado entre sesiones.

### D5: Code snapshots via endpoint existente, extendido con query por session

Actualmente no hay un endpoint que devuelva snapshots por session. Hay dos opciones:
1. Agregar query param `?session_id=` al endpoint existente de snapshots
2. Incluir los snapshot IDs en el CTR event payload y fetchear individualmente

Elegimos opcion 1 — nuevo endpoint `GET /api/v1/cognitive/sessions/{id}/code-evolution` que agrega el join session → events → snapshot_ids internamente (todo dentro del schema cognitive + operational leido via servicio).

### D6: Governance prompts endpoint separado del events endpoint

El endpoint de governance events ya existe (`GET /api/v1/governance/events`). Pero los prompts tienen su propio modelo (`TutorSystemPrompt`) con SHA-256 y versioning. Agregamos `GET /api/v1/governance/prompts` para listar historial de prompts.

## Risks / Trade-offs

- **[Cross-schema data]** Code snapshots y tutor interactions viven en operational. → Mitigation: el frontend los fetchea via REST, el backend trace endpoint solo devuelve data del schema cognitive.
- **[Performance]** Una sesion con muchos eventos puede generar un payload grande. → Mitigation: paginacion en timeline, lazy loading de snapshots.
- **[Diff library size]** diff-match-patch agrega ~10KB gzipped al bundle. → Mitigation: dynamic import, solo carga cuando se abre la vista de diffs.
- **[N4 color mapping]** Los colores N1-N4 se hardcodean en constantes, no en el theme. → Mitigation: CSS custom properties dedicadas para N4 levels.
