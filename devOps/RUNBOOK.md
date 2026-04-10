# Runbook — Plataforma AI-Native

Guía operativa para administrar y mantener la plataforma en desarrollo y producción.

---

## Índice

1. [Iniciar y detener servicios](#1-iniciar-y-detener-servicios)
2. [Ver logs](#2-ver-logs)
3. [Migraciones de base de datos](#3-migraciones-de-base-de-datos)
4. [Resetear la base de datos](#4-resetear-la-base-de-datos)
5. [Health check de servicios](#5-health-check-de-servicios)
6. [Rotar el secreto JWT](#6-rotar-el-secreto-jwt)
7. [Actualizar el system prompt del tutor](#7-actualizar-el-system-prompt-del-tutor)
8. [Backup de base de datos](#8-backup-de-base-de-datos)
9. [Problemas comunes](#9-problemas-comunes)
10. [Procedimientos de emergencia](#10-procedimientos-de-emergencia)

---

## 1. Iniciar y detener servicios

### Desarrollo

```bash
# Levantar todos los servicios
cd devOps
./start.sh           # Linux/macOS
./start.ps1          # Windows (PowerShell 7+)

# Equivalente manual
docker compose up -d

# Detener (sin eliminar datos)
docker compose stop

# Detener y eliminar contenedores (datos persisten en volúmenes)
docker compose down

# Eliminar TODO incluyendo volúmenes (¡borra datos!)
docker compose down -v
```

### Producción

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Reiniciar un servicio específico

```bash
docker compose restart api
docker compose restart frontend
docker compose restart db
docker compose restart redis
```

---

## 2. Ver logs

```bash
# Todos los servicios (follow)
docker compose logs -f

# Solo la API
docker compose logs -f api

# Solo la DB
docker compose logs -f db

# Últimas 100 líneas de la API
docker compose logs --tail=100 api

# Con timestamps
docker compose logs -f --timestamps api
```

---

## 3. Migraciones de base de datos

```bash
# Aplicar todas las migraciones pendientes
docker compose exec api alembic upgrade head

# Ver estado actual
docker compose exec api alembic current

# Ver historial de migraciones
docker compose exec api alembic history

# Crear nueva migración (auto-generate desde modelos)
docker compose exec api alembic revision --autogenerate -m "descripcion_del_cambio"

# Revertir una migración
docker compose exec api alembic downgrade -1

# Revertir a una revisión específica
docker compose exec api alembic downgrade <revision_id>
```

---

## 4. Resetear la base de datos

> **PELIGRO**: Destruye todos los datos. Solo usar en desarrollo.

```bash
# Opción 1: Script SQL
docker compose exec -T db psql -U ainative -d ainative < devOps/reset_tables.sql

# Opción 2: Recrear volumen completo
docker compose down -v
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py
```

---

## 5. Health check de servicios

```bash
# API health endpoint
curl http://localhost:8000/api/v1/health

# Respuesta esperada:
# {"status": "ok", "db": "connected", "redis": "connected", "version": "x.x.x"}

# Estado de contenedores Docker
docker compose ps

# Estadísticas de recursos
docker stats

# Verificar DB directamente
docker compose exec db pg_isready -U ainative -d ainative

# Verificar Redis
docker compose exec redis redis-cli ping
# Respuesta esperada: PONG
```

---

## 6. Rotar el secreto JWT

La rotación invalida **todos los tokens activos**. Coordinar con los usuarios si es producción.

```bash
# 1. Generar nuevo secreto (256 bits, base64)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Actualizar en .env
#    JWT_SECRET_KEY=<nuevo_valor>

# 3. Reiniciar la API para que tome el nuevo valor
docker compose restart api

# 4. Verificar que el servicio arrancó
docker compose logs --tail=20 api
curl http://localhost:8000/api/v1/health
```

> Nota: Los tokens emitidos con el secreto anterior dejarán de ser válidos inmediatamente. Los usuarios tendrán que hacer login de nuevo.

---

## 7. Actualizar el system prompt del tutor

El system prompt del tutor está definido en `backend/app/services/tutor/prompts.py`.

```bash
# 1. Editar el archivo de prompts
#    backend/app/services/tutor/prompts.py

# 2. En desarrollo (con --reload): el cambio se aplica automáticamente

# 3. En producción: reiniciar la API
docker compose restart api

# 4. Verificar el nuevo comportamiento con una sesión de prueba
curl -X POST http://localhost:8000/api/v1/tutor/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"exercise_id": 1}'
```

---

## 8. Backup de base de datos

```bash
# Backup manual
./devOps/backup/backup.sh

# El archivo se guarda en: devOps/backup/backups/
# Nombre: ainative_YYYYMMDD_HHMMSS.dump.gz

# Restaurar desde backup
./devOps/backup/restore.sh devOps/backup/backups/ainative_20260410_120000.dump.gz
```

Ver documentación completa en [backup/README.md](backup/README.md).

---

## 9. Problemas comunes

### DB connection refused

**Síntoma**: `asyncpg.exceptions.ConnectionRefusedError` en la API.

```bash
# Verificar que la DB está corriendo
docker compose ps db
docker compose logs db

# Si está caída, reiniciar
docker compose restart db

# Esperar healthcheck y reiniciar API
docker compose restart api
```

### Redis timeout / connection error

**Síntoma**: `redis.exceptions.TimeoutError` o `ConnectionError`.

```bash
# Verificar Redis
docker compose exec redis redis-cli ping

# Ver uso de memoria
docker compose exec redis redis-cli info memory

# Si hay problema de memoria, limpiar cache (¡no datos críticos!)
docker compose exec redis redis-cli FLUSHDB

# Reiniciar Redis
docker compose restart redis
docker compose restart api
```

### LLM rate limited (Anthropic API)

**Síntoma**: `429 Too Many Requests` en logs de la API, errores en el tutor.

```bash
# Ver logs de rate limiting
docker compose logs api | grep "rate_limit\|429\|RateLimitError"

# Opciones:
# 1. Esperar el reset del rate limit (generalmente 1 minuto)
# 2. Verificar el tier de la API key en console.anthropic.com
# 3. Activar el fallback a Ollama si está configurado (ver .env)
```

### Puerto ya en uso

**Síntoma**: `Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use`.

```bash
# Encontrar el proceso que usa el puerto
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :6379

# Terminar el proceso
sudo kill -9 <PID>

# O cambiar el puerto en docker-compose.yml
```

### Migraciones en estado inconsistente

**Síntoma**: `alembic.util.exc.CommandError: Target database is not up to date`.

```bash
# Ver estado actual
docker compose exec api alembic current
docker compose exec api alembic history

# Marcar como aplicada (si la migración ya se aplicó manualmente)
docker compose exec api alembic stamp head

# O revertir y re-aplicar
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

---

## 10. Procedimientos de emergencia

### Sandbox escape detectado

Si el sistema detecta un intento de escape del sandbox de ejecución de código:

```bash
# 1. Ver el evento en los logs de governance
docker compose exec db psql -U ainative -d ainative \
  -c "SELECT * FROM governance.sandbox_events WHERE severity = 'critical' ORDER BY created_at DESC LIMIT 10;"

# 2. Identificar el usuario/submission involucrado
# 3. Suspender el usuario temporalmente vía API admin
curl -X PATCH http://localhost:8000/api/v1/admin/users/<user_id>/suspend \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"reason": "sandbox_escape_attempt"}'

# 4. Registrar el incidente en governance.audit_logs
# 5. Notificar al docente responsable
# 6. Revisar el código de la submission involucrada
```

### Violación de integridad CTR (Control de Trampa)

Si se detecta que un alumno manipuló la integridad de una entrega:

```bash
# 1. Ver las violaciones recientes
docker compose exec db psql -U ainative -d ainative \
  -c "SELECT * FROM governance.integrity_checks WHERE status = 'violation' ORDER BY created_at DESC LIMIT 20;"

# 2. Obtener detalles de la submission
# Campo hash_mismatch indica qué fue alterado

# 3. Marcar la submission como inválida
curl -X PATCH http://localhost:8000/api/v1/admin/submissions/<submission_id>/invalidate \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"reason": "integrity_violation", "details": "..."}'

# 4. Generar reporte para el docente
curl http://localhost:8000/api/v1/admin/reports/integrity?user_id=<user_id> \
  -H "Authorization: Bearer <admin_token>"
```
