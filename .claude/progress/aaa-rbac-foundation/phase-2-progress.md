---
type: progress
schema_version: 2
doc_type: progress
prd: aaa-rbac-foundation
feature_slug: aaa-rbac-foundation
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 2
title: Repository & Service Layer - Auth Context Definition & Propagation
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 8
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- backend-architect
- data-layer-expert
tasks:
- id: SVR-001
  description: Create AuthContext frozen dataclass (user_id, tenant_id, roles, scopes)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1 pt
  priority: critical
- id: SVR-002
  description: Define RBAC Role enum and Scope enum constants
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1 pt
  priority: high
- id: SVR-003
  description: Create TenantContext ContextVar with set_tenant_context() helper
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 1 pt
  priority: high
- id: SVR-004
  description: Update IArtifactRepository, ICollectionRepository interfaces with optional
    auth_context param
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  dependencies:
  - SVR-001
  estimated_effort: 2 pts
  priority: high
- id: SVR-005
  description: Update local repository implementations with owner_id validation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVR-004
  estimated_effort: 2 pts
  priority: high
- id: SVR-006
  description: Update enterprise repository implementations with tenant_id + owner_id
    enforcement
  status: completed
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies:
  - SVR-004
  estimated_effort: 2 pts
  priority: high
- id: SVR-007
  description: Update artifact/collection services to accept and thread AuthContext
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVR-001
  - SVR-004
  estimated_effort: 2 pts
  priority: high
- id: SVR-008
  description: Add owner_id, owner_type, visibility to request/response DTOs
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVR-001
  estimated_effort: 2 pts
  priority: medium
parallelization:
  batch_1:
  - SVR-001
  - SVR-002
  - SVR-003
  batch_2:
  - SVR-004
  - SVR-008
  batch_3:
  - SVR-005
  - SVR-006
  - SVR-007
  critical_path:
  - SVR-001
  - SVR-004
  - SVR-005
  estimated_total_time: 5 days
blockers: []
success_criteria:
- id: SC-1
  description: AuthContext dataclass compiles and validates
  status: pending
- id: SC-2
  description: RBAC enums define all required roles and scopes
  status: pending
- id: SC-3
  description: TenantContext ContextVar threads through enterprise repos
  status: pending
- id: SC-4
  description: Repository interfaces updated with auth_context param
  status: pending
- id: SC-5
  description: Service layer accepts and propagates auth_context
  status: pending
- id: SC-6
  description: DTOs include new fields with validation
  status: pending
- id: SC-7
  description: Zero-auth local mode still works without auth_context
  status: pending
files_modified:
- skillmeat/api/schemas/auth.py
- skillmeat/cache/enterprise_repositories.py
- skillmeat/core/interfaces/repositories.py
- skillmeat/core/repositories/local_*.py
- skillmeat/core/services/artifact_service.py
- skillmeat/core/services/collection_service.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/api/schemas/collections.py
progress: 100
updated: '2026-03-06'
---

# aaa-rbac-foundation - Phase 2: Repository & Service Layer - Auth Context Definition & Propagation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-2-progress.md -t SVR-001 -s completed
```

---

## Objective

Define the AuthContext dataclass, RBAC enums, and TenantContext ContextVar. Update repository interfaces and implementations to accept auth context. Wire service layer to propagate auth context to repositories. Maintain backward compatibility with zero-auth local mode.

---

## Orchestration Quick Reference

```bash
# Batch 1: Foundation types (parallel - no file overlap)
Task("python-backend-engineer", "Create AuthContext dataclass and RBAC enums.
  New file: skillmeat/api/schemas/auth.py
  AuthContext: frozen dataclass with user_id (UUID), tenant_id (UUID), roles (list[str]), scopes (list[str])
  Role enum: system_admin, team_admin, team_member, viewer
  Scope enum: artifact:read, artifact:write, collection:read, collection:write, deployment:read, deployment:write, admin:*
  Include LOCAL_ADMIN_CONTEXT constant (system_admin with all scopes)")

Task("data-layer-expert", "Create TenantContext ContextVar in enterprise_repositories.py.
  File: skillmeat/cache/enterprise_repositories.py
  Add: TenantContext = contextvars.ContextVar('tenant_context', default=DEFAULT_TENANT_ID)
  Add: set_tenant_context(tenant_id: uuid.UUID) helper function
  Pattern: Follow .claude/context/key-context/tenant-scoping-strategy.md section 4")

# Batch 2: Interface + DTO updates
Task("python-backend-engineer", "Update repository interfaces and DTOs.
  Files: skillmeat/core/interfaces/repositories.py, skillmeat/api/schemas/artifacts.py, skillmeat/api/schemas/collections.py
  Interfaces: Add optional auth_context: AuthContext | None = None to all CRUD methods
  DTOs: Add owner_id (UUID|None), owner_type (str='user'), visibility (str='private') fields")

# Batch 3: Implementations (parallel - different repo types)
Task("python-backend-engineer", "Update local repository implementations.
  Files: skillmeat/core/repositories/local_*.py
  Add auth_context param; validate owner_id on writes; default to LOCAL_ADMIN_CONTEXT when None")

Task("data-layer-expert", "Update enterprise repository implementations.
  File: skillmeat/cache/enterprise_repositories.py
  Add auth_context param; enforce tenant_id from TenantContext ContextVar; owner_id checks on writes")

Task("backend-architect", "Update service layer to accept and thread AuthContext.
  Files: skillmeat/core/services/artifact_service.py, collection_service.py
  Accept AuthContext param; pass to repository calls; default to LOCAL_ADMIN_CONTEXT in local mode
  Pattern: Follow tenant-scoping-strategy.md section 3-4")
```
