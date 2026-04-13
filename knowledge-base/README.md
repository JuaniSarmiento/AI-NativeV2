# Knowledge Base — Plataforma AI-Native

## Índice de Navegación

### 01 — Negocio

| Archivo | Contenido |
|---------|----------|
| [01_vision_y_contexto.md](01-negocio/01_vision_y_contexto.md) | Problema, solución, modelo N4, CTR, calidad epistémica, contexto institucional |
| [02_actores_y_roles.md](01-negocio/02_actores_y_roles.md) | Estudiante, docente, admin, tutor IA. Matriz de permisos RBAC |
| [03_features_y_epics.md](01-negocio/03_features_y_epics.md) | 5 EPICs (Fase 0-4), stories priorizadas, dependencias, criterios de completitud |
| [04_reglas_de_negocio.md](01-negocio/04_reglas_de_negocio.md) | Reglas normativas (RN-1 a RN-8), operativas (RO-1 a RO-6), gobernanza (RG-1 a RG-5) |
| [05_flujos_principales.md](01-negocio/05_flujos_principales.md) | Flujo end-to-end alumno, diálogo socrático, dashboard docente, construcción CTR |
| [06_backlog.md](01-negocio/06_backlog.md) | 70 items priorizados P0-P3, organizados por fase, con dependencias |

### 02 — Arquitectura

| Archivo | Contenido |
|---------|----------|
| [01_arquitectura_general.md](02-arquitectura/01_arquitectura_general.md) | C4 model, capas, 4 schemas PostgreSQL, estructura backend/frontend |
| [02_modelo_de_datos.md](02-arquitectura/02_modelo_de_datos.md) | Todas las tablas, campos, tipos, relaciones, índices, JSONB, hash chain |
| [03_api_y_endpoints.md](02-arquitectura/03_api_y_endpoints.md) | Todos los endpoints REST + WebSocket, request/response schemas |
| [04_patrones_de_diseno.md](02-arquitectura/04_patrones_de_diseno.md) | Repository, UoW, Domain Service, Event Bus, Hash Chain, DI, Strategy, Guard |
| [05_eventos_y_websocket.md](02-arquitectura/05_eventos_y_websocket.md) | WebSocket streaming del tutor, Event Bus entre fases, eventos cognitivos |
| [06_abstracciones_y_contratos.md](02-arquitectura/06_abstracciones_y_contratos.md) | Interfaces, contratos OpenAPI, LLM Protocol, base classes, excepciones |
| [07_adrs.md](02-arquitectura/07_adrs.md) | 7 ADRs: monolito, hash chain, WebSocket, Event Bus, sandbox, LLM adapters, schemas |

### 03 — Seguridad

| Archivo | Contenido |
|---------|----------|
| [01_modelo_de_seguridad.md](03-seguridad/01_modelo_de_seguridad.md) | JWT + refresh rotation, RBAC, rate limiting, CORS, security headers |
| [02_superficie_de_ataque.md](03-seguridad/02_superficie_de_ataque.md) | Análisis de superficie: sandbox, tutor LLM, API, WebSocket, CTR, frontend |

### 04 — Infraestructura

| Archivo | Contenido |
|---------|----------|
| [01_configuracion.md](04-infraestructura/01_configuracion.md) | Variables de entorno, pydantic-settings, Docker Compose, dev vs prod |
| [02_dependencias.md](04-infraestructura/02_dependencias.md) | Python + Node dependencies, version pinning, security updates |
| [03_deploy.md](04-infraestructura/03_deploy.md) | Docker dev/prod, nginx, GitHub Actions CI/CD, health checks |
| [04_migraciones.md](04-infraestructura/04_migraciones.md) | Alembic multi-schema, auto-generate, seed data, pitfalls |
| [05_integraciones.md](04-infraestructura/05_integraciones.md) | Anthropic API, LLM adapters, Monaco Editor, Recharts, MSW |

### 05 — Developer Experience

| Archivo | Contenido |
|---------|----------|
| [01_onboarding.md](05-dx/01_onboarding.md) | Setup completo para nuevo desarrollador, verificación, IDE |
| [02_tooling.md](05-dx/02_tooling.md) | Herramientas: uvicorn, pytest, Vite, Docker, git hooks |
| [03_trampas_conocidas.md](05-dx/03_trampas_conocidas.md) | Gotchas del stack: SQLAlchemy async, Zustand, hash chain, sandbox |
| [04_convenciones_y_estandares.md](05-dx/04_convenciones_y_estandares.md) | Naming, schemas, endpoints, commits, branching, imports, types |
| [05_workflow_implementacion.md](05-dx/05_workflow_implementacion.md) | Proceso de 9 pasos para implementar un feature, con ejemplo |
| [06_estrategia_de_testing.md](05-dx/06_estrategia_de_testing.md) | Pirámide de tests, adversarial tutor tests, testcontainers, CI |

### 06 — Estado del Proyecto

| Archivo | Contenido |
|---------|----------|
| [01_roadmap.md](06-estado/01_roadmap.md) | Timeline: Fase 0 → piloto → iteraciones futuras |
| [02_preguntas_y_suposiciones.md](06-estado/02_preguntas_y_suposiciones.md) | Suposiciones activas, preguntas abiertas, defaults aplicados |
| [03_salud_del_proyecto.md](06-estado/03_salud_del_proyecto.md) | Plantilla de estado semanal por fase |
| [04_deuda_tecnica.md](06-estado/04_deuda_tecnica.md) | Registro de deuda técnica (vacío — greenfield) |
| [05_inconsistencias.md](06-estado/05_inconsistencias.md) | Log de inconsistencias detectadas por validación |

### 07 — Anexos

| Archivo | Contenido |
|---------|----------|
| [01_referencia_skills.md](07-anexos/01_referencia_skills.md) | 7 Claude Code skills con patrones de código |
| [02_estructura_de_codigo.md](07-anexos/02_estructura_de_codigo.md) | Árbol completo de directorios backend + frontend |
| [03_glosario.md](07-anexos/03_glosario.md) | 16 términos del dominio AI-Native (desde empate3) |

---

**Total**: 35 archivos de documentación + 8 resúmenes consolidados en `_resumen/` | **Fuente de verdad**: `scaffold-decisions.yaml`
