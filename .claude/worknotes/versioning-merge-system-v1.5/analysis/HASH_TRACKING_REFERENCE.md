# Hash & Tracking Mechanisms - Quick Reference

**Status:** 2025-12-17
**System:** SkillMeat Versioning & Merge System

---

## 1. Hash Functions Available

### 1.1 Content Hash Service
**File:** `skillmeat/core/services/content_hash.py`

```python
from skillmeat.core.services.content_hash import (
    compute_content_hash,
    detect_changes,
    verify_content_integrity,
    read_file_with_hash
)

# Compute hash of string content
hash_value = compute_content_hash("# My Skill")
# → "abc123def456..." (64 chars, SHA256 hex)

# Detect if file changed from collection
has_changed = detect_changes(collection_hash, deployed_file_path)
# → True if file differs, False if matches or missing

# Verify content integrity
is_valid = verify_content_integrity(expected_hash, content)
# → True if content matches hash

# Read file and get hash in one operation
content, hash_value = read_file_with_hash(file_path)
```

**Use Cases:**
- Change detection for drift sync
- Artifact content comparison
- Integrity verification

**Algorithm:** SHA256 (UTF-8 encoded)

---

### 1.2 File Hasher
**File:** `skillmeat/core/sharing/hasher.py`

```python
from skillmeat.core.sharing.hasher import FileHasher
from pathlib import Path

# Hash single file
hash_value = FileHasher.hash_file(Path("skill.py"))
# → "sha256:abc123def456..."

# Hash entire directory (deterministic)
dir_hash = FileHasher.hash_directory(Path("artifacts/my-skill"))
# → "sha256:def456ghi789..." (same content = same hash)

# Hash string or bytes
hash_value = FileHasher.hash_string("some text")
# → "sha256:xyz..."

hash_value = FileHasher.hash_bytes(b"binary data")
# → "sha256:abc..."

# Verify hash matches file
is_valid = FileHasher.verify_hash(file_path, expected_hash)
# → True if matches, False otherwise
```

**Key Feature:** Deterministic - sorted file lists ensure same directory always produces same hash

**Algorithm:** SHA256 with sorted files (reproducible)

---

### 1.3 Bundle Hasher
**File:** `skillmeat/core/sharing/hasher.py`

```python
from skillmeat.core.sharing.hasher import BundleHasher
from pathlib import Path

# Hash manifest (with sorted keys for determinism)
manifest = {
    "name": "my-skill",
    "version": "1.0.0",
    "artifacts": ["skill.py", "skill.md"]
}
manifest_hash = BundleHasher.hash_manifest(manifest)
# → "sha256:abc..."

# Hash specific artifact files
artifact_hash = BundleHasher.hash_artifact_files(
    Path("artifacts/my-skill"),
    ["skill.py", "skill.md", "README.md"]
)
# → "sha256:def..."

# Compute overall bundle hash from parts
bundle_hash = BundleHasher.compute_bundle_hash(
    manifest_dict=manifest,
    artifact_hashes=["sha256:abc...", "sha256:def..."]
)
# → "sha256:xyz..."

# Verify bundle integrity
is_valid = BundleHasher.verify_bundle_integrity(
    manifest_dict=manifest_with_hash,
    artifact_hashes=[...]
)
# → True if bundle_hash field matches computed hash
```

**Use Cases:**
- Bundle integrity verification
- Reproducible bundle creation
- Change detection across multiple artifacts

---

## 2. Version Tracking System

### 2.1 VersionManager
**File:** `skillmeat/core/version.py`

```python
from skillmeat.core.version import VersionManager
from skillmeat.storage.snapshot import SnapshotManager
from pathlib import Path

# Initialize
snapshot_manager = SnapshotManager(Path.home() / ".skillmeat" / "snapshots")
version_manager = VersionManager(snapshot_manager)

# Create version snapshot (auto-called on sync/deploy)
snapshot = version_manager.create_version(
    collection_path=Path.home() / ".skillmeat" / "collection",
    message="Merged upstream documentation update",
    source="merge",  # source|upstream|deploy|merge|rollback
    artifacts=["my-skill"],
    custom_hash=None  # Optional: provide precomputed hash
)
# → Snapshot object with id, timestamp, hash, metadata

# List versions with pagination
versions, next_cursor = version_manager.list_versions(
    collection_name="default",
    limit=10,
    cursor=None  # Use from previous response for pagination
)
# → List of Snapshot objects + next cursor for pagination

# Get single version
snapshot = version_manager.get_version(
    collection_name="default",
    snapshot_id="snap_2025-12-15T10:30:00Z"
)
# → Snapshot object with full content

# Compare two versions
diff_result = version_manager.compare_versions(
    collection_name="default",
    snapshot_id_1="snap_id_1",
    snapshot_id_2="snap_id_2"
)
# → DiffResult with added/removed/modified files

# Intelligent rollback (preserves local changes)
rollback_result = version_manager.rollback(
    collection_name="default",
    source_snapshot_id="snap_current",
    target_snapshot_id="snap_old",
    preserve_changes=True
)
# → RollbackResult with merged content, conflicts if any
```

**Auto-Capture Hooks:**
```python
# Automatically called in sync.py
version_manager.capture_version_on_sync(
    collection_path,
    sync_type="pull",  # pull|push
    message="Synced from upstream"
)

# Automatically called in deployment.py
version_manager.capture_version_on_deploy(
    collection_path,
    deploy_type="deploy",  # deploy|undeploy
    artifact_name="my-skill"
)
```

---

### 2.2 Snapshot Manager
**File:** `skillmeat/storage/snapshot.py`

```python
from skillmeat.storage.snapshot import SnapshotManager, Snapshot
from pathlib import Path

# Initialize
snapshot_manager = SnapshotManager(
    snapshots_dir=Path.home() / ".skillmeat" / "snapshots"
)

# Create snapshot (tarball of entire collection)
snapshot = snapshot_manager.create_snapshot(
    collection_path=Path.home() / ".skillmeat" / "collection",
    collection_name="default",
    message="Pre-sync backup"
)
# → Snapshot(
#     id="snap_2025-12-15T10:30:00Z",
#     timestamp=datetime(...),
#     collection_name="default",
#     artifact_count=42,
#     message="Pre-sync backup"
# )

# List snapshots
snapshots = snapshot_manager.list_snapshots("default")
# → [Snapshot(...), Snapshot(...), ...]

# Get snapshot details
snapshot = snapshot_manager.get_snapshot("default", snapshot_id)

# Restore from snapshot (extract tarball)
snapshot_manager.restore_snapshot(
    collection_name="default",
    snapshot_id=snapshot_id,
    target_path=collection_path,
    preserve_local=True  # Keep newer files
)
# → Restores collection from tarball

# Delete old snapshot
snapshot_manager.delete_snapshot("default", snapshot_id)
```

**Storage Location:**
```
~/.skillmeat/snapshots/
└── default/
    ├── 2025-12-15T10:30:00Z.tar.gz
    ├── 2025-12-15T14:45:00Z.tar.gz
    └── ...
```

---

### 2.3 Metadata Tracking
**File:** `skillmeat/core/version.py`

```python
# Metadata structure stored per snapshot
{
    "versions": {
        "version_count": 3,
        "entries": [
            {
                "id": "v1-abc123de",
                "timestamp": "2025-12-15T10:00:00Z",
                "hash": "abc123def456..." ,  # SHA256 of snapshot
                "source": "source",          # source|upstream|deploy|merge|rollback
                "files_changed": ["skill.py", "skill.md"],
                "change_summary": "Initial upload"
            },
            {
                "id": "v2-def456ab",
                "timestamp": "2025-12-15T14:30:00Z",
                "hash": "def456ghi789...",
                "source": "merge",
                "files_changed": ["skill.md"],
                "change_summary": "Merged upstream",
                "parent_versions": ["v1-abc123de"]  # For merge tracking
            }
        ]
    }
}
```

---

## 3. Merge Engine

### 3.1 MergeEngine
**File:** `skillmeat/core/merge_engine.py`

```python
from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import DiffResult

# Initialize
merge_engine = MergeEngine()

# Perform three-way merge
merge_result = merge_engine.merge(
    base=snapshot_v1,          # Source version (common ancestor)
    ours=snapshot_v2,          # Collection version (local)
    theirs=snapshot_v3         # Project version (remote)
)
# → MergeResult(
#     merged_files=[("skill.py", "merged content"), ...],
#     conflicts=[
#         ConflictMetadata(
#             file_path="README.md",
#             conflict_type="content_conflict",
#             base_content="...",
#             our_content="...",
#             their_content="...",
#             conflict_markers="<<<<<<\n...\n======"
#         )
#     ]
# )

# Analyze merge safety before executing
safety_analysis = merge_engine.analyze_merge_safety(base, ours, theirs)
# → RollbackSafetyAnalysis(
#     safe=True,
#     warnings=[],
#     conflict_count=1,
#     auto_merge_count=5
# )

# Resolve single conflict
resolved_content = merge_engine.resolve_conflict(
    file_path="README.md",
    base_content="original",
    our_content="local change",
    their_content="upstream change",
    strategy="ours"  # ours|theirs|base|custom
)
```

---

### 3.2 Diff Engine
**File:** `skillmeat/core/diff_engine.py`

```python
from skillmeat.core.diff_engine import DiffEngine

# Initialize
diff_engine = DiffEngine()

# Generate file-level diff between two snapshots
file_diff = diff_engine.diff_files(
    snapshot_old,
    snapshot_new
)
# → DiffResult(
#     added=["new_file.py"],
#     removed=["old_file.py"],
#     modified=["skill.md"],
#     unchanged=["README.md"],
#     diffs={
#         "skill.md": {
#             "unified_diff": "@@ -1,5 +1,6 @@\n...",
#             "status": "modified"
#         }
#     }
# )

# Generate line-level diff for specific file
line_diff = diff_engine.diff_lines(content1, content2)
# → Unified diff format with line numbers
```

---

## 4. Integration Points

### 4.1 Sync Integration
**File:** `skillmeat/core/sync.py`

```python
# Auto-snapshot before sync (line 651-658)
version_manager._auto_capture_version(
    collection_path,
    "Pre-sync snapshot"
)

# Three-way merge during sync (in _sync_merge)
merge_result = merge_engine.merge(
    base=source_snapshot,      # From GitHub
    ours=collection_snapshot,  # Local collection
    theirs=deployed_snapshot   # Deployed state
)

# Auto-snapshot after sync (line 993-1015)
if sync_success:
    version_manager._auto_capture_version(
        collection_path,
        "Post-sync snapshot"
    )

# Auto-rollback on failure (line 711-729)
if sync_failed:
    version_manager.rollback(
        source_snapshot_id=pre_sync_snapshot,
        preserve_changes=True
    )
```

### 4.2 Deployment Integration
**File:** `skillmeat/core/deployment.py`

```python
# Auto-snapshot on deploy (line 248-267)
version_manager.capture_version_on_deploy(
    collection_path,
    deploy_type="deploy",
    artifact_name="my-skill"
)
```

---

## 5. API Endpoints (Hash-Related)

### 5.1 Get Snapshot with Hash
```http
GET /api/v1/versions/snapshots/{id}

Response:
{
    "id": "snap_2025-12-15T10:30:00Z",
    "timestamp": "2025-12-15T10:30:00Z",
    "collection_name": "default",
    "hash": "abc123def456...",    ← Content hash
    "artifact_count": 42,
    "message": "Pre-sync backup"
}
```

### 5.2 Compare Snapshots (Get Diff with Hashes)
```http
POST /api/v1/versions/snapshots/diff

Request:
{
    "snapshot_id_1": "snap_id_1",
    "snapshot_id_2": "snap_id_2"
}

Response:
{
    "added": ["new_file.py"],
    "removed": ["old_file.py"],
    "modified": ["skill.md"],
    "diffs": {
        "skill.md": {
            "unified_diff": "@@ -1,5 +1,6 @@\n...",
            "status": "modified"
        }
    }
}
```

### 5.3 Merge with Conflict Detection
```http
POST /api/v1/merge/execute

Request:
{
    "base_snapshot": "snap_v1",
    "our_snapshot": "snap_v2",
    "their_snapshot": "snap_v3",
    "strategy": "auto"
}

Response:
{
    "merged_files": [
        {
            "file_path": "skill.py",
            "content": "merged content",
            "hash": "abc123..."  ← Hash of merged content
        }
    ],
    "conflicts": [
        {
            "file_path": "README.md",
            "conflict_type": "content_conflict",
            "base_content": "...",
            "our_content": "...",
            "their_content": "...",
            "conflict_markers": "<<<<<<\n...\n======"
        }
    ]
}
```

---

## 6. Rollback Audit Trail

**File:** `skillmeat/core/version.py` (RollbackAuditTrail class)

```python
from skillmeat.core.version import RollbackAuditTrail
from skillmeat.models import RollbackAuditEntry
from datetime import datetime
from pathlib import Path

# Initialize
audit_trail = RollbackAuditTrail(Path.home() / ".skillmeat" / "audit")

# Record rollback operation
entry = RollbackAuditEntry(
    id="rb_20241216_123456",
    timestamp=datetime.now(),
    collection_name="default",
    source_snapshot_id="snap_abc123",
    target_snapshot_id="snap_def456",
    operation_type="intelligent",
    files_merged=["skill.md"],
    files_conflicted=[],
    success=True
)
audit_trail.record(entry)

# Audit file location
# ~/.skillmeat/audit/default_rollback_audit.toml
```

---

## 7. Practical Examples

### Example 1: Version Snapshot Before Sync

```python
from skillmeat.core.version import VersionManager
from skillmeat.storage.snapshot import SnapshotManager
from pathlib import Path

collection_path = Path.home() / ".skillmeat" / "collection"
snapshot_manager = SnapshotManager(Path.home() / ".skillmeat" / "snapshots")
version_manager = VersionManager(snapshot_manager)

# Before sync, create snapshot
pre_sync_snapshot = version_manager.create_version(
    collection_path=collection_path,
    message="Pre-sync backup",
    source="source",
    artifacts=None  # All artifacts
)

print(f"Snapshot created: {pre_sync_snapshot.id}")
print(f"Hash: {pre_sync_snapshot.hash}")
print(f"Artifacts: {pre_sync_snapshot.artifact_count}")

# Run sync...
# sync_engine.sync(...)

# After sync, create another snapshot
post_sync_snapshot = version_manager.create_version(
    collection_path=collection_path,
    message="Post-sync snapshot",
    source="upstream",
    artifacts=None
)

# Compare
diff_result = version_manager.compare_versions(
    collection_name="default",
    snapshot_id_1=pre_sync_snapshot.id,
    snapshot_id_2=post_sync_snapshot.id
)

print(f"Modified files: {diff_result.modified}")
print(f"Added files: {diff_result.added}")
```

### Example 2: Three-Way Merge

```python
from skillmeat.core.merge_engine import MergeEngine
from skillmeat.core.version import VersionManager

version_manager = VersionManager(snapshot_manager)
merge_engine = MergeEngine()

# Get three versions
source_snapshot = version_manager.get_version("default", "snap_source")
collection_snapshot = version_manager.get_version("default", "snap_collection")
project_snapshot = version_manager.get_version("default", "snap_project")

# Perform merge
merge_result = merge_engine.merge(
    base=source_snapshot,
    ours=collection_snapshot,
    theirs=project_snapshot
)

print(f"Auto-merged files: {len(merge_result.merged_files)}")
print(f"Conflicts: {len(merge_result.conflicts)}")

# Show conflicts to user
for conflict in merge_result.conflicts:
    print(f"\nConflict in {conflict.file_path}:")
    print(f"  Type: {conflict.conflict_type}")
    print(f"  Conflict markers:")
    print(conflict.conflict_markers)

# User resolves conflicts
resolved_content = merge_engine.resolve_conflict(
    file_path="README.md",
    base_content=conflict.base_content,
    our_content=conflict.our_content,
    their_content=conflict.their_content,
    strategy="ours"  # User chose local version
)

# Apply merge
# sync_engine.apply_merge(merge_result, ...)
```

### Example 3: Intelligent Rollback

```python
from skillmeat.core.version import VersionManager

version_manager = VersionManager(snapshot_manager)

# Get current snapshot
current = version_manager.get_version("default", "snap_current")

# Get old snapshot to rollback to
old_version = version_manager.list_versions("default", limit=5)[0]

# Analyze rollback safety
analysis = version_manager.analyze_rollback_safety(
    source_snapshot_id=current.id,
    target_snapshot_id=old_version.id
)

print(f"Safe to rollback: {analysis.safe}")
print(f"Warnings: {analysis.warnings}")
print(f"Local changes preserved: {analysis.local_changes_preserved}")

# Perform rollback
if analysis.safe:
    rollback_result = version_manager.rollback(
        collection_name="default",
        source_snapshot_id=current.id,
        target_snapshot_id=old_version.id,
        preserve_changes=True
    )

    print(f"Rollback successful: {rollback_result.success}")
    print(f"Files restored: {rollback_result.files_restored}")
    print(f"Conflicts: {len(rollback_result.conflicts)}")
else:
    print("Rollback not safe - manual intervention required")
```

---

## 8. Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Snapshot creation | < 1s | Entire collection tarball |
| Hash computation | < 100ms | SHA256 of snapshot |
| Compare snapshots | < 500ms | File-level diff for 100+ files |
| Three-way merge | < 2s | Complex merge with conflicts |
| Rollback | < 1s | Extraction and merge |
| History retrieval | < 100ms | Single version retrieval |
| Pagination | < 200ms | List 100 versions |

---

## 9. Key Design Decisions

1. **Tarball Snapshots** - Simple, readable, deterministic
2. **SHA256 Hashing** - Cryptographically secure, standard
3. **Three-Way Merge** - Line-level granularity, not semantic
4. **Deterministic Ordering** - Sorted file lists for reproducibility
5. **Audit Trail** - TOML-based for human readability
6. **Atomic Operations** - All-or-nothing merge/rollback

---

**Reference Created:** 2025-12-17

This document provides quick access to hash and tracking mechanisms. For detailed information, see `VERSIONING_SYSTEM_ANALYSIS.md` or the individual source files.
