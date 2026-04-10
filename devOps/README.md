# devOps — Plataforma AI-Native

Directorio de infraestructura, scripts operativos y documentación de deployment para la Plataforma AI-Native.

---

## Estructura

```
devOps/
├── docker-compose.yml          # Entorno de desarrollo local
├── docker-compose.prod.yml     # Override de producción
├── start.sh                    # Script de arranque para Linux/macOS
├── start.ps1                   # Script de arranque para Windows (PowerShell 7+)
├── reset_tables.sql            # Reset de todas las tablas (solo dev)
├── RUNBOOK.md                  # Guía operativa completa
├── SCALING.md                  # Estrategia de escalabilidad
├── nginx/
│   └── nginx.conf              # Configuración de nginx para producción
└── backup/
    ├── backup.sh               # Script de backup de PostgreSQL
    ├── restore.sh              # Script de restauración
    ├── README.md               # Documentación de backup
    └── backups/                # Directorio de backups (gitignored)
```

---

## Descripción de archivos

| Archivo | Propósito |
|---|---|
| `docker-compose.yml` | Define los 4 servicios de desarrollo: `api`, `db`, `redis`, `frontend` con hot-reload |
| `docker-compose.prod.yml` | Override de producción: builds desde Dockerfile, nginx, políticas restart, sin puertos expuestos para DB/Redis |
| `start.sh` | Levanta el entorno completo: verifica Docker, crea `.env` si no existe, corre migraciones y seed |
| `start.ps1` | Equivalente de `start.sh` para desarrolladores en Windows |
| `reset_tables.sql` | TRUNCATE CASCADE de todos los schemas + reset de secuencias. Solo usar en dev |
| `RUNBOOK.md` | Guía operativa: logs, migraciones, rotación de JWT, backup, troubleshooting y emergencias |
| `SCALING.md` | Análisis de cuellos de botella y plan de escala por etapa (piloto → institucional) |
| `nginx/nginx.conf` | Proxy reverso para producción: `/api/` → FastAPI, `/ws/` → WebSocket, `/` → SPA React |
| `backup/backup.sh` | pg_dump con formato custom, compresión gzip, retención de 7 días |
| `backup/restore.sh` | Restauración con confirmación interactiva, pg_restore + alembic upgrade head |
| `backup/README.md` | Estrategia de backup, automatización con cron, verificación de integridad |

---

## Referencia rápida de comandos

### Desarrollo

```bash
# Levantar entorno completo
cd devOps && ./start.sh

# Ver logs de la API
docker compose logs -f api

# Correr migraciones manualmente
docker compose exec api alembic upgrade head

# Shell de PostgreSQL
docker compose exec db psql -U ainative -d ainative

# Shell de Redis
docker compose exec redis redis-cli

# Reiniciar un servicio
docker compose restart api

# Detener todo
docker compose down
```

### Producción

```bash
# Levantar en modo producción
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Ver estado
docker compose ps
docker stats

# Health check
curl http://localhost/api/v1/health
```

### Backup

```bash
# Backup manual
./backup/backup.sh

# Restaurar
./backup/restore.sh backup/backups/ainative_20260410_120000.dump.gz
```

---

## Configuración de entornos

### Desarrollo

El entorno de desarrollo usa `docker-compose.yml` solo. Los servicios montan el código fuente como volumen para hot-reload. Las credenciales están en `.env` (copiado desde `env.example`).

Puertos expuestos en desarrollo:
- **5173** — Frontend (Vite dev server)
- **8000** — API (FastAPI + Swagger UI en `/docs`)
- **5432** — PostgreSQL
- **6379** — Redis

### Producción

El entorno de producción usa ambos compose files (`-f docker-compose.yml -f docker-compose.prod.yml`). Los servicios se construyen desde Dockerfiles. Solo nginx expone el puerto 80 (y 443 con SSL).

Ver [RUNBOOK.md](RUNBOOK.md) para operaciones detalladas y [SCALING.md](SCALING.md) para planificación de capacidad.
