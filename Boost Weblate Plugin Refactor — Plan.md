# Boost Weblate Plugin Refactor — Plan

**Goal:** Replace the `boost-weblate` Weblate fork with a standalone plugin package `cppa-weblate-plugin`
installed on top of **upstream Weblate from PyPI**.  Once complete, the `boost-weblate` fork repo is retired
and the `weblate-docker` Dockerfile installs only upstream Weblate + this plugin.  The package must meet
Alliance minimum engineering standards: tests (≥ 90 % coverage), CI, CD, reproducible installation, and full
documentation.

> **Context:** This refactor is a direct response to the quality review (April 2026).
> Findings WL1–WL12 from the CppDigest repo cleanup tracker are addressed here.

---

## Package Structure

```
cppa-weblate-plugin/
├── LICENSE                          ← BSL-1.0 (confirm with Alliance legal) [WL-new]
├── README.md                        ← package overview, quickstart, architecture section, config reference [WL1]
├── docs/
│   ├── deployment-runbook.md        ← install, rollback, health checks [WL7]
│   └── boost-endpoint-api.md        ← OpenAPI / REST reference for /boost-endpoint/ [WL8]
├── pyproject.toml                   ← declares ALL runtime deps [WL9]
├── .github/
│   └── workflows/
│       ├── ci.yml                   ← pytest, ruff, coverage gate [WL6, WL12]
│       └── integration.yml          ← Weblate + package smoke tests [WL6]
├── tests/
│   ├── formats/
│   │   └── test_quickbook.py        ← QuickBook parser unit tests [WL5]
│   └── endpoint/
│       ├── test_views.py            ← boost_endpoint request/response tests [WL5, WL8]
│       └── test_services.py         ← BoostComponentService unit tests [WL5]
└── src/boost_weblate/
    ├── formats/
    │   └── quickbook.py             ← QuickBook format implementation
    ├── utils/
    │   └── quickbook.py             ← QuickBook utilities
    └── endpoint/                    ← boost_endpoint Django app
        ├── apps.py                  ← AppConfig; registers boost-endpoint URLs in ready()
        ├── urls.py
        ├── views.py
        ├── serializers.py
        └── services.py
```

### Settings wiring

Follows the [official Weblate customization pattern](https://docs.weblate.org/en/latest/admin/customize.html).
All wiring is done once as **committed infrastructure changes** to `weblate-docker` — no manual steps at deploy time.

**`weblate-docker/Dockerfile`** — add the plugin install and bake in the settings override:

```dockerfile
# Install the plugin (after upstream weblate install)
# renovate: datasource=github-tags depName=cppalliance/cppa-weblate-plugin
RUN uv pip install --compile-bytecode \
    "git+https://github.com/cppalliance/cppa-weblate-plugin@<tag>"

# Bake settings override into the image
COPY weblate-docker/settings-override.py /app/data/settings-override.py
```

**`weblate-docker/settings-override.py`** (new committed file, copied into image):

```python
# Register the QuickBook format (no env-var equivalent for WEBLATE_FORMATS).
WEBLATE_FORMATS += ("boost_weblate.formats.quickbook.QuickBookFormat",)
```

**`weblate-docker/environment.example`** — `INSTALLED_APPS` via `WEBLATE_ADD_APPS` (standard Docker env var):

```bash
# boost_weblate plugin
WEBLATE_ADD_APPS=boost_weblate.endpoint
```

The `boost-endpoint` URL registration is handled in `BoostEndpointConfig.ready()` inside `apps.py`
(no `ROOT_URLCONF` override needed — this follows the `AppConfig`-based pattern).

---

## Quality Baseline (applies to every phase)

| Requirement | Standard | Tracker ref |
|-------------|----------|-------------|
| Test coverage | ≥ 90 % (enforced by `--cov-fail-under=90`) | WL5, WL12 |
| CI | GitHub Actions: `pytest`, `ruff check`, coverage gate on every PR | WL6 |
| Integration test | CI job: `uv pip install weblate "git+https://…/cppa-weblate-plugin@HEAD"` in a Docker-compose stack → smoke-test endpoint + format registration | WL6 |
| CD | Dockerfile installs plugin from Git (`git+https://…/cppa-weblate-plugin@<tag>`) and `COPY`s `settings-override.py` (containing only `WEBLATE_FORMATS +=`) into the image; `WEBLATE_ADD_APPS` env var handles `INSTALLED_APPS`; URL registration in `AppConfig.ready()`. | new |
| LICENSE | BSL-1.0 file in repo root (confirm with Alliance legal) | new |
| Runtime deps | All deps declared in `pyproject.toml`; no implicit system deps without docs | WL9 |
| Documentation | README (quickstart + architecture section), deployment runbook, REST API reference | WL1, WL7, WL8 |
| Reproducible install | `uv pip install "git+https://…/cppa-weblate-plugin@<tag>"` works against upstream Weblate PyPI package | new |

---

## Phases

### Phase 0 — Repo Skeleton & Documentation (Days 1–3)

Addresses **WL1** (bus-factor / knowledge capture) before any code moves.

- Create `cppa-weblate-plugin` repo with `pyproject.toml`, `LICENSE`, `.github/` stub
  (create `ci.yml` and `integration.yml` as empty placeholder workflows now so PRs have CI targets from day one).
- Write `README.md`: package overview, quickstart, end-to-end architecture section (Weblate → QuickBook format →
  boost-endpoint → boost-docs-translation), and config reference — addresses **WL1**.
- Write `docs/deployment-runbook.md`: install steps, env vars, rollback (pin back to previous tag in Dockerfile
  and redeploy), health checks.
- Document the `boost-endpoint` REST contract in `docs/boost-endpoint-api.md` (resolves WL8 / BDT9 linkage).
- Declare all runtime dependencies in `pyproject.toml` (weblate pin, any remaining deps) — **WL9**.
- Document `settings-override.py` location and delivery: the file is committed to `weblate-docker/` and
  `COPY`-ed into the image at build time — no manual volume seeding required at deploy time.
  `INSTALLED_APPS` is wired via `WEBLATE_ADD_APPS` in `weblate-docker/environment.example`.
  URL registration is handled in `BoostEndpointConfig.ready()` — no `ROOT_URLCONF` override needed.

### Phase 1 — QuickBook (Days 4–9)

- Implement `formats/quickbook.py` and `utils/quickbook.py` in the package;
  register via `WEBLATE_FORMATS +=`.
  The existing `boost-weblate` fork serves as a behavioural reference only — code is written fresh.
- **Tests:** unit tests for the QuickBook parser (round-trip parse + edge cases).
  QuickBook is the highest-risk untested code — **WL5** first target.
  Target: ≥ 90 % coverage on `formats/quickbook.py` and `utils/quickbook.py`.

### Phase 2 — boost_endpoint App (Days 6–14, parallel with P1)

Implement `src/boost_weblate/endpoint/` fresh.
The existing `boost-weblate` fork serves as a behavioural reference only — code is written fresh.

URL registration is handled in `BoostEndpointConfig.ready()` via Django's URL include mechanism
(no `ROOT_URLCONF` override — follows the official [Weblate customization pattern](https://docs.weblate.org/en/latest/admin/customize.html)):

```python
# src/boost_weblate/endpoint/apps.py
from django.apps import AppConfig

class BoostEndpointConfig(AppConfig):
    name = "boost_weblate.endpoint"
    label = "boost_endpoint"
    verbose_name = "Boost documentation translation API"

    def ready(self):
        from django.urls import include, path
        from weblate.urls import urlpatterns
        urlpatterns += [
            path("boost-endpoint/", include("boost_weblate.endpoint.urls")),
        ]
```

**Tests:** unit + integration tests for every view in `boost_weblate/endpoint/`.
Every REST endpoint must have a request/response test — **WL5**, **WL8**.

**WL11:** The 300s `time.sleep()` in `add_language_to_component` blocks the request thread.
Refactor to a Celery task chain or background thread so the HTTP response returns immediately.

### Phase 3 — CI / CD / Coverage Enforcement (Days 13–21)

- Wire GitHub Actions:
  - **CI workflow** (`ci.yml`): `ruff check`, `pytest --cov --cov-fail-under=90`, coverage upload — **WL6, WL12**.
  - **Integration workflow** (`integration.yml`): `uv pip install weblate "git+https://…/cppa-weblate-plugin@HEAD"`
    in a Docker-compose stack → smoke-test format registration and `/boost-endpoint/` responses — **WL6**.
- Consolidate settings wiring: commit `weblate-docker/settings-override.py` (containing only `WEBLATE_FORMATS +=`)
  and add `COPY` of it into the Dockerfile; add `WEBLATE_ADD_APPS=boost_weblate.endpoint`
  to `weblate-docker/environment.example`. URL registration is in `AppConfig.ready()` — no `ROOT_URLCONF`.
  No manual volume steps at deploy time.
- Update `weblate-docker` Dockerfile: replace `"/app/boost-weblate[${WEBLATE_EXTRAS}]"` local-path install
  with upstream `weblate[${WEBLATE_EXTRAS}]` from PyPI plus a `uv pip install` of
  `"git+https://…/cppa-weblate-plugin@<tag>"` for the plugin, and add a
  `COPY weblate-docker/settings-override.py /app/data/settings-override.py` step.
  Commit `weblate-docker/settings-override.py` (containing only `WEBLATE_FORMATS +=`).
  Add `# renovate: datasource=github-tags depName=cppalliance/cppa-weblate-plugin` above the plugin install
  line so Renovate can track tag bumps automatically.
  The existing CD workflow (SSH → `git pull` → `docker compose up --build`) remains unchanged.
- **Retire `boost-weblate` fork**: once the Dockerfile swap is verified in production, archive or delete
  the `boost-weblate` repo. The `weblate-docker` submodule reference to it is also removed at this point.
- **Tag and release process**: create the initial tag (`YYYY.M.N-cppalliance.1`) on the `main` branch of
  `cppa-weblate-plugin` after Phase 3 passes CI. Bump the tag in the Dockerfile, commit, push — the existing
  CD workflow picks it up on next `workflow_dispatch` run.
- Update `docs/deployment-runbook.md` with the Phase 3 rollback procedure: to roll back, pin the Dockerfile
  back to the previous tag, commit, and trigger the CD workflow.

---

## Timeline

```
Day   1    3    5    7    9   11   13   15   17   19   21
      |----|----|----|----|----|----|----|----|----|-----|
P0    [Docs + sk]                         [runbook update]
P1         [===QuickBook + tests====]
P2                   [=boost_endpoint + tests=]
P3                                  [=CI / CD / coverage]
```

> P0 runbook is revisited at the end of P3 to add the rollback procedure for the Dockerfile tag swap.

**Total: 3 weeks.**

---

## Cleanup Tracker Cross-Reference (weblate findings)

| Finding | Description | Resolution in this plan |
|---------|-------------|------------------------|
| WL1 | Bus factor 1 — sole knowledge holder | Phase 0: architecture section in README.md + deployment runbook |
| WL2 | Silent translation corruption — `translate_batch_json()` returns untranslated source on retry exhaustion | Fork-only (OpenRouter auto-translate code); **eliminated when fork is retired** |
| WL3 | Global `os.environ["PATH"]` mutation in AsciiDoc handler — concurrent request race | Fork-only (upstream Weblate AsciiDoc code); **eliminated when fork is retired** |
| WL4 | Merge paralysis — `component.py` injection + zero tests + no CI | Resolved by retiring the fork entirely; plugin runs on top of upstream Weblate |
| WL5 | Zero tests for custom code | Phases 1–2: tests in package; ≥ 90 % gate |
| WL6 | CI runs no test suite | Phase 3: `pytest` + integration test in CI |
| WL7 | No deployment runbook | Phase 0: `docs/deployment-runbook.md` |
| WL8 | No OpenAPI docs for `/boost-endpoint/` | Phase 0: `docs/boost-endpoint-api.md` |
| WL9 | Undeclared runtime deps | Phase 0: `pyproject.toml` |
| WL10 | Unbounded message history in OpenRouter translator | Fork-only (OpenRouter auto-translate code); **eliminated when fork is retired** |
| WL11 | Synchronous 300s sleep in `add_language_to_component` blocks request thread | Moves into plugin (`services.py`); Phase 2: refactor to Celery task or background thread |
| WL12 | Disabled coverage enforcement | Phase 3: `--cov-fail-under=90` in CI |

