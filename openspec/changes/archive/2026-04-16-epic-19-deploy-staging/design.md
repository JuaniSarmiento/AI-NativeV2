## Context

Dev environment uses docker-compose.yml in devOps/ with hot reload. Production needs: no hot reload, gunicorn workers, persistent volumes, healthchecks, restart policies, secrets management.

## Decisions

### D1: docker-compose.prod.yml separado
No modificar el de dev. Archivo separado con overrides de produccion.

### D2: Backup via pg_dump cron script
Simple pg_dump diario a directorio con rotacion de 7 dias.

### D3: Monitoreo via healthcheck endpoint + script
El /api/v1/health/full ya existe. Script que lo consulta periodicamente y alerta.
