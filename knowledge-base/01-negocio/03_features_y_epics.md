# Features y EPICs

## Estructura del Proyecto en Fases

El proyecto se divide por **dominio funcional**, no por capa técnica. Cada fase produce un módulo autónomo con interfaces bien definidas (endpoints REST + schemas Pydantic/TypeScript). Esto permite que 4 programadores trabajen en paralelo con mínima dependencia cruzada.

### Timeline

```
Semanas 1-2:   FASE 0 ────── (todos juntos) Setup monorepo, DB, auth, contratos
Semanas 3-12:  FASES 1-4 ─── (paralelo) Cada dev trabaja contra contratos de Fase 0
Semanas 13-14: INTEGRACIÓN── Testing E2E, ajustes de compatibilidad
Semanas 15-16: QA FINAL ──── Deploy staging, prueba con usuarios piloto
```

---

## EPIC 0 — Fundación Compartida (Fase 0)

**Duración**: Semanas 1-2 (todo el equipo junto)
**Objetivo**: Construir la base común para que los 4 devs trabajen en paralelo con confianza.

| ID | Story | Prioridad | Dependencias |
|----|-------|-----------|-------------|
| E0-S1 | Setup monorepo con estructura `/backend`, `/frontend`, `/shared`, `/infra` | critical | — |
| E0-S2 | Docker Compose: api + db + redis + frontend con hot reload | critical | E0-S1 |
| E0-S3 | PostgreSQL con 4 schemas iniciales (operational, cognitive, governance, analytics) | critical | E0-S2 |
| E0-S4 | Auth JWT + RBAC (alumno/docente/admin) con refresh rotation 15min/7d | critical | E0-S3 |
| E0-S5 | OpenAPI spec completo + tipos TypeScript auto-generados | high | E0-S3 |
| E0-S6 | CI pipeline básico: lint + tests + build en GitHub Actions | high | E0-S1 |
| E0-S7 | Seed data: 1 curso, 1 comisión, 3 ejercicios, 2 usuarios (1 alumno, 1 docente) | medium | E0-S3, E0-S4 |

**Criterio de completitud**: Docker Compose levanta API + DB + Frontend en un comando. Auth JWT funcional. OpenAPI spec validado. CI pasa lint + tests. Seed data cargada.

---

## EPIC 1 — Core Académico + Sandbox (Fase 1)

**Duración**: Semanas 3-12 (paralelo)
**Schema owner**: `operational` (courses, commissions, exercises, submissions, code_snapshots, enrollments)
**Objetivo**: Construir los cimientos operativos — gestión de cursos, ejercicios, submissions y sandbox de ejecución segura.

| ID | Story | Prioridad | Dependencias |
|----|-------|-----------|-------------|
| E1-S1 | CRUD cursos, comisiones, ejercicios, enrollments | critical | EPIC-0 |
| E1-S2 | Submission flow: crear draft, ejecutar en sandbox, enviar | critical | E1-S1 |
| E1-S3 | Sandbox Python seguro (timeout 10s, memory 128MB, sin red, sin filesystem) | critical | E1-S1 |
| E1-S4 | Code snapshots automáticos cada 30s + ante ejecución | high | E1-S2 |
| E1-S5 | Test cases del ejercicio como assertions con reporte pass/fail individual | high | E1-S3 |

**Modelos de datos clave**:
- `courses`: id (UUID PK), name, description, is_active
- `commissions`: id, course_id (FK), teacher_id (FK → users), name, year, semester, is_active
- `exercises`: id, course_id (FK → courses), title, description (markdown), difficulty, topic_taxonomy (JSONB), starter_code, test_cases (JSONB), constraints
- `submissions`: id, student_id (FK), exercise_id (FK), code (TEXT), runtime_ms, stdout, stderr, test_results (JSONB), score, status (pending/running/passed/failed/error)
- `code_snapshots`: id, student_id, exercise_id, submission_id (nullable FK), code, snapshot_at
- `enrollments`: id, student_id, commission_id, enrolled_at, status

**Criterio de completitud**: Un alumno puede ver ejercicios, escribir código, ejecutarlo en sandbox, ver output, enviar submission. El docente puede ver submissions con resultados. Snapshots se guardan automáticamente.

---

## EPIC 2 — Tutor IA Socrático (Fase 2)

**Duración**: Semanas 3-12 (paralelo)
**Schema owner**: `operational` (tutor_interactions). Fase 2 también escribe en `governance` (governance_events al detectar violaciones, tutor_system_prompts gestionados por admin)
**Objetivo**: Construir el tutor de IA que acompaña al alumno — regulado, registrado, y nunca entrega soluciones.

| ID | Story | Prioridad | Dependencias |
|----|-------|-----------|-------------|
| E2-S1 | Chat streaming alumno-tutor via WebSocket | critical | EPIC-0 |
| E2-S2 | System prompt socrático versionado con SHA-256 | critical | E2-S1 |
| E2-S3 | Constructor de contexto (ejercicio + código actual + historial) | critical | E2-S1 |
| E2-S4 | Post-procesador / guardrails anti-solver | critical | E2-S2 |
| E2-S5 | Clasificación N4 de cada interacción (critical/exploratory/dependent) | high | E2-S1 |
| E2-S6 | Reflexión post-ejercicio (formulario guiado, persistido en `operational` por Fase 2; Fase 3 recibe evento `reflection.submitted` via Event Bus para incorporarlo al CTR) | high | E2-S1 |
| E2-S7 | Registro de governance events (policy violations, prompt updates) | medium | E2-S4 |

**Componentes internos del Tutor Orchestrator**:
1. **Pre-procesador**: normaliza input, detecta idioma, extrae contexto del ejercicio y estado del código
2. **Constructor de contexto**: arma prompt completo (system prompt + enunciado + código + historial + restricciones)
3. **Cliente LLM**: llama API Anthropic con streaming via WebSocket al frontend
4. **Post-procesador / Guardrails**: analiza respuesta del LLM antes de enviar. Detecta y reformula soluciones directas
5. **Registrador de interacción**: persiste cada turno con clasificación N4 y resultado del policy check

**Modelos de datos clave**:
- `tutor_interactions`: id, session_id (correlación lógica con cognitive_sessions.id — sin FK estricta para respetar ownership entre fases), student_id, exercise_id, role (user/assistant), content, n4_level, tokens_used, model_version, prompt_hash, created_at
- `tutor_system_prompts`: id, name, content, sha256_hash, version, is_active, guardrails_config, created_by, created_at
- `governance_events`: id, event_type (policy_violation/prompt_update/model_change), details (JSONB)

**Criterio de completitud**: Chat funcional con streaming. Tutor nunca entrega soluciones (verificado por guardrails, 20+ tests adversarios). Interacciones registradas con clasificación N4 y policy check. Reflexión post-ejercicio funcional.

---

## EPIC 3 — Motor Cognitivo + Evaluación (Fase 3)

**Duración**: Semanas 3-12 (paralelo)
**Schema owner**: `cognitive` (sessions, events, metrics, reasoning), `analytics` (risk_assessments)
**Objetivo**: El cerebro analítico — toma datos crudos y los transforma en un perfil cognitivo basado en el modelo N4. Lo que diferencia esta plataforma de cualquier juez online.

| ID | Story | Prioridad | Dependencias |
|----|-------|-----------|-------------|
| E3-S1 | Cognitive Event Classifier (event_type → N1-N4 según mapeo empate3) | critical | EPIC-0 |
| E3-S2 | CTR Builder con hash chain SHA-256 encadenado | critical | E3-S1 |
| E3-S3 | Validación CTR mínimo (al menos 1 evento por N1-N4) | critical | E3-S2 |
| E3-S4 | Cognitive Worker: métricas N1-N4 + Qe + dependency por sesión | critical | E3-S2 |
| E3-S5 | Risk Worker: detección de alumnos en riesgo (dependency/disengagement/stagnation) | high — dependencia bloqueante para el dashboard docente (E4-S4) | E3-S4 |
| E3-S6 | Evaluation Engine: E = f(N1, N2, N3, N4, Qe) | high | E3-S4 |

**Componentes internos**:
1. **Cognitive Event Classifier**: clasifica eventos crudos en event_type y n4_level según mapeo canónico del documento maestro
2. **CTR Builder**: agrupa eventos por sesión, construye hash chain, determina validez mínima
3. **Cognitive Worker**: calcula métricas agregadas por sesión (N1-N4 + Qe como constructo jerárquico)
4. **Risk Worker**: analiza patrones a nivel alumno/curso (dependencia excesiva, desenganche, estancamiento)
5. **Evaluation Engine**: sintetiza en función evaluativa formal

**Sistema de eventos en 3 niveles**:

El sistema maneja eventos en 3 capas distintas. Fase 3 transforma los eventos del bus al formato CTR al consumirlos.

| Bus Event (Redis Streams) | CTR Event (cognitive_events) | N4 Level | Notas |
|--------------------------|----------------------------|---------|-------|
| `reads_problem` | `reads_problem` | N1 | Frontend emite cuando alumno abre ejercicio |
| `code.snapshot.captured` | `code.snapshot` | N2 | Cada 30s + ante ejecución |
| `code.executed` | `code.run` | N3 | Alumno ejecuta código en sandbox |
| `tutor.interaction.completed` | `tutor.question_asked` | N4 | Turno del alumno en chat |
| `tutor.interaction.completed` | `tutor.response_received` | N4 | Turno del tutor en chat |
| `exercise.submitted` | `submission.created` | N2/N3 | Alumno envía solución final |
| `reflection.submitted` | `reflection.submitted` | — (metacognitivo) | Alimenta reflection_score |
| — | `session.started` | — | Evento de lifecycle |
| — | `session.closed` | — | Evento de lifecycle |

Adicionalmente, Fase 3 infiere **indicadores comportamentales** del análisis de patrones sobre el CTR (no se almacenan como events): `asks_clarification` (N1), `reformulates_problem` (N1), `defines_strategy` (N2), `changes_strategy` (N2), `asks_hint` (N2), `interprets_error` (N3), `fixes_error` (N3), `asks_explanation` (N4), `audits_ai_suggestion` (N4). Estos indicadores contribuyen a los scores N1-N4 pero no son event_types del CTR.

**Modelos de datos clave**:
- `cognitive_sessions`: id (UUID PK), student_id, exercise_id, started_at, ended_at, status (open/closed/invalidated), ctr_hash_chain, is_valid_ctr
- `cognitive_events`: id (UUID PK), session_id, event_type (enum), n4_level (N1/N2/N3/N4), payload (JSONB), sequence_number, timestamp, event_hash: VARCHAR(64) — Hash SHA-256 de este evento, parte de la cadena hash del CTR
- `cognitive_metrics`: id, session_id, n1_comprehension_score, n2_strategy_score, n3_validation_score, n4_ai_interaction_score, qe_score, qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification, dependency_score, reflection_score, success_efficiency, total_interactions, help_seeking_ratio, autonomy_index, risk_level
- `reasoning_records`: id, session_id, classification (understanding/planning/debugging/ai_interaction/metacognition), content (JSONB), decisions (JSONB), metacognition_score
- `risk_assessments`: id, student_id, commission_id, assessment_type (dependency/disengagement/stagnation), risk_level (low/medium/high/critical), details (JSONB)

**Criterio de completitud**: Eventos se clasifican automáticamente por N1-N4. CTR con hash chain íntegro. is_valid_ctr correcto. Métricas calculadas por sesión. Dashboard docente con datos agregados. Sistema detecta alumnos en riesgo.

---

## EPIC 4 — Frontend Completo (Fase 4)

**Duración**: Semanas 3-12 (paralelo), integración Semanas 13-14
**Schema owner**: ninguno (consume APIs)
**Objetivo**: Todo lo que los usuarios ven y tocan. Dos interfaces: alumno y docente.

| ID | Story | Prioridad | Dependencias |
|----|-------|-----------|-------------|
| E4-S1 | Dashboard alumno: cursos, ejercicios pendientes/completados, progreso | critical | EPIC-0 |
| E4-S2 | Vista de ejercicio: Monaco Editor + chat tutor + panel output (3 paneles) | critical | E4-S1 |
| E4-S3 | Panel de reflexión post-ejercicio | high | E4-S2 |
| E4-S4 | Dashboard docente: indicadores agregados, radar N1-N4, alumnos en riesgo | critical | E4-S1 |
| E4-S5 | Traza cognitiva visual: timeline con eventos color-coded N1-N4 + diff código | high | E4-S4 |
| E4-S6 | Patrones de ejercicio: vista agregada de estrategias de la clase | medium | E4-S4 |
| E4-S7 | Reportes de gobernanza: violaciones, cambios de prompts, alertas | medium | E4-S4 |
| E4-S8 | MSW (Mock Service Worker) para desarrollo paralelo con APIs mock | critical | E4-S1 |
| E4-S9 | Responsive para tablet en aula | medium | E4-S2, E4-S4 |

**Pantallas del alumno**:
- Dashboard personal: cursos inscriptos, ejercicios pendientes/completados, progreso general
- Vista de ejercicio (principal): layout 3 paneles — enunciado (izquierda), Monaco editor (centro), chat tutor + output (derecha). Botones: Ejecutar, Enviar, Guardar snapshot
- Panel de reflexión: formulario guiado (qué fue lo más difícil, qué estrategia usó, cómo evalúa su uso de la IA, qué haría diferente)
- Historial de submissions: lista con status y score multidimensional

**Pantallas del docente**:
- Dashboard de curso: vista general de comisión con indicadores agregados, promedio N1-N4, distribución Qe, alumnos en riesgo (color-coded)
- Perfil de alumno: detalle individual con radar chart N1-N4, evolución temporal, dependency_score, historial de interacciones con IA
- Vista de traza cognitiva: reconstrucción completa del episodio — timeline visual con eventos color-coded (N1=azul, N2=verde, N3=naranja, N4=violeta), código evolutivo con diff, chat completo con tutor
- Patrones de ejercicio: vista agregada de cómo la clase resolvió un ejercicio particular
- Reportes de gobernanza: violaciones del tutor, cambios de prompts, alertas

**Estrategia de desarrollo paralelo**: MSW intercepta requests HTTP en desarrollo y devuelve datos simulados respetando schemas Pydantic/TypeScript compartidos. Cuando las APIs reales estén listas, se remueve MSW sin cambios de código.

**Criterio de completitud**: Todas las pantallas funcionales con datos reales post-integración. Flujo end-to-end alumno (ver ejercicio → escribir → ejecutar → chatear → enviar → reflexionar). Docente puede analizar desde dashboard hasta traza cognitiva individual. Responsive en tablet.

---

## Diagrama de Dependencias entre EPICs

```
                    EPIC 0 (Fundación)
                    ┌──────┴──────┐
                    │             │
              ┌─────┤             ├─────┐
              │     │             │     │
           EPIC 1   EPIC 2    EPIC 3   EPIC 4
           (Core)   (Tutor)   (Motor)  (Frontend)
              │        │         │        │
              │        │         │        │
              └────────┴────┬────┘        │
                            │             │
                    Eventos cognitivos     │
                    (Event Bus)           │
                            │             │
                            └──────┬──────┘
                                   │
                            INTEGRACIÓN
                            (Semanas 13-14)
```

**Puntos de integración críticos**:
1. **Fase 4 → Fase 1**: Alumno ejecuta código (`POST /api/v1/student/exercises/{id}/run`)
2. **Fase 4 → Fase 2**: Alumno chatea con tutor (WebSocket `/ws/tutor/chat`)
3. **Fase 1,2 → Fase 3**: Acciones generan eventos cognitivos (Event Bus)
4. **Fase 4 → Fase 3**: Docente ve métricas cognitivas (`GET /api/v1/teacher/courses/{id}/dashboard`)
