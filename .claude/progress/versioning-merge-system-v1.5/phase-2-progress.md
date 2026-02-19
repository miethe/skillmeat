---
type: progress
prd: versioning-merge-system-v1.5
phase: 2
title: Version Lineage Tracking
status: completed
created: 2025-12-17
updated: 2025-12-17
completed_at: 2025-12-17
duration_estimate: 1-2 days
effort_estimate: 8-16h
priority: HIGH
tasks:
- id: TASK-2.1
  description: Add database migration for change_origin enum column
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1-2h
  priority: HIGH
  commit: bf021c6
  files:
  - skillmeat/cache/migrations/versions/20251217_1500_add_artifact_versions.py
- id: TASK-2.2
  description: Update ArtifactVersion model with change_origin field
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 1-2h
  priority: HIGH
  commit: bf021c6
  files:
  - skillmeat/cache/models.py
- id: TASK-2.3
  description: Populate parent_hash on deployment (parent=NULL)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 2-3h
  priority: HIGH
  commit: bf021c6
  files:
  - skillmeat/core/deployment.py
  - skillmeat/core/version_tracking.py
- id: TASK-2.4
  description: Populate parent_hash on sync (parent=previous hash)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 2-3h
  priority: HIGH
  commit: bf021c6
  files:
  - skillmeat/core/sync.py
- id: TASK-2.5
  description: Populate version_lineage array
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 2-4h
  priority: HIGH
  commit: bf021c6
  files:
  - skillmeat/core/version_lineage.py
- id: TASK-2.6
  description: Add database indexes on content_hash and parent_hash
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 1-2h
  priority: MEDIUM
  commit: bf021c6
  files:
  - skillmeat/cache/migrations/versions/20251217_1500_add_artifact_versions.py
- id: TASK-2.7
  description: Write unit tests for version chain creation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 2-4h
  priority: HIGH
  commit: bf021c6
  files:
  - tests/test_version_lineage.py
  - tests/core/test_version_lineage_utils.py
  - tests/unit/test_version_tracking.py
  - tests/unit/test_deployment_version_integration.py
  - tests/unit/test_sync_version_creation.py
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
  - TASK-2.6
  - TASK-2.7
completion: 100%
schema_version: 2
doc_type: progress
feature_slug: versioning-merge-system-v1-5
---

# Phase 2: Version Lineage Tracking

## Overview

Implement version lineage tracking to build a complete version chain for each artifact. Track parent-child relationships between versions and capture the origin of each change (deployment, sync, local modification).

**Goal**: Build a complete version history graph with change attribution.

**Duration**: 1-2 days | **Effort**: 8-16h | **Priority**: HIGH

---

## Tasks

### TASK-2.1: Add database migration for change_origin enum column
**Status**: Pending | **Effort**: 1-2h | **Priority**: HIGH

**Description**:
Create Alembic migration to add `change_origin` enum column to `artifact_versions` table. Enum values: `deployment`, `sync`, `local_modification`.

**Files**:
- `alembic/versions/XXX_add_change_origin.py`

**Migration Steps**:
1. Add `change_origin` enum type
2. Add `change_origin` column (nullable, for backwards compatibility)
3. Add indexes on `content_hash` and `parent_hash`

**Acceptance Criteria**:
- [ ] Migration created and tested
- [ ] Enum type created with correct values
- [ ] Column added (nullable)
- [ ] Indexes created
- [ ] Migration reversible (downgrade works)

---

### TASK-2.2: Update ArtifactVersion model with change_origin field
**Status**: Pending | **Effort**: 1-2h | **Priority**: HIGH

**Description**:
Update SQLAlchemy model for `ArtifactVersion` to include `change_origin` field with proper enum type and validation.

**Files**:
- `skillmeat/storage/models.py`

**Acceptance Criteria**:
- [ ] `change_origin` field added to model
- [ ] Enum type mapped correctly
- [ ] Field is nullable (backwards compatibility)
- [ ] Validation prevents invalid enum values

**Dependencies**: TASK-2.1 (migration must run first)

---

### TASK-2.3: Populate parent_hash on deployment (parent=NULL)
**Status**: Pending | **Effort**: 2-3h | **Priority**: HIGH

**Description**:
Update deployment logic to create `ArtifactVersion` record with `parent_hash=NULL` and `change_origin='deployment'` when an artifact is first deployed.

**Files**:
- `skillmeat/storage/deployment.py`
- `skillmeat/core/deployment.py`

**Logic**:
```python
# On deploy_artifact()
version = ArtifactVersion(
    content_hash=compute_hash(artifact),
    parent_hash=None,  # No parent (root version)
    change_origin='deployment',
    version_lineage=[compute_hash(artifact)],
    ...
)
```

**Acceptance Criteria**:
- [ ] ArtifactVersion created on deployment
- [ ] `parent_hash` is NULL for deployments
- [ ] `change_origin` is 'deployment'
- [ ] `version_lineage` contains only the current hash

**Dependencies**: TASK-2.1 (migration must run first)

---

### TASK-2.4: Populate parent_hash on sync (parent=previous hash)
**Status**: Pending | **Effort**: 2-3h | **Priority**: HIGH

**Description**:
Update sync logic to create `ArtifactVersion` record with `parent_hash=<previous_version_hash>` and `change_origin='sync'` when syncing changes from upstream.

**Files**:
- `skillmeat/core/sync.py`

**Logic**:
```python
# On sync_artifact()
current_hash = get_deployed_artifact_hash(artifact_id)
new_hash = compute_hash(upstream_artifact)

version = ArtifactVersion(
    content_hash=new_hash,
    parent_hash=current_hash,  # Parent is previous deployed version
    change_origin='sync',
    version_lineage=parent.version_lineage + [new_hash],
    ...
)
```

**Acceptance Criteria**:
- [ ] ArtifactVersion created on sync
- [ ] `parent_hash` set to previous deployed hash
- [ ] `change_origin` is 'sync'
- [ ] `version_lineage` extends parent lineage

**Dependencies**: TASK-2.1 (migration must run first)

---

### TASK-2.5: Populate version_lineage array
**Status**: Pending | **Effort**: 2-4h | **Priority**: HIGH

**Description**:
Implement logic to build and maintain `version_lineage` array by walking parent chain. Array should contain all ancestor hashes in chronological order.

**Files**:
- `skillmeat/storage/snapshot.py`
- `skillmeat/core/sync.py`

**Logic**:
```python
def build_version_lineage(parent_hash: Optional[str], current_hash: str) -> list[str]:
    """Build version lineage by walking parent chain."""
    if parent_hash is None:
        return [current_hash]  # Root version

    parent = get_version_by_hash(parent_hash)
    return parent.version_lineage + [current_hash]
```

**Acceptance Criteria**:
- [ ] Lineage built correctly for deployments (single hash)
- [ ] Lineage built correctly for syncs (parent + current)
- [ ] Lineage built correctly for local mods (parent + current)
- [ ] Efficient query (use cached parent lineage)

**Dependencies**: TASK-2.1 (migration must run first)

---

### TASK-2.6: Add database indexes on content_hash and parent_hash
**Status**: Pending | **Effort**: 1-2h | **Priority**: MEDIUM

**Description**:
Add database indexes to optimize queries for version chain traversal and common ancestor searches.

**Files**:
- `alembic/versions/XXX_add_change_origin.py`

**Indexes**:
1. `idx_artifact_versions_content_hash` - for snapshot lookups
2. `idx_artifact_versions_parent_hash` - for parent chain queries
3. Composite index on `(artifact_id, created_at)` - for timeline queries

**Acceptance Criteria**:
- [ ] Indexes created in migration
- [ ] Query performance improved (benchmark)
- [ ] No negative impact on write performance

**Dependencies**: TASK-2.1 (part of same migration)

---

### TASK-2.7: Write unit tests for version chain creation
**Status**: Pending | **Effort**: 2-4h | **Priority**: HIGH

**Description**:
Write comprehensive unit tests covering version chain creation, lineage building, and change origin tracking.

**Files**:
- `tests/test_version_lineage.py`

**Test Cases**:
1. Deploy artifact → parent=NULL, change_origin='deployment'
2. Sync artifact → parent=previous, change_origin='sync'
3. Local modification → parent=previous, change_origin='local_modification'
4. Version lineage builds correctly (3+ versions)
5. Version chain traversal works (find common ancestor)

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] >80% coverage for new code
- [ ] Edge cases tested (orphaned versions, cycles)

**Dependencies**: TASK-2.1 (migration must run first)

---

## Orchestration Quick Reference

**Batch 1** (Sequential - Migration First):
- TASK-2.1 → `python-backend-engineer` (1-2h)

**Batch 2** (All Parallel After Migration):
- TASK-2.2 → `python-backend-engineer` (1-2h)
- TASK-2.3 → `python-backend-engineer` (2-3h)
- TASK-2.4 → `python-backend-engineer` (2-3h)
- TASK-2.5 → `python-backend-engineer` (2-4h)
- TASK-2.6 → `python-backend-engineer` (1-2h)
- TASK-2.7 → `python-backend-engineer` (2-4h)

### Task Delegation Commands

```python
# Batch 1: Migration (MUST complete first)
Task("python-backend-engineer", """TASK-2.1: Add database migration for change_origin enum column

Files:
- alembic/versions/XXX_add_change_origin.py

Migration Steps:
1. Create enum type: ('deployment', 'sync', 'local_modification')
2. Add change_origin column to artifact_versions (nullable)
3. Add indexes:
   - idx_artifact_versions_content_hash
   - idx_artifact_versions_parent_hash
   - idx_artifact_versions_artifact_created (composite)

Requirements:
- Migration must be reversible
- Use Alembic best practices
- Test upgrade/downgrade

Acceptance:
- Migration runs successfully
- Indexes created
- Downgrade works
""")

# Batch 2: After migration (all parallel)
Task("python-backend-engineer", """TASK-2.2: Update ArtifactVersion model with change_origin field

Files:
- skillmeat/storage/models.py

Requirements:
- Add change_origin field (Enum type)
- Field is nullable (backwards compatibility)
- Map to database enum type
- Validation prevents invalid values

Depends on: TASK-2.1 (migration)

Acceptance:
- Model updated
- Enum mapped correctly
- Validation works
""")

Task("python-backend-engineer", """TASK-2.3: Populate parent_hash on deployment (parent=NULL)

Files:
- skillmeat/storage/deployment.py
- skillmeat/core/deployment.py

Requirements:
- Create ArtifactVersion on deployment
- Set parent_hash=NULL (root version)
- Set change_origin='deployment'
- Set version_lineage=[current_hash]

Depends on: TASK-2.1 (migration)

Acceptance:
- Version created on deploy
- Parent is NULL
- Change origin is correct
""")

Task("python-backend-engineer", """TASK-2.4: Populate parent_hash on sync (parent=previous hash)

Files:
- skillmeat/core/sync.py

Requirements:
- Create ArtifactVersion on sync
- Set parent_hash=<previous_deployed_hash>
- Set change_origin='sync'
- Extend version_lineage from parent

Depends on: TASK-2.1 (migration)

Acceptance:
- Version created on sync
- Parent is previous hash
- Lineage extends correctly
""")

Task("python-backend-engineer", """TASK-2.5: Populate version_lineage array

Files:
- skillmeat/storage/snapshot.py
- skillmeat/core/sync.py

Requirements:
- Implement build_version_lineage() function
- Walk parent chain to build lineage
- Handle root versions (parent=NULL)
- Use cached parent lineage (don't re-walk)

Depends on: TASK-2.1 (migration)

Acceptance:
- Lineage built correctly
- Efficient (uses parent cache)
- Handles all edge cases
""")

Task("python-backend-engineer", """TASK-2.6: Add database indexes on content_hash and parent_hash

Files:
- alembic/versions/XXX_add_change_origin.py (part of TASK-2.1)

Requirements:
- Add indexes in migration:
  - content_hash (for snapshot lookups)
  - parent_hash (for parent chain queries)
  - (artifact_id, created_at) composite

Depends on: TASK-2.1 (same migration)

Acceptance:
- Indexes created
- Query performance improved
- No write regression
""")

Task("python-backend-engineer", """TASK-2.7: Write unit tests for version chain creation

Files:
- tests/test_version_lineage.py

Test Cases:
1. Deploy → parent=NULL, origin='deployment'
2. Sync → parent=previous, origin='sync'
3. Local mod → parent=previous, origin='local_modification'
4. Lineage builds correctly (3+ versions)
5. Common ancestor search works

Depends on: TASK-2.1 (migration)

Coverage:
- >80% for new code
- All edge cases
""")
```

---

## Success Criteria

- [ ] All tasks completed
- [ ] Database migration runs successfully
- [ ] Version chain built for all operations (deploy, sync, local mod)
- [ ] `change_origin` tracked correctly
- [ ] Indexes improve query performance
- [ ] Unit tests pass (>80% coverage)

---

## Dependencies

**Blocks**:
- Phase 3 (Modification Tracking) - needs version lineage to track local mods
- Phase 4 (Change Attribution) - needs change_origin to attribute changes

**Blocked By**:
- Phase 1 (Core Baseline Support) - needs baseline storage working

---

## Notes

**Key Insight**: Version lineage is built incrementally by extending parent's lineage + current hash. This avoids expensive graph traversal.

**Performance**: Indexes on `content_hash` and `parent_hash` are critical for common ancestor searches during three-way merge.

**Backwards Compatibility**: `change_origin` is nullable to support old versions created before v1.5. Default to NULL for unknown origin.
