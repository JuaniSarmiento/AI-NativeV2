.PHONY: dev down test lint seed migrate ingest

dev:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

test:
	cd backend && python -m pytest tests/ --tb=short -q
	cd frontend && npx vitest run

lint:
	cd backend && ruff check . && mypy app/ --ignore-missing-imports
	cd frontend && npx eslint . && npx prettier --check .

seed:
	PYTHONPATH=backend python -m infra.seed.runner

migrate:
	cd backend && alembic upgrade head

ingest:
	cd backend && python -m app.core.rag.ingest
