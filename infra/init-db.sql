-- AI-Native platform schema initialization
-- Runs once on first container start (docker-entrypoint-initdb.d)

CREATE SCHEMA IF NOT EXISTS operational;
CREATE SCHEMA IF NOT EXISTS cognitive;
CREATE SCHEMA IF NOT EXISTS governance;
CREATE SCHEMA IF NOT EXISTS analytics;
