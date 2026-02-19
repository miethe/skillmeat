---
type: progress
schema_version: 2
doc_type: progress
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
phase: 1
title: Type System + Backend CRUD
status: completed
created: '2026-02-19'
updated: '2026-02-19'
prd_ref: docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
overall_progress: 0
completion_estimate: on-track
total_tasks: 16
completed_tasks: 16
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- frontend-developer
- python-backend-engineer
contributors: []
tasks:
- id: CUX-P1-01
  description: Add 'composite' to ArtifactType union in skillmeat/web/types/artifact.ts
  status: completed
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-02
  description: Add composite entry to ARTIFACT_TYPES config registry with icon, label,
    color, form schema
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-01
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-03
  description: Update parseArtifactId() and formatArtifactId() to handle 'composite'
    type
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-01
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-04
  description: Add 'composite' to platform defaults constant
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-01
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-05
  description: Verify CompositeService create/update/delete methods exist and are
    tested
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-06
  description: Verify CompositeMembership ORM model has position column; create migration
    if absent
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-07
  description: Create composites.py router with 6 endpoint stubs; register in FastAPI
    app under /api/v1/composites
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-05
  - CUX-P1-06
  estimated_effort: 2pt
  priority: high
- id: CUX-P1-08
  description: Implement POST /api/v1/composites — composite creation with members
    and positions
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 2pt
  priority: high
- id: CUX-P1-09
  description: Implement PUT /api/v1/composites/{id} — update composite metadata
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-10
  description: Implement DELETE /api/v1/composites/{id} — delete composite with optional
    cascade
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-11
  description: Implement POST /api/v1/composites/{id}/members — add member to composite
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-12
  description: Implement DELETE /api/v1/composites/{id}/members/{member_id} — remove
    member
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-13
  description: Implement PATCH /api/v1/composites/{id}/members — reorder members
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P1-14
  description: Create Pydantic request/response schemas for all 6 endpoints
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-07
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-15
  description: Regenerate openapi.json with all 6 new endpoints and schemas
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-14
  estimated_effort: 1pt
  priority: high
- id: CUX-P1-16
  description: Write integration tests for all 6 endpoints covering happy path and
    error cases
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-15
  estimated_effort: 2pt
  priority: high
parallelization:
  batch_1:
  - CUX-P1-01
  - CUX-P1-05
  - CUX-P1-06
  batch_2:
  - CUX-P1-02
  - CUX-P1-03
  - CUX-P1-04
  - CUX-P1-07
  batch_3:
  - CUX-P1-08
  - CUX-P1-09
  - CUX-P1-10
  - CUX-P1-11
  - CUX-P1-12
  - CUX-P1-13
  - CUX-P1-14
  batch_4:
  - CUX-P1-15
  batch_5:
  - CUX-P1-16
  critical_path:
  - CUX-P1-01
  - CUX-P1-07
  - CUX-P1-14
  - CUX-P1-15
  - CUX-P1-16
  estimated_total_time: 3-4 days
blockers: []
success_criteria:
- id: SC-P1-1
  description: Enum change does not break existing type-checking (pnpm type-check
    passes)
  status: pending
- id: SC-P1-2
  description: All 6 CRUD endpoints implement and return correct status codes
  status: pending
- id: SC-P1-3
  description: Integration tests for all endpoints pass
  status: pending
- id: SC-P1-4
  description: openapi.json regenerated and includes all endpoints
  status: pending
- id: SC-P1-5
  description: No regression in existing artifact type paths
  status: pending
- id: SC-P1-6
  description: pnpm build succeeds
  status: pending
- id: SC-P1-7
  description: pnpm lint passes with no new warnings
  status: pending
- id: SC-P1-8
  description: UUID column migration applies cleanly (if performed)
  status: pending
files_modified: []
progress: 100
commit_refs:
- 21f7a79c,fbf2beb7,f02be28e
---
# Phase 1: Type System + Backend CRUD

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
# Single task
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-1-progress.md -t CUX-P1-01 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-1-progress.md \
  --updates "CUX-P1-01:completed,CUX-P1-05:completed,CUX-P1-06:completed"
```

---

## Objective

Add `'composite'` to the frontend type system (type union, config, ID parsing, platform defaults) and wire 6 CRUD endpoints to the existing backend CompositeService. No new business logic -- purely surface-level integration of v1 infrastructure.

---

## Orchestration Quick Reference

### Batch 1 (No dependencies — launch immediately)

```
Task("frontend-developer", "CUX-P1-01: Add 'composite' to ArtifactType union.
  File: skillmeat/web/types/artifact.ts
  Add 'composite' to the ArtifactType union type. Ensure all switch statements handle new case.")

Task("python-backend-engineer", "CUX-P1-05: Verify CompositeService CRUD methods exist and are tested.
  File: skillmeat/core/services/composite_service.py
  Confirm create_composite(), update_composite(), delete_composite() exist. Implement if absent.")

Task("python-backend-engineer", "CUX-P1-06: Verify CompositeMembership has position column.
  File: skillmeat/cache/models.py
  Check position column on CompositeMembership. Create Alembic migration if missing.")
```

### Batch 2 (After Batch 1)

```
Task("frontend-developer", "CUX-P1-02, CUX-P1-03, CUX-P1-04: ARTIFACT_TYPES config, ID parsing, platform defaults.
  Files: skillmeat/web/lib/constants/, skillmeat/web/types/artifact.ts
  Add composite config entry, update parse/format functions, add to platform defaults.")

Task("python-backend-engineer", "CUX-P1-07: Create composites.py router with 6 endpoint stubs.
  File: skillmeat/api/routers/composites.py
  Register under /api/v1/composites in main app. Follow existing router patterns.")
```

### Batch 3 (After Batch 2)

```
Task("python-backend-engineer", "CUX-P1-08 through CUX-P1-14: Implement all 6 endpoints + Pydantic schemas.
  Files: skillmeat/api/routers/composites.py, skillmeat/api/schemas/
  Implement POST create, PUT update, DELETE, POST add-member, DELETE remove-member, PATCH reorder.
  Create all request/response schemas.")
```

### Batch 4 (After Batch 3)

```
Task("python-backend-engineer", "CUX-P1-15: Regenerate openapi.json.
  File: skillmeat/api/openapi.json
  Run FastAPI schema generation. Verify all 6 endpoints appear.")
```

### Batch 5 (After Batch 4)

```
Task("python-backend-engineer", "CUX-P1-16: Write integration tests for all 6 composite endpoints.
  File: tests/test_composites_api.py
  Cover happy path and error cases (400, 404) for each endpoint. >80% coverage target.")
```

---

## Known Gotchas

- Complete frontend type tasks (CUX-P1-01 through CUX-P1-04) before backend work begins so the team has a stable foundation.
- CUX-P1-05 and CUX-P1-06 are verification tasks -- read codebase first. Escalate if v1 infrastructure is incomplete.
- Check if `AssociationsDTO` or similar already exists from v1; reuse where possible.
- All endpoints must follow existing error response patterns in the codebase.
- Router must be registered in main FastAPI app with correct prefix.
