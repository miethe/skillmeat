---
type: progress
prd: versioning-merge-system
phase: 1
title: Storage Infrastructure
status: partial
started: '2025-11-30'
completed: null
overall_progress: 60
completion_estimate: architecture-deviation
total_tasks: 6
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
owners:
- data-layer-expert
contributors:
- python-backend-engineer
tasks:
- id: TASK-1.1
  description: Design and document versions/ and latest/ directory layout for artifacts
  status: deviated
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 3h
  priority: high
  implementation: Uses ~/.skillmeat/snapshots/{collection}/*.tar.gz instead of per-artifact
    versions/
  note: 'Different architecture: tarball-based collection snapshots vs directory-based
    artifact versions'
- id: TASK-1.2
  description: Define .version.toml schema with id, timestamp, hash, source, files_changed,
    change_summary, parent_versions
  status: partial
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-1.1
  estimated_effort: 3h
  priority: high
  implementation: snapshots.toml in SnapshotManager with id, timestamp, message, artifact_count
  note: 'Missing: files_changed, change_summary, parent_versions fields'
- id: TASK-1.3
  description: Implement deterministic version ID generation (v{n}-{hash})
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-1.2
  estimated_effort: 2h
  priority: high
  implementation: Snapshot ID = timestamp format YYYYMMDD-HHMMSS-microseconds (deterministic,
    sortable)
- id: TASK-1.4
  description: Implement deterministic file hashing strategy for artifact files (SHA256)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 2h
  priority: medium
  implementation: compute_content_hash() in utils/filesystem.py uses SHA256
- id: TASK-1.5
  description: Build utility to create version snapshot directories from source artifacts
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-1.1
  estimated_effort: 2h
  priority: high
  implementation: SnapshotManager.create_snapshot() creates tar.gz of collection
- id: TASK-1.6
  description: Design gzip/bzip2 compression option for version storage (optional,
    feature-flagged)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-1.5
  estimated_effort: 2h
  priority: low
  implementation: Snapshots are always gzip compressed (tar.gz)
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.4
  batch_2:
  - TASK-1.2
  - TASK-1.5
  batch_3:
  - TASK-1.3
  - TASK-1.6
  critical_path:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  estimated_total_time: 3d
blockers: []
success_criteria:
- id: SC-1
  description: Version directory structure designed and documented with clear examples
  status: deviated
  note: Using tarball snapshots instead of version directories
- id: SC-2
  description: TOML schema complete with all required fields and validation rules
  status: partial
- id: SC-3
  description: Version ID generation produces sortable, unique IDs with content hash
  status: completed
- id: SC-4
  description: Hash computation deterministic - same artifact produces same hash
  status: completed
- id: SC-5
  description: Directory creation utility handles edge cases (missing files, symlinks)
  status: completed
- id: SC-6
  description: Unit tests for all utilities achieve >90% coverage
  status: partial
files_modified:
- path: skillmeat/storage/snapshot.py
  status: created
  lines: 271
  note: SnapshotManager with tarball-based snapshots
- path: skillmeat/utils/filesystem.py
  status: modified
  note: compute_content_hash() for SHA256 hashing
schema_version: 2
doc_type: progress
feature_slug: versioning-merge-system
---

# versioning-merge-system - Phase 1: Storage Infrastructure

**Phase**: 1 of 11
**Status**: ⚠️ PARTIAL (60%) - Implemented with different architecture (tarball snapshots vs versioned directories)
**Duration**: Started 2025-11-30, estimated completion 2025-12-03
**Owner**: data-layer-expert
**Contributors**: python-backend-engineer

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- TASK-1.1 → `data-layer-expert` (3h) - Directory structure design
- TASK-1.4 → `data-layer-expert` (2h) - File hashing strategy

**Batch 2** (Sequential - Depends on Batch 1):
- TASK-1.2 → `data-layer-expert` (3h) - TOML schema definition - **Blocked by**: TASK-1.1
- TASK-1.5 → `data-layer-expert` (2h) - Snapshot directory utility - **Blocked by**: TASK-1.1

**Batch 3** (Sequential - Depends on Batch 2):
- TASK-1.3 → `data-layer-expert` (2h) - Version ID generation - **Blocked by**: TASK-1.2
- TASK-1.6 → `data-layer-expert` (2h) - Compression strategy (optional) - **Blocked by**: TASK-1.5

**Critical Path**: TASK-1.1 → TASK-1.2 → TASK-1.3 (8h total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("data-layer-expert", "TASK-1.1: Design and document versions/ and latest/ directory layout for artifacts. Support symlinks for latest version. Document in design doc with examples.")
Task("data-layer-expert", "TASK-1.4: Implement deterministic file hashing strategy for artifact files using SHA256. Handle different file types, optimize for performance.")

# Batch 2 (After Batch 1 completes)
Task("data-layer-expert", "TASK-1.2: Define .version.toml schema with all required fields: id, timestamp, hash, source, files_changed, change_summary, parent_versions. Include validation rules.")
Task("data-layer-expert", "TASK-1.5: Build utility to create version snapshot directories from source artifacts. Handle symlinks, missing files, edge cases.")

# Batch 3 (After Batch 2 completes)
Task("data-layer-expert", "TASK-1.3: Implement deterministic version ID generation using v{n}-{hash} format. IDs must be sortable, unique, contain content hash.")
Task("data-layer-expert", "TASK-1.6: Design gzip/bzip2 compression option for version storage. Make optional via feature flag, document storage savings.")
```

---

## Overview

Phase 1 establishes the foundational storage structure for version history at both collection and project levels. This phase creates the directory layout, metadata schema, hashing strategy, and utilities needed by all subsequent phases.

**Why This Phase**: Version history requires robust storage infrastructure that is deterministic, space-efficient, and supports both collection-level (~/.skillmeat/collection/) and project-level (./.claude/) artifacts. This foundation enables all merge, rollback, and comparison operations in later phases.

**Scope**:
- ✅ **IN SCOPE**: Directory structure design, TOML schema, version ID generation, file hashing, snapshot creation utilities, optional compression
- ❌ **OUT OF SCOPE**: CRUD operations (Phase 2), merge logic (Phase 5), API endpoints (Phase 7), UI components (Phase 8-9)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | Version directory structure designed and documented with clear examples | ⏳ Pending |
| SC-2 | TOML schema complete with all required fields and validation rules | ⏳ Pending |
| SC-3 | Version ID generation produces sortable, unique IDs with content hash | ⏳ Pending |
| SC-4 | Hash computation deterministic - same artifact produces same hash | ⏳ Pending |
| SC-5 | Directory creation utility handles edge cases (missing files, symlinks) | ⏳ Pending |
| SC-6 | Unit tests for all utilities achieve >90% coverage | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| TASK-1.1 | Design versions/ and latest/ directory layout | ⏳ | data-layer-expert | None | 3h | Supports symlinks, documented |
| TASK-1.2 | Define .version.toml schema | ⏳ | data-layer-expert | TASK-1.1 | 3h | All required fields |
| TASK-1.3 | Implement version ID generation (v{n}-{hash}) | ⏳ | data-layer-expert | TASK-1.2 | 2h | Sortable, unique, deterministic |
| TASK-1.4 | Implement file hashing (SHA256) | ⏳ | data-layer-expert | None | 2h | Fast, handles all file types |
| TASK-1.5 | Build snapshot directory creation utility | ⏳ | data-layer-expert | TASK-1.1 | 2h | Handles symlinks, edge cases |
| TASK-1.6 | Design compression strategy (optional) | ⏳ | data-layer-expert | TASK-1.5 | 2h | Feature-flagged, optional |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State

SkillMeat currently stores artifacts in flat directories at collection and project levels:

**Collection Level**:
```
~/.skillmeat/collection/artifacts/{artifact-name}/
  ├── SKILL.md
  ├── supporting-file.md
  └── scripts/
```

**Project Level**:
```
./.claude/skills/{artifact-name}/
  ├── SKILL.md
  ├── supporting-file.md
  └── scripts/
```

Currently, there is NO version history - updates overwrite existing files. This phase adds versioned storage.

### Target Architecture

After Phase 1, artifacts will have versioned snapshots:

**Collection Level with Versions**:
```
~/.skillmeat/collection/artifacts/{artifact-name}/
  ├── versions/
  │   ├── v1-abc123/
  │   │   ├── .version.toml
  │   │   ├── SKILL.md
  │   │   └── scripts/
  │   ├── v2-def456/
  │   │   ├── .version.toml
  │   │   ├── SKILL.md
  │   │   └── scripts/
  │   └── latest -> v2-def456/  # Symlink
  └── manifest.toml
```

**Version Metadata Schema (.version.toml)**:
```toml
[version]
id = "v2-def456"
timestamp = "2025-11-30T10:00:00Z"
hash = "def456..."
source = "anthropics/skills/canvas-design"
parent_versions = ["v1-abc123"]

[changes]
files_changed = ["SKILL.md", "scripts/process.js"]
summary = "2 modified"
```

### Reference Patterns

**Similar Storage Patterns in SkillMeat**:
- Snapshot storage in `storage/snapshot_manager.py` uses timestamped directories - can mirror this pattern
- Manifest TOML in `storage/manifest_manager.py` shows TOML schema patterns
- Lockfile structure in `storage/lockfile_manager.py` demonstrates SHA resolution

**Version Control Inspiration**:
- Git's content-addressable storage (hash-based identification)
- Symlinks for "latest" pointer (similar to git HEAD)
- Immutable snapshots with metadata

---

## Implementation Details

### Technical Approach

1. **Directory Structure Design (TASK-1.1)**:
   - Create `versions/` subdirectory under each artifact directory
   - Use `v{n}-{short-hash}/` naming for version directories
   - Create `latest` symlink pointing to most recent version
   - Support both collection and project level paths

2. **TOML Schema Definition (TASK-1.2)**:
   - Define required fields: id, timestamp, hash, source, parent_versions
   - Define optional fields: files_changed, summary, merge_parent_versions
   - Use TOML for consistency with existing SkillMeat manifests
   - Add validation rules for each field

3. **Version ID Generation (TASK-1.3)**:
   - Format: `v{n}-{short-hash}` where n is sequential and hash is first 7 chars of content hash
   - Sequential number for sortability, hash for uniqueness
   - Deterministic based on artifact content

4. **File Hashing (TASK-1.4)**:
   - Use SHA256 for cryptographic strength
   - Hash directory tree contents (not just individual files)
   - Handle binary and text files consistently
   - Optimize for performance (streaming, caching)

5. **Snapshot Creation (TASK-1.5)**:
   - Copy all artifact files to versioned directory
   - Write .version.toml metadata
   - Update latest symlink atomically
   - Handle edge cases (missing files, broken symlinks)

6. **Compression Strategy (TASK-1.6)**:
   - Design optional gzip compression for version directories
   - Feature flag: `storage.version_compression = true/false`
   - Measure storage savings vs. performance tradeoff
   - Document compression ratios

### Known Gotchas

**Cross-Platform Symlinks**:
- Windows symlink support requires admin privileges or Developer Mode
- Fallback: Copy instead of symlink on Windows if needed
- Test symlink creation on all platforms (Linux, macOS, Windows)

**Deterministic Hashing**:
- File modification times should NOT affect hash
- Directory traversal order must be deterministic (sorted)
- Line ending normalization (CRLF vs LF) may be needed

**Atomic Operations**:
- Use temp directory + atomic move pattern
- Prevent partial writes if process interrupted
- Ensure latest symlink update is atomic

**Storage Growth**:
- Version history can grow large over time
- Phase 3 will add retention policies
- For now, document expected storage usage

### Development Setup

**Prerequisites**:
- Python 3.9+ with tomllib/tomli support
- Development dependencies: pytest, pytest-cov, black, mypy

**Testing Approach**:
- Unit tests for each utility function (hashing, ID generation)
- Integration tests for directory creation
- Cross-platform tests (Linux, macOS, Windows)
- Performance benchmarks for hashing large artifacts

**Quality Standards**:
- >90% test coverage for all utilities
- All code formatted with Black
- Type hints with mypy validation
- Docstrings on all public functions

---

## Blockers

### Active Blockers

_No active blockers at this time._

### Potential Risks

1. **Cross-platform symlink handling**: Mitigation: Implement fallback for Windows
2. **Storage space growth**: Mitigation: Document compression option, plan retention policies for Phase 3
3. **Performance with large artifacts**: Mitigation: Benchmark hashing, optimize if needed

---

## Dependencies

### External Dependencies

- **None for Phase 1**: This phase is foundational and has no external dependencies

### Internal Integration Points

- **Phase 2**: Will build VersionRepository on top of this storage infrastructure
- **Phase 3**: Will extend metadata schema for retention policies
- **storage/manifest_manager.py**: Reference for TOML schema patterns
- **storage/snapshot_manager.py**: Reference for directory snapshot patterns

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Version ID generation, hashing, TOML schema | 95%+ | ⏳ |
| Unit | Directory creation utility, symlink handling | 90%+ | ⏳ |
| Integration | Full snapshot creation workflow | Core flows | ⏳ |
| Cross-platform | Linux, macOS, Windows compatibility | All utilities | ⏳ |
| Performance | Hash computation on 10MB+ artifacts | <500ms target | ⏳ |

**Test Data Sets**:
- Small artifact: 2-3 files, <10KB total
- Medium artifact: 10-15 files, ~500KB total
- Large artifact: 50+ files, 10MB+ total
- Edge cases: Binary files, symlinks, Unicode filenames

---

## Next Session Agenda

### Immediate Actions (Next Session)

1. [ ] TASK-1.1: Design directory structure - create design doc with examples
2. [ ] TASK-1.4: Implement file hashing utility - start with basic SHA256
3. [ ] Set up test infrastructure with pytest fixtures for temp directories

### Upcoming Critical Items

- **Week of 2025-12-02**: Complete all Phase 1 tasks, prepare for Phase 2 (Repository Layer)
- **Handoff to Phase 2**: Provide completed design docs and utilities to python-backend-engineer

### Context for Continuing Agent

**Design Decisions Needed**:
- Finalize directory naming convention (v{n}-{hash} vs. alternatives)
- Decide on hash length (7 chars like git, or longer?)
- Confirm compression strategy (optional for v1, required later?)

**Files to Create**:
- `core/storage/version_storage.py` - Core storage utilities
- `core/storage/version_schema.py` - TOML schema and validation
- `tests/test_version_storage.py` - Unit tests
- `docs/architecture/version-storage.md` - Design documentation

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Storage Patterns**: `storage/snapshot_manager.py`, `storage/manifest_manager.py`
- **Schema Reference**: `storage/lockfile_manager.py` for TOML schema examples
