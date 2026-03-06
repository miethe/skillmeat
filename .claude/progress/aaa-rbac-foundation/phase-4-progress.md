---
type: progress
schema_version: 2
doc_type: progress
prd: "aaa-rbac-foundation"
feature_slug: "aaa-rbac-foundation"
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 4
title: "API Layer - Auth Injection & Endpoint Protection"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: ["backend-architect", "api-documenter"]

tasks:
  - id: "API-001"
    description: "Add require_auth to critical routers (artifacts, collections, projects) - Batch 1"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "4 pts"
    priority: "critical"

  - id: "API-002"
    description: "Add require_auth to supporting routers (deployments, groups, tags, versions, bundles) - Batch 2"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "API-003"
    description: "Add require_auth to marketplace & content routers - Batch 3"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-002"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "API-004"
    description: "Ensure health & utility routers remain auth-free (public endpoints)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-003"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "API-005"
    description: "Update all router function signatures to accept AuthContext and thread to services"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "API-006"
    description: "Add auth requirements to OpenAPI schema; document scopes and roles"
    status: "pending"
    assigned_to: ["api-documenter"]
    dependencies: ["API-005"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "API-007"
    description: "Create integration tests for protected endpoints with valid/invalid auth and scopes"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-005"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "API-008"
    description: "Verify zero-auth local mode works without Authorization header"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "1 pt"
    priority: "critical"

parallelization:
  batch_1: ["API-001"]
  batch_2: ["API-002", "API-005", "API-008"]
  batch_3: ["API-003", "API-006", "API-007"]
  batch_4: ["API-004"]
  critical_path: ["API-001", "API-005", "API-007"]
  estimated_total_time: "8 days"

blockers: []

success_criteria:
  - { id: "SC-1", description: "All 30+ routers have require_auth or are explicitly marked public", status: "pending" }
  - { id: "SC-2", description: "Write endpoints validate scopes (artifact:write, collection:write)", status: "pending" }
  - { id: "SC-3", description: "AuthContext threaded through all router->service calls", status: "pending" }
  - { id: "SC-4", description: "OpenAPI documentation reflects auth requirements", status: "pending" }
  - { id: "SC-5", description: "Integration tests for protected endpoints pass", status: "pending" }
  - { id: "SC-6", description: "Local zero-auth mode works transparently", status: "pending" }

files_modified:
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/api/routers/collections.py"
  - "skillmeat/api/routers/projects.py"
  - "skillmeat/api/routers/deployments.py"
  - "skillmeat/api/routers/groups.py"
  - "skillmeat/api/routers/tags.py"
  - "skillmeat/api/routers/versions.py"
  - "skillmeat/api/routers/bundles.py"
  - "skillmeat/api/routers/marketplace.py"
  - "skillmeat/api/routers/marketplace_catalog.py"
  - "skillmeat/api/openapi.json"
  - "skillmeat/api/tests/test_auth_api.py"
---

# aaa-rbac-foundation - Phase 4: API Layer - Auth Injection & Endpoint Protection

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-4-progress.md -t API-001 -s completed
```

---

## Objective

Add require_auth dependency to all 30+ API routers via a 3-batch phased rollout. Update handler signatures to receive AuthContext. Verify zero-auth local mode and update OpenAPI docs.

---

## Implementation Notes

### Phased Router Rollout Strategy
- **Batch 1** (critical): artifacts, collections, projects — highest traffic, most important to protect
- **Batch 2** (supporting): deployments, groups, tags, versions, bundles — depend on Batch 1 patterns
- **Batch 3** (marketplace): marketplace, marketplace-catalog, context-sync — lower priority
- **Exempt**: health, cache, settings — remain public

### File Contention Risk
Each batch modifies different router files. Batches MUST be sequential to avoid merge conflicts. Within each batch, files can be edited in parallel.
