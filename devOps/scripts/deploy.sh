#!/bin/bash
# Deploy script — pull latest, migrate, restart
# Usage: ./deploy.sh

set -euo pipefail

cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "=== AI-Native Deploy ==="
echo "Project: $PROJECT_ROOT"
echo "Time: $(date)"
echo ""

# 1. Pull latest code
echo "--- Pulling latest code ---"
git pull origin master

# 2. Build and restart services
echo "--- Building and restarting services ---"
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 3. Wait for API to be healthy
echo "--- Waiting for API health ---"
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "API healthy after ${i}s"
    break
  fi
  echo "  Waiting... ($i/30)"
  sleep 2
done

# 4. Run migrations
echo "--- Running migrations ---"
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# 5. Final health check
echo "--- Final health check ---"
curl -s http://localhost:8000/api/v1/health/full | python3 -m json.tool

echo ""
echo "=== Deploy complete at $(date) ==="
