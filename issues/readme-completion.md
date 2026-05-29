### Problem

The project README lacked documentation for the Docker-based development workflows (CI and CD stacks), the CI/CD pipeline structure, integration test instructions, and the environment/configuration reference. Contributors and operators had no single-page overview of how to run, test, and deploy the plugin beyond basic `uv` local development.

### Acceptance Criteria

- [ ] Quick Start section covers local development, Docker CI stack, and Docker CD/staging workflows
- [ ] Architecture diagram includes `settings_override.py`, `INSTALLED_APPS`, and Celery worker nodes with correct edges
- [ ] CI/CD Pipelines section documents all seven CI sub-workflows (lint, test, package, dependencies, combination-smoke, combination-auth, combination-functional) and the CD workflow
- [ ] Integration test instructions explain how to run smoke, auth, and functional test scripts locally, including the optional `GH_TEST_REPO_TOKEN` secret
- [ ] Environment & Configuration Reference table links to `.env.example`, `docs/deployment-runbook.md`, `docs/boost-endpoint-api.md`, `docs/plugin-http-routes.md`, `docker/README.md`, and `.github/README.md`
- [ ] Boost Endpoint Routes section documents `WEBLATE_URL_PREFIX` path-prefixing behaviour
- [ ] Celery section is reframed as "Celery Requirement for add-or-update" with worker verification command and `CELERY_SINGLE_PROCESS` guidance
- [ ] Contributing section includes concrete `prek install` / `prek run` commands and a local coverage command block

### Implementation Notes

- The Quick Start was restructured into three subsections (local dev, Docker CI, Docker CD/staging) instead of one long block, improving scannability for different audiences.
- The Mermaid architecture diagram was updated to reflect the actual runtime wiring (`settings_override.py` → `WEBLATE_FORMATS` / `INSTALLED_APPS`, `EP` → `CEL` Celery loop); test nodes were removed from the diagram since they are not part of the runtime architecture.
- Internal link anchors were renamed (e.g. `Routes` → `Boost Endpoint Routes`, `Celery task` → `Celery Requirement for add-or-update`) and all in-page references updated to match.
- Verbose code examples that duplicated CI behaviour (e.g. full `pytest` coverage flags) were moved to the Contributing section to keep Quick Start minimal.

### References

- `README.md`
