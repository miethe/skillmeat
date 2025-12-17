---
title: Version Management APIs Developer Guide
description: Guide for developers integrating with SkillMeat's versioning system
audience: developers
tags: [versioning, snapshots, rollback, merge, api]
created: 2024-12-17
updated: 2024-12-17
category: Development
status: active
related: ["API Reference", "Versioning System Overview", "Sync Architecture"]
---

# Version Management APIs Developer Guide

This guide covers the service layer APIs for SkillMeat's versioning system. For REST endpoint documentation, see the [API Reference](../api-reference.md).

## Overview

SkillMeat provides two complementary APIs for version management:

1. **VersionManager** - High-level service API for typical versioning operations
2. **SnapshotManager** - Low-level API for snapshot creation and restoration

### When to Use Each API

| Operation | API | Reason |
|-----------|-----|--------|
| Create snapshot | `VersionManager` | Automatic safety snapshots, audit trail |
| List/get snapshots | Either | `VersionManager` simpler for typical use |
| Rollback with merge | `VersionManager` | Preserves changes, handles conflicts |
| Simple restore | Either | `SnapshotManager` if no change preservation needed |
| Low-level operations | `SnapshotManager` | Direct tarball management |
| Audit tracking | `VersionManager` | Records rollback history |

## VersionManager API Reference

### Initialization

```python
from skillmeat.core.version import VersionManager

# Basic initialization (uses defaults)
version_mgr = VersionManager()

# With custom managers
from skillmeat.core.collection import CollectionManager
from skillmeat.storage.snapshot import SnapshotManager

collection_mgr = CollectionManager()
snapshot_mgr = SnapshotManager(Path.home() / ".skillmeat" / "snapshots")
version_mgr = VersionManager(
    collection_mgr=collection_mgr,
    snapshot_mgr=snapshot_mgr
)
```

### Core Methods

#### `create_snapshot(collection_name, message)`

Create a new snapshot of a collection.

**Signature:**
```python
def create_snapshot(
    self,
    collection_name: Optional[str] = None,
    message: str = "Manual snapshot",
) -> Snapshot
```

**Parameters:**
- `collection_name` (str, optional): Collection to snapshot. Uses active collection if None.
- `message` (str): Description of the snapshot

**Returns:** `Snapshot` object with metadata

**Raises:**
- `ValueError`: Collection not found
- `RuntimeError`: Snapshot creation failed

**Example:**
```python
# Create snapshot of default collection
snapshot = version_mgr.create_snapshot(message="Pre-deployment backup")
print(f"Created snapshot: {snapshot.id}")
print(f"  Timestamp: {snapshot.timestamp}")
print(f"  Artifacts: {snapshot.artifact_count}")

# Create snapshot of specific collection
snapshot = version_mgr.create_snapshot(
    collection_name="experimental",
    message="Before testing new features"
)
```

**Console Output:**
```
Creating snapshot of 'default'...
✓ Snapshot created: 20241217-143022-123456
  Message: Pre-deployment backup
  Artifacts: 15
```

#### `list_snapshots(collection_name, limit, cursor)`

List snapshots with cursor-based pagination.

**Signature:**
```python
def list_snapshots(
    self,
    collection_name: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Tuple[List[Snapshot], Optional[str]]
```

**Parameters:**
- `collection_name` (str, optional): Collection to list. Uses active if None.
- `limit` (int): Max snapshots per page (1-100, default 50)
- `cursor` (str, optional): Pagination cursor (snapshot ID to start after)

**Returns:** Tuple of (snapshots, next_cursor)
- `snapshots`: List of `Snapshot` objects, newest first
- `next_cursor`: ID of last snapshot if more exist, None otherwise

**Raises:**
- `ValueError`: Invalid limit or cursor

**Example:**
```python
# Get first page
snapshots, cursor = version_mgr.list_snapshots(limit=10)
print(f"Found {len(snapshots)} snapshots")
for snap in snapshots:
    print(f"  {snap.id}: {snap.message}")
    print(f"    Created: {snap.timestamp}")
    print(f"    Artifacts: {snap.artifact_count}")

# Paginate through all snapshots
all_snapshots = []
cursor = None
while True:
    snapshots, cursor = version_mgr.list_snapshots(limit=20, cursor=cursor)
    all_snapshots.extend(snapshots)
    if cursor is None:
        break

print(f"Total snapshots: {len(all_snapshots)}")
```

#### `get_snapshot(snapshot_id, collection_name)`

Retrieve a specific snapshot by ID.

**Signature:**
```python
def get_snapshot(
    self,
    snapshot_id: str,
    collection_name: Optional[str] = None,
) -> Optional[Snapshot]
```

**Parameters:**
- `snapshot_id` (str): Snapshot ID to retrieve
- `collection_name` (str, optional): Collection name (uses active if None)

**Returns:** `Snapshot` object if found, None otherwise

**Example:**
```python
snapshot = version_mgr.get_snapshot("20241217-143022-123456")
if snapshot:
    print(f"Found: {snapshot.message}")
else:
    print("Snapshot not found")
```

#### `delete_snapshot(snapshot_id, collection_name)`

Delete a specific snapshot and its tarball.

**Signature:**
```python
def delete_snapshot(
    self,
    snapshot_id: str,
    collection_name: Optional[str] = None,
) -> None
```

**Parameters:**
- `snapshot_id` (str): Snapshot to delete
- `collection_name` (str, optional): Collection name (uses active if None)

**Raises:**
- `ValueError`: Snapshot not found

**Example:**
```python
try:
    version_mgr.delete_snapshot("20241217-143022-123456")
    print("Snapshot deleted")
except ValueError as e:
    print(f"Error: {e}")
```

#### `cleanup_snapshots(collection_name, keep_count)`

Delete old snapshots, keeping most recent N.

**Signature:**
```python
def cleanup_snapshots(
    self,
    collection_name: Optional[str] = None,
    keep_count: int = 10,
) -> List[Snapshot]
```

**Parameters:**
- `collection_name` (str, optional): Collection name (uses active if None)
- `keep_count` (int): Number of snapshots to keep (default 10)

**Returns:** List of deleted snapshots

**Example:**
```python
deleted = version_mgr.cleanup_snapshots(keep_count=5)
print(f"Cleaned up {len(deleted)} old snapshot(s)")
for snap in deleted:
    print(f"  Deleted: {snap.id}")
```

### Rollback Methods

#### `analyze_rollback_safety(snapshot_id, collection_name)`

Analyze whether rollback is safe before attempting it.

Performs a dry-run analysis to detect potential conflicts. This helps understand what will happen during rollback without making changes.

**Signature:**
```python
def analyze_rollback_safety(
    self,
    snapshot_id: str,
    collection_name: Optional[str] = None,
) -> RollbackSafetyAnalysis
```

**Parameters:**
- `snapshot_id` (str): Snapshot to analyze rollback to
- `collection_name` (str, optional): Collection name (uses active if None)

**Returns:** `RollbackSafetyAnalysis` object

**Example:**
```python
analysis = version_mgr.analyze_rollback_safety("20241217-143022-123456")

print(f"Is safe: {analysis.is_safe}")
print(f"Local changes: {analysis.local_changes_detected}")
print(f"Conflicts: {len(analysis.files_with_conflicts)}")

if analysis.is_safe:
    print(f"Summary: {analysis.summary()}")
else:
    print("Conflicts detected:")
    for file in analysis.files_with_conflicts[:5]:
        print(f"  - {file}")
    if analysis.warnings:
        print("Warnings:")
        for warning in analysis.warnings:
            print(f"  - {warning}")
```

#### `intelligent_rollback(...)`

Rollback to snapshot with intelligent change preservation.

Performs a three-way merge during rollback to preserve uncommitted local changes where possible. This is the recommended method for most rollback scenarios.

**Signature:**
```python
def intelligent_rollback(
    self,
    snapshot_id: str,
    collection_name: Optional[str] = None,
    preserve_changes: bool = True,
    selective_paths: Optional[List[str]] = None,
    confirm: bool = True,
) -> RollbackResult
```

**Parameters:**
- `snapshot_id` (str): Snapshot to restore
- `collection_name` (str, optional): Collection name (uses active if None)
- `preserve_changes` (bool): Attempt to preserve local changes via merge (default True)
- `selective_paths` (List[str], optional): Only rollback specific file paths (None = all)
- `confirm` (bool): Require user confirmation (default True)

**Returns:** `RollbackResult` with detailed information

**Key Behaviors:**
- Creates automatic safety snapshot before rollback
- Performs three-way diff to detect conflicts
- Merges local changes where possible
- Records audit entry of operation
- Preserves both changes and rollback information

**Example - Basic Intelligent Rollback:**
```python
result = version_mgr.intelligent_rollback("20241217-143022-123456")

if result.success:
    print(f"Rollback successful!")
    print(f"  Files restored: {len(result.files_restored)}")
    print(f"  Files merged: {len(result.files_merged)}")
    print(f"  Conflicts: {len(result.conflicts)}")
    print(f"  Safety snapshot: {result.safety_snapshot_id}")
else:
    print(f"Rollback failed: {result.error}")
```

**Example - Selective Rollback:**
```python
# Only rollback specific artifacts
result = version_mgr.intelligent_rollback(
    snapshot_id="20241217-143022-123456",
    selective_paths=["skills/canvas-design", "commands/test"]
)

print(result.summary())
```

**Example - No User Confirmation:**
```python
# Useful for automated workflows
result = version_mgr.intelligent_rollback(
    snapshot_id="20241217-143022-123456",
    confirm=False
)
```

**Console Output Example:**
```
Analyzing rollback safety...
Safe to rollback: 5 local changes will be merged
Intelligent rollback: Will attempt to preserve your uncommitted changes
  Snapshot: 20241217-143022-123456
  Created: 2024-12-17 14:30:22
  Message: Pre-deployment backup
Proceed with intelligent rollback? [y/N]: y

Creating safety snapshot before rollback...
Extracting snapshot 20241217-143022-123456...
Analyzing current state...
Detecting local changes...
Merging changes: 5 changed, 0 conflicts...
Applying merged changes...
✓ Intelligent rollback successful: 5 files merged
```

#### `rollback(snapshot_id, collection_name, confirm)`

Simple rollback without change preservation.

This method performs a straightforward restoration, replacing the entire collection with the snapshot. Use this when you want a clean restore without merging changes.

**Signature:**
```python
def rollback(
    self,
    snapshot_id: str,
    collection_name: Optional[str] = None,
    confirm: bool = True,
) -> None
```

**Parameters:**
- `snapshot_id` (str): Snapshot to restore
- `collection_name` (str, optional): Collection name (uses active if None)
- `confirm` (bool): Require user confirmation (default True)

**Raises:**
- `ValueError`: Snapshot not found or user cancelled
- `RuntimeError`: Rollback failed

**Example:**
```python
try:
    version_mgr.rollback("20241217-143022-123456")
    print("Rollback completed")
except ValueError as e:
    print(f"Rollback cancelled: {e}")
except Exception as e:
    print(f"Rollback failed: {e}")
```

### Audit Trail Methods

#### Audit Trail Access

The `VersionManager` maintains audit trails of all rollback operations for debugging and history tracking.

**Example - View Rollback History:**
```python
# Get last 10 rollback operations for collection
history = version_mgr.audit_trail.get_history("default", limit=10)

for entry in history:
    print(f"{entry.id} - {entry.timestamp}")
    print(f"  Operation: {entry.operation_type}")
    print(f"  From: {entry.source_snapshot_id}")
    print(f"  To: {entry.target_snapshot_id}")
    print(f"  Status: {'Success' if entry.success else 'Failed'}")
    if entry.error:
        print(f"  Error: {entry.error}")
```

**Example - Find Specific Audit Entry:**
```python
entry = version_mgr.audit_trail.get_entry("rb_20241217_143022")
if entry:
    print(f"Found rollback operation from {entry.timestamp}")
    print(f"Files merged: {len(entry.files_merged)}")
    print(f"Files with conflicts: {len(entry.conflicts_pending)}")
```

## SnapshotManager API Reference

### Initialization

```python
from skillmeat.storage.snapshot import SnapshotManager
from pathlib import Path

# Initialize with snapshots directory
snapshots_dir = Path.home() / ".skillmeat" / "snapshots"
snapshot_mgr = SnapshotManager(snapshots_dir)
```

### Core Methods

#### `create_snapshot(collection_path, collection_name, message)`

Create tarball snapshot of a collection.

**Signature:**
```python
def create_snapshot(
    self,
    collection_path: Path,
    collection_name: str,
    message: str
) -> Snapshot
```

**Parameters:**
- `collection_path` (Path): Path to collection directory
- `collection_name` (str): Name of collection (used for organization)
- `message` (str): Snapshot description

**Returns:** `Snapshot` object

**Raises:**
- `FileNotFoundError`: Collection doesn't exist
- `IOError`: Snapshot creation failed

**Example:**
```python
from pathlib import Path

collection_path = Path.home() / ".skillmeat" / "collection"
snapshot = snapshot_mgr.create_snapshot(
    collection_path,
    collection_name="default",
    message="Before major refactor"
)
print(f"Created: {snapshot.id}")
print(f"Tarball: {snapshot.tarball_path}")
```

#### `list_snapshots(collection_name, limit, cursor)`

List snapshots with cursor-based pagination.

**Signature:**
```python
def list_snapshots(
    self,
    collection_name: str,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Tuple[List[Snapshot], Optional[str]]
```

**Returns:** Tuple of (snapshots, next_cursor)

**Example:**
```python
snapshots, cursor = snapshot_mgr.list_snapshots(
    "default",
    limit=20
)
print(f"Page 1: {len(snapshots)} snapshots")

# Get next page
if cursor:
    more, next_cursor = snapshot_mgr.list_snapshots(
        "default",
        limit=20,
        cursor=cursor
    )
    print(f"Page 2: {len(more)} snapshots")
```

#### `restore_snapshot(snapshot, collection_path)`

Extract snapshot to collection directory.

**WARNING:** This is a destructive operation that replaces the target collection directory!

**Signature:**
```python
def restore_snapshot(
    self,
    snapshot: Snapshot,
    collection_path: Path
) -> None
```

**Parameters:**
- `snapshot` (Snapshot): Snapshot object to restore
- `collection_path` (Path): Target directory for restored collection

**Raises:**
- `FileNotFoundError`: Snapshot tarball doesn't exist
- `IOError`: Restore operation failed

**Example:**
```python
snapshot = snapshot_mgr.list_snapshots("default", limit=1)[0][0]
target_path = Path.home() / ".skillmeat" / "collection_restored"

snapshot_mgr.restore_snapshot(snapshot, target_path)
print(f"Restored to: {target_path}")
```

#### `delete_snapshot(snapshot)`

Delete snapshot tarball and update metadata.

**Signature:**
```python
def delete_snapshot(self, snapshot: Snapshot) -> None
```

**Parameters:**
- `snapshot` (Snapshot): Snapshot object to delete

**Example:**
```python
snapshot = snapshot_mgr.list_snapshots("default", limit=1)[0][0]
snapshot_mgr.delete_snapshot(snapshot)
print("Snapshot deleted")
```

#### `cleanup_old_snapshots(collection_name, keep_count)`

Delete old snapshots, keeping most recent N.

**Signature:**
```python
def cleanup_old_snapshots(
    self,
    collection_name: str,
    keep_count: int = 10
) -> List[Snapshot]
```

**Returns:** List of deleted snapshots

**Example:**
```python
deleted = snapshot_mgr.cleanup_old_snapshots("default", keep_count=5)
print(f"Deleted {len(deleted)} snapshots")
```

## Data Models

### Snapshot

**Location:** `skillmeat.storage.snapshot`

Represents snapshot metadata.

```python
@dataclass
class Snapshot:
    id: str              # Timestamp-based ID (e.g., "20241217-143022-123456")
    timestamp: datetime  # Creation time (UTC)
    message: str         # Description
    collection_name: str # Source collection name
    artifact_count: int  # Number of artifacts in snapshot
    tarball_path: Path   # Path to .tar.gz file
```

### RollbackResult

**Location:** `skillmeat.models`

Result of intelligent rollback operation.

```python
@dataclass
class RollbackResult:
    success: bool                              # Rollback succeeded
    snapshot_id: str                           # Snapshot restored
    files_restored: List[str] = []             # Files directly restored
    files_merged: List[str] = []               # Files merged to preserve changes
    conflicts: List[ConflictMetadata] = []     # Unresolved conflicts
    safety_snapshot_id: Optional[str] = None   # Pre-rollback safety snapshot
    error: Optional[str] = None                # Error message if failed

    # Properties
    has_conflicts: bool  # True if conflicts exist
    total_files: int     # Total files processed

    # Methods
    def summary() -> str # Human-readable summary
```

### RollbackSafetyAnalysis

**Location:** `skillmeat.models`

Pre-rollback safety analysis.

```python
@dataclass
class RollbackSafetyAnalysis:
    is_safe: bool                          # Rollback can proceed without conflicts
    snapshot_id: str                       # Snapshot ID being analyzed
    snapshot_exists: bool = True           # Snapshot was found
    local_changes_detected: int = 0        # Number of changed files
    files_with_conflicts: List[str] = []   # Files with potential conflicts
    files_safe_to_restore: List[str] = []  # Files safe to restore
    files_to_merge: List[str] = []         # Files requiring merge
    warnings: List[str] = []               # Warning messages

    # Methods
    def summary() -> str # Human-readable summary
```

### ConflictMetadata

**Location:** `skillmeat.models`

Metadata for merge conflict.

```python
@dataclass
class ConflictMetadata:
    file_path: str                         # Path to conflicting file
    conflict_type: str                     # "content", "deletion", "both_modified", "add_add"
    base_content: Optional[str] = None     # Base/ancestor version content
    local_content: Optional[str] = None    # Local version content (None if deleted)
    remote_content: Optional[str] = None   # Remote version content (None if deleted)
    auto_mergeable: bool = False           # Can be auto-merged
    merge_strategy: Optional[str] = None   # "use_local", "use_remote", "use_base", "manual"
    is_binary: bool = False                # Binary file (no content diff)
```

### RollbackAuditEntry

**Location:** `skillmeat.models`

Audit trail entry for rollback operation.

```python
@dataclass
class RollbackAuditEntry:
    id: str                                # Unique ID (e.g., "rb_20241217_143022")
    timestamp: datetime                    # When rollback occurred
    collection_name: str                   # Collection rolled back
    source_snapshot_id: str                # Rolled back FROM (safety snapshot)
    target_snapshot_id: str                # Rolled back TO
    operation_type: str                    # "simple", "intelligent", "selective"
    files_restored: List[str] = []         # Files directly restored
    files_merged: List[str] = []           # Files merged
    conflicts_resolved: List[str] = []     # Conflicts successfully resolved
    conflicts_pending: List[str] = []      # Conflicts requiring manual resolution
    preserve_changes_enabled: bool = False # Intelligent rollback used
    selective_paths: Optional[List[str]] = None  # Selective paths (None = full)
    success: bool = True                   # Operation succeeded
    error: Optional[str] = None            # Error message if failed
    metadata: Dict[str, Any] = {}          # Additional metadata

    # Methods
    def to_dict() -> Dict[str, Any]   # Convert to TOML-serializable dict
    def from_dict(data) -> RollbackAuditEntry  # Create from dict
```

## Error Handling

### Common Exceptions

#### ValueError

Raised for invalid parameters or operations.

```python
try:
    snapshot = version_mgr.get_snapshot("invalid_id")
    if snapshot is None:
        raise ValueError("Snapshot not found")
except ValueError as e:
    logger.error(f"Invalid operation: {e}")
```

**Common cases:**
- Snapshot not found
- Collection not found
- Invalid collection name
- Invalid cursor for pagination

#### FileNotFoundError

Raised when files don't exist.

```python
try:
    snapshot = snapshot_mgr.create_snapshot(
        Path("/nonexistent"),
        "default",
        "test"
    )
except FileNotFoundError as e:
    logger.error(f"Collection missing: {e}")
```

#### IOError

Raised for I/O failures (tarball creation, extraction, etc.).

```python
try:
    result = version_mgr.intelligent_rollback("snap_id")
except Exception as e:
    logger.error(f"Rollback I/O error: {e}")
```

### Best Practices

**1. Always handle user cancellation:**
```python
result = version_mgr.intelligent_rollback(snapshot_id)
if result.error and "cancelled" in result.error.lower():
    print("User cancelled rollback")
```

**2. Check for conflicts:**
```python
result = version_mgr.intelligent_rollback(snapshot_id)
if result.has_conflicts:
    print(f"Resolve {len(result.conflicts)} conflicts manually")
    for conflict in result.conflicts:
        print(f"  - {conflict.file_path}")
```

**3. Log audit entries for tracking:**
```python
history = version_mgr.audit_trail.get_history("default", limit=1)
if history and not history[0].success:
    print(f"Last rollback failed: {history[0].error}")
```

## Integration Patterns

### Auto-Capture on Sync

Create snapshots before and after sync operations to track changes:

```python
def sync_with_snapshots(sync_engine, collection_name):
    version_mgr = VersionManager()

    # Create pre-sync snapshot
    pre_snapshot = version_mgr.create_snapshot(
        collection_name=collection_name,
        message="Pre-sync backup"
    )

    try:
        # Perform sync
        result = sync_engine.sync_collection(collection_name)

        # Create post-sync snapshot
        post_snapshot = version_mgr.create_snapshot(
            collection_name=collection_name,
            message="Post-sync state"
        )

        return {"pre": pre_snapshot.id, "post": post_snapshot.id}

    except Exception as e:
        # Rollback on failure
        result = version_mgr.intelligent_rollback(
            snapshot_id=pre_snapshot.id,
            collection_name=collection_name,
            confirm=False
        )
        raise RuntimeError(f"Sync failed and rolled back: {e}")
```

### Selective Rollback

Rollback only specific artifacts:

```python
def selective_rollback_artifacts(version_mgr, snapshot_id, artifacts):
    """Rollback only specific artifacts."""

    # Convert artifact names to relative paths
    selective_paths = [f"skills/{name}" for name in artifacts]

    result = version_mgr.intelligent_rollback(
        snapshot_id=snapshot_id,
        selective_paths=selective_paths,
        confirm=False
    )

    return result
```

### Rollback with Analysis

Always analyze before rolling back in automated scenarios:

```python
def safe_automated_rollback(version_mgr, snapshot_id):
    """Rollback with pre-flight safety checks."""

    # Analyze first
    analysis = version_mgr.analyze_rollback_safety(snapshot_id)

    if not analysis.is_safe:
        logger.warning(f"Rollback not safe: {analysis.summary()}")
        return None

    # Proceed with rollback
    result = version_mgr.intelligent_rollback(
        snapshot_id=snapshot_id,
        confirm=False
    )

    if not result.success:
        logger.error(f"Rollback failed: {result.error}")
        return None

    return result
```

### Snapshot Lifecycle Management

Manage snapshot storage to prevent disk bloat:

```python
def manage_collection_snapshots(version_mgr, collection_name):
    """Clean up old snapshots but keep recent ones."""

    # Keep last 10 snapshots
    deleted = version_mgr.cleanup_snapshots(
        collection_name=collection_name,
        keep_count=10
    )

    total_freed = sum(
        snapshot.tarball_path.stat().st_size
        for snapshot in deleted
        if snapshot.tarball_path.exists()
    )

    logger.info(
        f"Cleaned up {len(deleted)} snapshots, "
        f"freed {total_freed / 1024 / 1024:.1f}MB"
    )

    return deleted
```

## Testing

### Unit Testing Snapshots

```python
import tempfile
from pathlib import Path
from skillmeat.storage.snapshot import SnapshotManager

def test_snapshot_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test collection
        collection_path = Path(tmpdir) / "test_collection"
        collection_path.mkdir()
        (collection_path / "test_file.txt").write_text("test content")

        # Create snapshot
        snapshots_dir = Path(tmpdir) / "snapshots"
        snapshot_mgr = SnapshotManager(snapshots_dir)

        snapshot = snapshot_mgr.create_snapshot(
            collection_path,
            "test_collection",
            "Test snapshot"
        )

        assert snapshot.id is not None
        assert snapshot.tarball_path.exists()
        assert snapshot.message == "Test snapshot"
```

### Integration Testing Rollback

```python
def test_intelligent_rollback_preserves_changes():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        version_mgr = VersionManager()
        collection_path = Path(tmpdir) / "collection"
        collection_path.mkdir()

        # Create initial snapshot
        snapshot1 = version_mgr.create_snapshot(
            collection_name="default",
            message="Initial"
        )

        # Make changes
        (collection_path / "new_file.txt").write_text("new content")

        # Rollback
        result = version_mgr.intelligent_rollback(
            snapshot_id=snapshot1.id,
            confirm=False
        )

        assert result.success
        assert result.safety_snapshot_id is not None
```

## Performance Considerations

### Snapshot Creation

- **Time complexity**: O(n) where n = number of files
- **Space complexity**: O(m) where m = uncompressed collection size
- Compression ratio typically 50-70% for text artifacts

### Rollback Operations

- **Three-way diff**: O(n) where n = number of files
- **Merge operation**: O(n) for auto-mergeable files
- **Conflict detection**: O(c) where c = number of conflicts

### Optimization Tips

1. **Use selective rollback** for large collections with few affected files
2. **Disable change preservation** if not needed (`preserve_changes=False`)
3. **Clean up snapshots regularly** to manage disk space
4. **Use pagination** when listing many snapshots

## Reference

- **API Endpoint Documentation**: `docs/development/versioning/api-reference.md`
- **Versioning System Overview**: `docs/development/versioning/overview.md`
- **Sync Architecture**: `docs/development/sync/architecture.md`
- **Source Code**: `skillmeat/core/version.py`, `skillmeat/storage/snapshot.py`
