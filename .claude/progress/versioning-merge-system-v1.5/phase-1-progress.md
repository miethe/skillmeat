---
type: progress
prd: versioning-merge-system-v1.5
phase: 1
title: Core Baseline Support (Fix Three-Way Merge)
status: completed
created: 2025-12-17
updated: 2025-12-17
completed_at: 2025-12-17
duration_estimate: 2-3 days
effort_estimate: 16-24h
priority: HIGH
tasks:
- id: TASK-1.1
  description: Add merge_base_snapshot field to deployment metadata schema
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3-4h
  priority: HIGH
  files:
  - skillmeat/core/deployment.py
  - skillmeat/api/schemas/deployments.py
- id: TASK-1.2
  description: Update deploy_artifact() to store baseline hash on deployment
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3-4h
  priority: HIGH
  files:
  - skillmeat/storage/deployment.py
  - skillmeat/core/deployment.py
- id: TASK-1.3
  description: Modify three_way_merge() to retrieve baseline from metadata
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 4-6h
  priority: HIGH
  files:
  - skillmeat/core/sync.py
  - skillmeat/storage/snapshot.py
- id: TASK-1.4
  description: Add fallback logic for old deployments (no baseline)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3-4h
  priority: HIGH
  files:
  - skillmeat/core/sync.py
- id: TASK-1.5
  description: Write unit tests for merge base retrieval
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3-6h
  priority: HIGH
  files:
  - tests/test_three_way_merge.py
  - tests/test_deployment_baseline.py
  - tests/test_sync_merge_fallback.py
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
completion: 100%
schema_version: 2
doc_type: progress
feature_slug: versioning-merge-system-v1-5
---

# Phase 1: Core Baseline Support (Fix Three-Way Merge)

## Overview

Fix the three-way merge algorithm by properly tracking the merge base (baseline) snapshot. Currently, the system defaults to empty baseline when retrieving merge base from deployment metadata, causing incorrect conflict detection.

**Goal**: Store and retrieve the correct baseline hash for three-way merges.

**Duration**: 2-3 days | **Effort**: 16-24h | **Priority**: HIGH

---

## Tasks

### TASK-1.1: Add merge_base_snapshot field to deployment metadata schema
**Status**: Pending | **Effort**: 3-4h | **Priority**: HIGH

**Description**:
Add `merge_base_snapshot` field to deployment metadata schema to store the content hash of the artifact at deployment time. This becomes the baseline for future three-way merges.

**Files**:
- `skillmeat/storage/deployment.py` - Update metadata schema
- `skillmeat/storage/models.py` - Update DeploymentMetadata model if needed

**Acceptance Criteria**:
- [ ] `merge_base_snapshot` field added to metadata schema
- [ ] Field is optional (for backwards compatibility)
- [ ] Field stores content hash (SHA-256)
- [ ] Schema validation passes

---

### TASK-1.2: Update deploy_artifact() to store baseline hash on deployment
**Status**: Pending | **Effort**: 3-4h | **Priority**: HIGH

**Description**:
Modify `deploy_artifact()` to compute and store the content hash of the deployed artifact as `merge_base_snapshot` in deployment metadata.

**Files**:
- `skillmeat/storage/deployment.py` - Update deploy_artifact()
- `skillmeat/core/deployment.py` - Add hash computation logic

**Acceptance Criteria**:
- [ ] Content hash computed during deployment
- [ ] Hash stored in `merge_base_snapshot` field
- [ ] Hash matches deployed artifact content
- [ ] No performance regression (hash computation is fast)

---

### TASK-1.3: Modify three_way_merge() to retrieve baseline from metadata
**Status**: Pending | **Effort**: 4-6h | **Priority**: HIGH

**Description**:
Update `three_way_merge()` to retrieve the merge base snapshot from deployment metadata instead of using empty baseline. Implement proper snapshot retrieval by content hash.

**Files**:
- `skillmeat/core/sync.py` - Update three_way_merge()

**Acceptance Criteria**:
- [ ] Baseline retrieved from `merge_base_snapshot` field
- [ ] Snapshot loaded by content hash from version history
- [ ] Three-way merge uses correct baseline
- [ ] Merge algorithm produces correct conflict detection

---

### TASK-1.4: Add fallback logic for old deployments (no baseline)
**Status**: Pending | **Effort**: 3-4h | **Priority**: HIGH

**Description**:
Implement fallback logic for deployments created before v1.5 that don't have `merge_base_snapshot` field. Use heuristics to determine baseline (e.g., find common ancestor or use empty baseline with warning).

**Files**:
- `skillmeat/core/sync.py` - Add fallback logic
- `skillmeat/storage/deployment.py` - Add helper functions

**Acceptance Criteria**:
- [ ] Old deployments detected (no merge_base_snapshot)
- [ ] Fallback logic uses common ancestor search
- [ ] Warning logged when fallback is used
- [ ] Graceful degradation (no errors)

---

### TASK-1.5: Write unit tests for merge base retrieval
**Status**: Pending | **Effort**: 3-6h | **Priority**: HIGH

**Description**:
Write comprehensive unit tests for merge base retrieval, covering new deployments (with baseline), old deployments (without baseline), and edge cases.

**Files**:
- `tests/test_three_way_merge.py` - Test merge with correct baseline
- `tests/test_deployment_baseline.py` - Test baseline storage/retrieval

**Test Cases**:
- [ ] Deploy artifact → baseline stored
- [ ] Sync with baseline → correct merge
- [ ] Old deployment (no baseline) → fallback works
- [ ] Missing snapshot → graceful error
- [ ] Baseline mismatch → warning logged

---

## Orchestration Quick Reference

**Batch 1** (All Parallel - No Dependencies):
- TASK-1.1 → `python-backend-engineer` (3-4h)
- TASK-1.2 → `python-backend-engineer` (3-4h)
- TASK-1.3 → `python-backend-engineer` (4-6h)
- TASK-1.4 → `python-backend-engineer` (3-4h)
- TASK-1.5 → `python-backend-engineer` (3-6h)

### Task Delegation Commands

```python
# Execute all tasks in parallel (batch 1)
Task("python-backend-engineer", """TASK-1.1: Add merge_base_snapshot field to deployment metadata schema

Files:
- skillmeat/storage/deployment.py
- skillmeat/storage/models.py

Requirements:
- Add merge_base_snapshot (optional string field) to deployment metadata schema
- Field stores content hash (SHA-256) of deployed artifact
- Must be backwards compatible (optional field)
- Update schema validation

Acceptance:
- Schema updated with new field
- Field is optional
- Validation passes
""")

Task("python-backend-engineer", """TASK-1.2: Update deploy_artifact() to store baseline hash on deployment

Files:
- skillmeat/storage/deployment.py
- skillmeat/core/deployment.py

Requirements:
- Compute content hash during deployment
- Store hash in merge_base_snapshot field
- Hash must match deployed artifact content exactly
- No performance regression

Acceptance:
- Hash computed and stored on every deployment
- Hash is accurate
- Fast execution
""")

Task("python-backend-engineer", """TASK-1.3: Modify three_way_merge() to retrieve baseline from metadata

Files:
- skillmeat/core/sync.py

Requirements:
- Retrieve baseline from merge_base_snapshot field in deployment metadata
- Load snapshot by content hash from version history
- Use retrieved baseline in three-way merge algorithm
- Proper error handling if baseline not found

Acceptance:
- Baseline retrieved correctly
- Three-way merge uses correct baseline
- Conflicts detected accurately
""")

Task("python-backend-engineer", """TASK-1.4: Add fallback logic for old deployments (no baseline)

Files:
- skillmeat/core/sync.py
- skillmeat/storage/deployment.py

Requirements:
- Detect old deployments (missing merge_base_snapshot)
- Implement fallback: search for common ancestor in version history
- Log warning when fallback is used
- Graceful degradation (no errors)

Acceptance:
- Old deployments work without errors
- Fallback logic finds reasonable baseline
- Warning logged
""")

Task("python-backend-engineer", """TASK-1.5: Write unit tests for merge base retrieval

Files:
- tests/test_three_way_merge.py
- tests/test_deployment_baseline.py

Test Cases:
1. New deployment stores baseline hash
2. Three-way merge retrieves correct baseline
3. Old deployment (no baseline) uses fallback
4. Missing snapshot handled gracefully
5. Baseline mismatch logs warning

Coverage:
- >80% coverage for new code
- All edge cases tested
""")
```

---

## Success Criteria

- [ ] All tasks completed
- [ ] Baseline hash stored on every new deployment
- [ ] Three-way merge retrieves correct baseline
- [ ] Old deployments work with fallback logic
- [ ] Unit tests pass (>80% coverage)
- [ ] No performance regression
- [ ] Documentation updated

---

## Dependencies

**Blocks**:
- Phase 2 (Version Lineage Tracking) - needs baseline storage working

**Blocked By**:
- None (this is the foundation)

---

## Notes

**Current Issue**: Three-way merge defaults to empty baseline, causing false conflicts.

**Root Cause**: Baseline not stored during deployment, retrieval fails.

**Fix**: Store baseline hash in deployment metadata, retrieve during merge.

**Backwards Compatibility**: Old deployments use fallback logic (common ancestor search).
