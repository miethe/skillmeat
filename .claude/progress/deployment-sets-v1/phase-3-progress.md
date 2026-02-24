---
type: progress
schema_version: 2
doc_type: progress
prd: "deployment-sets-v1"
feature_slug: "deployment-sets"
prd_ref: docs/project_plans/PRDs/features/deployment-sets-v1.md
plan_ref: docs/project_plans/implementation_plans/features/deployment-sets-v1.md
phase: 3
title: "API Layer"
status: "planning"
started: "2026-02-23"
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 2
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["python-backend-engineer"]
contributors: []
tasks:
  - id: "DS-007"
    description: "Pydantic schemas for all deployment set DTOs (create, update, response, member, resolve, batch deploy)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DS-006"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "DS-008"
    description: "11 REST endpoints + router registration in server.py with owner-scope enforcement hooks"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DS-007"]
    estimated_effort: "3 pts"
    priority: "high"
parallelization:
  batch_1: ["DS-007"]
  batch_2: ["DS-008"]
  critical_path: ["DS-007", "DS-008"]
  estimated_total_time: "1 day"
blockers: []
success_criteria:
  - { id: "SC-1", description: "All 11 endpoints registered and returning correct HTTP status codes", status: "pending" }
  - { id: "SC-2", description: "Integration tests cover happy path + error cases", status: "pending" }
  - { id: "SC-3", description: "HTTP 422 for circular-ref add-member confirmed by test", status: "pending" }
  - { id: "SC-4", description: "No ORM model objects returned in any response (DTOs only)", status: "pending" }
  - { id: "SC-5", description: "Router registered in server.py; dev server starts without error", status: "pending" }
files_modified: [
  "skillmeat/api/schemas/deployment_sets.py",
  "skillmeat/api/routers/deployment_sets.py",
  "skillmeat/api/server.py"
]
---

# deployment-sets-v1 - Phase 3: API Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/deployment-sets-v1/phase-3-progress.md -t DS-007 -s completed
```

---

## Objective

Create Pydantic DTOs and 11 FastAPI REST endpoints for deployment set CRUD, member management, resolution, and batch deploy. Register router in server.py and add owner-scope enforcement hooks.

---

## Orchestration Quick Reference

```python
# Batch 1: Schemas
Task("python-backend-engineer", "Create Pydantic schemas in skillmeat/api/schemas/deployment_sets.py. See implementation plan Phase 3, task DS-007. Follow existing schemas pattern in skillmeat/api/schemas/.", model="sonnet", mode="acceptEdits")

# Batch 2: Endpoints + router (after DS-007)
Task("python-backend-engineer", "Create router at skillmeat/api/routers/deployment_sets.py with all 11 endpoints. Register in skillmeat/api/server.py under API prefix wiring. Map CycleError->422, NotFound->404 and enforce owner-scope hooks. Write integration tests. See implementation plan Phase 3, task DS-008.", model="sonnet", mode="acceptEdits")
```

---

## Implementation Notes

### 11 Endpoints (from PRD)
1. POST /deployment-sets — Create set
2. GET /deployment-sets — List sets (paginated)
3. GET /deployment-sets/{id} — Get set with members
4. PUT /deployment-sets/{id} — Update set metadata
5. DELETE /deployment-sets/{id} — Delete set (cascade members)
6. POST /deployment-sets/{id}/clone — Clone set
7. POST /deployment-sets/{id}/members — Add member
8. DELETE /deployment-sets/{id}/members/{member_id} — Remove member
9. PUT /deployment-sets/{id}/members/{member_id} — Update member position
10. GET /deployment-sets/{id}/resolve — Resolve to artifact UUIDs
11. POST /deployment-sets/{id}/deploy — Batch deploy

### Patterns to Follow
- Follow `skillmeat/api/routers/groups.py` for router structure
- Follow `skillmeat/api/schemas/` for DTO patterns
