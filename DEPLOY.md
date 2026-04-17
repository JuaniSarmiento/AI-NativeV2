# Deploy Guide — AI-Native

## Prerequisites

- Docker + Docker Compose
- Git
- Server with 2GB+ RAM

## Quick Deploy

```bash
# 1. Clone
git clone https://github.com/JuaniSarmiento/AI-NativeV2.git
cd AI-NativeV2

# 2. Configure
cp env.example .env
# Edit .env with production values:
#   SECRET_KEY=<openssl rand -hex 32>
#   POSTGRES_PASSWORD=<strong password>
#   MISTRAL_API_KEY=<your key>
#   APP_ENV=production
#   DEBUG=false

# 3. Deploy
docker compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# 5. Seed initial data
bash devOps/scripts/seed-production.sh

# 6. Verify
curl http://localhost:8000/api/v1/health/full
```

## Scripts

| Script | Description |
|--------|-------------|
| `devOps/scripts/deploy.sh` | Pull + build + migrate + restart |
| `devOps/scripts/rollback.sh [commit]` | Rollback to previous version |
| `devOps/scripts/backup-db.sh` | Database backup with 7-day rotation |
| `devOps/scripts/seed-production.sh` | Create initial docente + course |
| `devOps/scripts/health-monitor.sh` | Poll health endpoint every 60s |

## Backup

```bash
# Manual backup
bash devOps/scripts/backup-db.sh

# Cron (daily at 3am)
0 3 * * * /path/to/devOps/scripts/backup-db.sh >> /var/log/ainative-backup.log 2>&1
```

## Rollback

```bash
# Rollback 1 commit
bash devOps/scripts/rollback.sh

# Rollback to specific commit
bash devOps/scripts/rollback.sh abc1234

# If migration changed, also run:
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

## Monitoring

```bash
# One-time health check
curl http://localhost:8000/api/v1/health/full

# Continuous monitoring
nohup bash devOps/scripts/health-monitor.sh >> /var/log/ainative-health.log 2>&1 &
```

## Default Accounts (after seed)

| Role | Email | Password |
|------|-------|----------|
| Docente | docente@utn.edu | DocE2E2026! |
| Admin | admin@utn.edu | AdmE2E2026! |
