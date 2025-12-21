---
title: Merge Engine Developer Guide
description: Comprehensive guide for developers working with SkillMeat's three-way merge engine
audience: developers
tags:
  - merge
  - versioning
  - three-way-merge
  - conflict-resolution
  - diff-engine
created: 2025-12-17
updated: 2025-12-17
category: development
status: complete
related_documents:
  - ../versioning-system-architecture.md
  - ../conflict-resolution-strategies.md
---

# Merge Engine Developer Guide

This guide provides a comprehensive overview of SkillMeat's merge engine for developers who need to understand, extend, or integrate with the three-way merge system.

## Overview

The merge engine is responsible for intelligently combining file changes from two branches (local and remote) using a common ancestor (base) as reference. It automatically resolves simple cases and generates Git-style conflict markers for complex conflicts.

### Key Components

1. **DiffEngine** - Performs file/directory comparison and three-way analysis
2. **MergeEngine** - Executes merge operations and handles conflicts
3. **VersionMergeService** - High-level orchestration for merge workflows

### When to Use

| Operation | Use This | Why |
|-----------|----------|-----|
| Compare two files | `DiffEngine.diff_files()` | Fast hash-based comparison with unified diff output |
| Compare two directories | `DiffEngine.diff_directories()` | Identifies added, removed, and modified files |
| Detect merge conflicts | `DiffEngine.three_way_diff()` | Compares three versions to classify changes |
| Execute merge | `MergeEngine.merge()` | Performs actual merge with conflict detection |
| High-level workflows | `VersionMergeService` | Orchestrates merge with snapshots and safety features |

## DiffEngine API Reference

The DiffEngine performs all comparison operations. Located in `skillmeat/core/diff_engine.py`.

### File Comparison

Compare two individual files with binary detection and unified diff generation.

```python
from skillmeat.core.diff_engine import DiffEngine
from pathlib import Path

diff_engine = DiffEngine()

# Compare two text files
result = diff_engine.diff_files(
    source_file=Path("old.py"),
    target_file=Path("new.py")
)

print(f"Status: {result.status}")  # "modified", "unchanged", "binary"
print(f"Lines added: {result.lines_added}")
print(f"Lines removed: {result.lines_removed}")

if result.unified_diff:
    print("Diff output:")
    print(result.unified_diff)
```

**FileDiff Result Structure:**

```python
@dataclass
class FileDiff:
    path: str                           # Relative path to file
    status: str                         # "added", "removed", "modified", "unchanged", "binary"
    lines_added: int                    # Count of added lines (text only)
    lines_removed: int                  # Count of removed lines (text only)
    unified_diff: Optional[str]         # Unified diff output (None for binary)
```

**Status Meanings:**

| Status | Meaning |
|--------|---------|
| `unchanged` | Files are identical (no diff needed) |
| `modified` | Files differ, unified diff generated |
| `binary` | At least one file is binary, cannot generate diff |

### Directory Comparison

Compare entire directory structures with recursive file analysis.

```python
# Compare two directories
diff_result = diff_engine.diff_directories(
    source_path=Path("base"),
    target_path=Path("modified"),
    ignore_patterns=["*.pyc", "__pycache__", ".git"]
)

print(f"Files added: {diff_result.files_added}")           # List[str]
print(f"Files removed: {diff_result.files_removed}")       # List[str]
print(f"Files modified: {len(diff_result.files_modified)}")  # List[FileDiff]
print(f"Files unchanged: {len(diff_result.files_unchanged)}")

# Get summary
print(diff_result.summary())  # "3 added, 2 removed, 5 modified (+45 -23 lines)"
```

**DiffResult Properties:**

```python
@dataclass
class DiffResult:
    source_path: Path                   # Source directory
    target_path: Path                   # Target directory
    files_added: List[str]              # New files in target
    files_removed: List[str]            # Deleted files from source
    files_modified: List[FileDiff]      # Changed files with diff details
    files_unchanged: List[str]          # Files that didn't change
    total_lines_added: int              # Sum across all modified files
    total_lines_removed: int            # Sum across all modified files

    @property
    def has_changes(self) -> bool:      # True if any changes
    @property
    def total_files_changed(self) -> int:  # Count of changed files
    def summary(self) -> str:           # Human-readable summary
```

### Three-Way Diff

Perform three-way comparison for merge conflict detection.

```python
# Perform three-way diff
result = diff_engine.three_way_diff(
    base_path=Path("base"),           # Common ancestor
    local_path=Path("local"),         # Your changes
    remote_path=Path("remote"),       # Changes to merge in
    ignore_patterns=["*.pyc", ".git"]
)

# Check for auto-mergeable changes
print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
for file_path in result.auto_mergeable:
    print(f"  - {file_path}")

# Check for conflicts
print(f"Conflicts: {len(result.conflicts)}")
for conflict in result.conflicts:
    print(f"  - {conflict.file_path}: {conflict.conflict_type}")
    if conflict.is_binary:
        print(f"    (binary file - cannot auto-merge)")
```

**ThreeWayDiffResult:**

```python
@dataclass
class ThreeWayDiffResult:
    base_path: Path                     # Base directory
    local_path: Path                    # Local directory
    remote_path: Path                   # Remote directory
    auto_mergeable: List[str]           # Files that can auto-merge
    conflicts: List[ConflictMetadata]   # Files requiring manual resolution
    stats: DiffStats                    # Statistics
```

### Understanding Three-Way Merge Logic

The three-way diff algorithm compares files across three versions to classify changes:

```
Case 1: All unchanged
  base == local == remote → No action needed

Case 2: Only one version changed
  base == local, remote changed → Auto-merge (use remote)
  base == remote, local changed → Auto-merge (use local)

Case 3: Both changed identically
  local == remote (but != base) → Auto-merge (both agree)

Case 4: Both changed to different content
  base != local != remote → Conflict (manual resolution required)

Case 5: Add/add conflict
  file not in base, added in both → Conflict if different content

Case 6: Modify/delete conflict
  file modified in one, deleted in other → Conflict
```

**Example Scenarios:**

```python
# Scenario: Only local modified
# base:   "Hello\nWorld"
# local:  "Hello\nUniverse"
# remote: "Hello\nWorld"
# Result: Auto-merge, use local (only local changed)

# Scenario: Only remote modified
# base:   "Hello\nWorld"
# local:  "Hello\nWorld"
# remote: "Hello\nGalaxy"
# Result: Auto-merge, use remote (only remote changed)

# Scenario: Both modified differently
# base:   "Hello\nWorld"
# local:  "Hello\nUniverse"
# remote: "Hello\nGalaxy"
# Result: Conflict (both changed, no consensus)

# Scenario: Symmetric modification
# base:   "Hello\nWorld"
# local:  "Hello\nWorld\nGoodbye"
# remote: "Hello\nWorld\nGoodbye"
# Result: Auto-merge, both changed identically
```

### ConflictMetadata Structure

Detailed information about a detected conflict:

```python
@dataclass
class ConflictMetadata:
    file_path: str                      # Relative path to conflicting file
    conflict_type: str                  # Type of conflict detected
    base_content: Optional[str]         # Content from base (None if new)
    local_content: Optional[str]        # Content from local (None if deleted)
    remote_content: Optional[str]       # Content from remote (None if deleted)
    auto_mergeable: bool                # Can be auto-merged?
    merge_strategy: Optional[str]       # Recommended strategy if auto_mergeable
    is_binary: bool                     # Binary files cannot merge content

# Conflict types:
# "content" - File content differs
# "deletion" - One version deleted, other modified
# "both_modified" - Both versions modified differently
# "add_add" - Both versions added file with different content
```

## MergeEngine API Reference

The MergeEngine executes merge operations. Located in `skillmeat/core/merge_engine.py`.

### Merge Directories

Perform complete three-way merge of directory structures.

```python
from skillmeat.core.merge_engine import MergeEngine
from pathlib import Path

engine = MergeEngine(ignore_patterns=["*.pyc", "__pycache__"])

# Execute merge
result = engine.merge(
    base_path=Path("base"),
    local_path=Path("local"),
    remote_path=Path("remote"),
    output_path=Path("merged")  # Optional - if not provided, only analyzes
)

# Check result
if result.success:
    print(f"Merge successful!")
    print(f"Auto-merged files: {len(result.auto_merged)}")
else:
    print(f"Merge has conflicts: {len(result.conflicts)}")
    for conflict in result.conflicts:
        print(f"  - {conflict.file_path}: {conflict.conflict_type}")

# Check statistics
print(f"Total files processed: {result.stats.total_files}")
print(f"Binary conflicts: {result.stats.binary_conflicts}")
```

**MergeResult:**

```python
@dataclass
class MergeResult:
    success: bool                       # True if no conflicts
    auto_merged: List[str]              # Files successfully merged
    conflicts: List[ConflictMetadata]   # Files with conflicts
    stats: MergeStats                   # Operation statistics
    output_path: Optional[Path]         # Where merged files were written
    error: Optional[str]                # Error message if failed

@dataclass
class MergeStats:
    total_files: int = 0
    auto_merged: int = 0
    conflicts: int = 0
    binary_conflicts: int = 0
```

### Merge Individual Files

Merge three versions of a single file.

```python
# Merge three versions of one file
result = engine.merge_files(
    base_file=Path("base/config.json"),
    local_file=Path("local/config.json"),
    remote_file=Path("remote/config.json"),
    output_file=Path("merged/config.json")  # Optional
)

# Access merged content
if result.success:
    print("File merged successfully")
    # merged_file exists at output_file path
else:
    print(f"Conflicts detected in file")
    # result.merged_content contains the file with conflict markers
    if result.merged_content:
        print(result.merged_content)
```

### Conflict Markers

When text file conflicts occur, the merge engine generates Git-style conflict markers:

```
<<<<<<< LOCAL (current)
Your local changes here
...
=======
Remote changes here
...
>>>>>>> REMOTE (incoming)
```

**Real Example:**

```python
# If local and remote both modify config.json differently:

# base/config.json:
"""
{
  "version": "1.0",
  "debug": false
}
"""

# local/config.json:
"""
{
  "version": "1.1",
  "debug": true,
  "timeout": 30
}
"""

# remote/config.json:
"""
{
  "version": "2.0",
  "debug": false,
  "max_retries": 3
}
"""

# merged result (with conflict markers):
"""
<<<<<<< LOCAL (current)
{
  "version": "1.1",
  "debug": true,
  "timeout": 30
}
=======
{
  "version": "2.0",
  "debug": false,
  "max_retries": 3
}
>>>>>>> REMOTE (incoming)
"""
```

### Initialization Options

Configure the merge engine with ignore patterns.

```python
# Default initialization
engine = MergeEngine()

# With custom ignore patterns
engine = MergeEngine(ignore_patterns=[
    "*.pyc",           # Python bytecode
    "__pycache__",     # Python cache directories
    ".git/*",          # Git metadata
    "node_modules/*",  # Node dependencies
    ".DS_Store",       # macOS metadata
    "*.log",           # Log files
    "*.tmp"            # Temporary files
])

# Built-in default patterns (always included):
# __pycache__, *.pyc, *.pyo, .git, .gitignore,
# node_modules, .DS_Store, *.swp, .pytest_cache,
# .mypy_cache, .ruff_cache, *.egg-info, dist, build
```

## VersionMergeService API Reference

High-level service for orchestrating merge workflows. Located in `skillmeat/core/version_merge.py`.

### Pre-Merge Safety Analysis

Analyze potential conflicts before attempting merge.

```python
from skillmeat.core.version_merge import VersionMergeService

service = VersionMergeService()

# Analyze merge safety (dry-run, no files modified)
analysis = service.analyze_merge_safety(
    base_snapshot_id="20241201-120000",
    local_collection="main",
    remote_snapshot_id="20241215-150000"
)

# Check results
if analysis.can_auto_merge:
    print("Safe to auto-merge")
    print(f"Auto-mergeable files: {analysis.auto_mergeable_count}")
else:
    print(f"Conflicts detected: {analysis.conflict_count}")
    for conflict in analysis.conflicts:
        print(f"  - {conflict.file_path}")

# Check warnings
for warning in analysis.warnings:
    print(f"Warning: {warning}")
```

**MergeSafetyAnalysis:**

```python
@dataclass
class MergeSafetyAnalysis:
    can_auto_merge: bool                # Safe to auto-merge?
    files_to_merge: List[str]           # All files involved
    auto_mergeable_count: int           # Count auto-mergeable
    conflict_count: int                 # Count conflicting
    conflicts: List[ConflictMetadata]   # Detailed conflict info
    warnings: List[str]                 # User-friendly warnings
    is_safe: bool                       # Overall safety assessment
```

### Execute Merge with Conflict Detection

Perform complete merge with safety snapshots and comprehensive conflict reporting.

```python
# Execute merge
result = service.merge_with_conflict_detection(
    base_snapshot_id="20241201-120000",
    local_collection="main",
    remote_snapshot_id="20241215-150000",
    auto_snapshot=True  # Create backup before merge
)

# Check status
if result.success:
    print(f"Merge completed successfully")
    print(f"Files merged: {len(result.files_merged)}")
else:
    print(f"Merge has conflicts: {len(result.conflicts)}")
    if result.pre_merge_snapshot_id:
        print(f"Safety snapshot created: {result.pre_merge_snapshot_id}")

# Examine conflicts
for conflict in result.conflicts:
    print(f"Conflict: {conflict.file_path}")
    print(f"  Type: {conflict.conflict_type}")
    print(f"  Binary: {conflict.is_binary}")
```

**VersionMergeResult:**

```python
@dataclass
class VersionMergeResult:
    success: bool                       # Merge completed without conflicts?
    merge_result: Optional[MergeResult] # Underlying merge result
    files_merged: List[str]             # Successfully merged files
    conflicts: List[ConflictMetadata]   # Unresolved conflicts
    pre_merge_snapshot_id: Optional[str] # Safety snapshot ID
    error: Optional[str]                # Error message if failed
```

### Merge Preview

Get preview of what would change without executing merge.

```python
# Get preview
preview = service.get_merge_preview(
    base_snapshot_id="20241201-120000",
    local_collection="main",
    remote_snapshot_id="20241215-150000"
)

print(f"Files to add: {len(preview.files_added)}")
print(f"Files to remove: {len(preview.files_removed)}")
print(f"Files to change: {len(preview.files_changed)}")
print(f"Potential conflicts: {len(preview.potential_conflicts)}")

if preview.can_auto_merge:
    print("Can merge automatically")
else:
    print("Manual resolution required")
```

### Conflict Resolution

Resolve individual conflicts after merge.

```python
# After merge with conflicts, resolve them
conflict = result.conflicts[0]

# Resolution options:
# 1. Use local version
service.resolve_conflict(conflict, "use_local")

# 2. Use remote version
service.resolve_conflict(conflict, "use_remote")

# 3. Use base version
service.resolve_conflict(conflict, "use_base")

# 4. Use custom content
service.resolve_conflict(
    conflict,
    "custom",
    custom_content="combined content"
)
```

### Recommended Merge Strategy

Get merge strategy based on sync direction and change state.

```python
from skillmeat.models import SyncDirection

strategy = service.get_recommended_strategy(
    direction=SyncDirection.UPSTREAM_TO_COLLECTION,
    has_local_changes=True,
    has_remote_changes=True
)

print(f"Auto-merge: {strategy.auto_merge}")
print(f"Conflict action: {strategy.conflict_action}")
print(f"Create backup: {strategy.create_backup}")

# Strategy recommendations by direction:
# UPSTREAM_TO_COLLECTION: Prefer upstream, warn on local changes
# COLLECTION_TO_PROJECT: Prefer collection, preserve project customizations
# PROJECT_TO_COLLECTION: Require explicit approval
# BIDIRECTIONAL: Full three-way merge with prompts
```

## Error Handling

Proper error handling patterns for merge operations.

```python
from pathlib import Path
from skillmeat.core.merge_engine import MergeEngine

engine = MergeEngine()

try:
    result = engine.merge(
        base_path=Path("base"),
        local_path=Path("local"),
        remote_path=Path("remote")
    )
except FileNotFoundError as e:
    print(f"Path not found: {e}")
    # Handle: Check that all three paths exist
except NotADirectoryError as e:
    print(f"Expected directory: {e}")
    # Handle: Ensure all paths are directories
except PermissionError as e:
    print(f"Permission denied: {e}")
    # Handle: Check file permissions
except OSError as e:
    print(f"I/O error during merge: {e}")
    # Handle: Check disk space, filesystem issues

# Always check result.error even if no exception
if result.error:
    print(f"Merge failed: {result.error}")
```

## Testing Merge Logic

Write tests for merge operations.

```python
import tempfile
from pathlib import Path
from skillmeat.core.merge_engine import MergeEngine

def test_simple_merge():
    """Test auto-merge of non-overlapping changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directories
        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for d in [base, local, remote, output]:
            d.mkdir()

        # Create base file
        (base / "file.txt").write_text("Line 1\nLine 2\nLine 3\n")

        # Local modifies line 2
        (local / "file.txt").write_text("Line 1\nLine 2 MODIFIED\nLine 3\n")

        # Remote modifies line 3
        (remote / "file.txt").write_text("Line 1\nLine 2\nLine 3 MODIFIED\n")

        # Merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        # Verify
        assert result.success, f"Merge should succeed, got: {result.error}"
        assert len(result.auto_merged) == 1
        assert len(result.conflicts) == 0

        # Verify merged content
        merged = (output / "file.txt").read_text()
        assert "Line 2 MODIFIED" in merged
        assert "Line 3 MODIFIED" in merged


def test_conflict_detection():
    """Test conflict detection on overlapping changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directories
        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for d in [base, local, remote, output]:
            d.mkdir()

        # Create base file
        (base / "file.txt").write_text("shared\nchangeable\nshared\n")

        # Local modifies changeable line
        (local / "file.txt").write_text("shared\nLOCAL\nshared\n")

        # Remote also modifies changeable line (differently)
        (remote / "file.txt").write_text("shared\nREMOTE\nshared\n")

        # Merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        # Verify conflict
        assert not result.success, "Should have conflicts"
        assert len(result.conflicts) == 1
        assert result.conflicts[0].conflict_type == "both_modified"
        assert not result.conflicts[0].is_binary

        # Verify conflict markers
        merged = (output / "file.txt").read_text()
        assert "<<<<<<< LOCAL" in merged
        assert "=======" in merged
        assert ">>>>>>> REMOTE" in merged
```

## Extending the Merge Engine

### Custom Ignore Patterns

Create a merge engine with domain-specific ignore patterns.

```python
# For Python projects
python_engine = MergeEngine(ignore_patterns=[
    "*.pyc",
    "*.pyo",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "*.egg-info"
])

# For Node.js projects
node_engine = MergeEngine(ignore_patterns=[
    "node_modules",
    "package-lock.json",
    "yarn.lock",
    ".npm",
    "dist",
    "build"
])

# For general projects
general_engine = MergeEngine(ignore_patterns=[
    ".git",
    ".gitignore",
    ".github",
    ".gitlab",
    ".vscode",
    ".idea",
    ".DS_Store",
    "Thumbs.db"
])
```

### Merge Strategies

The merge engine supports multiple strategies for different scenarios:

| Strategy | When to Use | Example |
|----------|------------|---------|
| `use_local` | Local-only changes | One version deleted file |
| `use_remote` | Remote-only changes | Only remote added content |
| `use_base` | Both deleted | Agree on deletion |
| `manual` | Conflicting changes | Both modified same lines |

```python
# Strategy is determined automatically based on changes
# But you can inspect and override after merge:

result = engine.merge(base, local, remote, output)

for conflict in result.conflicts:
    if conflict.conflict_type == "deletion":
        # One deleted, one modified
        if conflict.local_content is None:
            # Use remote (local was deleted)
            print(f"File should be deleted: {conflict.file_path}")
```

## Performance Considerations

### Hash-Based File Comparison

The diff engine uses SHA-256 hashing for fast file comparison:

```python
# Files are compared by:
# 1. Size check (fast)
# 2. SHA-256 hash comparison (fast for large files)
# 3. Content comparison only if needed

# This makes it efficient even for large files:
result = engine.diff_files(
    Path("large_binary.bin"),  # 100MB file
    Path("modified_binary.bin")  # Only compares hashes, not content
)
```

### Directory Recursion

Directory comparison is recursive and efficient:

```python
# Scans entire directory tree
# Respects ignore patterns to skip directories
# Uses set operations for O(n) complexity

result = engine.diff_directories(
    Path("huge_directory"),  # Millions of files
    Path("huge_directory_modified"),
    ignore_patterns=["node_modules/*", ".git/*"]  # Skip large directories
)
```

### Atomic Operations

All file writes are atomic using temp files:

```python
# Merge engine uses temporary files and atomic rename
# to ensure consistency:
#
# 1. Write to .filename.tmp in same directory
# 2. Atomic rename to final filename
# 3. If error: cleanup temp file
#
# This ensures no partial/corrupt files on failure
```

## Common Patterns

### Check for Safe Auto-Merge

```python
service = VersionMergeService()

analysis = service.analyze_merge_safety(
    base_snapshot_id="snap_base",
    local_collection="main",
    remote_snapshot_id="snap_remote"
)

if analysis.can_auto_merge:
    # Safe to merge automatically
    result = service.merge_with_conflict_detection(
        base_snapshot_id="snap_base",
        local_collection="main",
        remote_snapshot_id="snap_remote"
    )
else:
    # Require manual resolution
    print(f"Requires manual resolution: {analysis.conflict_count} conflicts")
    for conflict in analysis.conflicts:
        print(f"  - {conflict.file_path}")
```

### Merge with Fallback Strategy

```python
engine = MergeEngine()

# First, try automatic merge
result = engine.merge(base, local, remote)

if not result.success:
    # If conflicts exist, try alternative strategies
    for conflict in result.conflicts:
        if conflict.conflict_type == "both_modified":
            # For overlapping edits, prefer local
            print(f"Preferring local version: {conflict.file_path}")
        elif conflict.is_binary:
            # For binary conflicts, use remote
            print(f"Using remote version: {conflict.file_path}")
```

### Generate User-Friendly Conflict Report

```python
result = service.merge_with_conflict_detection(...)

if not result.success:
    report = []
    report.append(f"Merge completed with {len(result.conflicts)} conflicts:")
    report.append("")

    # Group by type
    by_type = {}
    for conflict in result.conflicts:
        ctype = conflict.conflict_type
        if ctype not in by_type:
            by_type[ctype] = []
        by_type[ctype].append(conflict)

    for ctype, conflicts in by_type.items():
        report.append(f"{ctype} ({len(conflicts)} files):")
        for conflict in conflicts:
            icon = "BINARY" if conflict.is_binary else "TEXT"
            report.append(f"  [{icon}] {conflict.file_path}")
        report.append("")

    print("\n".join(report))
```

## Integration with Other Systems

### Using with Sync Engine

```python
from skillmeat.core.sync_engine import SyncEngine
from skillmeat.models import SyncDirection

sync = SyncEngine()

# Sync uses merge internally for intelligent updates
result = sync.sync(
    source="github:user/repo",
    target="~/.skillmeat/collection/main",
    direction=SyncDirection.UPSTREAM_TO_COLLECTION
)

# Merge conflicts are part of sync result
if result.conflicts:
    # Handle via merge service
    service = VersionMergeService()
    for conflict in result.conflicts:
        service.resolve_conflict(conflict, "use_remote")
```

### Version Control Integration

```python
from skillmeat.core.version_merge import VersionMergeService

service = VersionMergeService()

# Get pre-merge snapshot as backup
pre_snapshot = version_mgr.auto_snapshot(
    "main",
    "Before merge with feature-branch"
)

# Execute merge
result = service.merge_with_conflict_detection(
    base_snapshot_id=common_ancestor,
    local_collection="main",
    remote_snapshot_id="feature-branch"
)

# If merge fails, rollback to pre-snapshot
if not result.success:
    version_mgr.restore_snapshot(pre_snapshot, target_path)
```

## Troubleshooting

### Merge Fails with "Path not found"

```python
# Solution: Verify all paths exist and are directories
from pathlib import Path

base = Path("base")
if not base.exists():
    raise FileNotFoundError(f"Base path does not exist: {base}")
if not base.is_dir():
    raise NotADirectoryError(f"Base path is not a directory: {base}")
```

### Binary Files Show as Conflicts

```python
# Binary files cannot have content merged
# Options:
# 1. Use strategy to prefer one version
if conflict.is_binary:
    # Prefer local version
    print(f"Binary conflict, using local: {conflict.file_path}")
    # File will be copied from local

# 2. Add to ignore patterns
engine = MergeEngine(ignore_patterns=["*.jpg", "*.png", "*.pdf"])
```

### Merge is Slow on Large Directories

```python
# Add ignore patterns to skip unnecessary directories
engine = MergeEngine(ignore_patterns=[
    "node_modules/*",  # Skip dependencies
    ".git/*",          # Skip version control
    "dist/*",          # Skip build output
    ".venv/*"          # Skip virtual env
])

# Merge will be much faster by skipping these
result = engine.merge(base, local, remote)
```

### Conflict Markers Appear in Wrong Place

```python
# This usually means files have different line endings
# Solution: Ensure consistent line endings

# Check line endings
with open(file, 'rb') as f:
    content = f.read()
    if b'\r\n' in content:
        print("File has Windows line endings (CRLF)")
    elif b'\n' in content:
        print("File has Unix line endings (LF)")

# Normalize line endings before merge
for path in [base, local, remote]:
    for file in path.rglob("*"):
        if file.is_file():
            content = file.read_bytes()
            # Convert CRLF to LF
            content = content.replace(b'\r\n', b'\n')
            file.write_bytes(content)
```

## See Also

- [Versioning System Architecture](../versioning-system-architecture.md)
- [Conflict Resolution Strategies](../conflict-resolution-strategies.md)
- [Sync Engine Documentation](../sync-engine-guide.md)
- [Version History and Snapshots](../snapshots-and-history.md)
