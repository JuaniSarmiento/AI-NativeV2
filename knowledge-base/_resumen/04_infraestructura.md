# Resumen Consolidado — 04-infraestructura

> 5 archivos. Última actualización: 2026-04-13

---

## 01_configuracion.md — Datos Clave

### Variables de entorno backend (env.example)
- APP: APP_NAME, APP_VERSION, DEBUG, ENVIRONMENT
- Seguridad: SECRET_KEY (256 bits), ACCESS_TOKEN_EXPIRE_MINUTES=15, REFRESH_TOKEN_EXPIRE_DAYS=7, ALLOWED_ORIGINS
- DB: DATABASE_URL (postgresql+asyncpg://), POOL_SIZE=10, MAX_OVERFLOW=20, POOL_TIMEOUT=30
- Redis: REDIS_URL, REDIS_PASSWORD, REDIS_SSL
- Anthropic: ANTHROPIC_API_KEY, ANTHROPIC_MODEL=claude-sonnet-4-20250514, MAX_TOKENS=4096, TEMPERATURE=0.7, TIMEOUT=30
- Rate limiting: configurable vía env vars (RATE_LIMIT_TUTOR_MESSAGES=30, etc.)
- Sandbox: SANDBOX_TIMEOUT=10, SANDBOX_MEMORY_MB=128, SANDBOX_ALLOWED_IMPORTS=math,random,...
- Logging: LOG_LEVEL, LOG_FORMAT (json|pretty)
- Server: HOST=0.0.0.0, PORT=8000, WORKERS=1

### Pydantic Settings
- Validación de tipos en startup
- .env file con case_sensitive=False

---

## 02_dependencias.md — Datos Clave

### Backend Python (pyproject.toml)
- Python >=3.12
- FastAPI >=0.115, uvicorn >=0.30 [standard]
- SQLAlchemy >=2.0.30 [asyncio], asyncpg >=0.29, alembic >=1.13
- Pydantic >=2.7, pydantic-settings >=2.3
- python-jose >=3.3 [cryptography] — NOTA: siempre algorithms=["HS256"] en decode()
- bcrypt >=4.1
- redis >=5.0 [hiredis]
- anthropic >=0.30
- httpx >=0.27

### Frontend (package.json)
- React ^19.0, react-router-dom ^7.0
- Zustand ^5.0, @tanstack/react-query ^5.50
- Zod ^3.23
- Monaco Editor ^4.6 / ^0.49
- Recharts ^2.12
- TailwindCSS ^4.0
- MSW ^2.3 (dev)
- Vitest ^2.0, Playwright ^1.45
- TypeScript ^5.5

### Nota: Alembic usa driver sync (psycopg2-binary) mientras la app usa asyncpg

---

## 03_deploy.md — Datos Clave

- 3 entornos: dev (Docker Compose), staging (docker-compose.prod + Nginx), producción (futuro)
- CI/CD: GitHub Actions (lint + tests + build)
- Docker multi-stage builds
- Health check endpoint

---

## 04_migraciones.md — Datos Clave

### INCONSISTENCIAS CRÍTICAS

**IC-I1: Schema analytics tiene tablas completamente distintas**
- 02-arquitectura/02_modelo_de_datos: analytics solo tiene `risk_assessments`
- 04-infraestructura/04_migraciones: analytics tiene `exercise_attempts`, `student_metrics`, `course_stats`, `risk_assessments`
- Las 3 tablas extras (exercise_attempts, student_metrics, course_stats) NO aparecen en NINGÚN otro doc.

**IC-I2: exercises SIGUE con commission_id aquí**
- `exercises: id, commission_id (FK)` en el schema listing de migraciones
- Ya lo corregimos a course_id en 01-negocio y 02-arquitectura. Falta este archivo.

**IC-I3: tutor_interactions tiene FK a cognitive.cognitive_sessions**
- `tutor_interactions: session_id (FK cognitive.cognitive_sessions)` — FK cross-schema explícita
- En 02-arquitectura decidimos que es correlación lógica SIN FK cross-schema
- Este archivo contradice esa decisión

**IC-I4: cognitive_events tiene campo user_id**
- Schema listing dice: `cognitive_events: ..., user_id` 
- 02-arquitectura/02_modelo_de_datos NO tiene user_id en cognitive_events (tiene session_id que referencia student_id indirectamente)

**IC-I5: cognitive_metrics incompleto (otra vez)**
- Faltan: qe_score, qe_components, dependency_score, reflection_score, success_efficiency

**IC-I6: governance_events schema difiere**
- 02-arquitectura: actor_id, target_type, target_id, details(JSONB)
- 04-infra: actor_id, description, payload(JSONB)
- Campos distintos.

**IC-I7: tutor_system_prompts simplificado**
- 02-arquitectura: name, content, sha256_hash, version, is_active, guardrails_config, created_by
- 04-infra: version_hash, content, is_active, created_at
- Muchos campos faltantes.

**IC-I8: Tabla reflections no aparece aquí**
- 02-arquitectura/02_modelo define tabla reflections
- 04-infraestructura/04_migraciones no la lista

**IC-I9: Tabla event_outbox no aparece aquí**
- 02-arquitectura/02_modelo define event_outbox
- 04-infraestructura/04_migraciones no la lista

**IC-I10: commissions sin teacher_id ni semester**
- 02-arquitectura: teacher_id, year, semester
- 04-infra: course_id, name, year, is_active — falta teacher_id y semester

---

## 05_integraciones.md — Datos Clave

- Anthropic Claude API integration
- LLM Adapter Protocol (misma que 02-arquitectura/04_patrones)
- Monaco Editor config
- Recharts para gráficos
- MSW para desarrollo paralelo frontend

---

## FIXES NECESARIOS en 04_migraciones.md

1. exercises: commission_id → course_id
2. tutor_interactions: session_id sin FK cross-schema (correlación lógica)
3. cognitive_events: remover user_id (se obtiene vía session)
4. cognitive_metrics: agregar campos Qe + dependency + reflection + efficiency
5. governance_events: alinear con 02-arquitectura (actor_id, target_type, target_id, details)
6. tutor_system_prompts: agregar name, sha256_hash, version, guardrails_config, created_by
7. commissions: agregar teacher_id y semester
8. Agregar tabla reflections
9. Agregar tabla event_outbox
10. analytics: decidir si exercise_attempts, student_metrics, course_stats existen o se eliminan
