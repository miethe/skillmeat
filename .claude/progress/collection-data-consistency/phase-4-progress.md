---
type: progress
prd: "collection-data-consistency"
phase: 4
title: "Caching Layer"
status: pending
started: null
completed: null
progress: 0

total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "TASK-4.1"
    title: "Implement Collection Count Cache"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    model: "opus"
    effort: "1h"
    priority: "high"
    files:
      - "skillmeat/cache/collection_cache.py"

  - id: "TASK-4.2"
    title: "Integrate Cache with CollectionService"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    model: "sonnet"
    effort: "0.5h"
    priority: "high"
    files:
      - "skillmeat/api/services/collection_service.py"

  - id: "TASK-4.3"
    title: "Add Cache Invalidation on Add Artifact"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    model: "sonnet"
    effort: "0.25h"
    priority: "high"
    files:
      - "skillmeat/api/routers/user_collections.py"

  - id: "TASK-4.4"
    title: "Add Cache Invalidation on Remove Artifact"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    model: "sonnet"
    effort: "0.25h"
    priority: "high"
    files:
      - "skillmeat/api/routers/user_collections.py"

  - id: "TASK-4.5"
    title: "Add Cache Invalidation on Delete Collection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    model: "sonnet"
    effort: "0.25h"
    priority: "high"
    files:
      - "skillmeat/api/routers/user_collections.py"

  - id: "TASK-4.6"
    title: "Add Cache Unit Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    model: "sonnet"
    effort: "0.5h"
    priority: "medium"
    files:
      - "tests/cache/test_collection_cache.py"

parallelization:
  batch_1: ["TASK-4.1"]
  batch_2: ["TASK-4.2", "TASK-4.3", "TASK-4.4", "TASK-4.5", "TASK-4.6"]

blockers: []

success_criteria:
  - id: "SC-4.1"
    description: "Cache class created with thread-safe operations"
    status: "pending"
  - id: "SC-4.2"
    description: "TTL expiration working (verified via tests)"
    status: "pending"
  - id: "SC-4.3"
    description: "Cache invalidation triggered on add/remove/delete operations"
    status: "pending"
  - id: "SC-4.4"
    description: "Cache hit rate visible in logs"
    status: "pending"
  - id: "SC-4.5"
    description: "No stale data visible after invalidation events"
    status: "pending"
  - id: "SC-4.6"
    description: "Cache unit tests achieve >80% coverage"
    status: "pending"
---

# Phase 4: Caching Layer

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-data-consistency/phase-4-progress.md \
  -t TASK-4.1 -s completed

# Batch update after parallel execution
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-data-consistency/phase-4-progress.md \
  --updates "TASK-4.2:completed,TASK-4.3:completed,TASK-4.4:completed,TASK-4.5:completed,TASK-4.6:completed"
```

## Overview

Phase 4 adds a TTL-based in-memory cache for collection artifact counts. This provides sustained performance beyond the query optimization by reducing database hits for frequently-accessed count data. The cache uses a 5-minute TTL with explicit invalidation on mutation operations.

**Estimated Duration**: 2-3 hours
**Risk**: Low (additive change)
**Dependencies**: Phase 3 complete (CollectionService must exist)

## Tasks

### TASK-4.1: Implement Collection Count Cache

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 1h
**Priority**: high
**Model**: opus

**Description**: Create `cache/collection_cache.py` with TTL-based in-memory cache for collection artifact counts

**Requirements**:
- Cache class with get_counts(), set_counts(), invalidate(), invalidate_all()
- 5-minute TTL (DEFAULT_TTL = 300)
- Thread-safe with Lock
- Returns (cached_counts, missing_ids) tuple from get_counts
- Singleton pattern with get_collection_count_cache()
- get_stats() for monitoring

**Files**:
- `skillmeat/cache/collection_cache.py` (NEW)

**Key Implementation Notes**:
- Use `threading.Lock` for thread safety
- Store tuple of (count, timestamp) for TTL checking
- Lazy expiration (check on read, not background cleanup)

---

### TASK-4.2: Integrate Cache with CollectionService

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-4.1

**Description**: Update CollectionService to use cache for count lookups

**Requirements**:
- Cache hit rate logged (debug level)
- Fallback to DB on miss
- Cache populated after DB query
- No breaking changes to service interface

**Files**:
- `skillmeat/api/services/collection_service.py`: Integrate cache

---

### TASK-4.3: Add Cache Invalidation on Add Artifact

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-4.1

**Description**: Invalidate cache on `POST /api/v1/user-collections/{id}/artifacts`

**Requirements**:
- Cache invalidated when artifact added to collection
- Invalidation happens after successful database commit

**Files**:
- `skillmeat/api/routers/user_collections.py`: Add invalidation call

---

### TASK-4.4: Add Cache Invalidation on Remove Artifact

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-4.1

**Description**: Invalidate cache on `DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id}`

**Requirements**:
- Cache invalidated when artifact removed from collection
- Invalidation happens after successful database commit

**Files**:
- `skillmeat/api/routers/user_collections.py`: Add invalidation call

---

### TASK-4.5: Add Cache Invalidation on Delete Collection

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.25h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-4.1

**Description**: Invalidate cache on `DELETE /api/v1/user-collections/{id}`

**Requirements**:
- Cache invalidated when collection deleted
- Invalidation happens after successful database commit

**Files**:
- `skillmeat/api/routers/user_collections.py`: Add invalidation call

---

### TASK-4.6: Add Cache Unit Tests

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: medium
**Model**: sonnet
**Dependencies**: TASK-4.1

**Description**: Create tests for cache behavior including TTL expiration

**Requirements**:
- Tests cover get, set, invalidate, invalidate_all
- Tests verify TTL expiration
- Tests verify concurrent access patterns
- >80% coverage

**Files**:
- `tests/cache/test_collection_cache.py` (NEW)

---

## Quality Gates

- [ ] Cache class created with thread-safe operations
- [ ] TTL expiration working (verified via tests)
- [ ] Cache invalidation triggered on add/remove/delete operations
- [ ] Cache hit rate visible in logs
- [ ] No stale data visible after invalidation events
- [ ] Cache unit tests achieve >80% coverage

## Key Files Modified

- `skillmeat/cache/collection_cache.py` (NEW)
- `skillmeat/api/services/collection_service.py`
- `skillmeat/api/routers/user_collections.py`
- `tests/cache/test_collection_cache.py` (NEW)
