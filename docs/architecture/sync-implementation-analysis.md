---
title: SkillMeat Sync Implementation Analysis
description: Technical analysis of the SkillMeat sync system including artifact state representation, change detection, deployment tracking, and three-way merge architecture
audience: developers
tags:
  - sync
  - implementation-analysis
  - architecture
  - versioning
  - deployment
  - change-detection
created: 2025-12-17
updated: 2025-12-18
category: Architecture
status: stable
related_documents:
  - versioning-diagrams.md
  - artifact-state-transitions.md
---

# SkillMeat Sync Implementation Analysis

**Analysis Date**: 2025-12-18
**Scope**: Current sync architecture, artifact tracking, change detection, and version tracking
**Purpose**: Foundation for understanding versioning and merge system implementation (v1.5)

---

## Executive Summary

SkillMeat uses a **three-way sync model** with SHA-256 content hashing to track artifact state across three locations:
1. **Collection** (source of truth for user-managed artifacts)
2. **Project** (deployed artifacts that may have local modifications)
3. **Deployment Metadata** (baseline state at deployment time)

The sync system detects **drift** (differences from baseline), categorizes it, and provides multiple resolution strategies (overwrite, merge, fork). Version snapshots are automatically created during deploy/sync operations.

---

## 1. Artifact State Representation

### 1.1 Core State Tracking

**Three-Way State Model**:
- **Deployed SHA**: `deployment.content_hash` - Content hash at deployment time (baseline)
- **Collection SHA**: Computed from current collection artifact files
- **Project SHA**: Computed from current project artifact files

```python
# From core/deployment.py: Deployment class
@dataclass
class Deployment:
    artifact_name: str
    artifact_type: str
    from_collection: str
    deployed_at: datetime
    artifact_path: Path  # Relative within .claude/ (e.g., "commands/review.md")
    content_hash: str    # SHA-256 at deployment time
    local_modifications: bool = False
    parent_hash: Optional[str] = None  # Version lineage
    version_lineage: List[str] = field(default_factory=list)  # Hashes (newest first)
    last_modified_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
```

**Stored In**: `.claude/.skillmeat-deployed.toml`

```toml
[[deployed]]
artifact_name = "my-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-12-17T10:30:00+00:00"
artifact_path = "skills/my-skill"
content_hash = "abc123def456..."  # SHA-256
local_modifications = false
```

### 1.2 Hash Computation

**Hash Algorithm**: SHA-256 of all files in artifact directory

```python
# From core/sync.py: SyncManager._compute_artifact_hash()
def _compute_artifact_hash(artifact_path: Path) -> str:
    """Compute SHA-256 hash of artifact directory.

    1. Get all files in artifact (sorted for consistency)
    2. Hash: relative_path + file_content for each file
    3. Return: hexadecimal digest (64 chars)
    """
    hasher = hashlib.sha256()
    file_paths = sorted(artifact_path.rglob("*"))
    for file_path in file_paths:
        if file_path.is_file():
            rel_path = file_path.relative_to(artifact_path)
            hasher.update(str(rel_path).encode("utf-8"))
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
```

**Properties**:
- ✅ Deterministic: Same content = same hash
- ✅ Sensitive to file additions, deletions, modifications
- ✅ Sensitive to file path changes (relative path included)
- ⚠️ Includes binary files without special handling
- ⚠️ Skips unreadable files with warning (non-fatal)

---

## 2. Change Detection System

### 2.1 Drift Detection Algorithm

**Three-way conflict detection** compares three SHAs:

```python
# From core/sync.py: SyncManager.check_drift()

# Deployed baseline (base version)
base_sha = deployed.sha

# Current collection state (upstream)
collection_sha = self._compute_artifact_hash(collection_artifact["path"])

# Current project state (local)
current_project_sha = self._compute_artifact_hash(project_artifact_path)

# Detect changes
collection_changed = collection_sha != base_sha
project_changed = current_project_sha != base_sha

# Determine drift type
if collection_changed and project_changed:
    drift_type = "conflict"      # Both sides modified
elif collection_changed:
    drift_type = "outdated"      # Collection updated, project stale
else:
    drift_type = "modified"      # Project locally modified
```

### 2.2 Drift Types

| Type | Condition | Recommendation | Use Case |
|------|-----------|-----------------|----------|
| **modified** | Project changed, collection same | pull_from_project | Captured manual edits |
| **outdated** | Collection changed, project same | push_to_collection | Deploy collection updates |
| **conflict** | Both changed | review_manually | Requires user decision |
| **added** | New in collection, not deployed | deploy_to_project | Deploy new artifact |
| **removed** | Removed from collection | remove_from_project | Clean up project |

### 2.3 Drift Detection Results

```python
# From models.py: DriftDetectionResult
@dataclass
class DriftDetectionResult:
    artifact_name: str
    artifact_type: str
    drift_type: Literal["modified", "outdated", "conflict", "added", "removed", "version_mismatch"]
    collection_sha: Optional[str] = None      # Current collection SHA (None if removed)
    project_sha: Optional[str] = None         # Current project SHA (None if added)
    collection_version: Optional[str] = None
    project_version: Optional[str] = None
    last_deployed: Optional[str] = None       # ISO 8601 timestamp
    recommendation: str = "review_manually"
```

**Populated by** `SyncManager.check_drift()`:
1. Load deployment metadata from `.skillmeat-deployed.toml`
2. For each deployed artifact, compute current SHAs
3. Compare: deployed vs current (collection and project)
4. Generate DriftDetectionResult for each artifact

---

## 3. Deployment Tracking

### 3.1 Deployment Recording

**When Recording Happens**:
- ✅ After successful artifact deployment (`DeploymentManager.deploy_artifacts()`)
- ✅ Updated when artifact re-deployed
- ✅ Removed when artifact undeployed

**Recording Method**:
```python
# From storage/deployment.py: DeploymentTracker.record_deployment()

# 1. Read existing deployments
deployments = DeploymentTracker.read_deployments(project_path)

# 2. Create new Deployment record
deployment = Deployment(
    artifact_name=artifact.name,
    artifact_type=artifact.type.value,
    from_collection=collection_name,
    deployed_at=datetime.now(),
    artifact_path=artifact_path,
    content_hash=collection_sha,  # Hash at deployment time
    local_modifications=False,
)

# 3. Update list (replace if exists, append if new)
# 4. Write atomically to .skillmeat-deployed.toml
```

### 3.2 Metadata File Format

**File**: `.claude/.skillmeat-deployed.toml`

```toml
[[deployed]]
artifact_name = "my-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-12-17T10:30:00+00:00"
artifact_path = "skills/my-skill"
content_hash = "abc123def456..."
local_modifications = false
parent_hash = "def456ghi789..."     # Optional: parent version
version_lineage = ["abc123...", "def456..."]  # Optional: history
```

### 3.3 Backward Compatibility

**Dual Hash Fields**:
```python
# From core/deployment.py: Deployment.to_dict()
result["collection_sha"] = self.content_hash  # Backward compat

# From storage/deployment.py
content_hash = data.get("content_hash") or data.get("collection_sha")
```

Old metadata files using `collection_sha` still work.

---

## 4. Modification Detection

### 4.1 Local Modification Detection

**Method**: `DeploymentTracker.detect_modifications()`

```python
# 1. Get deployment record
deployment = DeploymentTracker.get_deployment(project_path, artifact_name, type)

# 2. Compute current project artifact hash
artifact_full_path = project_path / ".claude" / deployment.artifact_path
current_hash = compute_content_hash(artifact_full_path)

# 3. Compare with deployment hash
return current_hash != deployment.content_hash
```

**Result**:
- `True`: Project file differs from deployed baseline
- `False`: Project file matches deployed baseline

**Used By**:
- Drift detection to distinguish "modified" vs "outdated"
- Deployment status checks
- UI sync status indicators

### 4.2 Modification Tracking Fields

```python
# From core/deployment.py: Deployment
local_modifications: bool = False                    # Current state flag
modification_detected_at: Optional[datetime] = None  # First detection time
last_modified_check: Optional[datetime] = None       # Last check timestamp
```

⚠️ **Note**: These fields are currently placeholders - actual tracking logic needs implementation for versioning system.

---

## 5. Sync Operation Flow

### 5.1 Pull Sync (Project → Collection)

**Direction**: Project modifications → Collection (capture local edits)

**Flow**:
```
1. check_drift()
   ↓ Detects "modified" artifacts (project changed, collection unchanged)
2. Filter to "pullable" drift
   ↓ Only pull artifacts with project modifications
3. Show preview
   ↓ Display artifacts to be synced (with SHAs)
4. For each artifact:
   - _sync_artifact()
   - Apply strategy (overwrite/merge/fork)
   - Copy from project to collection
5. _update_collection_lock()
   ↓ Update manifest/lock files
6. Auto-snapshot (SVCV-002)
   ↓ Capture version after sync
7. Record analytics
```

**Strategies**:
- **overwrite**: Replace collection with project version
- **merge**: Three-way merge (collection as base)
- **fork**: Create new artifact with `-fork` suffix
- **prompt**: Ask user for each artifact

**Conflict Handling**:
- Merge strategy may produce Git-style conflict markers
- Conflicts tracked in `ArtifactSyncResult.conflict_files`
- User can review and resolve manually

### 5.2 Deployment (Collection → Project)

**Direction**: Collection artifacts → Project (deploy updates)

**Flow**:
```
1. Find artifact in collection
   ↓ Resolve by name/type
2. Copy artifact to project
   ↓ `.claude/{type}/{name}`
3. Compute content hash
   ↓ SHA-256 of deployed artifact
4. DeploymentTracker.record_deployment()
   ↓ Write to .skillmeat-deployed.toml
5. Auto-snapshot (SVCV-003)
   ↓ Capture version after deployment
```

**Stored Data**:
- artifact_name, artifact_type
- from_collection (source collection name)
- content_hash (SHA at deployment time)
- deployed_at (ISO 8601 timestamp)
- artifact_path (relative within .claude/)

---

## 6. Version Tracking Integration

### 6.1 Automatic Snapshots

**When Created**:
- ✅ After deployment (`DeploymentManager.deploy_artifacts()`)
- ✅ After sync pull (`SyncManager.sync_from_project()`)
- ✅ Support for pre-sync snapshots (rollback safety)

**Snapshot Message Format**:
```
Auto-deploy: skill1, skill2, and 3 more to /path/to/project at 2025-12-17T10:30:00.000000
Auto-sync from project: skill1, skill2 and 1 more at 2025-12-17T10:30:00.000000
```

**Implementation**:
```python
# From core/deployment.py
snapshot = self.version_mgr.auto_snapshot(
    collection_name=collection.name,
    message=f"Auto-deploy: {artifact_list} to {project_path}...",
)
```

### 6.2 Snapshot Manager Integration

**File**: `skillmeat/storage/snapshot.py` (referenced but not analyzed)

**Used For**:
- Pre-sync snapshot creation (rollback protection)
- Automatic snapshot after successful sync/deploy
- Version lineage tracking

---

## 7. Data Structures Summary

### 7.1 Storage Layer

| Class | Purpose | Location | Format |
|-------|---------|----------|--------|
| `Deployment` | Tracks single artifact deployment | `.skillmeat-deployed.toml` | TOML |
| `DeploymentTracker` | Read/write deployment metadata | Storage layer | Static methods |
| `DeploymentMetadata` | Old metadata format (legacy) | `.skillmeat-deployed.toml` | TOML |

### 7.2 Core Sync Layer

| Class | Purpose |
|-------|---------|
| `SyncManager` | Drift detection, sync operations |
| `DriftDetectionResult` | Single drift result |
| `ArtifactSyncResult` | Single artifact sync result |
| `SyncResult` | Batch sync operation result |

### 7.3 Deployment Layer

| Class | Purpose |
|-------|---------|
| `DeploymentManager` | Deploy/undeploy artifacts |
| `Deployment` | Track artifact deployment state |

---

## 8. Current Limitations and Design Gaps

### 8.1 Three-Way Merge Gaps

**Current Implementation**:
```python
# From core/sync.py: _sync_merge()
merge_result = merge_engine.merge(
    base_path=collection_artifact_path,   # Uses collection as base
    local_path=collection_artifact_path,  # Collection = local
    remote_path=project_artifact_path,    # Project = remote
    output_path=collection_artifact_path, # In-place update
)
```

**Issue**: Base version is **unknown** - uses current collection as base instead of deployed baseline.

**Gap**: Need to track deployed baseline separately for true three-way merge.

### 8.2 Version Lineage Incomplete

**Fields Defined**:
```python
parent_hash: Optional[str] = None           # Parent version
version_lineage: List[str] = field(default_factory=list)  # All versions
```

**Implementation Status**: ⚠️ **Placeholder only** - logic not fully implemented.

### 8.3 Modification Tracking Incomplete

**Fields Defined**:
```python
local_modifications: bool = False
modification_detected_at: Optional[datetime] = None
last_modified_check: Optional[datetime] = None
```

**Implementation Status**: ⚠️ **Fields written but logic minimal** - needs version system integration.

### 8.4 Version Information Gap

**Current Limitation**:
- `_get_artifact_version()` extracts from artifact metadata file
- No version tracking **across deployments**
- No version history stored with deployment metadata
- Cannot distinguish version changes vs content changes

### 8.5 Sync Preconditions Not Enforced

**Checked in** `validate_sync_preconditions()` but not enforced by sync methods:
- Deployment metadata must exist
- Collection must be accessible
- Project must have `.claude/` directory

Could fail during sync without validation.

---

## 9. Key Data Flow Diagrams

### 9.1 Deployment to Project

```
Collection Artifact
    ↓
DeploymentManager.deploy_artifacts()
    ↓ Copy to project
Project Artifact (.claude/skills/name/)
    ↓ Compute hash
content_hash = SHA-256(project artifact)
    ↓ Record
DeploymentTracker.record_deployment()
    ↓ Write
.skillmeat-deployed.toml
    {
        artifact_name, artifact_type,
        from_collection, content_hash,
        deployed_at, artifact_path
    }
```

### 9.2 Drift Detection

```
.skillmeat-deployed.toml (baseline)
    ↓ Load deployed.sha (base)
Drift Detection
    ↓ Compute:
    - collection_sha = hash(collection artifact)
    - project_sha = hash(project artifact)
    ↓ Compare:
    - collection_changed = (collection_sha != deployed.sha)
    - project_changed = (project_sha != deployed.sha)
    ↓ Categorize:
    - Both changed → CONFLICT
    - Collection only → OUTDATED
    - Project only → MODIFIED
    ↓ Return
DriftDetectionResult[]
```

### 9.3 Pull Sync Flow

```
check_drift()
    ↓ Identify "modified" (local changes)
Display preview
    ↓ Show SHAs to be synced
Confirm with user
    ↓ User chooses strategy
For each artifact:
    ├─ overwrite
    │  └─ rm collection; cp project → collection
    ├─ merge
    │  └─ 3-way merge (collection, deployed, project)
    └─ fork
       └─ cp project → collection-fork
    ↓ Update lock files
    ↓ Create auto-snapshot
    ↓ Record analytics
    ↓ Return SyncResult
```

---

## 10. Integration Points with Versioning System

### 10.1 Snapshot Integration (SVCV-002, SVCV-003)

**Auto-snapshots Created**:
- **SVCV-003**: After deployment (captures deployed artifacts)
- **SVCV-002**: After sync pull (captures merged state)

**Message Format**: Includes artifact names and timestamp

**Versioning System Use**:
```python
snapshot = self.version_mgr.auto_snapshot(
    collection_name=collection_name,
    message=message,
)
```

### 10.2 Deployment Metadata as Baseline

**Deployment records serve as**:
1. **Baseline for three-way merge** (currently underutilized)
2. **Version reference** for drift detection
3. **Audit trail** of deployment timestamps
4. **Source collection tracking** (from_collection)

### 10.3 Hash Tracking for Version Chains

**Fields Available**:
```python
parent_hash: Optional[str] = None
version_lineage: List[str] = field(default_factory=list)
```

**Purpose**: Track artifact version history across deployments.

**Current Status**: Defined but not actively populated.

---

## 11. Recommended Enhancements for v1.5

### 11.1 Improve Three-Way Merge

**Action**: Store deployed baseline separately
```python
# Add to Deployment:
deployed_baseline: Optional[str] = None  # Path to temp baseline
```

### 11.2 Implement Version Lineage

**Action**: Populate version_lineage when recording deployment
```python
# Update: If previous deployment exists, set as parent
# Maintain lineage chain: [current, parent, grandparent, ...]
```

### 11.3 Enhance Modification Tracking

**Action**: Populate modification_detected_at when first detected
```python
# In check_drift():
if drift.drift_type == "modified":
    deployment.modification_detected_at = datetime.now()
    deployment.last_modified_check = datetime.now()
```

### 11.4 Validate Sync Preconditions

**Action**: Call validate_sync_preconditions() at sync start
```python
# In sync_from_project():
issues = self.validate_sync_preconditions(project_path)
if issues:
    raise ValueError(f"Sync preconditions failed: {issues}")
```

---

## 12. References

**Key Files**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py` - Main sync logic
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py` - Deployment tracking
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py` - Deployment persistence
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/models.py` - Data models
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_sync.py` - Sync tests

**Related Tests**:
- `tests/test_sync.py` - Hash computation, drift detection
- `tests/test_sync_pull.py` - Pull sync operations
- `tests/test_sync_rollback.py` - Rollback behavior
- `tests/integration/test_sync_flow.py` - End-to-end sync
