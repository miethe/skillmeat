---
type: progress
prd: "versioning-merge-system"
phase: 5
title: "Service Layer - Three-Way Merge Engine"
status: "planning"
started: "2025-12-03"
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 11
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["backend-architect"]
contributors: ["python-backend-engineer"]

tasks:
  - id: "MERGE-001"
    description: "Implement three_way_merge(base, ours, theirs) algorithm"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["REPO-006"]
    estimated_effort: "8h"
    priority: "high"

  - id: "MERGE-002"
    description: "Implement file_changed(base, new) helper"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "2h"
    priority: "high"

  - id: "MERGE-003"
    description: "Implement line-level merge for text files"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "5h"
    priority: "high"

  - id: "MERGE-004"
    description: "Implement conflict marker generation (<<<<<<< ours, =======, >>>>>>> theirs)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-003"]
    estimated_effort: "2h"
    priority: "high"

  - id: "MERGE-005"
    description: "Implement three_way_diff for visualization"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "5h"
    priority: "high"

  - id: "MERGE-006"
    description: "Implement classify_change (upstream_only, local_only, conflict, unchanged)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-002"]
    estimated_effort: "3h"
    priority: "high"

  - id: "MERGE-007"
    description: "Implement preview_merge without applying"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "3h"
    priority: "high"

  - id: "MERGE-008"
    description: "Implement apply_merge with atomic writes"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "3h"
    priority: "high"

  - id: "MERGE-009"
    description: "Create test data sets with 50+ merge scenarios"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "5h"
    priority: "high"

  - id: "MERGE-010"
    description: "Implement binary file merge handling"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "2h"
    priority: "medium"

  - id: "MERGE-011"
    description: "Implement merge_stats calculation"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001"]
    estimated_effort: "2h"
    priority: "medium"

parallelization:
  batch_1: ["MERGE-001"]
  batch_2: ["MERGE-002", "MERGE-003", "MERGE-005", "MERGE-007", "MERGE-008", "MERGE-010", "MERGE-011"]
  batch_3: ["MERGE-004", "MERGE-006", "MERGE-009"]
  critical_path: ["MERGE-001", "MERGE-003", "MERGE-004"]
  estimated_total_time: "4-5d"

blockers:
  - id: "BLOCK-1"
    description: "Depends on REPO-006 (VersionRepository complete) from Phase 3"
    status: "pending"
    resolution: "Can run parallel with Phase 4 if Phase 3 dependencies available"

success_criteria:
  - id: "SC-1"
    description: "Three-way merge algorithm handles all cases (no conflicts, local-only, upstream-only, divergent changes)"
    status: "pending"
  - id: "SC-2"
    description: "Line-level merge works for text files with proper diff computation"
    status: "pending"
  - id: "SC-3"
    description: "Conflict markers clearly formatted with ours/base/theirs markers"
    status: "pending"
  - id: "SC-4"
    description: "Three-way diff produces correct output for visualization"
    status: "pending"
  - id: "SC-5"
    description: "Merge preview accurate without modifying files"
    status: "pending"
  - id: "SC-6"
    description: "Binary files handled gracefully with ours/theirs selection"
    status: "pending"
  - id: "SC-7"
    description: "Atomic merge application (no partial writes on interruption)"
    status: "pending"
  - id: "SC-8"
    description: "Unit tests with 50+ scenarios achieve >90% coverage"
    status: "pending"
  - id: "SC-9"
    description: "Performance: 10MB artifact merge completes in <2 seconds"
    status: "pending"
---

# versioning-merge-system - Phase 5: Service Layer - Three-Way Merge Engine

**Phase**: 5 of 10
**Status**: ⏳ Planning (0% complete)
**Duration**: Estimated 4-5 days
**Owner**: backend-architect
**Contributors**: python-backend-engineer

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Core Algorithm - No Parallelization):
- MERGE-001 → `backend-architect` (8h) - Three-way merge algorithm - **Blocks all other tasks**

**Batch 2** (Parallel - Depends on Batch 1):
- MERGE-002 → `backend-architect` (2h) - file_changed() helper
- MERGE-003 → `backend-architect` (5h) - Line-level merge for text files - **Critical path**
- MERGE-005 → `backend-architect` (5h) - Three-way diff for visualization
- MERGE-007 → `backend-architect` (3h) - Preview merge without applying
- MERGE-008 → `backend-architect` (3h) - Apply merge with atomic writes
- MERGE-010 → `backend-architect` (2h) - Binary file merge handling
- MERGE-011 → `backend-architect` (2h) - Merge stats calculation

**Batch 3** (Final Polish - Depends on Batch 2):
- MERGE-004 → `backend-architect` (2h) - Conflict marker generation - **Blocked by**: MERGE-003
- MERGE-006 → `backend-architect` (3h) - Classify change types
- MERGE-009 → `backend-architect` (5h) - Test data sets with 50+ scenarios

**Critical Path**: MERGE-001 → MERGE-003 → MERGE-004 (15h total)

### Task Delegation Commands

```
# Batch 1 (Launch first)
Task("backend-architect", "MERGE-001: Implement three_way_merge(base, ours, theirs) algorithm. Handle: no conflicts, local-only changes, upstream-only changes, divergent changes (conflicts). Return merged artifact dict or conflict markers. File: core/merge/merge_engine.py")

# Batch 2 (After MERGE-001 completes - launch all in parallel)
Task("backend-architect", "MERGE-002: Implement file_changed(base, new) helper. Returns True if file changed between base and new versions. Used by classification logic.")
Task("backend-architect", "MERGE-003: Implement line-level merge for text files. Uses 3-way diff (base vs ours vs theirs). Handle line insertions, deletions, modifications. Return merged text or conflict markers.")
Task("backend-architect", "MERGE-005: Implement three_way_diff for visualization. Produces diff output showing base -> ours changes and base -> theirs changes side by side.")
Task("backend-architect", "MERGE-007: Implement preview_merge without applying. Returns: what would merge produce, which files have conflicts, merge_stats. Does not modify files.")
Task("backend-architect", "MERGE-008: Implement apply_merge with atomic writes. Apply merge results to artifact directory. Use temp directory + atomic move pattern. Handle interruption gracefully.")
Task("backend-architect", "MERGE-010: Implement binary file merge handling. For binary files: return ours by default, allow user override to select theirs. No conflict markers for binaries.")
Task("backend-architect", "MERGE-011: Implement merge_stats calculation. Returns: files_merged, files_conflicted, lines_added, lines_deleted, merge_type.")

# Batch 3 (After Batch 2 completes)
Task("backend-architect", "MERGE-004: Implement conflict marker generation. Format: <<<<<<< ours [content] ======= [base] >>>>>>> theirs [content]. Markers must be clearly formatted.")
Task("backend-architect", "MERGE-006: Implement classify_change(change_type). Returns: upstream_only, local_only, conflict, or unchanged. Used by merge logic to decide actions.")
Task("backend-architect", "MERGE-009: Create test data sets with 50+ merge scenarios covering: no conflicts, upstream-only, local-only, divergent changes, binary files, edge cases. Generate synthetic artifacts.")
```

---

## Overview

Phase 5 implements the core three-way merge engine that powers the versioning system. This service layer handles merging artifact versions when both upstream and local changes exist, detecting conflicts, generating merge previews, and applying merges atomically.

**Why This Phase**: The three-way merge algorithm is the heart of the versioning system. It must handle all conflict scenarios, be performant for large artifacts, and provide clear feedback on what will be merged. This phase is critical for the sync and conflict resolution features.

**Scope**:
- ✅ **IN SCOPE**: Three-way merge algorithm, line-level text merge, conflict detection, conflict markers, merge preview, atomic apply, binary file handling, test scenarios
- ❌ **OUT OF SCOPE**: User conflict resolution UI (Phase 8), API endpoints (Phase 7), merge strategy policies (Phase 6)

**Dependencies**:
- Requires REPO-006 (VersionRepository) from Phase 3
- Can run parallel with Phase 4 (Repository Extensions)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | Three-way merge algorithm handles all cases (no conflicts, local-only, upstream-only, divergent) | ⏳ Pending |
| SC-2 | Line-level merge works for text files with proper diff computation | ⏳ Pending |
| SC-3 | Conflict markers clearly formatted with ours/base/theirs markers | ⏳ Pending |
| SC-4 | Three-way diff produces correct output for visualization | ⏳ Pending |
| SC-5 | Merge preview accurate without modifying files | ⏳ Pending |
| SC-6 | Binary files handled gracefully with ours/theirs selection | ⏳ Pending |
| SC-7 | Atomic merge application (no partial writes on interruption) | ⏳ Pending |
| SC-8 | Unit tests with 50+ scenarios achieve >90% coverage | ⏳ Pending |
| SC-9 | Performance: 10MB artifact merge completes in <2 seconds | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| MERGE-001 | Three-way merge(base, ours, theirs) | ⏳ | backend-architect | REPO-006 | 8h | Core algorithm, all cases |
| MERGE-002 | file_changed(base, new) helper | ⏳ | backend-architect | MERGE-001 | 2h | Boolean change detection |
| MERGE-003 | Line-level merge for text files | ⏳ | backend-architect | MERGE-001 | 5h | 3-way diff, conflict markers |
| MERGE-004 | Conflict marker generation | ⏳ | backend-architect | MERGE-003 | 2h | <<<<<<< ours, =======, >>>>>>> |
| MERGE-005 | Three-way diff for visualization | ⏳ | backend-architect | MERGE-001 | 5h | Side-by-side diff output |
| MERGE-006 | Classify change (upstream/local/conflict) | ⏳ | backend-architect | MERGE-002 | 3h | Change type classification |
| MERGE-007 | Preview merge without applying | ⏳ | backend-architect | MERGE-001 | 3h | Returns predicted result |
| MERGE-008 | Apply merge with atomic writes | ⏳ | backend-architect | MERGE-001 | 3h | Temp + atomic move pattern |
| MERGE-009 | Test data sets (50+ scenarios) | ⏳ | backend-architect | MERGE-001 | 5h | Comprehensive test coverage |
| MERGE-010 | Binary file merge handling | ⏳ | backend-architect | MERGE-001 | 2h | ours by default, override |
| MERGE-011 | Merge stats calculation | ⏳ | backend-architect | MERGE-001 | 2h | Metrics for merge result |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State (Phase 4 Complete)

By Phase 4, the versioning system has:
- ✅ Storage infrastructure (versioned directories, TOML metadata)
- ✅ VersionRepository with CRUD operations
- ✅ Repository extensions (diff, comparison, lineage tracking)
- ❌ No merge logic - Phase 5 adds this

### Three-Way Merge Algorithm

Three-way merge takes three versions and produces a merged result:

```
base (common ancestor)
  |
  +---> ours (local changes)
  |
  +---> theirs (upstream changes)
  |
  v
merged (result)
```

**Algorithm Logic**:

1. For each file in base ∪ ours ∪ theirs:
   - If only in ours: keep from ours (local creation)
   - If only in theirs: take from theirs (upstream creation)
   - If deleted in ours: delete in result (local deletion)
   - If deleted in theirs: delete in result (upstream deletion)
   - If modified in both (both ours and theirs changed same file):
     - For text files: line-level 3-way merge
     - For binary files: conflict marker or use ours by default
     - If merge produces conflicts: include conflict markers
   - If only one side modified: take that version (non-conflicting change)

**Conflict Detection**:
- Conflict occurs when both ours and theirs modify same file
- Line-level conflicts: when changes touch same lines
- File-level conflicts: when one deletes but other modifies

### Target Architecture

Phase 5 creates:

```python
# core/merge/merge_engine.py
class MergeEngine:
    def three_way_merge(base: dict, ours: dict, theirs: dict) -> dict
    def preview_merge(base: dict, ours: dict, theirs: dict) -> MergePreview
    def apply_merge(artifact_dir: Path, merge_result: dict) -> None

# core/merge/text_merge.py
def line_level_merge(base_lines, ours_lines, theirs_lines) -> list
def detect_line_conflicts(ours_lines, theirs_lines, base_lines) -> list

# core/merge/conflict_markers.py
def generate_conflict_markers(ours_content, base_content, theirs_content) -> str

# core/merge/classification.py
def classify_change(base_file, new_file) -> ChangeType  # upstream_only, local_only, conflict, unchanged
```

### Reference Patterns

**Similar Patterns in SkillMeat**:
- Diff computation in Phase 4 (foundation for merge logic)
- Atomic write pattern in snapshot_manager.py (use for apply_merge)
- File operations in manifest_manager.py (copy, move, delete)

**Merge Algorithm References**:
- Git's three-way merge (handling divergent changes, conflict markers)
- Diff3 algorithm (line-level merge with conflict detection)
- Myers diff algorithm (efficient line-level diffing)

---

## Implementation Details

### Technical Approach

#### 1. Three-Way Merge Algorithm (MERGE-001)

**Core Logic**:
```python
def three_way_merge(base: dict, ours: dict, theirs: dict) -> dict:
    """
    Merge three versions of an artifact.

    Args:
        base: Common ancestor version (file dict)
        ours: Local changes (file dict)
        theirs: Upstream changes (file dict)

    Returns:
        Merged artifact dict or dict with conflict markers
    """
    merged = {}

    # Collect all files from all three versions
    all_files = set(base.keys()) | set(ours.keys()) | set(theirs.keys())

    for file_path in all_files:
        base_content = base.get(file_path)
        ours_content = ours.get(file_path)
        theirs_content = theirs.get(file_path)

        # Decision tree:
        if ours_content is None and theirs_content is None:
            # Deleted in both or never existed - skip
            continue
        elif ours_content is None:
            # Deleted in ours (local delete)
            if theirs_content == base_content:
                # Only ours changed (deletion) - keep deletion
                continue
            else:
                # Conflict: ours deleted but theirs modified
                merged[file_path] = conflict_marker(base_content, None, theirs_content)
        elif theirs_content is None:
            # Deleted in theirs (upstream delete)
            if ours_content == base_content:
                # Only theirs changed (deletion) - apply deletion
                continue
            else:
                # Conflict: theirs deleted but ours modified
                merged[file_path] = conflict_marker(base_content, ours_content, None)
        elif ours_content == theirs_content:
            # Both sides match - take either
            merged[file_path] = ours_content
        elif ours_content == base_content:
            # Only theirs changed - take upstream
            merged[file_path] = theirs_content
        elif theirs_content == base_content:
            # Only ours changed - keep local
            merged[file_path] = ours_content
        else:
            # Both sides changed differently - conflict
            if is_text_file(file_path):
                merged[file_path] = line_level_merge(base_content, ours_content, theirs_content)
            else:
                # Binary file - use ours by default with conflict marker
                merged[file_path] = conflict_marker(base_content, ours_content, theirs_content)

    return merged
```

**File Type Detection**:
- Text files: .md, .py, .js, .txt, .toml, .yaml, etc.
- Binary files: .png, .jpg, .pdf, .zip, etc.
- Use file extension and magic bytes for detection

#### 2. Line-Level Merge (MERGE-003)

**Algorithm (similar to diff3)**:
```python
def line_level_merge(base_lines, ours_lines, theirs_lines) -> list:
    """Merge three versions at line level."""

    # Compute diffs
    base_to_ours = compute_diff(base_lines, ours_lines)
    base_to_theirs = compute_diff(base_lines, theirs_lines)

    # Apply non-conflicting changes
    result = apply_diff_sequence(base_lines, base_to_ours, base_to_theirs)

    # Detect conflicts where both sides changed same lines
    conflicts = detect_conflicts(base_to_ours, base_to_theirs)

    if conflicts:
        # Insert conflict markers
        result = insert_conflict_markers(result, conflicts, ours_lines, theirs_lines)

    return result
```

**Diff Algorithm**:
- Use Myers diff algorithm for optimal line-level diffing
- Compute longest common subsequence (LCS)
- Generate edit operations: insert, delete, modify

**Conflict Detection**:
- Conflict = both ours and theirs modify overlapping line ranges
- Mark line ranges with conflicts
- Generate context around conflicts (±3 lines)

#### 3. Conflict Markers (MERGE-004)

**Format**:
```
<<<<<<< ours
[ours content]
=======
[theirs content]
>>>>>>> theirs
```

**Three-Way Format** (with base context):
```
<<<<<<< ours
[ours content]
||||||| base
[base content]
=======
[theirs content]
>>>>>>> theirs
```

**Implementation**:
- Insert markers at conflict boundaries
- Preserve line numbers for error reporting
- Make markers easily recognizable

#### 4. Merge Preview (MERGE-007)

**Return Structure**:
```python
@dataclass
class MergePreview:
    merged_artifact: dict  # Predicted merge result
    conflicts: list[str]  # List of files with conflicts
    merge_stats: MergeStats
    would_succeed: bool  # True if no unresolvable conflicts
    affected_files: dict  # What changed where
```

**Used For**:
- Showing user what will happen before applying
- Detecting conflicts early
- Providing merge statistics

#### 5. Atomic Apply (MERGE-008)

**Pattern**:
```python
def apply_merge(artifact_dir: Path, merge_result: dict) -> None:
    """Apply merge atomically."""

    # Create temp directory for new content
    temp_dir = artifact_dir.parent / f".merge-tmp-{uuid4()}"

    try:
        # Copy original files to temp
        copy_tree(artifact_dir, temp_dir)

        # Apply merge changes to temp
        for file_path, content in merge_result.items():
            (temp_dir / file_path).write_text(content)

        # Delete files that should be removed
        for file_path in get_deleted_files(merge_result):
            (temp_dir / file_path).unlink()

        # Atomic swap: move temp to actual location
        remove_tree(artifact_dir)
        temp_dir.rename(artifact_dir)

    except Exception as e:
        # Cleanup temp on failure
        if temp_dir.exists():
            remove_tree(temp_dir)
        raise
```

**Safety**:
- Original artifact preserved until final rename
- If process interrupted, can retry or cleanup
- No partial writes to real artifact

#### 6. Binary File Handling (MERGE-010)

**Strategy**:
- Default to ours (local version preferred)
- Option to override and use theirs
- Cannot auto-merge binary files
- Document which version was used

**Implementation**:
```python
def merge_binary_file(ours, theirs, strategy="ours"):
    """Merge binary file using specified strategy."""
    if strategy == "ours":
        return ours
    elif strategy == "theirs":
        return theirs
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
```

#### 7. Merge Statistics (MERGE-011)

**Metrics**:
```python
@dataclass
class MergeStats:
    files_merged: int
    files_with_conflicts: int
    files_added: int
    files_deleted: int
    files_unchanged: int
    lines_added: int
    lines_deleted: int
    merge_type: str  # "clean", "has_conflicts", "unresolvable"
```

**Calculations**:
- Count file operations (add, delete, modify)
- Count line operations from diffs
- Classify overall merge type

### Known Gotchas

**Line Ending Normalization**:
- CRLF vs LF differences should not be treated as changes
- Normalize to LF for comparison, preserve original in output

**Unicode and Encoding**:
- Handle UTF-8, UTF-16, Latin-1
- Detect encoding from file magic bytes
- Default to UTF-8 for undetectable files

**Large File Performance**:
- Diff computation can be slow for very large files (>1MB)
- Consider caching diffs if files don't change
- Profile with large test artifacts to meet <2s target

**Whitespace-Only Changes**:
- Option to ignore whitespace in merge detection
- But preserve exact whitespace in merged output
- Document handling of tabs vs spaces

**Symlinks and Special Files**:
- Treat symlinks as text files (preserve target path)
- Skip special files (sockets, devices)
- Error if unsupported file types encountered

### Development Setup

**Prerequisites**:
- Phase 3 complete (VersionRepository)
- Phase 4 complete (Diff engine)
- Python 3.9+ with difflib, typing

**Libraries**:
- `difflib` (standard library) for diff computation
- Or: `python-Levenshtein` (optional, faster)
- Or: `diff_match_patch` for more options

**Testing Approach**:
- Unit tests for each component (merge, diff, classification)
- Integration tests for full merge workflow
- 50+ test scenarios covering all cases
- Performance benchmarks (target: <2s for 10MB)
- Fuzz testing with random artifact combinations

**Quality Standards**:
- >90% test coverage
- All code formatted with Black
- Type hints with mypy validation
- Docstrings on all public functions
- Performance targets documented

---

## Test Data Sets (MERGE-009)

### Categories

**1. No Conflicts (Clean Merges)**:
- Upstream adds file, ours unchanged
- Ours modifies file, upstream unchanged
- Both add same file with identical content
- File deleted upstream, ours unchanged

**2. Local-Only Changes**:
- Ours modifies multiple files, upstream unchanged
- Ours adds new feature, base and theirs unchanged
- Ours refactors, theirs unchanged

**3. Upstream-Only Changes**:
- Theirs adds file, ours unchanged
- Theirs modifies file, ours unchanged
- Theirs deletes file, ours unchanged

**4. Divergent Changes (Conflicts)**:
- Both modify same file in different ways
- Both add same file with different content
- Ours modifies, theirs deletes same file
- Both modify different parts of same file (should merge cleanly)

**5. Complex Scenarios**:
- Rename: ours deletes A, theirs deletes A, both add A_new
- Multi-file feature: ours adds files A+B, theirs adds B+C
- Refactor conflict: ours moves code, theirs modifies moved code
- Merge conflict with symlinks

**6. Binary Files**:
- Ours modifies .png, theirs unchanged
- Theirs modifies .pdf, ours unchanged
- Both modify same .jpg (should use ours)

**7. Edge Cases**:
- Empty artifact vs artifact with files
- Unicode filenames and content
- Very large files (>10MB)
- Files with no newline at EOF
- Mixed line endings (CRLF vs LF)

### Test Artifact Size Distribution

- 10 small artifacts (<10KB each)
- 20 medium artifacts (~100KB each)
- 15 large artifacts (~1MB each)
- 5 very large artifacts (>5MB each)

---

## Blockers

### Active Blockers

- **BLOCK-1**: Depends on REPO-006 from Phase 3. Can proceed if Phase 3 complete or provides interfaces.

### Potential Risks

1. **Merge algorithm correctness**: Mitigation: 50+ test scenarios, fuzzing
2. **Performance with large artifacts**: Mitigation: Benchmark, optimize diff algorithm
3. **Conflict marker readability**: Mitigation: Clear formatting, user testing
4. **Line ending complications**: Mitigation: Normalize before comparison
5. **Encoding detection**: Mitigation: Use magic bytes, default to UTF-8

---

## Dependencies

### External Dependencies

- `difflib` (Python standard library)
- Optional: `python-Levenshtein` for faster diffing

### Internal Integration Points

- **Phase 3 (REPO-006)**: VersionRepository interface - provides access to artifact versions
- **Phase 4 (Diff)**: Three-way diff computation - builds on diff engine
- **Phase 6 (Merge Policies)**: Will add policy layer on top of this engine
- **Phase 7 (API)**: Will expose merge operations via REST endpoints
- **Phase 8 (UI)**: Will use merge preview and stats for conflict resolution UI

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Merge algorithm, diffs, classification | 95%+ | ⏳ |
| Unit | Conflict detection, markers, stats | 90%+ | ⏳ |
| Integration | Full merge workflow (preview + apply) | Core flows | ⏳ |
| Scenario | 50+ merge test cases covering all types | All major cases | ⏳ |
| Performance | Hash computation on 10MB+ artifacts | <2s target | ⏳ |
| Cross-platform | Line ending handling on Unix/Windows | All utilities | ⏳ |

**Test Data Sets**:
- 50+ synthetic merge scenarios
- Real artifact examples (skills, commands)
- Edge cases (empty files, binary, large)
- Performance test suite with timing

---

## Next Session Agenda

### Immediate Actions (Next Session)

1. [ ] MERGE-001: Implement three-way merge algorithm core
2. [ ] Set up test infrastructure with 50+ merge scenarios
3. [ ] Create test artifact generators for synthetic data

### Upcoming Critical Items

- **After MERGE-001**: Launch Batch 2 in parallel (MERGE-002 through MERGE-011)
- **Critical path completion**: MERGE-001 → MERGE-003 → MERGE-004 (should complete by day 2-3)
- **Full phase completion**: Target end of day 5

### Context for Continuing Agent

**Design Decisions Needed**:
- Myers diff vs difflib for line-level merge (performance tradeoff)
- Three-way vs two-way conflict markers format
- Binary file merge strategy (ours default vs user choice)
- Max file size before considering too large to merge

**Files to Create**:
- `core/merge/merge_engine.py` - Core merge logic
- `core/merge/text_merge.py` - Line-level text merge
- `core/merge/conflict_markers.py` - Conflict marker generation
- `core/merge/classification.py` - Change classification
- `tests/test_merge_engine.py` - Core merge tests
- `tests/fixtures/merge_scenarios.py` - 50+ test scenarios
- `docs/merge-algorithm.md` - Detailed algorithm documentation

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Phase 3 (VersionRepository)**: `.claude/progress/versioning-merge-system/phase-3-progress.md`
- **Phase 4 (Repository Extensions)**: `.claude/progress/versioning-merge-system/phase-4-progress.md`
- **Diff Algorithm Reference**: https://en.wikipedia.org/wiki/Myers_diff_algorithm
- **Three-Way Merge**: https://en.wikipedia.org/wiki/Merge_(version_control)
