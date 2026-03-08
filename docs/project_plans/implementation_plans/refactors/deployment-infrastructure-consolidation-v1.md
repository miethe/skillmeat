---
schema_version: 2
doc_type: implementation_plan
title: 'Implementation Plan: Deployment Infrastructure Consolidation'
status: in-progress
created: 2026-03-08
updated: '2026-03-08'
feature_slug: deployment-infrastructure-consolidation
feature_version: v1
prd_ref: docs/project_plans/PRDs/refactors/deployment-infrastructure-consolidation-v1.md
plan_ref: null
scope: Consolidate deployment infra into unified Docker + Makefile workflow
effort_estimate: 31 pts
priority: high
risk_level: medium
category: product-planning
tags:
- implementation
- deployment
- docker
- infrastructure
- devops
- consolidation
related_documents:
- docs/project_plans/PRDs/refactors/deployment-infrastructure-consolidation-v1.md
- docs/ops/operations-guide.md
- docs/ops/enterprise-readiness-checklist.md
- .github/workflows/publish-images.yml
- docs/deployment/README.md
owner: null
contributors: []
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- Dockerfile
- skillmeat/web/Dockerfile
- .dockerignore
- docker-entrypoint.sh
- docker-compose.yml
- docker-compose.override.yml
- docker-compose.monitoring.yml
- .env.local.example
- .env.local-auth.example
- .env.enterprise.example
- Makefile
- .github/workflows/publish-images.yml
- deploy/staging/deploy.sh
- deploy/production/deploy.sh
- docs/deployment/README.md
- docs/deployment/local.md
- docs/deployment/enterprise.md
- docs/deployment/development.md
- docs/deployment/configuration.md
- docs/ops/operations-guide.md
---

# Implementation Plan: Deployment Infrastructure Consolidation

**Plan ID**: `IMPL-2026-03-08-DEPLOYMENT-CONSOLIDATION`
**Date**: 2026-03-08
**Author**: Implementation Planner
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/refactors/deployment-infrastructure-consolidation-v1.md`
- **Operations Guide**: `docs/ops/operations-guide.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 31 story points
**Target Timeline**: 6 weeks

## Executive Summary

SkillMeat's deployment infrastructure is fragmented across 5 Docker Compose files, 4 env template locations, and no production Dockerfiles. This plan consolidates everything into a single compose file with edition profiles, production-grade multi-stage Dockerfiles, a developer Makefile, automated GHCR publishing, and unified deployment documentation—reducing time-to-deploy from 30+ minutes to under 5 minutes.

**Key outcomes:**
- Single `docker-compose.yml` with `local`, `local-auth`, and `enterprise` profiles
- Multi-stage Dockerfiles for API (< 500 MB) and Web (< 300 MB)
- `Makefile` as the canonical developer entry point
- Automatic GHCR image publishing on releases
- Single deployment documentation entry point

## Implementation Strategy

### Architecture Sequence

This project does NOT follow the standard 8-layer architecture (Database → Repository → Service → API → UI → Testing → Docs → Deploy). Instead, it follows an infrastructure progression:

1. **Phase 1: Container Foundation** - Dockerfiles and entrypoint script
2. **Phase 2: Compose Consolidation** - Unified docker-compose.yml with profiles
3. **Phase 3: Developer Experience** - Makefile for local development
4. **Phase 4: Distribution** - Container publishing and PyPI readiness
5. **Phase 5: Documentation** - Deployment guides and configuration reference
6. **Phase 6: Cleanup** - Remove deprecated files and update references

### Parallel Work Opportunities

- **Phase 1 tasks** (DEPLOY-1.1, 1.2, 1.3): Dockerfiles and `.dockerignore` can run in parallel
- **Phase 2 tasks** (DEPLOY-2.2, 2.3, 2.4): Dev override, monitoring rename, and env templates can run in parallel after unified compose
- **Phase 4 tasks** (DEPLOY-4.1, 4.2): GHCR workflow and PyPI readiness can run in parallel
- **Phase 5 tasks** (DEPLOY-5.1, 5.3): README and configuration reference can run in parallel

### Critical Path

Phase 1 (foundation) → Phase 2 (compose) → Phase 3 (Makefile) → Phase 6 (cleanup)

Phase 4 (distribution) and Phase 5 (documentation) can run in parallel with Phase 3.

---

## Phase Breakdown

### Phase 1: Container Foundation (8 pts)

**Duration**: 2–3 days
**Dependencies**: None
**Assigned Subagent(s)**: devops-architect, platform-engineer

Core container infrastructure that everything else depends on.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-1.1 | API Dockerfile | Multi-stage production Dockerfile for FastAPI. Builder stage installs deps from `pyproject.toml`, production stage copies wheels and source code only. Python 3.12-slim base, non-root user `app`, HEALTHCHECK directive. Must handle both SQLite (local) and Postgres (enterprise) via env vars. | Non-root user enforced; healthcheck passes; image builds; no pip/setuptools in final layer | 3 pts | devops-architect | None |
| DEPLOY-1.2 | Web Dockerfile | Multi-stage Next.js Dockerfile. Deps stage installs from `package.json`, build stage runs `next build` with standalone output, runner stage uses Node 20-slim, non-root user `nextjs`. | Non-root user enforced; standalone output used; image builds; serves UI | 2 pts | devops-architect | None |
| DEPLOY-1.3 | .dockerignore | Exclude `.git`, `node_modules`, `__pycache__`, `.env*`, `.claude/`, `tests/`, `docs/`, `demo/`, `deploy/`, `*.pyc`, `.mypy_cache`, `.pytest_cache`, `.next` | File exists at repo root; `docker build --progress=plain` shows excluded paths not copied | 0.5 pts | devops-architect | None |
| DEPLOY-1.4 | docker-entrypoint.sh | API entrypoint script: detect DB type from `DATABASE_URL`, run `alembic upgrade head` if Postgres, create SQLite dir if local, exec uvicorn with reload flag if `SKILLMEAT_RELOAD=true`. Handle SIGTERM gracefully via trap. | Script runs migrations before uvicorn; migration failure causes non-zero exit; uvicorn starts after migrations | 1.5 pts | devops-architect | DEPLOY-1.1 |
| DEPLOY-1.5 | Verify builds | Build both images locally (`docker build -t skillmeat-api . -f Dockerfile && docker build -t skillmeat-web skillmeat/web/ -f Dockerfile`), verify they start with healthchecks, test basic functionality (API /health, Web serving assets), measure sizes (API < 500MB, Web < 300MB) | Both images build successfully; API responds at /health; Web serves index.html; sizes within targets | 1 pt | platform-engineer | DEPLOY-1.1, DEPLOY-1.2 |

**Phase 1 Quality Gates:**
- [ ] Both Dockerfiles build successfully
- [ ] API and Web images run as non-root users (verified via `docker inspect`)
- [ ] API healthcheck responds to `/health` within 5 seconds
- [ ] Web healthcheck responds to requests within 5 seconds
- [ ] API image size < 500 MB
- [ ] Web image size < 300 MB
- [ ] `.dockerignore` prevents `node_modules`, `.git`, `.env*`, `.claude/` from build context
- [ ] `docker-entrypoint.sh` runs migrations (if Postgres) before uvicorn startup

**Parallelization**: DEPLOY-1.1, 1.2, 1.3 can run in parallel (no dependencies). DEPLOY-1.4 depends on 1.1 only. DEPLOY-1.5 depends on 1.1 and 1.2.

---

### Phase 2: Compose Consolidation (7 pts)

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: devops-architect, platform-engineer

Unified docker-compose.yml with profiles replacing 3+ separate compose files.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-2.1 | Unified docker-compose.yml | Create `docker-compose.yml` at repo root with three profiles: `local` (API+Web, SQLite), `local-auth` (API+Web, SQLite, Clerk vars), `enterprise` (API+Web+Postgres, enterprise vars). All services include healthchecks and `restart: unless-stopped` in enterprise profile. Postgres service only in enterprise profile. Named volume `skillmeat-data` mounted at `/home/app/.skillmeat` for local-edition persistence. Both API and Web services build from local Dockerfiles. | `docker compose config --profile local` validates; `docker compose --profile local up` starts and passes healthchecks; `docker compose --profile enterprise up` includes postgres; all 3 profiles start without errors | 3 pts | devops-architect | Phase 1 |
| DEPLOY-2.2 | docker-compose.override.yml | Create dev overrides: volume bind-mounts for hot reload (repo root `skillmeat/` into API container `/app/skillmeat`, `skillmeat/web` into Web container `/app/src`), expose debug ports (5678 for Python), set `SKILLMEAT_ENV=development`, `SKILLMEAT_RELOAD=true`. This file auto-applies during `docker compose up` for dev workflows without needing to be explicitly referenced. | File exists; `docker compose up` applies overrides automatically; code changes in mounted volumes reflect without container restart; debug ports exposed | 2 pts | devops-architect | DEPLOY-2.1 |
| DEPLOY-2.3 | Rename observability compose | Rename `docker-compose.monitoring.yml` → `docker-compose.monitoring.yml`. Update any references in docs or scripts. Keep existing content (Prometheus, Grafana, Loki, Promtail configs) unchanged. | File renamed; all references updated; `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up` starts monitoring services | 0.5 pts | devops-architect | None |
| DEPLOY-2.4 | Consolidate env templates | Create 3 env templates at repo root: `.env.local.example` (minimal: `SKILLMEAT_EDITION=local`, ports, `SKILLMEAT_COLLECTION_DIR`), `.env.local-auth.example` (adds `SKILLMEAT_AUTH_PROVIDER=clerk`, `CLERK_*` vars), `.env.enterprise.example` (adds `SKILLMEAT_EDITION=enterprise`, `DATABASE_URL`, auth vars, worker counts, CORS origins). Each should be self-documenting with inline comments. Remove old root `.env.example` (replaced by `.env.local.example`). | All 3 templates exist at repo root; each is self-documenting; `cp .env.local.example .env && docker compose --profile local up` works without modification | 1.5 pts | devops-architect | DEPLOY-2.1 |

**Phase 2 Quality Gates:**
- [ ] `docker compose --profile local up -d` starts API + Web with SQLite
- [ ] `docker compose --profile enterprise up -d` starts API + Web + Postgres
- [ ] All healthchecks pass within 30 seconds
- [ ] Dev override (`docker-compose.override.yml`) provides hot-reload (code changes reflect without restart)
- [ ] Named volume persists data across `docker compose down && docker compose up`
- [ ] Monitoring addon works: `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up`
- [ ] All env templates are complete and self-documenting
- [ ] No references to removed files remain in codebase

**Parallelization**: DEPLOY-2.1 must come first. Then 2.2, 2.3, 2.4 can run in parallel.

---

### Phase 3: Developer Experience (4 pts)

**Duration**: 1 day
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: devops-architect, platform-engineer

Makefile and CLI improvements for local development.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-3.1 | Makefile | Create root `Makefile` with targets: `help` (list all targets), `dev` (native API + Web), `dev-docker` (containerized with hot reload), `dev-enterprise` (enterprise with Postgres), `build` (production images), `build-api` (API only), `build-web` (Web only), `up` (alias for `docker compose up`), `up-auth` (with local-auth profile), `up-enterprise` (enterprise profile), `down`, `test` (all tests), `test-python`, `test-web`, `test-integration`, `lint`, `format`, `typecheck`, `db-migrate`, `db-reset`, `db-seed`, `clean` (remove containers/volumes), `doctor` (diagnose environment), `logs`, `logs-api`, `logs-web`, `shell-api`, `shell-db` (interactive shells). Include `.PHONY` declarations and helpful `help` target with one-line descriptions. | Makefile exists at repo root; `make help` shows all targets with descriptions; all targets are syntactically valid; `make dev` starts native environment | 3 pts | devops-architect | Phase 2 |
| DEPLOY-3.2 | Makefile verification | Test all Makefile targets work correctly on macOS/Linux. Verify `make help` output is clear and accurate. Verify `make dev` matches current `skillmeat web dev` behavior. Test `make build` produces correct images. Test `make test` runs both Python and web tests. | `make help` output complete and clear; `make dev` starts native dev within 60s; `make build` produces images; `make test` succeeds; `make down` cleans up | 1 pt | platform-engineer | DEPLOY-3.1 |

**Phase 3 Quality Gates:**
- [ ] `make help` displays all targets with descriptions
- [ ] `make dev` starts native development environment (API + Web on host)
- [ ] `make dev-docker` starts containerized dev with hot reload
- [ ] `make build` produces production images
- [ ] `make test` runs all tests successfully
- [ ] All targets work on both macOS and Linux (if testing in CI)
- [ ] `make clean` removes containers and named volumes

**Parallelization**: Sequential (DEPLOY-3.2 depends on DEPLOY-3.1).

---

### Phase 4: Distribution (5 pts)

**Duration**: 1–2 days
**Dependencies**: Phase 1 complete (for GHCR workflow)
**Assigned Subagent(s)**: devops-architect, python-backend-engineer

Container image publishing and package distribution.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-4.1 | GHCR publish workflow | GitHub Actions workflow `.github/workflows/publish-images.yml` triggered on release tags (e.g., `v0.9.0`). Build multi-platform images (linux/amd64, linux/arm64) using Docker Buildx and GitHub cache. Push to `ghcr.io/miethe/skillmeat-api` and `ghcr.io/miethe/skillmeat-web` with tag matching release version. Use `docker/build-push-action@v5` and `docker/setup-buildx-action@v2`. | Workflow file exists in `.github/workflows/`; workflow passes in dry-run or on test tag; images appear in GHCR with correct tags; multi-platform builds succeed | 3 pts | devops-architect | Phase 1 |
| DEPLOY-4.2 | PyPI readiness check | Audit `pyproject.toml` for complete metadata: description (long_description), classifiers (development status, license, Python versions), license field, project-urls (Repository, Documentation, Issues), readme path and content type. Verify existing `release-package.yml` workflow is functional. Document any fixes needed. Do NOT publish; document the publish procedure for later. | `pyproject.toml` has complete metadata; `build` and `twine check` pass without warnings; publish procedure documented in `docs/deployment/pypi-publishing.md` | 1 pt | python-backend-engineer | None |
| DEPLOY-4.3 | Homebrew formula (stretch goal) | Create `Formula/skillmeat.rb` in the repo (or publish to a separate homebrew-tap repo if setup is trivial). Pip-based formula installing the CLI from PyPI. This is a stretch goal — create the formula but don't set up tap hosting unless it's a one-time setup. | Formula file exists; `brew tap miethe/skillmeat` + `brew install skillmeat` works locally on macOS (manual test); formula syntax valid | 1 pt | devops-architect | DEPLOY-4.2 |

**Phase 4 Quality Gates:**
- [ ] GHCR workflow passes in dry-run or on a test tag
- [ ] `pyproject.toml` has complete metadata
- [ ] Build and twine checks pass without warnings
- [ ] PyPI publish procedure documented
- [ ] (Stretch) Homebrew formula syntax valid and installs CLI locally

**Parallelization**: DEPLOY-4.1 and DEPLOY-4.2 can run in parallel. DEPLOY-4.3 depends on DEPLOY-4.2.

---

### Phase 5: Documentation (4 pts)

**Duration**: 1 day
**Dependencies**: Phase 2 complete; Phase 3 complete for Makefile references
**Assigned Subagent(s)**: documentation-writer

Consolidated deployment documentation.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-5.1 | Deployment README | Create `docs/deployment/README.md` as the single entry point for all deployment info. Quick-start for each pattern (local, local-auth, enterprise), links to detailed guides, decision tree: "which pattern should I use?", overview of the unified compose profiles and env templates. | File exists at `docs/deployment/README.md`; covers all three patterns; decision tree clear; links to phase-specific guides work | 1.5 pts | documentation-writer | Phase 2 |
| DEPLOY-5.2 | Pattern-specific guides | Create `docs/deployment/local.md` (Docker + native setup, SQLite), `docs/deployment/enterprise.md` (Postgres, Clerk, monitoring, team setup), `docs/deployment/development.md` (Makefile targets, hot reload, testing, debugging) | All three guides exist; each includes copy-pasteable quick-start commands; local.md covers `docker compose --profile local`; enterprise.md covers monitoring addon; development.md covers all Makefile targets | 1.5 pts | documentation-writer | DEPLOY-5.1 |
| DEPLOY-5.3 | Configuration reference | Create `docs/deployment/configuration.md` — unified env var reference table (all vars, defaults, which edition needs what, required vs optional, example values for each) | File exists; table includes all env vars from all three `.env.*example` files; each var has description, default, edition applicability, required/optional flag | 1 pt | documentation-writer | DEPLOY-2.4 |

**Phase 5 Quality Gates:**
- [ ] All deployment questions answerable from `docs/deployment/`
- [ ] Each pattern has copy-pasteable quick-start commands
- [ ] Env var reference is complete and accurate
- [ ] No external files needed to deploy (all info self-contained in docs)
- [ ] Links to guides and examples work

**Parallelization**: DEPLOY-5.1 and DEPLOY-5.3 can run in parallel. DEPLOY-5.2 depends on DEPLOY-5.1 for consistent structure.

---

### Phase 6: Cleanup (3 pts)

**Duration**: 0.5 days
**Dependencies**: Phases 2–5 complete
**Assigned Subagent(s)**: devops-architect, documentation-writer, platform-engineer

Remove deprecated files and update references.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Agent(s) | Dependencies |
|---------|------|-------------|-------------------|----------|----------|--------------|
| DEPLOY-6.1 | Remove deprecated compose files | Remove `docker-compose.demo.yml`. Remove `deploy/staging/docker-compose.staging.yml`. Remove `deploy/production/docker-compose.production.yml`. These are replaced by the unified compose with profiles. | Files removed from repo; `git log` shows removal; no references to removed files in `.gitignore` or scripts | 0.5 pts | devops-architect | Phases 2, 3 |
| DEPLOY-6.2 | Update deploy scripts | Update `deploy/staging/deploy.sh` and `deploy/production/deploy.sh` to reference the unified `docker-compose.yml` with appropriate profiles and env files. Update image references (`ghcr.io/miethe/skillmeat-api`, `ghcr.io/miethe/skillmeat-web`) to match GHCR publishing. Validate scripts still work end-to-end. | Scripts reference unified compose; image names updated; smoke tests pass against new stack; no references to old compose files | 1 pt | devops-architect | DEPLOY-6.1 |
| DEPLOY-6.3 | Remove old env templates | Remove root `.env.example` (replaced by `.env.local.example`). Keep `deploy/staging/env.staging` and `deploy/production/env.production` since they're referenced by deploy scripts, but add a comment pointing to canonical templates at root. | `.env.example` removed; staging/production env files have comment linking to root templates; no broken references | 0.5 pts | devops-architect | DEPLOY-2.4 |
| DEPLOY-6.4 | Update operations guide | Update `docs/ops/operations-guide.md` to link to new `docs/deployment/` docs. Remove any duplicated deployment instructions. Update README.md deployment section to link to new consolidated guide. | `docs/ops/operations-guide.md` links to `docs/deployment/README.md`; duplicated instructions removed; README.md deployment section updated | 0.5 pts | documentation-writer | Phase 5 |
| DEPLOY-6.5 | Final validation | Run all smoke tests against unified compose deployment. Verify `make dev` and `make dev-enterprise` work end-to-end. Verify GHCR images are used in staging/production scripts. Verify no broken references to removed files remain. | All smoke tests pass (staging + production); `make dev` starts native dev; `make dev-enterprise` starts containerized enterprise; no build/reference errors | 0.5 pts | platform-engineer | All previous phases |

**Phase 6 Quality Gates:**
- [ ] No references to removed files (`docker-compose.demo.yml`, etc.) remain in codebase
- [ ] Deploy scripts work with unified compose and GHCR images
- [ ] All smoke tests pass
- [ ] Operations guide links are correct and up-to-date
- [ ] README.md deployment section points to new docs

**Parallelization**: DEPLOY-6.1, 6.3 can run in parallel. DEPLOY-6.2 depends on DEPLOY-6.1. DEPLOY-6.4 depends on Phase 5. DEPLOY-6.5 depends on all others.

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Breaking existing deploy scripts during compose consolidation | High | Medium | Update scripts incrementally; validate each against test deployment before removing old files. Use feature branches. Run smoke tests after each change. |
| Filesystem volume permissions differ on macOS vs Linux (UID/GID mismatch) | Medium | High | Test on both macOS and Linux; document `PUID`/`PGID` env vars if needed. Use named volumes as default (not host bind-mount). Document known macOS Docker Desktop bind-mount latency. |
| Next.js standalone build output incomplete (missing static assets) | Medium | Low | Standalone mode already configured and tested via `skillmeat web build`. Validate in CI that build succeeds and all assets present. |
| Hot reload performance degradation in containerized dev | Low | Medium | Use `:delegated` or `:cached` bind-mount options. Document macOS Docker Desktop latency. Keep native `make dev` as recommended path. |
| `.dockerignore` missing sensitive paths leaks secrets into image | High | Low | Enumerate all sensitive paths explicitly (`.env*`, `.ssh/`, `~/.config/`). Add CI step that scans image for common secret patterns using tools like `trivy`. |
| Staging/production deploy scripts break during transition | High | Medium | Update scripts in same commit as unified compose. Add smoke test to CI. Deploy to staging first with both old and new scripts in parallel during transition window. |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Scope creep (e.g., Kubernetes, IaC) | Medium | High | Document non-goals clearly. Use this plan scope strictly. Track any requests as separate PRDs. |
| Resource constraints (only one DevOps engineer available) | High | Medium | Parallelize Phases 1/2 with independent agents. Delegate documentation to writers. Keep Phases 4/5 separate from critical path (Phases 1–3/6). |
| Dependency delays (e.g., GHCR permissions not available) | Low | Low | Verify GHCR access early. Test workflow syntax locally before merging. Use dry-run mode if needed. |

---

## Resource Requirements

### Team Composition

- **DevOps Architect**: 2 FTE for Phases 1–3, 1 FTE for Phase 4–6 (primary agent for all infrastructure work)
- **Platform Engineer**: Part-time for verification and validation (Phases 1–3, 6)
- **Documentation Writer**: Part-time for Phase 5 (1.5 FTE equivalent effort)
- **Python Backend Engineer**: Small part-time task in Phase 4 (PyPI audit)

### Skill Requirements

- Docker and Docker Compose proficiency (v2 profiles, multi-stage builds)
- Bash scripting (entrypoint script, Makefile)
- GitHub Actions and GHCR publishing
- FastAPI and Next.js basics (understanding app structure)
- DevOps best practices (security, image optimization, healthchecks)

---

## Success Metrics

### Delivery Metrics

- On-time delivery (±10%)
- All 6 phases completed
- Zero P0 bugs in first week of production use

### Business Metrics

- Time to first successful deploy (new user) < 5 minutes
- Docker Compose files to understand: 1 (+ 2 optional addons)
- Env template locations: 1 (repo root)
- Container images available on GHCR on every release

### Technical Metrics

- API image size < 500 MB
- Web image size < 300 MB
- Container startup to healthy < 30 seconds
- All smoke tests pass
- 100% deployment documentation coverage

---

## Communication Plan

- **Daily standups**: Brief sync on blockers and progress (async Slack updates acceptable)
- **Phase reviews**: Formal review at end of each phase before proceeding
- **Stakeholder updates**: Weekly summary of progress
- **Documentation**: All decisions and procedures documented inline in code and docs/

---

## Post-Implementation

- **Monitoring**: Track deployment times and user feedback
- **Refinement**: Document lessons learned and gotchas
- **Future work**: Consider Kubernetes manifests, Terraform, or Helm charts if demand warrants
- **Maintenance**: Update docs and workflows as dependencies change

---

## Appendices

### Files Affected Summary

**New files** (27 total):
- `Dockerfile` (API, at repo root)
- `skillmeat/web/Dockerfile` (Web)
- `.dockerignore`
- `docker-entrypoint.sh`
- `docker-compose.yml` (unified, replaces demo/staging/production split)
- `docker-compose.override.yml` (dev overrides, auto-applied)
- `docker-compose.monitoring.yml` (renamed from observability)
- `.env.local.example` (replaces generic .env.example)
- `.env.local-auth.example`
- `.env.enterprise.example`
- `Makefile` (root)
- `.github/workflows/publish-images.yml` (GHCR publishing)
- `docs/deployment/README.md` (consolidation entry point)
- `docs/deployment/local.md` (local pattern guide)
- `docs/deployment/enterprise.md` (enterprise pattern guide)
- `docs/deployment/development.md` (dev environment guide)
- `docs/deployment/configuration.md` (env var reference)
- `docs/deployment/pypi-publishing.md` (optional, for Phase 4)

**Modified files** (5 total):
- `deploy/staging/deploy.sh` (update to use unified compose)
- `deploy/production/deploy.sh` (update to use unified compose)
- `docs/ops/operations-guide.md` (link to new docs)
- `README.md` (deployment section → link to new docs)
- `pyproject.toml` (audit/fixes if needed for PyPI readiness)

**Removed files** (4 total):
- `docker-compose.demo.yml` (superseded by unified compose)
- `deploy/staging/docker-compose.staging.yml` (superseded)
- `deploy/production/docker-compose.production.yml` (superseded)
- `.env.example` (replaced by `.env.local.example`)

### Known Dependencies

- **Docker Engine 24+** and **Docker Compose v2** on all target systems
- **Python 3.12-slim** and **Node 20** base images (already required)
- **Alembic** and **Next.js standalone output** (both already working)
- **GHCR** and **GitHub Actions** (no new permissions needed; use existing GITHUB_TOKEN)

### Success Stories and Benchmarks

Target user experience post-implementation:

**New Self-Hosting User:**
1. `git clone <repo>`
2. `cp .env.local.example .env`
3. `docker compose --profile local up -d`
4. Open browser to localhost:8080

**Developer Contributing:**
1. `make dev` (start native dev environment within 60 seconds)
2. Code → save → browser auto-reloads
3. `make test` (run all tests)
4. `git push`

**Enterprise Operator:**
1. `cp .env.enterprise.example .env`
2. Fill in `DATABASE_URL`, `CLERK_*`, other auth vars
3. `docker compose --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d`
4. Full production-equivalent stack including monitoring

---

**Progress Tracking:**

See `.claude/progress/deployment-infrastructure-consolidation/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-08
