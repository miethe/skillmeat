---
type: progress
prd: "versioning-merge-system"
phase: 3
title: "Repository Layer - Version Comparisons & Metadata"
status: "planning"
started: "2025-12-03"
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "REPO-012"
    description: "Implement get_version_diff(v1_id, v2_id) for two-way diffs"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-006"]
    estimated_effort: "3h"
    priority: "high"

  - id: "REPO-013"
    description: "Implement get_files_changed(v1_id, v2_id)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-012"]
    estimated_effort: "2h"
    priority: "high"

  - id: "REPO-014"
    description: "Implement version summary calculation ('{N} added, {M} modified, {K} removed')"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-012"]
    estimated_effort: "2h"
    priority: "high"

  - id: "REPO-015"
    description: "Implement retention policy support (keep last N or N days)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-005"]
    estimated_effort: "3h"
    priority: "medium"

  - id: "REPO-016"
    description: "Implement get_version_for_restore helper"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-006"]
    estimated_effort: "2h"
    priority: "medium"

  - id: "REPO-017"
    description: "Extend .version.toml with audit metadata (performed_by, merge_parent_versions)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-002"]
    estimated_effort: "2h"
    priority: "medium"

parallelization:
  batch_1: ["REPO-012", "REPO-015", "REPO-017"]
  batch_2: ["REPO-013", "REPO-014", "REPO-016"]
  critical_path: ["REPO-012", "REPO-013", "REPO-014"]
  estimated_total_time: "2.5d"

blockers: []

success_criteria:
  - id: "SC-3.1"
    description: "Two-way diffs compute correctly for artifact versions with file-level granularity"
    status: "pending"
  - id: "SC-3.2"
    description: "Files changed lists are accurate and distinguish added/modified/removed"
    status: "pending"
  - id: "SC-3.3"
    description: "Summaries are human-readable and accurately reflect changes"
    status: "pending"
  - id: "SC-3.4"
    description: "Retention policies execute correctly (last N or N days)"
    status: "pending"
  - id: "SC-3.5"
    description: "Rollback preparation includes all needed files and metadata"
    status: "pending"
  - id: "SC-3.6"
    description: "Audit metadata stores correctly and persists in .version.toml"
    status: "pending"
  - id: "SC-3.7"
    description: "Unit tests achieve >85% coverage for all repository methods"
    status: "pending"
---

# versioning-merge-system - Phase 3: Repository Layer - Version Comparisons & Metadata

**Phase**: 3 of 11
**Status**: ⏳ Planning (0% complete)
**Duration**: Estimated 2-3 days, starting 2025-12-03
**Owner**: python-backend-engineer
**Contributors**: None

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - Independent Tasks):
- REPO-012 → `python-backend-engineer` (3h) - Two-way diff implementation
- REPO-015 → `python-backend-engineer` (3h) - Retention policy support
- REPO-017 → `python-backend-engineer` (2h) - Audit metadata extension

**Batch 2** (Sequential - Depends on REPO-012):
- REPO-013 → `python-backend-engineer` (2h) - Files changed implementation - **Blocked by**: REPO-012
- REPO-014 → `python-backend-engineer` (2h) - Summary calculation - **Blocked by**: REPO-012
- REPO-016 → `python-backend-engineer` (2h) - Restore helper - **Depends on**: REPO-006

**Critical Path**: REPO-012 → REPO-013 → REPO-014 (7h total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("python-backend-engineer", "REPO-012: Implement get_version_diff(v1_id, v2_id) in VersionRepository. Return two-way diff structure showing files added, modified, removed. Include line-level diffs for text files. Use difflib for Python files.")

Task("python-backend-engineer", "REPO-015: Implement retention policy support in VersionRepository. Support 'keep_last_n' (int) and 'keep_days' (int) policies. Implement prune method to delete old versions. Store policy config in manifest.")

Task("python-backend-engineer", "REPO-017: Extend .version.toml schema with audit metadata: performed_by (string, user/agent who created), merge_parent_versions (list of parent v1, v2 for merges). Add validation for these fields.")

# Batch 2 (After REPO-012 completes)
Task("python-backend-engineer", "REPO-013: Implement get_files_changed(v1_id, v2_id) based on REPO-012 diff. Return structured list: added (files), modified (files), removed (files). Include file sizes and hashes.")

Task("python-backend-engineer", "REPO-014: Implement version summary calculation. Format: '{N} added, {M} modified, {K} removed'. Handle singular/plural forms. Display in UI summaries and comparison views.")

Task("python-backend-engineer", "REPO-016: Implement get_version_for_restore(artifact_id, restore_point) helper. Accept version ID or timestamp. Return full version metadata plus file listing. Prepare context for restore operation.")
```

---

## Overview

Phase 3 builds out comparison and metadata operations in the VersionRepository, enabling two-way version comparisons, change tracking, and retention policies. This phase is critical for UI features like version diff views and smart retention management.

**Why This Phase**: After establishing storage (Phase 1) and CRUD operations (Phase 2), the next layer is comparison/analysis operations. Diffs are central to the UX (users want to see what changed between versions) and retention policies are essential for managing storage growth. Audit metadata is required for compliance and merge tracking.

**Scope**:
- ✅ **IN SCOPE**: Version diffs, file change tracking, summary generation, retention policies, audit metadata, restore helpers
- ❌ **OUT OF SCOPE**: UI components (Phase 8-9), API endpoints (Phase 7), merge logic (Phase 5), rollback execution (Phase 4)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-3.1 | Two-way diffs compute correctly with file-level granularity | ⏳ Pending |
| SC-3.2 | Files changed lists are accurate (added/modified/removed) | ⏳ Pending |
| SC-3.3 | Summaries are human-readable and accurate | ⏳ Pending |
| SC-3.4 | Retention policies execute correctly (last N or N days) | ⏳ Pending |
| SC-3.5 | Rollback preparation includes all needed files and metadata | ⏳ Pending |
| SC-3.6 | Audit metadata stores and persists correctly | ⏳ Pending |
| SC-3.7 | Unit tests achieve >85% coverage for all repository methods | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| REPO-012 | Implement get_version_diff(v1_id, v2_id) | ⏳ | python-backend-engineer | REPO-006 | 3h | Two-way, file-level granularity |
| REPO-013 | Implement get_files_changed(v1_id, v2_id) | ⏳ | python-backend-engineer | REPO-012 | 2h | Added/modified/removed lists |
| REPO-014 | Implement version summary calculation | ⏳ | python-backend-engineer | REPO-012 | 2h | Human-readable format |
| REPO-015 | Implement retention policy support | ⏳ | python-backend-engineer | REPO-005 | 3h | Last N or N days policies |
| REPO-016 | Implement get_version_for_restore helper | ⏳ | python-backend-engineer | REPO-006 | 2h | Restore context preparation |
| REPO-017 | Extend .version.toml with audit metadata | ⏳ | python-backend-engineer | REPO-002 | 2h | performed_by, merge_parent_versions |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State (After Phase 2)

After Phase 2 completion, the VersionRepository has:
- `create_version(artifact_id, source_path, metadata)` - Creates versioned snapshot
- `get_version(artifact_id, version_id)` - Retrieves version
- `list_versions(artifact_id)` - Lists all versions
- `delete_version(artifact_id, version_id)` - Removes version

**Current .version.toml Schema**:
```toml
[version]
id = "v2-def456"
timestamp = "2025-11-30T10:00:00Z"
hash = "def456..."
source = "anthropics/skills/canvas-design"
parent_versions = ["v1-abc123"]

[changes]
files_changed = ["SKILL.md"]
summary = "1 modified"
```

### Target Architecture (After Phase 3)

After Phase 3, VersionRepository will support:

1. **Version Diffs** - `get_version_diff(v1_id, v2_id)`:
```python
diff = repo.get_version_diff("v1-abc123", "v2-def456")
# Returns:
# {
#   "added": ["new-file.md"],
#   "modified": [{"file": "SKILL.md", "lines_added": 5, "lines_removed": 2}],
#   "removed": ["old-script.js"],
#   "file_diffs": {"SKILL.md": unified_diff_text}
# }
```

2. **Files Changed** - `get_files_changed(v1_id, v2_id)`:
```python
changes = repo.get_files_changed("v1-abc123", "v2-def456")
# Returns:
# {
#   "added": [{"name": "new-file.md", "size": 1024}],
#   "modified": [{"name": "SKILL.md", "size_before": 2048, "size_after": 2100}],
#   "removed": [{"name": "old-script.js", "size": 512}]
# }
```

3. **Version Summaries** - `get_summary(v1_id, v2_id)`:
```python
summary = repo.get_summary("v1-abc123", "v2-def456")
# Returns: "2 added, 1 modified, 1 removed"
```

4. **Retention Policies** - `apply_retention_policy(artifact_id, policy)`:
```python
policy = {"type": "last_n", "value": 10}  # Keep last 10 versions
# Or:
policy = {"type": "days", "value": 30}    # Keep last 30 days

repo.apply_retention_policy(artifact_id, policy)
# Deletes old versions, returns list of deleted version IDs
```

5. **Audit Metadata** - Extended .version.toml:
```toml
[version]
id = "v2-def456"
timestamp = "2025-11-30T10:00:00Z"
hash = "def456..."
source = "anthropics/skills/canvas-design"
parent_versions = ["v1-abc123"]
performed_by = "user@example.com"  # NEW: Who created this version
merge_parent_versions = ["v1-abc123", "v1-xyz789"]  # NEW: For merge commits

[changes]
files_changed = ["SKILL.md"]
summary = "1 modified"
```

6. **Restore Helpers** - `get_version_for_restore(artifact_id, restore_point)`:
```python
restore_ctx = repo.get_version_for_restore("canvas", "v1-abc123")
# Returns complete version snapshot plus metadata for restore operation
```

### Reference Patterns

**Similar Comparison Operations in SkillMeat**:
- `storage/manifest_manager.py` - Compares manifest versions
- `core/sync.py` - Already has diff-like operations for artifact syncing

**Version Comparison Patterns**:
- Git's `git diff` interface (file-level granularity)
- Python's `difflib` for unified diffs
- Semantic versioning concepts (backward compatibility)

**Retention Policy Patterns**:
- Docker image retention (last N images, or by age)
- Log rotation policies (size-based, age-based)
- Backup retention (keep last N backups)

---

## Implementation Details

### REPO-012: Two-Way Version Diffs

**Goal**: Compare two versions and return structured diff information.

**Input**: `artifact_id`, `v1_id`, `v2_id`
**Output**: Structured diff showing:
- Added files (new in v2)
- Modified files (changed between v1 and v2)
- Removed files (in v1 but not v2)
- File diffs (unified diff text for text files)

**Algorithm**:
1. Load both version snapshots from disk
2. Enumerate files in v1 and v2
3. Compare file hashes (quick check for modifications)
4. For modified text files, compute unified diff using difflib
5. Return structured result

**Edge Cases**:
- Binary files (show size change, skip textual diff)
- Symlinks (compare link targets)
- Large files (truncate diffs at reasonable size, e.g., 10KB)
- New artifact versions without parent (treat as "all added")

**Performance Considerations**:
- Cache file hashes to avoid recomputing
- Lazy-load large diffs (only on explicit request)
- Limit diff size to prevent memory bloat

### REPO-013: Files Changed

**Goal**: Return structured list of changed files with metadata.

**Input**: Depends on REPO-012 diff structure
**Output**: List of files with types and metadata

```python
{
    "added": [
        {"name": "new-file.md", "size": 1024, "hash": "..."}
    ],
    "modified": [
        {
            "name": "SKILL.md",
            "size_before": 2048,
            "size_after": 2100,
            "hash_before": "abc123",
            "hash_after": "def456"
        }
    ],
    "removed": [
        {"name": "old-script.js", "size": 512, "hash": "..."}
    ]
}
```

**Algorithm**:
- Extract file metadata from REPO-012 diff result
- Calculate size changes
- Include file hashes from version metadata
- Categorize files into added/modified/removed

### REPO-014: Version Summary Calculation

**Goal**: Human-readable summary of version differences.

**Output Format**: `"{N} added, {M} modified, {K} removed"`
- Only include non-zero categories
- Use singular/plural forms correctly
- Examples:
  - "1 added, 2 modified" (no removed)
  - "5 added" (only additions)
  - "1 removed" (only removal)

**Algorithm**:
- Count files in each category from REPO-013 result
- Build summary string with proper grammar
- Cache summary in version metadata

### REPO-015: Retention Policy Support

**Goal**: Implement policies to automatically delete old versions and manage storage.

**Policies Supported**:
1. **last_n**: Keep only last N versions (delete older)
2. **days**: Keep versions from last N days (delete older)

**Configuration** (in manifest):
```toml
[versioning.retention_policy]
type = "last_n"  # or "days"
value = 10       # Keep last 10 versions, or 10 days
```

**Algorithm**:
1. Parse retention policy from artifact manifest
2. List all versions sorted by timestamp
3. Identify versions to delete based on policy
4. Delete identified versions (cascade delete files)
5. Update manifest with pruning record
6. Return list of deleted version IDs

**Edge Cases**:
- Policy change (was last_n, now days)
- Pinned versions (prevent deletion of important versions)
- Concurrent prune operations (ensure atomicity)

**Performance**:
- Prune on demand, not automatic (user trigger for now)
- Phase 8+ can add scheduled pruning

### REPO-016: Restore Helper

**Goal**: Prepare version for restore operation with all needed context.

**Input**: `artifact_id`, `restore_point` (version ID or timestamp)
**Output**: Complete restore context

```python
{
    "artifact_id": "canvas",
    "version_id": "v1-abc123",
    "version_metadata": {...},  # Full .version.toml content
    "files": [                  # File listing with hashes
        {"name": "SKILL.md", "hash": "abc123", "size": 2048}
    ],
    "source_path": "path/to/versions/v1-abc123",
    "can_restore": True,        # Validation: all files present
    "warnings": []              # e.g., "Restoring to older version"
}
```

**Algorithm**:
1. Find version by ID or nearest timestamp
2. Load version metadata from .version.toml
3. List all files in version snapshot
4. Validate all files exist and hashes match
5. Return context for restore operation

**Validation**:
- Check version directory exists
- Check .version.toml parses correctly
- Verify file hashes match metadata
- Warn if restoring to older version

### REPO-017: Audit Metadata Extension

**Goal**: Extend .version.toml schema to track who created versions and merge relationships.

**Schema Additions**:

```toml
[version]
id = "v2-def456"
timestamp = "2025-11-30T10:00:00Z"
hash = "def456..."
source = "anthropics/skills/canvas-design"
parent_versions = ["v1-abc123"]           # Existing (linear history)
performed_by = "alice@example.com"        # NEW: Creator
merge_parent_versions = ["v1-abc123", "v1-xyz789"]  # NEW: For merge commits
```

**performed_by**:
- String: email, username, or agent identifier
- Optional (defaults to "system" if not provided)
- Used for attribution and audit logs

**merge_parent_versions**:
- List of version IDs that were merged
- Only present for merge commits (Phase 5)
- Enables tracking merge lineage

**Validation Rules**:
- `performed_by` must be non-empty string or None
- `merge_parent_versions` must be list of valid version IDs
- Can only have merge_parent_versions if it's a merge (validated in Phase 5)

**API Updates**:
- `create_version(..., performed_by="user", merge_parents=[...])`
- Store metadata atomically with version creation

---

## Known Gotchas and Learnings

**Diff Performance**: Computing diffs for large files (>1MB) can be slow. Consider:
- Limiting diff output size
- Lazy-loading diffs on request
- Using binary-safe diff algorithm

**Retention Policy Conflicts**: If policies change frequently, version deletion becomes unclear:
- Document policy change history in manifest
- Implement "force_keep" list for protected versions
- Add dry-run mode to preview what would be deleted

**Audit Trail Completeness**: If performed_by is inconsistent, audit trail is incomplete:
- Always capture performed_by in create_version
- Default to environment variables or agent identity
- Validate in tests that every version has audit metadata

**File Size Tracking**: Summary counts don't capture storage impact:
- Phase 3: Include optional total size delta in summary
- Phase 8+: Display storage usage alongside summaries

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | get_version_diff, get_files_changed, summary | 90%+ | ⏳ |
| Unit | Retention policy logic and deletion | 85%+ | ⏳ |
| Unit | Audit metadata schema and validation | 90%+ | ⏳ |
| Unit | Restore helper and validation | 85%+ | ⏳ |
| Integration | Full diff workflow (create, compare, summarize) | Core flows | ⏳ |
| Integration | Retention policy execution end-to-end | Core flows | ⏳ |

**Test Data Sets**:
- Small changes (1-2 files modified)
- Large changes (50+ files, multiple additions/removals)
- Complex scenarios (symlinks, binary files, encoding changes)
- Edge cases (empty versions, single-file artifacts)

**Test Fixtures**:
- Pre-built version pairs with known diffs
- Retention policy test cases (last_n=3, days=7, etc.)
- Audit metadata variations

---

## Dependencies

### Phase Dependencies

- **Phase 2**: VersionRepository base class and CRUD operations (REPO-002 through REPO-011)
- **Phase 5**: Merge logic will use audit metadata (merge_parent_versions)
- **Phase 8-9**: UI will consume diff results and summaries
- **Phase 7**: API endpoints will expose these methods via REST

### Internal Files Modified

- `core/storage/version_repository.py` - Add methods from this phase
- `core/storage/version_schema.py` - Extend .version.toml schema
- `tests/test_version_repository.py` - Add comprehensive tests

---

## Next Session Agenda

### Immediate Actions (Next Session)

1. [ ] REPO-012: Design diff algorithm and implement get_version_diff
2. [ ] REPO-015: Design retention policy logic
3. [ ] REPO-017: Update version schema with audit fields
4. [ ] Set up test fixtures with pre-built version pairs

### Upcoming Critical Items

- **Critical Path**: Complete REPO-012 before REPO-013/REPO-014
- **Parallel Work**: REPO-015 and REPO-017 can proceed independently
- **Quality Gate**: >85% test coverage required before phase completion

### Context for Continuing Agent

**Design Decisions Needed**:
- Diff output format (unified diff vs. custom JSON)
- How to handle binary file diffs (show only metadata)
- Max diff size before truncation/pagination
- Retention policy priority (last_n vs. days if both specified)

**Files to Reference**:
- `core/storage/version_repository.py` - Base class
- `core/storage/version_schema.py` - TOML schema
- `tests/test_version_repository.py` - Test patterns
- Phase 2 implementation for CRUD method patterns

**Integration Points**:
- Phase 5 (merge) will pass merge_parent_versions to create_version
- Phase 7 (API) will expose diff methods as REST endpoints
- Phase 8-9 (UI) will display summaries and diffs

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md` (Phase 3 section)
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Phase 2 Context**: `.claude/progress/versioning-merge-system/phase-2-progress.md`
- **Python difflib Documentation**: https://docs.python.org/3/library/difflib.html
- **Retention Policy Patterns**: Docker, Kubernetes, and backup systems
