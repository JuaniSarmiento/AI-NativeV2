#!/bin/bash
# Database backup script — run daily via cron
# Usage: ./backup-db.sh
# Cron example: 0 3 * * * /path/to/backup-db.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/juani/ProyectosFacultad/AI-Native/devOps/backups}"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_USER="${POSTGRES_USER:-ainative}"
DB_NAME="${POSTGRES_DB:-ainative}"
DB_HOST="${POSTGRES_HOST:-localhost}"

BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting backup of $DB_NAME..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Dump and compress
docker compose -f devOps/docker-compose.prod.yml exec -T db \
  pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "[$(date)] Cleanup done. $REMAINING backups retained."
