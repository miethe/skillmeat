# P1-003 MergeEngine Core - Handoff from P1-002

**From**: backend-architect (P1-002 - Three-Way Diff Architecture Review)
**To**: backend-architect (P1-003 - MergeEngine Core)
**Date**: 2025-11-15
**Status**: P1-002 COMPLETE → P1-003 READY

---

## Executive Summary

P1-002 (Three-Way Diff) is COMPLETE and PRODUCTION READY. The DiffEngine provides a robust foundation for P1-003 (MergeEngine Core).

**Key Insight**: MergeEngine already exists and has basic functionality integrated in Phase 0. P1-003 should focus on ENHANCEMENT rather than creation from scratch.

---

## What P1-002 Delivers to P1-003

### 1. Three-Way Diff API

**Available Method**:
```python
from skillmeat.core.diff_engine import DiffEngine

engine = DiffEngine()
result = engine.three_way_diff(
    base_path=Path("/path/to/base"),
    local_path=Path("/path/to/local"),
    remote_path=Path("/path/to/remote"),
    ignore_patterns=["*.pyc", ".git"]  # Optional
)
```

**Returns**: `ThreeWayDiffResult`
- `auto_mergeable: List[str]` - Files that can be auto-merged
- `conflicts: List[ConflictMetadata]` - Files requiring resolution
- `stats: DiffStats` - Statistics about the diff

### 2. Conflict Metadata Structure

**ConflictMetadata** provides everything MergeEngine needs:

```python
@dataclass
class ConflictMetadata:
    file_path: str                    # Relative path to file
    conflict_type: Literal[           # Type of conflict
        "content",                    #   - Content differs
        "deletion",                   #   - Deleted in one version
        "both_modified",              #   - Modified in both
        "add_add"                     #   - Added in both
    ]
    base_content: Optional[str]       # Base version content (or None)
    local_content: Optional[str]      # Local version content (or None)
    remote_content: Optional[str]     # Remote version content (or None)
    auto_mergeable: bool              # Can this be auto-merged?
    merge_strategy: Optional[Literal[ # How to merge if auto_mergeable=True
        "use_local",                  #   - Use local version
        "use_remote",                 #   - Use remote version
        "use_base",                   #   - Use base version
        "manual"                      #   - Requires user intervention
    ]]
    is_binary: bool                   # Is this a binary file?
```

### 3. Integration Contract

**Guarantees from DiffEngine**:
1. ✅ All files in `auto_mergeable` have a valid `merge_strategy` (not "manual")
2. ✅ All files in `conflicts` require manual resolution
3. ✅ Binary files are marked with `is_binary=True` and have `content=None`
4. ✅ Text files have content populated (unless deleted)

**What MergeEngine Must Do**:
1. Process `auto_mergeable` files automatically using the provided strategy
2. Handle `conflicts` by either:
   - Generating Git-style conflict markers (for text files)
   - Flagging as unresolvable (for binary files)
3. Return a `MergeResult` with status and statistics

---

## Current MergeEngine State

**File**: `/home/user/skillmeat/skillmeat/core/merge_engine.py`
**Status**: BASIC IMPLEMENTATION EXISTS (created in Phase 0)

### What Already Works

**Existing Method**:
```python
from skillmeat.core.merge_engine import MergeEngine

engine = MergeEngine()
result = engine.merge(
    base_path=Path("base"),
    local_path=Path("local"),
    remote_path=Path("remote"),
    output_path=Path("output")  # Optional
)
```

**Current Capabilities**:
- ✅ Calls `diff_engine.three_way_diff()` to get conflict metadata
- ✅ Processes `auto_mergeable` files using `_auto_merge_file()`
- ✅ Handles text conflicts using `_handle_text_conflict()`
- ✅ Flags binary conflicts as unresolvable
- ✅ Returns `MergeResult` with statistics

**Integration Points** (already working):
- Used in `ArtifactManager._apply_merge_strategy()` (P0-002)
- Integrated into update flow with Phase 0 simplification (base==local)

### What Needs Enhancement (P1-003 Scope)

Based on P1-003 acceptance criteria:

#### AC1: Auto-Merge Simple Cases
**Status**: ✅ PARTIALLY IMPLEMENTED

**Current**:
- Auto-merge exists in `_auto_merge_file()` method
- Executes strategies: `use_local`, `use_remote`, `use_base`

**Needs**:
- ✅ Verify correctness of auto-merge logic
- ⚠️ Add error handling for file copy failures
- ⚠️ Add logging for merge decisions
- ✅ Test coverage for all auto-merge scenarios

#### AC2: Conflict Detection
**Status**: ✅ COMPLETE (handled by DiffEngine)

**Current**:
- DiffEngine provides conflict metadata
- MergeEngine consumes it correctly

**Needs**:
- Nothing additional (delegated to DiffEngine)

#### AC3: Conflict Markers (Git-Style)
**Status**: ⚠️ NEEDS REVIEW

**Current**:
- `_handle_text_conflict()` method exists
- Generates conflict markers for text files

**Needs**:
- ✅ Review marker format (should match Git format)
- ✅ Test conflict marker generation
- ⚠️ Add metadata to markers (branch/version info)

**Git-Style Marker Format**:
```
<<<<<<< LOCAL (or HEAD)
local content here
=======
remote content here
>>>>>>> REMOTE (or branch name)
```

**Enhanced Format** (recommended):
```
<<<<<<< LOCAL (artifact_name v1.2.3)
local content here
||||||| BASE (common ancestor v1.2.0)
base content here
=======
remote content here
>>>>>>> REMOTE (artifact_name v1.3.0)
```

---

## P1-003 Scope Definition

### What P1-003 SHOULD Do

Based on architecture review, P1-003 should focus on:

1. **Verification & Testing** (2 pts):
   - Verify existing auto-merge logic is correct
   - Add comprehensive test coverage for MergeEngine
   - Test all conflict types (content, deletion, both_modified, add_add)
   - Test all merge strategies (use_local, use_remote, use_base, manual)

2. **Enhancement & Hardening** (2 pts):
   - Improve conflict marker generation (add metadata)
   - Add error handling for file copy failures
   - Add logging for merge decisions
   - Add rollback capability for partial merges

3. **Documentation** (not in scope - delegate to documentation-writer):
   - API documentation
   - Examples
   - Troubleshooting guide

### What P1-003 Should NOT Do

- ❌ Rewrite existing working code (DRY - Don't Repeat Yourself)
- ❌ Change the three-way diff algorithm (that's P1-002's responsibility)
- ❌ Implement line-level merging (future enhancement, not MVP)
- ❌ Add interactive merge conflict resolution (that's CLI's job in P1-004 or P3-004)

---

## Integration Architecture

### Data Flow: DiffEngine → MergeEngine

```
┌─────────────────────────────────────────────────────────────┐
│                    MergeEngine.merge()                      │
│                                                             │
│  INPUT:                                                     │
│  ├─ base_path: Path                                         │
│  ├─ local_path: Path                                        │
│  ├─ remote_path: Path                                       │
│  └─ output_path: Optional[Path]                             │
│                                                             │
│  STEP 1: Get Diff Analysis                                 │
│  ├─ diff_result = diff_engine.three_way_diff(...)          │
│  └─ Result: ThreeWayDiffResult                             │
│     ├─ auto_mergeable: List[str]                            │
│     └─ conflicts: List[ConflictMetadata]                    │
│                                                             │
│  STEP 2: Process Auto-Mergeable Files                      │
│  ├─ For each file in auto_mergeable:                        │
│  │   ├─ Get metadata via _analyze_three_way_file()         │
│  │   ├─ Execute strategy:                                  │
│  │   │   ├─ use_local → copy local to output               │
│  │   │   ├─ use_remote → copy remote to output             │
│  │   │   └─ use_base → copy base to output                 │
│  │   └─ Record in result.auto_merged                       │
│  └─ Error handling: rollback on failure                    │
│                                                             │
│  STEP 3: Process Conflicts                                 │
│  ├─ For each conflict in conflicts:                         │
│  │   ├─ If binary:                                         │
│  │   │   └─ Flag as unresolvable                           │
│  │   └─ If text:                                           │
│  │       ├─ Generate conflict markers                      │
│  │       ├─ Write to output_path                           │
│  │       └─ Record in result.conflicts                     │
│  └─ Binary conflicts: cannot auto-merge                    │
│                                                             │
│  STEP 4: Return Result                                     │
│  └─ MergeResult:                                           │
│     ├─ success: bool (no conflicts)                         │
│     ├─ auto_merged: List[str]                              │
│     ├─ conflicts: List[ConflictMetadata]                   │
│     ├─ output_path: Optional[Path]                         │
│     └─ stats: MergeStats                                   │
└─────────────────────────────────────────────────────────────┘
```

### Error Handling Strategy

**Failure Points**:
1. **Path Validation**: FileNotFoundError, NotADirectoryError
   - Handled by: DiffEngine (propagated to MergeEngine)
   - Action: Fail fast with clear error message

2. **File Copy Failures**: PermissionError, OSError, IOError
   - Handled by: MergeEngine (needs enhancement)
   - Action: Rollback partial merge, return error in MergeResult

3. **Output Directory Creation**: PermissionError
   - Handled by: MergeEngine (`output_path.mkdir(parents=True, exist_ok=True)`)
   - Action: Fail with clear error message

**Recommended Error Handling Pattern**:
```python
def merge(self, base_path, local_path, remote_path, output_path):
    # Step 1: Validate (let DiffEngine handle)
    diff_result = self.diff_engine.three_way_diff(...)

    # Step 2: Create output directory
    try:
        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        return MergeResult(success=False, error=f"Cannot create output: {e}")

    # Step 3: Process files (wrap in try/except)
    for file_path in diff_result.auto_mergeable:
        try:
            # Auto-merge logic
        except (IOError, PermissionError) as e:
            # Log error
            # Rollback partial changes
            return MergeResult(success=False, error=f"Merge failed: {e}")

    # Step 4: Return success
    return MergeResult(success=True, ...)
```

---

## Test Coverage Requirements

### P1-003 Must Test

**Auto-Merge Scenarios** (use_local, use_remote, use_base):
- ✅ Remote changed, local unchanged → use_remote
- ✅ Local changed, remote unchanged → use_local
- ✅ Both changed identically → use_local (or use_remote)
- ✅ File deleted in both → use_local (deletion)
- ✅ File added only locally → use_local
- ✅ File added only remotely → use_remote

**Conflict Scenarios** (manual resolution):
- ✅ Both modified differently → conflict markers
- ✅ Deleted locally, modified remotely → conflict markers
- ✅ Modified locally, deleted remotely → conflict markers
- ✅ Added in both with different content → conflict markers
- ✅ Binary conflict → flag as unresolvable

**Edge Cases**:
- ✅ Empty files
- ✅ Empty directories
- ✅ Nested directories
- ✅ Ignore patterns respected
- ⚠️ File copy failure (needs enhancement)
- ⚠️ Permission errors (needs enhancement)
- ⚠️ Output path creation failure (needs enhancement)

**Performance**:
- ✅ Merge 100 files in <2s
- ⚠️ Merge 500 files in <5s (needs benchmark)

---

## Recommended Test Structure

### Test File: `tests/test_merge_engine.py`

**Test Classes**:

```python
class TestMergeEngineAutoMerge:
    """Test auto-merge scenarios with all strategies."""

    def test_use_remote_strategy(self, tmp_path):
        """Test merging when only remote changed."""

    def test_use_local_strategy(self, tmp_path):
        """Test merging when only local changed."""

    def test_use_base_strategy(self, tmp_path):
        """Test merging when reverting to base."""

    def test_both_changed_identically(self, tmp_path):
        """Test merging when both made same change."""


class TestMergeEngineConflicts:
    """Test conflict detection and marker generation."""

    def test_both_modified_conflict(self, tmp_path):
        """Test conflict markers for divergent changes."""

    def test_deletion_conflict_local(self, tmp_path):
        """Test conflict when deleted locally, modified remotely."""

    def test_deletion_conflict_remote(self, tmp_path):
        """Test conflict when deleted remotely, modified locally."""

    def test_add_add_conflict(self, tmp_path):
        """Test conflict when same file added differently."""

    def test_binary_conflict(self, tmp_path):
        """Test binary file conflict handling."""


class TestMergeEngineMarkerGeneration:
    """Test Git-style conflict marker format."""

    def test_basic_conflict_markers(self, tmp_path):
        """Test standard <<<<<<< ======= >>>>>>> format."""

    def test_marker_metadata(self, tmp_path):
        """Test markers include version/branch info."""

    def test_marker_line_endings(self, tmp_path):
        """Test markers work with different line endings."""


class TestMergeEngineErrorHandling:
    """Test error handling and rollback."""

    def test_output_path_creation_failure(self, tmp_path):
        """Test handling when output directory cannot be created."""

    def test_file_copy_permission_error(self, tmp_path):
        """Test handling when file copy fails due to permissions."""

    def test_partial_merge_rollback(self, tmp_path):
        """Test rollback when merge fails partway through."""


class TestMergeEngineIntegration:
    """Test integration with DiffEngine and real-world scenarios."""

    def test_complex_directory_merge(self, tmp_path):
        """Test merging complex nested directory structures."""

    def test_mixed_conflicts_and_auto_merge(self, tmp_path):
        """Test scenario with both auto-mergeable and conflicted files."""

    def test_ignore_patterns_respected(self, tmp_path):
        """Test that merge respects ignore patterns from diff."""


class TestMergeEnginePerformance:
    """Performance benchmarks for merge operations."""

    def test_merge_100_files(self, tmp_path):
        """Test merging 100 files completes in <2s."""

    def test_merge_500_files(self, tmp_path):
        """Test merging 500 files completes in <5s."""
```

**Fixture Reuse**:
- Reuse fixtures from `tests/fixtures/phase2/diff/auto_merge_scenarios/`
- Add new fixtures for conflict marker validation

---

## Known Issues from Phase 0

### Issue 1: Base == Local Simplification

**Current State** (Phase 0):
```python
# In ArtifactManager._apply_merge_strategy()
merge_result = merge_engine.merge(
    base_path=local_artifact_path,  # ⚠️ Uses current as base
    local_path=local_artifact_path,
    remote_path=temp_workspace
)
```

**Problem**: This doesn't allow for proper three-way merge because base and local are the same.

**Phase 1 Fix**: Use snapshot-based base tracking
```python
# Get snapshot of base version
base_snapshot = self._get_base_snapshot(artifact_name)
base_workspace = base_snapshot.extract_to_temp()

merge_result = merge_engine.merge(
    base_path=base_workspace,        # ✅ Proper historical base
    local_path=local_artifact_path,
    remote_path=temp_workspace
)
```

**Impact on P1-003**: MergeEngine doesn't need to change - this is a caller responsibility (ArtifactManager).

### Issue 2: No Rollback on Partial Merge

**Current State**: If merge fails after copying some files, no cleanup occurs.

**Phase 1 Fix**: Add rollback capability
```python
def merge(self, ...):
    # Track copied files
    copied_files = []

    try:
        for file in auto_mergeable:
            # Copy file
            copied_files.append(file)
    except Exception as e:
        # Rollback: delete all copied files
        for file in copied_files:
            try:
                (output_path / file).unlink()
            except:
                pass
        raise
```

**Impact on P1-003**: This is within MergeEngine's scope and should be added.

---

## Acceptance Criteria Checklist for P1-003

From implementation plan:

- [ ] **AC1**: `merge()` merges simple cases automatically
  - Status: Partially implemented, needs verification

- [ ] **AC2**: Conflict files use Git-style markers
  - Status: Implemented, needs format verification

- [ ] **AC3**: Binary conflicts flagged (not merged)
  - Status: Implemented, needs testing

- [ ] **AC4**: Returns MergeResult with statistics
  - Status: Implemented, complete

- [ ] **AC5**: Respects ignore patterns from DiffEngine
  - Status: Implemented (DiffEngine handles), needs verification

- [ ] **AC6**: Test coverage ≥75%
  - Status: Not yet measured, needs test suite

---

## Recommendations for P1-003

### High Priority (Must Do)

1. **Add Error Handling**:
   - Wrap file copy operations in try/except
   - Implement rollback for partial merges
   - Add clear error messages

2. **Verify Conflict Markers**:
   - Review `_handle_text_conflict()` implementation
   - Ensure Git-compatible format
   - Add version/branch metadata

3. **Comprehensive Testing**:
   - Create test_merge_engine.py with 5 test classes
   - Achieve ≥75% coverage target
   - Test all auto-merge and conflict scenarios

4. **Integration Testing**:
   - Test end-to-end diff → merge flow
   - Verify MergeEngine works with DiffEngine output
   - Test with real-world artifact structures

### Medium Priority (Should Do)

1. **Add Logging**:
   - Log merge decisions (use_local, use_remote, etc.)
   - Log conflict detection
   - Log file operations

2. **Performance Benchmarks**:
   - Measure merge time for 100 files
   - Measure merge time for 500 files
   - Compare against PRD targets

3. **Improve Conflict Markers**:
   - Add BASE section (`||||||| BASE`)
   - Include artifact name and version
   - Add timestamp

### Low Priority (Nice to Have)

1. **Smart Merge Strategies**:
   - Detect common patterns (e.g., imports added to same file)
   - Suggest merge strategy based on file type
   - Add heuristics for auto-resolution

2. **Diff Visualization**:
   - Add side-by-side diff display option
   - Highlight changes in conflict markers
   - Generate HTML diff report

---

## Files to Review

**Core Implementation**:
- `/home/user/skillmeat/skillmeat/core/merge_engine.py` (review and enhance)
- `/home/user/skillmeat/skillmeat/core/diff_engine.py` (reference only, do not modify)
- `/home/user/skillmeat/skillmeat/models.py` (MergeResult, MergeStats)

**Integration Points**:
- `/home/user/skillmeat/skillmeat/core/artifact.py` (_apply_merge_strategy method)

**Tests to Create**:
- `/home/user/skillmeat/tests/test_merge_engine.py` (new file)

**Fixtures to Reuse**:
- `/home/user/skillmeat/tests/fixtures/phase2/diff/auto_merge_scenarios/`

---

## Success Criteria

P1-003 is COMPLETE when:

1. ✅ All auto-merge scenarios tested and passing
2. ✅ All conflict scenarios tested and passing
3. ✅ Conflict markers validated (Git-compatible format)
4. ✅ Error handling added for file operations
5. ✅ Rollback capability implemented for partial merges
6. ✅ Test coverage ≥75% for merge_engine.py
7. ✅ Integration with DiffEngine verified end-to-end
8. ✅ Performance benchmarks pass (<2s for 100 files)

---

## Questions for P1-003 Owner

1. Should we add line-level merging (like Git's smart merge) or stick with file-level?
   - Recommendation: Stick with file-level for MVP, add line-level in Phase 2+

2. Should conflict markers include BASE section or just LOCAL/REMOTE?
   - Recommendation: Include BASE for 3-way context (more informative)

3. Should we implement interactive conflict resolution in MergeEngine or CLI?
   - Recommendation: CLI's responsibility (P1-004 or P3-004), MergeEngine just generates markers

4. What rollback strategy should we use for partial merges?
   - Recommendation: Delete copied files, leave output_path in pre-merge state

---

**Handoff Complete**: 2025-11-15
**From**: backend-architect (P1-002)
**Status**: Ready for P1-003 execution
