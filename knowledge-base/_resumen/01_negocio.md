# Resumen Consolidado — 01-negocio

> Generado a partir de la lectura de los 6 archivos de `knowledge-base/01-negocio/`.
> Última actualización: 2026-04-13

---

## 01_vision_y_contexto.md — Datos Clave

- **Problema**: La IA generativa rompió la relación código ↔ aprendizaje. El código ya no es evidencia confiable.
- **Solución**: Pasar de `E = correctness(output)` a `E = f(N1, N2, N3, N4, Qe)` — observar procesos cognitivos.
- **Modelo N4** (4 dimensiones irreductibles):
  - **N1 — Comprensión**: ¿entiende el problema? (reformulación, I/O, casos borde)
  - **N2 — Estrategia**: ¿planifica? (estructuras, justificación)
  - **N3 — Validación**: ¿verifica? (tests, errores, corrección iterativa)
  - **N4 — Interacción con IA**: ¿usa la IA críticamente? (crítico/exploratorio/dependiente)
- **Qe (Calidad Epistémica)**: constructo jerárquico con 4 componentes:
  - `quality_prompt`, `critical_evaluation`, `integration`, `verification`
- **CTR (Cognitive Trace Record)**: artefacto interpretativo, NO log técnico.
  - Inmutable post-cierre (hash chain SHA-256)
  - Hash génesis: `SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())`
  - Hash cadena: `hash(n) = SHA256(hash(n-1) + datos(n))`
  - Hash de cada evento almacenado en `event_hash` de `cognitive_events`
  - Hash final almacenado en `ctr_hash_chain` de `cognitive_sessions`
  - Mínimo viable: ≥1 evento por N1-N4 por episodio (episodio = cognitive_session)
- **Indicador cruzado Código↔Discurso**: salvaguarda contra performatividad. Cada afirmación conceptual del alumno debe correlacionar con una modificación de código en la misma ventana temporal.
- **Contexto institucional**: UTN FRM, tesis doctoral Dr. Alberto Cortez
- **Documento maestro**: empate3.docx
- **Principios de herencia semántica**: subordinación técnica, no degradación semántica, trazabilidad semántica, coherencia evaluativa, integración IA

---

## 02_actores_y_roles.md — Datos Clave

### Actores

| Actor | Rol | Restricciones clave |
|-------|-----|-------------------|
| **Estudiante** | Resuelve ejercicios, chatea con tutor, genera CTR | No ve otros perfiles, no crea ejercicios, rate limited 30 msg/hr/ejercicio, sandbox 10s/128MB |
| **Docente** | Observa, interpreta, actúa sobre datos | Solo ve su comisión, no modifica CTR ni métricas, no modifica prompts |
| **Admin** | Gestiona sistema y gobernanza | Todo sin restricción de comisión. No modifica CTRs cerrados |
| **Tutor IA** | Componente del sistema (no usuario) | NUNCA solución completa, máx 5 líneas código, preguntas socráticas |

### Principios socráticos operativos del tutor (6 principios)
1. Nunca entregar la solución completa
2. Partir del error real del estudiante
3. Preguntas breves y progresivas
4. Forzar prueba con caso concreto
5. Cierre con reflexión metacognitiva explícita
6. No introducir vocabulario no usado por el alumno

### RBAC (matriz completa)

| Recurso | alumno | docente | admin |
|---------|--------|---------|-------|
| Cursos | ver propios | gestionar propios | gestionar todos |
| Comisiones | ver propias | gestionar propias | gestionar todas |
| Ejercicios | ver + resolver | crear + editar | gestionar todos |
| Submissions | crear + ver propias | ver todas (su comisión) | ver todas |
| Tutor chat | chatear (rate limited) | — | — |
| Métricas cognitivas | ver propias | ver todas (su comisión) | ver todas |
| Traza cognitiva (CTR) | — | ver (su comisión) | ver todas |
| Risk assessments | — | ver (su comisión) | ver todos |
| Governance events | — | ver reportes | gestionar |
| Tutor system prompts | — | — | gestionar |
| Usuarios | — | — | gestionar |

**Nota**: Docente NO chatea con el tutor. Solo observa sesiones pasadas de sus alumnos.

### Invariancia entre proveedores LLM
- Objetivo de diseño para futuro (P3)
- v1 solo valida contra Anthropic adapter
- Items P3 del backlog: #29 (OpenAI), #30 (Ollama)

---

## 03_features_y_epics.md — Datos Clave

### Estructura en fases
- **Fase 0** (Semanas 1-2): Fundación compartida — monorepo, Docker, DB, auth, OpenAPI, CI, seeds
- **Fase 1** (Semanas 3-12): Core Académico + Sandbox — CRUD, submissions, sandbox, snapshots
- **Fase 2** (Semanas 3-12): Tutor IA Socrático — WebSocket chat, guardrails, N4 classification, reflexión
- **Fase 3** (Semanas 3-12): Motor Cognitivo + Evaluación — classifier, CTR, metrics, risk, evaluation
- **Fase 4** (Semanas 3-12): Frontend Completo — dashboards alumno/docente, Monaco, chat streaming
- **Integración** (Semanas 13-14): E2E testing, remover MSW
- **QA Final** (Semanas 15-16): Deploy staging, piloto

### Schema ownership
| Fase | Schema | Tablas |
|------|--------|--------|
| Fase 1 | operational | courses, commissions, exercises, submissions, code_snapshots, enrollments |
| Fase 2 | operational | tutor_interactions |
| Fase 2 | governance | governance_events, tutor_system_prompts |
| Fase 3 | cognitive | cognitive_sessions, cognitive_events, cognitive_metrics, reasoning_records |
| Fase 3 | analytics | risk_assessments |

### Modelos de datos clave (resumen de campos)

**Fase 1 — operational:**
- `courses`: id (UUID PK), name, description, is_active
- `commissions`: id, course_id (FK), name, year, semester, schedule, is_active
- `exercises`: id, course_id (FK → courses), title, description (md), difficulty, topic_taxonomy (JSONB), starter_code, test_cases (JSONB), constraints
- `submissions`: id, student_id (FK), exercise_id (FK), code (TEXT), runtime_ms, stdout, stderr, test_results (JSONB), score, status (pending/running/passed/failed/error)
- `code_snapshots`: id, student_id, exercise_id, submission_id (nullable FK), code, snapshot_at
- `enrollments`: id, student_id, commission_id, enrolled_at, status

**Fase 2 — operational + governance:**
- `tutor_interactions`: id, session_id (correlación lógica con cognitive_sessions.id, sin FK), student_id, exercise_id, role (user/assistant), content, n4_level, tokens_used, model_version, prompt_hash, created_at
- `tutor_system_prompts`: id, name, content, sha256_hash, version, is_active, guardrails_config, created_by, created_at
- `governance_events`: id, event_type (policy_violation/prompt_update/model_change), details (JSONB)

**Fase 3 — cognitive + analytics:**
- `cognitive_sessions`: id (UUID PK), student_id, exercise_id, started_at, ended_at, status (open/closed/invalidated), ctr_hash_chain, is_valid_ctr
- `cognitive_events`: id (UUID PK), session_id, event_type (enum), n4_level (N1-N4), payload (JSONB), sequence_number, timestamp, event_hash (VARCHAR 64)
- `cognitive_metrics`: id, session_id, n1_comprehension_score, n2_strategy_score, n3_validation_score, n4_ai_interaction_score, qe_score, qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification, dependency_score, reflection_score, success_efficiency, total_interactions, help_seeking_ratio, autonomy_index, risk_level
- `reasoning_records`: id, session_id, classification (understanding/planning/debugging/ai_interaction/metacognition), content (JSONB), decisions (JSONB), metacognition_score
- `risk_assessments`: id, student_id, commission_id, assessment_type (dependency/disengagement/stagnation), risk_level (low/medium/high/critical), details (JSONB)

### Sistema de eventos en 3 niveles

| Bus Event (Redis) | CTR Event (DB) | N4 Level |
|-------------------|---------------|---------|
| reads_problem | reads_problem | N1 |
| code.snapshot.captured | code.snapshot | N2 |
| code.executed | code.run | N3 |
| tutor.interaction.completed | tutor.question_asked / tutor.response_received | N4 |
| exercise.submitted | submission.created | N2/N3 |
| reflection.submitted | reflection.submitted | — (metacognitivo) |
| — | session.started / session.closed | — (lifecycle) |

Indicadores comportamentales inferidos (NO event_types): asks_clarification(N1), defines_strategy(N2), asks_hint(N2), interprets_error(N3), fixes_error(N3), asks_explanation(N4), audits_ai_suggestion(N4)

### Puntos de integración críticos
1. Fase 4 → Fase 1: Alumno ejecuta código (`POST /api/v1/student/exercises/{id}/run`)
2. Fase 4 → Fase 2: Alumno chatea con tutor (WebSocket `/ws/tutor/chat`)
3. Fases 1,2 → Fase 3: Acciones generan eventos cognitivos (Event Bus)
4. Fase 4 → Fase 3: Docente ve métricas (`GET /api/v1/teacher/courses/{id}/dashboard`)

### Componentes del Tutor Orchestrator (5)
1. Pre-procesador (normaliza, idioma, contexto)
2. Constructor de contexto (prompt completo)
3. Cliente LLM (Anthropic, streaming)
4. Post-procesador / Guardrails (detecta soluciones, reformula)
5. Registrador de interacción (persiste, clasifica N4, policy check)

### Componentes del Motor Cognitivo (5)
1. Cognitive Event Classifier (event_type → N4)
2. CTR Builder (hash chain, validez)
3. Cognitive Worker (métricas N1-N4 + Qe)
4. Risk Worker (dependency, disengagement, stagnation)
5. Evaluation Engine (E = f(N1,N2,N3,N4,Qe))

---

## 04_reglas_de_negocio.md — Datos Clave

### Reglas Normativas (no negociables, del modelo teórico)

| ID | Regla | Enforcement | Violación típica |
|----|-------|-------------|-----------------|
| RN-1 | No evaluación sin trazabilidad | Evaluation Engine valida existencia de eventos | Score sin CTR |
| RN-2 | No métrica sin interpretación | Cada métrica documentada en rúbrica N4 | Campo numérico sin significado pedagógico |
| RN-3 | No dato sin contexto | Schema requiere timestamp, session_id, payload | Evento como log genérico |
| RN-4 | No IA sin registro | tutor_interactions registra todo + prompt_hash | Llamar LLM sin persistir |
| RN-5 | No evaluación binaria | Siempre 4 scores + Qe + dependency | Reportar solo "7.5" |
| RN-6 | Tutor nunca entrega soluciones | Guardrails + governance_event | Bloque >5 líneas o solución completa |
| RN-7 | CTR inmutable post-cierre | Hash chain SHA-256 | Modificar evento post-cierre |
| RN-8 | Propiedad de datos por fase | Permisos DB + contratos API | Frontend INSERT en cognitive_events |

### Reglas Operativas

| ID | Regla | Detalle |
|----|-------|---------|
| RO-1 | CTR mínimo viable | ≥1 evento por N1-N4 → is_valid_ctr. Si no cumple, CTR existe pero no sostiene conclusiones formales |
| RO-2 | Rate limiting tutor | 30 msg/hr por alumno por ejercicio → HTTP 429 |
| RO-3 | Sandbox ejecución | 10s timeout, 128MB, sin red, sin FS fuera /tmp. Dev=subprocess, Prod=Docker+seccomp |
| RO-4 | Versionado prompts | Semver + sha256_hash + flag active. Cambio genera governance event, requiere admin |
| RO-5 | Reflexión obligatoria | Post-submission, formulario guiado. Si omite, submission OK pero CTR sin metacognición |
| RO-6 | Snapshots automáticos | Cada 30s + ante ejecución. `edit_distance_from_previous` para análisis evolutivo |

### Reglas de Gobernanza

| ID | Regla |
|----|-------|
| RG-1 | Subordinación técnica: arquitectura depende del modelo, no al revés |
| RG-2 | No degradación semántica: evento cognitivo ≠ log técnico |
| RG-3 | Coherencia evaluativa: evaluación no puede derivarse solo de submissions.score |
| RG-4 | Versionado semántico empate3: mayor(X.0)=constructo estable, menor(X.Y)=operativo provisional, refinamiento(X.Y.Z)=en refinamiento |
| RG-5 | Auditor de coherencia: verifica vocabulario canónico, excepciones, versionado, desacoples |

### Matriz de validación (5 preguntas para auditar decisiones técnicas)
1. ¿Qué constructo de la tesis justifica este componente?
2. ¿Qué evidencia produce o consume?
3. ¿En qué tabla queda persistida?
4. ¿Qué endpoint habilita su operación?
5. ¿Cómo impacta en la evaluación?

---

## 05_flujos_principales.md — Datos Clave

### 5 flujos documentados

**Flujo 1 — Alumno resuelve ejercicio (E2E, 14 pasos)**:
Login → Dashboard → Selecciona ejercicio → Inicia cognitive_session → Lee enunciado (N1) → Escribe código (snapshots 30s) → Ejecuta sandbox (N3) → Chatea tutor (N4) → Modifica y pasa tests (N3) → Submit → Cierra sesión → Reflexión → Fase 3 calcula métricas → Docente ve dashboard

**Flujo 2 — Diálogo con tutor socrático**:
Mensaje alumno → Pre-procesador → Constructor contexto → Cliente LLM (streaming) → Post-procesador/Guardrails → Registrador → Event Bus → Fase 3
- Clasificación N4: critical | exploratory | dependent
- Policy check: ok | violation_detected | reformulated

**Flujo 3 — Docente analiza dashboard**:
Login → Selecciona comisión → Dashboard (promedios N1-N4, distribución Qe, alumnos riesgo, ejercicios difíciles) → Click alumno riesgo → Perfil (radar, evolución, dependency) → Traza cognitiva (timeline, diff código, chat) → Identifica patrón → Intervención presencial

**Flujo 4 — Construcción del CTR**:
Eventos crudos (Event Bus) → Event Classifier (type + N4) → CTR Builder (hash chain, sequence, validación mínima) → Cognitive Worker (scores N1-N4, Qe, dependency, reflection_score, success_efficiency) → Risk Worker (periódico, dependency/disengagement/stagnation)

**Flujo 5 — Validación de integridad CTR**:
Seleccionar sesión → Obtener eventos por sequence → Recalcular hash chain → Comparar con ctr_hash_chain → Íntegro o comprometido (governance_event)

### Detalle Event Bus — Fases origen de eventos

| Acción | Fase origen | Evento | N4 |
|--------|------------|--------|-----|
| Lee enunciado | Fase 4 | reads_problem | N1 |
| Reformula en chat | Fase 2 | reformulates_problem | N1 |
| Pide aclaración | Fase 2 | asks_clarification | N1 |
| Define estrategia | Fase 4 | defines_strategy | N2 |
| Cambia estrategia | Fase 4 | changes_strategy | N2 |
| Pide hint | Fase 2 | asks_hint | N2 |
| Ejecuta código | Fase 1 | runs_test | N3 |
| Interpreta error | Fase 4 | interprets_error | N3 |
| Corrige error | Fase 4 | fixes_error | N3 |
| Pide explicación | Fase 2 | asks_explanation | N4 |
| Audita sugerencia | Fase 2 | audits_ai_suggestion | N4 |

### Métricas calculadas por Cognitive Worker
- Scores N1-N4 (basados en rúbrica)
- Qe = f(quality_prompt, critical_evaluation, integration, verification)
- dependency_score = ratio eventos N4 "dependent"
- reflection_score (basado en reflexión post-ejercicio)
- success_efficiency = score / (intentos + tiempo)

---

## 06_backlog.md — Datos Clave

### Prioridades
| Prioridad | Significado |
|-----------|------------|
| P0 | Bloqueante, sin esto nada funciona |
| P1 | Necesario para MVP funcional |
| P2 | Mejora significativa no bloqueante |
| P3 | Nice-to-have para piloto |

### Items por fase
- **Fase 0**: #1-#7 (7 items)
- **Fase 1**: #8-#17 (10 items)
- **Fase 2**: #18-#30 (13 items, incluye #29-#30 como P3 futuro)
- **Fase 3**: #31-#45 (15 items)
- **Fase 4**: #46-#63 (18 items)
- **Integración/QA**: #64-#70 (7 items)
- **Total**: 70 items

### Dependencias bloqueantes notables
- Risk Worker (#42) es **dependencia bloqueante** para dashboard docente (#56 frontend)
- E3-S5 Risk Worker es bloqueante para E4-S4 Dashboard docente
- MSW (#47) depende de OpenAPI spec (#5)
- Toda Fase 1-4 depende de Fase 0 completada

### Items P3 (futuro, no MVP)
- #29: Adapter OpenAI
- #30: Adapter Ollama local

---

## INCONSISTENCIAS DETECTADAS Y RESUELTAS

### IC-1: FK de exercises — commission_id vs course_id (RESUELTA)

- **Problema**: 03_features_y_epics.md decía `commission_id`, CLAUDE.md decía `Course → Exercise`
- **Decisión**: `exercises.course_id` (FK → courses). En contexto UTN, el curso define el currícula. Las comisiones son secciones. Si se necesita granularidad futura, se agrega tabla pivot.
- **Fix aplicado**: Corregido en 03_features_y_epics.md

### IC-2: Conteo de prioridades en backlog (RESUELTA)

- **Problema**: Los parciales estaban mal (P0=28→32, P1=29→28, P2=10→8, P3=3→2)
- **Fix aplicado**: Corregido en 06_backlog.md con conteo real

### IC-3: RBAC docente/tutor — diferente granularidad (ACLARADA)

- **Situación**: 02_actores_y_roles dice docente="—" en tutor chat, CLAUDE.md dice "ver sesiones"
- **Resolución**: No es contradicción. Docente no CHATEA pero sí VE sesiones pasadas. Las tablas usan diferente granularidad. Ambas correctas en su contexto.

### IC-4: tutor_interactions.session_id (RESUELTA)

- **Decisión**: `session_id` es correlación lógica con `cognitive_sessions.id`, SIN FK estricta a nivel DB. Fase 2 recibe el ID del frontend y lo almacena. Respeta ownership entre fases (RN-8).
- **Fix aplicado**: Aclarado en 03_features_y_epics.md con nota en la definición del modelo

### IC-5: cognitive_metrics campos faltantes (RESUELTA)

- **Problema**: Faltaban qe_score, qe_components, dependency_score, reflection_score, success_efficiency
- **Fix aplicado**: Campos agregados a la definición del modelo en 03_features_y_epics.md

### IC-6: Reflexión post-ejercicio — event_type faltante (RESUELTA)

- **Decisión**: event_type = `submits_reflection`, sin nivel N4 (es metacognitivo, transversal). Alimenta reflection_score por separado.
- **Fix aplicado**: Agregado al mapeo event_type → N4 en 03 y a la tabla de Event Bus en 05

### IC-7: Indicador Código↔Discurso — sin EPIC ni backlog (RESUELTA)

- **Decisión**: Post-MVP. Los datos se capturan en v1 (snapshots + interactions con timestamps), el indicador se construye después sin cambios de schema.
- **Fix aplicado**: Nota agregada en 01_vision_y_contexto.md
