# Phase 1 to Phase 3 Handoff Notes

**Date**: 2025-11-15
**From**: Phase 1 (Intelligence Execution - Diff/Merge)
**To**: Phase 3 (Intelligence Execution - Sync)
**Status**: Phase 1 COMPLETE - Ready for Phase 3 Integration

## Executive Summary

Phase 1 has successfully implemented comprehensive diff and merge functionality for SkillMeat. The DiffEngine and MergeEngine provide robust, well-tested APIs for comparing artifacts and performing three-way merges with automatic conflict detection and resolution.

**Key Deliverables:**
- DiffEngine: File/directory diffing with three-way merge support
- MergeEngine: Intelligent merging with auto-resolution and conflict markers
- 87% test coverage across 84 comprehensive tests
- Performance: 218 files/second (500 files in ~2.3s)
- 40+ reusable test fixtures

## API Summary

### DiffEngine (`skillmeat/core/diff_engine.py`)

The DiffEngine provides file and directory comparison capabilities with support for three-way diffs needed for merge operations.

#### Core Methods

##### 1. `diff_files(source_file: Path, target_file: Path) -> FileDiff`

Compares two individual files, detecting text vs binary and generating unified diffs.

**Usage:**
```python
from pathlib import Path
from skillmeat.core.diff_engine import DiffEngine

engine = DiffEngine()
result = engine.diff_files(
    Path("old_version.txt"),
    Path("new_version.txt")
)

print(f"Status: {result.status}")  # "modified", "unchanged", "binary"
print(f"Changes: +{result.lines_added} -{result.lines_removed}")
if result.unified_diff:
    print(result.unified_diff)
```

**Returns:**
- `FileDiff` object with:
  - `path`: Relative file path
  - `status`: "modified", "unchanged", "binary"
  - `lines_added`: Number of lines added
  - `lines_removed`: Number of lines removed
  - `unified_diff`: Git-style unified diff (text files only)

**Edge Cases:**
- Binary files: Returns `status="binary"`, no unified diff
- Identical files: Fast path using SHA-256 hash comparison
- Encoding errors: Handled gracefully, falls back to binary

##### 2. `diff_directories(source_path: Path, target_path: Path, ignore_patterns: Optional[List[str]] = None) -> DiffResult`

Recursively compares two directory structures.

**Usage:**
```python
result = engine.diff_directories(
    Path("version1/"),
    Path("version2/"),
    ignore_patterns=["*.pyc", "*.swp"]  # Optional
)

print(result.summary())  # "5 added, 2 removed, 3 modified (+10 -5 lines)"
print(f"Added: {result.files_added}")
print(f"Removed: {result.files_removed}")
print(f"Modified: {result.files_modified}")
```

**Returns:**
- `DiffResult` object with:
  - `files_added`: List of added file paths
  - `files_removed`: List of removed file paths
  - `files_modified`: List of `FileDiff` objects
  - `files_unchanged`: List of unchanged file paths
  - `total_lines_added`: Cumulative lines added
  - `total_lines_removed`: Cumulative lines removed
  - `has_changes`: Boolean property
  - `summary()`: Human-readable summary

**Ignore Patterns:**
Default patterns automatically ignored:
- `__pycache__`, `*.pyc`, `*.pyo`
- `.git`, `.gitignore`
- `node_modules`
- `.DS_Store`
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `*.egg-info`, `dist`, `build`

##### 3. `three_way_diff(base_path: Path, local_path: Path, remote_path: Path, ignore_patterns: Optional[List[str]] = None) -> ThreeWayDiffResult`

**THIS IS THE KEY METHOD FOR PHASE 3 SYNC OPERATIONS.**

Performs three-way diff for merge conflict detection, comparing a common ancestor (base) with local and remote modifications.

**Three-Way Diff Logic:**

| Base | Local | Remote | Result |
|------|-------|--------|--------|
| A | A | A | NO CHANGE (unchanged) |
| A | A | B | AUTO-MERGE (use remote) |
| A | B | A | AUTO-MERGE (use local) |
| A | B | B | AUTO-MERGE (both identical) |
| A | B | C | CONFLICT (manual resolution) |
| A | - | A | AUTO-MERGE (delete local) |
| A | A | - | AUTO-MERGE (delete remote) |
| A | B | - | CONFLICT (modified vs deleted) |
| A | - | B | CONFLICT (deleted vs modified) |
| - | A | B | CONFLICT (add-add different) |
| - | A | A | AUTO-MERGE (add-add identical) |

**Usage for Sync:**
```python
result = engine.three_way_diff(
    base_path=Path("collection/skill/v1.0.0/"),     # Common ancestor
    local_path=Path(".claude/skills/skill/"),        # Local modifications
    remote_path=Path("collection/skill/v2.0.0/"),    # Remote/upstream version
)

# Check if can auto-merge
if result.can_auto_merge:
    print(f"Safe to auto-sync: {len(result.auto_mergeable)} files")
    for file_path in result.auto_mergeable:
        print(f"  - {file_path}")
else:
    print(f"Conflicts detected: {len(result.conflicts)} files")
    for conflict in result.conflicts:
        print(f"  - {conflict.file_path}: {conflict.conflict_type}")
        print(f"    Strategy: {conflict.merge_strategy}")
```

**Returns:**
- `ThreeWayDiffResult` object with:
  - `auto_mergeable`: List of file paths that can auto-merge
  - `conflicts`: List of `ConflictMetadata` objects requiring attention
  - `stats`: `DiffStats` with counts
  - `can_auto_merge`: Boolean (True if no conflicts)
  - `has_conflicts`: Boolean (True if conflicts exist)
  - `total_files`: Total files with changes
  - `summary()`: Human-readable summary

**ConflictMetadata Fields:**
```python
@dataclass
class ConflictMetadata:
    file_path: str                    # Relative path
    conflict_type: str                # "content", "deletion", "add_add", "both_modified"
    base_content: Optional[str]       # Content from base (None if binary/new)
    local_content: Optional[str]      # Content from local (None if deleted/binary)
    remote_content: Optional[str]     # Content from remote (None if deleted/binary)
    auto_mergeable: bool              # True if can auto-merge
    merge_strategy: str               # "use_local", "use_remote", "use_base", "manual"
    is_binary: bool                   # True if binary file
```

### MergeEngine (`skillmeat/core/merge_engine.py`)

The MergeEngine performs actual merge operations, auto-merging simple cases and generating conflict markers for complex conflicts.

#### Core Methods

##### 1. `merge(base_path: Path, local_path: Path, remote_path: Path, output_path: Optional[Path] = None) -> MergeResult`

Performs three-way merge with automatic conflict resolution.

**Usage for Sync:**
```python
from skillmeat.core.merge_engine import MergeEngine

merge_engine = MergeEngine(ignore_patterns=["*.pyc"])

result = merge_engine.merge(
    base_path=Path("collection/skill/v1.0.0/"),
    local_path=Path(".claude/skills/skill/"),
    remote_path=Path("collection/skill/v2.0.0/"),
    output_path=Path(".claude/skills/skill.merged/")
)

if result.success:
    print(f"Auto-merged successfully: {len(result.auto_merged)} files")
    # Replace local with merged output
else:
    print(f"Conflicts require resolution: {len(result.conflicts)} files")
    for conflict in result.conflicts:
        if conflict.is_binary:
            print(f"Binary conflict: {conflict.file_path}")
        else:
            print(f"Text conflict: {conflict.file_path}")
            # Conflict markers written to output_path
```

**Returns:**
- `MergeResult` object with:
  - `success`: Boolean (True if no conflicts)
  - `auto_merged`: List of auto-merged file paths
  - `conflicts`: List of `ConflictMetadata` objects
  - `output_path`: Path where merge result was written
  - `stats`: `MergeStats` with counts
  - `merged_content`: Content of merged file (for single-file merges)
  - `summary()`: Human-readable summary

**Auto-Merge Strategies:**

1. **use_local**: Copy local version to output
   - When: Remote unchanged, local modified
   - Sync implication: Keep local changes

2. **use_remote**: Copy remote version to output
   - When: Local unchanged, remote modified
   - Sync implication: Accept upstream changes

3. **use_base**: Copy base version to output
   - When: Both deleted (rare case)
   - Sync implication: File removed

4. **manual**: Generate conflict markers or flag binary conflict
   - When: Both modified differently
   - Sync implication: User intervention required

##### 2. `merge_files(base_file: Path, local_file: Path, remote_file: Path, output_file: Optional[Path] = None) -> MergeResult`

Convenience method for merging individual files.

**Usage:**
```python
result = merge_engine.merge_files(
    base_file=Path("collection/skill/v1.0.0/SKILL.md"),
    local_file=Path(".claude/skills/skill/SKILL.md"),
    remote_file=Path("collection/skill/v2.0.0/SKILL.md"),
    output_file=Path(".claude/skills/skill/SKILL.md.merged")
)

if result.success:
    print(result.merged_content)  # Available in result
```

## Conflict Resolution Patterns

### Pattern 1: Auto-Sync Safe Files

When `auto_mergeable` is True, the file can be safely synced without user intervention.

```python
def sync_auto_mergeable(diff_result: ThreeWayDiffResult, engine: MergeEngine):
    """Sync all auto-mergeable files."""
    for file_path in diff_result.auto_mergeable:
        # Get the conflict metadata to determine merge strategy
        metadata = engine.diff_engine._analyze_three_way_file(
            file_path, base_path, local_path, remote_path, []
        )

        if metadata.merge_strategy == "use_remote":
            # Accept upstream change
            shutil.copy2(remote_path / file_path, local_path / file_path)
        elif metadata.merge_strategy == "use_local":
            # Keep local change (no action needed)
            pass
        # Handle other strategies as needed
```

### Pattern 2: Interactive Conflict Resolution

When conflicts exist, present to user for resolution.

```python
def handle_conflicts(result: ThreeWayDiffResult):
    """Present conflicts to user for resolution."""
    if not result.has_conflicts:
        return

    for conflict in result.conflicts:
        if conflict.is_binary:
            # Binary conflicts require user choice
            choice = prompt_user(
                f"Binary conflict in {conflict.file_path}",
                options=["keep local", "use remote", "skip"]
            )
            # Apply choice...
        else:
            # Text conflicts: offer merge tool or manual edit
            if conflict.conflict_type == "deletion":
                choice = prompt_user(
                    f"Deletion conflict: {conflict.file_path}",
                    details=f"Local: {'deleted' if not conflict.local_content else 'modified'}, "
                            f"Remote: {'deleted' if not conflict.remote_content else 'modified'}",
                    options=["keep local", "use remote", "manual"]
                )
            else:
                # Content conflict: show diff and offer resolution
                show_diff(conflict.base_content, conflict.local_content, conflict.remote_content)
                choice = prompt_user(
                    f"Content conflict: {conflict.file_path}",
                    options=["keep local", "use remote", "merge tool", "edit manually"]
                )
```

### Pattern 3: Conflict Markers for Later Resolution

For text files, MergeEngine generates Git-style conflict markers:

```
<<<<<<< LOCAL (current)
local changes here
=======
remote changes here
>>>>>>> REMOTE (incoming)
```

**Usage:**
```python
merge_engine = MergeEngine()
result = merge_engine.merge(base_path, local_path, remote_path, output_path)

for conflict in result.conflicts:
    if not conflict.is_binary:
        # Conflict markers written to output_path / conflict.file_path
        conflict_file = output_path / conflict.file_path
        print(f"Review and resolve: {conflict_file}")
```

## Integration Guide for Phase 3 Sync

### Recommended Sync Workflow

```python
from pathlib import Path
from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.merge_engine import MergeEngine

def sync_artifact(
    base_version: Path,      # Collection snapshot (common ancestor)
    local_artifact: Path,    # .claude deployment
    remote_version: Path,    # Latest collection version
    dry_run: bool = False
) -> tuple[bool, str]:
    """Sync an artifact from collection to deployment.

    Returns:
        (success: bool, message: str)
    """
    # Step 1: Perform three-way diff
    diff_engine = DiffEngine()
    diff_result = diff_engine.three_way_diff(
        base_version, local_artifact, remote_version
    )

    # Step 2: Check if can auto-sync
    if diff_result.can_auto_merge:
        if dry_run:
            return (True, f"Can auto-sync {len(diff_result.auto_mergeable)} files")

        # Step 3: Perform merge
        merge_engine = MergeEngine()
        merge_result = merge_engine.merge(
            base_version, local_artifact, remote_version,
            output_path=local_artifact.parent / f"{local_artifact.name}.synced"
        )

        if merge_result.success:
            # Replace local with synced version
            shutil.rmtree(local_artifact)
            shutil.move(merge_result.output_path, local_artifact)
            return (True, f"Synced {len(merge_result.auto_merged)} files")

    # Step 4: Handle conflicts
    else:
        conflicts_summary = []
        for conflict in diff_result.conflicts:
            conflicts_summary.append(
                f"  - {conflict.file_path}: {conflict.conflict_type}"
            )

        message = f"Conflicts detected:\n" + "\n".join(conflicts_summary)
        message += "\n\nRun with --interactive to resolve conflicts"

        return (False, message)
```

### Snapshot Management for Three-Way Diff

Phase 3 will need to track "base" versions for three-way diff. Recommended approach:

**Option 1: Snapshot on Deployment**
```python
# When deploying from collection to .claude/
def deploy_artifact(collection_artifact: Path, deployment_path: Path):
    # Deploy artifact
    shutil.copytree(collection_artifact, deployment_path)

    # Save snapshot for future sync
    snapshot_path = get_snapshot_path(deployment_path)
    shutil.copytree(collection_artifact, snapshot_path)

    # Record snapshot metadata
    save_snapshot_metadata(deployment_path, {
        "snapshot_path": str(snapshot_path),
        "source_version": get_artifact_version(collection_artifact),
        "deployed_at": datetime.now().isoformat()
    })
```

**Option 2: Use Collection Version Tracking**
```python
# Track which collection version was last synced
def get_base_version(artifact_name: str) -> Path:
    """Get the base version for three-way diff."""
    metadata = load_deployment_metadata(artifact_name)
    last_synced_version = metadata.get("last_synced_version")
    return collection_path / artifact_name / last_synced_version
```

### Detecting Local Modifications

```python
def has_local_modifications(
    deployed_artifact: Path,
    snapshot: Path
) -> bool:
    """Check if deployed artifact has been modified locally."""
    diff_engine = DiffEngine()
    result = diff_engine.diff_directories(snapshot, deployed_artifact)
    return result.has_changes
```

### Upstream Change Detection

```python
def has_upstream_changes(
    snapshot: Path,
    latest_collection_version: Path
) -> bool:
    """Check if collection has newer version."""
    diff_engine = DiffEngine()
    result = diff_engine.diff_directories(snapshot, latest_collection_version)
    return result.has_changes
```

## Performance Characteristics

**Benchmarks** (from test suite):

| Operation | Files | Time | Rate |
|-----------|-------|------|------|
| diff_files() | 1 | <10ms | - |
| diff_directories() | 100 | <50ms | 2000/s |
| three_way_diff() | 500 | ~2.3s | 218/s |
| merge() | 500 | ~2.3s | 218/s |

**Optimization Strategies:**

1. **Hash-based comparison**: Files with same size are compared via SHA-256 hash before content diff
2. **Lazy diff generation**: Unified diffs only generated when needed
3. **Ignore patterns**: Default patterns skip unnecessary files
4. **Parallel processing**: Future optimization opportunity (currently sequential)

**Performance Considerations for Phase 3:**

- Large artifacts (>500 files): Consider progress indicators
- Binary files: Fast comparison (hash-based), no diff generation
- Network operations: Diff/merge is local filesystem only
- Memory usage: Files read into memory for diff; consider streaming for very large files (>100MB)

## Known Limitations

### 1. Line-Level Merging Only

The current implementation performs file-level merging, not line-level or semantic merging.

**Impact:**
- If both local and remote modify different lines in the same file, it's marked as a conflict
- True line-level merging (like Git) would detect non-overlapping changes

**Workaround for Phase 3:**
- Use conflict markers for text files
- User can manually resolve or use external merge tool

**Future Enhancement:**
Consider implementing true line-level merging similar to Git's merge algorithm.

### 2. Binary File Conflicts

Binary files with conflicts cannot be automatically resolved.

**Impact:**
- Any modification to the same binary file in both local and remote creates conflict
- No automatic resolution possible

**Recommendation for Phase 3:**
- Prompt user to choose: keep local, use remote, or cancel
- Consider hash-based detection: if hashes match, it's the same change

### 3. Symlinks Not Fully Tested

Symbolic links handling has not been extensively tested.

**Impact:**
- May not correctly handle symlinks in all scenarios
- Could treat symlink as regular file

**Recommendation for Phase 3:**
- Add explicit symlink tests if needed
- Consider whether symlinks should be allowed in artifacts

### 4. Large File Performance

Files >100MB are read into memory, which could cause performance issues.

**Impact:**
- Memory usage scales with file size
- Very large binary files (>1GB) may cause slowdowns

**Recommendation for Phase 3:**
- Add size warnings for large files
- Consider streaming comparison for very large files

### 5. No Semantic Conflict Detection

Conflicts are detected at content level, not semantic level.

**Example:**
```python
# Local change:
def hello(name):
    print(f"Hello {name}")

# Remote change:
def hello(person):
    print(f"Hello {person}")
```

This would be marked as a conflict even though the changes are semantically equivalent (just parameter rename).

**Impact:**
- Some "false positive" conflicts that could theoretically auto-merge

**Recommendation:**
- Accept this limitation for Phase 3
- Consider semantic diff as future enhancement for specific file types (e.g., Python, JSON)

## Testing Fixtures Available

Phase 1 has created 40+ reusable test fixtures in `tests/fixtures/phase2/diff/`:

### Useful Fixtures for Phase 3

**Conflict Scenarios** (`conflict_scenarios/`):
- `content_conflict.md`: Both versions modified same file differently
- `deletion_conflict.txt`: One deleted, one modified
- `add_add_conflict.py`: Same file added with different content
- `both_modified.json`: Complex multi-field conflict

**Auto-Merge Scenarios** (`auto_merge_scenarios/`):
- `local_only_changed.txt`: Only local modified
- `remote_only_changed.py`: Only remote modified
- `both_identical.md`: Both made same changes
- `deleted_both.txt`: Both deleted same file
- `unchanged.cfg`: No changes in any version

**Edge Cases** (`edge_cases/`):
- `nested/`: Deeply nested directory structure
- `whitespace_variations.txt`: Various whitespace patterns
- `long_lines.txt`: Lines >200 chars
- `encoding_test.txt`: Unicode and special characters

See `/home/user/skillmeat/tests/fixtures/phase2/diff/README.md` for complete documentation.

## API Stability

**Stable APIs** (safe to use in Phase 3):
- `DiffEngine.three_way_diff()` - Core sync detection API
- `MergeEngine.merge()` - Core merge API
- `ConflictMetadata` - Conflict representation
- `ThreeWayDiffResult` - Diff result structure
- `MergeResult` - Merge result structure

**Internal APIs** (may change):
- `DiffEngine._analyze_three_way_file()` - Internal helper
- `DiffEngine._should_ignore()` - Internal pattern matching
- `MergeEngine._generate_conflict_markers()` - Internal marker generation

**Recommended Usage:**
- Use only public methods (no underscore prefix)
- Don't rely on internal implementation details
- Check result objects using documented properties

## Error Handling

All Phase 1 APIs raise standard Python exceptions:

```python
# FileNotFoundError
try:
    result = engine.three_way_diff(base, local, remote)
except FileNotFoundError as e:
    print(f"Path not found: {e}")

# NotADirectoryError
try:
    result = engine.diff_directories(path1, path2)
except NotADirectoryError as e:
    print(f"Expected directory: {e}")
```

**Recommendation for Phase 3:**
- Wrap Phase 1 calls in try/except
- Validate paths before calling diff/merge APIs
- Present user-friendly error messages

## Example: Complete Sync Implementation

```python
from pathlib import Path
from typing import Optional
from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.merge_engine import MergeEngine

class ArtifactSync:
    """Handles artifact synchronization from collection to deployment."""

    def __init__(self):
        self.diff_engine = DiffEngine()
        self.merge_engine = MergeEngine()

    def sync(
        self,
        artifact_name: str,
        collection_path: Path,
        deployment_path: Path,
        snapshot_path: Path,
        interactive: bool = False,
        dry_run: bool = False
    ) -> dict:
        """Sync artifact from collection to deployment.

        Args:
            artifact_name: Name of artifact to sync
            collection_path: Path to collection artifact (latest version)
            deployment_path: Path to deployed artifact (.claude/)
            snapshot_path: Path to snapshot (base version for three-way)
            interactive: If True, prompt for conflict resolution
            dry_run: If True, don't apply changes

        Returns:
            dict with sync result:
                - success: bool
                - message: str
                - conflicts: List[ConflictMetadata]
                - auto_merged: List[str]
        """
        # Validate paths
        for path, name in [
            (collection_path, "collection"),
            (deployment_path, "deployment"),
            (snapshot_path, "snapshot")
        ]:
            if not path.exists():
                return {
                    "success": False,
                    "message": f"{name} path not found: {path}",
                    "conflicts": [],
                    "auto_merged": []
                }

        # Perform three-way diff
        try:
            diff_result = self.diff_engine.three_way_diff(
                snapshot_path,      # base (common ancestor)
                deployment_path,    # local (deployed version)
                collection_path     # remote (latest collection version)
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"Diff failed: {e}",
                "conflicts": [],
                "auto_merged": []
            }

        # Check for changes
        if not diff_result.has_conflicts and not diff_result.auto_mergeable:
            return {
                "success": True,
                "message": "Already up to date",
                "conflicts": [],
                "auto_merged": []
            }

        # Handle conflicts
        if diff_result.has_conflicts:
            if not interactive:
                return {
                    "success": False,
                    "message": f"Conflicts detected: {len(diff_result.conflicts)} files. "
                               f"Run with --interactive to resolve.",
                    "conflicts": diff_result.conflicts,
                    "auto_merged": diff_result.auto_mergeable
                }
            else:
                # Interactive conflict resolution
                resolved_conflicts = self._resolve_conflicts_interactively(
                    diff_result.conflicts,
                    snapshot_path,
                    deployment_path,
                    collection_path
                )

                if not resolved_conflicts:
                    return {
                        "success": False,
                        "message": "Conflict resolution cancelled",
                        "conflicts": diff_result.conflicts,
                        "auto_merged": []
                    }

        # Perform merge
        if dry_run:
            return {
                "success": True,
                "message": f"Dry run: would merge {len(diff_result.auto_mergeable)} files",
                "conflicts": diff_result.conflicts if diff_result.has_conflicts else [],
                "auto_merged": diff_result.auto_mergeable
            }

        # Create temporary merge output
        merge_output = deployment_path.parent / f".{artifact_name}.sync.tmp"

        try:
            merge_result = self.merge_engine.merge(
                snapshot_path,
                deployment_path,
                collection_path,
                merge_output
            )

            if merge_result.success or interactive:
                # Replace deployment with merged version
                import shutil
                shutil.rmtree(deployment_path)
                shutil.move(merge_output, deployment_path)

                # Update snapshot to new collection version
                shutil.rmtree(snapshot_path)
                shutil.copytree(collection_path, snapshot_path)

                return {
                    "success": True,
                    "message": f"Synced {len(merge_result.auto_merged)} files",
                    "conflicts": merge_result.conflicts if merge_result.conflicts else [],
                    "auto_merged": merge_result.auto_merged
                }
            else:
                # Cleanup
                shutil.rmtree(merge_output)

                return {
                    "success": False,
                    "message": f"Merge failed: {len(merge_result.conflicts)} conflicts",
                    "conflicts": merge_result.conflicts,
                    "auto_merged": []
                }

        except Exception as e:
            # Cleanup on error
            if merge_output.exists():
                import shutil
                shutil.rmtree(merge_output)

            return {
                "success": False,
                "message": f"Merge failed: {e}",
                "conflicts": [],
                "auto_merged": []
            }

    def _resolve_conflicts_interactively(
        self,
        conflicts: list,
        base_path: Path,
        local_path: Path,
        remote_path: Path
    ) -> bool:
        """Interactively resolve conflicts.

        Returns:
            True if all conflicts resolved, False if cancelled
        """
        # Implementation would prompt user for each conflict
        # This is a placeholder for Phase 3 implementation
        pass
```

## Recommendations for Phase 3

### 1. Snapshot Strategy

Implement one of these snapshot strategies:

**Option A: Snapshot on Deploy**
- Save copy of collection artifact when deploying
- Store in `.skillmeat/snapshots/{artifact_name}/`
- Metadata tracks source version

**Option B: Version-Based Snapshots**
- Track collection version in deployment metadata
- Use collection version history as snapshot
- Requires collection to preserve versions

**Recommendation**: Option A is simpler and more reliable.

### 2. Conflict Resolution UI

Implement interactive conflict resolution:

1. **List conflicts**: Show all conflicting files with conflict types
2. **For each conflict**:
   - Binary: Offer "keep local", "use remote", "skip"
   - Text deletion: Offer "keep local", "use remote", "view diff"
   - Text content: Offer "keep local", "use remote", "merge tool", "edit"
3. **Preview changes**: Show what will change before applying
4. **Apply/Cancel**: Allow user to apply or cancel sync

### 3. Sync Modes

Consider implementing multiple sync modes:

- **Auto-sync**: Only sync if no conflicts (safe)
- **Force-remote**: Always use remote (override local)
- **Force-local**: Keep local, ignore remote
- **Interactive**: Prompt for conflict resolution
- **Dry-run**: Preview what would change

### 4. Progress Indicators

For large artifacts (>100 files):

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Syncing...", total=len(files))
    for file in files:
        # Sync file
        progress.update(task, advance=1)
```

### 5. Logging and Audit Trail

Log all sync operations:

```python
import logging

logger = logging.getLogger("skillmeat.sync")

logger.info(f"Sync started: {artifact_name}")
logger.info(f"Auto-merged: {len(auto_merged)} files")
logger.warning(f"Conflicts: {len(conflicts)} files")
logger.info(f"Sync completed: {success}")
```

## Questions for Phase 3 Team

1. **Snapshot Storage**: Where should snapshots be stored? `.skillmeat/snapshots/`?
2. **Conflict UI**: CLI-based prompts or web UI for conflict resolution?
3. **Default Behavior**: What should happen if sync has conflicts and not in interactive mode?
4. **Version Tracking**: How to track which collection version was last synced?
5. **Rollback**: Should we support rolling back a sync if user is unhappy?
6. **Partial Sync**: Should we support syncing only specific files in an artifact?

## Contact and Support

**Phase 1 Artifacts:**
- Source: `skillmeat/core/diff_engine.py`, `skillmeat/core/merge_engine.py`
- Tests: `tests/test_diff_basic.py`, `tests/test_three_way_diff.py`, `tests/test_merge_engine.py`, `tests/test_cli_diff.py`
- Fixtures: `tests/fixtures/phase2/diff/`
- Models: `skillmeat/models.py` (FileDiff, DiffResult, ConflictMetadata, ThreeWayDiffResult, MergeResult)

**Documentation:**
- Fixture README: `/home/user/skillmeat/tests/fixtures/phase2/diff/README.md`
- Quality Gates: 8/8 passed (see quality gates check)
- Test Coverage: 87% (exceeds 75% requirement)

**Status**: Phase 1 is complete and ready for Phase 3 integration. All APIs are stable and well-tested.

---

**Prepared by**: Phase 1 Intelligence Execution Team
**Date**: 2025-11-15
**Next Phase**: Phase 3 (Sync) - Ready to begin
