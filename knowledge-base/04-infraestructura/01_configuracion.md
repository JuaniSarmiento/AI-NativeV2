# Configuración del Entorno — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto
**Clasificación**: Documentación interna — infraestructura

---

## Índice

1. [Variables de entorno — Backend](#1-variables-de-entorno-backend)
2. [pydantic-settings — Configuración tipada](#2-pydantic-settings)
3. [Variables de entorno — Frontend](#3-variables-de-entorno-frontend)
4. [Docker Compose — Configuración de servicios](#4-docker-compose)
5. [Diferencias dev vs producción](#5-dev-vs-producción)
6. [Patrones de .gitignore](#6-gitignore)

---

## 1. Variables de Entorno — Backend

El archivo `.env` en la raíz del proyecto (ignorado por git) contiene todas las variables de configuración. El archivo `env.example` (incluido en el repo) documenta las variables requeridas sin valores reales.

### 1.1 Variables completas (`backend/env.example`)

```bash
# ============================================================
# APLICACIÓN
# ============================================================
APP_NAME=AI-Native Platform
APP_VERSION=0.1.0
DEBUG=true                          # false en producción
ENVIRONMENT=development             # development | staging | production

# ============================================================
# SEGURIDAD
# ============================================================
SECRET_KEY=cambiar-por-clave-aleatoria-256bits
# Generar con: openssl rand -hex 32
# NUNCA usar el valor de ejemplo en producción

ACCESS_TOKEN_EXPIRE_MINUTES=15      # Vida del JWT access token
REFRESH_TOKEN_EXPIRE_DAYS=7         # Vida del JWT refresh token

ALLOWED_ORIGINS=http://localhost:5173
# En producción: https://tu-dominio.com

# ============================================================
# BASE DE DATOS
# ============================================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/ainative
# Formato: postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}
# asyncpg es el driver async para PostgreSQL
# El host "db" corresponde al service name en Docker Compose

DATABASE_POOL_SIZE=10               # Conexiones en el pool
DATABASE_MAX_OVERFLOW=20            # Conexiones adicionales bajo carga
DATABASE_POOL_TIMEOUT=30            # Segundos antes de timeout al obtener conexión

# ============================================================
# REDIS
# ============================================================
REDIS_URL=redis://redis:6379/0
# El host "redis" corresponde al service name en Docker Compose
# /0 es la DB number (0-15)

REDIS_PASSWORD=                     # Vacío en dev. Setear en producción.
REDIS_SSL=false                     # true en producción si Redis está en cloud

# ============================================================
# ANTHROPIC (LLM)
# ============================================================
ANTHROPIC_API_KEY=sk-ant-...        # Clave de API de Anthropic
ANTHROPIC_MODEL=claude-sonnet-4-20250514   # Modelo para el tutor (latest Claude Sonnet)
ANTHROPIC_MAX_TOKENS=4096           # Máximo tokens en respuesta del tutor
ANTHROPIC_TEMPERATURE=0.7           # Creatividad del tutor (0-1)
ANTHROPIC_TIMEOUT=30                # Segundos máximos esperando respuesta del LLM

# ============================================================
# RATE LIMITING
# ============================================================
RATE_LIMIT_TUTOR_MESSAGES=30        # Mensajes por hora al tutor por usuario
RATE_LIMIT_TUTOR_WINDOW=3600        # Ventana en segundos (1 hora)
RATE_LIMIT_API_REQUESTS=100         # Requests por minuto por IP
RATE_LIMIT_API_WINDOW=60            # Ventana en segundos (1 minuto)
RATE_LIMIT_LOGIN_ATTEMPTS=10        # Intentos de login por IP
RATE_LIMIT_LOGIN_WINDOW=300         # Ventana de 5 minutos

# ============================================================
# SANDBOX
# ============================================================
SANDBOX_TIMEOUT=10                  # Segundos máximos de ejecución de código
SANDBOX_MEMORY_MB=128               # Límite de memoria en MB
SANDBOX_ALLOWED_IMPORTS=math,random,statistics,itertools,functools,collections,string,re,json,csv,datetime,typing,dataclasses
# Lista separada por comas de módulos Python permitidos

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FORMAT=json                     # json (prod) | pretty (dev)
LOG_FILE=                           # Vacío = solo stdout. Path para archivo adicional.

# ============================================================
# CORS
# ============================================================
FRONTEND_URL=http://localhost:5173  # URL del frontend para CORS y redirects

# ============================================================
# SERVIDOR
# ============================================================
HOST=0.0.0.0
PORT=8000
WORKERS=1                           # 1 en dev, ajustar en prod según CPU cores
```

### 1.2 Descripción de variables críticas

| Variable | Obligatoria | Descripción | Impacto si falta/incorrecta |
|----------|-------------|-------------|------------------------------|
| `SECRET_KEY` | Sí | Firma todos los JWT | Seguridad total comprometida |
| `DATABASE_URL` | Sí | Conexión a PostgreSQL | La app no arranca |
| `ANTHROPIC_API_KEY` | Sí | Acceso al LLM | El tutor no funciona |
| `REDIS_URL` | Sí | Auth, rate limiting, sesiones | La app no arranca |
| `DEBUG` | No | Expone stack traces, habilita reload | En prod: debe ser `false` |
| `ALLOWED_ORIGINS` | Sí | CORS — qué frontend puede conectarse | Requests cross-origin bloqueados |

---

## 2. pydantic-settings — Configuración Tipada

El backend usa `pydantic-settings` para cargar las variables de entorno con validación de tipos y valores en startup.

### 2.1 Implementación de `Settings`

```python
# app/core/config.py
from pydantic import AnyHttpUrl, AnyUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",         # ignorar vars no declaradas
    )

    # Aplicación
    APP_NAME: str = "AI-Native Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Seguridad
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # Base de datos
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 2048
    ANTHROPIC_TEMPERATURE: float = 0.7
    ANTHROPIC_TIMEOUT: int = 30

    # Rate limiting
    RATE_LIMIT_TUTOR_MESSAGES: int = 30
    RATE_LIMIT_TUTOR_WINDOW: int = 3600
    RATE_LIMIT_API_REQUESTS: int = 100
    RATE_LIMIT_API_WINDOW: int = 60

    # Sandbox
    SANDBOX_TIMEOUT: int = 10
    SANDBOX_MEMORY_MB: int = 128
    SANDBOX_ALLOWED_IMPORTS: str = "math,random,statistics"

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"  # En producción: https://tu-dominio.com

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "pretty"] = "json"

    # Servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Propiedades derivadas
    @property
    def sandbox_allowed_imports_list(self) -> list[str]:
        return [m.strip() for m in self.SANDBOX_ALLOWED_IMPORTS.split(",")]

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 64:
            raise ValueError(
                "SECRET_KEY debe tener al menos 64 caracteres hex (256 bits). "
                "Generar con: openssl rand -hex 32  →  produce 64 chars = 256 bits"
            )
        if v in ("cambiar-por-clave-aleatoria-256bits", "your-secret-key"):
            raise ValueError("SECRET_KEY es un placeholder. Generar una clave real con openssl rand -hex 32")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG debe ser False en producción")
            if "localhost" in self.DATABASE_URL:
                raise ValueError("DATABASE_URL con localhost no es válido en producción")
            if not self.REDIS_PASSWORD:
                raise ValueError("REDIS_PASSWORD no puede estar vacío en producción")
            if any("localhost" in origin for origin in self.ALLOWED_ORIGINS):
                raise ValueError("ALLOWED_ORIGINS no puede contener localhost en producción")
            frontend_url = getattr(self, "FRONTEND_URL", "")
            if frontend_url and not frontend_url.startswith("https://"):
                raise ValueError("FRONTEND_URL debe usar https:// en producción")
        return self


# Singleton — importar desde aquí en toda la app
settings = Settings()
```

### 2.2 Uso en la aplicación

```python
# Cualquier módulo del backend:
from app.core.config import settings

# Uso:
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
```

**Por qué pydantic-settings**: validación en startup (la app falla rápido si falta una variable), tipado completo, conversión automática (strings a bool, int, list), y soporte para `.env` files sin código adicional.

---

## 3. Variables de Entorno — Frontend

Vite expone variables de entorno al código del cliente mediante el prefijo `VITE_`. Las variables sin ese prefijo son accesibles solo durante el build y no se exponen en el bundle.

### 3.1 Archivo `frontend/env.example`

```bash
# ============================================================
# API
# ============================================================
VITE_API_URL=http://localhost:8000
# URL base de la API REST del backend
# En producción: https://api.tu-dominio.com/api/v1

VITE_WS_URL=ws://localhost:8000
# URL base para conexiones WebSocket
# En producción: wss://api.tu-dominio.com

# ============================================================
# APLICACIÓN
# ============================================================
VITE_APP_NAME=AI-Native Platform
VITE_APP_VERSION=0.1.0

# ============================================================
# FEATURE FLAGS
# ============================================================
VITE_ENABLE_MOCK_API=false
# true en desarrollo cuando el backend no está disponible
# Activa Mock Service Worker (MSW) para simular la API

VITE_ENABLE_DEVTOOLS=true
# Habilita herramientas de desarrollo de Zustand/React Query

# ============================================================
# ANALYTICS / TELEMETRÍA (futuro)
# ============================================================
# VITE_SENTRY_DSN=
# VITE_POSTHOG_KEY=
```

### 3.2 Acceso en el código TypeScript

```typescript
// src/config/env.ts
const config = {
  apiUrl: `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`,
  wsUrl: import.meta.env.VITE_WS_URL ?? "ws://localhost:8000",
  appName: import.meta.env.VITE_APP_NAME ?? "AI-Native",
  enableMockApi: import.meta.env.VITE_ENABLE_MOCK_API === "true",
  enableDevtools: import.meta.env.VITE_ENABLE_DEVTOOLS === "true",
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;

export default config;
```

### 3.3 Variables de Vite disponibles sin configuración

| Variable | Descripción |
|----------|-------------|
| `import.meta.env.MODE` | `"development"` \| `"production"` \| `"test"` |
| `import.meta.env.DEV` | `true` en modo desarrollo |
| `import.meta.env.PROD` | `true` en modo producción |
| `import.meta.env.BASE_URL` | Base URL de la app (configurada en `vite.config.ts`) |
| `import.meta.env.SSR` | `true` si se hace server-side rendering |

---

## 4. Docker Compose — Configuración de Servicios

### 4.1 `docker-compose.yml` (desarrollo)

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ────────────────────────────────────────
  # Backend FastAPI
  # ────────────────────────────────────────
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development           # Multi-stage: dev con hot reload
    volumes:
      - ./backend:/app              # Mount del código para hot reload
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/ainative
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ────────────────────────────────────────
  # PostgreSQL 16
  # ────────────────────────────────────────
  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ainative
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init_schemas.sql:/docker-entrypoint-initdb.d/01_schemas.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ainative"]
      interval: 5s
      timeout: 3s
      retries: 10

  # ────────────────────────────────────────
  # Redis 7
  # ────────────────────────────────────────
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ────────────────────────────────────────
  # Frontend React 19 + Vite
  # ────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./frontend:/app
      - /app/node_modules           # Named volume para evitar override de node_modules
    ports:
      - "5173:5173"
    env_file:
      - ./frontend/.env
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
    depends_on:
      - api
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres_data:
  redis_data:
```

### 4.2 Puertos y servicios

| Servicio | Puerto interno | Puerto externo (dev) | Descripción |
|----------|---------------|---------------------|-------------|
| `api` (FastAPI) | 8000 | 8000 | REST API + WebSocket |
| `db` (PostgreSQL 16) | 5432 | 5432 | Base de datos |
| `redis` (Redis 7) | 6379 | 6379 | Cache, sesiones, rate limiting |
| `frontend` (Vite) | 5173 | 5173 | Dev server con HMR |

### 4.3 Health checks

Los health checks en Docker Compose garantizan el orden correcto de startup:
- `api` espera a que `db` y `redis` estén healthy
- `frontend` espera a que `api` esté healthy (para evitar errores CORS en el startup)

---

## 5. Dev vs Producción

### 5.1 Diferencias clave

| Aspecto | Desarrollo | Producción |
|---------|-----------|-----------|
| `DEBUG` | `true` | `false` (obligatorio) |
| Hot reload | Sí (uvicorn --reload, Vite HMR) | No (workers estables) |
| Docker target | `development` | `production` (multi-stage build) |
| Frontend | Vite dev server (:5173) | Nginx sirviendo bundle estático |
| CORS origins | `localhost:5173` | Dominio HTTPS del frontend |
| SECRET_KEY | Cualquier valor | Mínimo 64 chars hex (256 bits), generado con `openssl rand -hex 32` |
| Database password | `postgres` | Contraseña fuerte, Docker secret |
| HTTPS | No | Sí (Nginx + Let's Encrypt o certificado propio) |
| Logging | `pretty` (human-readable) | `json` (estructurado para Loki/Grafana) |
| Workers | 1 | `2 * CPU + 1` (gunicorn con workers uvicorn) |
| Monitoring | No | Structured logs + /api/v1/health endpoint |

### 5.2 Variables que DEBEN cambiar en producción

```bash
# Obligatorias en producción:
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=<generar con openssl rand -hex 32>
DATABASE_URL=postgresql+asyncpg://user:secure_pass@db-host:5432/ainative
REDIS_PASSWORD=<contraseña fuerte>
REDIS_SSL=true
ALLOWED_ORIGINS=https://tu-dominio.com
FRONTEND_URL=https://tu-dominio.com
LOG_FORMAT=json
WORKERS=4                    # según CPU del VPS
```

### 5.3 `docker-compose.prod.yml` (staging/producción — esquema)

```yaml
# Agrega sobre docker-compose.yml:
services:
  api:
    build:
      target: production       # Multi-stage build sin dev dependencies
    environment:
      - DEBUG=false
      - WORKERS=4
    # Sin volumes de código (imagen contiene el código)

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - frontend_build:/usr/share/nginx/html
    depends_on:
      - api

  frontend:
    build:
      target: production       # Solo hace el build, nginx sirve el output
    volumes:
      - frontend_build:/app/dist

volumes:
  frontend_build:
```

---

## 6. Patrones de .gitignore

### 6.1 `.gitignore` de la raíz

```gitignore
# ============================================================
# Secretos y configuración local — NUNCA commitear
# ============================================================
.env
.env.local
.env.*.local
backend/.env
frontend/.env
*.pem
*.key
*.cert

# ============================================================
# Python
# ============================================================
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.venv/
venv/
env/

# ============================================================
# Node / Frontend
# ============================================================
node_modules/
frontend/dist/
frontend/build/
.vite/

# ============================================================
# Docker
# ============================================================
*.log
docker-compose.override.yml     # overrides locales, ignorar

# ============================================================
# IDE
# ============================================================
.vscode/settings.json           # settings personales (mantener .vscode/extensions.json)
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# ============================================================
# Base de datos local
# ============================================================
*.sqlite
*.db

# ============================================================
# Alembic
# ============================================================
# NO ignorar alembic/versions/ — las migraciones van en el repo
```

### 6.2 Archivos que SIEMPRE van en el repo

| Archivo | Razón |
|---------|-------|
| `env.example` | Documenta variables requeridas sin valores reales |
| `alembic/versions/*.py` | Historial de migraciones — parte del código |
| `docker-compose.yml` | Configuración del entorno de desarrollo |
| `pyproject.toml` | Dependencias y configuración del proyecto Python |
| `package.json` + `package-lock.json` | Dependencias exactas del frontend |

### 6.3 Verificación pre-commit

Se recomienda el hook de pre-commit para evitar commitear secretos accidentalmente:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: Detect hardcoded secrets

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
        args: ['--maxkb=500']
```

---

**Referencias internas**:
- `knowledge-base/04-infraestructura/03_deploy.md` — proceso de deployment
- `knowledge-base/04-infraestructura/02_dependencias.md` — dependencias del proyecto
- `scaffold-decisions.yaml` — decisiones de infraestructura y seguridad
