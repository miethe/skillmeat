---
type: progress
schema_version: 2
doc_type: progress
prd: aaa-rbac-foundation
feature_slug: aaa-rbac-foundation
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 3
title: Middleware & Auth Providers - Pluggable Authentication
status: pending
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 2
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- backend-architect
contributors:
- python-backend-engineer
tasks:
- id: AUTH-001
  description: Create abstract AuthProvider ABC with validate(request) -> AuthContext
  status: completed
  assigned_to:
  - backend-architect
  dependencies: []
  estimated_effort: 1 pt
  priority: critical
- id: AUTH-002
  description: Implement LocalAuthProvider (returns static local_admin AuthContext)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - AUTH-001
  estimated_effort: 1 pt
  priority: critical
- id: AUTH-003
  description: Implement ClerkAuthProvider (validates JWTs, maps claims to AuthContext)
  status: pending
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies:
  - AUTH-001
  estimated_effort: 3 pts
  priority: high
- id: AUTH-004
  description: Create require_auth FastAPI dependency with scope validation
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - AUTH-001
  estimated_effort: 2 pts
  priority: critical
- id: AUTH-005
  description: Refactor verify_enterprise_pat() to return AuthContext (REQ-20260306)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2 pts
  priority: high
- id: AUTH-006
  description: Create TenantContext middleware that sets ContextVar from AuthContext
    (REQ-20260306)
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - AUTH-004
  estimated_effort: 2 pts
  priority: high
- id: AUTH-007
  description: Add SKILLMEAT_AUTH_PROVIDER env var config and provider instantiation
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - AUTH-001
  estimated_effort: 1 pt
  priority: medium
- id: AUTH-008
  description: Unit tests for LocalAuthProvider, ClerkAuthProvider, require_auth
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - AUTH-002
  - AUTH-003
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - AUTH-001
  - AUTH-005
  batch_2:
  - AUTH-002
  - AUTH-003
  - AUTH-004
  - AUTH-007
  batch_3:
  - AUTH-006
  - AUTH-008
  critical_path:
  - AUTH-001
  - AUTH-004
  - AUTH-006
  estimated_total_time: 5 days
blockers: []
success_criteria:
- id: SC-1
  description: AuthProvider ABC compiles and is documented
  status: pending
- id: SC-2
  description: LocalAuthProvider returns consistent local_admin context
  status: pending
- id: SC-3
  description: ClerkAuthProvider validates JWTs and maps claims
  status: pending
- id: SC-4
  description: require_auth dependency injects AuthContext correctly
  status: pending
- id: SC-5
  description: verify_enterprise_pat() returns AuthContext (REQ-20260306)
  status: pending
- id: SC-6
  description: TenantContext set before service layer execution (REQ-20260306)
  status: pending
- id: SC-7
  description: Zero-auth mode still works transparently
  status: pending
files_modified:
- skillmeat/api/auth/provider.py
- skillmeat/api/auth/local_provider.py
- skillmeat/api/auth/clerk_provider.py
- skillmeat/api/dependencies.py
- skillmeat/api/middleware/enterprise_auth.py
- skillmeat/api/config.py
- skillmeat/api/tests/test_auth_providers.py
progress: 25
updated: '2026-03-07'
---

# aaa-rbac-foundation - Phase 3: Middleware & Auth Providers - Pluggable Authentication

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-3-progress.md -t AUTH-001 -s completed
```

---

## Objective

Build the pluggable authentication system: abstract AuthProvider interface, LocalAuthProvider (zero-auth), ClerkAuthProvider (JWT), require_auth FastAPI dependency, and TenantContext middleware. Address REQ-20260306 by updating verify_enterprise_pat() and wiring TenantContext.

---

## Orchestration Quick Reference

```bash
# Batch 1: ABC + PAT refactor (parallel - different files)
Task("backend-architect", "Create AuthProvider ABC.
  New file: skillmeat/api/auth/provider.py
  ABC with: validate(request: Request) -> AuthContext (async)
  Handle: missing auth headers, invalid tokens, expired tokens
  Pattern: Strategy pattern; instantiate via SKILLMEAT_AUTH_PROVIDER config")

Task("python-backend-engineer", "Refactor verify_enterprise_pat() per REQ-20260306.
  File: skillmeat/api/middleware/enterprise_auth.py
  Change: Return AuthContext instead of bare str token
  Add: Extract tenant_id/user_id from PAT claims
  Add: Support dual-mode PAT + Clerk JWT Bearer tokens")

# Batch 2: Providers + dependency + config (parallel - separate new files)
Task("python-backend-engineer", "Implement LocalAuthProvider.
  New file: skillmeat/api/auth/local_provider.py
  Always returns LOCAL_ADMIN_CONTEXT (system_admin, all scopes)
  No validation needed; zero-auth transparent")

Task("backend-architect", "Implement ClerkAuthProvider.
  New file: skillmeat/api/auth/clerk_provider.py
  Validate Clerk JWT from Authorization: Bearer header
  Map claims: org_id -> tenant_id, sub -> user_id, clerk_roles -> roles
  Handle: Invalid JWT -> 401; missing claims -> 403")

Task("python-backend-engineer", "Create require_auth FastAPI dependency.
  File: skillmeat/api/dependencies.py
  Dependency: calls AuthProvider.validate(); optionally checks scopes
  Signature: require_auth(scopes: list[str] | None = None)
  Returns: AuthContext injected into route handler")

Task("python-backend-engineer", "Add SKILLMEAT_AUTH_PROVIDER config.
  File: skillmeat/api/config.py
  Add: auth_provider field to APISettings (default='local')
  Values: 'local' | 'clerk'
  Wire: Instantiate correct provider at app startup")

# Batch 3: Middleware + tests
Task("backend-architect", "Create TenantContext middleware per REQ-20260306.
  File: skillmeat/api/middleware/enterprise_auth.py or new middleware
  Before service layer: extract tenant_id from AuthContext, call set_tenant_context()
  Ensure: _get_content_service() in enterprise_content.py gets correct TenantContext")

Task("python-backend-engineer", "Write unit tests for auth providers.
  New file: skillmeat/api/tests/test_auth_providers.py
  Test: LocalAuthProvider always succeeds; ClerkAuthProvider validates JWT (mock);
        Invalid tokens raise 401; require_auth checks scopes; 403 on scope mismatch")
```
