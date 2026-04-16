#!/bin/bash
# Rollback script — revert to previous commit and redeploy
# Usage: ./rollback.sh [commit-hash]
# Without args: rolls back 1 commit

set -euo pipefail

cd "$(dirname "$0")/../.."

COMMIT="${1:-HEAD~1}"

echo "=== AI-Native Rollback ==="
echo "Rolling back to: $COMMIT"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""

read -p "Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

# 1. Backup current DB before rollback
echo "--- Backing up database ---"
bash devOps/scripts/backup-db.sh || echo "Backup failed — continuing anyway"

# 2. Checkout the target commit
echo "--- Checking out $COMMIT ---"
git checkout "$COMMIT"

# 3. Rebuild and restart
echo "--- Rebuilding services ---"
docker compose -f devOps/docker-compose.prod.yml build
docker compose -f devOps/docker-compose.prod.yml up -d

# 4. Wait for health
echo "--- Waiting for API health ---"
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "API healthy after ${i}s"
    break
  fi
  sleep 2
done

echo ""
echo "=== Rollback complete ==="
echo "Now at: $(git rev-parse --short HEAD)"
echo "NOTE: Run 'alembic downgrade' manually if the rollback includes migration changes."
