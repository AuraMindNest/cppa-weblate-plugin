### Problem

The project had no continuous deployment pipeline. After CI passed on the `develop` branch, there was no automated mechanism to deploy the updated plugin to the staging server, build the CD Docker image, verify container health, or report failures — requiring manual SSH and docker commands for every deploy.

### Acceptance Criteria

- [ ] `cd.yml` workflow triggers automatically after a successful CI run on the `develop` branch (via `workflow_run` event)
- [ ] Workflow SSHes to the deploy server at `/opt/cppa-weblate-plugin`, pulls the latest code, and runs `docker compose -f docker/docker-compose.cd.yml --env-file .env build && up -d`
- [ ] Health check polls `http://127.0.0.1:9103/weblate/healthz/` for up to 120 seconds (24 attempts × 5 s) after deploy
- [ ] On health check failure, the last 40 lines of container logs are dumped and the workflow exits non-zero
- [ ] Concurrency is locked per branch with `cancel-in-progress: false` so deploys never overlap
- [ ] `docker-compose.cd.yml` builds an overlay image on `weblate/weblate:latest` that copies `settings_override.py` and installs the plugin via `uv pip install`
- [ ] CD compose binds to `127.0.0.1:${WEBLATE_PORT}` (default 9103), uses host PostgreSQL via `host.docker.internal`, and connects to Redis via the external `boost-data-collector_default` network
- [ ] Required secrets (`POSTGRES_PASSWORD`, `WEBLATE_ADMIN_PASSWORD`) are enforced via `${VAR:?set in .env}` syntax — compose refuses to start if unset
- [ ] `.env.example` provides an annotated template covering all Compose-only, required-secret, Weblate setup, SSL/proxy, access control, PostgreSQL, Redis, email, and Celery variables
- [ ] CI sub-workflows are renamed from `ci-integration-*` to `ci-combination-*` and updated to reference `docker-compose.ci.yml` (renamed from `docker-compose.yml`)

### Implementation Notes

- The CD workflow uses `workflow_run` to chain off the CI workflow rather than duplicating CI checks, keeping the pipeline DRY.
- The compose file uses `extra_hosts: ["host.docker.internal:host-gateway"]` so the containerised Weblate can reach the host PostgreSQL without exposing Postgres on the Docker bridge network.
- The external Redis network (`boost-data-collector_default`) is expected to already exist from a sibling stack; this avoids running a second Redis instance.
- The `docker-compose.yml` → `docker-compose.ci.yml` rename and `ci-integration-*` → `ci-combination-*` workflow renames were done in the same commit to keep CI and CD compose files clearly distinguished.
- Integration test helpers (`docker_exec.py`, `gh_repo.py`, `compose.sh`, `weblate-stack.sh`) were updated to reference the renamed CI compose file.

### References

- `.github/workflows/cd.yml`
- `docker/docker-compose.cd.yml`
- `.env.example`
- `.github/workflows/ci.yml`
- `.github/workflows/ci-combination-smoke.yml`
- `.github/workflows/ci-combination-auth.yml`
- `.github/workflows/ci-combination-functional.yml`
- `.github/workflows/ci-lint.yml`
- `.github/workflows/ci-test.yml`
- `.github/workflows/ci-package.yml`
- `.github/workflows/ci-dependencies.yml`
- `docker/docker-compose.ci.yml`
- `docker/README.md`
- `.github/README.md`
- `scripts/README.md`
- `scripts/lib/compose.sh`
- `scripts/lib/weblate-stack.sh`
- `scripts/integration-functional.sh`
- `tests/integration/lib/docker_exec.py`
- `tests/integration/lib/gh_repo.py`
- `tests/integration/test_functional.py`
- `pyproject.toml`
- `uv.lock`
