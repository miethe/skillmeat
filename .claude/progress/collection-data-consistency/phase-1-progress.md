---
type: progress
prd: "collection-data-consistency"
phase: 1
title: "Critical Performance Fix"
status: pending
started: null
completed: null
progress: 0

total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "TASK-1.1"
    title: "Fix N+1 COUNT Query Pattern"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    model: "opus"
    effort: "1.5h"
    priority: "critical"
    files:
      - "skillmeat/api/routers/artifacts.py"

  - id: "TASK-1.2"
    title: "Update Relationship Loading Strategy"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    model: "opus"
    effort: "0.5h"
    priority: "high"
    files:
      - "skillmeat/cache/models.py"

  - id: "TASK-1.3"
    title: "Add Query Performance Logging"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    model: "sonnet"
    effort: "0.5h"
    priority: "medium"
    files:
      - "skillmeat/api/routers/artifacts.py"

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2"]
  batch_2: ["TASK-1.3"]

blockers: []

success_criteria:
  - id: "SC-1.1"
    description: "API response time for 50-artifact list <200ms (p95)"
    status: "pending"
  - id: "SC-1.2"
    description: "Database queries per request <=5 (verified via logging)"
    status: "pending"
  - id: "SC-1.3"
    description: "Existing artifact list tests pass"
    status: "pending"
  - id: "SC-1.4"
    description: "No regression in artifact detail endpoint"
    status: "pending"
---

# Phase 1: Critical Performance Fix

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-data-consistency/phase-1-progress.md \
  -t TASK-1.1 -s completed

# Batch update after parallel execution
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-data-consistency/phase-1-progress.md \
  --updates "TASK-1.1:completed,TASK-1.2:completed"
```

## Overview

Phase 1 addresses the critical N+1 query pattern in the artifacts router that causes 100+ database queries per page load. This is the highest-priority fix with immediate performance impact. The fix replaces per-artifact COUNT queries with a single aggregation query using GROUP BY.

**Estimated Duration**: 2-3 hours
**Risk**: Low (isolated change)
**Dependencies**: None (can run parallel with Phase 2)

## Tasks

### TASK-1.1: Fix N+1 COUNT Query Pattern

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 1.5h
**Priority**: critical
**Model**: opus

**Description**: Replace per-artifact COUNT queries with single aggregation query using GROUP BY in `artifacts.py:1897-1916`

**Requirements**:
- Single COUNT query replaces 100+ individual queries
- API response time <200ms for 50 artifacts
- Use `func.count()` with GROUP BY pattern
- Build count_map dictionary for O(1) lookups

**Files**:
- `skillmeat/api/routers/artifacts.py`: Replace N+1 loop with batch aggregation

**Implementation Reference**:
```python
from sqlalchemy import func

count_query = (
    db_session.query(
        CollectionArtifact.collection_id,
        func.count(CollectionArtifact.artifact_id).label('artifact_count')
    )
    .filter(CollectionArtifact.collection_id.in_(collection_ids))
    .group_by(CollectionArtifact.collection_id)
    .all()
)
count_map = {row.collection_id: row.artifact_count for row in count_query}
```

---

### TASK-1.2: Update Relationship Loading Strategy

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: opus

**Description**: Change `lazy="selectin"` to `lazy="select"` on Artifact.collections, Collection.groups, Collection.collection_artifacts in `cache/models.py`

**Requirements**:
- Relationships load on-demand only
- No duplicate eager loading when manual queries used
- Verify no regressions in endpoints that rely on relationships

**Files**:
- `skillmeat/cache/models.py`: Update relationship lazy loading strategy

---

### TASK-1.3: Add Query Performance Logging

**Status**: `pending`
**Assigned**: python-backend-engineer
**Effort**: 0.5h
**Priority**: medium
**Model**: sonnet
**Dependencies**: TASK-1.1

**Description**: Add timing logs for artifact list endpoint to validate improvement

**Requirements**:
- Query count visible in logs for monitoring
- Timing metrics for before/after comparison
- Non-intrusive logging (debug level)

**Files**:
- `skillmeat/api/routers/artifacts.py`: Add performance logging

---

## Quality Gates

- [ ] API response time for 50-artifact list <200ms (p95)
- [ ] Database queries per request <=5 (verified via logging)
- [ ] Existing artifact list tests pass
- [ ] No regression in artifact detail endpoint
- [ ] Performance improvement documented in commit message

## Key Files Modified

- `skillmeat/api/routers/artifacts.py`
- `skillmeat/cache/models.py`
