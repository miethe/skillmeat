---
type: progress
prd: versioning-merge-system
phase: 2
title: Repository Layer - Version CRUD
status: planning
started: '2025-12-03'
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 11
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
- data-layer-expert
contributors: []
tasks:
- id: REPO-001
  description: Create VersionRepository base class with CRUD interface
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: REPO-002
  description: 'Implement create_version: snapshot files, write metadata TOML'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-001
  estimated_effort: 5h
  priority: high
- id: REPO-003
  description: Implement get_version to retrieve specific version
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-002
  estimated_effort: 2h
  priority: high
- id: REPO-004
  description: Implement list_versions with chronological ordering
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-002
  estimated_effort: 3h
  priority: high
- id: REPO-005
  description: Implement delete_version with safety checks
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-002
  estimated_effort: 2h
  priority: medium
- id: REPO-006
  description: Implement get_version_content for file retrieval
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-003
  estimated_effort: 3h
  priority: medium
- id: REPO-007
  description: Implement version existence check helper
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-003
  estimated_effort: 1h
  priority: medium
- id: REPO-008
  description: Implement get_latest_version helper
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-004
  estimated_effort: 1h
  priority: medium
- id: REPO-009
  description: Implement CollectionVersionRepository for ~/.skillmeat/
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-001
  estimated_effort: 3h
  priority: high
- id: REPO-010
  description: Implement ProjectVersionRepository for ./.claude/
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-001
  estimated_effort: 3h
  priority: high
- id: REPO-011
  description: Test TOML read/write for version metadata persistence
  status: pending
  assigned_to:
  - data-layer-expert
  dependencies:
  - REPO-002
  estimated_effort: 2h
  priority: high
parallelization:
  batch_1:
  - REPO-001
  batch_2:
  - REPO-002
  - REPO-009
  - REPO-010
  batch_3:
  - REPO-003
  - REPO-004
  - REPO-005
  batch_4:
  - REPO-006
  - REPO-007
  - REPO-008
  - REPO-011
  critical_path:
  - REPO-001
  - REPO-002
  - REPO-003
  - REPO-006
  estimated_total_time: 5d
blockers: []
success_criteria:
- id: SC-1
  description: VersionRepository base class with full CRUD interface defined
  status: pending
- id: SC-2
  description: create_version atomically snapshots files and writes .version.toml
  status: pending
- id: SC-3
  description: get_version retrieves specific version with all metadata intact
  status: pending
- id: SC-4
  description: list_versions returns chronologically ordered results (oldest to newest)
  status: pending
- id: SC-5
  description: delete_version safely removes versions with validation checks
  status: pending
- id: SC-6
  description: get_version_content retrieves individual files from versions (text/binary)
  status: pending
- id: SC-7
  description: CollectionVersionRepository and ProjectVersionRepository fully functional
  status: pending
- id: SC-8
  description: All CRUD operations tested end-to-end with >85% coverage
  status: pending
- id: SC-9
  description: Version metadata persists and loads correctly across sessions
  status: pending
- id: SC-10
  description: 'List performance: 100 versions < 100ms'
  status: pending
schema_version: 2
doc_type: progress
feature_slug: versioning-merge-system
---

# versioning-merge-system - Phase 2: Repository Layer - Version CRUD

**Phase**: 2 of 10
**Status**: ⏳ Planning (0% complete)
**Duration**: Started 2025-12-03, estimated completion 2025-12-08
**Owners**: python-backend-engineer, data-layer-expert
**Contributors**: None yet

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - Blocking):
- REPO-001 → `python-backend-engineer` (3h) - Base class definition - **No dependencies**

**Batch 2** (Parallel - After Batch 1):
- REPO-002 → `python-backend-engineer` (5h) - create_version implementation - **Blocked by**: REPO-001
- REPO-009 → `python-backend-engineer` (3h) - CollectionVersionRepository - **Blocked by**: REPO-001
- REPO-010 → `python-backend-engineer` (3h) - ProjectVersionRepository - **Blocked by**: REPO-001

**Batch 3** (Parallel - After Batch 2):
- REPO-003 → `python-backend-engineer` (2h) - get_version - **Blocked by**: REPO-002
- REPO-004 → `python-backend-engineer` (3h) - list_versions - **Blocked by**: REPO-002
- REPO-005 → `python-backend-engineer` (2h) - delete_version - **Blocked by**: REPO-002

**Batch 4** (Parallel - After Batch 3):
- REPO-006 → `python-backend-engineer` (3h) - get_version_content - **Blocked by**: REPO-003
- REPO-007 → `python-backend-engineer` (1h) - version_exists helper - **Blocked by**: REPO-003
- REPO-008 → `python-backend-engineer` (1h) - get_latest_version helper - **Blocked by**: REPO-004
- REPO-011 → `data-layer-expert` (2h) - TOML persistence testing - **Blocked by**: REPO-002

**Critical Path**: REPO-001 → REPO-002 → REPO-003 → REPO-006 (13h total)

### Task Delegation Commands

```
# Batch 1 (Launch immediately)
Task("python-backend-engineer", "REPO-001: Create VersionRepository base class with full CRUD interface. Define abstract methods: create_version(source_path, version_id, metadata), get_version(version_id), list_versions(), delete_version(version_id), version_exists(version_id). Include type hints, docstrings, and base constructor for artifact_path.")

# Batch 2 (After Batch 1 completes)
Task("python-backend-engineer", "REPO-002: Implement create_version method. Atomically snapshot files to versions/{version_id}/, write .version.toml metadata, update latest symlink. Handle edge cases: missing files, symlinks, empty artifacts. Use temp directory pattern for atomic moves.")
Task("python-backend-engineer", "REPO-009: Implement CollectionVersionRepository subclass for ~/.skillmeat/collection/artifacts/{artifact-name}/. Override storage path logic to use collection-level paths. Support all CRUD operations.")
Task("python-backend-engineer", "REPO-010: Implement ProjectVersionRepository subclass for ./.claude/skills/{artifact-name}/. Override storage path logic to use project-level paths. Support all CRUD operations.")

# Batch 3 (After Batch 2 completes)
Task("python-backend-engineer", "REPO-003: Implement get_version method. Load .version.toml from versions/{version_id}/, return VersionData object with all metadata. Handle missing versions gracefully with descriptive errors.")
Task("python-backend-engineer", "REPO-004: Implement list_versions method. Scan versions/ directory, sort chronologically (oldest to newest), return list of VersionData objects. Include filtering by creation timestamp range.")
Task("python-backend-engineer", "REPO-005: Implement delete_version method. Validate version exists and is not latest, remove version directory atomically, update latest symlink if needed. Include safety check - raise exception if latest.")

# Batch 4 (After Batch 3 completes)
Task("python-backend-engineer", "REPO-006: Implement get_version_content method. Load individual files from versions/{version_id}/, return file contents (text/binary). Support directory listing with recursive option.")
Task("python-backend-engineer", "REPO-007: Implement version_exists helper method. Check if versions/{version_id}/ exists and contains valid .version.toml. Return boolean.")
Task("python-backend-engineer", "REPO-008: Implement get_latest_version helper method. Read latest symlink, resolve to actual version_id, call get_version. Return None if no versions exist.")
Task("data-layer-expert", "REPO-011: Write comprehensive tests for TOML read/write cycle. Test metadata persistence, field validation, schema evolution. Verify .version.toml loads correctly after create_version and persists across sessions. >85% coverage.")
```

---

## Overview

Phase 2 implements the Repository Layer, which provides a consistent CRUD interface for version history operations at both collection and project levels. This layer sits on top of Phase 1's storage infrastructure and provides the foundation for all version management operations in subsequent phases.

**Why This Phase**: The repository pattern abstracts away storage implementation details and provides a clean interface for version management. Two implementations (Collection and Project) enable consistent version handling across different artifact scopes while supporting scope-specific behavior.

**Scope**:
- ✅ **IN SCOPE**: Base class design, all CRUD operations, both repository implementations, metadata persistence, performance optimization
- ❌ **OUT OF SCOPE**: Merge logic (Phase 5), comparison operations (Phase 4), API endpoints (Phase 7), UI components (Phase 8-9), retention policies (Phase 3)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | VersionRepository base class with full CRUD interface defined | ⏳ Pending |
| SC-2 | create_version atomically snapshots files and writes .version.toml | ⏳ Pending |
| SC-3 | get_version retrieves specific version with all metadata intact | ⏳ Pending |
| SC-4 | list_versions returns chronologically ordered results (oldest to newest) | ⏳ Pending |
| SC-5 | delete_version safely removes versions with validation checks | ⏳ Pending |
| SC-6 | get_version_content retrieves individual files from versions (text/binary) | ⏳ Pending |
| SC-7 | CollectionVersionRepository and ProjectVersionRepository fully functional | ⏳ Pending |
| SC-8 | All CRUD operations tested end-to-end with >85% coverage | ⏳ Pending |
| SC-9 | Version metadata persists and loads correctly across sessions | ⏳ Pending |
| SC-10 | List performance: 100 versions < 100ms | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| REPO-001 | Create VersionRepository base class | ⏳ | python-backend-engineer | None | 3h | CRUD interface, abstract methods |
| REPO-002 | Implement create_version | ⏳ | python-backend-engineer | REPO-001 | 5h | Atomic snapshot, metadata write |
| REPO-003 | Implement get_version | ⏳ | python-backend-engineer | REPO-002 | 2h | Load .version.toml, return VersionData |
| REPO-004 | Implement list_versions | ⏳ | python-backend-engineer | REPO-002 | 3h | Chronological sort, range filter |
| REPO-005 | Implement delete_version | ⏳ | python-backend-engineer | REPO-002 | 2h | Safety checks, atomic remove |
| REPO-006 | Implement get_version_content | ⏳ | python-backend-engineer | REPO-003 | 3h | File/directory retrieval, binary support |
| REPO-007 | Implement version_exists helper | ⏳ | python-backend-engineer | REPO-003 | 1h | Boolean check with validation |
| REPO-008 | Implement get_latest_version helper | ⏳ | python-backend-engineer | REPO-004 | 1h | Symlink resolution |
| REPO-009 | Implement CollectionVersionRepository | ⏳ | python-backend-engineer | REPO-001 | 3h | ~/.skillmeat/ paths |
| REPO-010 | Implement ProjectVersionRepository | ⏳ | python-backend-engineer | REPO-001 | 3h | ./.claude/ paths |
| REPO-011 | Test TOML persistence | ⏳ | data-layer-expert | REPO-002 | 2h | Read/write cycle, schema validation |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State (After Phase 1)

After Phase 1 completion, the storage infrastructure is in place:

**Directory Structure**:
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
  │   └── latest -> v2-def456/
  └── manifest.toml
```

**Version Metadata Schema (.version.toml)** (from Phase 1):
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

### Target Architecture (After Phase 2)

A clean repository abstraction with two implementations:

**VersionRepository Base Class**:
```python
class VersionRepository(ABC):
    """Abstract base for version CRUD operations."""

    def __init__(self, artifact_path: Path):
        self.artifact_path = artifact_path

    @abstractmethod
    def create_version(self, source_path: Path, version_id: str, metadata: dict) -> VersionData:
        """Create new version from source artifacts."""

    @abstractmethod
    def get_version(self, version_id: str) -> VersionData:
        """Retrieve specific version metadata."""

    @abstractmethod
    def list_versions(self) -> List[VersionData]:
        """List all versions in chronological order."""

    @abstractmethod
    def delete_version(self, version_id: str) -> None:
        """Delete version with safety checks."""

    @abstractmethod
    def version_exists(self, version_id: str) -> bool:
        """Check if version exists."""

    @abstractmethod
    def get_version_content(self, version_id: str, file_path: str = None) -> Union[str, bytes, dict]:
        """Retrieve file contents from version."""

    @abstractmethod
    def get_latest_version(self) -> Optional[VersionData]:
        """Get the latest version."""
```

**Two Implementations**:
- `CollectionVersionRepository` - Manages versions at ~/.skillmeat/collection/artifacts/{artifact-name}/
- `ProjectVersionRepository` - Manages versions at ./.claude/skills/{artifact-name}/

### Reference Patterns in SkillMeat

**Similar Repository Patterns**:
- `storage/snapshot_manager.py` - Snapshot creation and directory management
- `storage/manifest_manager.py` - TOML reading and writing
- `storage/lockfile_manager.py` - Version tracking with TOML

**Domain Models** (to reference):
- `models/artifact.py` - Artifact data structures
- `models/artifact_manifest.py` - Manifest schema

---

## Implementation Details

### Core Components

**1. VersionRepository Base Class (REPO-001)**

Define abstract interface for all version operations:

```python
# Location: core/storage/version_repository.py

class VersionData:
    """Data class for version metadata."""
    id: str
    timestamp: datetime
    hash: str
    source: str
    parent_versions: List[str]
    files_changed: List[str]
    summary: str

class VersionRepository(ABC):
    """Abstract base class for version management."""

    def __init__(self, artifact_path: Path):
        """Initialize with artifact root path."""
        self.artifact_path = artifact_path
        self.versions_dir = artifact_path / "versions"

    # All methods abstract with full type hints
```

**Key Design Decisions**:
- Use `artifact_path` as flexible root (supports both collection and project)
- TOML for metadata persistence (consistent with SkillMeat)
- Return `VersionData` objects for type safety
- Timestamps and sorting for chronological operations

**2. create_version Implementation (REPO-002)**

Atomically create a new version:

```python
def create_version(
    self,
    source_path: Path,
    version_id: str,
    metadata: dict
) -> VersionData:
    """
    Create version snapshot.

    Process:
    1. Validate source_path exists
    2. Create temp directory
    3. Copy all files from source_path to temp
    4. Write .version.toml with metadata
    5. Atomically move temp to versions/{version_id}/
    6. Update latest symlink
    """
```

**Edge Cases to Handle**:
- Missing source files (skip with warning)
- Broken symlinks in source (follow or skip)
- Empty artifacts (allow, document)
- Unicode filenames (handle cross-platform)
- Permission errors (raise descriptive exception)

**3. CRUD Operations (REPO-003 to REPO-008)**

```python
def get_version(self, version_id: str) -> VersionData:
    """Load .version.toml and return VersionData."""

def list_versions(self, start_date=None, end_date=None) -> List[VersionData]:
    """List all versions sorted oldest to newest."""

def delete_version(self, version_id: str) -> None:
    """Delete version, raise if it's latest."""

def get_version_content(self, version_id: str, file_path: str = None) -> Union[str, bytes, dict]:
    """Get file contents (text/binary) or directory listing."""

def version_exists(self, version_id: str) -> bool:
    """Check if version exists and is valid."""

def get_latest_version(self) -> Optional[VersionData]:
    """Resolve latest symlink and return version."""
```

**4. Repository Implementations (REPO-009, REPO-010)**

```python
# Location: core/storage/collection_version_repository.py
class CollectionVersionRepository(VersionRepository):
    """Version repository for ~/.skillmeat/collection/artifacts/"""

    def __init__(self, artifact_name: str):
        collection_path = Path.home() / ".skillmeat" / "collection" / "artifacts" / artifact_name
        super().__init__(collection_path)

# Location: core/storage/project_version_repository.py
class ProjectVersionRepository(VersionRepository):
    """Version repository for ./.claude/skills/"""

    def __init__(self, artifact_name: str, project_root: Path = None):
        if project_root is None:
            project_root = Path.cwd()
        project_path = project_root / ".claude" / "skills" / artifact_name
        super().__init__(project_path)
```

### Testing Strategy

**Unit Tests (REPO-011 and throughout)**:
- Test each CRUD operation individually
- Mock filesystem for isolation
- Test error conditions (missing versions, permissions)
- Verify TOML round-trip (write then read)

**Integration Tests**:
- Full lifecycle: create → get → list → delete
- Multiple versions with chronological ordering
- Latest symlink behavior
- Metadata persistence across sessions

**Performance Tests**:
- Benchmark list_versions with 100+ versions (target <100ms)
- Profile file copying in create_version
- Memory usage with large artifacts

**Fixtures**:
```python
@pytest.fixture
def temp_collection():
    """Temporary collection directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_artifact(temp_collection):
    """Create sample artifact with files."""
    artifact_path = temp_collection / "test-skill"
    artifact_path.mkdir()
    (artifact_path / "SKILL.md").write_text("# Test")
    return artifact_path
```

---

## Implementation Plan

### Phase 2 Workflow

1. **Batch 1**: Implement `VersionRepository` base class with all abstract methods
2. **Batch 2**: Implement `create_version`, then both repository subclasses
3. **Batch 3**: Implement retrieval operations (get, list, delete)
4. **Batch 4**: Implement helper methods and comprehensive testing

### File Structure (Target)

```
core/storage/
├── version_repository.py          # Base class + VersionData
├── collection_version_repository.py
├── project_version_repository.py
└── version_repository_utils.py    # Helpers if needed

tests/
└── test_version_repository.py     # All tests
```

### Dependencies

**Phase 1 Completion**: Requires utilities from Phase 1:
- Version ID generation
- File hashing
- Directory snapshot creation

**Standard SkillMeat Libraries**:
- `pathlib` for path operations
- `tomllib`/`tomli` for TOML
- `datetime` for timestamps
- `shutil` for atomic moves

---

## Quality Standards

### Code Quality

- **Type Hints**: All functions fully typed (mypy --strict)
- **Docstrings**: All public methods with examples
- **Error Handling**: Specific exceptions with context
- **Code Style**: Black formatted, flake8 compliant

### Testing Requirements

- **Minimum Coverage**: >85% for all repository classes
- **Branch Coverage**: All error paths tested
- **Cross-Platform**: Tests pass on Linux, macOS, Windows
- **Performance**: list_versions(100 items) < 100ms

### Documentation

- Docstrings include:
  - Clear purpose
  - Parameter descriptions with types
  - Return value description
  - Example usage
  - Exceptions that can be raised

---

## Blockers

### Active Blockers

_None at this time. Phase 1 completion is prerequisite._

### Potential Risks

1. **Atomic filesystem operations**: Cross-platform symlink/move reliability
   - Mitigation: Fallback strategy for Windows, comprehensive test coverage

2. **Performance with large artifacts**: Copying 100MB+ artifacts into versions
   - Mitigation: Benchmark early, consider hardlinks/COW as future optimization

3. **TOML schema evolution**: Adding fields in future phases
   - Mitigation: Design schema with version field, test migration path

4. **Symlink permissions**: Windows may require elevated privileges
   - Mitigation: Document requirement, provide fallback with regular directories

---

## Dependencies

### External Dependencies

- **Phase 1 Completion**: Version storage infrastructure, ID generation, file hashing utilities

### Internal Integration Points

- **Phase 3**: Will extend VersionData schema for retention policies
- **Phase 4**: Will use get_version for comparison operations
- **Phase 5**: Will use CRUD operations for merge logic
- **Phase 7**: API endpoints will wrap repository methods
- **Phase 8-9**: UI components will consume repository data

### Files to Create/Modify

**New Files**:
- `core/storage/version_repository.py`
- `core/storage/collection_version_repository.py`
- `core/storage/project_version_repository.py`
- `tests/test_version_repository.py`

**Files to Reference**:
- `storage/snapshot_manager.py` - Directory snapshot patterns
- `storage/manifest_manager.py` - TOML patterns
- `models/artifact.py` - Data structures

---

## Next Session Agenda

### Immediate Actions (Next Session)

1. [ ] REPO-001: Complete VersionRepository base class definition
2. [ ] REPO-002: Implement create_version with atomic file operations
3. [ ] REPO-009, REPO-010: Implement both repository subclasses

### Upcoming Critical Items

- Verify Phase 1 utilities (hashing, ID generation) are ready
- Set up test fixtures for temporary directories
- Establish performance benchmarks for list_versions

### Context for Continuing Agent

**Key Constraints**:
- Must use Phase 1's version storage infrastructure
- TOML format must match Phase 1 schema
- All operations must be atomic (no partial states)
- Cross-platform compatibility required

**Design Decisions Pending**:
- File permission handling in snapshots (preserve or reset?)
- Binary file handling in get_version_content
- Symlink behavior on Windows fallback

**Integration Points**:
- Phase 1 utilities: version_id_generator, compute_directory_hash, create_snapshot
- Existing patterns: snapshot_manager.py, manifest_manager.py

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Phase 1 Progress**: `.claude/progress/versioning-merge-system/phase-1-progress.md`
- **Storage Patterns**: `storage/snapshot_manager.py`, `storage/manifest_manager.py`
- **Reference Models**: `models/artifact.py`, `models/artifact_manifest.py`
