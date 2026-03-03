---
type: progress
schema_version: 2
doc_type: progress
prd: backstage-integration-demo
feature_slug: backstage-integration-demo
prd_ref: docs/project_plans/PRDs/integrations/backstage-integration-demo.md
plan_ref: null
phase: 1
title: SAM Backend API
status: pending
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- code-reviewer
tasks:
- id: TASK-1.1
  description: Add render_in_memory(target_id, variables) method to TemplateService
    — returns list[RenderedFile] without writing to disk
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 4h
  priority: high
- id: TASK-1.2
  description: Add remote_git platform type to DeploymentProfile; add remote_url field
    to DeploymentSet model
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: TASK-1.3
  description: Create Pydantic schemas in skillmeat/api/schemas/idp_integration.py
    (IDPScaffoldRequest, IDPScaffoldResponse, IDPRegisterDeploymentRequest, IDPRegisterDeploymentResponse)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1h
  priority: high
- id: TASK-1.4
  description: Create skillmeat/api/routers/idp_integration.py with POST /scaffold
    and POST /register-deployment endpoints; register in server.py
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  estimated_effort: 3h
  priority: high
- id: TASK-1.5
  description: Unit and integration tests for both IDP endpoints (authenticated/unauthenticated,
    valid/invalid target_id, idempotent register)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.4
  estimated_effort: 3h
  priority: high
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  batch_2:
  - TASK-1.4
  batch_3:
  - TASK-1.5
  critical_path:
  - TASK-1.1
  - TASK-1.4
  - TASK-1.5
  estimated_total_time: 10h
blockers: []
success_criteria:
- id: SC-1
  description: POST /idp/scaffold returns Base64-encoded file tree for valid composite
  status: pending
- id: SC-2
  description: POST /idp/register-deployment creates DeploymentSet record
  status: pending
- id: SC-3
  description: Idempotent register-deployment updates instead of duplicating
  status: pending
- id: SC-4
  description: 401 returned without bearer token
  status: pending
- id: SC-5
  description: All existing deployment tests still pass
  status: pending
files_modified:
- skillmeat/core/services/template_service.py
- skillmeat/core/deployment.py
- skillmeat/cache/models.py
- skillmeat/api/routers/idp_integration.py
- skillmeat/api/schemas/idp_integration.py
- skillmeat/api/server.py
updated: '2026-03-03'
progress: 60
---

# backstage-integration-demo - Phase 1: SAM Backend API

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/backstage-integration-demo/phase-1-progress.md -t TASK-X -s completed
```

---

## Objective

Extend SAM's backend with two new IDP integration endpoints: a headless scaffold renderer that returns in-memory rendered context packs, and a deployment registration endpoint for tracking IDP-provisioned packs. Builds on existing TemplateService and DeploymentManager infrastructure.

---

## Implementation Notes

### Architectural Decisions

- `render_in_memory()` adds a code path to `TemplateService` that captures rendered files in a list instead of writing to disk. The existing disk-write path remains unchanged.
- `remote_git` is an additive enum value on `DeploymentProfile.platform` — no migration needed for existing records.
- New router at `skillmeat/api/routers/idp_integration.py` with prefix `/api/v1/integrations/idp/`.

### Patterns and Best Practices

- Follow existing router patterns in `skillmeat/api/routers/artifacts.py` for dependency injection and error handling.
- Pydantic schemas use `ConfigDict(str_strip_whitespace=True)` per existing conventions.
- OpenTelemetry spans for both endpoints per observability standards.

### Known Gotchas

- `TemplateService` uses `@lru_cache` for regex patterns — ensure `render_in_memory` doesn't break cache.
- `CompositeArtifact` membership uses UUID resolution (ADR-007) — the scaffold endpoint must resolve `type:name` to UUID before querying members.
- Register-deployment idempotency: check `(repo_url, target_id)` uniqueness before insert.

---

## Orchestration Quick Reference

```bash
# Batch 1 (parallel — no dependencies)
Task("python-backend-engineer", "TASK-1.1: Add render_in_memory() to TemplateService. File: skillmeat/core/services/template_service.py. Returns list[RenderedFile] (path + bytes). No disk writes. Reuse existing variable substitution logic.")
Task("python-backend-engineer", "TASK-1.2: Add remote_git platform to DeploymentProfile. File: skillmeat/cache/models.py, skillmeat/core/deployment.py. Add remote_url field to DeploymentSet.")
Task("python-backend-engineer", "TASK-1.3: Create Pydantic schemas. File: skillmeat/api/schemas/idp_integration.py. Models: IDPScaffoldRequest, IDPScaffoldResponse, RenderedFile, IDPRegisterDeploymentRequest, IDPRegisterDeploymentResponse.")

# Batch 2 (depends on batch 1)
Task("python-backend-engineer", "TASK-1.4: Create IDP integration router. File: skillmeat/api/routers/idp_integration.py. POST /scaffold and POST /register-deployment. Register in server.py. Follow patterns from artifacts.py router.")

# Batch 3 (depends on batch 2)
Task("python-backend-engineer", "TASK-1.5: Tests for IDP endpoints. Auth, valid/invalid target, idempotent register. Follow existing test patterns.")
```

---

## Completion Notes

_Fill in when phase is complete._
