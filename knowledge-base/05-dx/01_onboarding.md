# Onboarding — Guía para Nuevos Desarrolladores

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Indice

1. [Prerequisitos del Sistema](#1-prerequisitos-del-sistema)
2. [Clonar y Configurar el Repositorio](#2-clonar-y-configurar-el-repositorio)
3. [Levantar la Infraestructura con Docker](#3-levantar-la-infraestructura-con-docker)
4. [Configurar el Backend](#4-configurar-el-backend)
5. [Configurar el Frontend](#5-configurar-el-frontend)
6. [Verificar que Todo Funciona](#6-verificar-que-todo-funciona)
7. [Configurar el IDE](#7-configurar-el-ide)
8. [Problemas Frecuentes del Primer Día](#8-problemas-frecuentes-del-primer-día)
9. [Próximos Pasos](#9-próximos-pasos)

---

## 1. Prerequisitos del Sistema

Antes de clonar el repositorio, asegurate de tener instaladas las siguientes herramientas en las versiones correctas. Versiones menores pueden funcionar, pero no están soportadas oficialmente.

### Obligatorio

| Herramienta | Versión mínima | Verificar con |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ (LTS) | `node --version` |
| npm | 10+ | `npm --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ (plugin v2) | `docker compose version` |
| Git | 2.40+ | `git --version` |

> Nota: en Linux, el comando es `docker compose` (plugin v2), no `docker-compose` (v1 legacy). Si tu sistema tiene la versión v1, actualizá o instalá el plugin.

### Recomendado

| Herramienta | Motivo |
|---|---|
| `pyenv` | Gestionar versiones de Python sin conflictos con el sistema |
| `nvm` o `fnm` | Gestionar versiones de Node.js por proyecto |
| `make` | Atajos de comandos frecuentes vía Makefile del repo |
| `httpie` | Testear endpoints REST desde terminal de forma legible |
| VS Code | IDE recomendado, con extensiones descriptas en sección 7 |
| DBeaver | GUI para inspeccionar PostgreSQL |

### macOS (adicional)

```bash
# Instalar Homebrew si no lo tenés
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar herramientas
brew install python@3.12 node@20 git
brew install --cask docker
```

### Linux (Ubuntu/Debian)

```bash
# Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update && sudo apt install python3.12 python3.12-venv python3.12-dev

# Node 20 via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20 && nvm use 20

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER  # requiere logout/login
```

### Windows

Se recomienda usar **WSL2** (Windows Subsystem for Linux) con Ubuntu 22.04. El desarrollo directo en Windows no está soportado por diferencias en paths, line endings, y comportamiento del sandbox de Python (ver sección 8).

---

## 2. Clonar y Configurar el Repositorio

### Clonar

```bash
git clone https://github.com/utn-frm/ai-native-platform.git
cd ai-native-platform
```

### Estructura de alto nivel

```
ai-native-platform/
├── backend/          # FastAPI application
├── frontend/         # React 19 + Vite application
├── shared/           # Contratos compartidos (tipos, constantes)
├── infra/            # Kubernetes / Terraform configs
├── devOps/           # CI/CD pipelines, Dockerfiles
├── knowledge-base/   # Esta documentación
├── docker-compose.yml
├── docker-compose.override.yml  # Solo existe en dev
├── .env.example
└── Makefile
```

### Variables de entorno

```bash
# Copiar el template de variables de entorno
cp .env.example .env
```

Abrir `.env` y completar los valores que tienen `CHANGE_ME`:

```dotenv
# === POSTGRES ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ainative
POSTGRES_USER=ainative_user
POSTGRES_PASSWORD=CHANGE_ME          # Cambiar en dev por algo memorable

# === REDIS ===
REDIS_HOST=localhost
REDIS_PORT=6379

# === JWT ===
JWT_SECRET_KEY=CHANGE_ME             # Generar con: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === ANTHROPIC ===
ANTHROPIC_API_KEY=CHANGE_ME          # Obtener en https://console.anthropic.com/
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=4096

# === BACKEND ===
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# === FRONTEND ===
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

> IMPORTANTE: Nunca committear el archivo `.env` con credenciales reales. El `.gitignore` ya lo excluye, pero verificalo con `git status`.

Generar una clave JWT segura para desarrollo:

```bash
openssl rand -hex 32
# Pegar el output en JWT_SECRET_KEY
```

---

## 3. Levantar la Infraestructura con Docker

El `docker-compose.yml` levanta PostgreSQL 16 y Redis 7. La aplicación corre fuera de Docker en desarrollo para mayor velocidad de hot-reload.

```bash
# Levantar PostgreSQL y Redis en background
docker compose up -d postgres redis

# Verificar que están corriendo
docker compose ps
```

Output esperado:

```
NAME                IMAGE               STATUS          PORTS
ainative-postgres   postgres:16         Up              0.0.0.0:5432->5432/tcp
ainative-redis      redis:7-alpine      Up              0.0.0.0:6379->6379/tcp
```

### Comandos útiles de Docker

```bash
# Ver logs de postgres
docker compose logs -f postgres

# Ver logs de redis
docker compose logs -f redis

# Acceder a psql directamente
docker compose exec postgres psql -U ainative_user -d ainative

# Acceder a redis-cli
docker compose exec redis redis-cli

# Detener todo sin borrar volúmenes
docker compose stop

# Borrar todo incluyendo datos (reset total)
docker compose down -v
```

> Advertencia: `docker compose down -v` borra los volúmenes de datos. Usarlo solo cuando querés empezar desde cero.

---

## 4. Configurar el Backend

### Crear entorno virtual e instalar dependencias

```bash
cd backend

# Crear entorno virtual con Python 3.12
python3.12 -m venv .venv

# Activar (Linux/macOS)
source .venv/bin/activate

# Activar (Windows WSL2)
source .venv/bin/activate

# Verificar que el venv está activo
which python  # debe apuntar a backend/.venv/bin/python

# Instalar dependencias (incluyendo dev)
pip install -e ".[dev]"
```

> El proyecto usa `pyproject.toml` con dependencias opcionales `[dev]` para herramientas de testing y linting. `pip install -e ".[dev]"` instala todo.

### Ejecutar migraciones de Alembic

La base de datos tiene 4 schemas separados: `operational`, `cognitive`, `governance`, `analytics`. Las migraciones crean todos en orden.

```bash
# Asegurarse de estar en backend/ con el venv activo
# y que PostgreSQL esté corriendo

# Aplicar todas las migraciones
alembic upgrade head

# Verificar el estado
alembic current

# Ver historial de migraciones
alembic history --verbose
```

Output esperado de `alembic current`:

```
INFO  [alembic.runtime.migration] Running on postgresql+asyncpg://...
<revision_id> (head)
```

### Cargar datos de seed

```bash
# Cargar datos iniciales (usuarios de prueba, ejercicios demo, configuración)
python scripts/seed_data.py

# Output esperado:
# Creando schemas...          OK
# Creando roles...            OK
# Creando usuario admin...    OK (admin@utn.edu.ar / admin123dev)
# Creando usuario profesor... OK (profesor@utn.edu.ar / prof123dev)
# Creando usuario alumno...   OK (alumno@utn.edu.ar / alumno123dev)
# Cargando ejercicios demo... OK (10 ejercicios)
# Seed completado.
```

> Las contraseñas de seed son solo para desarrollo local. En staging/producción, el seed no crea usuarios con contraseñas hardcodeadas.

### Levantar el servidor de desarrollo

```bash
# Desde backend/ con el venv activo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternativa via Makefile (desde raíz del repo)
make backend-dev
```

Verificar: abrir `http://localhost:8000/docs` — debe aparecer la UI de Swagger con todos los endpoints documentados.

Endpoints de healthcheck:

```bash
# Healthcheck básico
curl http://localhost:8000/health
# Respuesta: {"status":"ok","version":"0.1.0"}

# Healthcheck con dependencias (postgres, redis)
curl http://localhost:8000/health/full
# Respuesta: {"status":"ok","postgres":"connected","redis":"connected"}
```

---

## 5. Configurar el Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Levantar servidor de desarrollo
npm run dev
```

Vite levanta el servidor en `http://localhost:5173`. Tiene hot-reload automático: cada cambio en `.tsx` / `.ts` se refleja instantáneamente sin recargar la página.

### Verificar que el frontend conecta con el backend

1. Abrir `http://localhost:5173`
2. Debería aparecer la pantalla de login
3. Ingresar con `alumno@utn.edu.ar` / `alumno123dev`
4. Verificar que redirige al dashboard sin errores en la consola del browser

### Variables de entorno del frontend

El frontend usa variables con prefijo `VITE_` en un archivo `.env` dentro de `frontend/`:

```bash
# frontend/.env (ya debería existir, se copia desde el .env raíz automáticamente)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_APP_ENV=development
```

> Las variables `VITE_*` se exponen al cliente. Nunca poner secrets ahí.

---

## 6. Verificar que Todo Funciona

### Checklist de verificación

```bash
# 1. Infraestructura
docker compose ps  # postgres y redis Up

# 2. Backend corriendo
curl http://localhost:8000/health
# {"status":"ok"}

# 3. Backend conecta a postgres y redis
curl http://localhost:8000/health/full
# {"status":"ok","postgres":"connected","redis":"connected"}

# 4. Login via API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alumno@utn.edu.ar","password":"alumno123dev"}'
# Debe devolver {"status":"ok","data":{"access_token":"...","refresh_token":"..."}}

# 5. Frontend accesible
curl -s http://localhost:5173 | grep -c "AI-Native"
# Debe retornar 1
```

### Ejecutar los tests

```bash
# Tests del backend (desde backend/ con venv activo)
pytest tests/ -v

# Tests rápidos (excluye tests de integración que requieren postgres real)
pytest tests/unit/ -v

# Tests con coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Tests del frontend (desde frontend/)
npm run test

# Tests E2E con Playwright (requiere que backend y frontend estén corriendo)
npm run test:e2e
```

Output esperado de pytest:

```
==================== test session starts ====================
collected 80+ items

tests/unit/test_hash_chain.py ............. PASSED
tests/unit/test_validators.py .......... PASSED
tests/integration/test_auth_routes.py ....... PASSED
...
==================== 80 passed in 12.34s ====================
```

---

## 7. Configurar el IDE

### VS Code (recomendado)

Instalar las extensiones del workspace (VS Code las sugiere automáticamente al abrir el repo, o instalar manualmente):

```bash
# Instalar via CLI todas las extensiones recomendadas
cat .vscode/extensions.json | jq -r '.recommendations[]' | xargs -L1 code --install-extension
```

#### Extensiones esenciales

| Extensión | ID | Motivo |
|---|---|---|
| Python | `ms-python.python` | Soporte Python completo |
| Pylance | `ms-python.vscode-pylance` | Type checking con mypy |
| Ruff | `charliermarsh.ruff` | Linter + formatter Python |
| ESLint | `dbaeumer.vscode-eslint` | Linting TypeScript/React |
| Prettier | `esbenp.prettier-vscode` | Formateo automático frontend |
| Tailwind CSS IntelliSense | `bradlc.vscode-tailwindcss` | Autocomplete de clases Tailwind |
| PostCSS Language Support | `csstools.postcss` | Sintaxis CSS moderno |
| SQLTools | `mtxr.sqltools` | Conexión a PostgreSQL desde VS Code |
| SQLTools PostgreSQL | `mtxr.sqltools-driver-pg` | Driver para SQLTools |
| GitLens | `eamodio.gitlens` | Visualización de historial Git |
| Thunder Client | `rangav.vscode-thunder-client` | Testeo de APIs REST dentro de VS Code |
| Docker | `ms-azuretools.vscode-docker` | Gestión de contenedores |

#### Configuración de workspace

El archivo `.vscode/settings.json` ya está en el repo con la configuración correcta:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "typescript.tsdk": "frontend/node_modules/typescript/lib",
  "eslint.workingDirectories": ["frontend"],
  "tailwindCSS.experimental.configFile": "frontend/tailwind.config.ts"
}
```

#### Configurar SQLTools para PostgreSQL local

1. Abrir la paleta de comandos: `Ctrl+Shift+P` → `SQLTools: Add New Connection`
2. Seleccionar PostgreSQL
3. Completar:
   - Host: `localhost`
   - Port: `5432`
   - Database: `ainative`
   - Username: `ainative_user`
   - Password: (la que pusiste en `.env`)
4. Guardar y conectar

### PyCharm / IntelliJ

Si preferís PyCharm:

1. Abrir la carpeta `backend/` como proyecto
2. Configurar el intérprete apuntando a `backend/.venv/bin/python`
3. Instalar el plugin `Ruff` para linting
4. Activar "Use per-project Python interpreter"
5. Configurar el test runner como `pytest` con working directory `backend/`

---

## 8. Problemas Frecuentes del Primer Día

### Error: `ModuleNotFoundError: No module named 'app'`

**Causa**: pytest no encuentra el módulo `app` porque no estás en el directorio correcto o el paquete no está instalado en modo editable.

**Solución**:
```bash
# Asegurarte de estar en backend/ con el venv activo
cd backend
source .venv/bin/activate
pip install -e ".[dev]"   # el -e (editable) es clave
pytest tests/
```

### Error: `asyncpg.exceptions.ConnectionDoesNotExistError`

**Causa**: La base de datos no está corriendo, o las credenciales en `.env` no coinciden con el contenedor.

**Solución**:
```bash
docker compose ps          # verificar que postgres está Up
docker compose logs postgres  # buscar errores en el log
# Si cambió la contraseña después de crear el contenedor:
docker compose down -v     # borrar volúmenes
docker compose up -d postgres
alembic upgrade head        # volver a migrar
python scripts/seed_data.py # volver a seedear
```

### Error: `alembic.util.exc.CommandError: Can't locate revision identified by...`

**Causa**: El estado de Alembic en la base de datos no coincide con los archivos de migración (puede pasar después de hacer `git pull` con nuevas migraciones).

**Solución**:
```bash
alembic current   # ver en qué revisión está
alembic history   # ver el árbol de revisiones
alembic upgrade head  # avanzar a la última
# Si hay conflicto total:
docker compose down -v && docker compose up -d postgres
alembic upgrade head
python scripts/seed_data.py
```

### Error en frontend: `VITE_API_BASE_URL is not defined`

**Causa**: El archivo `frontend/.env` no existe o no tiene la variable.

**Solución**:
```bash
# Verificar que existe
ls frontend/.env
# Si no existe:
cp .env.example frontend/.env
# Editar frontend/.env con los valores correctos
```

### El hot-reload de Vite no funciona en WSL2

**Causa**: WSL2 tiene problemas con `inotify` para detectar cambios de archivos.

**Solución**: Agregar a `frontend/vite.config.ts`:
```typescript
export default defineConfig({
  server: {
    watch: {
      usePolling: true,  // Agregar esto
      interval: 1000,
    },
  },
})
```

### Error: `ImportError: cannot import name 'model_config' from 'pydantic'`

**Causa**: Hay una versión de Pydantic v1 instalada en el entorno. El proyecto requiere Pydantic v2.

**Solución**:
```bash
pip show pydantic  # verificar versión
# Si es v1:
pip install "pydantic>=2.0"
# O recrear el venv:
deactivate
rm -rf backend/.venv
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e ".[dev]"
```

### Error: `jwt.exceptions.DecodeError` en tests

**Causa**: La variable `JWT_SECRET_KEY` en `.env` no está configurada o tiene el valor por defecto `CHANGE_ME`.

**Solución**:
```bash
# Generar una clave válida
openssl rand -hex 32
# Pegar en .env en JWT_SECRET_KEY
```

### Error de CORS en el frontend: `Access-Control-Allow-Origin`

**Causa**: El backend solo permite requests desde `http://localhost:5173` por defecto. Si cambiaste el puerto de Vite, hay que actualizar la configuración.

**Solución**: En `backend/app/core/config.py`, la lista `CORS_ORIGINS` se lee desde `.env`. Agregar el origen del frontend:
```dotenv
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Los tests de integración son muy lentos

**Causa**: Cada test de integración levanta un contenedor PostgreSQL fresco via `testcontainers`. Es por diseño: garantizan aislamiento total.

**Optimización**: Para desarrollo rápido, correr solo los unit tests y dejar los de integración para CI:
```bash
pytest tests/unit/ -v          # rápido, sin docker
pytest tests/integration/ -v   # lento, requiere docker running
```

---

## 9. Próximos Pasos

Una vez que todo funciona:

1. **Leer la arquitectura**: `knowledge-base/02-arquitectura/01_arquitectura_general.md` — entender el sistema antes de tocar código.
2. **Entender el dominio**: `knowledge-base/01-negocio/01_vision_y_contexto.md` — el modelo N4, CTR, trazabilidad cognitiva.
3. **Revisar las convenciones**: `knowledge-base/05-dx/04_convenciones_y_estandares.md` — cómo se escribe el código en este proyecto.
4. **Revisar las trampas conocidas**: `knowledge-base/05-dx/03_trampas_conocidas.md` — errores que ya resolvimos para que no los repitas.
5. **Asignarte una issue**: revisar el tablero de GitHub y asignarte una issue del sprint actual.
6. **Leer el workflow**: `knowledge-base/05-dx/05_workflow_implementacion.md` — cómo hacer una PR correctamente.

Cualquier duda, preguntarle al tech lead o abrir una discusión en GitHub. Bienvenido al equipo.
