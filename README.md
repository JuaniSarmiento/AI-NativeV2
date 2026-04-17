# Plataforma AI-Native

Sistema pedagogico para ensenanza de programacion universitaria (UTN FRM). Integra un tutor IA socratico que guia sin dar respuestas, registro del proceso cognitivo del alumno (CTR), evaluacion multidimensional N4, y correccion asistida por IA.

## Que hace

- **Alumno**: se registra, se inscribe a un curso/comision, resuelve actividades con ejercicios de codigo, ejecuta en sandbox, chatea con tutor IA socratico, envia, llena reflexion
- **Docente**: crea cursos y comisiones, genera actividades con IA, corrige entregas con IA (nota + feedback por ejercicio), ve dashboard cognitivo con metricas N1-N4, alertas de riesgo, traza cognitiva completa
- **Admin**: todo lo del docente + reportes de gobernanza (eventos de auditoria, historial de prompts)

## Stack

| Componente | Tecnologia | Puerto |
|------------|-----------|--------|
| Backend API | Python 3.12 + FastAPI + SQLAlchemy 2.0 async | 8000 |
| Frontend | React 19 + TypeScript + Zustand 5 + TailwindCSS 4 + Vite | 5173 (dev) / 80 (prod) |
| Base de datos | PostgreSQL 16 (4 schemas: operational, cognitive, governance, analytics) | 5432 |
| Cache + Event Bus | Redis 7 (Streams, rate limiting, token blacklist) | 6379 |
| LLM | Mistral API (configurable, soporta Anthropic) | — |

---

## Deploy en VPS (Produccion)

### Requisitos del servidor

- Ubuntu 22.04+ o Debian 12+
- 2 GB RAM minimo (4 GB recomendado)
- 20 GB disco
- Docker + Docker Compose instalados
- Puerto 80 (frontend) y 8000 (API) abiertos

### Paso 1: Instalar Docker (si no esta)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Re-login para que tome efecto
```

### Paso 2: Clonar el repositorio

```bash
git clone https://github.com/JuaniSarmiento/AI-NativeV2.git
cd AI-NativeV2
```

### Paso 3: Configurar variables de entorno

```bash
cp env.example .env
nano .env
```

**Variables CRITICAS que hay que cambiar:**

| Variable | Que poner | Ejemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Generar con `openssl rand -hex 32` | `a1b2c3d4e5f6...` (64 chars) |
| `POSTGRES_PASSWORD` | Password fuerte para la DB | `MiPassSegura2026!` |
| `MISTRAL_API_KEY` | Tu API key de Mistral (https://console.mistral.ai) | `sk-...` |
| `APP_ENV` | Cambiar a `production` | `production` |
| `DEBUG` | Cambiar a `false` | `false` |
| `CORS_ORIGINS` | Dominio real del frontend | `["http://tu-ip:80"]` |

**Variables que pueden quedar como estan:**

| Variable | Default | Nota |
|----------|---------|------|
| `DATABASE_URL` | Se overridea en docker-compose | No tocar |
| `REDIS_URL` | Se overridea en docker-compose | No tocar |
| `TUTOR_LLM_PROVIDER` | `mistral` | Cambiar a `anthropic` si se usa Claude |
| `POSTGRES_USER` | `ainative` | Puede quedar |
| `POSTGRES_DB` | `ainative` | Puede quedar |

### Paso 4: Levantar todo

```bash
# Build y levantar
docker compose -f docker-compose.prod.yml up -d --build

# Esperar a que arranque (30 segundos aprox)
# Verificar que los 4 servicios estan corriendo:
docker compose -f docker-compose.prod.yml ps
```

Deberia mostrar 4 servicios: `api`, `frontend`, `db`, `redis` — todos `Up (healthy)`.

### Paso 5: Correr migraciones de base de datos

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

Esto crea los 4 schemas (operational, cognitive, governance, analytics) y todas las tablas.

### Paso 6: Seedear datos iniciales

```bash
# Crear el prompt socratico del tutor IA (OBLIGATORIO)
docker compose -f docker-compose.prod.yml exec -T db psql -U ainative -c "
INSERT INTO governance.tutor_system_prompts (id, name, content, sha256_hash, version, is_active, created_by)
VALUES (
  gen_random_uuid(),
  'socratic_tutor_contextual_v2',
  'Sos un tutor socratico de programacion universitaria (UTN FRM). Tu objetivo es GUIAR al alumno sin darle la respuesta directa.

## Ejercicio actual
**Titulo:** {exercise_title}
**Enunciado:** {exercise_description}
**Dificultad:** {exercise_difficulty}
**Temas:** {exercise_topics}
**Lenguaje:** {exercise_language}

## Codigo actual del alumno
\`\`\`
{student_code}
\`\`\`

## Reglas ESTRICTAS
1. NUNCA des la solucion completa. Maximo 5 lineas de codigo como pista.
2. Hace preguntas socraticas que guien al alumno a encontrar la respuesta.
3. Si el alumno pide la respuesta directa, explica POR QUE no se la das y reformula con una pregunta.
4. Referite siempre al ejercicio actual y al codigo que el alumno escribio.
5. Si el alumno no entiende el enunciado, ayudalo a desglosarlo paso a paso.
6. Usa espanol rioplatense (vos, tenes, fijate).
7. Se paciente y alentador.',
  encode(sha256('socratic_tutor_v2_prod'::bytea), 'hex'),
  'v2.0.0',
  true,
  '00000000-0000-0000-0000-000000000000'
);
"

# Crear cuentas iniciales (docente + admin)
bash devOps/scripts/seed-production.sh
```

### Paso 7: Verificar que funciona

```bash
# Health check
curl http://localhost:8000/api/v1/health/full

# Deberia devolver:
# {"status":"ok","data":{"database":"ok","redis":"ok"}}

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:80
# Deberia devolver: 200
```

### Paso 8: Acceder

- **Frontend**: `http://TU-IP:80`
- **API docs**: `http://TU-IP:8000/docs`

**Cuentas default (despues del seed):**

| Rol | Email | Password |
|-----|-------|----------|
| Docente | docente@utn.edu | DocE2E2026! |
| Admin | admin@utn.edu | AdmE2E2026! |

Los alumnos se registran solos desde la pantalla de registro.

---

## Operaciones

### Ver logs

```bash
# Todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Solo API
docker compose -f docker-compose.prod.yml logs -f api

# Solo errores
docker compose -f docker-compose.prod.yml logs api | grep ERROR
```

### Backup de base de datos

```bash
# Backup manual
bash devOps/scripts/backup-db.sh

# Los backups se guardan en devOps/backups/
ls devOps/backups/

# Programar backup diario (cron)
crontab -e
# Agregar: 0 3 * * * cd /ruta/al/proyecto && bash devOps/scripts/backup-db.sh >> /var/log/ainative-backup.log 2>&1
```

### Restaurar backup

```bash
gunzip -c devOps/backups/ainative_20260416_030000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U ainative ainative
```

### Actualizar (deploy nueva version)

```bash
bash devOps/scripts/deploy.sh
# Hace: git pull → build → restart → migrate → health check
```

### Rollback

```bash
bash devOps/scripts/rollback.sh          # Vuelve 1 commit atras
bash devOps/scripts/rollback.sh abc1234  # Vuelve a un commit especifico
```

### Reiniciar servicios

```bash
docker compose -f docker-compose.prod.yml restart
```

### Parar todo

```bash
docker compose -f docker-compose.prod.yml down
# Los datos se mantienen en los volumes
```

### Monitoreo continuo

```bash
nohup bash devOps/scripts/health-monitor.sh >> /var/log/ainative-health.log 2>&1 &
```

---

## Desarrollo Local

### Levantar para desarrollo (con hot reload)

```bash
docker compose -f devOps/docker-compose.yml up -d
# API: http://localhost:8000 (hot reload)
# Frontend: http://localhost:5173 (hot reload)
# DB: localhost:5432
# Redis: localhost:6379
```

### Correr migraciones

```bash
docker compose -f devOps/docker-compose.yml exec api alembic upgrade head
```

### Correr tests

```bash
# Backend unit tests
cd backend && SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://x:x@localhost/x python -m pytest tests/unit/ -v

# E2E tests (requiere frontend + backend corriendo)
npm run test:e2e
```

---

## Arquitectura

```
Alumno (browser)
  │
  ├── Frontend (React 19 + Vite)  ──── proxy ────┐
  │     - Editor de codigo                        │
  │     - Chat con tutor IA (WebSocket)           │
  │     - Vista de nota y feedback                │
  │                                               ▼
  │                                         Backend (FastAPI)
  │                                           │
  │                              ┌────────────┼────────────────┐
  │                              │            │                │
  │                         PostgreSQL     Redis 7         Mistral API
  │                         (4 schemas)   (Event Bus)     (Tutor + Grading)
  │                              │            │
  │                    operational │     events:submissions
  │                    cognitive   │     events:tutor
  │                    governance  │     events:code
  │                    analytics   │     events:cognitive
  │                              │
  │                     CognitiveEventConsumer
  │                     (background worker)
  │                              │
  │                     Cognitive Sessions → Metrics → Dashboard
  │
Docente (browser)
  ├── Dashboard cognitivo (N1-N4, radar chart, riesgo)
  ├── Correccion con IA (nota + feedback por ejercicio)
  └── Traza cognitiva visual (timeline, code diffs, chat)
```

## Modelo de Evaluacion

```
E = f(N1, N2, N3, N4, Qe)

N1 — Comprension: ¿entiende el problema?
N2 — Estrategia: ¿puede planificar una solucion?
N3 — Validacion: ¿verifica y corrige?
N4 — Interaccion IA: ¿usa la IA criticamente o como oraculo?
Qe — Calidad epistemica: ¿las preguntas al tutor son de calidad?
```

No se evalua solo el codigo final. Se observa TODO el proceso cognitivo del alumno.

## Licencia

Proyecto academico — UTN Facultad Regional Mendoza. Tesis doctoral Dr. Alberto Cortez.
