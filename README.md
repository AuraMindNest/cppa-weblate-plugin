<!--
SPDX-FileCopyrightText: 2026 Andrew Zhang <whisper67265@outlook.com>

SPDX-License-Identifier: BSL-1.0
-->

# cppa-weblate-plugin

## Overview

**cppa-weblate-plugin** is a small Python package (`boost_weblate` on import, `cppa-weblate-plugin` on PyPI) that extends [Weblate](https://weblate.org/) with formats needed for **Boost C++ Libraries** documentation translation. Today it implements **QuickBook** (`.qbk`): a monolingual convert pipeline that extracts translatable prose into Gettext-style workflows and writes translations back into the original template.

**Why a plugin instead of a Weblate fork?** A fork must be rebased across upstream security fixes, releases, and dependency changes. Shipping **stock Weblate** (PyPI or the official image) plus this plugin keeps you on the supported upgrade path while still teaching Weblate how to parse and serialize QuickBook. Customization lives in versioned Python code and a single settings hook, not in a divergent Weblate tree.

**Supported formats**

| Format     | Module | Status   |
| ---------- | ------ | -------- |
| QuickBook  | `boost_weblate.formats.quickbook` | Implemented |

Additional formats should follow the same split: a thin class under `src/boost_weblate/formats/` that plugs into Weblate's format APIs, with parsing and reconstruction under `src/boost_weblate/utils/`.

## Quickstart

Clone the repository, create a local virtual environment with [uv](https://docs.astral.sh/uv/), activate it, and install the package in editable mode with development dependencies (hook runner and test tooling):

```bash
git clone https://github.com/cppalliance/cppa-weblate-plugin.git
cd cppa-weblate-plugin
uv venv
source .venv/bin/activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
uv pip install -e '.[dev]'
```

Run the test suite:

```bash
pytest
```

Run with the same coverage gate as CI (terminal + XML + HTML, 90% minimum on `boost_weblate`):

```bash
pytest -v --tb=short \
  --cov=boost_weblate \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --cov-fail-under=90
coverage report
```

(`coverage.xml`, `htmlcov/`, and `.coverage` are gitignored; open `htmlcov/index.html` locally to browse line coverage.)

Run the same checks CI uses (lint, reuse, workflow lint, and pytest via [prek](https://pypi.org/project/prek/) reading `.pre-commit-config.yaml`):

```bash
prek run --all-files --show-diff-on-failure
```

Install Git hooks so those checks run on each commit:

```bash
prek install
```

**Alternative with uv groups:** if you prefer a project-local environment managed entirely by uv, `uv sync --group pre-commit` installs the hook runner and pytest into the uv environment; then use `uv run --only-group pre-commit prek run --all-files --show-diff-on-failure` and `uv run --only-group pre-commit prek install`. If you use the classic `pre-commit` CLI instead of prek, install it separately and run `pre-commit install` after syncing dependencies.

## Architecture

Weblate discovers formats by **import path** (see [WEBLATE_FORMATS config](#weblate_formats-configuration)). This repository keeps a clear boundary between "what Weblate sees" and "how a file format works."

```mermaid
flowchart TB
  subgraph weblate["Weblate"]
    WF["WEBLATE_FORMATS"]
    CF["ConvertFormat / store"]
    RP["real_patterns (URL list)"]
  end
  subgraph plugin["boost_weblate"]
    FMT["formats/ — format adapters"]
    UTL["utils/ — parse & serialize"]
    EP["endpoint/ — HTTP API + Celery"]
    TST["tests/ — mirrors src layout"]
  end
  WF --> FMT
  FMT --> CF
  FMT --> UTL
  EP -->|AppConfig.ready()| RP
  TST -.-> FMT
  TST -.-> UTL
  TST -.-> EP
```

- **`src/boost_weblate/formats/`** — Weblate-facing **format classes** (subclasses of Weblate's `BaseFormat` family, such as `weblate.formats.convert.ConvertFormat`). `QuickBookFormat` follows the same pattern as built-in convert formats (for example AsciiDoc): it turns a template file into a translation store and, on save, applies translations back using the template plus the store.

- **`src/boost_weblate/utils/`** — **Format-specific logic** with no Weblate import cycle: QuickBook parsing, segment extraction, translate-toolkit storage (`QuickBookFile` / `QuickBookUnit`), and reconstruction (`QuickBookTranslator`). New formats should add a sibling module (or package) here.

- **`src/boost_weblate/endpoint/`** — **HTTP API** for Boost documentation project/component management. Exposes three routes under `/boost-endpoint/` (see [Routes](#routes)), uses Django REST Framework for auth and serialization, and hands off heavy work to a Celery task (see [Celery task](#celery-task)).

- **`tests/`** — **Pytest** layout mirrors `src/boost_weblate/` (`tests/formats/`, `tests/utils/`, `tests/endpoint/`). Shared fixtures live under `tests/fixtures/`. `tests/conftest.py` configures `sys.path`, sets `DJANGO_SETTINGS_MODULE` to `tests.django_qbk_format_settings`, and calls `django.setup()` so format tests can load Weblate's Django stack without requiring PostgreSQL.

## WEBLATE_FORMATS configuration

Weblate discovers formats from the `WEBLATE_FORMATS` setting (see `FileFormatLoader` in upstream `weblate.formats.models`). The official Docker image evaluates a single optional file after base settings: if `/app/data/settings-override.py` exists, it is compiled and executed with `exec()` in the **same namespace** as the rest of `weblate.settings_docker`.

Stock `weblate.settings_docker` does **not** always bind `WEBLATE_FORMATS` in that namespace before the hook runs, so a bare `WEBLATE_FORMATS += (...)` in the override can raise `NameError`. This repository ships `src/boost_weblate/settings_override.py` as the Docker `exec()` fragment: it assigns `WEBLATE_FORMATS` by **reading** upstream `weblate/formats/models.py` and regex-slicing `FormatsConf.FORMATS` (aligned with the installed Weblate version, without importing `weblate.formats.models` during settings load, which can raise `AppRegistryNotReady`). It also appends the endpoint Django app to `INSTALLED_APPS` — see [`WEBLATE_ADD_APPS`](#weblate_add_apps) below.

**Operators:** ensure the plugin package is installed in the Weblate environment (`pip` / image layer), then install the override file where Weblate expects it. For the stock Docker layout:

```dockerfile
COPY settings-override.py /app/data/settings-override.py
```

That path is fixed; Weblate does not scan `DATA_DIR` for arbitrary override files. The override file is **not** the same as `WEBLATE_PY_PATH` / `python/customize` (importable customization on `sys.path`); for format registration, use this exec hook unless your image explicitly imports another settings module. See the comments in `settings_override.py` for the full distinction.

**Adding another format:** implement the class under `boost_weblate/formats/`, append its dotted class path in `weblate_formats_with_quickbook()` (or extend the tuple built there), redeploy, and restart Weblate. If upstream changes the layout of `FormatsConf` in `models.py`, update the regex in `settings_override.py` accordingly.

## WEBLATE_ADD_APPS

`WEBLATE_ADD_APPS` is a Weblate Docker environment variable that appends entries to `INSTALLED_APPS` before the container starts (handled by Weblate's own Docker entrypoint, not by this plugin).

This plugin registers the endpoint Django app in `settings_override.py` directly:

```python
# excerpt from src/boost_weblate/settings_override.py
_INSTALLED_APPS = globals().get("INSTALLED_APPS")
if _INSTALLED_APPS is not None:
    if isinstance(_INSTALLED_APPS, tuple):
        globals()["INSTALLED_APPS"] = _INSTALLED_APPS + (_ENDPOINT_APP_CONFIG,)
    else:
        _INSTALLED_APPS += (_ENDPOINT_APP_CONFIG,)
```

where `_ENDPOINT_APP_CONFIG = "boost_weblate.endpoint.apps.BoostEndpointConfig"`.

**Two approaches — pick one, not both:**

| Approach | How it works | When to use |
|----------|-------------|-------------|
| `settings_override.py` (this repo) | `exec()`'d fragment appends to `INSTALLED_APPS` directly and also sets `WEBLATE_FORMATS` | Recommended — one file covers both format registration and app installation |
| `WEBLATE_ADD_APPS` env var | Weblate Docker entrypoint adds to `INSTALLED_APPS` before Django starts | Use only if you are not deploying `settings_override.py` at all |

> **Important:** if you set `WEBLATE_ADD_APPS=boost_weblate.endpoint.apps.BoostEndpointConfig` **and** deploy `settings_override.py`, the app will be added to `INSTALLED_APPS` twice, which raises a `django.core.exceptions.ImproperlyConfigured` error at startup. Remove one source.

Note that adding the app to `INSTALLED_APPS` (by either method) is **necessary but not sufficient** for HTTP routes to be active — see [Routes](#routes) below for why.

## Routes

The plugin exposes three HTTP endpoints, all under the `/boost-endpoint/` prefix on the Weblate site:

| Method | Path | Handler | Auth | Response |
|--------|------|---------|------|----------|
| `GET` | `/boost-endpoint/plugin-ping/` | `plugin_ping` | None | `200 ok` (plain text) |
| `GET` | `/boost-endpoint/info/` | `BoostEndpointInfo` | Required | `200` JSON: `module`, `version`, `capabilities` |
| `POST` | `/boost-endpoint/add-or-update/` | `AddOrUpdateView` | Required | `202` JSON: `status`, `task_id`, `detail` |

### Why routes need explicit registration

Weblate's `urls.py` does **not** auto-discover URLconfs from arbitrary `INSTALLED_APPS` entries. It builds a single `real_patterns` list by hand and only extends it for known built-in apps (legal, SAML, git-export, etc.) via explicit `if "app" in settings.INSTALLED_APPS:` guards — there is no generic plugin scan.

This plugin handles registration in `BoostEndpointConfig.ready()` (`src/boost_weblate/endpoint/apps.py`), which runs once at Django startup and appends to `weblate.urls.real_patterns`:

```python
wl_urls.real_patterns.append(
    path(
        "boost-endpoint/",
        include(("boost_weblate.endpoint.urls", "boost_endpoint")),
    ),
)
```

The operation is idempotent (guarded by a `_cppa_boost_weblate_urls_registered` attribute on the module). Routes sit under Weblate's `URL_PREFIX` handling because `real_patterns` is used before the prefix wrapper is applied.

### Request / response for `POST /boost-endpoint/add-or-update/`

**Request body (JSON):**

```json
{
  "organization": "boostorg",
  "version": "boost-1.90.0",
  "add_or_update": {
    "zh_Hans": ["json", "unordered"],
    "ja": ["json"]
  },
  "extensions": [".adoc", ".md"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organization` | string | Yes | GitHub organization that owns the Boost submodule repos |
| `version` | string | Yes | Boost release tag, e.g. `"boost-1.90.0"` |
| `add_or_update` | object | Yes | Map of language code → list of submodule names (non-empty list per key) |
| `extensions` | array of strings | No | File extensions to scan (e.g. `[".adoc", ".md"]`); defaults to all Weblate-supported extensions |

**Response (202 Accepted):**

```json
{
  "status": "accepted",
  "task_id": "d3b07384-d9a2-4f9b-a0cf-1234567890ab",
  "detail": "Boost add-or-update is running in the background; check Celery logs or task result for completion."
}
```

The view validates the request with `AddOrUpdateRequestSerializer`, dispatches the Celery task, and returns immediately. A `400` response with an `errors` object is returned if validation fails.

## Celery task

Heavy work (git clone, file scanning, Weblate project/component create-or-update) runs asynchronously in a Celery worker via `boost_add_or_update_task` (`src/boost_weblate/endpoint/tasks.py`). The view enqueues the task with `.delay()` and returns HTTP 202 immediately.

```text
POST /boost-endpoint/add-or-update/
        │
        ▼
AddOrUpdateView.post()
  Validate body → AddOrUpdateRequestSerializer
        │ valid
        ▼
boost_add_or_update_task.delay(
    organization, add_or_update, version, extensions, user_id
)
        │                       │
        │ HTTP 202 + task_id    │ (worker picks up)
        ◄───────────────────    ▼
                        for each lang_code → submodule_list:
                            BoostComponentService(org, lang, version, extensions)
                                .process_all(submodules, user, request)
                        returns dict[lang_code → result]
```

**Task signature:**

```python
@app.task(trail=False)
def boost_add_or_update_task(
    *,
    organization: str,
    add_or_update: dict[str, list[str]],
    version: str,
    extensions: list[str] | None,
    user_id: int,
) -> dict[str, Any]:
```

- Uses Weblate's own Celery `app` instance (`weblate.utils.celery.app`), so it runs in the same worker pool as all other Weblate tasks with no extra broker configuration.
- `user_id` is passed instead of the `User` object because Celery serializes task arguments to JSON; the task re-fetches the user from the database inside the worker.
- Exceptions propagate unhandled so Celery marks the task as `FAILURE` and monitoring/alerting can act on it.
- `trail=False` suppresses Celery's default task-result trail to avoid unbounded result-backend growth.

**`BoostComponentService`** (`src/boost_weblate/endpoint/services.py`) performs the actual work for each language:

1. Clone the GitHub submodule repository for the given organization, version, and language.
2. Scan the cloned tree for files matching the requested (or all supported) extensions.
3. Build Weblate `Project` and `Component` configurations from the scan results.
4. Call `get_or_create` on each `Project`/`Component` via the Weblate ORM; update existing ones.
5. Add the target language to each component via `add_new_language`.
6. Delete stale components no longer present in the scan, commit, and push.

The service has no plugin-owned models; it operates entirely through Weblate's Django ORM.

## Contributing

- **Hooks:** use prek (or classic pre-commit) with `.pre-commit-config.yaml` so local runs match CI (Ruff, YAML/TOML checks, REUSE, actionlint, pytest).

- **Tests:** add tests next to the code you touch (`tests/formats/`, `tests/utils/`, or `tests/endpoint/`). Keep `django.setup()`-friendly patterns; heavy DB or migration suites are intentionally avoided in the bundled Django test settings.

- **CI coverage:** the *Lint and format* workflow runs a **Tests and coverage** job that prints `term-missing` output, runs `coverage report`, writes `coverage.xml` and `htmlcov/`, and uploads those plus `.coverage` as a workflow artifact (download from the run's *Artifacts* section on GitHub). Coverage is configured in `pyproject.toml` (`[tool.coverage.*]`); the job uses `uv sync --frozen --group dev --group pre-commit` so `pytest-cov` and `coverage[toml]` match the lockfile.

- **Pull requests:** open PRs against the default branch on GitHub. Keep changes focused; ensure CI is green (build/wheel checks, lint, tests). Respond to review feedback on the PR thread; for design questions or bug reports, use [Issues](https://github.com/cppalliance/cppa-weblate-plugin/issues).

## License

This plugin is BSL-licensed; when used with Weblate, Weblate's GPLv3 license applies to the combined deployment. See `LICENSE` for the Boost Software License text.
