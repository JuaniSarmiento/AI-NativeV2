# Tooling — Herramientas de Desarrollo

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Indice

1. [Backend — Herramientas Python](#1-backend--herramientas-python)
2. [Frontend — Herramientas JavaScript/TypeScript](#2-frontend--herramientas-javascripttypescript)
3. [Base de Datos — PostgreSQL](#3-base-de-datos--postgresql)
4. [Docker — Contenedores e Infraestructura Local](#4-docker--contenedores-e-infraestructura-local)
5. [Testeo de APIs](#5-testeo-de-apis)
6. [Git Hooks — Pre-commit](#6-git-hooks--pre-commit)
7. [Makefile — Comandos de Conveniencia](#7-makefile--comandos-de-conveniencia)
8. [CI/CD — GitHub Actions](#8-cicd--github-actions)

---

## 1. Backend — Herramientas Python

### uvicorn — Servidor ASGI

`uvicorn` es el servidor ASGI que corre la aplicación FastAPI en desarrollo y producción.

```bash
# Desarrollo: con hot-reload automático
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Con log level más detallado
uvicorn app.main:app --reload --log-level debug

# Producción (sin reload, múltiples workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Con SSL (staging)
uvicorn app.main:app --ssl-keyfile ./key.pem --ssl-certfile ./cert.pem
```

El flag `--reload` monitorea cambios en archivos `.py` y reinicia automáticamente el proceso. En producción NO se usa `--reload` ni `--workers` juntos — son mutuamente excluyentes.

Configuración relevante en `backend/app/core/config.py`:
- `BACKEND_HOST`: host de binding (default `0.0.0.0`)
- `BACKEND_PORT`: puerto (default `8000`)
- `RELOAD`: activar reload (solo en `ENVIRONMENT=development`)

### pytest — Framework de Testing

El proyecto usa `pytest` con plugins async para testing de FastAPI + SQLAlchemy.

```bash
# Correr todos los tests
pytest

# Con output verbose (ver nombre de cada test)
pytest -v

# Con output muy verbose (ver prints y logs)
pytest -s -v

# Correr solo un archivo
pytest tests/unit/test_hash_chain.py -v

# Correr solo un test específico
pytest tests/unit/test_hash_chain.py::test_compute_hash_deterministic -v

# Correr tests que matcheen un pattern en el nombre
pytest -k "test_auth" -v

# Con coverage report en terminal
pytest --cov=app --cov-report=term-missing

# Con coverage report en HTML (abrir htmlcov/index.html)
pytest --cov=app --cov-report=html

# Mostrar los 10 tests más lentos
pytest --durations=10

# Correr en paralelo (plugin pytest-xdist, instalar con pip)
pytest -n auto

# Solo tests marcados como "unit" (via @pytest.mark.unit)
pytest -m unit

# Excluir tests marcados como "slow"
pytest -m "not slow"
```

Configuración de pytest en `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"        # todos los tests async corren con asyncio automáticamente
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
markers = [
    "unit: tests unitarios sin dependencias externas",
    "integration: tests de integración con postgres real",
    "adversarial: tests de prompts adversariales al tutor",
    "slow: tests que tardan más de 5 segundos",
]
```

### alembic — Migraciones de Base de Datos

`alembic` gestiona el esquema de la base de datos. El proyecto usa 4 schemas PostgreSQL separados: `operational`, `cognitive`, `governance`, `analytics`.

```bash
# Ver revisión actual aplicada
alembic current

# Ver historial completo de revisiones
alembic history --verbose

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar una migración específica
alembic upgrade <revision_id>

# Deshacer la última migración
alembic downgrade -1

# Deshacer hasta una revisión específica
alembic downgrade <revision_id>

# Generar una nueva migración automática (detecta cambios en modelos)
alembic revision --autogenerate -m "add_exercise_difficulty_column"

# Generar una migración vacía (para escribir SQL manual)
alembic revision -m "add_search_index_on_exercises"

# Ver el SQL que generaría una migración sin ejecutarla
alembic upgrade head --sql
```

> IMPORTANTE: Las migraciones autogeneradas con `--autogenerate` deben revisarse manualmente antes de aplicar. Alembic no detecta todo correctamente, especialmente los cambios de tipo, índices complejos, y restricciones a nivel de schema.

Estructura de migraciones en `backend/alembic/`:
```
alembic/
├── env.py              # Configuración del contexto de migración
├── script.py.mako      # Template para nuevas migraciones
└── versions/
    ├── 0001_initial_schemas.py
    ├── 0002_create_users_table.py
    └── ...
```

Para migraciones multi-schema, el `env.py` incluye configuración especial que se detalla en `knowledge-base/05-dx/03_trampas_conocidas.md`.

### ruff — Linter y Formatter Python

`ruff` reemplaza a `flake8`, `isort`, `black`, y `pep8` en un solo binario extremadamente rápido.

```bash
# Verificar estilo sin modificar archivos
ruff check .

# Verificar con auto-fix de problemas simples
ruff check . --fix

# Formatear código (equivalente a black)
ruff format .

# Verificar formato sin modificar
ruff format . --check

# Revisar un solo archivo
ruff check app/services/tutor_service.py
```

Configuración en `backend/pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]
ignore = [
    "E501",  # line too long (ruff format lo maneja)
    "B008",  # do not perform function calls in default arguments (FastAPI Depends)
]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

### mypy — Verificación de Tipos Estáticos

`mypy` verifica los type hints de Python de forma estática, sin ejecutar el código.

```bash
# Verificar todo el proyecto
mypy app/

# Verificar un módulo específico
mypy app/services/tutor_service.py

# Con output detallado
mypy app/ --show-error-codes --pretty

# Ignorar errores en módulos sin stubs (útil para bibliotecas terceras)
mypy app/ --ignore-missing-imports
```

Configuración en `backend/pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
```

El modo `strict = true` activa todas las verificaciones estrictas: `--disallow-untyped-defs`, `--disallow-any-generics`, `--warn-return-any`, etc.

---

## 2. Frontend — Herramientas JavaScript/TypeScript

### Vite — Servidor de Desarrollo y Bundler

`vite` es el build tool del frontend. Ofrece arranque instantáneo y hot-reload basado en ES modules nativos.

```bash
# Servidor de desarrollo
npm run dev
# Disponible en http://localhost:5173

# Build de producción
npm run build
# Output en frontend/dist/

# Preview del build de producción localmente
npm run preview
# Disponible en http://localhost:4173

# Build con análisis de bundle (requiere rollup-plugin-visualizer)
npm run build:analyze
```

Configuración relevante en `frontend/vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          zustand: ['zustand'],
        },
      },
    },
  },
})
```

### Vitest — Testing de Unidad e Integración

`vitest` es el test runner del frontend, compatible con la API de Jest pero integrado con Vite.

```bash
# Correr tests en modo watch (desarrollo)
npm run test

# Correr tests una sola vez (CI)
npm run test:run

# Con coverage report
npm run test:coverage

# Con UI interactiva (abre browser con reporte)
npm run test:ui

# Correr un archivo específico
npx vitest run src/stores/authStore.test.ts

# Correr tests que matcheen un pattern
npx vitest run --reporter=verbose -t "should update user"
```

Configuración en `frontend/vite.config.ts` (sección test):

```typescript
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './src/test/setup.ts',
  coverage: {
    provider: 'v8',
    reporter: ['text', 'lcov', 'html'],
    exclude: ['src/test/**', '**/*.d.ts', 'src/main.tsx'],
  },
}
```

### Playwright — Tests E2E

`playwright` ejecuta tests de extremo a extremo en browsers reales (Chromium, Firefox, WebKit).

```bash
# Instalar browsers (solo primera vez)
npx playwright install

# Correr todos los tests E2E
npm run test:e2e

# Correr con UI interactiva (ver el browser)
npx playwright test --ui

# Correr en modo headed (ver el browser sin UI interactiva)
npx playwright test --headed

# Correr solo un archivo de test
npx playwright test e2e/auth.spec.ts

# Generar reporte HTML y abrirlo
npx playwright show-report

# Modo debug (pausa en cada paso)
npx playwright test --debug

# Generar test desde interacción manual (codegen)
npx playwright codegen http://localhost:5173
```

Configuración en `frontend/playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: './e2e',
  baseURL: 'http://localhost:5173',
  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },
})
```

### ESLint — Linter TypeScript/React

```bash
# Verificar estilo
npm run lint

# Auto-fix problemas corregibles
npm run lint:fix
```

Configuración en `frontend/eslint.config.ts` (flat config de ESLint 9):

- `@typescript-eslint/recommended-type-checked`: reglas estrictas de TypeScript
- `eslint-plugin-react-hooks`: reglas para hooks de React
- `eslint-plugin-react-refresh`: reglas para Vite HMR

### Prettier — Formatter

```bash
# Formatear todos los archivos
npm run format

# Verificar sin modificar
npm run format:check
```

Configuración en `frontend/.prettierrc`:
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

## 3. Base de Datos — PostgreSQL

### psql CLI

```bash
# Conectar a la base de datos local (via docker compose)
docker compose exec postgres psql -U ainative_user -d ainative

# Comandos útiles dentro de psql:
\dn          -- listar schemas
\dt          -- listar tablas en schema actual
\dt operational.*  -- listar tablas del schema operational
\d users     -- describir estructura de la tabla users
\l           -- listar bases de datos
\c ainative  -- cambiar a base de datos ainative
\x           -- modo expanded (filas en vertical, más legible)
\q           -- salir

# Ejecutar query directamente sin entrar al REPL
docker compose exec postgres psql -U ainative_user -d ainative \
  -c "SELECT id, email FROM operational.users LIMIT 5;"

# Ejecutar un archivo SQL
docker compose exec postgres psql -U ainative_user -d ainative \
  -f /path/to/query.sql
```

### DBeaver (GUI recomendada)

DBeaver es una GUI gratuita y open-source que soporta PostgreSQL y sus features avanzados (schemas, particiones, JSONB, etc.).

**Configuración de conexión**:
1. Nueva conexión → PostgreSQL
2. Host: `localhost`, Port: `5432`
3. Database: `ainative`
4. Username: `ainative_user`, Password: (del `.env`)
5. Test connection → Finish

**Features útiles de DBeaver para este proyecto**:
- Navegación por schemas: expandir `ainative` → `Schemas` → ver los 4 schemas
- JSONB viewer: al hacer SELECT de columnas JSONB, DBeaver las muestra como árbol navegable
- ER Diagram: click derecho en schema → View Diagram
- Query history: `Ctrl+Alt+H`
- Export de resultados a CSV

### pgAdmin (alternativa web)

Si preferís pgAdmin, el `docker-compose.yml` incluye un servicio opcional:

```bash
# Levantar pgAdmin
docker compose --profile tools up -d pgadmin

# Acceder en http://localhost:5050
# Email: admin@admin.com
# Password: admin (solo local)
```

### Queries frecuentes para debugging

```sql
-- Ver todas las tablas por schema
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('operational', 'cognitive', 'governance', 'analytics')
ORDER BY schemaname, tablename;

-- Ver el tamaño de cada tabla
SELECT
  schemaname,
  relname AS tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;

-- Ver conexiones activas
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
WHERE datname = 'ainative';

-- Ver índices de una tabla
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'cognitive_trace_records';

-- Revisar el hash chain (últimos 5 registros)
SELECT id, created_at, hash, previous_hash
FROM cognitive.cognitive_trace_records
ORDER BY created_at DESC
LIMIT 5;
```

---

## 4. Docker — Contenedores e Infraestructura Local

### Comandos esenciales

```bash
# Levantar servicios en background
docker compose up -d

# Levantar solo servicios específicos
docker compose up -d postgres redis

# Levantar con reconstrucción de imágenes
docker compose up -d --build

# Ver estado de todos los servicios
docker compose ps

# Ver logs de un servicio (con follow)
docker compose logs -f postgres
docker compose logs -f redis

# Ver logs de todos los servicios
docker compose logs -f

# Ejecutar comando en un contenedor en ejecución
docker compose exec postgres psql -U ainative_user -d ainative
docker compose exec redis redis-cli

# Ver métricas de uso de recursos
docker stats

# Detener todos los servicios (sin borrar datos)
docker compose stop

# Detener y eliminar contenedores (sin borrar volúmenes)
docker compose down

# Borrar todo incluyendo volúmenes (reset total, DESTRUCTIVO)
docker compose down -v

# Reconstruir una imagen específica
docker compose build backend

# Ver imágenes locales
docker images | grep ainative
```

### Troubleshooting de Docker

```bash
# Puerto ya en uso (5432 ocupado por postgres local)
# Solución: cambiar el puerto en docker-compose.yml o detener postgres local
sudo systemctl stop postgresql    # Linux
brew services stop postgresql     # macOS

# Contenedor no arranca
docker compose logs postgres      # ver el error

# Volumen corrupto
docker compose down -v            # borrar volúmenes
docker compose up -d postgres     # levantar de nuevo

# Limpiar todo (imágenes, contenedores, volúmenes huérfanos)
docker system prune -a            # CUIDADO: borra todo lo que no está en uso
```

---

## 5. Testeo de APIs

### httpie (recomendado por legibilidad)

```bash
# Instalar
pip install httpie

# Login
http POST localhost:8000/api/v1/auth/login \
  email=alumno@utn.edu.ar \
  password=alumno123dev

# Con token (guardar en variable)
TOKEN=$(http -b POST localhost:8000/api/v1/auth/login \
  email=alumno@utn.edu.ar \
  password=alumno123dev | jq -r '.data.access_token')

# Request autenticado
http GET localhost:8000/api/v1/exercises \
  Authorization:"Bearer $TOKEN"

# POST con JSON complejo
http POST localhost:8000/api/v1/exercises \
  Authorization:"Bearer $TOKEN" \
  title="Fibonacci" \
  description="Implementar Fibonacci iterativo" \
  difficulty=2

# Con query params
http GET localhost:8000/api/v1/exercises \
  Authorization:"Bearer $TOKEN" \
  page==1 per_page==20 difficulty==2
```

### curl (sin dependencias extra)

```bash
# Login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alumno@utn.edu.ar","password":"alumno123dev"}' | jq

# Guardar token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alumno@utn.edu.ar","password":"alumno123dev"}' \
  | jq -r '.data.access_token')

# Request autenticado
curl -s http://localhost:8000/api/v1/exercises \
  -H "Authorization: Bearer $TOKEN" | jq

# POST
curl -s -X POST http://localhost:8000/api/v1/exercises \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Fibonacci","description":"...","difficulty":2}' | jq
```

### OpenAPI — Swagger UI

FastAPI genera automáticamente la documentación interactiva de la API:

- **Swagger UI**: `http://localhost:8000/docs` — interfaz interactiva, permite hacer requests
- **ReDoc**: `http://localhost:8000/redoc` — documentación estática, más legible
- **OpenAPI JSON**: `http://localhost:8000/openapi.json` — schema en formato JSON

En Swagger UI:
1. Click en `Authorize` (esquina superior derecha)
2. Ingresar: `Bearer <tu_token>`
3. Los requests subsiguientes incluyen el header automáticamente

---

## 6. Git Hooks — Pre-commit

El proyecto usa `pre-commit` para ejecutar linting y formateo automáticamente antes de cada commit. Esto garantiza que el código que llega al repositorio siempre pasa los checks básicos.

### Instalación

```bash
# Instalar pre-commit (ya está en las dependencias dev del backend)
pip install pre-commit

# Instalar los hooks en el repositorio local
pre-commit install

# Opcional: instalar también el hook de commit-msg para validar convenciones
pre-commit install --hook-type commit-msg
```

### Configuración en `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      # Backend: ruff check
      - id: ruff-check
        name: ruff (lint)
        language: system
        entry: bash -c 'cd backend && ruff check .'
        types: [python]
        pass_filenames: false

      # Backend: ruff format
      - id: ruff-format
        name: ruff (format)
        language: system
        entry: bash -c 'cd backend && ruff format --check .'
        types: [python]
        pass_filenames: false

      # Backend: mypy (solo en archivos cambiados)
      - id: mypy
        name: mypy (type check)
        language: system
        entry: bash -c 'cd backend && mypy app/'
        types: [python]
        pass_filenames: false

      # Frontend: eslint
      - id: eslint
        name: eslint
        language: system
        entry: bash -c 'cd frontend && npm run lint'
        types_or: [ts, tsx]
        pass_filenames: false

      # Frontend: prettier
      - id: prettier
        name: prettier
        language: system
        entry: bash -c 'cd frontend && npm run format:check'
        types_or: [ts, tsx, css, json]
        pass_filenames: false

      # Conventional commits
      - id: conventional-commits
        name: conventional commits
        language: pygrep
        entry: '^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+'
        stages: [commit-msg]
```

### Uso

```bash
# El hook corre automáticamente al hacer git commit
git add .
git commit -m "feat(auth): add refresh token rotation"
# Si algún check falla, el commit se cancela

# Correr los hooks manualmente en todos los archivos
pre-commit run --all-files

# Correr un hook específico
pre-commit run ruff-check

# Omitir hooks en casos de emergencia (NO abusar)
git commit --no-verify -m "wip: work in progress"
```

---

## 7. Makefile — Comandos de Conveniencia

El repositorio incluye un `Makefile` en la raíz con atajos para los comandos más frecuentes:

```bash
# Desarrollo
make dev              # Levantar docker + backend + frontend en paralelo
make backend-dev      # Solo backend con uvicorn --reload
make frontend-dev     # Solo frontend con vite dev

# Tests
make test             # Todos los tests (backend + frontend)
make test-backend     # Solo tests del backend
make test-frontend    # Solo tests del frontend
make test-e2e         # Tests E2E con Playwright
make test-cov         # Tests con coverage report

# Base de datos
make migrate          # alembic upgrade head
make migrate-new      # alembic revision --autogenerate
make seed             # python scripts/seed_data.py
make db-reset         # docker compose down -v + up + migrate + seed

# Linting
make lint             # ruff check + mypy + eslint + prettier check
make lint-fix         # ruff check --fix + ruff format + eslint --fix + prettier

# Docker
make up               # docker compose up -d
make down             # docker compose down
make logs             # docker compose logs -f

# Utilidades
make clean            # Limpiar caches, __pycache__, dist, coverage
make help             # Mostrar todos los comandos disponibles
```

---

## 8. CI/CD — GitHub Actions

El pipeline de CI corre automáticamente en cada push y PR. Configurado en `.github/workflows/`.

### Workflow principal: `ci.yml`

```
push/PR → lint → test-unit → test-integration → build
```

Cada job corre en paralelo donde es posible:
- `lint`: ruff + mypy + eslint + prettier (30s aprox)
- `test-unit`: pytest tests/unit + vitest (1min aprox)
- `test-integration`: pytest tests/integration con testcontainers (3min aprox)
- `build`: docker build + vite build (2min aprox)

### Ver el estado del CI

```bash
# Via GitHub CLI
gh run list
gh run view <run_id>
gh run watch <run_id>

# Ver logs de un job fallido
gh run view <run_id> --log-failed
```

El merge a `main` requiere que todos los jobs de CI pasen. No hay excepciones salvo aprobación explícita del tech lead.
