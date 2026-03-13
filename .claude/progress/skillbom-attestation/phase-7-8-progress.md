---
schema_version: 2
doc_type: progress
type: progress
prd: skillbom-attestation
feature_slug: skillbom-attestation
phase: 7-8
status: in_progress
created: 2026-03-10
updated: '2026-03-13'
prd_ref: docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-7-8-api-cli.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-7.1
  name: 'Implement GET /api/v1/bom/snapshot endpoint: current BOM snapshot with owner-scope
    filtering'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.2
  name: 'Implement POST /api/v1/bom/generate endpoint: trigger on-demand BOM generation,
    store snapshot, return 201'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.3
  name: 'Implement GET /api/v1/bom/history endpoint: paginated artifact history with
    event_type/time_range/actor_id filters'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.4
  name: 'Implement GET /api/v1/attestations endpoint: owner-scoped paginated attestation
    list'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.5
  name: 'Implement POST /api/v1/attestations endpoint: create manual attestation record
    with artifact validation'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.6
  name: 'Implement GET /api/v1/attestations/{id} endpoint: attestation detail with
    auth verification'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.7
  name: 'Implement POST /api/v1/bom/verify endpoint: verify BOM signature with optional
    multipart signature file upload'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-7.8
  name: Implement GET /integrations/idp/bom-card/{project_id} endpoint in idp_integration.py
    with enterprise PAT auth, Backstage-compatible payload, < 500ms load time
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 3 pts
- id: TASK-8.1
  name: Implement skillmeat bom generate CLI command writing .skillmeat/context.lock
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-8.2
  name: Implement skillmeat bom verify, skillmeat bom restore, and skillmeat bom install-hook
    CLI commands
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-8.1
  estimate: 3 pts
- id: TASK-8.3
  name: Implement skillmeat history <artifact-name> and skillmeat history --all CLI
    commands with table/JSON output
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 3 pts
- id: TASK-8.4
  name: Implement auth middleware for all BOM endpoints (@require_auth with artifact:read/write/admin:*
    scopes) and cursor-based pagination for list endpoints
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-7.1
  - TASK-7.2
  - TASK-7.3
  - TASK-7.4
  - TASK-7.5
  - TASK-7.6
  - TASK-7.7
  - TASK-7.8
  estimate: 4 pts
- id: TASK-8.5
  name: Implement skillmeat attest create, skillmeat attest list, and skillmeat attest
    show CLI commands with signing and formatting
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 5 pts
- id: TASK-8.6
  name: Update OpenAPI spec, write integration tests for all 8 endpoints (auth, filtering,
    pagination, errors), write CLI integration tests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-8.4
  - TASK-8.5
  estimate: 5 pts
parallelization:
  batch_1:
  - TASK-7.1
  - TASK-7.2
  - TASK-7.3
  - TASK-7.4
  batch_2:
  - TASK-7.5
  - TASK-7.6
  - TASK-7.7
  - TASK-7.8
  batch_3:
  - TASK-8.1
  - TASK-8.2
  - TASK-8.3
  batch_4:
  - TASK-8.4
  - TASK-8.5
  - TASK-8.6
total_tasks: 14
completed_tasks: 0
in_progress_tasks: 4
blocked_tasks: 0
progress: 0
---

# Phase 7-8 Progress: API & CLI — HTTP & Command-Line Surfaces

**Objective**: Expose BOM, history, and attestation data via 8 REST API endpoints (gateway for web/Backstage) and implement bom/history/attest CLI command groups.

## Entry Criteria

- Phases 1-6 complete: models, generators, history, RBAC, git integration, and crypto signing all stable and tested
- Repositories and services available and tested
- Authentication/authorization middleware (`require_auth`, `verify_enterprise_pat`) available
- Pydantic schemas in `skillmeat/api/schemas/bom.py` validated

## Exit Criteria

- All 8 API endpoints implemented in `skillmeat/api/routers/bom.py` with correct HTTP methods, status codes, and request/response shapes
- `@require_auth(scopes=[artifact:read])` on read endpoints; `[artifact:write]` on writes; enterprise PAT on Backstage card endpoint
- Owner-scope filtering enforced in service layer (no cross-tenant/cross-user data leakage)
- Cursor-based pagination implemented for `/bom/history` and `/attestations` list endpoints
- `skillmeat/api/openapi.json` updated; Swagger UI at `/docs` shows all 8 endpoints with correct schemas
- All 4 `bom` subcommands functional: `generate`, `verify`, `restore`, `install-hook`
- `skillmeat history <artifact-name>` and `skillmeat history --all` return formatted timelines
- All 3 `attest` subcommands functional: `create`, `list`, `show` (with optional signing)
- CLI commands auto-detect local vs enterprise edition; connect to correct DB or API
- Output formatting: `--format table` (Rich, no Unicode box drawing) and `--format json` supported across all commands
- Integration tests: all 8 endpoints tested with user/team/enterprise auth contexts; 401/403/404/422 error cases covered
- CLI integration tests: all commands tested with mock DB and API
- API response times: history query (100 events) < 200ms p95; attestation list < 100ms p95
- CLI test coverage >= 80%

## Phase Plan Reference

`docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-7-8-api-cli.md`
