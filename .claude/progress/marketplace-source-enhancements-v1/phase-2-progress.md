---
type: progress
prd: "marketplace-source-enhancements-v1"
phase: 2
title: "Backend Exclusions"
status: in_progress
progress: 50
total_tasks: 8
completed_tasks: 4
story_points: 8
last_updated: "2025-12-31T21:30:00Z"
session_note: "Batch 1-2 completed. Recovered from session interruption."

tasks:
  - id: "TASK-2.1"
    title: "Add excluded fields to CatalogEntry model"
    status: "completed"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimate: "1h"
    completed_at: "2025-12-31T21:00:00Z"
  - id: "TASK-2.2"
    title: "Create Alembic migration"
    status: "completed"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-2.1"]
    estimate: "1h"
    completed_at: "2025-12-31T21:05:00Z"
    agent_id: "ad49e23"
  - id: "TASK-2.3"
    title: "Add excluded status to schemas"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "1h"
    completed_at: "2025-12-31T21:00:00Z"
  - id: "TASK-2.4"
    title: "Create ExcludeArtifactRequest schema"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.3"]
    estimate: "1h"
    completed_at: "2025-12-31T21:04:00Z"
    agent_id: "ab8736f"
  - id: "TASK-2.5"
    title: "Add PATCH exclude endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.2", "TASK-2.4"]
    estimate: "2h"
  - id: "TASK-2.6"
    title: "Add restore endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.5"]
    estimate: "1h"
  - id: "TASK-2.7"
    title: "Update catalog list to filter excluded"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.5"]
    estimate: "1h"
  - id: "TASK-2.8"
    title: "Backend API tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.6", "TASK-2.7"]
    estimate: "2h"

parallelization:
  batch_1: ["TASK-2.1", "TASK-2.3"]  # COMPLETED
  batch_2: ["TASK-2.2", "TASK-2.4"]  # COMPLETED
  batch_3: ["TASK-2.5"]  # PENDING
  batch_4: ["TASK-2.6", "TASK-2.7"]  # PENDING
  batch_5: ["TASK-2.8"]  # PENDING

blockers: []
---

# Phase 2: Backend Exclusions

## Overview

Backend changes to support marking artifacts as "Not an Artifact". Adds database fields, API endpoints for exclude/restore.

## Key Changes
- Add `excluded_at`, `excluded_reason` fields to MarketplaceCatalogEntry model
- Add `excluded` to CatalogStatus enum
- PATCH endpoint for excluding artifacts
- DELETE (restore) endpoint for restoring excluded artifacts

## Orchestration Quick Reference

### Batch 1 (Parallel - No Dependencies)
```
Task("data-layer-expert", "TASK-2.1: Add excluded fields to CatalogEntry model.
     File: skillmeat/cache/models.py
     - Add excluded_at: datetime | None field
     - Add excluded_reason: str | None field
     - Update __repr__ to include excluded status")

Task("python-backend-engineer", "TASK-2.3: Add excluded status to schemas.
     File: skillmeat/api/schemas/marketplace.py
     - Add 'excluded' to CatalogStatus literal type
     - Update CatalogEntryResponse with excluded_at, excluded_reason fields")
```

### Batch 2 (After Batch 1)
```
Task("data-layer-expert", "TASK-2.2: Create Alembic migration.
     File: skillmeat/api/alembic/versions/xxx_add_excluded_fields.py
     - Add excluded_at column (nullable datetime)
     - Add excluded_reason column (nullable string, max 500 chars)
     - Add index on excluded_at for efficient filtering")

Task("python-backend-engineer", "TASK-2.4: Create ExcludeArtifactRequest schema.
     File: skillmeat/api/schemas/marketplace.py
     - ExcludeArtifactRequest with optional reason field
     - RestoreArtifactRequest (minimal, just entry_id)")
```

### Batch 3 (After Batch 2)
```
Task("python-backend-engineer", "TASK-2.5: Add PATCH exclude endpoint.
     File: skillmeat/api/routers/marketplace_sources.py
     - PATCH /api/v1/marketplace/sources/{source_id}/artifacts/{entry_id}/exclude
     - Set status to 'excluded', excluded_at to now(), excluded_reason from request
     - Return updated CatalogEntryResponse")
```

### Batch 4 (After Batch 3)
```
Task("python-backend-engineer", "TASK-2.6: Add restore endpoint.
     File: skillmeat/api/routers/marketplace_sources.py
     - DELETE /api/v1/marketplace/sources/{source_id}/artifacts/{entry_id}/exclude
     - Reset status to 'new', clear excluded_at and excluded_reason
     - Return updated CatalogEntryResponse")

Task("python-backend-engineer", "TASK-2.7: Update catalog list filtering.
     File: skillmeat/api/routers/marketplace_sources.py
     - Add include_excluded query param (default false)
     - Filter out excluded by default
     - When include_excluded=true, return all including excluded")
```

### Batch 5 (After Batch 4)
```
Task("python-backend-engineer", "TASK-2.8: Backend API tests.
     File: tests/api/test_marketplace_sources.py
     - Test exclude endpoint (success, not found, already excluded)
     - Test restore endpoint (success, not found, not excluded)
     - Test catalog filtering (excluded hidden by default, shown with flag)")
```

## Quality Gates
- [ ] All 8 tasks complete
- [ ] Migration runs without errors
- [ ] API tests passing (>80% coverage)
- [ ] Exclude/restore <500ms response time
- [ ] No breaking changes to existing endpoints
