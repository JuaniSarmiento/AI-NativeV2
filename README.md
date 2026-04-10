# Plataforma AI-Native

Sistema pedagógico-tecnológico para enseñanza de programación universitaria con trazabilidad cognitiva N4. FastAPI + React 19 + PostgreSQL + Redis.

## Prerequisitos

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose
- Git

## Setup Rápido

```bash
# Clonar repositorio
git clone <repo-url> && cd ai-native

# Copiar variables de entorno
cp env.example .env
# Editar .env: configurar ANTHROPIC_API_KEY, JWT_SECRET_KEY, APP_SECRET_KEY

# Levantar con Docker Compose
cd devOps && chmod +x start.sh && ./start.sh

# O manualmente:
docker compose up -d
# Esperar que DB esté healthy, luego:
cd ../backend && pip install -e ".[dev]"
alembic upgrade head
python -m app.seed  # cargar datos iniciales

cd ../frontend && npm install && npm run dev
```

## Verificar

- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Health check: http://localhost:8000/api/v1/health
- Login con seed data: alumno@test.com / docente@test.com

## Variables de Entorno

Copiar `env.example` a `.env` y completar con valores locales. Variables críticas:

| Variable | Descripción |
|----------|------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `ANTHROPIC_API_KEY` | API key para el tutor socrático (**CHANGE_ME**) |
| `JWT_SECRET_KEY` | Secret para firmar tokens JWT (**CHANGE_ME**) |
| `APP_SECRET_KEY` | Secret general de la aplicación (**CHANGE_ME**) |

## Estructura del Proyecto

```
ai-native/
├── backend/                # FastAPI + SQLAlchemy 2.0 async (Python 3.12)
│   ├── app/features/       # Módulos por dominio (auth, courses, tutor, cognitive...)
│   ├── alembic/            # Migraciones de DB
│   ├── prompts/            # System prompts versionados del tutor
│   ├── rubrics/            # Rúbricas N4
│   └── tests/              # Unit, integration, adversarial
├── frontend/               # React 19 + Zustand 5 + TailwindCSS 4 (Vite)
│   └── src/features/       # Feature folders (auth, student, teacher, exercise)
├── shared/                 # Schemas compartidos, contratos OpenAPI
├── infra/                  # Docker Compose, scripts, seed data
├── devOps/                 # Docker, nginx, backup, RUNBOOK
├── knowledge-base/         # Documentación completa del sistema (35 archivos)
└── openspec/               # Spec-Driven Development artifacts
```

## Equipo

| Dev | Fase | Schema Owner |
|-----|------|-------------|
| Dev 1 | Fase 1 — Core Académico + Sandbox | operational (courses, exercises, submissions) |
| Dev 2 | Fase 2 — Tutor IA Socrático | operational (tutor), governance |
| Dev 3 | Fase 3 — Motor Cognitivo + Evaluación | cognitive, analytics |
| Dev 4 | Fase 4 — Frontend Completo | — (consume APIs) |

## Timeline

| Período | Actividad |
|---------|----------|
| Semanas 1-2 | Fase 0 — Fundación (todo el equipo) |
| Semanas 3-12 | Fases 1-4 en paralelo |
| Semanas 13-14 | Integración y testing E2E |
| Semanas 15-16 | QA final y piloto con usuarios |

## Documentación

| Documento | Contenido |
|-----------|----------|
| [CLAUDE.md](CLAUDE.md) | Instrucciones para Claude Code (canonical) |
| [AGENTS.md](AGENTS.md) | Instrucciones model-agnostic para otros AI tools |
| [knowledge-base/](knowledge-base/README.md) | Documentación completa: negocio, arquitectura, seguridad, infra, DX |
| [Historias de Usuario.md](Historias%20de%20Usuario.md) | 42 user stories organizadas en 5 EPICs |
| [guia_desarrollo.md](guia_desarrollo.md) | Cómo implementar features (backend + frontend) |
| [metodologia_github.md](metodologia_github.md) | Branching, commits, PRs, reviews |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Guía de contribución |
| [devOps/RUNBOOK.md](devOps/RUNBOOK.md) | Operaciones: start, stop, backup, troubleshooting |
| [devOps/SCALING.md](devOps/SCALING.md) | Plan de escalabilidad |

## Modelo Teórico

Este sistema implementa el modelo AI-Native con Trazabilidad Cognitiva N4, parte de la tesis doctoral del Dr. Alberto Cortez (UTN FRM). El documento maestro de unificación conceptual (empate3) es la referencia normativa para toda decisión técnica.

**Evaluación**: `E = f(N1, N2, N3, N4, Qe)` — reemplaza `E = correctness(output)`

## Licencia

Proyecto académico — UTN Facultad Regional Mendoza.
