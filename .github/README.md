<!--
SPDX-FileCopyrightText: 2026 William Jin <AuraMindNest@outlook.com>

SPDX-License-Identifier: BSL-1.0
-->

# `.github/`

GitHub Actions and CI/CD helpers for this repository.

## Workflows

| File | Role |
|------|------|
| [`workflows/ci.yml`](workflows/ci.yml) | Umbrella **CI** — runs on push/PR to `main` and `develop` |
| [`workflows/cd.yml`](workflows/cd.yml) | **Deploy** — after CI succeeds on push to `develop` (`staging`) or `main` (`production`); inline SSH script parameterized by branch |
| [`workflows/promote-main.yml`](workflows/promote-main.yml) | **Promote to production** — manual `workflow_dispatch`; ff-only `develop` → `main` via `PROMOTE_PAT` so CI and `cd.yml` run on `main` |
| [`workflows/release.yml`](workflows/release.yml) | **Release** — manual `workflow_dispatch` only; tags `main` from `pyproject.toml` (`v<version>`) and creates a GitHub Release with Weblate compatibility metadata |
| [`workflows/ci-lint.yml`](workflows/ci-lint.yml) | Lint and format (prek) |
| [`workflows/ci-test.yml`](workflows/ci-test.yml) | Unit tests and coverage |
| [`workflows/ci-package.yml`](workflows/ci-package.yml) | Build and package checks |
| [`workflows/ci-dependencies.yml`](workflows/ci-dependencies.yml) | Dependency and license audit |
| [`workflows/ci-weblate-pin.yml`](workflows/ci-weblate-pin.yml) | **Weblate version sync** — callable from CI; runs [`scripts/check-weblate-pin-sync.sh`](../scripts/check-weblate-pin-sync.sh) so `pyproject.toml` and `Dockerfile.weblate-plugin` pins match |
| [`workflows/weblate-pin-bump.yml`](workflows/weblate-pin-bump.yml) | Scheduled Weblate pin bump (PyPI + Docker + `uv.lock`) |
| [`workflows/ci-plugin-smoke.yml`](workflows/ci-plugin-smoke.yml) | Plugin smoke (Docker stack) |
| [`workflows/ci-plugin-functional.yml`](workflows/ci-plugin-functional.yml) | Plugin functional tests |
| [`workflows/ci-plugin-auth.yml`](workflows/ci-plugin-auth.yml) | Plugin auth tests |

Callable workflows (`ci-*`, `ci-plugin-*`) are triggered only via `workflow_call` from `ci.yml`, not directly on push.

## Other paths

| Path | Role |
|------|------|
| [`ci/apt-install`](ci/apt-install) | Apt packages for Weblate-related CI jobs |

### Deploy environments and secrets

[`cd.yml`](workflows/cd.yml) selects the GitHub environment from the CI branch (`workflow_run.head_branch`):

| Environment | CI branch | When deploy runs |
|-------------|-----------|------------------|
| **staging** | `develop` | After a successful CI run on a push to `develop` |
| **production** | `main` | After a successful CI run on a push to `main` (typically following [`promote-main.yml`](workflows/promote-main.yml)) |

Both environments use the **same secret names** (configure different values per host):

| Secret | Purpose |
|--------|---------|
| `SSH_HOST` | Deploy server hostname |
| `SSH_USER` | SSH user |
| `SSH_PRIVATE_KEY` | Private key for deploy |
| `WEBLATE_PORT` | Host port for post-deploy `/healthz/` poll |
| `WEBLATE_URL_PREFIX` | URL prefix for health check (e.g. `/weblate`) |
| `SSH_PORT` | Optional SSH port (default `22`) |

Server path: `/opt/cppa-weblate-plugin` with [`docker/docker-compose.cd.yml`](../docker/docker-compose.cd.yml). Full procedure: [`docs/deployment-runbook.md`](../docs/deployment-runbook.md).

### Production promotion (repository secret)

[`promote-main.yml`](workflows/promote-main.yml) is separate from deploy: it ff-only merges `develop` into `main` and pushes with **`PROMOTE_PAT`** (classic or fine-grained PAT, **Contents: write**). Without a PAT, GitHub does not trigger CI or `cd.yml` on that push. Optional: required reviewers on the **production** environment only.

## Weblate version pinning

Weblate is **not** bumped by Dependabot. A single logical release is pinned in two places:

| Location | Example | Format |
|----------|---------|--------|
| [`pyproject.toml`](../pyproject.toml) | `Weblate[all]==2026.5` | PyPI calver |
| [`docker/Dockerfile.weblate-plugin`](../docker/Dockerfile.weblate-plugin) | `FROM weblate/weblate:2026.5.0.0` | Docker fixed tag `YEAR.MONTH.PATCH.BUILD` |

Mapping lives in [`scripts/weblate-version-map.sh`](../scripts/weblate-version-map.sh). CI runs [`scripts/check-weblate-pin-sync.sh`](../scripts/check-weblate-pin-sync.sh) on every PR. [`weblate-pin-bump.yml`](workflows/weblate-pin-bump.yml) opens a PR weekly (Monday 09:00 UTC) when a newer PyPI release has a matching Docker fixed tag.
