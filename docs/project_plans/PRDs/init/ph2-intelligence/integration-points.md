---
title: Sync & Versioning System Integration Points
description: Technical specification for integrating sync system with versioning/merge system v1.5. Covers 8 key integration points and implementation patterns.
phase: 2
status: reference
category: technical-specification
audience: developers
tags:
  - sync-integration
  - versioning-system
  - three-way-merge
  - snapshot-integration
  - implementation-guide
created: 2025-12-17
updated: 2025-12-18
related_documents:
  - versioning-analysis-index.md
  - task-2.4-implementation.md
---

# Sync & Versioning System Integration Points

**Document Purpose**: Identify exactly where sync system must integrate with the versioning/merge system v1.5

---

## 1. Artifact State Representation Interface

### 1.1 Current State Snapshot

**What the sync system provides**:
```python
# From sync.py and deployment.py

class Deployment:
    artifact_name: str
    artifact_type: str
    from_collection: str
    deployed_at: datetime
    artifact_path: Path
    content_hash: str          # ← SHA-256 baseline
    local_modifications: bool
    parent_hash: Optional[str]  # ← Version reference
    version_lineage: List[str]  # ← History chain
    last_modified_check: Optional[datetime]
    modification_detected_at: Optional[datetime]

class DriftDetectionResult:
    artifact_name: str
    artifact_type: str
    drift_type: Literal["modified", "outdated", "conflict", "added", "removed"]
    collection_sha: Optional[str]    # ← Current state
    project_sha: Optional[str]       # ← Current state
    collection_version: Optional[str]
    project_version: Optional[str]
    last_deployed: Optional[str]
    recommendation: str
```

**For Versioning System**:
- ✅ Use `content_hash` as version identifier
- ✅ Use `parent_hash` to link versions
- ✅ Use `version_lineage` as history
- ✅ Use `drift_type` to determine version strategy
- ✅ Use `collection_sha`, `project_sha` for merge analysis

### 1.2 What Needs to Change

**Add to Deployment**:
```python
# Track versioning metadata
snapshot_id: Optional[str] = None              # Link to snapshot (SVCV-002/003)
version_tag: Optional[str] = None              # Manual version tag (v1.2.0)
is_major_change: bool = False                  # For semantic versioning
merge_base_snapshot: Optional[str] = None      # For conflict resolution
```

---

## 2. Hash-Based Version Tracking

### 2.1 Current Implementation

**Hash Computation** (core/sync.py):
```python
def _compute_artifact_hash(artifact_path: Path) -> str:
    """SHA-256 of all files in artifact directory."""
    hasher = hashlib.sha256()
    file_paths = sorted(artifact_path.rglob("*"))
    for file_path in file_paths:
        if file_path.is_file():
            rel_path = file_path.relative_to(artifact_path)
            hasher.update(str(rel_path).encode("utf-8"))
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
```

**Used for**:
- ✅ Baseline at deployment
- ✅ Change detection
- ✅ Conflict identification

### 2.2 Integration with Version System

**Hashes represent**:
1. **Artifact version identity** - Hash = version ID
2. **Content authenticity** - Same hash = same content
3. **Change detection** - Different hash = changed

**Versioning system should**:
- Use hash as canonical version identifier
- Never change hash for same content
- Create new hash for any modification
- Link hashes in version chain: v2 (hash_B) ← v1 (hash_A)

**Implementation**:
```python
# In version_manager.py or versioning system
class ArtifactVersion:
    content_hash: str                          # SHA-256 (immutable)
    version_number: Optional[str]              # "1.2.0" (semantic)
    parent_hash: Optional[str]                 # Previous version
    created_at: datetime
    created_by: str                            # "deploy" or "sync" or "manual"
    snapshot_id: Optional[str]                 # Link to backup
    commit_message: Optional[str]              # Why changed
```

---

## 3. Snapshot Integration Points

### 3.1 Current Auto-Snapshot Triggers

**SVCV-003: After Deployment**
```python
# From deployment.py: DeploymentManager.deploy_artifacts()
snapshot = self.version_mgr.auto_snapshot(
    collection_name=collection.name,
    message=f"Auto-deploy: {artifact_list} to {project_path}...",
)
# Records: artifact names, target project, timestamp
```

**SVCV-002: After Pull Sync**
```python
# From sync.py: SyncManager.sync_from_project()
snapshot = self.version_mgr.auto_snapshot(
    collection_name=collection_name,
    message=f"Auto-sync from project: {artifact_list}...",
)
# Records: synced artifacts, strategy used, merge result
```

### 3.2 Enhanced Integration Needed

**Snapshot Should Store**:
1. **Content baseline**: Full artifact state at snapshot time
2. **Metadata**: Which artifacts, which versions, why created
3. **Lineage**: Links to previous snapshots
4. **Revert info**: Can restore any snapshot

**For Conflict Resolution**:
```python
# Pre-sync snapshot (rollback safety)
snapshot = self.snapshot_mgr.create_snapshot(
    collection_path=collection_path,
    collection_name=collection_name,
    message="Pre-sync snapshot (automatic)",
    purpose="rollback",  # ← New: purpose flag
)

# Store snapshot ID in deployment for three-way merge
deployment.merge_base_snapshot = snapshot.id
```

**For Version History**:
```python
# Link snapshot to deployment version
deployment.snapshot_id = snapshot.id

# Allows:
# - Browse version by snapshot
# - Restore to any previous version
# - Compare snapshots
```

### 3.3 Snapshot Metadata Enhancement

```python
# In snapshot.py (or models.py)
class Snapshot:
    id: str
    collection_name: str
    message: str
    created_at: datetime
    artifacts: Dict[str, ArtifactSnapshotInfo]  # ← NEW

class ArtifactSnapshotInfo:
    artifact_name: str
    artifact_type: str
    content_hash: str                           # ← NEW
    source: str                                 # ← "deploy", "sync", "manual"
    deployment_metadata: Dict[str, Any]         # ← NEW
```

---

## 4. Three-Way Merge Support

### 4.1 Current Gap

**Problem**: Three-way merge lacks baseline version

```python
# Current implementation (sync.py: _sync_merge)
merge_engine.merge(
    base_path=collection_artifact_path,        # ❌ WRONG: current collection
    local_path=collection_artifact_path,       # ❌ Same as base
    remote_path=project_artifact_path,
    output_path=collection_artifact_path,
)

# Should be:
merge_engine.merge(
    base_path=deployed_artifact_path,          # ✅ Deployed baseline
    local_path=collection_artifact_path,       # ✅ Upstream changes
    remote_path=project_artifact_path,         # ✅ Local changes
    output_path=collection_artifact_path,
)
```

### 4.2 Solution: Store Deployment Baseline

**Option A: Temporary File**
```python
# During deployment, save baseline
deployed_baseline = temp_dir / "baseline"
shutil.copytree(collection_artifact_path, deployed_baseline)

# Store path in deployment metadata
deployment.baseline_snapshot = str(deployed_baseline.resolve())

# Use for merge:
merge_engine.merge(
    base_path=Path(deployment.baseline_snapshot),
    local_path=collection_artifact_path,
    remote_path=project_artifact_path,
    output_path=collection_artifact_path,
)
```

**Option B: Snapshot-Based Baseline**
```python
# Create snapshot at deployment time
baseline_snapshot = self.snapshot_mgr.create_snapshot(
    collection_path=collection_path,
    message=f"Baseline for {artifact_name}",
    purpose="merge_base",
)

# Store snapshot ID
deployment.merge_base_snapshot = baseline_snapshot.id

# Reconstruct for merge:
baseline_artifact = self.snapshot_mgr.extract_artifact(
    baseline_snapshot.id,
    artifact_name,
    artifact_type
)
merge_engine.merge(
    base_path=baseline_artifact,
    local_path=collection_artifact_path,
    remote_path=project_artifact_path,
    output_path=collection_artifact_path,
)
```

**Option B is better** because:
- ✅ Integrates with snapshot system
- ✅ Provides audit trail
- ✅ Enables version browsing
- ✅ Supports rollback
- ❌ Slightly more overhead

### 4.3 Integration Points

```python
# In sync.py: _sync_merge()
def _sync_merge(self, project_artifact_path, collection_artifact_path, artifact_name):
    # Get deployment for baseline
    deployment = self._get_deployment(artifact_name)

    if deployment.merge_base_snapshot:
        # Reconstruct baseline from snapshot
        base_path = self.snapshot_mgr.extract_artifact(
            deployment.merge_base_snapshot,
            artifact_name,
            deployment.artifact_type
        )
    else:
        # Fallback (warn user)
        logger.warning(f"No merge baseline for {artifact_name}, using collection as base")
        base_path = collection_artifact_path

    # Three-way merge with proper baseline
    merge_result = self.merge_engine.merge(
        base_path=base_path,
        local_path=collection_artifact_path,
        remote_path=project_artifact_path,
        output_path=collection_artifact_path,
    )

    return ArtifactSyncResult(
        artifact_name=artifact_name,
        success=merge_result.success or not merge_result.has_conflicts,
        has_conflict=merge_result.has_conflicts,
        conflict_files=[c.file_path for c in merge_result.conflicts],
    )
```

---

## 5. Version Lineage Chain

### 5.1 Current Placeholders

```python
# From deployment.py: Deployment class
parent_hash: Optional[str] = None
version_lineage: List[str] = field(default_factory=list)
```

**Currently**: Defined but not populated

### 5.2 Population Logic

**When Recording Deployment**:
```python
# In storage/deployment.py: DeploymentTracker.record_deployment()

# 1. Load existing deployment
existing = DeploymentTracker.get_deployment(project_path, artifact_name, type)

# 2. Compute new hash
new_hash = compute_content_hash(dest_path)

# 3. Create new record with lineage
if existing:
    new_record = Deployment(
        # ... other fields ...
        content_hash=new_hash,
        parent_hash=existing.content_hash,  # ← Link to previous
        version_lineage=[
            new_hash,
            *existing.version_lineage  # ← Prepend new hash
        ],
    )
else:
    new_record = Deployment(
        # ... other fields ...
        content_hash=new_hash,
        parent_hash=None,
        version_lineage=[new_hash],
    )

# 4. Store
DeploymentTracker.write_deployments(project_path, [new_record])
```

### 5.3 Versioning System Usage

```python
# In version_manager.py
class VersionManager:
    def get_version_history(self, artifact_name: str) -> List[ArtifactVersion]:
        """Get version chain from deployment records."""
        deployment = DeploymentTracker.get_deployment(...)

        versions = []
        for hash in deployment.version_lineage:
            version = ArtifactVersion(
                content_hash=hash,
                version_number=self._derive_version_number(hash),
                created_at=self._get_creation_time(hash),
                # ...
            )
            versions.append(version)

        return versions

    def compare_versions(self, from_hash: str, to_hash: str):
        """Compare two versions in chain."""
        # Use snapshots to reconstruct versions
        # Diff them
        # Return changes
```

---

## 6. Modification Tracking Enhancement

### 6.1 Current Fields (Unused)

```python
# From deployment.py: Deployment
local_modifications: bool = False
modification_detected_at: Optional[datetime] = None
last_modified_check: Optional[datetime] = None
```

### 6.2 Population Logic

**In drift detection** (sync.py):
```python
# When detecting "modified" drift
if drift_type == "modified":
    deployment.local_modifications = True

    if not deployment.modification_detected_at:
        # First time detecting modification
        deployment.modification_detected_at = datetime.now()

    # Always update check timestamp
    deployment.last_modified_check = datetime.now()

    # Save updated deployment
    DeploymentTracker.write_deployments(project_path, deployments)
```

### 6.3 Versioning System Usage

```python
# In version_manager.py
def analyze_artifact_timeline(self, artifact_name: str):
    """Show when artifact was deployed, modified, synced."""
    deployment = DeploymentTracker.get_deployment(...)

    timeline = {
        "deployed_at": deployment.deployed_at,
        "first_modification": deployment.modification_detected_at,
        "last_modification_check": deployment.last_modified_check,
        "is_currently_modified": deployment.local_modifications,
        "version_count": len(deployment.version_lineage),
        "parent_artifact": deployment.parent_hash,
    }

    return timeline
```

---

## 7. Conflict Resolution Tracking

### 7.1 Conflict Event Recording

**Current**: Conflicts tracked in `ArtifactSyncResult.conflict_files`

**Enhanced**:
```python
# In models.py
@dataclass
class ConflictResolutionRecord:
    artifact_name: str
    artifact_type: str
    conflict_detected_at: datetime
    conflict_type: str  # "content", "deletion", "both_modified"
    base_version_hash: str
    local_version_hash: str
    remote_version_hash: str
    resolution_strategy: str  # "overwrite", "merge", "fork", "manual"
    resolution_completed_at: Optional[datetime] = None
    resolved_version_hash: Optional[str] = None
    conflict_markers_count: int = 0
    unresolved_conflicts: List[str] = field(default_factory=list)
```

### 7.2 Storage and Tracking

```python
# In sync.py: after conflict resolution
def _record_conflict_resolution(
    self,
    artifact_name: str,
    artifact_type: str,
    deployment: Deployment,
    result: ArtifactSyncResult,
    strategy: str,
):
    """Record conflict resolution for audit trail."""
    record = ConflictResolutionRecord(
        artifact_name=artifact_name,
        artifact_type=artifact_type,
        conflict_detected_at=datetime.now(),
        conflict_type="content",  # TODO: compute actual type
        base_version_hash=deployment.content_hash,
        local_version_hash=result.collection_sha,
        remote_version_hash=result.project_sha,
        resolution_strategy=strategy,
        conflict_markers_count=len(result.conflict_files),
    )

    # Store in database or file
    self.conflict_tracker.record(record)
```

### 7.3 Versioning System Integration

```python
# In version_manager.py
def analyze_conflicts(self, artifact_name: str):
    """Show conflict history for artifact."""
    records = self.conflict_tracker.get_records(artifact_name)

    # Identify patterns
    # Suggest resolutions
    # Show unresolved conflicts
```

---

## 8. Semantic Versioning Integration

### 8.1 Auto-Detection

```python
# In deployment.py or version_manager.py
def should_increment_version(
    self,
    old_hash: str,
    new_hash: str,
    change_analysis: DiffResult,
) -> Optional[str]:
    """Suggest version bump based on changes.

    Returns: "major", "minor", "patch", or None
    """
    if not change_analysis.has_changes:
        return None

    # MAJOR: Breaking changes (file deletions, major restructure)
    if change_analysis.files_removed:
        return "major"

    # MINOR: New features (files added)
    if change_analysis.files_added:
        return "minor"

    # PATCH: Bug fixes (files modified, no structural changes)
    if change_analysis.files_modified:
        return "patch"

    return None
```

### 8.2 Manual Version Tagging

```python
# Add to Deployment:
class Deployment:
    # ... existing fields ...
    version_tag: Optional[str] = None  # "v1.2.0", "beta", etc.
    is_major_change: bool = False      # For changelog

# In deployment.py
def tag_version(
    self,
    artifact_name: str,
    artifact_type: str,
    project_path: Path,
    version_tag: str,
    is_major: bool = False,
):
    """Manually tag a version."""
    deployment = DeploymentTracker.get_deployment(...)
    deployment.version_tag = version_tag
    deployment.is_major_change = is_major
    DeploymentTracker.write_deployments(...)
```

---

## 9. Analytics and Audit Trail

### 9.1 Sync Events to Track

```python
# Extend EventTracker in core/analytics.py
class EventTracker:
    def track_deployment(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        content_hash: str,
        version_tag: Optional[str] = None,
    ):
        """Track deployment event."""

    def track_sync_pull(
        self,
        artifact_name: str,
        artifact_type: str,
        strategy: str,
        drift_type: str,
        base_hash: str,
        result_hash: str,
        conflicts_detected: int = 0,
    ):
        """Track pull sync event."""

    def track_conflict_resolution(
        self,
        artifact_name: str,
        conflict_type: str,
        resolution_strategy: str,
        resolved: bool,
    ):
        """Track conflict resolution."""
```

### 9.2 Audit Trail Usage

```python
# In version_manager.py
def get_artifact_audit_trail(self, artifact_name: str):
    """Show complete history of artifact."""
    return {
        "deployments": self._get_deployment_events(artifact_name),
        "syncs": self._get_sync_events(artifact_name),
        "conflicts": self._get_conflict_events(artifact_name),
        "versions": self._get_versions(artifact_name),
        "snapshots": self._get_snapshots(artifact_name),
    }
```

---

## 10. Implementation Checklist for v1.5

### Phase 1: Baseline & Storage
- [ ] Add `merge_base_snapshot` to Deployment
- [ ] Implement snapshot-based baseline storage
- [ ] Update DeploymentTracker to save baseline
- [ ] Add snapshot_id to Deployment

### Phase 2: Version Lineage
- [ ] Populate `parent_hash` on deployment
- [ ] Maintain `version_lineage` chain
- [ ] Add version comparison methods
- [ ] Add version history queries

### Phase 3: Modification Tracking
- [ ] Populate `modification_detected_at`
- [ ] Update `last_modified_check` on drift checks
- [ ] Implement modification timeline analysis
- [ ] Add modification status to UI

### Phase 4: Conflict Tracking
- [ ] Create ConflictResolutionRecord model
- [ ] Record conflict events
- [ ] Track resolution strategies
- [ ] Build conflict analytics

### Phase 5: Enhanced Three-Way Merge
- [ ] Use stored baseline in merge
- [ ] Improve merge conflict detection
- [ ] Add merge preview before execution
- [ ] Support manual conflict resolution UI

### Phase 6: Semantic Versioning
- [ ] Auto-detect version bump candidates
- [ ] Allow manual version tagging
- [ ] Track version changes in changelog
- [ ] Link versions to snapshots

---

## 11. Data Flow Diagrams

### Deploy with Versioning

```
User: deploy artifact
  ↓
DeploymentManager.deploy_artifacts()
  ├─ Copy collection → project
  ├─ Compute content_hash = H1
  ├─ DeploymentTracker.record_deployment()
  │  ├─ Load existing deployment
  │  ├─ If exists: set parent_hash = H0
  │  ├─ Create version_lineage = [H1, H0, H-1, ...]
  │  └─ Write to .skillmeat-deployed.toml
  ├─ Create baseline snapshot
  │  └─ deployment.merge_base_snapshot = snap_id
  ├─ Auto-snapshot (SVCV-003)
  │  └─ Link deployment → snapshot
  └─ Record analytics
     └─ version_tag, is_major_change (optional)
```

### Sync Pull with Conflict Resolution

```
User: sync pull (with conflict)
  ↓
check_drift()
  → drift_type = "conflict" (A, B, C)
  ↓
Show preview
  ↓
User chooses strategy
  ├─ merge:
  │  ├─ Load deployment.merge_base_snapshot
  │  ├─ Reconstruct baseline (A)
  │  ├─ 3-way merge(A, B, C)
  │  ├─ Write merged to collection
  │  └─ Record conflict_markers_count
  │
  ├─ overwrite:
  │  ├─ Copy project → collection
  │  └─ Mark for manual re-deploy
  │
  └─ fork:
     └─ Create artifact-fork variant
  ↓
Auto-snapshot (SVCV-002)
  └─ Link to conflict resolution
  ↓
Record conflict resolution event
  └─ Base + Local + Remote hashes
```

---

## 12. Integration Testing Strategy

### Test: Deploy → Modify → Sync with Merge

```
1. Deploy artifact (hash=H1)
   → deployment.content_hash = H1
   → deployment.merge_base_snapshot = snap_id_1
   → deployment.version_lineage = [H1]

2. Collection updated (hash=H2)
   → deployment.content_hash = H1 (unchanged)
   → collection_sha = H2

3. Project modified (hash=H3)
   → project_sha = H3
   → Drift: CONFLICT

4. Sync pull (merge)
   → Load baseline from snap_id_1 (hash=H1)
   → 3-way merge(H1, H2, H3)
   → Assume merge produces H4
   → Update collection
   → Create snapshot (snap_id_2)
   → Record conflict resolution

5. Next deployment
   → New deployment with:
     - content_hash = H4 (merged)
     - parent_hash = H1 (deployed baseline)
     - version_lineage = [H4, H1]
     - merge_base_snapshot = snap_id_2 (new baseline)
```

---

## Summary

**Key Integration Points**:
1. ✅ **Hash-based versioning**: Use content_hash as version ID
2. ✅ **Snapshot baseline**: Store deployed baseline in snapshot
3. ✅ **Version lineage**: Maintain parent_hash chain
4. ✅ **Modification tracking**: Populate detected_at fields
5. ✅ **Conflict recording**: Track resolution decisions
6. ✅ **Three-way merge**: Use stored baseline
7. ✅ **Analytics**: Record all sync/deploy/conflict events
8. ✅ **Semantic versioning**: Auto-detect version bumps

**Files to Modify**:
- `skillmeat/core/deployment.py` - Add versioning fields
- `skillmeat/core/sync.py` - Use baselines, track conflicts
- `skillmeat/storage/deployment.py` - Populate lineage
- `skillmeat/models.py` - Add versioning models
- `skillmeat/core/version.py` - Integrate with version system
