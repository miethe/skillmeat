---
title: SkillMeat Versioning - Phase 2 Quick Start
description: Implementation guide for Phase 2 versioning. Covers ArtifactVersion model, version tracking, integration points, and testing checklist
audience: developers
tags:
  - versioning
  - phase-2
  - artifact-version
  - quick-start
  - implementation
category: guides
created: 2025-12-18
updated: 2025-12-18
status: active
related:
  - /docs/user/guides/sync-quick-reference.md
---

# SkillMeat Versioning - Quick Start for Phase 2 Implementation

## TL;DR - What You Need to Know

**No ArtifactVersion model exists yet.** Version tracking is currently file-based:
- Snapshots stored as tarballs in `~/.skillmeat/snapshots/{collection}/`
- Deployment metadata in `./.claude/.skillmeat-deployed.toml`
- Audit logs in `~/.skillmeat/audit/{collection}_rollback_audit.toml`

**Phase 1 (DONE)**: Three-way merge infrastructure, snapshots, drift detection
**Phase 2 (TODO)**: Structured ArtifactVersion model with parent/child relationships

---

## Critical File Paths

```
Core Versioning:
  skillmeat/core/version.py              → VersionManager, RollbackAuditTrail
  skillmeat/core/sync.py                 → SyncManager (uses VersionManager)
  skillmeat/core/merge_engine.py         → Three-way merge logic
  skillmeat/core/diff_engine.py          → File diffing

Storage Layer:
  skillmeat/storage/snapshot.py          → Snapshot, SnapshotManager
  skillmeat/storage/deployment.py        → DeploymentTracker

Database:
  skillmeat/cache/models.py              → Artifact model (version fields exist!)
  skillmeat/cache/migrations/versions/   → Migration files

Data Models:
  skillmeat/models.py                    → Dataclasses (lines 109-1050)
    - ThreeWayDiffResult (212-244)
    - ConflictMetadata (110-158)
    - RollbackResult (787-885)
    - RollbackAuditEntry (944-1050)
    - DriftDetectionResult (622-669)
    - DeploymentRecord/Metadata (582-620)
```

---

## Understanding Current Version Tracking

### Snapshots (Current Implementation)

```python
# In skillmeat/storage/snapshot.py
@dataclass
class Snapshot:
    id: str                  # "20251217_143022_abc123"
    timestamp: datetime      # When created
    message: str             # User description
    collection_name: str     # Which collection
    artifact_count: int      # How many artifacts
    tarball_path: Path       # ~/.skillmeat/snapshots/collection/snap.tar.gz
```

**Location on disk**:
```
~/.skillmeat/snapshots/
  └── {collection_name}/
      ├── snapshots.toml           # Metadata index
      ├── 20251217_143022_abc.tar.gz
      ├── 20251217_143100_def.tar.gz
      └── ...
```

### Deployment Metadata (Current Implementation)

```python
# In .claude/.skillmeat-deployed.toml
[deployed]
  [[deployed.items]]
  name = "canvas-design"
  type = "skill"
  source = "github:user/repo/path"
  version = "v1.2.0"
  sha = "abc123def456..."  # Content hash from collection
  deployed_at = "2025-12-17T14:30:22Z"
  deployed_from = "default"
```

**This is the "baseline" for drift detection**

### Three-Way Drift Detection

```
Phase 1 Comparison:
  deployed.sha      ← baseline (what was deployed)
  collection_sha    ← upstream (current collection version)
  project_sha       ← local (current project version)

Result:
  - If only collection changed: "outdated" (update needed)
  - If only project changed: "modified" (local edits)
  - If both changed: "conflict" (three-way merge needed)
```

---

## Artifact Model - Version Fields Ready

**File**: `skillmeat/cache/models.py` (lines 186-322)

```python
class Artifact(Base):
    # These fields EXIST but versioning logic is still file-based:
    deployed_version: Optional[str]     # e.g., "v1.2.0"
    upstream_version: Optional[str]     # Latest available
    is_outdated: bool                   # deployed != upstream
    local_modified: bool                # Has local changes

    # Already using:
    content_hash: Optional[str]         # SHA256 for comparison
```

**Current State**: These fields are populated but versioning logic doesn't use them for history/parent-child relationships yet.

---

## Key Integration Points

### SyncManager Uses VersionManager

**File**: `skillmeat/core/sync.py` (lines 38-63)

```python
class SyncManager:
    def __init__(self, ..., version_manager=None):
        self._version_mgr = version_manager

    @property
    def version_mgr(self):
        """Lazy-load VersionManager on first access"""
        if self._version_mgr is None:
            from skillmeat.core.version import VersionManager
            self._version_mgr = VersionManager(
                collection_mgr=self.collection_mgr,
                snapshot_mgr=self.snapshot_mgr,
            )
        return self._version_mgr
```

**Implication**: Any sync operation can automatically create snapshots for recovery

### VersionManager Creates Safety Snapshots

**File**: `skillmeat/core/version.py`

Operations that auto-snapshot:
- `merge()` - creates safety snapshot before merge
- `rollback()` - creates safety snapshot before rollback
- Intelligent rollback preserves local changes via three-way merge

---

## Dataclasses You'll Need for Phase 2

### RollbackAuditEntry
**File**: `skillmeat/models.py` (lines 944-1050)

Every rollback creates this record:
```python
@dataclass
class RollbackAuditEntry:
    id: str                          # "rb_20251217_143022"
    timestamp: datetime
    collection_name: str
    source_snapshot_id: str          # Safety snapshot
    target_snapshot_id: str          # Target snapshot
    operation_type: Literal["simple", "intelligent", "selective"]
    files_restored: List[str]
    files_merged: List[str]          # Via three-way merge
    conflicts_resolved: List[str]
    conflicts_pending: List[str]     # Need manual resolution
    preserve_changes_enabled: bool
    selective_paths: Optional[List[str]]
    success: bool
    error: Optional[str]
    metadata: Dict[str, Any]
```

### ConflictMetadata
**File**: `skillmeat/models.py` (lines 110-158)

Describes a conflicting file:
```python
@dataclass
class ConflictMetadata:
    file_path: str
    conflict_type: Literal["content", "deletion", "both_modified", "add_add"]
    base_content: Optional[str]      # Ancestor
    local_content: Optional[str]     # Project version
    remote_content: Optional[str]    # Collection version
    auto_mergeable: bool
    merge_strategy: Optional[Literal["use_local", "use_remote", "use_base", "manual"]]
```

### DriftDetectionResult
**File**: `skillmeat/models.py` (lines 622-669)

What changed and how:
```python
@dataclass
class DriftDetectionResult:
    artifact_name: str
    drift_type: Literal["modified", "outdated", "conflict", "added", "removed", "version_mismatch"]
    collection_sha: Optional[str]
    project_sha: Optional[str]
    collection_version: Optional[str]
    project_version: Optional[str]
    last_deployed: Optional[str]     # ISO timestamp
    recommendation: str               # What to do about it
```

---

## What Phase 2 Needs to Add

### 1. New ArtifactVersion Model
Create new migration:
```python
class ArtifactVersion(Base):
    """Version record for artifact."""
    id: str = PK()
    artifact_id: str = FK(Artifact.id)
    version_tag: str          # "v1.2.0" or "snap_20251217"
    version_sha: str          # Content hash
    parent_version_id: Optional[str] = FK(self)  # Parent version
    created_at: datetime
    created_by: str           # "system" or user
    snapshot_id: str          # Link to tarball
    merge_strategy: Optional[str]
    metadata: json
```

### 2. Update VersionManager
- Create ArtifactVersion record on snapshot creation
- Track parent relationships
- Query version history for merge strategy selection

### 3. Update Artifact Model
- Add `current_version_id: Optional[str]` FK to ArtifactVersion
- Stop storing version strings, use relationship instead

### 4. New Endpoints (API)
- `GET /api/v1/artifacts/{id}/versions` - version history
- `POST /api/v1/artifacts/{id}/versions/{version_id}/merge` - merge to version
- `GET /api/v1/artifacts/{id}/versions/{version_id}/diff` - preview

---

## Testing Checklist

When implementing Phase 2:

- [ ] Create migration file
- [ ] Model relationships work (parent/child)
- [ ] VersionManager creates records on snapshot
- [ ] Version history queryable
- [ ] Merge preserves parent links
- [ ] Rollback creates new ArtifactVersion
- [ ] Audit trail still records operations
- [ ] Existing Phase 1 flows still work
- [ ] Database migrations apply cleanly
- [ ] ORM relationships lazy-load correctly

---

## Common Queries You'll Need

### Get version history for artifact
```python
# Pseudo-code - implement in repository layer
session.query(ArtifactVersion)\
    .filter(ArtifactVersion.artifact_id == artifact_id)\
    .order_by(ArtifactVersion.created_at.desc())\
    .all()
```

### Find common ancestor for three-way merge
```python
# New method for VersionManager
def find_common_ancestor(version_a_id, version_b_id) -> Optional[str]:
    """Find LCA in version DAG"""
    # Trace parents from both versions
    # Find first common node
```

### Get merge strategy for versions
```python
# New method for VersionManager
def get_merge_strategy(from_version_id, to_version_id) -> str:
    """Based on version history, recommend merge strategy"""
    # Query relationship distance
    # Check metadata for stored strategies
    # Return recommendation
```

---

## Phase 1 Reference: What Already Works

Phase 1 (just merged in `e00864c`) includes:

✅ **Three-Way Merge**
```python
# skillmeat/core/merge_engine.py
result = merge_engine.three_way_merge(base, local, remote)
```

✅ **Automatic Safety Snapshots**
```python
# skillmeat/core/version.py
version_mgr.rollback(snapshot_id, preserve_changes=True)
# Creates safety snapshot automatically
```

✅ **Conflict Detection**
```python
# skillmeat/core/diff_engine.py
diff = diff_engine.three_way_diff(base_path, local_path, remote_path)
# Returns ConflictMetadata[] for conflicts
```

✅ **Audit Trail**
```python
# Automatically recorded by VersionManager
audit_trail.record(RollbackAuditEntry(...))
```

---

## Glossary

| Term | Meaning | Location |
|------|---------|----------|
| **Snapshot** | Point-in-time tarball of collection | ~/.skillmeat/snapshots/ |
| **Deployment** | Record of what was deployed to project | ./.claude/.skillmeat-deployed.toml |
| **Drift** | Difference between deployed/collection/project | DriftDetectionResult |
| **Three-way merge** | Merge using base + local + remote | MergeEngine |
| **Safety snapshot** | Pre-operation backup for recovery | RollbackResult.safety_snapshot_id |
| **Audit entry** | Record of rollback operation | RollbackAuditEntry |
| **Base/Ancestor** | Original state before changes | ConflictMetadata.base_content |
| **Local** | Project's current state | ConflictMetadata.local_content |
| **Remote** | Collection's current state | ConflictMetadata.remote_content |
| **SHA** | Content hash (SHA256) | Artifact, DeploymentRecord |
| **Version tag** | Human-readable version | "v1.2.0", "latest", snapshot ID |

---

## Next Steps for Implementation

1. **Read** `skillmeat/core/version.py` - understand VersionManager architecture
2. **Read** `skillmeat/models.py` lines 109-1050 - understand dataclasses
3. **Review** migration structure in `skillmeat/cache/migrations/versions/`
4. **Create** new migration for ArtifactVersion model
5. **Update** VersionManager to populate new records
6. **Add** repository methods for version queries
7. **Update** SyncManager to use version history
8. **Add** API endpoints for version management
9. **Write** tests for version history and merge strategies

---

## Questions? Check These Files First

| Question | File | Lines |
|----------|------|-------|
| How do snapshots work? | skillmeat/storage/snapshot.py | 40-200 |
| How is drift detected? | skillmeat/core/sync.py | 65-200 |
| How does merge work? | skillmeat/core/merge_engine.py | Full file |
| How are rollbacks audited? | skillmeat/core/version.py | 34-145 |
| What dataclasses exist? | skillmeat/models.py | 109-1050 |
| What's the DB schema? | skillmeat/cache/models.py | 186-322 |
| How are migrations done? | skillmeat/cache/migrations/versions/001_initial_schema.py | Full file |
