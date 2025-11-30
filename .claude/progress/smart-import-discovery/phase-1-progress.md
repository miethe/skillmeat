---
# === PROGRESS TRACKING: Smart Import & Discovery - Phase 1 ===
# Data Layer & Service Foundation

# Metadata: Identification and Classification
type: progress
prd: "smart-import-discovery"
phase: 1
title: "Data Layer & Service Foundation"
status: "planning"
started: "2025-11-30"
completed: null

# Overall Progress: Status and Estimates
overall_progress: 0
completion_estimate: "on-track"

# Task Counts: Machine-readable task state
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

# Ownership: Primary and secondary agents
owners: ["python-backend-engineer"]
contributors: ["backend-architect"]

# === ORCHESTRATION QUICK REFERENCE ===
# For lead-architect and orchestration agents: All tasks with assignments and dependencies
tasks:
  - id: "TASK-1.1"
    description: "Create GitHub Metadata Extraction Service - GitHubMetadataExtractor class with URL parsing (user/repo/path[@version]), GitHub API fetch, metadata extraction from frontmatter, and in-memory caching with 1-hour TTL"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "8h"
    priority: "high"

  - id: "TASK-1.2"
    description: "Create Artifact Discovery Service - ArtifactDiscoveryService class that scans .claude/ directory, detects artifact types (skill/command/agent/hook/mcp), extracts basic metadata from frontmatter, and validates artifact structure"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "8h"
    priority: "high"

  - id: "TASK-1.3"
    description: "Implement Metadata Cache - In-memory cache implementation with 1-hour TTL, thread-safe operations, cache hit/miss tracking, and invalidation support"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3h"
    priority: "medium"

  - id: "TASK-1.4"
    description: "Create Discovery & Import Schemas - Define Pydantic schemas for DiscoveredArtifact, DiscoveryResult, BulkImportRequest, GitHubMetadataResponse, and validation logic"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TASK-1.1", "TASK-1.2"]
    estimated_effort: "5h"
    priority: "high"

  - id: "TASK-1.5"
    description: "Unit Tests: GitHub Metadata Service - Test URL parsing (user/repo/path formats), API calls, metadata extraction, caching behavior, error scenarios (404, rate limit, invalid URLs). Target >80% coverage"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "5h"
    priority: "high"

  - id: "TASK-1.6"
    description: "Unit Tests: Artifact Discovery Service - Test directory scanning, artifact type detection, metadata extraction from frontmatter, error handling (missing files, invalid artifacts). Target >80% coverage"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "5h"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2", "TASK-1.3"]
  batch_2: ["TASK-1.4"]
  batch_3: ["TASK-1.5", "TASK-1.6"]
  critical_path: ["TASK-1.1", "TASK-1.4"]
  estimated_total_time: "3d"

# Critical Blockers: For immediate visibility
blockers: []

# Success Criteria: Acceptance conditions for phase completion
success_criteria:
  - id: "SC-1"
    description: "All services have >80% unit test coverage"
    status: "pending"
  - id: "SC-2"
    description: "Error handling validates invalid artifacts, GitHub API errors, missing directories"
    status: "pending"
  - id: "SC-3"
    description: "Metadata cache correctly implements TTL and thread-safety"
    status: "pending"
  - id: "SC-4"
    description: "All schemas validated against existing artifact structures"
    status: "pending"
  - id: "SC-5"
    description: "Performance: discovery scan completes in <2 seconds for 50+ artifacts"
    status: "pending"

# Files Modified: What's being changed in this phase
files_modified:
  - "skillmeat/core/discovery.py"
  - "skillmeat/core/github_metadata.py"
  - "skillmeat/core/cache.py"
  - "skillmeat/api/schemas/discovery.py"
  - "tests/test_github_metadata.py"
  - "tests/test_discovery.py"
---

# smart-import-discovery - Phase 1: Data Layer & Service Foundation

**Phase**: 1 of 5
**Status**: ⏳ Planning (0% complete)
**Duration**: Started 2025-11-30, estimated completion 2025-12-02
**Owner**: python-backend-engineer
**Contributors**: backend-architect

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- TASK-1.1 → `python-backend-engineer` (8h) - GitHub Metadata Extraction Service
- TASK-1.2 → `python-backend-engineer` (8h) - Artifact Discovery Service
- TASK-1.3 → `python-backend-engineer` (3h) - Metadata Cache

**Batch 2** (Sequential - Depends on Batch 1):
- TASK-1.4 → `backend-architect` (5h) - Discovery & Import Schemas - **Blocked by**: TASK-1.1, TASK-1.2

**Batch 3** (Parallel - Depends on Batch 1 completion):
- TASK-1.5 → `python-backend-engineer` (5h) - Unit Tests: GitHub Metadata - **Blocked by**: TASK-1.1
- TASK-1.6 → `python-backend-engineer` (5h) - Unit Tests: Artifact Discovery - **Blocked by**: TASK-1.2

**Critical Path**: TASK-1.1 → TASK-1.4 (13h total)

### Task Delegation Commands

```python
# Batch 1 (Launch in parallel)
Task("python-backend-engineer", "TASK-1.1: Create GitHub Metadata Extraction Service - GitHubMetadataExtractor class with URL parsing (user/repo/path[@version]), GitHub API fetch, metadata extraction from frontmatter, and in-memory caching. Location: skillmeat/core/github_metadata.py")

Task("python-backend-engineer", "TASK-1.2: Create Artifact Discovery Service - ArtifactDiscoveryService class that scans .claude/ directory, detects artifact types (skill/command/agent/hook/mcp), extracts basic metadata from frontmatter. Location: skillmeat/core/discovery.py")

Task("python-backend-engineer", "TASK-1.3: Implement Metadata Cache - In-memory cache with 1-hour TTL, thread-safe operations, cache hit/miss tracking. Location: skillmeat/core/cache.py")

# Batch 2 (After Batch 1 completes)
Task("backend-architect", "TASK-1.4: Create Discovery & Import Schemas - Define Pydantic schemas for DiscoveredArtifact, DiscoveryResult, BulkImportRequest, GitHubMetadataResponse. Location: skillmeat/api/schemas/discovery.py")

# Batch 3 (After TASK-1.1 and TASK-1.2 complete)
Task("python-backend-engineer", "TASK-1.5: Unit Tests: GitHub Metadata Service - Test URL parsing, API calls, metadata extraction, caching, error scenarios. Target >80% coverage. Location: tests/test_github_metadata.py")

Task("python-backend-engineer", "TASK-1.6: Unit Tests: Artifact Discovery Service - Test directory scanning, artifact detection, metadata extraction, error handling. Target >80% coverage. Location: tests/test_discovery.py")
```

---

## Overview

Phase 1 establishes the foundational data layer and service components for Smart Import & Discovery. This phase implements the core business logic for scanning `.claude/` directories, extracting artifact metadata, and fetching GitHub metadata to enable auto-population.

**Why This Phase**: Without these foundational services, we cannot implement the API endpoints or UI components in subsequent phases. This phase delivers the core capabilities that all other phases depend on.

**Scope**:
- **IN SCOPE**: Service layer implementation, schema definitions, unit tests, in-memory caching
- **OUT OF SCOPE**: API endpoints (Phase 2), UI components (Phase 3), database persistence (future enhancement)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All services have >80% unit test coverage | ⏳ Pending |
| SC-2 | Error handling validates invalid artifacts, GitHub API errors, missing directories | ⏳ Pending |
| SC-3 | Metadata cache correctly implements TTL and thread-safety | ⏳ Pending |
| SC-4 | All schemas validated against existing artifact structures | ⏳ Pending |
| SC-5 | Performance: discovery scan completes in <2 seconds for 50+ artifacts | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| TASK-1.1 | GitHub Metadata Extraction Service | ⏳ | python-backend-engineer | None | 8h | Parse user/repo/path, fetch metadata, cache responses |
| TASK-1.2 | Artifact Discovery Service | ⏳ | python-backend-engineer | None | 8h | Scan .claude/, detect types, extract metadata |
| TASK-1.3 | Metadata Cache | ⏳ | python-backend-engineer | None | 3h | In-memory cache with TTL, thread-safe |
| TASK-1.4 | Discovery & Import Schemas | ⏳ | backend-architect | TASK-1.1, TASK-1.2 | 5h | Pydantic schemas for all data structures |
| TASK-1.5 | Unit Tests: GitHub Metadata | ⏳ | python-backend-engineer | TASK-1.1 | 5h | >80% coverage, all error scenarios |
| TASK-1.6 | Unit Tests: Artifact Discovery | ⏳ | python-backend-engineer | TASK-1.2 | 5h | >80% coverage, validation tests |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State

SkillMeat currently has:
- **Artifact Manager** (`skillmeat/core/artifact.py`) - Handles artifact installation and management
- **Manifest System** - TOML-based manifest and lock file management
- **GitHub Integration** - Basic GitHub source parsing and fetching
- **Filesystem Storage** - Collection stored in `~/.skillmeat/collection/`

**Key Files**:
- `skillmeat/core/artifact.py` - ArtifactManager class with install/update/remove methods
- `skillmeat/storage/manifest.py` - ManifestManager for TOML manifest handling
- `skillmeat/sources/github.py` - GitHubSource class for artifact fetching

### Reference Patterns

**Similar Features**:
- **Artifact Source Parsing** in `skillmeat/sources/github.py` shows the current `user/repo/path[@version]` format parsing
- **Metadata Extraction** in `skillmeat/core/artifact.py` demonstrates YAML frontmatter parsing from SKILL.md files
- **Caching Strategy** should follow Python's `functools.lru_cache` pattern with custom TTL implementation

### Phase 1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Service Layer (New)                           │
│  ┌────────────────────┐  ┌────────────────────────────────┐    │
│  │ ArtifactDiscovery  │  │ GitHubMetadataExtractor        │    │
│  │ - scan .claude/    │  │ - parse URLs                   │    │
│  │ - detect types     │  │ - fetch GitHub metadata        │    │
│  │ - extract metadata │  │ - extract frontmatter          │    │
│  │ - validate         │  │ - normalize metadata           │    │
│  └────────────────────┘  └────────────────────────────────┘    │
│           │                         │                            │
│           │                         │                            │
│  ┌────────┴─────────────────────────┴───────────────┐           │
│  │         MetadataCache (In-Memory)                │           │
│  │  - 1-hour TTL                                    │           │
│  │  - Thread-safe operations                       │           │
│  │  - Cache hit/miss tracking                      │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│           Repository & Data Layer (Existing)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ~/.skillmeat/collection/                               │  │
│  │ ├── artifacts/                                          │  │
│  │ │   ├── skills/                                        │  │
│  │ │   │   └── [artifact_name]/                           │  │
│  │ │   │       ├── SKILL.md (frontmatter with metadata) │  │
│  │ │   │       └── ...                                    │  │
│  │ ├── manifest.toml                                      │  │
│  │ └── manifest-lock.toml                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Service 1: GitHubMetadataExtractor

**Location**: `skillmeat/core/github_metadata.py`

**Class Structure**:
```python
class GitHubMetadataExtractor:
    def __init__(self, cache: MetadataCache, token: Optional[str] = None):
        self.cache = cache
        self.token = token
        self.base_url = "https://api.github.com"

    def parse_github_url(self, url: str) -> GitHubSourceSpec:
        """Parse user/repo/path[@version] format"""

    def fetch_metadata(self, source: str) -> GitHubMetadata:
        """Fetch metadata from GitHub (with caching)"""

    def _fetch_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch file from GitHub API"""

    def _extract_frontmatter(self, content: str) -> Dict:
        """Extract YAML frontmatter from markdown"""

    def _fetch_repo_metadata(self, owner: str, repo: str) -> Dict:
        """Fetch repo metadata from GitHub API"""
```

**URL Formats Supported**:
- `user/repo/path` → defaults to latest
- `user/repo/path@v1.0.0` → specific version tag
- `user/repo/path@abc1234` → specific commit SHA
- `https://github.com/user/repo/tree/main/path` → GitHub URL

### Service 2: ArtifactDiscoveryService

**Location**: `skillmeat/core/discovery.py`

**Class Structure**:
```python
class ArtifactDiscoveryService:
    def __init__(self, collection_path: Path):
        self.collection_path = collection_path
        self.supported_types = ["skill", "command", "agent", "hook", "mcp"]

    def discover_artifacts(self) -> DiscoveryResult:
        """Scan .claude/artifacts/ and discover all artifacts"""

    def _extract_artifact_metadata(self, artifact_path: Path) -> Dict:
        """Extract metadata from artifact frontmatter"""

    def _detect_artifact_type(self, artifact_path: Path) -> str:
        """Detect type from directory structure"""

    def _validate_artifact(self, artifact_path: Path) -> bool:
        """Validate artifact structure"""
```

**Detection Logic**:
- Skills: Check for `SKILL.md` file
- Commands: Check for `COMMAND.md` file
- Agents: Check for `AGENT.md` file
- MCPs: Check for `mcp.json` or `package.json` with MCP metadata

### Service 3: MetadataCache

**Location**: `skillmeat/core/cache.py`

**Class Structure**:
```python
class MetadataCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._cache = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict]:
        """Get cached metadata if fresh"""

    def set(self, key: str, value: Dict) -> None:
        """Cache metadata with TTL"""

    def invalidate(self, key: str) -> None:
        """Remove cached entry"""

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry has expired"""
```

### Pydantic Schemas

**Location**: `skillmeat/api/schemas/discovery.py`

```python
class DiscoveredArtifact(BaseModel):
    type: str
    name: str
    source: Optional[str]
    version: Optional[str]
    scope: Optional[str]
    tags: Optional[List[str]]
    description: Optional[str]
    path: str
    discovered_at: datetime

class DiscoveryResult(BaseModel):
    discovered_count: int
    artifacts: List[DiscoveredArtifact]
    errors: List[str]
    scan_duration_ms: float

class GitHubSourceSpec(BaseModel):
    owner: str
    repo: str
    path: str
    version: Optional[str] = "latest"

class GitHubMetadata(BaseModel):
    title: Optional[str]
    description: Optional[str]
    author: Optional[str]
    license: Optional[str]
    topics: List[str] = []
    url: str
    fetched_at: datetime
    source: str = "auto-populated"
```

---

## Known Gotchas

### GitHub Rate Limiting
- **Issue**: GitHub API has rate limits (60/hour unauthenticated, 5000/hour authenticated)
- **Solution**:
  - Implement caching with 1-hour TTL to reduce API calls
  - Use GitHub token if available (from `skillmeat config get github-token`)
  - Gracefully handle 429 responses with clear error messages

### Artifact Type Detection
- **Issue**: Some artifacts may not have clear type indicators
- **Solution**:
  - Check for specific metadata files in priority order (SKILL.md > COMMAND.md > AGENT.md)
  - Fall back to directory structure analysis
  - Log warnings for ambiguous artifacts

### Thread Safety
- **Issue**: Cache may be accessed concurrently from multiple requests
- **Solution**:
  - Use `threading.Lock()` for cache operations
  - Test concurrent access in unit tests

### Python Version Compatibility
- **Issue**: Must support Python 3.9+
- **Solution**:
  - Use `tomli` for Python <3.11, `tomllib` for 3.11+
  - Test on all supported Python versions (3.9, 3.10, 3.11, 3.12)

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | GitHubMetadataExtractor | >80% | ⏳ TASK-1.5 |
| Unit | ArtifactDiscoveryService | >80% | ⏳ TASK-1.6 |
| Unit | MetadataCache | >80% | ⏳ TASK-1.3 |
| Integration | Service composition | Core flows | Phase 2 |
| Performance | Discovery scan | <2s for 50+ artifacts | ⏳ SC-5 |

### Test Scenarios to Cover

**TASK-1.5 (GitHub Metadata Tests)**:
- ✓ Parse valid `user/repo/path` format
- ✓ Parse with version tags (`@v1.0.0`)
- ✓ Parse with commit SHAs (`@abc1234`)
- ✓ Parse GitHub URLs
- ✓ Handle invalid URLs gracefully
- ✓ Fetch and extract frontmatter
- ✓ Cache hits and misses
- ✓ Cache TTL expiration
- ✓ GitHub API 404 errors
- ✓ GitHub API rate limit (429) errors
- ✓ Network timeouts

**TASK-1.6 (Discovery Tests)**:
- ✓ Scan directory with multiple artifact types
- ✓ Detect skills, commands, agents
- ✓ Extract metadata from frontmatter
- ✓ Handle missing metadata files
- ✓ Handle corrupted YAML frontmatter
- ✓ Handle missing directories
- ✓ Validate artifact structure
- ✓ Performance: scan 50+ artifacts in <2s

---

## Dependencies

### External Dependencies

**Python Packages** (add to `pyproject.toml`):
- `pyyaml` - YAML frontmatter parsing (already present)
- `requests` - HTTP requests to GitHub API (already present)
- `pydantic` - Schema validation (already present)

**GitHub API**:
- Optional GitHub token for rate limit increase
- Handles public repository access without auth

### Internal Integration Points

- **ArtifactManager** (`skillmeat/core/artifact.py`) - Will integrate with discovery results in Phase 2
- **ManifestManager** (`skillmeat/storage/manifest.py`) - Will update manifest with discovered artifacts
- **GitHubSource** (`skillmeat/sources/github.py`) - Reuse URL parsing logic, extend with metadata extraction

---

## Blockers

### Active Blockers

No active blockers at Phase 1 start.

### Resolved Blockers

None yet.

---

## Next Session Agenda

### Immediate Actions (Next Session)
1. [ ] Launch Batch 1 tasks in parallel (TASK-1.1, TASK-1.2, TASK-1.3)
2. [ ] Verify GitHub API token configuration for testing
3. [ ] Create test fixtures for artifact structures

### Upcoming Critical Items

- **Week of 2025-12-02**: Phase 1 completion, begin Phase 2 API endpoint implementation
- **Dependency update**: Schema definitions (TASK-1.4) must complete before Phase 2 can begin

### Context for Continuing Agent

**Phase 1 Goal**: Build foundational services that enable artifact discovery and GitHub metadata extraction. These services will be consumed by API endpoints in Phase 2.

**Key Decisions**:
- In-memory caching (not Redis) for MVP simplicity
- Filesystem-based discovery (no database schema changes)
- Thread-safe cache implementation for concurrent API requests
- 1-hour TTL balances freshness vs. API rate limits

**Next Phase Preview**: Phase 2 will create FastAPI endpoints that consume these services and expose them to the frontend.

---

## Session Notes

### 2025-11-30

**Phase 1 Initiated**:
- Progress tracking file created with schema-compliant YAML frontmatter
- All 6 tasks defined with proper TASK-1.X format
- Parallelization strategy computed: 3 batches, 3-day estimated completion
- Success criteria defined with measurable acceptance conditions

**Ready for Execution**:
- Batch 1 (3 parallel tasks) ready to launch
- Task delegation commands prepared in Orchestration Quick Reference
- All file locations and implementation details documented

**Next Session**:
- Execute Batch 1 task delegation
- Begin GitHubMetadataExtractor implementation

---

## Additional Resources

- **PRD**: `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
- **Architecture Reference**: `/skillmeat/CLAUDE.md` (SkillMeat architecture overview)
- **Schema Reference**: `.claude/skills/artifact-tracking/schemas/progress.schema.yaml`
