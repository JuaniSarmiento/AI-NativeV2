# Comparación Cross-Folder — Auditoría Final

> Última actualización: 2026-04-13
> Compara datos entre las 7 carpetas del knowledge-base para detectar inconsistencias residuales.

---

## 1. Modelo de Datos — Estado Final

### Fuente de verdad: `02-arquitectura/02_modelo_de_datos.md`

Todas las carpetas ahora están alineadas con este archivo como fuente canónica.

| Tabla | Schema | FK clave | Verificado en |
|-------|--------|----------|---------------|
| exercises | operational | course_id → courses | 01, 02, 04 ✅ |
| enrollments | operational | commission_id → commissions | 01, 02, 04 ✅ |
| risk_assessments | analytics | commission_id | 01, 02, 04 ✅ |
| tutor_interactions | operational | session_id (correlación, sin FK cross-schema) | 01, 02, 04 ✅ |
| cognitive_events | cognitive | event_hash (no current_hash) | 02, 05, 07 ✅ |
| reflections | operational | submission_id (UNIQUE) | 02, 03_api, 04 ✅ |
| event_outbox | operational | outbox pattern | 02, 04, 05 ✅ |

### Campos unificados en cognitive_metrics
n1-n4 scores, qe_score, qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification, dependency_score, reflection_score, success_efficiency, total_interactions, help_seeking_ratio, autonomy_index, risk_level, computed_at

---

## 2. Event Types — Sistema de 3 Niveles (UNIFICADO)

### Fuente de verdad: `01-negocio/03_features_y_epics.md` (tabla unificada)

| Bus Event (Redis Streams) | CTR Event (cognitive_events) | N4 Level |
|--------------------------|----------------------------|---------|
| reads_problem | reads_problem | N1 |
| code.snapshot.captured | code.snapshot | N2 |
| code.executed | code.run | N3 |
| tutor.interaction.completed | tutor.question_asked | N4 |
| tutor.interaction.completed | tutor.response_received | N4 |
| exercise.submitted | submission.created | N2/N3 |
| reflection.submitted | reflection.submitted | — (metacognitivo) |
| — | session.started | — (lifecycle) |
| — | session.closed | — (lifecycle) |

**Indicadores comportamentales** (inferidos por Fase 3, NO almacenados como events):
asks_clarification, reformulates_problem, defines_strategy, changes_strategy, asks_hint, interprets_error, fixes_error, asks_explanation, audits_ai_suggestion

Verificado en: 01-negocio ✅, 02-arquitectura/02 ✅, 02-arquitectura/05 ✅

---

## 3. Naming — Unificado

| Concepto | Nombre canónico | Antes había |
|----------|----------------|-------------|
| Excepción base | DomainError | DomainError + DomainException |
| Hash campo | event_hash | event_hash + current_hash + hash |
| Hash service | HashChainService (clase) | funciones sueltas |
| Hash ubicación | app/features/cognitive/hash_chain.py | app/core/hash_chain.py |
| Rate limiting | Sliding Window (ZSET) | Sliding Window + Token Bucket |

---

## 4. Endpoints — Alineados

| Recurso | Ruta canónica |
|---------|--------------|
| Exercises CRUD | GET/POST /api/v1/courses/{course_id}/exercises |
| Sandbox run | POST /api/v1/student/exercises/{id}/run | POST /code/execute |
| Tutor chat | WS /ws/tutor/chat | POST /tutor/message |
| Reflexión | POST /api/v1/submissions/{id}/reflection | POST /reflection |

---

## 5. Auth — Consistente entre carpetas

| Dato | Valor | Verificado en |
|------|-------|---------------|
| Access token TTL | 15 min | 01-negocio, 03-seguridad, 04-infra ✅ |
| Refresh token TTL | 7 días | 03-seguridad, 04-infra ✅ |
| Algorithm | HS256 | 03-seguridad ✅ |
| Token storage | Access=Zustand, Refresh=httpOnly cookie | 01-negocio, 03-seguridad ✅ |
| Rate limit tutor | 30 msg/hr por user+exercise | 01-negocio, 03-seguridad, 02-arq ✅ |
| Sandbox limits | 10s timeout, 128MB RAM | 01-negocio, 02-arq, 03-seguridad, 04-infra ✅ |
| Password hash | bcrypt factor 12 | 03-seguridad ✅ |

---

## 6. Acceso Docente a CTR — Resuelto

**Decisión final**: El docente PUEDE ver la traza cognitiva de sus alumnos (timeline con eventos N1-N4, código evolutivo, chat) vía endpoint REST (`GET /teacher/sessions/{id}/trace`). NO accede directamente a la tabla cognitive_events por SQL.

Verificado en: 01-negocio/02 (RBAC) ✅, 02-arquitectura/01 (corregido) ✅, 02-arquitectura/03 (API) ✅, 03-seguridad (RBAC matrix corregida) ✅

---

## 7. Governance de Prompts — Consistente

| Owner | Mecanismo | Verificado |
|-------|-----------|-----------|
| Schema governance (Fase 2 escribe events, Admin gestiona prompts, Fase 3 audita) | tutor_system_prompts con sha256_hash, version semver, is_active (partial unique index) | 01, 02, 04, 07_adrs ✅ |
| Solo admin puede cambiar | Genera governance_event al activar/desactivar | 01, 03 ✅ |
| Cada interacción registra prompt_hash | VARCHAR(64) en tutor_interactions | 01, 02 ✅ |

---

## 8. Inconsistencias Residuales (NO fixeadas — decisión pendiente)

### CR-1: Reflexión — ¿obligatoria o no?
- 01-negocio/04_reglas (RO-5): "obligatoria" — pero si se omite, submission se acepta sin evento metacognición
- En la práctica es soft-obligatoria: la UI la muestra automáticamente, pero no bloquea
- **Acción**: Dejar como está. Es un soft requirement, no un hard block.

### CR-2: Schema ownership de governance
- 01-negocio/03: "Fase 2 es owner de governance (governance_events, tutor_system_prompts)"
- 02-arquitectura/01: "Fase 3 es owner de governance"
- **Análisis**: Fase 2 ESCRIBE governance_events (cuando guardrails detectan violación) y Fase 2 LEE tutor_system_prompts (prompt activo). Pero en 02-arquitectura, governance es "owner: Fase 3".
- **Acción necesaria**: Resolver quién escribe governance_events — ¿Fase 2 o Fase 3? Si Fase 2 escribe, governance debería tener ownership compartido o Fase 2 debería emitir evento al bus y Fase 3 lo persiste.

### CR-3: commissions.schedule — campo fantasma
- 01-negocio/03 tiene `schedule` en commissions
- 02-arquitectura/02 NO tiene schedule
- **Acción**: Remover schedule de 01-negocio (no está en el modelo canónico)

---

## 9. Fixes Aplicados — Primera Comparación

1. Acceso docente a CTR aclarado en 02-arquitectura/01
2. subprocess.Popen → asyncio.create_subprocess_exec en ADR-005
3. Resúmenes actualizados: courses sin semester, risk_assessments con commission_id, DomainError unificado, event_type mapeo actualizado

## 10. Fixes Aplicados — Segunda Pasada (post-review)

4. "Fase 4 = Frontend" unificado en 06-estado/01_roadmap, 03_salud, 02_preguntas (era "Evaluación")
5. WS /ws/tutor/chat unificado en 07-anexos/02_estructura y 01_referencia_skills (era /ws/tutor/{session_id})
6. DX/convenciones: endpoints de exercises y tutor alineados con API canónica
7. CognitiveEvent.user_id removido de index example en DX/convenciones
8. Glosario: analytics.session_metrics → cognitive.cognitive_metrics, estructura CTR alineada con modelo canónico
9. Env vars unificadas en onboarding (DATABASE_URL, HOST, PORT, VITE_API_URL)
10. Healthcheck: /api/v1/health unificado en onboarding
11. Tooling: BACKEND_HOST → HOST, BACKEND_PORT → PORT
12. hash_chain import path corregido en testing (línea 92 que quedaba)
13. Governance ownership aclarado en 02-arquitectura/01 (Fase 2 escribe, admin gestiona prompts, Fase 3 audita)
14. Meta-claim de 05_inconsistencias actualizado con auditoría real
15. Workflow: exercises endpoint alineado con /courses/{id}/exercises
16. README: nota sobre 8 resúmenes adicionales en _resumen/
