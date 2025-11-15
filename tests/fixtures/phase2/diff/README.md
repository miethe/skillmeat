# Phase 2 Diff/Merge Test Fixtures

This directory contains comprehensive, reusable test fixtures for Phase 1 diff and merge operations. These fixtures support testing of the DiffEngine, MergeEngine, and CLI diff commands.

## Directory Structure

```
tests/fixtures/phase2/diff/
├── README.md                          # This file
├── text_files/                        # Basic text file test cases
│   ├── simple.txt                     # Single-line file
│   ├── multi_line.txt                 # Multi-line document (7 lines)
│   ├── empty.txt                      # Empty file (0 bytes)
│   ├── large.txt                      # Large file (1000 lines)
│   └── special_chars.txt              # Unicode, emoji, special characters
├── binary_files/                      # Binary file test cases
│   ├── image.png                      # Minimal PNG image
│   ├── archive.zip                    # ZIP archive
│   └── executable.bin                 # Binary executable (ELF format)
├── conflict_scenarios/                # Three-way merge conflicts
│   ├── base/                          # Common ancestor version
│   │   ├── content_conflict.md        # File with content conflict
│   │   ├── deletion_conflict.txt      # File deleted locally, modified remotely
│   │   ├── both_modified.json         # Both versions modified differently
│   │   └── (no add_add_conflict.py)   # File doesn't exist in base
│   ├── local/                         # Local modifications
│   │   ├── content_conflict.md        # Local changes
│   │   ├── (deletion_conflict.txt deleted)
│   │   ├── add_add_conflict.py        # New file added locally
│   │   └── both_modified.json         # Local modifications
│   └── remote/                        # Remote modifications
│       ├── content_conflict.md        # Remote changes
│       ├── deletion_conflict.txt      # Remote modifications
│       ├── add_add_conflict.py        # New file added remotely (different content)
│       └── both_modified.json         # Remote modifications
├── auto_merge_scenarios/              # Auto-mergeable scenarios
│   ├── base/                          # Common ancestor
│   │   ├── local_only_changed.txt     # File changed only locally
│   │   ├── remote_only_changed.py     # File changed only remotely
│   │   ├── both_identical.md          # Both changed identically
│   │   ├── deleted_both.txt           # Deleted in both versions
│   │   └── unchanged.cfg              # Unchanged in all versions
│   ├── local/                         # Local version
│   │   ├── local_only_changed.txt     # Modified locally
│   │   ├── remote_only_changed.py     # Unchanged
│   │   ├── both_identical.md          # Same changes as remote
│   │   ├── (deleted_both.txt deleted)
│   │   └── unchanged.cfg              # Unchanged
│   └── remote/                        # Remote version
│       ├── local_only_changed.txt     # Unchanged
│       ├── remote_only_changed.py     # Modified remotely
│       ├── both_identical.md          # Same changes as local
│       ├── (deleted_both.txt deleted)
│       └── unchanged.cfg              # Unchanged
├── edge_cases/                        # Edge case scenarios
│   ├── nested/                        # Nested directory structure
│   │   ├── file_level1.txt
│   │   └── dir1/
│   │       ├── file_level2.txt
│   │       └── dir2/
│   │           └── deep_file.txt
│   ├── whitespace_variations.txt      # Different whitespace patterns
│   ├── long_lines.txt                 # Very long lines (>200 chars)
│   ├── no_newline_at_end.txt          # File without trailing newline
│   ├── only_whitespace.txt            # File with only whitespace
│   ├── encoding_test.txt              # UTF-8 encoding test
│   └── permissions/                   # Files with different permissions
│       └── readable.txt
├── dir_v1/                            # Legacy: Directory version 1
│   ├── common.txt
│   ├── removed.txt
│   └── modified.txt
├── dir_v2/                            # Legacy: Directory version 2
│   ├── common.txt
│   ├── added.txt
│   └── modified.txt
├── file_v1.txt                        # Legacy: File version 1
└── file_v2.txt                        # Legacy: File version 2
```

## Usage

### In Tests

```python
from pathlib import Path

# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "phase2" / "diff"

def test_with_text_fixture():
    """Example: Using text file fixtures."""
    simple_file = FIXTURES_DIR / "text_files" / "simple.txt"
    content = simple_file.read_text()
    # Use fixture in test...

def test_with_conflict_scenario():
    """Example: Using three-way conflict fixtures."""
    base_dir = FIXTURES_DIR / "conflict_scenarios" / "base"
    local_dir = FIXTURES_DIR / "conflict_scenarios" / "local"
    remote_dir = FIXTURES_DIR / "conflict_scenarios" / "remote"

    engine = DiffEngine()
    result = engine.three_way_diff(base_dir, local_dir, remote_dir)
    # Verify conflict detection...

def test_with_auto_merge_scenario():
    """Example: Using auto-mergeable fixtures."""
    base_dir = FIXTURES_DIR / "auto_merge_scenarios" / "base"
    local_dir = FIXTURES_DIR / "auto_merge_scenarios" / "local"
    remote_dir = FIXTURES_DIR / "auto_merge_scenarios" / "remote"

    merge_engine = MergeEngine()
    result = merge_engine.merge(base_dir, local_dir, remote_dir)
    # Verify auto-merge success...
```

## Fixture Categories

### 1. Text Files

Basic text file test cases for file-level diff operations.

#### simple.txt
- Single-line text file
- Use case: Basic file comparison

#### multi_line.txt
- 7-line document with varied content
- Use case: Line-by-line diff testing

#### empty.txt
- Empty file (0 bytes)
- Use case: Edge case testing for empty files

#### large.txt
- 1000+ lines
- Use case: Performance testing, large file handling

#### special_chars.txt
- Unicode characters (Greek, Math, Emoji, CJK, Arabic)
- ASCII special characters
- Accented characters
- Whitespace variations
- Use case: Encoding and special character handling

### 2. Binary Files

Binary file test cases for binary diff detection.

#### image.png
- Minimal 1x1 PNG image
- Use case: Binary file detection, cannot generate text diff

#### archive.zip
- ZIP archive with multiple files
- Use case: Compressed file handling

#### executable.bin
- Binary executable (ELF format header)
- Use case: Binary conflict detection

### 3. Conflict Scenarios

Pre-configured three-way merge conflicts that require manual resolution.

#### 1. content_conflict.md
**Scenario**: Both local and remote modified the same file in different ways.

- **Base**: Original introduction and section 1
- **Local**: Modified introduction ("LOCALLY MODIFIED") and section 1 line 1
- **Remote**: Modified introduction ("REMOTELY MODIFIED") and section 1 line 2
- **Expected**: Conflict requiring manual merge
- **Conflict Type**: `both_modified`

#### 2. deletion_conflict.txt
**Scenario**: File deleted locally but modified remotely.

- **Base**: Original 4-line file
- **Local**: File deleted (doesn't exist)
- **Remote**: Modified content with new line
- **Expected**: Deletion conflict
- **Conflict Type**: `deletion`

#### 3. add_add_conflict.py
**Scenario**: Same filename added in both versions with different content.

- **Base**: File doesn't exist
- **Local**: Python file with `calculate_sum()` function
- **Remote**: Python file with `calculate_product()` function
- **Expected**: Add-add conflict
- **Conflict Type**: `add_add`

#### 4. both_modified.json
**Scenario**: JSON config file modified differently in both versions.

- **Base**: Version 1.0.0 with basic config
- **Local**: Version 1.1.0 with local package and description
- **Remote**: Version 1.2.0 with remote package, new author, and license change
- **Expected**: Complex conflict with multiple changes
- **Conflict Type**: `both_modified`

### 4. Auto-Merge Scenarios

Pre-configured scenarios that should auto-merge successfully.

#### 1. local_only_changed.txt
**Scenario**: Only local version changed.

- **Base**: Original 3-line content
- **Local**: Modified line 1, added line 4
- **Remote**: Unchanged from base
- **Expected**: Auto-merge using local version
- **Strategy**: `use_local`

#### 2. remote_only_changed.py
**Scenario**: Only remote version changed.

- **Base**: Simple hello() function
- **Local**: Unchanged from base
- **Remote**: Enhanced with parameters, docstrings, and goodbye() function
- **Expected**: Auto-merge using remote version
- **Strategy**: `use_remote`

#### 3. both_identical.md
**Scenario**: Both local and remote made identical changes.

- **Base**: Original documentation
- **Local**: Updated overview and details
- **Remote**: Same updates as local
- **Expected**: Auto-merge (both versions are identical)
- **Strategy**: `use_local` (or `use_remote`, both work)

#### 4. deleted_both.txt
**Scenario**: File deleted in both versions.

- **Base**: Original file with content
- **Local**: Deleted (doesn't exist)
- **Remote**: Deleted (doesn't exist)
- **Expected**: Auto-merge deletion
- **Strategy**: `use_local` (deletion agreed upon)

#### 5. unchanged.cfg
**Scenario**: File unchanged in all versions.

- **Base**: Config file
- **Local**: Unchanged
- **Remote**: Unchanged
- **Expected**: No merge needed (unchanged)

### 5. Edge Cases

Special scenarios for edge case testing.

#### nested/
- Deeply nested directory structure (3 levels)
- Tests: Recursive directory traversal
- Files at multiple levels: level1, level2, and level3 (deep_file.txt)

#### whitespace_variations.txt
- Trailing spaces, trailing tabs
- Leading tabs, leading spaces
- Mixed spaces and tabs
- Tests: Whitespace handling in diffs

#### long_lines.txt
- Lines exceeding 200 characters
- Tests: Line wrapping, display constraints

#### no_newline_at_end.txt
- File without trailing newline
- Tests: EOF handling

#### only_whitespace.txt
- File containing only whitespace characters
- Tests: Empty-like file handling

#### encoding_test.txt
- UTF-8 encoded file with extended characters
- Special Unicode cases (zero-width space, non-breaking space, etc.)
- Tests: Encoding handling

#### permissions/
- Files with different permission modes
- Tests: Permission preservation during merge

### 6. Legacy Fixtures

These fixtures existed before the comprehensive library was built.

#### dir_v1/ and dir_v2/
- Simple two-version directory comparison
- Contains: common.txt, removed.txt (v1), added.txt (v2), modified.txt (both)

#### file_v1.txt and file_v2.txt
- Simple two-version file comparison
- One line removed, two lines added

## Test Coverage Matrix

| Fixture Category | DiffEngine | MergeEngine | CLI Diff | Three-Way |
|------------------|------------|-------------|----------|-----------|
| Text Files       | ✓          | ✓           | ✓        | ✓         |
| Binary Files     | ✓          | ✓           | ✓        | ✓         |
| Conflict Scenarios | ✓        | ✓           | ✓        | ✓         |
| Auto-Merge Scenarios | ✓      | ✓           | ✓        | ✓         |
| Edge Cases       | ✓          | ✓           | ✓        | ✓         |

## Fixture Design Principles

1. **Reusability**: All fixtures can be used across multiple test files
2. **Clarity**: Each fixture has a clear, documented purpose
3. **Realism**: Fixtures use realistic content (code, docs, configs)
4. **Completeness**: Cover all major diff/merge scenarios
5. **Maintainability**: Small, focused fixtures that are easy to understand
6. **Performance**: Include large files for performance testing

## Adding New Fixtures

When adding new fixtures, follow these guidelines:

1. **Location**: Place in appropriate category directory
2. **Naming**: Use descriptive names that indicate purpose
3. **Size**: Keep fixtures small unless testing performance
4. **Documentation**: Update this README with new fixture details
5. **Scenarios**: For three-way fixtures, create base/local/remote versions
6. **Realism**: Use realistic content relevant to the test case

## Example Usage in Tests

### Example 1: Testing File Diff

```python
def test_diff_special_characters():
    """Test diff engine handles special characters correctly."""
    engine = DiffEngine()

    # Create modified version
    source = FIXTURES_DIR / "text_files" / "special_chars.txt"
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        content = source.read_text()
        tmp.write(content.replace("🔥", "🚀"))
        target_path = tmp.name

    try:
        result = engine.diff_files(source, Path(target_path))
        assert result.status == "modified"
        assert "🔥" in result.unified_diff
        assert "🚀" in result.unified_diff
    finally:
        Path(target_path).unlink()
```

### Example 2: Testing Three-Way Merge Conflict

```python
def test_content_conflict():
    """Test detection of content conflict."""
    engine = DiffEngine()

    base = FIXTURES_DIR / "conflict_scenarios" / "base"
    local = FIXTURES_DIR / "conflict_scenarios" / "local"
    remote = FIXTURES_DIR / "conflict_scenarios" / "remote"

    result = engine.three_way_diff(base, local, remote)

    # Should detect conflict in content_conflict.md
    assert result.has_conflicts
    conflicts = [c for c in result.conflicts if c.file_path == "content_conflict.md"]
    assert len(conflicts) == 1

    conflict = conflicts[0]
    assert conflict.conflict_type == "both_modified"
    assert conflict.auto_mergeable is False
    assert "LOCALLY MODIFIED" in conflict.local_content
    assert "REMOTELY MODIFIED" in conflict.remote_content
```

### Example 3: Testing Auto-Merge

```python
def test_auto_merge_remote_only():
    """Test auto-merge when only remote changed."""
    merge_engine = MergeEngine()

    base = FIXTURES_DIR / "auto_merge_scenarios" / "base"
    local = FIXTURES_DIR / "auto_merge_scenarios" / "local"
    remote = FIXTURES_DIR / "auto_merge_scenarios" / "remote"

    with tempfile.TemporaryDirectory() as output:
        result = merge_engine.merge(base, local, remote, Path(output))

        # Should auto-merge successfully
        assert result.success
        assert len(result.conflicts) == 0
        assert "remote_only_changed.py" in result.auto_merged

        # Verify merged content is from remote
        merged_file = Path(output) / "remote_only_changed.py"
        content = merged_file.read_text()
        assert "def goodbye" in content  # Remote added this function
```

## Performance Benchmarks

Using the large.txt fixture (1000 lines):

- **DiffEngine.diff_files()**: <10ms
- **DiffEngine.diff_directories()**: <50ms for 100 files
- **DiffEngine.three_way_diff()**: <2s for 500 files (PRD requirement)
- **MergeEngine.merge()**: <2s for 500 files

## Related Documentation

- `/home/user/skillmeat/skillmeat/core/diff_engine.py`: DiffEngine implementation
- `/home/user/skillmeat/skillmeat/core/merge_engine.py`: MergeEngine implementation
- `/home/user/skillmeat/tests/test_diff_basic.py`: Basic diff tests
- `/home/user/skillmeat/tests/test_three_way_diff.py`: Three-way diff tests (27 tests)
- `/home/user/skillmeat/tests/test_merge_engine.py`: Merge engine tests (23 tests)
- `/home/user/skillmeat/tests/test_cli_diff.py`: CLI diff tests (30 tests)

## Maintenance

Last Updated: 2025-11-15
Total Fixtures: 40+ files across 5 categories
Maintainer: SkillMeat Development Team
