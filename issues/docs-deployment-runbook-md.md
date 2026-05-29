### Problem

The project had no operational documentation for deploying the plugin to a staging or production server. Operators had to reverse-engineer the Docker Compose file, Dockerfile, and environment variables to understand prerequisites, build steps, health checks, and troubleshooting — increasing the risk of misconfiguration and failed deploys.

### Acceptance Criteria

- [ ] Prerequisites table lists Docker Engine version, host PostgreSQL, Redis, reverse proxy, and git checkout requirements
- [ ] Database Setup section provides the exact SQL commands to create the Postgres user and database, plus `pg_hba.conf` guidance for Docker bridge access
- [ ] Environment File section explains how to create `.env` from `.env.example` and documents required secrets (`POSTGRES_PASSWORD`, `WEBLATE_ADMIN_PASSWORD`) with compose-enforced validation
- [ ] Plugin-specific settings section explains how `settings_override.py` wires `WEBLATE_FORMATS` and `INSTALLED_APPS` without dedicated env vars
- [ ] Weblate environment variables table documents all key variables (`WEBLATE_PORT`, `WEBLATE_SITE_DOMAIN`, `WEBLATE_URL_PREFIX`, `POSTGRES_HOST`, `REDIS_HOST`, `CELERY_SINGLE_PROCESS`, etc.) with defaults and notes
- [ ] Build and Start section provides the exact `docker compose` build and up commands
- [ ] Health Checks section documents the Docker-level healthcheck configuration (interval, timeout, retries, start_period, total grace period), external CD pipeline polling, and the plugin-specific `/boost-endpoint/plugin-ping/` endpoint
- [ ] Post-Deploy Validation section provides five runnable checks: core health, plugin ping, authenticated info endpoint, QuickBook format verification, and Celery worker ping
- [ ] Automated CD Flow section summarises the `cd.yml` pipeline steps and concurrency locking
- [ ] Troubleshooting section covers container-stays-unhealthy scenarios (AppRegistryNotReady, Postgres connection, missing `.env`, URL prefix mismatch, Redis network), GitHub SSH host key errors, restart-without-rebuild, and full teardown

### Implementation Notes

- The runbook is designed to be followed top-to-bottom for first-time setup and used as a reference for ongoing operations; sections are ordered by deployment lifecycle.
- Health check math is made explicit (e.g. `60 s + 12 × 10 s = 180 s`) so operators can tune timeouts without re-deriving them.
- The troubleshooting table uses a symptom → likely cause → fix format for quick triage.
- All `docker compose` commands use the full `-f docker/docker-compose.cd.yml --env-file .env` form to avoid ambiguity with the CI compose file.

### References

- `docs/deployment-runbook.md`
