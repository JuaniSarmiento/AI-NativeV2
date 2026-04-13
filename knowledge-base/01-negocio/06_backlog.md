# Backlog Priorizado

## Criterios de Priorización

| Prioridad | Significado | Criterio |
|-----------|------------|---------|
| **P0 — Critical** | Bloqueante para el sistema. Sin esto, nada funciona | Fase 0 o core path del alumno |
| **P1 — High** | Necesario para el MVP funcional | Completa el flujo end-to-end |
| **P2 — Medium** | Mejora significativa pero no bloqueante | Dashboard docente, reportes |
| **P3 — Low** | Nice-to-have para piloto | Optimizaciones, features secundarios |

## Fase 0 — Fundación (Semanas 1-2, todo el equipo)

| # | Item | Prioridad | Owner | Dependencias | Done when |
|---|------|-----------|-------|-------------|-----------|
| 1 | Monorepo + estructura de directorios | P0 | Todos | — | `backend/`, `frontend/`, `shared/`, `infra/` creados con configs base |
| 2 | Docker Compose dev | P0 | Todos | #1 | `docker compose up` levanta api + db + redis + frontend |
| 3 | PostgreSQL + 4 schemas | P0 | Todos | #2 | Schemas operational, cognitive, governance, analytics creados |
| 4 | Auth JWT + RBAC | P0 | Todos | #3 | Login/registro funcional, middleware RBAC, refresh rotation |
| 5 | OpenAPI spec | P1 | Todos | #3 | Spec YAML completo, tipos TS auto-generados |
| 6 | CI pipeline | P1 | Todos | #1 | GitHub Actions: lint + tests + build |
| 7 | Seed data | P2 | Todos | #3, #4 | 1 curso, 1 comisión, 3 ejercicios, 2 usuarios |

## Fase 1 — Core Académico (Semanas 3-12, Dev 1)

| # | Item | Prioridad | Dependencias | Done when |
|---|------|-----------|-------------|-----------|
| 8 | Modelos SQLAlchemy: courses, commissions, enrollments | P0 | Fase 0 | Modelos + migración Alembic + repo base |
| 9 | CRUD cursos + comisiones | P0 | #8 | Endpoints REST, tests integration |
| 10 | Modelos: exercises, submissions, code_snapshots | P0 | #8 | Modelos con JSONB (test_cases, topic_taxonomy) |
| 11 | CRUD ejercicios | P0 | #10 | Filtros por curso, dificultad, topic |
| 12 | Sandbox Python | P0 | — | subprocess seguro, timeout 10s, 128MB |
| 13 | Submission flow | P0 | #10, #12 | draft → ejecutar → ver resultado → enviar |
| 14 | Test cases runner | P1 | #12 | Assertions individuales, reporte pass/fail |
| 15 | Code snapshots automáticos | P1 | #10 | Cada 30s + ante ejecución, edit_distance |
| 16 | Endpoint de ejecución | P1 | #12 | POST /run → stdout, stderr, runtime_ms, test_results |
| 17 | Tests integration sandbox | P1 | #12 | Edge cases: timeout, memory, syntax error |

## Fase 2 — Tutor IA (Semanas 3-12, Dev 2)

| # | Item | Prioridad | Dependencias | Done when |
|---|------|-----------|-------------|-----------|
| 18 | Modelos: tutor_interactions, tutor_system_prompts | P0 | Fase 0 | Modelos + migración |
| 19 | WebSocket endpoint /ws/tutor/chat | P0 | #18 | Handshake con JWT, streaming |
| 20 | System prompt socrático v1 | P0 | — | Prompt basado en Anexo A de active6.docx |
| 21 | Constructor de contexto | P0 | #19, #20 | Ejercicio + código + historial + restricciones |
| 22 | Cliente LLM (Anthropic adapter) | P0 | — | Streaming, token count, error handling |
| 23 | Post-procesador / guardrails | P0 | #22 | Detecta soluciones directas, reformula |
| 24 | Clasificación N4 | P1 | #19 | critical/exploratory/dependent por turno |
| 25 | Reflexión post-ejercicio | P1 | #18 | Formulario guiado, persiste respuestas |
| 26 | Governance events (violations) | P1 | #23 | Registra violaciones de policy |
| 27 | Versionado de prompts con SHA-256 | P1 | #20 | Hash en cada interacción registrada |
| 28 | Tests adversarios (20+) | P1 | #23 | Intentos de extraer solución → todos bloqueados |
| 29 | Adapter OpenAI (futuro) | P3 | #22 | Protocol LLMAdapter para invariancia |
| 30 | Adapter Ollama local (futuro) | P3 | #22 | Para testing sin cuota API |

## Fase 3 — Motor Cognitivo (Semanas 3-12, Dev 3)

| # | Item | Prioridad | Dependencias | Done when |
|---|------|-----------|-------------|-----------|
| 31 | Modelos: cognitive_sessions, cognitive_events | P0 | Fase 0 | Modelos + migración, JSONB payload |
| 32 | Event Bus consumer | P0 | #31 | Consume eventos de Fases 1 y 2 |
| 33 | Cognitive Event Classifier | P0 | #32 | Mapeo event_type → N4 según empate3 |
| 34 | CTR Builder + hash chain | P0 | #33 | SHA-256 encadenado, sequence_number |
| 35 | Validación CTR mínimo | P0 | #34 | is_valid_ctr = ≥1 evento por N1-N4 |
| 36 | Modelos: cognitive_metrics, reasoning_records | P1 | #31 | Modelos + migración |
| 37 | Cognitive Worker (scores N1-N4) | P1 | #34, #36 | Scores basados en rúbrica N4 |
| 38 | Calidad epistémica (Qe) | P1 | #37 | Constructo jerárquico: 4 componentes |
| 39 | Dependency score | P1 | #37 | Ratio de interacciones "dependent" |
| 40 | Evaluation Engine | P1 | #37, #38 | E = f(N1, N2, N3, N4, Qe) |
| 41 | Modelos: risk_assessments | P1 | #31 | Modelo + migración |
| 42 | Risk Worker | P1 | #37, #41 | Dependency, disengagement, stagnation — dependencia bloqueante para dashboard docente (#56) |
| 43 | Dashboard endpoints (agregados) | P1 | #37, #42 | GET /dashboard con promedios y riesgo |
| 44 | Endpoint traza cognitiva | P2 | #34 | Timeline de eventos + código + chat |
| 45 | Validación de integridad CTR | P2 | #34 | Endpoint de auditoría hash chain |

## Fase 4 — Frontend (Semanas 3-12, Dev 4)

| # | Item | Prioridad | Dependencias | Done when |
|---|------|-----------|-------------|-----------|
| 46 | Setup React + Vite + Zustand + TailwindCSS | P0 | Fase 0 | Build funcional, hot reload |
| 47 | MSW (Mock Service Worker) | P0 | #5 | Mocks basados en OpenAPI spec |
| 48 | Auth store + login/registro | P0 | #47 | useAuthStore, JWT en headers |
| 49 | Layout base + routing | P0 | #46 | Rutas alumno vs docente, protected routes |
| 50 | Dashboard alumno | P0 | #49 | Cursos, ejercicios, progreso |
| 51 | Vista ejercicio (3 paneles) | P0 | #50 | Monaco + chat + output |
| 52 | Integración Monaco Editor | P0 | #51 | Syntax highlighting Python, auto-save |
| 53 | Panel de ejecución + output | P0 | #51 | Ejecutar, ver stdout/stderr/tests |
| 54 | Chat streaming WebSocket | P0 | #51 | Tokens progresivos, reconexión |
| 55 | Panel reflexión | P1 | #51 | Formulario guiado post-submission |
| 56 | Dashboard docente | P1 | #49 | Indicadores agregados de comisión |
| 57 | Radar chart N1-N4 | P1 | #56 | Recharts, perfil individual de alumno |
| 58 | Tabla alumnos en riesgo | P1 | #56 | Color-coded por risk_level |
| 59 | Traza cognitiva visual | P2 | #56 | Timeline color-coded + diff + chat |
| 60 | Patrones de ejercicio | P2 | #56 | Vista agregada de estrategias |
| 61 | Reportes de gobernanza | P2 | #56 | Violaciones, cambios prompts |
| 62 | Responsive tablet | P2 | #51, #56 | Funcional en iPad/tablet |
| 63 | Historial submissions alumno | P2 | #50 | Lista con scores multidimensionales |

## Integración y QA (Semanas 13-16)

| # | Item | Prioridad | Dependencias | Done when |
|---|------|-----------|-------------|-----------|
| 64 | Remover MSW, conectar APIs reales | P0 | Fases 1-4 | Frontend funciona con backend real |
| 65 | Testing E2E con Playwright | P0 | #64 | Flujo completo alumno end-to-end |
| 66 | Testing E2E docente | P1 | #64 | Dashboard → traza cognitiva |
| 67 | Performance testing sandbox | P1 | — | 10+ ejecuciones concurrentes |
| 68 | Deploy a staging | P1 | #64 | Docker Compose prod funcional |
| 69 | Prueba con usuarios piloto | P1 | #68 | 1 comisión real, feedback |
| 70 | Fix bugs de integración | P1 | #64-#69 | Backlog de bugs a cero |

## Resumen por Prioridad

| Prioridad | Total items | % del backlog |
|-----------|------------|---------------|
| P0 — Critical | 28 | 40% |
| P1 — High | 29 | 41% |
| P2 — Medium | 10 | 14% |
| P3 — Low | 3 | 4% |
| **Total** | **70** | **100%** |
