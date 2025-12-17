---
type: progress
prd: versioning-merge-system-v1.5
phase: 3-4
title: "Modification Tracking & Change Attribution"
status: pending
created: 2025-12-17
updated: 2025-12-17
duration_estimate: "2-3 days"
effort_estimate: "14-20h"
priority: MEDIUM

tasks:
  # Phase 3: Modification Tracking Enhancement
  - id: "TASK-3.1"
    description: "Update detect_drift() to set modification_detected_at"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/core/sync.py"

  - id: "TASK-3.2"
    description: "Create ArtifactVersion record for local modifications"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/core/sync.py"
      - "skillmeat/storage/snapshot.py"

  - id: "TASK-3.3"
    description: "Update DriftDetection schema with attribution fields"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1-2h"
    priority: "MEDIUM"
    files:
      - "skillmeat/api/app/schemas/drift.py"

  - id: "TASK-3.4"
    description: "Add API response fields (change_origin, baseline_hash, current_hash)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1-2h"
    priority: "MEDIUM"
    files:
      - "skillmeat/api/app/routers/sync.py"

  - id: "TASK-3.5"
    description: "Write unit tests for modification timestamp setting"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "tests/test_modification_tracking.py"

  # Phase 4: Change Attribution Logic
  - id: "TASK-4.1"
    description: "Implement determine_change_origin() function"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.1", "TASK-3.2"]
    estimated_effort: "3-4h"
    priority: "MEDIUM"
    files:
      - "skillmeat/core/sync.py"

  - id: "TASK-4.2"
    description: "Update drift detection API to return change_origin per file"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/api/app/routers/sync.py"

  - id: "TASK-4.3"
    description: "Add summary counts (upstream_changes, local_changes, conflicts)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimated_effort: "1-2h"
    priority: "MEDIUM"
    files:
      - "skillmeat/api/app/schemas/drift.py"

  - id: "TASK-4.4"
    description: "Add change attribution to diff API responses"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/api/app/routers/sync.py"

  - id: "TASK-4.5"
    description: "Write unit tests for all change origin scenarios"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimated_effort: "3-4h"
    priority: "MEDIUM"
    files:
      - "tests/test_change_attribution.py"

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.2", "TASK-3.3", "TASK-3.4", "TASK-3.5"]
  batch_2: ["TASK-4.1"]
  batch_3: ["TASK-4.2", "TASK-4.3", "TASK-4.4", "TASK-4.5"]

completion: 0%
---

# Phase 3-4: Modification Tracking & Change Attribution

## Overview

Enhance modification tracking to capture when local changes occur and implement change attribution logic to distinguish between upstream changes, local changes, and conflicts.

**Phase 3 Goal**: Track local modifications with timestamps and version records.

**Phase 4 Goal**: Implement logic to determine change origin for each file in drift detection.

**Duration**: 2-3 days | **Effort**: 14-20h | **Priority**: MEDIUM

---

## Phase 3 Tasks: Modification Tracking Enhancement

### TASK-3.1: Update detect_drift() to set modification_detected_at
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Update `detect_drift()` to set `modification_detected_at` timestamp in deployment metadata when local changes are detected. This timestamp marks when the system first observed the modification.

**Files**:
- `skillmeat/core/sync.py`

**Logic**:
```python
# In detect_drift()
if drift_detected and not deployment.modification_detected_at:
    deployment.modification_detected_at = datetime.utcnow()
    update_deployment_metadata(deployment)
```

**Acceptance Criteria**:
- [ ] Timestamp set on first drift detection
- [ ] Timestamp not updated on subsequent detections
- [ ] Timestamp persisted in deployment metadata
- [ ] Timestamp accessible via API

---

### TASK-3.2: Create ArtifactVersion record for local modifications
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
When local modifications are detected, create an `ArtifactVersion` record with `change_origin='local_modification'` and `parent_hash=<deployed_version_hash>`.

**Files**:
- `skillmeat/core/sync.py`
- `skillmeat/storage/snapshot.py`

**Logic**:
```python
# In detect_drift()
if drift_detected:
    local_hash = compute_hash(local_artifact)
    deployed_hash = deployment.merge_base_snapshot

    version = ArtifactVersion(
        content_hash=local_hash,
        parent_hash=deployed_hash,
        change_origin='local_modification',
        version_lineage=build_lineage(deployed_hash, local_hash),
        created_at=datetime.utcnow()
    )
    save_version(version)
```

**Acceptance Criteria**:
- [ ] Version created when drift detected
- [ ] `parent_hash` set to deployed version
- [ ] `change_origin` is 'local_modification'
- [ ] Version lineage built correctly
- [ ] No duplicate versions (idempotent)

---

### TASK-3.3: Update DriftDetection schema with attribution fields
**Status**: Pending | **Effort**: 1-2h | **Priority**: MEDIUM

**Description**:
Add attribution fields to `DriftDetection` Pydantic schema to include change origin, baseline hash, and current hash in API responses.

**Files**:
- `skillmeat/api/app/schemas/drift.py`

**New Fields**:
```python
class DriftDetection(BaseModel):
    # Existing fields
    has_drift: bool
    modified_files: list[str]

    # New attribution fields
    change_origin: Optional[str] = None  # 'local', 'upstream', 'both'
    baseline_hash: Optional[str] = None  # Merge base hash
    current_hash: Optional[str] = None   # Current deployed hash
    modification_detected_at: Optional[datetime] = None
```

**Acceptance Criteria**:
- [ ] Schema updated with new fields
- [ ] Fields are optional (backwards compatibility)
- [ ] OpenAPI spec updated
- [ ] Validation works

---

### TASK-3.4: Add API response fields (change_origin, baseline_hash, current_hash)
**Status**: Pending | **Effort**: 1-2h | **Priority**: MEDIUM

**Description**:
Update drift detection API endpoint to populate new attribution fields in response.

**Files**:
- `skillmeat/api/app/routers/sync.py`

**Acceptance Criteria**:
- [ ] API returns new fields
- [ ] Baseline hash from deployment metadata
- [ ] Current hash from deployed artifact
- [ ] Change origin calculated (Phase 4)

---

### TASK-3.5: Write unit tests for modification timestamp setting
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Write unit tests for modification detection timestamp and version record creation.

**Files**:
- `tests/test_modification_tracking.py`

**Test Cases**:
1. Drift detected → timestamp set
2. Timestamp not updated on re-detection
3. ArtifactVersion created with correct parent
4. Version lineage built correctly
5. Idempotent (no duplicate versions)

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] >80% coverage for new code

---

## Phase 4 Tasks: Change Attribution Logic

### TASK-4.1: Implement determine_change_origin() function
**Status**: Pending | **Effort**: 3-4h | **Priority**: MEDIUM

**Description**:
Implement logic to determine change origin for each file by comparing baseline, deployed, and upstream versions.

**Files**:
- `skillmeat/core/sync.py`

**Logic**:
```python
def determine_change_origin(
    baseline_content: str,
    deployed_content: str,
    upstream_content: str
) -> str:
    """Determine change origin: 'upstream', 'local', 'both', or 'none'."""

    baseline_eq_deployed = baseline_content == deployed_content
    baseline_eq_upstream = baseline_content == upstream_content
    deployed_eq_upstream = deployed_content == upstream_content

    if deployed_eq_upstream:
        return 'none'  # No changes
    elif baseline_eq_deployed and not baseline_eq_upstream:
        return 'upstream'  # Only upstream changed
    elif baseline_eq_upstream and not baseline_eq_deployed:
        return 'local'  # Only local changed
    else:
        return 'both'  # Both changed (conflict)
```

**Acceptance Criteria**:
- [ ] Function implemented
- [ ] Handles all 4 scenarios (none, upstream, local, both)
- [ ] Efficient (uses hash comparison first, then content)
- [ ] Unit tested

**Dependencies**: TASK-3.1, TASK-3.2 (needs modification tracking)

---

### TASK-4.2: Update drift detection API to return change_origin per file
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Update drift detection API to call `determine_change_origin()` for each file and return change origin in response.

**Files**:
- `skillmeat/api/app/routers/sync.py`

**Response Format**:
```json
{
  "has_drift": true,
  "files": [
    {
      "path": "SKILL.md",
      "status": "modified",
      "change_origin": "local"
    },
    {
      "path": "scripts/example.js",
      "status": "modified",
      "change_origin": "upstream"
    }
  ]
}
```

**Acceptance Criteria**:
- [ ] API returns change_origin per file
- [ ] Change origin calculated correctly
- [ ] Performance acceptable (batch hashing)

**Dependencies**: TASK-4.1 (needs determine_change_origin())

---

### TASK-4.3: Add summary counts (upstream_changes, local_changes, conflicts)
**Status**: Pending | **Effort**: 1-2h | **Priority**: MEDIUM

**Description**:
Add summary counts to drift detection response showing breakdown of change origins.

**Files**:
- `skillmeat/api/app/schemas/drift.py`

**New Fields**:
```python
class DriftDetection(BaseModel):
    # ...
    summary: DriftSummary

class DriftSummary(BaseModel):
    total_files: int
    upstream_changes: int
    local_changes: int
    conflicts: int  # Both changed
    no_changes: int
```

**Acceptance Criteria**:
- [ ] Summary counts accurate
- [ ] Counts sum to total_files
- [ ] Schema updated

**Dependencies**: TASK-4.1 (needs determine_change_origin())

---

### TASK-4.4: Add change attribution to diff API responses
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Update diff API endpoint to include change origin information in file-level diff responses.

**Files**:
- `skillmeat/api/app/routers/sync.py`

**Response Enhancement**:
```json
{
  "path": "SKILL.md",
  "diff": "...",
  "change_origin": "local",
  "baseline_hash": "abc123",
  "deployed_hash": "def456",
  "upstream_hash": "def456"
}
```

**Acceptance Criteria**:
- [ ] Diff API returns change origin
- [ ] Hashes included for debugging
- [ ] Schema updated

**Dependencies**: TASK-4.1 (needs determine_change_origin())

---

### TASK-4.5: Write unit tests for all change origin scenarios
**Status**: Pending | **Effort**: 3-4h | **Priority**: MEDIUM

**Description**:
Write comprehensive unit tests covering all change origin scenarios (upstream, local, both, none).

**Files**:
- `tests/test_change_attribution.py`

**Test Scenarios**:
1. **Upstream only**: Baseline == Deployed, Baseline != Upstream → 'upstream'
2. **Local only**: Baseline == Upstream, Baseline != Deployed → 'local'
3. **Both (conflict)**: All different → 'both'
4. **None**: All same → 'none'
5. **Edge cases**: Missing files, binary files

**Acceptance Criteria**:
- [ ] All scenarios tested
- [ ] >80% coverage
- [ ] Edge cases handled

**Dependencies**: TASK-4.1 (needs determine_change_origin())

---

## Orchestration Quick Reference

**Batch 1** (All Parallel - Phase 3):
- TASK-3.1 → `python-backend-engineer` (2-3h)
- TASK-3.2 → `python-backend-engineer` (2-3h)
- TASK-3.3 → `python-backend-engineer` (1-2h)
- TASK-3.4 → `python-backend-engineer` (1-2h)
- TASK-3.5 → `python-backend-engineer` (2-3h)

**Batch 2** (Sequential - Core Logic):
- TASK-4.1 → `python-backend-engineer` (3-4h)

**Batch 3** (All Parallel - Phase 4 Features):
- TASK-4.2 → `python-backend-engineer` (2-3h)
- TASK-4.3 → `python-backend-engineer` (1-2h)
- TASK-4.4 → `python-backend-engineer` (2-3h)
- TASK-4.5 → `python-backend-engineer` (3-4h)

### Task Delegation Commands

```python
# Batch 1: Phase 3 (all parallel)
Task("python-backend-engineer", """TASK-3.1: Update detect_drift() to set modification_detected_at

Files:
- skillmeat/core/sync.py

Requirements:
- Set modification_detected_at timestamp on first drift detection
- Don't update on subsequent detections
- Persist in deployment metadata

Acceptance:
- Timestamp set correctly
- Only set once
- Persisted and retrievable
""")

Task("python-backend-engineer", """TASK-3.2: Create ArtifactVersion record for local modifications

Files:
- skillmeat/core/sync.py
- skillmeat/storage/snapshot.py

Requirements:
- Create ArtifactVersion when drift detected
- Set parent_hash to deployed version
- Set change_origin='local_modification'
- Build version lineage correctly
- Idempotent (no duplicates)

Acceptance:
- Version created on drift
- Parent and origin correct
- Lineage accurate
""")

Task("python-backend-engineer", """TASK-3.3: Update DriftDetection schema with attribution fields

Files:
- skillmeat/api/app/schemas/drift.py

New Fields:
- change_origin (Optional[str])
- baseline_hash (Optional[str])
- current_hash (Optional[str])
- modification_detected_at (Optional[datetime])

Requirements:
- Add fields to schema
- Fields are optional
- Update OpenAPI spec

Acceptance:
- Schema updated
- Validation works
""")

Task("python-backend-engineer", """TASK-3.4: Add API response fields (change_origin, baseline_hash, current_hash)

Files:
- skillmeat/api/app/routers/sync.py

Requirements:
- Populate new fields in drift detection response
- Baseline from deployment metadata
- Current hash from deployed artifact
- Change origin (Phase 4)

Acceptance:
- API returns new fields
- Values correct
""")

Task("python-backend-engineer", """TASK-3.5: Write unit tests for modification timestamp setting

Files:
- tests/test_modification_tracking.py

Test Cases:
1. Drift detected → timestamp set
2. Re-detection → timestamp unchanged
3. ArtifactVersion created
4. Lineage correct
5. Idempotent

Coverage: >80%
""")

# Batch 2: Core attribution logic (sequential)
Task("python-backend-engineer", """TASK-4.1: Implement determine_change_origin() function

Files:
- skillmeat/core/sync.py

Logic:
Compare baseline, deployed, upstream to determine:
- 'upstream': Only upstream changed
- 'local': Only local changed
- 'both': Both changed (conflict)
- 'none': No changes

Requirements:
- Implement function
- Handle all 4 scenarios
- Efficient (use hash comparison)
- Unit tested

Depends on: TASK-3.1, TASK-3.2

Acceptance:
- Function works for all scenarios
- Efficient
- Tested
""")

# Batch 3: Phase 4 features (all parallel after TASK-4.1)
Task("python-backend-engineer", """TASK-4.2: Update drift detection API to return change_origin per file

Files:
- skillmeat/api/app/routers/sync.py

Requirements:
- Call determine_change_origin() for each file
- Return change_origin in response
- Format: { path, status, change_origin }

Depends on: TASK-4.1

Acceptance:
- API returns change_origin per file
- Values correct
- Performance acceptable
""")

Task("python-backend-engineer", """TASK-4.3: Add summary counts (upstream_changes, local_changes, conflicts)

Files:
- skillmeat/api/app/schemas/drift.py

New Schema:
class DriftSummary(BaseModel):
    total_files: int
    upstream_changes: int
    local_changes: int
    conflicts: int

Depends on: TASK-4.1

Acceptance:
- Summary counts accurate
- Counts sum correctly
""")

Task("python-backend-engineer", """TASK-4.4: Add change attribution to diff API responses

Files:
- skillmeat/api/app/routers/sync.py

Enhancement:
Add change_origin, baseline_hash, deployed_hash, upstream_hash to diff responses

Depends on: TASK-4.1

Acceptance:
- Diff API returns attribution
- Hashes included
- Schema updated
""")

Task("python-backend-engineer", """TASK-4.5: Write unit tests for all change origin scenarios

Files:
- tests/test_change_attribution.py

Test Scenarios:
1. Upstream only
2. Local only
3. Both (conflict)
4. None
5. Edge cases (missing files, binary)

Depends on: TASK-4.1

Coverage: >80%
""")
```

---

## Success Criteria

- [ ] All tasks completed
- [ ] Modification timestamps tracked
- [ ] Change origin determined for all files
- [ ] API returns attribution information
- [ ] Summary counts accurate
- [ ] Unit tests pass (>80% coverage)

---

## Dependencies

**Blocks**:
- Phase 5 (Web UI Integration) - needs API to return change_origin

**Blocked By**:
- Phase 1 (Core Baseline Support) - needs baseline storage
- Phase 2 (Version Lineage Tracking) - needs change_origin field

---

## Notes

**Key Algorithm**: `determine_change_origin()` uses three-way comparison to attribute changes to upstream, local, or both (conflict).

**Performance**: Use hash comparison before content comparison for efficiency.

**UI Impact**: Change origin badges will be shown in diff viewer and version timeline (Phase 5).
