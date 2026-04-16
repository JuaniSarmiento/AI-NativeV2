#!/bin/bash
# Health monitor — polls the full health endpoint every 60s
# Usage: ./health-monitor.sh
# Run in background: nohup ./health-monitor.sh >> /var/log/ainative-health.log 2>&1 &

API="${API_URL:-http://localhost:8000}"
INTERVAL=60

echo "[$(date)] Health monitor started. Checking $API every ${INTERVAL}s"

while true; do
  STATUS=$(curl -s -o /tmp/health_response.json -w "%{http_code}" "$API/api/v1/health/full" 2>/dev/null || echo "000")

  if [ "$STATUS" = "200" ]; then
    DB=$(python3 -c "import json; d=json.load(open('/tmp/health_response.json')); print(d['data'].get('database','?'))" 2>/dev/null)
    REDIS=$(python3 -c "import json; d=json.load(open('/tmp/health_response.json')); print(d['data'].get('redis','?'))" 2>/dev/null)
    echo "[$(date)] OK — db=$DB redis=$REDIS"
  elif [ "$STATUS" = "503" ]; then
    echo "[$(date)] DEGRADED (503) — some services unhealthy"
    cat /tmp/health_response.json 2>/dev/null
  else
    echo "[$(date)] DOWN ($STATUS) — API not responding"
  fi

  sleep $INTERVAL
done
