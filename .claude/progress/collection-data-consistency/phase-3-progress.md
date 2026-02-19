---
type: progress
prd: collection-data-consistency
phase: 3
title: API Endpoint Consistency (CollectionService)
status: completed
started: null
completed: null
progress: 100
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-3.1
  title: Create CollectionService Class
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  effort: 2h
  priority: critical
  files:
  - skillmeat/api/services/collection_service.py
- id: TASK-3.2
  title: Create Services __init__.py
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: haiku
  effort: 0.25h
  priority: medium
  files:
  - skillmeat/api/services/__init__.py
- id: TASK-3.3
  title: Update GET /api/v1/artifacts
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: sonnet
  effort: 0.5h
  priority: high
  files:
  - skillmeat/api/routers/artifacts.py
- id: TASK-3.4
  title: Update GET /api/v1/artifacts/{id}
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: sonnet
  effort: 0.25h
  priority: high
  files:
  - skillmeat/api/routers/artifacts.py
- id: TASK-3.5
  title: Update GET /api/v1/projects/{id}/artifacts
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: sonnet
  effort: 0.5h
  priority: high
  files:
  - skillmeat/api/routers/projects.py
- id: TASK-3.6
  title: Update GET /api/v1/collections/{id}/artifacts
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: sonnet
  effort: 0.25h
  priority: medium
  files:
  - skillmeat/api/routers/collections.py
- id: TASK-3.7
  title: Add CollectionService Unit Tests
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  model: sonnet
  effort: 1h
  priority: high
  files:
  - tests/api/services/test_collection_service.py
parallelization:
  batch_1:
  - TASK-3.1
  batch_2:
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  - TASK-3.5
  - TASK-3.6
  - TASK-3.7
blockers: []
success_criteria:
- id: SC-3.1
  description: CollectionService class created with batch and single methods
  status: pending
- id: SC-3.2
  description: All artifact-returning endpoints use CollectionService
  status: pending
- id: SC-3.3
  description: No N+1 queries in any endpoint (verified via query logging)
  status: pending
- id: SC-3.4
  description: API responses include consistent collections array structure
  status: pending
- id: SC-3.5
  description: CollectionService unit tests achieve >80% coverage
  status: pending
- id: SC-3.6
  description: No regression in endpoint response schemas
  status: pending
updated: '2026-01-31'
schema_version: 2
doc_type: progress
feature_slug: collection-data-consistency
---

# Phase 3: API Endpoint Consistency (CollectionService)

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-data-consistency/phase-3-progress.md \
  -t TASK-3.1 -s completed

# Batch update after parallel execution
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-data-consistency/phase-3-progress.md \
  --updates "TASK-3.2:completed,TASK-3.3:completed,TASK-3.4:completed,TASK-3.5:completed,TASK-3.6:completed,TASK-3.7:completed"
```

## Overview

Phase 3 creates a centralized CollectionService abstraction to ensure all artifact-returning endpoints provide consistent collection membership data. This builds on the N+1 fix from Phase 1 by extracting the optimized query pattern into a reusable service.

**Estimated Duration**: 4-5 hours
**Risk**: Medium (multiple endpoints)
**Dependencies**: Phase 1 complete (uses optimized query pattern)

## Tasks

### TASK-3.1: Create CollectionService Class

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 2h
**Priority**: critical
**Model**: opus

**Description**: Create `api/services/collection_service.py` with `get_collection_membership_batch()` method

**Requirements**:
- Service class exists with proper docstrings
- Method accepts artifact_ids and returns Dict[str, List[ArtifactCollectionInfo]]
- Uses optimized batch query pattern from Phase 1
- Includes `get_collection_membership_single()` convenience method
- Thread-safe for concurrent requests

**Files**:
- `skillmeat/api/services/collection_service.py` (NEW)

**Key Implementation Notes**:
- Use subquery for counts to minimize database round trips
- Return empty list for artifacts with no collections (not None)
- All input artifact_ids should have entries in result dict

---

### TASK-3.2: Create Services __init__.py

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: medium
**Model**: haiku
**Dependencies**: TASK-3.1

**Description**: Create `api/services/__init__.py` with proper exports

**Requirements**:
- CollectionService importable from `skillmeat.api.services`
- Proper `__all__` declaration

**Files**:
- `skillmeat/api/services/__init__.py` (NEW)

---

### TASK-3.3: Update GET /api/v1/artifacts

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-3.1

**Description**: Refactor artifacts list endpoint to use CollectionService

**Requirements**:
- Endpoint returns consistent collections array
- Uses batch query via CollectionService
- No inline collection queries remain

**Files**:
- `skillmeat/api/routers/artifacts.py`: Use CollectionService for list endpoint

---

### TASK-3.4: Update GET /api/v1/artifacts/{id}

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-3.1

**Description**: Refactor artifact detail endpoint to use CollectionService

**Requirements**:
- Single artifact includes collections array
- Uses single method from CollectionService

**Files**:
- `skillmeat/api/routers/artifacts.py`: Use CollectionService for detail endpoint

---

### TASK-3.5: Update GET /api/v1/projects/{id}/artifacts

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-3.1

**Description**: Refactor project artifacts endpoint to use CollectionService

**Requirements**:
- Project artifact list includes collection membership
- Uses batch method for efficiency

**Files**:
- `skillmeat/api/routers/projects.py`: Use CollectionService

---

### TASK-3.6: Update GET /api/v1/collections/{id}/artifacts

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: medium
**Model**: sonnet
**Dependencies**: TASK-3.1

**Description**: Refactor collection artifacts endpoint to use CollectionService

**Requirements**:
- Collection artifact list is self-consistent
- Collection of the current request included in results

**Files**:
- `skillmeat/api/routers/collections.py`: Use CollectionService

---

### TASK-3.7: Add CollectionService Unit Tests

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 1h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-3.1

**Description**: Create tests for CollectionService methods

**Requirements**:
- >80% coverage
- Tests batch queries with various sizes
- Tests empty inputs
- Tests edge cases (no collections, missing artifacts)
- Tests concurrent access patterns

**Files**:
- `tests/api/services/test_collection_service.py` (NEW)

---

## Quality Gates

- [ ] CollectionService class created with batch and single methods
- [ ] All artifact-returning endpoints use CollectionService
- [ ] No N+1 queries in any endpoint (verified via query logging)
- [ ] API responses include consistent `collections` array structure
- [ ] CollectionService unit tests achieve >80% coverage
- [ ] No regression in endpoint response schemas

## Key Files Modified

- `skillmeat/api/services/collection_service.py` (NEW)
- `skillmeat/api/services/__init__.py` (NEW)
- `skillmeat/api/routers/artifacts.py`
- `skillmeat/api/routers/projects.py`
- `skillmeat/api/routers/collections.py`
- `tests/api/services/test_collection_service.py` (NEW)
