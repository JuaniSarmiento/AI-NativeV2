# Deploy y CI/CD — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto
**Clasificación**: Documentación interna — infraestructura

---

## Índice

1. [Entornos de deployment](#1-entornos)
2. [Desarrollo local — Docker Compose](#2-desarrollo-local)
3. [Staging — docker-compose.prod.yml + Nginx](#3-staging)
4. [Producción — consideraciones futuras](#4-producción)
5. [CI/CD — GitHub Actions](#5-cicd)
6. [Docker images — Multi-stage builds](#6-docker-images)
7. [Health check endpoint](#7-health-check)

---

## 1. Entornos

| Entorno | Descripción | Estado |
|---------|-------------|--------|
| **development** | Local con Docker Compose, hot reload | Activo |
| **staging** | Docker Compose + Nginx, sin hot reload | A implementar |
| **production** | VPS/cloud, SSL, backups | Futuro (post-tesis) |

El proyecto está en etapa académica activa. El foco actual es **development** con infraestructura de staging diseñada para validar el comportamiento en condiciones cercanas a producción.

---

## 2. Desarrollo Local — Docker Compose

### 2.1 Comandos de uso diario

```bash
# Levantar todo el stack
docker compose up

# Levantar en background
docker compose up -d

# Ver logs de un servicio
docker compose logs -f api
docker compose logs -f frontend

# Reiniciar un servicio sin reconstruir
docker compose restart api

# Reconstruir una imagen después de cambiar Dockerfile o dependencias
docker compose build api
docker compose up --build

# Detener y eliminar containers (mantiene volumes)
docker compose down

# Detener y eliminar containers + volumes (reset completo de DB)
docker compose down -v

# Ejecutar comandos en el container
docker compose exec api alembic upgrade head
docker compose exec api python -m pytest tests/
docker compose exec db psql -U postgres ainative
```

### 2.2 Flujo de startup correcto

Docker Compose asegura el orden con `depends_on` + `healthcheck`:

```
1. db (PostgreSQL) → espera healthcheck pg_isready
2. redis → espera healthcheck redis-cli ping
3. api → espera que db y redis estén healthy → ejecuta migraciones → levanta uvicorn
4. frontend → espera api (opcional) → levanta Vite dev server
```

El container `api` puede incluir un entrypoint que ejecute las migraciones automáticamente en desarrollo:

```bash
#!/bin/bash
# backend/entrypoint.sh
set -e

echo "Esperando base de datos..."
python -c "
import asyncio, asyncpg, os
async def wait():
    for i in range(30):
        try:
            conn = await asyncpg.connect(os.environ['DATABASE_URL'].replace('+asyncpg',''))
            await conn.close()
            print('DB lista')
            return
        except Exception:
            import time; time.sleep(1)
    raise Exception('DB no disponible')
asyncio.run(wait())
"

echo "Aplicando migraciones..."
alembic upgrade head

echo "Iniciando aplicación..."
exec "$@"
```

### 2.3 Hot reload

- **Backend**: `uvicorn --reload` detecta cambios en archivos `.py` y recarga sin reiniciar el container
- **Frontend**: Vite HMR (Hot Module Replacement) reemplaza módulos individuales sin perder el estado del browser

### 2.4 Reset del entorno de desarrollo

```bash
# Reset completo (DB + Redis + reconstruir)
docker compose down -v --remove-orphans
docker compose build --no-cache
docker compose up

# Solo resetear DB
docker compose stop db
docker volume rm ai-native_postgres_data
docker compose up db
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py  # datos de prueba
```

---

## 3. Staging — docker-compose.prod.yml + Nginx

### 3.1 `docker-compose.prod.yml`

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    environment:
      - DEBUG=false
      - ENVIRONMENT=staging
      - WORKERS=2
    env_file:
      - ./backend/.env.staging
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    expose:
      - "8000"                      # Exponer solo internamente (Nginx hace proxy)
    # Límites de recursos — protege el host de consumo descontrolado
    mem_limit: 512m
    cpus: "1.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s             # Dar tiempo para migraciones

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ainative
    volumes:
      - postgres_data:/var/lib/postgresql/data
    expose:
      - "5432"                      # Solo accesible internamente
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ainative"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    expose:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - frontend_build:/usr/share/nginx/html:ro
    depends_on:
      - api

  frontend-builder:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: builder
    volumes:
      - frontend_build:/app/dist
    command: sh -c "npm run build && echo 'Build completo'"

volumes:
  postgres_data:
  redis_data:
  frontend_build:
```

### 3.2 Nginx como reverse proxy

> **ADVERTENCIA**: La configuración mostrada a continuación escucha en HTTP (puerto 80) y es solo para **desarrollo/staging interno**. En producción, Nginx DEBE tener terminación TLS (HTTPS + WSS). Sin TLS: access tokens en query string del WS viajan en plaintext y la cookie de refresh token no puede tener `Secure` flag. Ver sección 4.2 para SSL con Let's Encrypt.

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript;

    # Upstream FastAPI
    upstream api_backend {
        server api:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name localhost;

        # ──────────────────────────────────────────
        # API REST
        # ──────────────────────────────────────────
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts para endpoints lentos (LLM)
            proxy_connect_timeout 10s;
            proxy_read_timeout 60s;     # LLM puede tardar hasta 30s
            proxy_send_timeout 60s;

            # Rate limiting (complemento al rate limiter de FastAPI)
            limit_req zone=api burst=20 nodelay;
        }

        # ──────────────────────────────────────────
        # WebSocket
        # ──────────────────────────────────────────
        location /ws {
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 3600s;   # WS connection larga
            proxy_send_timeout 3600s;
        }

        # ──────────────────────────────────────────
        # Frontend (SPA — React Router)
        # ──────────────────────────────────────────
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;  # SPA fallback

            # Cache de assets estáticos (JS, CSS, imágenes)
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }

            # No cachear index.html (para updates inmediatos)
            location = /index.html {
                expires off;
                add_header Cache-Control "no-cache, no-store, must-revalidate";
            }
        }
    }
}
```

### 3.3 Comandos de staging

```bash
# Deploy en staging
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Ver estado
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api

# Actualizar solo la API (zero downtime no garantizado — futuro)
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull api
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api
```

---

## 4. Producción — Consideraciones Futuras

El deployment en producción no es el foco de la tesis (etapa académica actual), pero se documenta la arquitectura target para no generar deuda técnica de diseño.

### 4.1 Opciones de infraestructura evaluadas

| Opción | Costo estimado | Complejidad | Adecuado para tesis |
|--------|---------------|-------------|---------------------|
| VPS (Hetzner CX21: 2vCPU/4GB) | ~€5/mes | Baja | Sí — suficiente para ~100 usuarios concurrentes |
| Railway | ~$20/mes | Muy baja | Sí — pero menos control de networking |
| AWS/GCP | Variable (auto-scaling) | Alta | Overkill para una tesis |
| Docker en UTN FRM | €0 | Media | Depende de disponibilidad de infra |

**Recomendación**: VPS en Hetzner o DigitalOcean para la defensa de tesis. Docker Compose en VPS con Nginx + Let's Encrypt.

### 4.2 SSL en producción

```bash
# Certbot con Let's Encrypt:
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/www/certbot:/var/www/certbot \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d tu-dominio.com \
  --email tu@email.com \
  --agree-tos

# Renovación automática (cron):
0 0 1 * * docker run --rm certbot/certbot renew && docker compose exec nginx nginx -s reload
```

### 4.3 Estrategia de backup

```bash
# Backup de PostgreSQL:
docker compose exec db pg_dump -U postgres ainative | gzip > backup_$(date +%Y%m%d_%H%M).sql.gz

# Backup de Redis (RDB snapshot):
docker compose exec redis redis-cli BGSAVE
docker cp $(docker compose ps -q redis):/data/dump.rdb ./backups/redis_$(date +%Y%m%d).rdb

# Script automático en cron (VPS):
# 0 2 * * * /opt/ai-native/scripts/backup.sh
```

### 4.4 Escalabilidad horizontal (futuro lejano)

Para escalar más allá de un VPS:
- **API**: stateless — se puede escalar horizontalmente con load balancer
- **WebSocket**: requiere sticky sessions en el load balancer (o migrar a Redis pub/sub para fanout multi-instancia)
- **DB**: Read replicas para queries de analytics (SQLAlchemy AsyncSession con engine separado para reads)
- **Redis**: Redis Cluster para alta disponibilidad

---

## 5. CI/CD — GitHub Actions

### 5.1 Pipeline completo

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main]      # GitHub Flow: solo main, no develop
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"

jobs:
  # ══════════════════════════════════════════════
  # BACKEND LINT + TYPE CHECK
  # ══════════════════════════════════════════════
  backend-lint:
    name: Backend — Lint y Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Instalar dependencias de desarrollo
        run: uv sync --frozen

      - name: Ruff lint
        run: ruff check .

      - name: Ruff format check
        run: ruff format --check .

      - name: MyPy type check
        run: mypy app/

  # ══════════════════════════════════════════════
  # BACKEND TESTS
  # ══════════════════════════════════════════════
  backend-tests:
    name: Backend — Tests
    runs-on: ubuntu-latest
    needs: backend-lint
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Instalar dependencias
        run: uv sync --frozen

      - name: Ejecutar tests
        run: pytest --cov=app --cov-report=xml --cov-fail-under=80
        env:
          # testcontainers levanta Docker real en CI
          DATABASE_URL: "not-used-testcontainers-manages-this"
          REDIS_URL: "not-used-testcontainers-manages-this"
          SECRET_KEY: "ci-test-secret-key-minimum-32-chars"
          ANTHROPIC_API_KEY: "sk-ant-dummy-key-for-tests"

      - name: Subir coverage a Codecov
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml

  # ══════════════════════════════════════════════
  # FRONTEND LINT + TYPE CHECK
  # ══════════════════════════════════════════════
  frontend-lint:
    name: Frontend — Lint y Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Instalar dependencias
        run: npm ci

      - name: ESLint
        run: npm run lint

      - name: TypeScript type check
        run: npm run type-check

  # ══════════════════════════════════════════════
  # FRONTEND TESTS
  # ══════════════════════════════════════════════
  frontend-tests:
    name: Frontend — Tests
    runs-on: ubuntu-latest
    needs: frontend-lint
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Instalar dependencias
        run: npm ci

      - name: Vitest
        run: npm run test:coverage

  # ══════════════════════════════════════════════
  # BUILD DE IMÁGENES
  # ══════════════════════════════════════════════
  build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login a GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build y push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          target: production
          push: true
          tags: ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build y push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          target: production
          push: true
          tags: ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ══════════════════════════════════════════════
  # DEPLOY A STAGING (solo en main)
  # ══════════════════════════════════════════════
  deploy-staging:
    name: Deploy a Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/ai-native
            git pull origin main
            docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
            # CRÍTICO: migraciones ANTES de servir tráfico con el nuevo código
            # Patrón: drain → migrate → deploy
            docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api alembic upgrade head
            docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5.2 Secrets requeridos en GitHub

| Secret | Descripción |
|--------|-------------|
| `STAGING_HOST` | IP o dominio del servidor de staging |
| `STAGING_USER` | Usuario SSH |
| `STAGING_SSH_KEY` | Clave SSH privada (la pública en `~/.ssh/authorized_keys` del server) |
| `ANTHROPIC_API_KEY_TEST` | Clave para tests de integración (si se necesita) |

### 5.3 Estrategia de branches

**GitHub Flow** (no Gitflow):

```
main          ← única rama de integración y producción. Todo merge va aquí.
feature/*     ← desarrollo de features. PR directamente a main.
hotfix/*      ← fixes urgentes. PR directamente a main.
```

No existe rama `develop`. Feature branches se crean desde `main` y se mergean a `main` vía Pull Request.

---

## 6. Docker Images — Multi-Stage Builds

### 6.1 Backend `Dockerfile`

```dockerfile
# backend/Dockerfile

# ══════════════════════════════════════════════
# Stage 1: Base (dependencias del SO)
# ══════════════════════════════════════════════
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias del SO (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ══════════════════════════════════════════════
# Stage 2: Dependencies (cacheable)
# ══════════════════════════════════════════════
FROM base AS dependencies

# Instalar uv para builds reproducibles con lockfile
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
# uv sync --frozen usa uv.lock para builds 100% reproducibles (no resuelve versiones en runtime)
RUN uv sync --frozen --no-dev

# ══════════════════════════════════════════════
# Stage 3: Development (hot reload)
# ══════════════════════════════════════════════
FROM base AS development

# En dev instalamos también deps de desarrollo desde lockfile
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen  # incluye dev deps

# El código se monta como volume en dev
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ══════════════════════════════════════════════
# Stage 4: Production (sin dev deps, usuario no-root)
# ══════════════════════════════════════════════
FROM base AS production

# Instalar uv y dependencias de producción desde lockfile
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
# --frozen: no actualizar lockfile (build reproducible). --no-dev: sin dependencias de testing.
RUN uv sync --frozen --no-dev

# Copiar código
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Usuario sin privilegios
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 6.2 Frontend `Dockerfile`

```dockerfile
# frontend/Dockerfile

# ══════════════════════════════════════════════
# Stage 1: Dependencies
# ══════════════════════════════════════════════
FROM node:20-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

# ══════════════════════════════════════════════
# Stage 2: Development (Vite dev server)
# ══════════════════════════════════════════════
FROM dependencies AS development

COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ══════════════════════════════════════════════
# Stage 3: Builder (genera el bundle estático)
# ══════════════════════════════════════════════
FROM dependencies AS builder

COPY . .
RUN npm run build
# Output en /app/dist

# ══════════════════════════════════════════════
# Stage 4: Production (Nginx sirviendo el bundle)
# ══════════════════════════════════════════════
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 7. Health Check Endpoint

### 7.1 Especificación

```
GET /api/v1/health

Respuesta exitosa (200 OK):
{
  "status": "healthy",
  "timestamp": "2026-04-10T12:00:00Z",
  "version": "0.1.0",
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.3
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.8
    }
  }
}

Respuesta degradada (503 Service Unavailable):
{
  "status": "unhealthy",
  "timestamp": "2026-04-10T12:00:00Z",
  "version": "0.1.0",
  "services": {
    "database": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.8
    }
  }
}
```

### 7.2 Implementación

```python
# app/api/v1/health.py
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/health")  # Con prefix /api/v1 del app → GET /api/v1/health
async def health_check(request: Request):
    db_status = await check_database(request.app.state.db_factory)
    redis_status = await check_redis(request.app.state.redis)

    all_healthy = db_status["status"] == "healthy" and redis_status["status"] == "healthy"

    response_data = {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
    }

    status_code = 200 if all_healthy else 503
    return JSONResponse(content=response_data, status_code=status_code)


async def check_database(session_factory) -> dict:
    start = time.monotonic()
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis(redis_client) -> dict:
    start = time.monotonic()
    try:
        await redis_client.ping()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 7.3 Uso del health check

| Contexto | Uso |
|----------|-----|
| Docker Compose | `healthcheck.test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]` |
| GitHub Actions | Step de smoke test post-deploy |
| Nginx | `proxy_next_upstream error timeout invalid_header http_503` |
| Monitoring futuro | Endpoint para Uptime Robot / Grafana alerting |

---

**Referencias internas**:
- `knowledge-base/04-infraestructura/01_configuracion.md` — variables de entorno por ambiente
- `knowledge-base/04-infraestructura/04_migraciones.md` — migraciones ejecutadas en startup
- `knowledge-base/04-infraestructura/02_dependencias.md` — dependencias del proyecto
