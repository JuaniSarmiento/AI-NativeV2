#!/usr/bin/env bash
# restore.sh — Restaura la base de datos PostgreSQL de AI-Native desde un backup
set -euo pipefail

# ─── Configuración ────────────────────────────────────────────────────────
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-ainative}"
DB_PASS="${POSTGRES_PASSWORD:-ainative}"
DB_NAME="${POSTGRES_DB:-ainative}"

# ─── Helpers ──────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; exit 1; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*"; }

# ─── Validar argumento ────────────────────────────────────────────────────
if [ $# -ne 1 ]; then
    echo "Uso: $0 <ruta_al_backup.dump.gz>"
    echo ""
    echo "Ejemplos:"
    echo "  $0 devOps/backup/backups/ainative_20260410_120000.dump.gz"
    echo "  $0 /path/to/ainative_20260410_120000.dump.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    err "No se encontró el archivo: $BACKUP_FILE"
fi

# ─── Información del backup ───────────────────────────────────────────────
SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
log "Archivo de backup: $BACKUP_FILE"
log "Tamaño: $SIZE"
log "Destino: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

# ─── Confirmación ─────────────────────────────────────────────────────────
echo ""
echo "======================================================="
echo "  ADVERTENCIA: Esta operación DESTRUYE todos los datos"
echo "  actuales en la base de datos '$DB_NAME'."
echo "  Esta acción NO se puede deshacer."
echo "======================================================="
echo ""
read -r -p "¿Confirmar restauración? Escribí 'SI' para continuar: " CONFIRM

if [ "$CONFIRM" != "SI" ]; then
    log "Restauración cancelada por el usuario."
    exit 0
fi

# ─── Descomprimir si es necesario ─────────────────────────────────────────
DUMP_FILE="$BACKUP_FILE"
TEMP_DUMP=""

if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Descomprimiendo backup..."
    TEMP_DUMP="/tmp/ainative_restore_$$.dump"
    gunzip -c "$BACKUP_FILE" > "$TEMP_DUMP"
    DUMP_FILE="$TEMP_DUMP"
    log "Descomprimido en: $TEMP_DUMP"
fi

# ─── Terminar conexiones activas ──────────────────────────────────────────
log "Terminando conexiones activas a la base de datos..."
PGPASSWORD="$DB_PASS" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="postgres" \
    --no-password \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || warn "No se pudieron terminar todas las conexiones activas."

# ─── Restaurar ────────────────────────────────────────────────────────────
log "Iniciando restauración..."

PGPASSWORD="$DB_PASS" pg_restore \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --verbose \
    "$DUMP_FILE" 2>&1 | while IFS= read -r line; do
        log "  pg_restore: $line"
    done

log "Restauración de datos completada."

# ─── Limpiar archivo temporal ─────────────────────────────────────────────
if [ -n "$TEMP_DUMP" ] && [ -f "$TEMP_DUMP" ]; then
    rm -f "$TEMP_DUMP"
    log "Archivo temporal eliminado."
fi

# ─── Ejecutar migraciones Alembic ─────────────────────────────────────────
log "Aplicando migraciones Alembic (upgrade head)..."
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if command -v docker &>/dev/null && docker compose -f "$PROJECT_ROOT/devOps/docker-compose.yml" ps api 2>/dev/null | grep -q "Up"; then
    docker compose -f "$PROJECT_ROOT/devOps/docker-compose.yml" exec -T api alembic upgrade head
    log "Migraciones aplicadas via Docker Compose."
elif command -v alembic &>/dev/null; then
    cd "$PROJECT_ROOT/backend"
    alembic upgrade head
    log "Migraciones aplicadas via alembic local."
else
    warn "No se pudo ejecutar alembic automáticamente."
    warn "Ejecutá manualmente: docker compose exec api alembic upgrade head"
fi

log "============================================"
log "Restauración completada exitosamente."
log "Base de datos: $DB_NAME en $DB_HOST:$DB_PORT"
log "============================================"
