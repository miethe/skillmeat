---
type: progress
schema_version: 2
doc_type: progress
prd: aaa-rbac-foundation
feature_slug: aaa-rbac-foundation
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 4
title: API Layer - Auth Injection & Endpoint Protection
status: pending
started: '2026-03-07'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 18
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- backend-architect
- api-documenter
- data-layer-expert
tasks:
- id: SEC-001
  description: Add aud (audience) claim validation to Clerk JWT in clerk_provider.py
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1 pt
  priority: critical
  source: addendum
- id: SEC-002
  description: Wire iss (issuer) claim validation using existing config in clerk_provider.py
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1 pt
  priority: critical
  source: addendum
- id: WIRE-001
  description: Instantiate auth provider in server.py lifespan based on config
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SEC-001
  - SEC-002
  estimated_effort: 2 pts
  priority: critical
  source: addendum
- id: WIRE-003
  description: Set request.state.auth_context in require_auth dependency
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 0.5 pt
  priority: critical
  source: addendum
- id: API-001
  description: Add require_auth to critical routers (artifacts, collections, projects)
    - Batch 1
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - WIRE-001
  estimated_effort: 4 pts
  priority: critical
- id: ENT-001
  description: Secure-by-default route protection — protected_router vs public_router
    pattern
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - WIRE-001
  estimated_effort: 3 pts
  priority: high
  source: addendum
- id: API-002
  description: Add require_auth to supporting routers (deployments, groups, tags,
    versions, bundles) - Batch 2
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-001
  estimated_effort: 3 pts
  priority: high
- id: API-005
  description: Update all router function signatures to accept AuthContext and thread
    to services
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-001
  estimated_effort: 3 pts
  priority: high
- id: API-008
  description: Verify zero-auth local mode works without Authorization header
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-001
  estimated_effort: 1 pt
  priority: critical
- id: API-003
  description: Add require_auth to marketplace & content routers - Batch 3
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-002
  estimated_effort: 2 pts
  priority: high
- id: WIRE-002
  description: Register TenantContext dependency on enterprise routers via set_tenant_context_dep
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - WIRE-001
  estimated_effort: 1 pt
  priority: high
  source: addendum
- id: API-004
  description: Ensure health & utility routers remain auth-free (public endpoints)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-003
  estimated_effort: 1 pt
  priority: medium
- id: ENT-002
  description: Visibility-based filtering in repositories (_apply_visibility_filter)
  status: pending
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies:
  - WIRE-001
  estimated_effort: 5 pts
  priority: high
  source: addendum
- id: DES-001
  description: Document and add str_owner_id helper for owner_id type mismatch (String
    vs UUID)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2 pts
  priority: medium
  source: addendum
- id: DES-002
  description: Document system_admin assignment path for Clerk (decision + implementation)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2 pts
  priority: medium
  source: addendum
- id: API-006
  description: Add auth requirements to OpenAPI schema; document scopes and roles
  status: pending
  assigned_to:
  - api-documenter
  dependencies:
  - API-005
  estimated_effort: 1 pt
  priority: medium
- id: API-007
  description: Create integration tests for protected endpoints with valid/invalid
    auth and scopes
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-005
  estimated_effort: 2 pts
  priority: high
- id: ENT-003
  description: Integration test — end-to-end auth flow (provider -> require_auth ->
    service layer)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - WIRE-001
  - API-005
  estimated_effort: 3 pts
  priority: high
  source: addendum
parallelization:
  batch_0:
  - SEC-001
  - SEC-002
  - WIRE-001
  - WIRE-003
  batch_1:
  - API-001
  - ENT-001
  batch_2:
  - API-002
  - API-005
  - API-008
  batch_3:
  - API-003
  - WIRE-002
  batch_4:
  - API-004
  - ENT-002
  - DES-001
  - DES-002
  batch_5:
  - API-006
  - API-007
  - ENT-003
  critical_path:
  - SEC-001
  - SEC-002
  - WIRE-001
  - API-001
  - API-005
  - API-007
  estimated_total_time: 10-12 days
blockers: []
success_criteria:
- id: SC-1
  description: All 30+ routers have require_auth or are explicitly marked public
  status: pending
- id: SC-2
  description: Write endpoints validate scopes (artifact:write, collection:write)
  status: pending
- id: SC-3
  description: AuthContext threaded through all router->service calls
  status: pending
- id: SC-4
  description: OpenAPI documentation reflects auth requirements
  status: pending
- id: SC-5
  description: Integration tests for protected endpoints pass
  status: pending
- id: SC-6
  description: Local zero-auth mode works transparently
  status: pending
- id: SC-7
  description: JWT aud/iss validation prevents cross-app token reuse (P0 security)
  status: pending
- id: SC-8
  description: Auth provider instantiated at startup and accessible via DI
  status: pending
- id: SC-9
  description: request.state.auth_context populated for observability
  status: pending
- id: SC-10
  description: Visibility-based filtering enforces private/team/public access
  status: pending
files_modified:
- skillmeat/api/auth/clerk_provider.py
- skillmeat/api/config.py
- skillmeat/api/server.py
- skillmeat/api/dependencies.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/routers/collections.py
- skillmeat/api/routers/projects.py
- skillmeat/api/routers/deployments.py
- skillmeat/api/routers/groups.py
- skillmeat/api/routers/tags.py
- skillmeat/api/routers/versions.py
- skillmeat/api/routers/bundles.py
- skillmeat/api/routers/marketplace.py
- skillmeat/api/routers/marketplace_catalog.py
- skillmeat/api/openapi.json
- skillmeat/api/tests/test_auth_api.py
- skillmeat/api/tests/test_auth_providers.py
progress: 22
updated: '2026-03-07'
---

# aaa-rbac-foundation - Phase 4: API Layer - Auth Injection & Endpoint Protection

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-4-progress.md -t API-001 -s completed
```

---

## Objective

Add require_auth dependency to all 30+ API routers via a phased rollout. Execute P0 security fixes (aud/iss validation) and wiring gaps (provider instantiation, request.state) before router protection. Update handler signatures to receive AuthContext. Verify zero-auth local mode and update OpenAPI docs.

---

## Addendum Integration

This phase incorporates tasks from the architecture review addendum:
- **P0 Security**: SEC-001, SEC-002 (JWT claim validation hardening)
- **P0 Wiring**: WIRE-001, WIRE-002, WIRE-003 (provider instantiation, TenantContext, request.state)
- **P1 Enterprise**: ENT-001 (secure-by-default), ENT-002 (visibility filtering), ENT-003 (e2e auth test)
- **P2 Design**: DES-001 (owner_id type helper), DES-002 (system_admin path docs)

## Implementation Notes

### Execution Order (Revised with Addendum)
- **Batch 0** (pre-wiring): SEC-001+SEC-002 (clerk_provider.py), WIRE-001 (server.py), WIRE-003 (dependencies.py)
- **Batch 1** (critical): API-001 (artifacts/collections/projects) + ENT-001 (secure-by-default pattern)
- **Batch 2** (supporting): API-002 (remaining routers) + API-005 (signatures) + API-008 (zero-auth)
- **Batch 3** (marketplace): API-003 + WIRE-002 (TenantContext registration)
- **Batch 4** (filtering/design): API-004 (public routes) + ENT-002 (visibility) + DES-001/002
- **Batch 5** (validation): API-006 (OpenAPI) + API-007/ENT-003 (integration tests)

### File Contention Risk
Each batch modifies different router files. Batches MUST be sequential to avoid merge conflicts. Within each batch, files can be edited in parallel.
