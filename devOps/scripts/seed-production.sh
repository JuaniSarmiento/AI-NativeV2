#!/bin/bash
# Seed production database with initial data
# Usage: ./seed-production.sh

set -euo pipefail

API="${API_URL:-http://localhost:8000/api/v1}"

echo "=== Seeding production data ==="

# 1. Register docente
echo "Creating docente account..."
DOCENTE=$(curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"docente@utn.edu","password":"DocE2E2026!","full_name":"Docente UTN","role":"docente"}')
DOCENTE_ID=$(echo "$DOCENTE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "already exists")
echo "  Docente: $DOCENTE_ID"

# 2. Register admin
echo "Creating admin account..."
curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@utn.edu","password":"AdmE2E2026!","full_name":"Admin UTN","role":"admin"}' > /dev/null 2>&1
echo "  Admin created"

# 3. Login as docente
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"docente@utn.edu","password":"DocE2E2026!"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 4. Create course
echo "Creating course..."
COURSE=$(curl -s -X POST "$API/courses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Programacion I - 2026","description":"Curso de Programacion I, UTN FRM, 2do semestre 2026"}')
COURSE_ID=$(echo "$COURSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "failed")
echo "  Course: $COURSE_ID"

# 5. Create commission
echo "Creating commission..."
curl -s -X POST "$API/courses/$COURSE_ID/commissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"K2026-1\",\"year\":2026,\"semester\":2,\"teacher_id\":\"$DOCENTE_ID\"}" > /dev/null 2>&1
echo "  Commission K2026-1 created"

echo ""
echo "=== Seed complete ==="
echo "Docente login: docente@utn.edu / DocE2E2026!"
echo "Admin login:   admin@utn.edu / AdmE2E2026!"
echo "Course: Programacion I - 2026 / Commission: K2026-1"
