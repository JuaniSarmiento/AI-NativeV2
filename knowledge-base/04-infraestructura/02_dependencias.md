# Dependencias del Proyecto — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto
**Clasificación**: Documentación interna — infraestructura

---

## Índice

1. [Backend Python — pyproject.toml](#1-backend-python)
2. [Frontend Node — package.json](#2-frontend-node)
3. [Estrategia de versionado](#3-estrategia-de-versionado)
4. [Seguridad y actualizaciones automáticas](#4-seguridad-y-actualizaciones)
5. [Árbol de dependencias clave](#5-árbol-de-dependencias)

---

## 1. Backend Python — pyproject.toml

El backend usa `pyproject.toml` con `uv` (o `pip`) como gestor de paquetes. Las dependencias se agrupan por funcionalidad.

### 1.1 `pyproject.toml` completo

```toml
[project]
name = "ai-native-backend"
version = "0.1.0"
description = "Backend para plataforma AI-Native — tutor socrático con CTR"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Juani", email = "juani@example.com" }]

[project.dependencies]
# ──────────────────────────────────────────────────────────────
# Web framework
# ──────────────────────────────────────────────────────────────
fastapi = ">=0.115.0,<1.0"
# FastAPI 0.115+ trae soporte nativo para lifespan, tipo-hints mejorados
# y mejor integración con Pydantic v2

uvicorn = {version = ">=0.30.0,<1.0", extras = ["standard"]}
# [standard] incluye: uvloop (event loop más rápido), httptools (parser HTTP),
# websockets, watchfiles (hot reload), python-dotenv

# ──────────────────────────────────────────────────────────────
# Base de datos
# ──────────────────────────────────────────────────────────────
sqlalchemy = {version = ">=2.0.30,<3.0", extras = ["asyncio"]}
# SQLAlchemy 2.0 async: session async, mapped columns, nuevo ORM API
# [asyncio] incluye greenlet para compatibilidad con asyncio

asyncpg = ">=0.29.0,<1.0"
# Driver async nativo para PostgreSQL. NO usa psycopg2.
# ~3-5x más rápido que el driver sync por diseño async nativo.

alembic = ">=1.13.0,<2.0"
# Migraciones de schema. Soporta multi-schema PostgreSQL.
# NOTA de drivers: la app usa asyncpg (postgresql+asyncpg://...) para runtime async.
# Alembic usa un driver SÍNCRONO (psycopg2/psycopg) en alembic.ini para las migraciones.
# Ambos coexisten: asyncpg en app, psycopg2-binary (dev dep) para alembic.

# ──────────────────────────────────────────────────────────────
# Validación y configuración
# ──────────────────────────────────────────────────────────────
pydantic = ">=2.7.0,<3.0"
# Pydantic v2: 10-50x más rápido que v1 por implementación en Rust.
# FastAPI 0.115+ requiere Pydantic v2.

pydantic-settings = ">=2.3.0,<3.0"
# Carga variables de entorno con validación de tipos en startup.
# Soporta .env files, env vars del OS, Docker secrets.

email-validator = ">=2.1.0,<3.0"
# Requerido por Pydantic para validar EmailStr.

# ──────────────────────────────────────────────────────────────
# Autenticación y seguridad
# ──────────────────────────────────────────────────────────────
python-jose = {version = ">=3.3.0,<4.0", extras = ["cryptography"]}
# JWT encoding/decoding. [cryptography] habilita RS256 para el futuro.
# CRÍTICO: siempre pasar algorithms=["HS256"] explícitamente en TODOS los decode() calls.
# python-jose tiene CVE histórico con algoritmos "none" y RS256 si no se especifica algorithms.
# NUNCA usar jose.decode(token, key) sin el argumento algorithms.

bcrypt = ">=4.1.0,<5.0"
# Hashing de contraseñas. Pure Python con C extension para performance.
# NOTA: bcrypt 4.x dropó compatibilidad con versiones < 3.6 de Python.
# Se usa bcrypt directamente (no via passlib) para evitar una dependencia extra.

# ──────────────────────────────────────────────────────────────
# Redis
# ──────────────────────────────────────────────────────────────
redis = {version = ">=5.0.0,<6.0", extras = ["hiredis"]}
# redis-py 5.x con soporte async nativo (redis.asyncio).
# [hiredis] parser C para ~5x mejor throughput en respuestas complejas.

# ──────────────────────────────────────────────────────────────
# LLM — Anthropic
# ──────────────────────────────────────────────────────────────
anthropic = ">=0.30.0,<1.0"
# SDK oficial de Anthropic. Incluye:
# - Streaming (AsyncStream)
# - Retry automático con exponential backoff
# - Token counting
# - Messages API

# ──────────────────────────────────────────────────────────────
# HTTP client (para integraciones externas)
# ──────────────────────────────────────────────────────────────
httpx = ">=0.27.0,<1.0"
# HTTP client async. Usado por el SDK de Anthropic y para tests.

# ──────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────
python-multipart = ">=0.0.9,<1.0"
# Requerido por FastAPI para parsear form data y file uploads.

structlog = ">=24.1.0,<25.0"
# Logging estructurado en JSON. Integra con el logging estándar de Python.
# Permite campos contextuales (request_id, user_id) en cada log entry.

python-slugify = ">=8.0.0,<9.0"
# Generación de slugs para IDs de ejercicios legibles.

[project.optional-dependencies]
# ──────────────────────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────────────────────
dev = [
  "pytest>=8.2.0,<9.0",
  "pytest-asyncio>=0.23.0,<1.0",   # Tests async con pytest
  "pytest-cov>=5.0.0,<6.0",        # Coverage reports
  "httpx>=0.27.0",                  # TestClient async para FastAPI
  "testcontainers>=4.4.0,<5.0",    # Containers de PostgreSQL/Redis en tests
  # testcontainers levanta containers Docker reales en tests de integración
  # Evita mocks de la DB — los tests prueban contra PostgreSQL real.

  # Linting y formateo
  "ruff>=0.4.0,<1.0",              # Linter + formatter ultrarrápido (Rust)
  "mypy>=1.10.0,<2.0",             # Type checking estático
  "pre-commit>=3.7.0,<4.0",        # Hooks pre-commit

  # Dev tools
  "ipython>=8.24.0",               # REPL mejorado para debugging
  "rich>=13.7.0",                  # Output colorido en terminal
]

[tool.pytest.ini_options]
asyncio_mode = "auto"             # Todos los tests async automáticamente
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "ANN", "S", "B", "A", "COM", "C4", "RET"]
ignore = ["ANN101", "ANN102"]     # no anotar self/cls

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

### 1.2 Tabla de dependencias de producción

| Paquete | Versión | Función |
|---------|---------|---------|
| `fastapi` | ≥0.115 | Web framework principal |
| `uvicorn[standard]` | ≥0.30 | Servidor ASGI (uvloop + websockets) |
| `sqlalchemy[asyncio]` | ≥2.0.30 | ORM async para PostgreSQL |
| `asyncpg` | ≥0.29 | Driver PostgreSQL async |
| `alembic` | ≥1.13 | Migraciones de schema |
| `pydantic` | ≥2.7 | Validación de datos (Rust core) |
| `pydantic-settings` | ≥2.3 | Configuración tipada desde env vars |
| `python-jose[cryptography]` | ≥3.3 | JWT tokens |
| `bcrypt` | ≥4.1 | Hash de contraseñas |
| `redis[hiredis]` | ≥5.0 | Cache, sesiones, rate limiting |
| `anthropic` | ≥0.30 | SDK Anthropic Claude API (claude-sonnet-4-20250514) |
| `structlog` | ≥24.1 | Logging JSON estructurado |

### 1.3 Dependencias de testing

| Paquete | Función |
|---------|---------|
| `pytest` + `pytest-asyncio` | Framework de tests con soporte async |
| `httpx` | Cliente HTTP para TestClient de FastAPI |
| `testcontainers` | PostgreSQL y Redis reales en tests de integración |
| `pytest-cov` | Coverage reports con umbral mínimo 80% |

**Por qué testcontainers y no mocks de DB**: los mocks de SQLAlchemy dan falsa confianza. Los tests de integración con containers reales detectan problemas de:
- Queries que funcionan en SQLite pero fallan en PostgreSQL (tipos de datos, JSONB, enums)
- Problemas de pool de conexiones
- Migraciones rotas
- Constraints de FK que los mocks ignoran

---

## 2. Frontend Node — package.json

### 2.1 `package.json` completo

```json
{
  "name": "ai-native-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:e2e": "playwright test",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives",
    "type-check": "tsc --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\""
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",

    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.50.0",

    "zod": "^3.23.0",

    "@monaco-editor/react": "^4.6.0",
    "monaco-editor": "^0.49.0",

    "recharts": "^2.12.0",

    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "rehype-sanitize": "^6.0.0",

    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",

    "date-fns": "^3.6.0",

    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.5.0",

    "vite": "^5.3.0",
    "@vitejs/plugin-react": "^4.3.0",

    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",

    "vitest": "^2.0.0",
    "@vitest/coverage-v8": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.4.0",
    "jsdom": "^24.1.0",

    "msw": "^2.3.0",

    "@playwright/test": "^1.45.0",

    "eslint": "^9.0.0",
    "@typescript-eslint/eslint-plugin": "^7.13.0",
    "@typescript-eslint/parser": "^7.13.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.7",

    "prettier": "^3.3.0",
    "prettier-plugin-tailwindcss": "^0.6.5"
  }
}
```

### 2.2 Tabla de dependencias clave

| Paquete | Versión | Función |
|---------|---------|---------|
| `react` + `react-dom` | ^19.0 | UI framework. React 19: Actions, `use()`, compiler |
| `react-router-dom` | ^7.0 | Routing SPA |
| `zustand` | ^5.0 | State management global (stores de auth, tutor, etc.) |
| `@tanstack/react-query` | ^5.50 | Server state, caching, sincronización con API |
| `zod` | ^3.23 | Validación de esquemas + inferencia de tipos TypeScript |
| `@monaco-editor/react` | ^4.6 | Editor de código (mismo que VS Code) |
| `recharts` | ^2.12 | Gráficos para dashboards de analytics |
| `react-markdown` | ^9.0 | Renderizado de Markdown (respuestas del tutor) |
| `rehype-sanitize` | ^6.0 | Sanitización de HTML en Markdown (anti-XSS) |
| `tailwindcss` | ^4.0 | CSS utility-first. v4: engine en Rust, sin config JS |

### 2.3 Dependencias de testing frontend

| Paquete | Función |
|---------|---------|
| `vitest` | Test runner compatible con Vite. ~10x más rápido que Jest en proyectos Vite |
| `@testing-library/react` | Testing orientado al comportamiento del usuario, no implementación |
| `jsdom` | DOM virtual para tests unitarios sin browser |
| `msw` (Mock Service Worker) | Intercepta requests HTTP y WS en tests e integración |
| `@playwright/test` | Tests E2E en browser real (Chromium/Firefox/WebKit) |

### 2.4 Descripción de dependencias clave

**zustand v5**:
- Sin boilerplate (no reducers, no actions)
- Selectores automáticos para re-renders optimizados
- Soporte nativo para slices (stores modulares)
- Compatible con DevTools de Redux

```typescript
// Ejemplo de store en Zustand 5:
import { create } from "zustand";
import { devtools } from "zustand/middleware";

interface AuthStore {
  user: User | null;
  accessToken: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  devtools(
    (set) => ({
      user: null,
      accessToken: null,
      login: async (credentials) => {
        const { user, access_token } = await authApi.login(credentials);
        set({ user, accessToken: access_token });
      },
      logout: () => set({ user: null, accessToken: null }),
    }),
    { name: "auth-store" }
  )
);
```

**@tanstack/react-query v5**:
- Gestión de server state (datos que vienen de la API)
- Cache automático con TTL configurable
- Optimistic updates para UI responsiva
- Background refetch cuando el usuario vuelve al tab

**Monaco Editor**:
- Editor de código completo con IntelliSense (para Python en los ejercicios)
- Carga bajo demanda (lazy) para no penalizar el bundle inicial
- Configuración de keybindings, temas, y linters

**MSW v2**:
- Intercepta requests en el Service Worker (en browser real)
- En tests: intercepta en Node via `@mswjs/interceptors`
- Permite simular la API sin modificar el código de producción

---

## 3. Estrategia de Versionado

### 3.1 Backend (Python)

**Formato**: `>=MAJOR.MINOR.PATCH,<NEXT_MAJOR`

Ejemplo: `fastapi = ">=0.115.0,<1.0"`

- Se acepta cualquier versión dentro del rango semver
- La cota superior es el próximo major (breaking changes)
- Se pindea el MINOR mínimo para asegurar features requeridas

**Lockfile**: `uv.lock` (con `uv`) o `requirements.txt` generado con `pip freeze` para reproducibilidad exacta en CI/CD.

```bash
# Generar lockfile:
uv lock                          # con uv
pip freeze > requirements.lock   # alternativa con pip

# Instalar desde lockfile:
uv sync --frozen                 # reproducible, no actualiza
```

### 3.2 Frontend (Node)

**Formato**: `^MAJOR.MINOR.PATCH` (caret — acepta minor y patch updates)

El `package-lock.json` (npm) garantiza reproducibilidad exacta en CI/CD.

```bash
# Instalar versiones exactas del lockfile:
npm ci                           # CI — usa package-lock.json exactamente

# Actualizar dependencias:
npm update                       # actualiza dentro del rango ^
npx npm-check-updates -u         # actualiza ranges a versiones más nuevas
```

### 3.3 Política de actualización

| Tipo de actualización | Frecuencia | Proceso |
|----------------------|------------|---------|
| Patch (bug fixes) | Semanal (automático via Dependabot) | PR automático, merge si CI pasa |
| Minor (features) | Mensual | Revisión manual del changelog |
| Major (breaking) | Caso a caso | Evaluación de impacto + migración planificada |
| Seguridad (cualquier nivel) | Inmediato | PR urgente, merge en 24h |

---

## 4. Seguridad y Actualizaciones

### 4.1 GitHub Dependabot

Configuración en `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Backend Python
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 5
    groups:
      production-dependencies:
        dependency-type: "production"
      development-dependencies:
        dependency-type: "development"
    ignore:
      # No auto-actualizar major versions
      - dependency-name: "fastapi"
        update-types: ["version-update:semver-major"]
      - dependency-name: "sqlalchemy"
        update-types: ["version-update:semver-major"]

  # Frontend Node
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 5
    groups:
      react-ecosystem:
        patterns: ["react*", "@types/react*"]
      testing:
        patterns: ["vitest*", "@testing-library*", "msw*", "playwright*"]
```

### 4.2 Audit de seguridad manual

```bash
# Backend:
pip-audit                        # escanea vulnerabilidades conocidas
safety check                     # alternativa

# Frontend:
npm audit                        # reporte de vulnerabilidades
npm audit fix                    # auto-fix vulnerabilidades no-breaking
npm audit fix --force            # fix breaking (revisar manualmente)
```

### 4.3 Vulnerabilidades conocidas a monitorear

| Paquete | CVE conocido histórico | Mitigación |
|---------|----------------------|------------|
| `python-jose` | Vulnerabilidad a algorithm confusion (none/RS256) si no se especifica `algorithms` | **OBLIGATORIO**: `algorithms=["HS256"]` en TODOS los `jwt.decode()`. Sin esto, un atacante puede firmar tokens con "none" y omitir verificación. |
| `pydantic` v1 | DoS en regex recursivos | Usar Pydantic v2 (reescrito en Rust, no afectado) |
| `fastapi` | N/A (framework joven, activo) | Mantener actualizado |
| `anthropic` SDK | N/A | Mantener actualizado (acceso a nuevos modelos) |

---

## 5. Árbol de Dependencias Clave

### 5.1 Árbol backend (simplificado)

```
ai-native-backend
├── fastapi
│   ├── starlette (routing, middleware, WebSocket)
│   ├── pydantic v2 (validación)
│   └── anyio (async I/O)
├── uvicorn[standard]
│   ├── uvloop (event loop C extension)
│   ├── httptools (HTTP parser C extension)
│   └── websockets
├── sqlalchemy[asyncio]
│   ├── asyncpg (driver PostgreSQL async)
│   └── greenlet (asyncio bridge)
├── alembic
│   └── mako (templates para migraciones)
├── anthropic
│   ├── httpx (HTTP client)
│   └── anyio
├── redis[hiredis]
│   └── hiredis (parser C)
└── pydantic-settings
    └── python-dotenv
```

### 5.2 Árbol frontend (simplificado)

```
ai-native-frontend
├── react 19
│   └── react-dom
├── react-router-dom 7
│   └── @remix-run/router
├── zustand 5
│   └── (sin dependencias externas — ~1KB)
├── @tanstack/react-query 5
│   └── (sin dependencias externas)
├── @monaco-editor/react
│   └── monaco-editor (heavy — ~5MB, cargar lazy)
├── recharts
│   ├── d3-* (subset de D3.js)
│   └── victory-vendor
├── zod 3
│   └── (sin dependencias externas — TypeScript first)
└── tailwindcss 4
    └── (@tailwindcss/vite — plugin para Vite)
```

### 5.3 Tamaño de bundle esperado (producción, gzipped)

| Chunk | Tamaño estimado | Notas |
|-------|----------------|-------|
| `react` + `react-dom` | ~45KB | React 19 es ligeramente más grande que 18 |
| `zustand` | ~2KB | Mínimo overhead |
| `@tanstack/react-query` | ~15KB | |
| `recharts` (lazy) | ~80KB | Cargar solo en páginas de analytics |
| `monaco-editor` (lazy) | ~2MB | Cargar solo en páginas de ejercicios |
| `zod` | ~12KB | |
| App code | ~100-200KB | Dependiendo del crecimiento |
| **Total sin Monaco** | **~400KB** | Initial load |
| **Con Monaco (lazy)** | **+2MB** | Solo al abrir un ejercicio |

**Estrategia de code splitting**: Monaco Editor y Recharts se cargan con `React.lazy()` + `Suspense` solo cuando el usuario accede a las rutas que los usan, evitando penalizar el tiempo inicial de carga.

---

**Referencias internas**:
- `knowledge-base/04-infraestructura/01_configuracion.md` — variables de entorno y configuración
- `knowledge-base/04-infraestructura/03_deploy.md` — Docker builds y CI/CD
- `knowledge-base/05-dx/01_onboarding.md` — setup del entorno de desarrollo
