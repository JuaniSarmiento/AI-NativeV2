## 1. Docker Compose Production

- [x] 1.1 Create docker-compose.prod.yml with healthchecks, restart policies, persistent volumes, vite preview
- [x] 1.2 Create backend Dockerfile.prod with gunicorn entrypoint

## 2. Scripts

- [x] 2.1 Create devOps/scripts/backup-db.sh — pg_dump with timestamp and 7-day rotation
- [x] 2.2 Create devOps/scripts/seed-production.sh — create initial course, commission, docente account
- [x] 2.3 Create devOps/scripts/health-monitor.sh — poll /api/v1/health/full every 60s, log status

## 3. Configuration

- [x] 3.1 Update env.example with ALL required variables documented (Mistral, tutor config, production overrides)
- [x] 3.2 Create devOps/scripts/deploy.sh — full deploy script (pull, build, migrate, restart, health check)
- [x] 3.3 Create devOps/scripts/rollback.sh — rollback to previous version with DB backup first

## 4. Documentation

- [x] 4.1 Create DEPLOY.md with step-by-step deploy guide, scripts reference, backup, rollback, monitoring
