<!--
SPDX-FileCopyrightText: 2026 Andrew Zhang <whisper67265@outlook.com>

SPDX-License-Identifier: BSL-1.0
-->

# docker/

Shared Docker assets for CI and CD.

- **Dockerfile.weblate-plugin** — Overlay on `weblate/weblate:latest`; installs the plugin via `uv pip install` and copies `settings-override.py`.
- **docker-compose.ci.yml** — PostgreSQL + Redis + Weblate stack for integration tests and CI.
- **docker-compose.cd.yml** — Weblate-only stack for staging/production (host Postgres, shared Redis).

## Usage

```bash
# CI / integration tests (from repo root):
docker compose -f docker/docker-compose.ci.yml build
docker compose -f docker/docker-compose.ci.yml up -d

# CD on deploy server (repo-root .env required; no secret defaults in compose):
docker compose -f docker/docker-compose.cd.yml --env-file .env up -d
```
