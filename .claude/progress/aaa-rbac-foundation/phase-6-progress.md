---
type: progress
schema_version: 2
doc_type: progress
prd: aaa-rbac-foundation
feature_slug: aaa-rbac-foundation
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 6
title: CLI Authentication - Device Code Flow & Credential Storage
status: in_progress
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: CLI-001
  description: Implement OAuth device code flow for skillmeat login
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3 pts
  priority: high
- id: CLI-002
  description: Implement secure credential storage (keyring or encrypted file)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-001
  estimated_effort: 2 pts
  priority: high
- id: CLI-003
  description: Implement skillmeat auth --token <PAT> for headless environments
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-002
  estimated_effort: 1 pt
  priority: high
- id: CLI-004
  description: Implement token refresh for expired JWTs
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-002
  estimated_effort: 1 pt
  priority: medium
- id: CLI-005
  description: Update CLI HTTP client to inject auth token into requests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-002
  estimated_effort: 1 pt
  priority: high
- id: CLI-006
  description: Implement skillmeat logout to clear stored credentials
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-002
  estimated_effort: 1 pt
  priority: low
- id: CLI-007
  description: Verify CLI works without login in local mode (SKILLMEAT_ENV=local)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-001
  estimated_effort: 1 pt
  priority: critical
- id: CLI-008
  description: CLI integration tests (mocked device code flow, PAT input, credential
    storage)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-005
  estimated_effort: 1 pt
  priority: medium
parallelization:
  batch_1:
  - CLI-001
  batch_2:
  - CLI-002
  - CLI-007
  batch_3:
  - CLI-003
  - CLI-004
  - CLI-005
  - CLI-006
  batch_4:
  - CLI-008
  critical_path:
  - CLI-001
  - CLI-002
  - CLI-005
  - CLI-008
  estimated_total_time: 5 days
blockers: []
success_criteria:
- id: SC-1
  description: Device code flow works end-to-end (mock Clerk endpoint)
  status: pending
- id: SC-2
  description: Credentials stored securely
  status: pending
- id: SC-3
  description: skillmeat auth --token <PAT> works
  status: pending
- id: SC-4
  description: Auth token injected into CLI HTTP requests
  status: pending
- id: SC-5
  description: Local zero-auth mode works without login
  status: pending
files_modified:
- skillmeat/cli/commands/auth.py
- skillmeat/cli/auth_flow.py
- skillmeat/cli/credential_store.py
- skillmeat/cli/http_client.py
- skillmeat/cli.py
updated: '2026-03-07'
---

# aaa-rbac-foundation - Phase 6: CLI Authentication - Device Code Flow & Credential Storage

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-6-progress.md -t CLI-001 -s completed
```

---

## Objective

Implement CLI authentication: `skillmeat login` (OAuth device code flow), `skillmeat auth --token` (PAT), `skillmeat logout`, secure credential storage, and auth token injection into HTTP requests. Maintain zero-auth in local mode.
