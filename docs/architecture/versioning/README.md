---
title: Versioning and Merge System Architecture
description: Complete architecture documentation for SkillMeat's collection-level versioning and intelligent three-way merge system
audience: developers, maintainers
tags: versioning, snapshots, merge, conflict-resolution, rollback
created: 2024-12-17
updated: 2024-12-17
category: Architecture
status: Active
related:
  - docs/architecture/decisions/004-artifact-version-tracking.md
  - docs/project_plans/ph2-intelligence/adr-0001-diff-merge-strategy.md
---

# Versioning and Merge System Architecture

SkillMeat implements a collection-level versioning system using tarball snapshots with intelligent three-way merge capabilities for conflict resolution and safe rollback operations.

## System Overview

### Design Philosophy

The versioning system prioritizes:
- **Atomicity**: Entire collection snapshots ensure consistent backup/restore
- **Safety**: Pre-merge safety analysis prevents data loss
- **Intelligent conflict detection**: Three-way diffs identify auto-mergeable changes
- **Change preservation**: Rollback with local change merging preserves user work
- **Efficiency**: Gzip compression, cursor-based pagination for large histories

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Layer                              │
│  (FastAPI routers: /api/v1/versions, /api/v1/merge)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Service Layer                               │
│  VersionManager          VersionMergeService                    │
│  - Snapshot creation     - Merge orchestration                 │
│  - Rollback operations   - Safety analysis                     │
│  - Audit trail           - Conflict detection                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                       Core Layer                                │
│  DiffEngine              MergeEngine                             │
│  - Two-way diff          - Auto-merge execution                │
│  - Three-way diff        - Conflict marker generation          │
│  - File comparison       - Atomic file operations              │
│  - Binary detection      - Transaction logging                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Storage Layer                              │
│  SnapshotManager         RollbackAuditTrail                     │
│  - Tarball operations    - Audit log management                │
│  - Metadata persistence  - Entry tracking                      │
│  - Collection packaging  - History queries                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              Filesystem & TOML Storage                           │
│  ~/.skillmeat/snapshots/  ~/.skillmeat/audit/                  │
└─────────────────────────────────────────────────────────────────┘
```

## Storage Architecture

### Directory Structure

```
~/.skillmeat/
├── snapshots/                          # All collection snapshots
│   ├── default/                        # Per-collection subdirectory
│   │   ├── 20241215-150000-123456.tar.gz
│   │   ├── 20241215-100000-654321.tar.gz
│   │   └── snapshots.toml              # Metadata index
│   └── backup/
│       └── snapshots.toml
├── audit/                              # Rollback audit trails
│   ├── default_rollback_audit.toml
│   └── backup_rollback_audit.toml
└── collection/                         # Active collection
    └── (live artifacts)
```

### Snapshot Tarball Format

**Filename**: `{timestamp}-{microseconds}.tar.gz`
- **timestamp**: `YYYYMMDD-HHMMSS` format
- **microseconds**: Added for uniqueness within same second

**Contents**: Complete collection directory tree
```
snapshot_root/
├── skills/
│   ├── pdf-processor/
│   │   ├── skill.yaml
│   │   └── README.md
│   └── image-analyzer/
└── commands/
    └── deploy/
        └── command.yaml
```

### Metadata Storage

**File**: `~/.skillmeat/snapshots/{collection_name}/snapshots.toml`

```toml
[[snapshots]]
id = "20241215-150000-123456"
timestamp = "2024-12-15T15:00:00"
message = "Manual snapshot before deploy"
artifact_count = 12
tarball_path = "/Users/user/.skillmeat/snapshots/default/20241215-150000-123456.tar.gz"

[[snapshots]]
id = "20241215-100000-654321"
timestamp = "2024-12-15T10:00:00"
message = "[auto] Before sync operation"
artifact_count = 12
tarball_path = "/Users/user/.skillmeat/snapshots/default/20241215-100000-654321.tar.gz"
```

### Audit Trail Format

**File**: `~/.skillmeat/audit/{collection_name}_rollback_audit.toml`

```toml
[[entries]]
id = "rb_20241216_123456"
timestamp = "2024-12-16T12:34:56"
collection_name = "default"
source_snapshot_id = "20241216-100000-000001"  # Safety snapshot created before rollback
target_snapshot_id = "20241215-150000-123456"   # What we rolled back to
operation_type = "intelligent"                  # simple | intelligent | selective
files_restored = ["(all files)"]
files_merged = ["skills/pdf-processor/skill.yaml"]
conflicts_pending = []
preserve_changes_enabled = true
selective_paths = null
success = true
error = null
```

**operation_type** values:
- `simple`: Full collection restore (no change preservation)
- `intelligent`: Three-way merge preserves local changes
- `selective`: Rollback specific file paths only

## Component Architecture

### SnapshotManager

**Responsibility**: Tarball-based snapshot storage and retrieval

**Key Methods**:
```python
def create_snapshot(
    collection_path: Path,
    collection_name: str,
    message: str
) -> Snapshot

def restore_snapshot(
    snapshot: Snapshot,
    collection_path: Path
) -> None

def list_snapshots(
    collection_name: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> Tuple[List[Snapshot], Optional[str]]

def delete_snapshot(snapshot: Snapshot) -> None

def cleanup_old_snapshots(
    collection_name: str,
    keep_count: int = 10
) -> List[Snapshot]
```

**Implementation Details**:
- Creates gzip-compressed tarballs for efficient storage
- Metadata stored separately in TOML for fast queries
- Cursor-based pagination supports large snapshot histories
- Atomic operations using temp files and rename

### DiffEngine

**Responsibility**: File and directory comparison with three-way merge support

**Key Methods**:
```python
def diff_files(
    source_file: Path,
    target_file: Path
) -> FileDiff

def diff_directories(
    source_path: Path,
    target_path: Path,
    ignore_patterns: Optional[List[str]] = None
) -> DiffResult

def three_way_diff(
    base_path: Path,
    local_path: Path,
    remote_path: Path,
    ignore_patterns: Optional[List[str]] = None
) -> ThreeWayDiffResult
```

**Three-Way Diff Algorithm**:

| Scenario | Base | Local | Remote | Decision |
|----------|------|-------|--------|----------|
| All same | A | A | A | NO CHANGE |
| Remote changed | A | A | B | AUTO-MERGE (use remote) |
| Local changed | A | B | A | AUTO-MERGE (use local) |
| Both same | A | B | B | AUTO-MERGE (same change) |
| Both different | A | B | C | CONFLICT (manual needed) |
| Local deleted | A | ø | B | CONFLICT (if B changed) |
| Remote deleted | A | B | ø | CONFLICT (if B changed) |
| Added both same | ø | A | A | AUTO-MERGE (same addition) |
| Added both diff | ø | A | B | CONFLICT (different content) |

**Diff Result Structure**:
```python
@dataclass
class ThreeWayDiffResult:
    auto_mergeable: List[str]              # Files can auto-merge
    conflicts: List[ConflictMetadata]      # Requires manual resolution
    stats: DiffStats
```

**Ignore Patterns** (gitignore-style):
```
__pycache__
*.pyc
.git
node_modules
.DS_Store
*.swp
.pytest_cache
dist
build
```

**Binary File Handling**:
- Detected via null-byte scanning in first 8KB
- Binary conflicts cannot be auto-merged, marked for manual resolution
- Conflict markers only generated for text files

### MergeEngine

**Responsibility**: Executing three-way merges with conflict detection

**Key Methods**:
```python
def merge(
    base_path: Path,
    local_path: Path,
    remote_path: Path,
    output_path: Optional[Path] = None
) -> MergeResult

def merge_files(
    base_file: Path,
    local_file: Path,
    remote_file: Path,
    output_file: Optional[Path] = None
) -> MergeResult
```

**Merge Result Structure**:
```python
@dataclass
class MergeResult:
    success: bool                          # True if no conflicts
    auto_merged: List[str]                 # Successfully merged files
    conflicts: List[ConflictMetadata]      # Files with conflicts
    output_path: Optional[Path]
    error: Optional[str]
    stats: MergeStats
```

**Auto-Merge Strategies**:
- `use_local`: Copy local version (local changed, remote unchanged)
- `use_remote`: Copy remote version (remote changed, local unchanged)
- `use_base`: Copy base version (both deleted)
- `manual`: Generate conflict markers (both changed differently)

**Conflict Markers** (Git-style for text files):
```
<<<<<<< LOCAL (current)
local version content here
=======
remote version content here
>>>>>>> REMOTE (incoming)
```

**Atomic File Operations**:
```python
def _atomic_copy(source: Path, dest: Path) -> None:
    # 1. Create temp file in destination directory
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".tmp"
    )
    # 2. Write/copy content to temp file
    # 3. Atomic rename (atomic on POSIX systems)
    Path(tmp_path).replace(dest)
```

**Transaction Logging**:
- Tracks files written during merge
- Allows rollback if operation fails
- Deletes created files if merge is interrupted

### VersionManager

**Responsibility**: High-level versioning operations and safety analysis

**Key Methods**:
```python
def create_snapshot(
    collection_name: Optional[str] = None,
    message: str = "Manual snapshot"
) -> Snapshot

def list_snapshots(
    collection_name: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None
) -> Tuple[List[Snapshot], Optional[str]]

def rollback(
    snapshot_id: str,
    collection_name: Optional[str] = None,
    confirm: bool = True
) -> None

def intelligent_rollback(
    snapshot_id: str,
    collection_name: Optional[str] = None,
    preserve_changes: bool = True,
    selective_paths: Optional[List[str]] = None,
    confirm: bool = True
) -> RollbackResult

def analyze_rollback_safety(
    snapshot_id: str,
    collection_name: Optional[str] = None
) -> RollbackSafetyAnalysis
```

**RollbackSafetyAnalysis**:
```python
@dataclass
class RollbackSafetyAnalysis:
    is_safe: bool
    snapshot_id: str
    snapshot_exists: bool
    local_changes_detected: int          # Count of local changes
    files_with_conflicts: List[str]      # Files requiring manual resolution
    files_safe_to_restore: List[str]     # Files that won't cause issues
    files_to_merge: List[str]            # Binary files needing manual merge
    warnings: List[str]                  # User-friendly warnings
```

**RollbackResult**:
```python
@dataclass
class RollbackResult:
    success: bool
    snapshot_id: str
    files_restored: List[str]
    files_merged: List[str]
    conflicts: List[ConflictMetadata]
    safety_snapshot_id: Optional[str]    # Snapshot created before rollback
    has_conflicts: bool
    error: Optional[str]
```

### VersionMergeService

**Responsibility**: Coordinating merge workflows and version operations

**Key Methods**:
```python
def analyze_merge_safety(
    base_snapshot_id: str,
    local_collection: str,
    remote_snapshot_id: str
) -> MergeSafetyAnalysis

def merge_with_conflict_detection(
    base_snapshot_id: str,
    local_collection: str,
    remote_snapshot_id: str,
    output_path: Optional[Path] = None,
    auto_snapshot: bool = True
) -> VersionMergeResult

def get_merge_preview(
    base_snapshot_id: str,
    local_collection: str,
    remote_snapshot_id: str
) -> MergePreview

def route_sync_merge(
    direction: SyncDirection,
    source_path: Path,
    target_path: Path,
    strategy: Optional[SyncMergeStrategy] = None,
    base_snapshot_id: Optional[str] = None
) -> VersionMergeResult
```

**MergeSafetyAnalysis**:
```python
@dataclass
class MergeSafetyAnalysis:
    can_auto_merge: bool
    files_to_merge: List[str]
    auto_mergeable_count: int
    conflict_count: int
    conflicts: List[ConflictMetadata]
    warnings: List[str]
```

**MergePreview**:
```python
@dataclass
class MergePreview:
    base_snapshot_id: str
    remote_snapshot_id: str
    files_changed: List[str]
    files_added: List[str]
    files_removed: List[str]
    potential_conflicts: List[ConflictMetadata]
    can_auto_merge: bool
```

**Sync Direction Strategies**:
```python
UPSTREAM_TO_COLLECTION:
  - Upstream is authoritative
  - Preserve local changes where possible
  - Warn on conflicts

COLLECTION_TO_PROJECT:
  - Collection is authoritative
  - Preserve project customizations
  - Auto-merge with conflict detection

PROJECT_TO_COLLECTION:
  - More conservative (reverse sync)
  - Require explicit approval
  - Always prompt on conflicts

BIDIRECTIONAL:
  - Full three-way merge
  - Both sides equal
  - Always prompt on conflicts
```

### RollbackAuditTrail

**Responsibility**: Recording and querying rollback operations

**Key Methods**:
```python
def record(entry: RollbackAuditEntry) -> None

def get_history(
    collection_name: str,
    limit: int = 50
) -> List[RollbackAuditEntry]

def get_entry(entry_id: str) -> Optional[RollbackAuditEntry]
```

## Data Flow

### Snapshot Creation Flow

```
┌─────────────────────────┐
│  create_snapshot()      │
│  (user or auto)         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Validate collection exists             │
│  Generate timestamp-based ID            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Create .tar.gz in ~/.skillmeat/        │
│  snapshots/{collection_name}/           │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Count artifacts for metadata           │
│  Create Snapshot object                 │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Update snapshots.toml with metadata    │
│  Atomic write for consistency           │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│  Return Snapshot        │
└─────────────────────────┘
```

### Simple Rollback Flow

```
┌────────────────────────┐
│  rollback()            │
│  (user request)        │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Validate snapshot exists              │
│  Prompt user for confirmation          │
└───────────┬───────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Create safety snapshot (current state)│
│  Store as "Before rollback" message    │
└───────────┬───────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Remove existing collection directory  │
│  Extract target snapshot to location   │
└───────────┬───────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Record audit entry                    │
│  operation_type = "simple"             │
└───────────┬───────────────────────────┘
            │
            ▼
┌────────────────────────┐
│  Return success        │
└────────────────────────┘
```

### Intelligent Rollback Flow

```
┌──────────────────────────┐
│  intelligent_rollback()  │
│  (with change preserve)  │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  analyze_rollback_safety()               │
│  Perform three-way diff:                 │
│  - base = target snapshot                │
│  - local = current collection state      │
│  - remote = target snapshot (same)       │
└──────────────┬───────────────────────────┘
               │
               ▼
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
  Is safe?         Has conflicts?
  (no conflicts)   (show warnings)
      │                 │
      │                 ▼
      │         Prompt user to proceed
      │                 │
      └─────────┬───────┘
                │
                ▼
┌──────────────────────────────────────────┐
│  Create safety snapshot (before rollback)│
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Extract target snapshot to temp dir     │
│  Copy current state to temp dir (local)  │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Perform DiffEngine.three_way_diff()     │
│  Identify:                               │
│  - auto_mergeable files                  │
│  - conflicting files                     │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  MergeEngine.merge() in temp directory   │
│  - Generate conflict markers for text    │
│  - Copy auto-merged files                │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Restore snapshot to collection          │
│  Overlay merged changes (preservation)   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Record audit entry                      │
│  operation_type = "intelligent"          │
│  files_merged = merged files             │
│  conflicts_pending = conflict files      │
└──────────────┬───────────────────────────┘
               │
               ▼
┌────────────────────────────────┐
│  Return RollbackResult with:   │
│  - success status              │
│  - list of merged files        │
│  - list of conflicted files    │
│  - safety snapshot ID          │
└────────────────────────────────┘
```

### Merge with Conflict Detection Flow

```
┌─────────────────────────────────────┐
│  merge_with_conflict_detection()    │
│  (sync or manual merge)             │
└────────────┬──────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  analyze_merge_safety()              │
│  Perform three-way diff on temps     │
│  - base = base snapshot              │
│  - local = current collection        │
│  - remote = incoming snapshot        │
└────────────┬───────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Create pre-merge safety snapshot    │
│  (current collection state)          │
└────────────┬───────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Extract base and remote to temps    │
│  Keep local in-place (not copied)    │
└────────────┬───────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  MergeEngine.merge()                 │
│  (output_path = local collection)    │
└────────────┬───────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Process auto-mergeable files        │
│  - Copy winning version to output    │
│  - Update local collection in-place  │
└────────────┬───────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Process conflicts                   │
│  - Generate conflict markers (text)  │
│  - Flag binary conflicts             │
│  - Write to output (local collection)│
└────────────┬───────────────────────┘
             │
             ▼
┌───────────────────────────────────────┐
│  Return VersionMergeResult:           │
│  - success = (no conflicts)           │
│  - files_merged = auto-merged list    │
│  - conflicts = conflicted files       │
│  - pre_merge_snapshot_id = safety ID  │
└───────────────────────────────────────┘
```

## Performance Considerations

### Tarball Compression

- **Algorithm**: Gzip (deflate)
- **Typical compression ratio**: 3:1 to 5:1 for artifact content
- **Trade-off**: Compression time vs storage savings
- **Recommendation**: ~500MB uncompressed → ~100MB compressed

### Pagination Performance

- **Cursor-based pagination**: O(n) scan from cursor position
- **Typical operation**: 50 snapshots per page
- **Max limit**: 100 snapshots (capped for performance)
- **Metadata parsing**: TOML parsing vs lazy loading (current: eager)

### Diff Engine Optimization

- **Hash-based comparison**: SHA-256 for fast equality check (fast path)
- **File size quick-reject**: Files with different sizes are different
- **Binary detection**: 8KB header scan, cache results
- **Ignore patterns**: Fnmatch-based filtering (fast for common patterns)

### Temporary Directory Usage

- **Merge operations**: Extract snapshots to `/tmp` for comparison
- **Atomic writes**: Temp files in same directory as destination for atomic rename
- **Cleanup**: Temp files deleted on completion or error
- **Symlink handling**: Resolved (not followed for security)

### Caching Strategy for VersionGraphBuilder

- **Cache TTL**: 5 minutes
- **Cache key**: `{artifact_id}:{collection_name}`
- **Invalidation**: Manual `clear_cache()` after deployments
- **Memory**: In-memory dict (suitable for per-process cache)

## Future Extensibility

### Retention Policies

Current: `cleanup_old_snapshots()` keeps fixed count
Future:
- Time-based: Keep snapshots from last 30 days
- Size-based: Keep until total size exceeds threshold
- Incremental: Delta compression between snapshots
- Scheduling: Background cleanup jobs

### Per-Artifact Versioning

Current: Collection-level only
Possible future enhancement:
- Track individual artifact versions
- Selective restore of specific artifacts
- Artifact-level dependency tracking

### Repository Abstraction Layer

Current: Local filesystem storage
Future:
- Abstract `RepositoryBackend` interface
- Implementations: Local, S3, Azure Blob, Git
- Enable distributed deployment tracking

### Advanced Queries

Current: Simple ID/collection lookups
Future:
- Query artifacts by content hash
- Find deployments with local modifications
- Trace artifact lineage across projects
- Dependency graph visualization

### Conflict Resolution Strategies

Current: Manual resolution via conflict markers
Future:
- `three-way-merge` algorithm (standard VCS approach)
- `prefer-local` / `prefer-remote` strategies
- Custom merge scripts (plugins)
- Semantic merge for YAML/JSON files

### Version Tracking Across Collections

Current: Per-collection audit trails
Future:
- Cross-collection version lineage
- Collection dependency graph
- Version compatibility matrix
- Shared artifact metadata registry

## Error Handling

### Safe Failure Modes

| Operation | Failure | Handling |
|-----------|---------|----------|
| Snapshot creation | Tarball write fails | Partial tarball deleted, error raised |
| Rollback | Extract fails | Safety snapshot preserved for recovery |
| Merge | Conflict detected | Conflict markers written, no data loss |
| Atomic write | Temp file failure | Destination unchanged, error raised |

### User-Facing Errors

```python
class SnapshotError(Exception):
    """Failed to create/restore snapshot"""

class MergeConflictError(Exception):
    """Merge resulted in conflicts (not necessarily fatal)"""

class RollbackError(Exception):
    """Rollback operation failed"""
```

## Security Considerations

### Atomic Operations

- All file writes use atomic temp+rename pattern
- Prevents partial/corrupted state on crash
- Safe on POSIX systems (ext4, HFS+, NTFS)

### Permission Checks

- Snapshot dir creation: User's home directory
- Restore: Extract to writable collection path
- Audit log: Per-collection write access

### Content Integrity

- SHA-256 hashing for version tracking
- No encryption (optional future enhancement)
- Tarball CRC validation on extraction

### Audit Trail Immutability

- Append-only TOML files
- Timestamp and operation logging
- Enables investigation of data issues

## Testing Strategy

### Unit Tests

- DiffEngine: Binary detection, ignore patterns, three-way diff logic
- MergeEngine: Auto-merge strategies, conflict generation, atomic writes
- SnapshotManager: Tarball creation/extraction, metadata consistency

### Integration Tests

- End-to-end rollback: Create snapshot → modify collection → rollback
- Merge workflows: Analyze → preview → execute
- Conflict resolution: Generate markers, manual resolution, re-merge

### Performance Tests

- Large collection snapshots (1000+ artifacts)
- Deep directory structures
- Binary vs text file handling
- Compression ratios and speeds

## API Integration Points

### REST Endpoints

```
POST   /api/v1/versions/snapshots         # Create snapshot
GET    /api/v1/versions/snapshots         # List snapshots (paginated)
GET    /api/v1/versions/snapshots/{id}    # Get specific snapshot
DELETE /api/v1/versions/snapshots/{id}    # Delete snapshot

POST   /api/v1/versions/rollback          # Simple rollback
POST   /api/v1/versions/rollback/analyze  # Safety analysis
POST   /api/v1/versions/rollback/intelligent  # With change preservation

POST   /api/v1/merge/analyze              # Merge safety analysis
POST   /api/v1/merge/preview              # Get merge preview
POST   /api/v1/merge/execute              # Execute merge
POST   /api/v1/merge/resolve              # Resolve single conflict
```

### Web UI Components

- **SnapshotHistory**: List view with pagination
- **RollbackDialog**: Confirmation and safety analysis
- **MergeDialog**: Preview before merge
- **ConflictResolver**: Inline conflict editing

## Related Documentation

- **ADR-004**: Artifact version tracking architecture
- **Diff/Merge Strategy ADR**: Three-way diff algorithm details
- **Web API Documentation**: REST endpoint specifications
- **CLI Guide**: Command-line usage examples
