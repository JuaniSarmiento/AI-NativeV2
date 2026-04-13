# Prompt de Auditoría — Knowledge Base + EPICs

Sos un auditor técnico. Tu trabajo es encontrar TODAS las inconsistencias en la documentación de este proyecto. No arregles nada — solo reportá.

## Contexto del proyecto

Plataforma AI-Native: sistema pedagógico-tecnológico para enseñanza de programación universitaria (UTN FRM). Tutor IA socrático + registro cognitivo (CTR) + evaluación multidimensional N4.

## Qué auditar

Carpeta `knowledge-base/` (7 subcarpetas, 35 archivos) + carpeta `epics/` (19 archivos) + `CLAUDE.md` + `AGENTS.md` + `Historias de Usuario.md`.

## Fuentes de verdad (en orden de prioridad)

1. **Modelo de datos**: `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
2. **Endpoints API**: `knowledge-base/02-arquitectura/03_api_y_endpoints.md`
3. **Eventos y WebSocket**: `knowledge-base/02-arquitectura/05_eventos_y_websocket.md`
4. **Seguridad**: `knowledge-base/03-seguridad/01_modelo_de_seguridad.md`
5. **EPICs**: `epics/EPIC-*.md` (implementación planificada)

Si dos docs se contradicen, el de mayor prioridad en esta lista es correcto.

## Qué buscar

### 1. Modelo de datos — verificar en TODOS los archivos

- `exercises` debe tener `course_id (FK → courses.id)`, NUNCA `commission_id`
- `tutor_interactions` debe tener `session_id` (correlación lógica, sin FK cross-schema)
- `cognitive_sessions` debe tener `commission_id` (denormalizado)
- `cognitive_events` NO tiene `user_id` (se obtiene vía session → student_id)
- `cognitive_metrics` debe tener: n1-n4 scores, qe_score, qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification, dependency_score, reflection_score, success_efficiency, total_interactions, help_seeking_ratio, autonomy_index, risk_level, computed_at
- `risk_assessments` usa `commission_id`, NO `course_id`
- `reasoning_records` usa `event_hash`, NO `current_hash`
- Hash campo canónico: `event_hash` en todas las tablas. NUNCA `hash` ni `current_hash`
- `courses` NO tiene campo `semester` (semester está en commissions)
- `commissions` tiene `teacher_id (FK → users.id)` y `semester`
- Tabla `reflections` existe en schema operational (campos: difficulty_perception, strategy_description, ai_usage_evaluation, what_would_change, confidence_level)
- Tabla `event_outbox` existe en schema operational
- Tabla `reasoning_records` existe en schema cognitive

### 2. Naming — verificar consistencia

- Excepción base: `DomainError` (NO `DomainException`)
- Hash service: `HashChainService` (clase, NO funciones sueltas como `compute_ctr_hash`)
- Hash ubicación: `app/features/cognitive/hash_chain.py` (NO `app/core/hash_chain.py`)
- Archivo env template: `env.example` (NO `.env.example`)
- Rate limiting: Sliding Window (ZSET) (NO Token Bucket)

### 3. Endpoints — verificar en TODOS los archivos

- Exercises: `GET/POST /api/v1/courses/{course_id}/exercises` (NO bajo `/commissions/`)
- Sandbox: `POST /api/v1/student/exercises/{id}/run` (con prefix `/student/`)
- Tutor chat: `WS /ws/tutor/chat?token=<jwt>` (NO `/ws/tutor/{session_id}`, NO REST POST)
- Reflexión: `POST /api/v1/submissions/{id}/reflection`
- Healthcheck: `GET /api/v1/health` (NO `/health` a secas)
- Frontend env: `VITE_API_URL` (NO `VITE_API_BASE_URL`), valor `http://localhost:8000` (sin `/api/v1`)

### 4. Event types — sistema de 3 niveles

Los nombres del Event Bus (Redis), del CTR (cognitive_events), y los indicadores N4 son DISTINTOS:

| Bus Event | CTR Event | N4 |
|-----------|-----------|-----|
| reads_problem | reads_problem | N1 |
| code.snapshot.captured | code.snapshot | N2 |
| code.executed | code.run | N3 |
| tutor.interaction.completed | tutor.question_asked / tutor.response_received | N4 |
| exercise.submitted | submission.created | N2/N3 |
| reflection.submitted | reflection.submitted | — (metacognitivo) |

Los indicadores comportamentales (asks_clarification, defines_strategy, etc.) son INFERIDOS, no event_types del CTR.

### 5. Fases — naming correcto

- Fase 0: Fundación (Infra + DB + Auth + Contratos)
- Fase 1: Core Académico (Cursos, Ejercicios, Sandbox, Submissions)
- Fase 2: Tutor IA (Chat, Guardrails, Clasificación N4, Governance, Reflexión)
- Fase 3: Motor Cognitivo + Evaluación (CTR, Métricas, Risk, Traza Visual)
- Fase 4: Frontend Completo (NO "Evaluación Cognitiva N4")

### 6. Governance ownership

- Schema `governance` es compartido: Fase 2 ESCRIBE governance_events (al detectar violaciones), Admin GESTIONA tutor_system_prompts, Fase 3 AUDITA
- NO es "Owner: Fase 3" exclusivamente

### 7. Auth / Seguridad

- Access token: 15 min, JWT HS256
- Refresh token: 7 días, cookie httpOnly SameSite=Strict
- Redis keys auth: `auth:refresh:{jti}`, `auth:blacklist:{jti}` (NO `token:blacklist:`)
- WS auth: JWT en query param `?token=`, verificación ANTES de websocket.accept()
- Sandbox: timeout 10s, 128MB, asyncio.create_subprocess_exec (NO subprocess.Popen)

### 8. Cross-references

- Verificar que las referencias a archivos de KB en las EPICs apuntan a archivos que existen
- Verificar que los "Blocked by" / "Blocks" entre EPICs son bidireccionales (si EPIC-05 dice "Blocks: EPIC-06", entonces EPIC-06 debe decir "Blocked by: EPIC-05")
- Verificar que no hay tablas fantasma (mencionadas en un doc pero no en el modelo canónico): `analytics.student_metrics`, `analytics.exercise_attempts`, `analytics.course_stats`, `analytics.session_metrics` NO existen

## Formato de reporte

Para cada inconsistencia encontrada:

```
### [ID]: [Título corto]
- **Archivo A**: [path]:línea — dice [X]
- **Archivo B**: [path]:línea — dice [Y]
- **Canónico**: [cuál es correcto según fuentes de verdad]
- **Severidad**: CRÍTICA | ALTA | MEDIA | BAJA
```

Al final, un resumen con conteo por severidad.

## IMPORTANTE

- No arregles nada, solo reportá
- Sé exhaustivo — revisá CADA archivo
- Si un archivo tiene una referencia a `analytics.session_metrics` o `exercise_attempts`, reportalo — esas tablas no existen
- Si encontrás un endpoint que no coincide con la API canónica, reportalo
- Si encontrás un campo de modelo que no coincide con 02_modelo_de_datos.md, reportalo
- Los archivos en `_resumen/` son auxiliares — si tienen datos desactualizados vs los archivos fuente, reportalo pero con severidad BAJA
