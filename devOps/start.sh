#!/usr/bin/env bash
# start.sh — Levanta el entorno de desarrollo de la Plataforma AI-Native
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVOPS_DIR="$PROJECT_ROOT/devOps"

# ─── Colores ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[ainative]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# ─── 1. Verificar Docker ───────────────────────────────────────────────────
log "Verificando Docker..."
docker info > /dev/null 2>&1 || err "Docker no está corriendo. Inicialo antes de continuar."

# ─── 2. Archivo .env ───────────────────────────────────────────────────────
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/env.example" ]; then
        warn ".env no encontrado. Copiando desde env.example..."
        cp "$PROJECT_ROOT/env.example" "$PROJECT_ROOT/.env"
        warn "Revisá y completá las variables en $PROJECT_ROOT/.env antes de continuar en producción."
    else
        err "No existe env.example en $PROJECT_ROOT. Creá un .env manualmente."
    fi
else
    log ".env encontrado."
fi

# ─── 3. Levantar servicios ─────────────────────────────────────────────────
log "Levantando servicios con Docker Compose..."
cd "$DEVOPS_DIR"
docker compose up -d

# ─── 4. Esperar a que la DB esté lista ────────────────────────────────────
log "Esperando que PostgreSQL esté disponible..."
RETRIES=30
until docker compose exec -T db pg_isready -U ainative -d ainative > /dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        err "PostgreSQL no respondió a tiempo. Revisá los logs: docker compose logs db"
    fi
    echo -n "."
    sleep 2
done
echo ""
log "PostgreSQL listo."

# ─── 5. Migraciones Alembic ────────────────────────────────────────────────
log "Ejecutando migraciones (alembic upgrade head)..."
docker compose exec -T api alembic upgrade head

# ─── 6. Seed de datos ──────────────────────────────────────────────────────
SEED_SCRIPT="$PROJECT_ROOT/backend/scripts/seed.py"
if [ -f "$SEED_SCRIPT" ]; then
    log "Cargando datos semilla..."
    docker compose exec -T api python scripts/seed.py
else
    warn "No se encontró scripts/seed.py — saltando seed de datos."
fi

# ─── 7. URLs de acceso ────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Plataforma AI-Native — Dev Ready      ${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  Frontend:   ${GREEN}http://localhost:5173${NC}"
echo -e "  API docs:   ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  API redoc:  ${GREEN}http://localhost:8000/redoc${NC}"
echo -e "  DB:         ${GREEN}postgresql://ainative:ainative@localhost:5432/ainative${NC}"
echo -e "  Redis:      ${GREEN}redis://localhost:6379${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
log "Para ver logs: docker compose logs -f api"
