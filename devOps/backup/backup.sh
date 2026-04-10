#!/usr/bin/env bash
# backup.sh — Realiza un backup de la base de datos PostgreSQL de AI-Native
set -euo pipefail

# ─── Configuración ────────────────────────────────────────────────────────
BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backups"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-ainative}"
DB_PASS="${POSTGRES_PASSWORD:-ainative}"
DB_NAME="${POSTGRES_DB:-ainative}"
RETAIN_DAYS=7

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# ─── Helpers ──────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ─── Preparar directorio ──────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ─── Dump ────────────────────────────────────────────────────────────────
log "Iniciando backup de '$DB_NAME' en $DB_HOST:$DB_PORT..."

PGPASSWORD="$DB_PASS" pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --verbose \
    --no-password \
    --file="$BACKUP_FILE" 2>&1 | while IFS= read -r line; do
        log "  pg_dump: $line"
    done

log "Dump completado: $BACKUP_FILE"

# ─── Comprimir ────────────────────────────────────────────────────────────
log "Comprimiendo backup..."
gzip -9 "$BACKUP_FILE"
log "Backup comprimido: $COMPRESSED_FILE"

# ─── Tamaño del archivo ───────────────────────────────────────────────────
SIZE=$(du -sh "$COMPRESSED_FILE" | cut -f1)
log "Tamaño final: $SIZE"

# ─── Limpiar backups antiguos ─────────────────────────────────────────────
log "Eliminando backups con más de $RETAIN_DAYS días..."
DELETED=0
while IFS= read -r old_file; do
    rm -f "$old_file"
    log "  Eliminado: $(basename "$old_file")"
    DELETED=$((DELETED + 1))
done < <(find "$BACKUP_DIR" -name "*.dump.gz" -mtime "+$RETAIN_DAYS" -type f)

if [ "$DELETED" -eq 0 ]; then
    log "No hay backups antiguos para eliminar."
else
    log "Se eliminaron $DELETED backups antiguos."
fi

# ─── Listado actual ───────────────────────────────────────────────────────
log "Backups actuales en $BACKUP_DIR:"
ls -lhtr "$BACKUP_DIR"/*.dump.gz 2>/dev/null | while IFS= read -r line; do
    log "  $line"
done

log "Backup completado exitosamente: $(basename "$COMPRESSED_FILE")"
