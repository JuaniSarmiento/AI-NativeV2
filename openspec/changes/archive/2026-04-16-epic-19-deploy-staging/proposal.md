## Why

El sistema esta completo y testeado (EPICs 1-18). Necesitamos preparar la infraestructura de deploy para staging/produccion: Docker Compose optimizado, scripts de backup, monitoreo, seed data de produccion, y documentacion de deploy/rollback.

## What Changes

- Docker Compose de produccion con healthchecks, restart policies, volumes persistentes
- Script de backup de DB automatizado
- Script de seed data para produccion (cursos reales, cuentas piloto)
- Monitoreo basico con healthcheck endpoint y script de uptime
- Documentacion de deploy y rollback
- env.example actualizado con todas las variables necesarias

## Capabilities

### New Capabilities
- `production-deploy`: Docker Compose produccion, backup, monitoreo, seed, documentacion

## Impact

- **Infra**: Nuevo `docker-compose.prod.yml`, scripts en `devOps/scripts/`
- **Docs**: Deploy guide, rollback procedure
- **Config**: env.example completo
