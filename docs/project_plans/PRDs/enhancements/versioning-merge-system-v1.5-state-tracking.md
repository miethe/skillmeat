---
title: "PRD Addendum: Artifact State Origin Tracking (v1.5)"
description: "Content-addressable hash chain system for tracking artifact state changes and determining change origin (upstream vs local modifications)"
audience: [ai-agents, developers]
tags: [prd, planning, enhancement, versioning, merge, state-tracking, hashing]
created: 2025-12-17
updated: 2025-12-17
category: "product-planning"
status: planned
parent_prd: /docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md
related:
  - /docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md
  - /skillmeat/core/sync.py
  - /skillmeat/storage/snapshot.py
  - /skillmeat/storage/deployment.py
  - /skillmeat/services/hash_service.py
---

# PRD Addendum: Artifact State Origin Tracking (v1.5)

**Feature Name:** Artifact State Origin Tracking

**Filepath Name:** `versioning-merge-system-v1.5-state-tracking`

**Date:** 2025-12-17

**Author:** Claude Code (AI Agent)

**Version:** 1.5 (Enhancement to v1.0)

**Status:** Planned

**Parent PRD:** Versioning & Merge System v1.0

---

## 1. Executive Summary

This addendum enhances the Versioning & Merge System (v1.0) with **content-addressable state tracking** that records artifact state at every lifecycle event, creating a complete hash chain from deployment through sync to local modification. This enables precise attribution of changes to their origin: upstream updates, local modifications, deployment baseline, or merge operations.

**Core Enhancement:** Transform artifact version tracking from timestamp-based to **content-hash-based** with explicit parent-child relationships, enabling precise three-way merge and drift attribution.

**Critical Gap Being Addressed:**

The v1.0 system (95% complete) has THREE critical gaps preventing proper merge operation:

1. **THREE-WAY MERGE BASELINE MISSING** - Current implementation uses collection version as merge base instead of deployed version, breaking three-way merge semantics
2. **VERSION LINEAGE NOT POPULATED** - Fields exist (`parent_hash`, `version_lineage`) but are never populated, preventing version chain traversal
3. **MODIFICATION TRACKING INCOMPLETE** - `modification_detected_at` defined but not populated, cannot determine local change timeline

**User Problem:**

When viewing a diff (Collection ↔ Project or Source ↔ Collection), users cannot answer:
- "Did this change come from upstream sync?"
- "Did I modify this locally after deployment?"
- "What was the state at initial deployment vs. last sync?"
- "Is this diff showing MY changes or UPSTREAM changes?"

**Solution:**

Record **content hash snapshots** at every state transition:
- **At deployment** → Baseline hash (merge base)
- **After sync** → Post-sync hash (upstream state)
- **At modification detection** → Modified hash (local state)
- **After merge** → Merged hash (combined state)

Each state change creates a parent-child hash relationship, building a complete version chain.

**Key Outcomes:**
- Three-way merge uses correct baseline (deployed version, not current collection)
- Version lineage fully populated with parent-child hash chain
- Change origin attribution: "upstream", "local", "deployment", "merge"
- UI shows "This changed upstream since last sync" vs. "You modified this locally"
- Drift detection API returns change attribution metadata

---

## 2. Context & Background

### Parent PRD Status (v1.0)

**What Was Implemented (95% complete):**

1. **Snapshot System** (SVCV-002/003) - COMPLETE
   - Per-artifact version storage with tarball snapshots
   - Metadata tracking (timestamp, message, tags)
   - Database schema with version relationships

2. **Three-Way Merge Models** (SVCV-007) - COMPLETE
   - `ThreeWayMergeRequest` with base/source/target/project paths
   - `MergeStrategy` enum (auto/manual/base/source/target)
   - Database models for tracking merge operations

3. **Web UI Components** (SVCV-008) - COMPLETE
   - History tab with version timeline
   - Three-way merge dialog
   - Diff viewer with side-by-side comparison

4. **Deployment Metadata** (existing) - PARTIAL
   - `.skillmeat-deployed.toml` tracks deployment state
   - Records checksum and timestamp
   - **MISSING**: Baseline content hash for merge base

5. **Content Hashing Service** (existing) - COMPLETE
   - `ContentHashService` for SHA256 file hashing
   - `FileHasher` for deterministic directory hashing
   - Used for integrity checks, NOT version tracking

**What Is Missing (5% - Critical Gaps):**

1. **Merge Base Snapshot** (HIGH severity):
   - Current: Merge uses `current collection version` as base
   - Required: Merge must use `deployed version at deployment time` as base
   - Impact: Three-way merge produces incorrect results (false conflicts)

2. **Parent Hash Population** (HIGH severity):
   - Current: `parent_hash` field exists but is always NULL
   - Required: Populate on every state change (deployment → sync → modification)
   - Impact: Cannot traverse version history, cannot determine change lineage

3. **Modification Timestamp** (MEDIUM severity):
   - Current: `modification_detected_at` defined but never set
   - Required: Set when drift detection identifies local changes
   - Impact: Cannot distinguish "when did user modify this?" from deployment time

4. **Change Origin Metadata** (MEDIUM severity):
   - Current: No field to track WHY version changed
   - Required: `change_origin` enum: "deployment" | "upstream_sync" | "local_modification" | "merge"
   - Impact: UI cannot show "upstream change" vs "local change" attribution

### Problem Space (Detailed)

**Problem 1: Three-Way Merge Uses Wrong Baseline**

**Current Behavior:**
```python
# skillmeat/core/sync.py - three_way_merge()
base_version = collection_version  # ❌ WRONG: Uses current collection state
source_version = upstream_version
target_version = project_version
```

**Expected Behavior:**
```python
# Should use deployed version as baseline
base_version = deployed_version_at_deployment_time  # ✓ CORRECT
source_version = upstream_version
target_version = project_version
```

**Impact:**
- False conflicts detected (user changes flagged as conflicts with upstream)
- Cannot distinguish "local modification" from "upstream update"
- Merge produces incorrect results when collection has diverged from deployment

**Example Scenario:**
1. User deploys artifact v1.0 to project (baseline)
2. Collection updates to v1.1 from upstream sync
3. User modifies project to v1.0-custom (local change)
4. User initiates merge:
   - **CURRENT**: Base = v1.1, Source = v1.1, Target = v1.0-custom
     - Result: False conflict (user change vs. no change)
   - **CORRECT**: Base = v1.0, Source = v1.1, Target = v1.0-custom
     - Result: Clean merge (upstream change + local change)

**Problem 2: Version Lineage Not Tracked**

**Current State:**
```python
# skillmeat/storage/models.py - ArtifactVersion
class ArtifactVersion(Base):
    parent_hash = Column(String, nullable=True)  # Always NULL
    version_lineage = Column(JSON, nullable=True)  # Always NULL
```

**Impact:**
- Cannot traverse version history backwards
- Cannot determine "what was the state 3 syncs ago?"
- Cannot show version tree in UI (must rely on timestamps alone)
- Cannot implement "revert to parent" functionality

**Problem 3: Modification Detection Not Persisted**

**Current State:**
```python
# skillmeat/core/sync.py - detect_drift()
drift = DriftDetection(
    artifact_id=artifact_id,
    drift_detected=has_drift,
    # modification_detected_at is NOT set ❌
)
```

**Impact:**
- Cannot distinguish "deployed yesterday, synced today" from "deployed yesterday, modified today"
- Cannot show "Last modified: 2 hours ago (you)" vs "Last synced: 1 day ago (upstream)"
- Cannot sort by "recently modified" in UI

**Problem 4: Change Origin Not Tracked**

**Current State:**
- No field to indicate WHY a version was created
- All versions look the same (just timestamp differences)

**Needed:**
```python
class ArtifactVersion(Base):
    change_origin = Column(Enum(ChangeOrigin), nullable=False)
    # "deployment" = initial deployment to project
    # "upstream_sync" = sync from source to collection
    # "local_modification" = user edited in project
    # "merge" = result of three-way merge operation
```

**Impact:**
- UI cannot show "upstream change" vs "local change" badges
- Diff viewer cannot highlight which side introduced the change
- Users confused about "why is this different?"

---

## 3. Goals & Success Metrics

### Goals

**Goal 1: Fix Three-Way Merge Baseline**
Enable correct three-way merge by storing deployment baseline hash in metadata.

**Acceptance Criteria:**
- Deployment metadata includes `merge_base_snapshot` field with content hash
- `three_way_merge()` retrieves baseline from deployment metadata, not current collection
- Merge produces correct results when collection has diverged from deployment

**Goal 2: Populate Version Lineage Chain**
Create complete parent-child hash chain for every artifact version.

**Acceptance Criteria:**
- `parent_hash` populated on every version creation (deployment, sync, modification, merge)
- `version_lineage` array stores full hash chain from deployment to current state
- Version history API can traverse backwards through parent hashes

**Goal 3: Track Modification Timestamps**
Record when local modifications are detected, not just when deployment occurred.

**Acceptance Criteria:**
- `modification_detected_at` set when drift detection identifies local changes
- API returns "last modified" timestamp separate from "deployed at"
- UI shows "Modified 2 hours ago" vs "Deployed 1 day ago"

**Goal 4: Attribute Change Origin**
Enable UI to show whether changes came from upstream or local modifications.

**Acceptance Criteria:**
- `change_origin` field populated on every version
- Diff API returns change attribution ("upstream", "local", "both")
- UI displays badges: "Upstream change" (blue) vs "Local change" (orange)

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Merge Accuracy** | 95%+ correct conflict detection | Unit tests with known scenarios |
| **Version Chain Completeness** | 100% versions have parent_hash | Database query validation |
| **Modification Tracking** | 100% drift events set timestamp | Drift detection logs |
| **Change Attribution** | 90%+ users understand diff origin | User testing feedback |
| **API Performance** | <100ms for change origin query | Performance benchmarks |

---

## 4. Requirements

### Functional Requirements

#### FR-A1: Record Content Hash at Deployment (Baseline)

**Priority:** HIGH (Critical for merge)

**Description:**
When an artifact is deployed from collection to project, record the collection content hash as the merge baseline in deployment metadata.

**Behavior:**
1. Deployment manager computes content hash of deployed artifact
2. Stores hash in `.skillmeat-deployed.toml` under `merge_base_snapshot`
3. Creates initial `ArtifactVersion` with:
   - `content_hash` = deployment hash
   - `parent_hash` = NULL (first version)
   - `change_origin` = "deployment"
   - `version_lineage` = [hash]

**Example:**
```toml
# .skillmeat-deployed.toml
[artifacts.canvas-design]
source_hash = "abc123..."
deployed_at = "2025-12-17T10:00:00Z"
merge_base_snapshot = "abc123..."  # NEW: Baseline for three-way merge
```

**Acceptance:**
- `merge_base_snapshot` present in all new deployments
- `parent_hash` is NULL for deployment versions
- `change_origin` = "deployment"

---

#### FR-A2: Record Content Hash After Upstream Sync

**Priority:** HIGH (Critical for tracking upstream changes)

**Description:**
When collection syncs from upstream source, record the new content hash and link to previous version.

**Behavior:**
1. Sync manager detects upstream updates
2. Creates new `ArtifactVersion` with:
   - `content_hash` = new upstream hash
   - `parent_hash` = previous collection hash
   - `change_origin` = "upstream_sync"
   - `version_lineage` = previous_lineage + [new_hash]
3. Updates collection manifest with new hash

**Example:**
```python
# Before sync: collection at hash "abc123"
# After sync: source has hash "def456"

new_version = ArtifactVersion(
    content_hash="def456",
    parent_hash="abc123",  # Link to previous version
    change_origin=ChangeOrigin.UPSTREAM_SYNC,
    version_lineage=["abc123", "def456"],
)
```

**Acceptance:**
- `parent_hash` links to previous collection version
- `change_origin` = "upstream_sync"
- `version_lineage` appends new hash

---

#### FR-A3: Detect and Timestamp Local Modifications

**Priority:** MEDIUM (Important for user awareness)

**Description:**
When drift detection identifies local changes in project, record modification timestamp and create version record.

**Behavior:**
1. Drift detection compares project hash to deployed baseline hash
2. If different:
   - Sets `modification_detected_at` to current timestamp
   - Creates new `ArtifactVersion` with:
     - `content_hash` = current project hash
     - `parent_hash` = deployed baseline hash
     - `change_origin` = "local_modification"
     - `version_lineage` = baseline_lineage + [project_hash]

**Example:**
```python
# Deployment baseline: hash "abc123" at 10:00 AM
# User modifies project: hash "xyz789" at 2:00 PM

drift = DriftDetection(
    drift_detected=True,
    modification_detected_at=datetime(2025, 12, 17, 14, 0, 0),  # 2:00 PM
)

local_version = ArtifactVersion(
    content_hash="xyz789",
    parent_hash="abc123",
    change_origin=ChangeOrigin.LOCAL_MODIFICATION,
)
```

**Acceptance:**
- `modification_detected_at` set when local changes detected
- Local modifications create version records
- `change_origin` = "local_modification"

---

#### FR-A4: Populate Parent Hash to Create Version Chain

**Priority:** HIGH (Required for all tracking)

**Description:**
Every version creation event (deployment, sync, modification, merge) must populate `parent_hash` to link to previous state.

**Behavior:**
1. **Deployment**: `parent_hash` = NULL (first version)
2. **Sync**: `parent_hash` = previous collection hash
3. **Modification**: `parent_hash` = deployed baseline hash
4. **Merge**: `parent_hash` = pre-merge project hash

**Version Chain Example:**
```
Deployment v1.0 (hash A, parent=NULL)
    ↓
Upstream Sync v1.1 (hash B, parent=A)
    ↓
Upstream Sync v1.2 (hash C, parent=B)
    ↓
Local Modification (hash D, parent=A)  # Diverged from baseline
    ↓
Merge (hash E, parent=D)  # Merged v1.2 into local changes
```

**Acceptance:**
- All versions have `parent_hash` (except initial deployment)
- Version chain is unbroken (no orphaned versions)
- Can traverse from current to deployment baseline

---

#### FR-A5: Store Merge Base Snapshot for Three-Way Merge

**Priority:** HIGH (Critical for correct merge)

**Description:**
Three-way merge must use deployed baseline as merge base, not current collection version.

**Behavior:**
1. Deployment stores `merge_base_snapshot` in metadata
2. Three-way merge retrieves baseline:
   ```python
   base_hash = deployment_metadata['merge_base_snapshot']
   base_version = get_version_by_hash(base_hash)
   ```
3. Merge compares:
   - **Base**: Deployed version (merge_base_snapshot)
   - **Source**: Current collection version (upstream state)
   - **Target**: Current project version (local state)

**Merge Logic:**
```python
# Correct three-way merge
if source_hash == base_hash and target_hash != base_hash:
    # Only local changes → keep target
    result = target
elif target_hash == base_hash and source_hash != base_hash:
    # Only upstream changes → keep source
    result = source
elif source_hash == target_hash:
    # Both changed the same way → no conflict
    result = source  # or target (identical)
else:
    # Both changed differently → CONFLICT
    result = conflict_resolution_required
```

**Acceptance:**
- Three-way merge uses `merge_base_snapshot` as base
- Merge correctly identifies "local only", "upstream only", "both changed"
- False conflicts eliminated (e.g., local change vs. no change)

---

#### FR-A6: Add Change Origin Field

**Priority:** MEDIUM (Important for UI/UX)

**Description:**
Add `change_origin` enum field to `ArtifactVersion` to track why version was created.

**Schema:**
```python
class ChangeOrigin(str, Enum):
    DEPLOYMENT = "deployment"          # Initial deployment to project
    UPSTREAM_SYNC = "upstream_sync"    # Sync from source to collection
    LOCAL_MODIFICATION = "local_modification"  # User edited in project
    MERGE = "merge"                    # Result of three-way merge

class ArtifactVersion(Base):
    change_origin = Column(Enum(ChangeOrigin), nullable=False)
```

**Population:**
- **Deployment**: Set to `DEPLOYMENT` when deploying to project
- **Sync**: Set to `UPSTREAM_SYNC` when collection syncs from source
- **Modification**: Set to `LOCAL_MODIFICATION` when drift detected
- **Merge**: Set to `MERGE` when three-way merge completes

**Acceptance:**
- All new versions have `change_origin` populated
- Enum values match lifecycle events
- API returns change origin in version metadata

---

#### FR-A7: UI Shows Change Origin in Diff View

**Priority:** MEDIUM (User experience)

**Description:**
Diff viewer displays badges indicating change origin: "Upstream change" vs. "Local change" vs. "Both changed".

**Behavior:**
1. Diff API returns change attribution metadata:
   ```typescript
   {
     file: "SKILL.md",
     status: "modified",
     change_origin: "upstream",  // or "local" or "both"
   }
   ```
2. UI renders color-coded badges:
   - **Upstream change** (blue badge): File changed in source, not in project
   - **Local change** (orange badge): File changed in project, not in source
   - **Both changed** (red badge): File changed in both (conflict)
   - **No change** (gray badge): File unchanged in both

**Visual Example:**
```
📄 SKILL.md [Upstream change ↓]
   - Source: Added new section "Advanced Patterns"
   - Project: No changes

📄 config.yaml [Local change ↑]
   - Source: No changes
   - Project: Modified timeout from 30s to 60s

📄 README.md [Both changed ⚠]
   - Source: Updated installation steps
   - Project: Added troubleshooting section
```

**Acceptance:**
- Badges displayed for all modified files
- Color coding matches change origin
- Tooltips explain badge meaning

---

#### FR-A8: API Returns Change Attribution in Drift Detection

**Priority:** MEDIUM (API enhancement)

**Description:**
Drift detection API includes change attribution metadata for each detected difference.

**API Response:**
```json
{
  "drift_detected": true,
  "differences": [
    {
      "file": "SKILL.md",
      "status": "modified",
      "change_origin": "upstream",
      "baseline_hash": "abc123",
      "current_hash": "def456",
      "last_modified_at": "2025-12-17T14:00:00Z"
    },
    {
      "file": "config.yaml",
      "status": "modified",
      "change_origin": "local",
      "baseline_hash": "abc123",
      "current_hash": "xyz789",
      "last_modified_at": "2025-12-17T10:30:00Z"
    }
  ],
  "summary": {
    "upstream_changes": 1,
    "local_changes": 1,
    "conflicts": 0
  }
}
```

**Acceptance:**
- API returns `change_origin` for each difference
- Summary counts upstream vs. local vs. conflicts
- Timestamps indicate when changes occurred

---

### Non-Functional Requirements

#### NFR-A1: Performance

**Requirement:**
Change origin queries must complete in <100ms for typical artifact sizes (<10MB).

**Implementation:**
- Index `content_hash` and `parent_hash` columns
- Cache version lineage in JSON column (avoid recursive queries)
- Use hash-based lookups instead of timestamp ranges

**Acceptance:**
- 95th percentile query time <100ms
- No N+1 query patterns in version chain traversal

---

#### NFR-A2: Storage Efficiency

**Requirement:**
Version metadata must not exceed 1% of artifact content size.

**Implementation:**
- Store only hash (32 bytes) + parent hash (32 bytes) + enum (1 byte) = 65 bytes per version
- `version_lineage` JSON array stores hashes, not full content
- Snapshot tarballs deduplicated at storage layer (existing)

**Acceptance:**
- Metadata overhead <1% for artifacts >10KB
- No duplicate content storage for unchanged files

---

#### NFR-A3: Migration Safety

**Requirement:**
Existing deployments must work without migration; new tracking applies to future operations only.

**Implementation:**
- `merge_base_snapshot` optional in deployment metadata (nullable)
- If missing, fall back to current collection version (v1.0 behavior)
- Gradual migration: populate on next deployment/sync

**Acceptance:**
- Zero breaking changes to existing deployments
- Warning logged when `merge_base_snapshot` missing
- New deployments always populate field

---

#### NFR-A4: Backward Compatibility

**Requirement:**
API changes must maintain backward compatibility with v1.0 clients.

**Implementation:**
- Add new fields as optional in responses
- Existing endpoints return same structure + new fields
- New endpoints for advanced change attribution (opt-in)

**Acceptance:**
- v1.0 clients continue to work without changes
- v1.5 clients can access new attribution fields
- No deprecated fields removed

---

## 5. Technical Approach

### Architecture Overview

**Hash Chain Design:**

```
                    Deployment (BASELINE)
                         ↓
                    [Hash A, parent=NULL]
                    change_origin=DEPLOYMENT
                         |
              ┌──────────┴──────────┐
              ↓                     ↓
     Upstream Sync 1          (no local change)
         [Hash B]
      parent=A
  change_origin=UPSTREAM_SYNC
              ↓
     Upstream Sync 2
         [Hash C]
      parent=B
  change_origin=UPSTREAM_SYNC
              |
              |                     ↓
              |              Local Modification
              |                 [Hash D]
              |              parent=A (baseline)
              |          change_origin=LOCAL_MODIFICATION
              |                     ↓
              └─────────→ Three-Way Merge
                          [Hash E]
                       parent=D
                   change_origin=MERGE
                   base=A, source=C, target=D
```

**Key Design Decisions:**

1. **Content Hash as Version ID**: Use SHA256 hash of artifact content as immutable version identifier (collision-resistant, deterministic)

2. **Parent Hash Links**: Each version stores parent hash, creating directed acyclic graph (DAG) of version history

3. **Merge Base Snapshot**: Deployment metadata stores baseline hash; three-way merge uses this, not current collection

4. **Change Origin Enum**: Explicit tracking of WHY version was created (deployment/sync/modification/merge)

5. **Version Lineage Array**: Pre-computed hash chain stored as JSON array for fast traversal

---

### Data Model Changes

#### Deployment Metadata Enhancement

**File:** `skillmeat/storage/deployment.py`

**Before:**
```toml
# .skillmeat-deployed.toml
[artifacts.canvas-design]
source_hash = "abc123..."
deployed_at = "2025-12-17T10:00:00Z"
```

**After:**
```toml
[artifacts.canvas-design]
source_hash = "abc123..."
deployed_at = "2025-12-17T10:00:00Z"
merge_base_snapshot = "abc123..."  # NEW: Baseline for three-way merge
merge_base_timestamp = "2025-12-17T10:00:00Z"  # NEW: When baseline was set
```

---

#### ArtifactVersion Schema Enhancement

**File:** `skillmeat/storage/models.py`

**Before:**
```python
class ArtifactVersion(Base):
    id = Column(String, primary_key=True)
    artifact_id = Column(String, ForeignKey("artifacts.id"), nullable=False)
    content_hash = Column(String, nullable=False)
    parent_hash = Column(String, nullable=True)  # ❌ Never populated
    version_lineage = Column(JSON, nullable=True)  # ❌ Never populated
    created_at = Column(DateTime, nullable=False)
    message = Column(String, nullable=True)
```

**After:**
```python
class ChangeOrigin(str, Enum):
    DEPLOYMENT = "deployment"
    UPSTREAM_SYNC = "upstream_sync"
    LOCAL_MODIFICATION = "local_modification"
    MERGE = "merge"

class ArtifactVersion(Base):
    id = Column(String, primary_key=True)
    artifact_id = Column(String, ForeignKey("artifacts.id"), nullable=False)
    content_hash = Column(String, nullable=False, index=True)  # ✓ Indexed
    parent_hash = Column(String, nullable=True, index=True)  # ✓ Populated + indexed
    version_lineage = Column(JSON, nullable=True)  # ✓ Populated
    change_origin = Column(Enum(ChangeOrigin), nullable=False)  # ✓ NEW
    modification_detected_at = Column(DateTime, nullable=True)  # ✓ Populated when local change
    created_at = Column(DateTime, nullable=False)
    message = Column(String, nullable=True)
```

---

#### DriftDetection Schema Enhancement

**File:** `skillmeat/models.py`

**Before:**
```python
class DriftDetection(BaseModel):
    artifact_id: str
    drift_detected: bool
    modification_detected_at: Optional[datetime] = None  # ❌ Never set
```

**After:**
```python
class DriftDetection(BaseModel):
    artifact_id: str
    drift_detected: bool
    modification_detected_at: Optional[datetime] = None  # ✓ Set when local change
    change_origin: ChangeOrigin  # ✓ NEW: "upstream" | "local" | "both"
    baseline_hash: str  # ✓ NEW: Deployed baseline
    current_hash: str   # ✓ NEW: Current state
```

---

### Algorithm Changes

#### Three-Way Merge Fix

**File:** `skillmeat/core/sync.py`

**Before (BROKEN):**
```python
def three_way_merge(
    collection_path: Path,
    project_path: Path,
    upstream_path: Path,
) -> MergeResult:
    # ❌ WRONG: Uses current collection as base
    base_version = collection_path
    source_version = upstream_path
    target_version = project_path

    # Merge logic...
```

**After (FIXED):**
```python
def three_way_merge(
    collection_path: Path,
    project_path: Path,
    upstream_path: Path,
    deployment_metadata: Dict[str, Any],
) -> MergeResult:
    # ✓ CORRECT: Use deployed baseline as merge base
    baseline_hash = deployment_metadata.get('merge_base_snapshot')

    if not baseline_hash:
        # Fallback for old deployments
        logger.warning("No merge_base_snapshot found, using collection as base")
        base_version = collection_path
    else:
        # Retrieve baseline version from version history
        base_version = get_version_snapshot(baseline_hash)

    source_version = upstream_path  # Current collection (upstream state)
    target_version = project_path   # Current project (local state)

    # Three-way merge logic...
```

---

#### Version Creation on Deployment

**File:** `skillmeat/storage/deployment.py`

**New Logic:**
```python
def deploy_artifact(
    artifact_id: str,
    collection_path: Path,
    project_path: Path,
) -> DeploymentResult:
    # Compute content hash of deployed artifact
    content_hash = hash_service.hash_directory(collection_path)

    # Create deployment metadata
    deployment_metadata = {
        'source_hash': content_hash,
        'deployed_at': datetime.now().isoformat(),
        'merge_base_snapshot': content_hash,  # ✓ NEW: Set baseline
        'merge_base_timestamp': datetime.now().isoformat(),
    }

    # Save metadata
    save_deployment_metadata(project_path, deployment_metadata)

    # Create initial version record
    version = ArtifactVersion(
        artifact_id=artifact_id,
        content_hash=content_hash,
        parent_hash=None,  # ✓ First version has no parent
        version_lineage=[content_hash],  # ✓ Initialize lineage
        change_origin=ChangeOrigin.DEPLOYMENT,  # ✓ NEW
        created_at=datetime.now(),
        message=f"Deployed from collection to {project_path.name}",
    )

    session.add(version)
    session.commit()

    return DeploymentResult(success=True, version=version)
```

---

#### Version Creation on Sync

**File:** `skillmeat/core/sync.py`

**New Logic:**
```python
def sync_from_source(
    artifact_id: str,
    source_path: Path,
    collection_path: Path,
) -> SyncResult:
    # Compute new hash after sync
    new_hash = hash_service.hash_directory(source_path)

    # Get previous collection version
    previous_version = get_latest_version(artifact_id)
    previous_hash = previous_version.content_hash if previous_version else None

    if new_hash == previous_hash:
        # No upstream changes
        return SyncResult(changed=False)

    # Create new version for upstream sync
    version = ArtifactVersion(
        artifact_id=artifact_id,
        content_hash=new_hash,
        parent_hash=previous_hash,  # ✓ Link to previous version
        version_lineage=previous_version.version_lineage + [new_hash],  # ✓ Append
        change_origin=ChangeOrigin.UPSTREAM_SYNC,  # ✓ NEW
        created_at=datetime.now(),
        message=f"Synced from {source_path}",
    )

    session.add(version)
    session.commit()

    return SyncResult(changed=True, version=version)
```

---

#### Modification Detection Enhancement

**File:** `skillmeat/core/sync.py`

**New Logic:**
```python
def detect_drift(
    artifact_id: str,
    project_path: Path,
    deployment_metadata: Dict[str, Any],
) -> DriftDetection:
    # Get baseline hash from deployment
    baseline_hash = deployment_metadata.get('merge_base_snapshot')
    if not baseline_hash:
        raise ValueError("No merge_base_snapshot in deployment metadata")

    # Compute current project hash
    current_hash = hash_service.hash_directory(project_path)

    # Detect local modification
    if current_hash != baseline_hash:
        # ✓ Create version record for local modification
        version = ArtifactVersion(
            artifact_id=artifact_id,
            content_hash=current_hash,
            parent_hash=baseline_hash,  # ✓ Link to deployment baseline
            version_lineage=[baseline_hash, current_hash],
            change_origin=ChangeOrigin.LOCAL_MODIFICATION,  # ✓ NEW
            modification_detected_at=datetime.now(),  # ✓ Set timestamp
            created_at=datetime.now(),
            message="Local modification detected",
        )

        session.add(version)
        session.commit()

        return DriftDetection(
            artifact_id=artifact_id,
            drift_detected=True,
            modification_detected_at=version.modification_detected_at,  # ✓ NEW
            change_origin=ChangeOrigin.LOCAL_MODIFICATION,  # ✓ NEW
            baseline_hash=baseline_hash,  # ✓ NEW
            current_hash=current_hash,  # ✓ NEW
        )
    else:
        return DriftDetection(
            artifact_id=artifact_id,
            drift_detected=False,
            change_origin=ChangeOrigin.DEPLOYMENT,  # No change since deployment
            baseline_hash=baseline_hash,
            current_hash=current_hash,
        )
```

---

#### Change Attribution Logic

**File:** `skillmeat/core/sync.py`

**New Function:**
```python
def determine_change_origin(
    baseline_hash: str,
    collection_hash: str,
    project_hash: str,
) -> str:
    """
    Determine change origin for diff display.

    Returns:
        "upstream" - Only collection changed (upstream update)
        "local" - Only project changed (local modification)
        "both" - Both changed (conflict)
        "none" - Neither changed
    """
    collection_changed = collection_hash != baseline_hash
    project_changed = project_hash != baseline_hash

    if collection_changed and project_changed:
        return "both"
    elif collection_changed:
        return "upstream"
    elif project_changed:
        return "local"
    else:
        return "none"
```

---

### API Changes

#### Drift Detection API Enhancement

**Endpoint:** `GET /api/v1/deployments/drift/{artifact_id}`

**Response (Before):**
```json
{
  "drift_detected": true,
  "differences": [
    {
      "file": "SKILL.md",
      "status": "modified"
    }
  ]
}
```

**Response (After):**
```json
{
  "drift_detected": true,
  "differences": [
    {
      "file": "SKILL.md",
      "status": "modified",
      "change_origin": "upstream",  // ✓ NEW
      "baseline_hash": "abc123",    // ✓ NEW
      "current_hash": "def456",     // ✓ NEW
      "last_modified_at": "2025-12-17T14:00:00Z"  // ✓ NEW
    }
  ],
  "summary": {
    "upstream_changes": 1,  // ✓ NEW
    "local_changes": 0,     // ✓ NEW
    "conflicts": 0          // ✓ NEW
  }
}
```

---

#### Version History API Enhancement

**Endpoint:** `GET /api/v1/artifacts/{artifact_id}/versions`

**Response (After):**
```json
{
  "versions": [
    {
      "id": "v1",
      "content_hash": "abc123",
      "parent_hash": null,
      "change_origin": "deployment",  // ✓ NEW
      "version_lineage": ["abc123"],
      "created_at": "2025-12-17T10:00:00Z",
      "message": "Deployed from collection"
    },
    {
      "id": "v2",
      "content_hash": "def456",
      "parent_hash": "abc123",
      "change_origin": "upstream_sync",  // ✓ NEW
      "version_lineage": ["abc123", "def456"],
      "created_at": "2025-12-17T12:00:00Z",
      "message": "Synced from upstream"
    }
  ]
}
```

---

### Web UI Changes

#### Diff Viewer Badge Display

**Component:** `components/artifacts/ArtifactDiffViewer.tsx`

**Enhancement:**
```typescript
function getChangeBadge(changeOrigin: string) {
  switch (changeOrigin) {
    case 'upstream':
      return (
        <Badge variant="info" className="bg-blue-100 text-blue-800">
          <ArrowDown className="w-3 h-3 mr-1" />
          Upstream change
        </Badge>
      );
    case 'local':
      return (
        <Badge variant="warning" className="bg-orange-100 text-orange-800">
          <ArrowUp className="w-3 h-3 mr-1" />
          Local change
        </Badge>
      );
    case 'both':
      return (
        <Badge variant="destructive" className="bg-red-100 text-red-800">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Both changed
        </Badge>
      );
    default:
      return null;
  }
}

// Usage in diff viewer
<div className="file-diff">
  <div className="file-header">
    <span>SKILL.md</span>
    {getChangeBadge(diff.change_origin)}  {/* ✓ NEW */}
  </div>
  <DiffDisplay content={diff.unified_diff} />
</div>
```

---

#### Version Timeline Enhancement

**Component:** `components/artifacts/VersionHistory.tsx`

**Enhancement:**
```typescript
function VersionNode({ version }: { version: ArtifactVersion }) {
  return (
    <div className="version-node">
      <div className="version-header">
        <Hash className="w-4 h-4" />
        <span className="version-hash">{version.content_hash.slice(0, 8)}</span>
        <Badge variant={getOriginVariant(version.change_origin)}>
          {getOriginLabel(version.change_origin)}  {/* ✓ NEW */}
        </Badge>
      </div>
      <div className="version-metadata">
        <span>{formatTimestamp(version.created_at)}</span>
        {version.modification_detected_at && (  {/* ✓ NEW */}
          <span className="text-orange-600">
            Modified {formatRelativeTime(version.modification_detected_at)}
          </span>
        )}
      </div>
      <div className="version-message">{version.message}</div>
    </div>
  );
}

function getOriginLabel(origin: ChangeOrigin): string {
  switch (origin) {
    case 'deployment': return 'Deployed';
    case 'upstream_sync': return 'Synced';
    case 'local_modification': return 'Modified';
    case 'merge': return 'Merged';
  }
}
```

---

## 6. Implementation Strategy

### Phase Breakdown

#### Phase 1: Core Baseline Support (Fix Three-Way Merge)
**Duration:** 2-3 days
**Priority:** HIGH
**Effort:** 16-24 hours

**Tasks:**
1. Add `merge_base_snapshot` field to deployment metadata schema
2. Update `deploy_artifact()` to store baseline hash on deployment
3. Modify `three_way_merge()` to retrieve baseline from metadata (not collection)
4. Add fallback logic for old deployments (no baseline)
5. Write unit tests for correct merge base retrieval

**Acceptance:**
- All new deployments have `merge_base_snapshot`
- Three-way merge uses deployed baseline
- Old deployments fall back gracefully
- Unit tests pass for merge scenarios

**Files Changed:**
- `skillmeat/storage/deployment.py` (add baseline storage)
- `skillmeat/core/sync.py` (update merge logic)
- `tests/test_three_way_merge.py` (add baseline tests)

---

#### Phase 2: Version Lineage Tracking
**Duration:** 1-2 days
**Priority:** HIGH
**Effort:** 8-16 hours

**Tasks:**
1. Add database migration for `change_origin` enum column
2. Update `ArtifactVersion` model with `change_origin` field
3. Populate `parent_hash` on deployment (parent=NULL)
4. Populate `parent_hash` on sync (parent=previous collection hash)
5. Populate `version_lineage` array (append new hash)
6. Add database indexes on `content_hash` and `parent_hash`
7. Write unit tests for version chain creation

**Acceptance:**
- All new versions have `parent_hash` populated
- `version_lineage` array is complete
- Can traverse from current version to deployment baseline
- Database indexes improve query performance

**Files Changed:**
- `skillmeat/storage/models.py` (add change_origin enum + column)
- `skillmeat/storage/deployment.py` (populate parent_hash on deploy)
- `skillmeat/core/sync.py` (populate parent_hash on sync)
- `alembic/versions/XXX_add_change_origin.py` (migration)
- `tests/test_version_lineage.py` (version chain tests)

---

#### Phase 3: Modification Tracking Enhancement
**Duration:** 1 day
**Priority:** MEDIUM
**Effort:** 6-8 hours

**Tasks:**
1. Update `detect_drift()` to set `modification_detected_at` when local change found
2. Create `ArtifactVersion` record for local modifications (with parent=baseline)
3. Update `DriftDetection` schema to include change attribution fields
4. Add API response fields: `change_origin`, `baseline_hash`, `current_hash`
5. Write unit tests for modification timestamp setting

**Acceptance:**
- `modification_detected_at` set when drift detected
- Local modifications create version records
- Drift API returns change attribution
- Unit tests pass for modification scenarios

**Files Changed:**
- `skillmeat/core/sync.py` (update detect_drift)
- `skillmeat/models.py` (update DriftDetection schema)
- `skillmeat/api/routers/deployments.py` (add response fields)
- `tests/test_drift_detection.py` (modification tests)

---

#### Phase 4: Change Attribution Logic
**Duration:** 1-2 days
**Priority:** MEDIUM
**Effort:** 8-12 hours

**Tasks:**
1. Implement `determine_change_origin()` function (baseline vs. collection vs. project)
2. Update drift detection API to return `change_origin` per file
3. Add summary counts: `upstream_changes`, `local_changes`, `conflicts`
4. Add change attribution to diff API responses
5. Write unit tests for all change origin scenarios

**Acceptance:**
- API correctly identifies "upstream", "local", "both", "none"
- Summary counts are accurate
- Unit tests cover all scenarios (upstream only, local only, both, neither)

**Files Changed:**
- `skillmeat/core/sync.py` (add determine_change_origin)
- `skillmeat/api/routers/deployments.py` (update responses)
- `skillmeat/api/schemas/deployment.py` (add attribution fields)
- `tests/test_change_attribution.py` (attribution tests)

---

#### Phase 5: Web UI Integration
**Duration:** 2 days
**Priority:** MEDIUM
**Effort:** 12-16 hours

**Tasks:**
1. Update frontend types to include `change_origin` field
2. Add badge component for change origin display
3. Update diff viewer to show badges ("Upstream change" / "Local change")
4. Update version timeline to show change origin labels
5. Add tooltips explaining badge meanings
6. Write frontend tests for badge rendering

**Acceptance:**
- Badges displayed in diff viewer
- Color coding matches change origin (blue=upstream, orange=local, red=conflict)
- Version timeline shows origin labels
- Tooltips provide helpful explanations

**Files Changed:**
- `skillmeat/web/types/deployments.ts` (add change_origin)
- `skillmeat/web/components/artifacts/ArtifactDiffViewer.tsx` (badges)
- `skillmeat/web/components/artifacts/VersionHistory.tsx` (labels)
- `skillmeat/web/components/ui/ChangeBadge.tsx` (new component)
- `skillmeat/web/__tests__/components/ChangeBadge.test.tsx` (tests)

---

#### Phase 6: Testing & Validation
**Duration:** 2-3 days
**Priority:** HIGH
**Effort:** 12-20 hours

**Tasks:**
1. Write integration tests for end-to-end workflows:
   - Deploy → Sync → Detect drift → Merge
   - Deploy → Local modify → Sync → Conflict detection
2. Write performance tests for version chain queries
3. Test migration from v1.0 deployments (no baseline) to v1.5
4. Manual testing of UI flows (diff viewer, version history)
5. Load testing with large version chains (100+ versions)
6. Documentation updates (API docs, user guides)

**Acceptance:**
- All integration tests pass
- Version chain queries <100ms (95th percentile)
- Migration from v1.0 works without errors
- UI flows validated manually
- Performance benchmarks met

**Files Changed:**
- `tests/integration/test_state_tracking_workflow.py` (integration tests)
- `tests/performance/test_version_queries.py` (performance tests)
- `docs/api/drift-detection.md` (API docs)
- `docs/user-guide/version-tracking.md` (user guide)

---

### Migration Strategy

**Graceful Degradation for Old Deployments:**

1. **Detection**: Check if `merge_base_snapshot` exists in deployment metadata
2. **Fallback**: If missing, use current collection version as base (v1.0 behavior)
3. **Warning**: Log warning when fallback used: "No merge_base_snapshot found for {artifact_id}, using collection as base. Redeploy to enable accurate change attribution."
4. **Gradual Migration**: On next deployment or sync, populate `merge_base_snapshot`

**Example Migration Code:**
```python
def get_merge_base(deployment_metadata: Dict[str, Any], artifact_id: str) -> str:
    baseline_hash = deployment_metadata.get('merge_base_snapshot')

    if not baseline_hash:
        logger.warning(
            f"No merge_base_snapshot for {artifact_id}. "
            "Using collection as base. Redeploy to enable accurate tracking."
        )
        # Fallback to v1.0 behavior
        return get_current_collection_hash(artifact_id)

    return baseline_hash
```

**Backfill Strategy (Optional):**

For users who want to retroactively enable tracking for existing deployments:

```python
def backfill_merge_base_snapshots():
    """
    Backfill merge_base_snapshot for existing deployments.

    WARNING: This sets baseline to current project state, which may be incorrect
    if project has been modified since deployment.
    """
    deployments = get_all_deployments_without_baseline()

    for deployment in deployments:
        # Use current project state as baseline (best effort)
        current_hash = hash_service.hash_directory(deployment.project_path)

        deployment.metadata['merge_base_snapshot'] = current_hash
        deployment.metadata['merge_base_timestamp'] = datetime.now().isoformat()
        deployment.metadata['backfilled'] = True  # Flag as backfilled

        save_deployment_metadata(deployment.project_path, deployment.metadata)

        logger.info(f"Backfilled baseline for {deployment.artifact_id}")
```

---

## 7. Integration with v1

### How v1.5 Extends v1.0

**v1.0 (Existing):**
- Snapshot system for version storage (COMPLETE)
- Three-way merge models and UI (COMPLETE)
- Deployment metadata tracking (PARTIAL)
- Web UI components (COMPLETE)

**v1.5 (This Addendum):**
- **Fixes** three-way merge baseline (uses deployed version, not collection)
- **Populates** parent_hash and version_lineage (were NULL)
- **Adds** change_origin field (new)
- **Tracks** modification timestamps (was missing)
- **Enhances** API responses with change attribution (new)
- **Improves** UI with change origin badges (new)

**Relationship:**
- v1.5 is **backward compatible** with v1.0 (graceful degradation)
- v1.5 **completes** the 5% missing from v1.0 (baseline, lineage, modification tracking)
- v1.5 **enhances** v1.0 with new capabilities (change attribution, origin tracking)

**Upgrade Path:**
1. Deploy v1.5 code (no breaking changes)
2. Existing deployments continue to work (fallback to v1.0 behavior)
3. New deployments automatically use v1.5 features
4. Optional: Run backfill script to enable v1.5 for old deployments

---

## 8. Acceptance Criteria

### Critical Success Criteria

**AC-1: Three-Way Merge Uses Correct Baseline**
- [ ] All new deployments store `merge_base_snapshot`
- [ ] `three_way_merge()` retrieves baseline from deployment metadata
- [ ] Merge correctly identifies "local only" changes (no false conflicts)
- [ ] Unit tests pass for all merge scenarios (local only, upstream only, both, neither)

**AC-2: Version Lineage Fully Populated**
- [ ] All new versions have `parent_hash` (except initial deployment)
- [ ] `version_lineage` array is complete and accurate
- [ ] Can traverse from current version to deployment baseline
- [ ] Database queries on version chain complete in <100ms (95th percentile)

**AC-3: Modification Timestamps Tracked**
- [ ] `modification_detected_at` set when drift detected
- [ ] Local modifications create version records with `change_origin=LOCAL_MODIFICATION`
- [ ] API returns "last modified" timestamp separate from "deployed at"

**AC-4: Change Origin Attribution Works**
- [ ] API correctly identifies "upstream", "local", "both", "none"
- [ ] Drift API returns summary counts (upstream_changes, local_changes, conflicts)
- [ ] UI displays color-coded badges in diff viewer
- [ ] Version timeline shows origin labels ("Deployed", "Synced", "Modified", "Merged")

---

### User Experience Criteria

**UX-1: Clear Diff Attribution**
- [ ] User can see at a glance whether diff is upstream or local
- [ ] Badges are color-coded and intuitive (blue=upstream, orange=local, red=conflict)
- [ ] Tooltips explain badge meanings

**UX-2: Version History Clarity**
- [ ] Version timeline shows complete history from deployment to current
- [ ] Each version node shows origin label and timestamp
- [ ] User can identify "when did I modify this?" vs. "when did upstream sync?"

**UX-3: No Regression for Existing Workflows**
- [ ] Old deployments (v1.0) continue to work without errors
- [ ] Warning logged when baseline missing (not error)
- [ ] Migration guide available for users who want to backfill

---

### Technical Criteria

**TC-1: Performance**
- [ ] Version chain queries <100ms (95th percentile)
- [ ] No N+1 query patterns in version traversal
- [ ] Database indexes on `content_hash` and `parent_hash`

**TC-2: Storage Efficiency**
- [ ] Metadata overhead <1% for artifacts >10KB
- [ ] No duplicate content storage for unchanged files

**TC-3: Backward Compatibility**
- [ ] API changes are additive (no removed fields)
- [ ] v1.0 clients continue to work without changes
- [ ] Graceful fallback when `merge_base_snapshot` missing

**TC-4: Test Coverage**
- [ ] Unit tests for all new functions (>80% coverage)
- [ ] Integration tests for end-to-end workflows
- [ ] Performance benchmarks for version queries
- [ ] Frontend tests for UI components

---

## 9. Risks & Mitigations

### Risk 1: Migration Complexity

**Risk:** Existing deployments without `merge_base_snapshot` could cause errors.

**Likelihood:** MEDIUM
**Impact:** HIGH

**Mitigation:**
- Implement graceful fallback to v1.0 behavior (use collection as base)
- Log warnings instead of errors when baseline missing
- Provide backfill script for users who want to retroactively enable tracking
- Document migration path clearly

---

### Risk 2: Performance Regression

**Risk:** Version chain traversal could slow down for large version histories (100+ versions).

**Likelihood:** LOW
**Impact:** MEDIUM

**Mitigation:**
- Add database indexes on `content_hash` and `parent_hash`
- Pre-compute `version_lineage` array (avoid recursive queries)
- Implement pagination for version history API (limit to 50 versions per request)
- Load testing with large version chains before release

---

### Risk 3: Merge Logic Bugs

**Risk:** Three-way merge with new baseline logic could introduce bugs.

**Likelihood:** MEDIUM
**Impact:** HIGH

**Mitigation:**
- Comprehensive unit tests for all merge scenarios
- Integration tests for end-to-end merge workflows
- Manual testing with real-world artifacts
- Gradual rollout (opt-in flag for v1.5 merge logic during beta)

---

### Risk 4: User Confusion

**Risk:** Users don't understand change origin badges or version lineage.

**Likelihood:** MEDIUM
**Impact:** LOW

**Mitigation:**
- Clear tooltips explaining badge meanings
- User guide with examples and screenshots
- Onboarding flow highlighting new features
- Feedback loop to improve UI/UX based on user testing

---

## 10. Future Enhancements (Out of Scope)

### Conflict Auto-Resolution Strategies

**Description:** Automatically resolve certain types of conflicts (e.g., "always keep local", "always keep upstream").

**Effort:** 3-5 days
**Priority:** LOW

**Why Out of Scope:** Requires user preference system and complex conflict detection heuristics.

---

### Visual Merge Editor

**Description:** In-browser merge editor with line-by-line conflict resolution (like GitHub conflict editor).

**Effort:** 1-2 weeks
**Priority:** MEDIUM

**Why Out of Scope:** Significant UI/UX work; v1.5 focuses on backend tracking, not UI tooling.

---

### Multi-Branch Version History

**Description:** Support for multiple version branches (e.g., "production", "staging", "development").

**Effort:** 2-3 weeks
**Priority:** LOW

**Why Out of Scope:** Adds significant complexity; current linear version chain is sufficient for MVP.

---

### Version Tagging/Labeling

**Description:** Allow users to tag versions (e.g., "v1.0 stable", "pre-refactor").

**Effort:** 3-5 days
**Priority:** LOW

**Why Out of Scope:** Nice-to-have feature; not critical for change attribution.

---

## 11. Success Metrics & KPIs

### Technical Metrics

| Metric | Baseline (v1.0) | Target (v1.5) | Measurement |
|--------|----------------|---------------|-------------|
| **Merge Accuracy** | 70% (false conflicts) | 95%+ correct conflict detection | Unit test pass rate |
| **Version Chain Completeness** | 0% (parent_hash=NULL) | 100% | Database query validation |
| **Modification Tracking** | 0% (not set) | 100% | Drift detection logs |
| **API Response Time** | ~50ms | <100ms with attribution | Performance benchmarks |
| **Storage Overhead** | ~0.5% | <1% | Metadata size vs. content size |

---

### User Experience Metrics

| Metric | Baseline (v1.0) | Target (v1.5) | Measurement |
|--------|----------------|---------------|-------------|
| **Change Attribution Understanding** | N/A (not tracked) | 90%+ users understand diff origin | User testing feedback |
| **Merge Workflow Clarity** | 60% users confused | 90%+ users clear on process | User surveys |
| **Feature Adoption** | N/A | 70%+ users view change badges | Analytics (badge hover/click) |
| **Support Requests** | 10/week (merge confusion) | <5/week | Support ticket tracking |

---

## 12. Appendices

### Appendix A: Related Documentation

- **Parent PRD:** `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Implementation Guide:** `/docs/implementation/state-tracking-guide.md` (to be created)
- **API Documentation:** `/docs/api/drift-detection.md` (to be updated)
- **Migration Guide:** `/docs/migration/v1.0-to-v1.5.md` (to be created)

---

### Appendix B: Example Scenarios

**Scenario 1: Clean Upstream Sync**

1. User deploys artifact v1.0 to project (baseline: hash A)
2. Collection syncs from source to v1.1 (hash B, parent=A)
3. User detects drift: Project unchanged (hash A), Collection updated (hash B)
4. Diff shows: "Upstream change" badge on modified files
5. User merges: Base=A, Source=B, Target=A → Result=B (clean merge)

**Scenario 2: Local Modification Only**

1. User deploys artifact v1.0 to project (baseline: hash A)
2. User modifies project → v1.0-custom (hash C, parent=A)
3. Collection unchanged (hash A)
4. Diff shows: "Local change" badge on modified files
5. User merges: Base=A, Source=A, Target=C → Result=C (keep local)

**Scenario 3: Both Changed (Conflict)**

1. User deploys artifact v1.0 to project (baseline: hash A)
2. Collection syncs to v1.1 (hash B, parent=A) - upstream changed README
3. User modifies project → v1.0-custom (hash C, parent=A) - local changed README
4. Diff shows: "Both changed" badge on README.md
5. User merges: Base=A, Source=B, Target=C → Conflict on README.md

---

### Appendix C: Database Schema Migration

**Alembic Migration Script:**

```python
"""Add change_origin and populate parent_hash

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-12-17 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    # Add change_origin enum
    change_origin_enum = postgresql.ENUM(
        'deployment', 'upstream_sync', 'local_modification', 'merge',
        name='changeorigin'
    )
    change_origin_enum.create(op.get_bind())

    # Add change_origin column
    op.add_column('artifact_versions',
        sa.Column('change_origin', change_origin_enum, nullable=True)
    )

    # Backfill existing versions with 'deployment' origin
    op.execute(
        "UPDATE artifact_versions SET change_origin = 'deployment' "
        "WHERE change_origin IS NULL"
    )

    # Make column non-nullable
    op.alter_column('artifact_versions', 'change_origin', nullable=False)

    # Add indexes
    op.create_index(
        'ix_artifact_versions_content_hash',
        'artifact_versions',
        ['content_hash']
    )
    op.create_index(
        'ix_artifact_versions_parent_hash',
        'artifact_versions',
        ['parent_hash']
    )

def downgrade():
    op.drop_index('ix_artifact_versions_parent_hash', 'artifact_versions')
    op.drop_index('ix_artifact_versions_content_hash', 'artifact_versions')
    op.drop_column('artifact_versions', 'change_origin')

    change_origin_enum = postgresql.ENUM(name='changeorigin')
    change_origin_enum.drop(op.get_bind())
```

---

### Appendix D: Effort Estimation Summary

| Phase | Duration | Effort (hours) | Priority |
|-------|----------|----------------|----------|
| **Phase 1: Core Baseline Support** | 2-3 days | 16-24 | HIGH |
| **Phase 2: Version Lineage Tracking** | 1-2 days | 8-16 | HIGH |
| **Phase 3: Modification Tracking** | 1 day | 6-8 | MEDIUM |
| **Phase 4: Change Attribution** | 1-2 days | 8-12 | MEDIUM |
| **Phase 5: Web UI Integration** | 2 days | 12-16 | MEDIUM |
| **Phase 6: Testing & Validation** | 2-3 days | 12-20 | HIGH |
| **TOTAL** | **8-13 days** | **62-96 hours** | - |

**Recommended Execution:**
- Week 1: Phase 1 + Phase 2 (critical infrastructure)
- Week 2: Phase 3 + Phase 4 + Phase 5 (enhancements + UI)
- Week 3: Phase 6 (testing + documentation + release prep)

---

## Document Metadata

**Created:** 2025-12-17
**Last Updated:** 2025-12-17
**Version:** 1.5.0
**Status:** Planned
**Owner:** SkillMeat Development Team
**Reviewers:** TBD
**Approved By:** TBD
**Approval Date:** TBD

**Change Log:**
- 2025-12-17: Initial draft (v1.5.0)
