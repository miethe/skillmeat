---
type: progress
prd: "smart-import-discovery-v1"
phase: 1
title: "Data Layer & Service Foundation"
status: pending
started: null
updated: "2025-11-30T00:00:00Z"
completion: 0
total_tasks: 6
completed_tasks: 0

tasks:
  - id: "SID-001"
    title: "Create GitHub Metadata Extraction Service"
    description: "Create skillmeat/core/github_metadata.py with GitHubMetadataExtractor class"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "3h"
    story_points: 8
    acceptance_criteria:
      - "Parse user/repo/path format and HTTPS URLs"
      - "Fetch metadata from GitHub API and file content"
      - "Extract YAML frontmatter from SKILL.md/COMMAND.md"
      - "Cache responses with 1-hour TTL"
      - "Handle GitHub API rate limits and errors gracefully"

  - id: "SID-002"
    title: "Create Artifact Discovery Service"
    description: "Create skillmeat/core/discovery.py with ArtifactDiscoveryService class"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "3h"
    story_points: 8
    acceptance_criteria:
      - "Scan .claude/artifacts/ directory recursively"
      - "Detect artifact types (skill, command, agent, hook, mcp)"
      - "Extract metadata from frontmatter"
      - "Validate artifact structure"
      - "Complete scan <2 seconds for 50+ artifacts"

  - id: "SID-003"
    title: "Implement Metadata Cache"
    description: "Create skillmeat/core/cache.py with MetadataCache class"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "In-memory cache with configurable TTL (default 1 hour)"
      - "Track cache hits/misses"
      - "Thread-safe operations"
      - "Simple API: get(), set(), invalidate()"

  - id: "SID-004"
    title: "Create Discovery & Import Schemas"
    description: "Create/update skillmeat/api/schemas/ with new Pydantic schemas"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-001", "SID-002"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "DiscoveredArtifact, DiscoveryRequest, DiscoveryResult schemas"
      - "BulkImportArtifact, BulkImportRequest, BulkImportResult schemas"
      - "GitHubMetadata, MetadataFetchRequest, MetadataFetchResponse schemas"
      - "ArtifactParameters, ParameterUpdateRequest, ParameterUpdateResponse schemas"
      - "Pydantic v2 syntax with examples"

  - id: "SID-005"
    title: "Unit Tests: GitHub Metadata Service"
    description: "Create skillmeat/core/tests/test_github_metadata.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-001"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - ">80% code coverage"
      - "Test URL parsing (standard, HTTPS, with version)"
      - "Test metadata fetching (success, errors, rate limiting)"
      - "Test caching (hit, miss, TTL expiration)"
      - "Mock GitHub API calls"

  - id: "SID-006"
    title: "Unit Tests: Artifact Discovery Service"
    description: "Create skillmeat/core/tests/test_discovery_service.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-002"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - ">80% code coverage"
      - "Test discovery (success, empty, multiple artifacts)"
      - "Test type detection (all artifact types)"
      - "Test error handling (invalid artifacts, permissions)"
      - "Performance benchmark (<2 seconds for 50+ artifacts)"

parallelization:
  batch_1: ["SID-001", "SID-002", "SID-003"]
  batch_2: ["SID-004", "SID-005", "SID-006"]
  critical_path: ["SID-001", "SID-004"]
  estimated_total_time: "8h"

blockers: []

quality_gates:
  - "All services have >80% unit test coverage"
  - "Error handling for invalid artifacts, GitHub API errors, missing directories"
  - "Metadata cache correctly implements TTL"
  - "All schemas validated against existing artifact structures"
  - "Performance: discovery scan <2 seconds for 50+ artifacts"
---

# Phase 1: Data Layer & Service Foundation

**Plan:** `docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
**Status:** Pending
**Story Points:** 34 total

## Orchestration Quick Reference

**Batch 1** (Parallel - 4h estimated):
- SID-001 → `python-backend-engineer` (3h) - GitHub Metadata Service
- SID-002 → `python-backend-engineer` (3h) - Artifact Discovery Service
- SID-003 → `python-backend-engineer` (1h) - Metadata Cache

**Batch 2** (Sequential after Batch 1 - 4h estimated):
- SID-004 → `python-backend-engineer` (2h) - Discovery & Import Schemas
- SID-005 → `python-backend-engineer` (2h) - GitHub Metadata Tests
- SID-006 → `python-backend-engineer` (2h) - Discovery Service Tests

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "SID-001: Create GitHub Metadata Extraction Service

Create skillmeat/core/github_metadata.py with GitHubMetadataExtractor class.

Requirements:
- Parse user/repo/path format: 'anthropics/skills/canvas-design'
- Parse HTTPS URLs: 'https://github.com/user/repo/tree/main/path'
- Parse versioned sources: 'user/repo/path@v1.0.0' or '@latest' or '@abc1234'
- Fetch metadata from GitHub API (repo info, topics, license)
- Fetch file content (SKILL.md, README.md) and extract YAML frontmatter
- Use MetadataCache for caching with 1-hour TTL
- Handle rate limits gracefully (return cached data or error)
- Support optional GitHub token for higher rate limits

Classes needed:
- GitHubSourceSpec(BaseModel): owner, repo, path, version
- GitHubMetadata(BaseModel): title, description, author, license, topics, url, fetched_at
- GitHubMetadataExtractor: parse_github_url(), fetch_metadata(), _fetch_file_content(), _extract_frontmatter()

Use httpx for async HTTP requests. Follow existing patterns in skillmeat/sources/github.py.")

Task("python-backend-engineer", "SID-002: Create Artifact Discovery Service

Create skillmeat/core/discovery.py with ArtifactDiscoveryService class.

Requirements:
- Scan .claude/artifacts/ directory (or collection path) recursively
- Detect artifact types: skill, command, agent, hook, mcp
- Detection based on: SKILL.md, COMMAND.md, AGENT.md, etc.
- Extract metadata from YAML frontmatter in artifact files
- Validate artifact structure (required files present)
- Handle invalid artifacts gracefully (log warning, skip, continue)
- Return DiscoveryResult with artifacts list and errors list
- Performance: <2 seconds for 50+ artifacts

Classes needed:
- DiscoveryRequest(BaseModel): scan_path (optional, default to collection)
- DiscoveredArtifact(BaseModel): type, name, source, version, scope, tags, description, path, discovered_at
- DiscoveryResult(BaseModel): discovered_count, artifacts, errors, scan_duration_ms
- ArtifactDiscoveryService: discover_artifacts(), _extract_artifact_metadata(), _detect_artifact_type(), _validate_artifact()

Use pathlib for filesystem operations. Follow patterns in skillmeat/core/artifact.py.")

Task("python-backend-engineer", "SID-003: Implement Metadata Cache

Create skillmeat/core/cache.py with MetadataCache class.

Requirements:
- In-memory dictionary-based cache
- Configurable TTL (default 3600 seconds = 1 hour)
- Store timestamps with each entry for TTL checking
- Track cache hits/misses for analytics (counters)
- Thread-safe using threading.Lock
- Simple API: get(key), set(key, value), invalidate(key), clear(), stats()

Class needed:
- MetadataCache:
  - __init__(ttl_seconds: int = 3600)
  - get(key: str) -> Optional[Dict] - returns None if expired/missing
  - set(key: str, value: Dict) -> None - stores with timestamp
  - invalidate(key: str) -> None - removes entry
  - clear() -> None - removes all entries
  - stats() -> Dict[str, int] - returns hits, misses, size

Keep implementation simple - no external dependencies needed.")
```

**Batch 2:**
```
Task("python-backend-engineer", "SID-004: Create Discovery & Import Schemas

Create/update skillmeat/api/schemas/discovery.py with new Pydantic v2 schemas.

Schemas needed:

1. Discovery schemas:
   - DiscoveryRequest(BaseModel): scan_path: Optional[str] = None
   - DiscoveredArtifact(BaseModel): type, name, source, version, scope, tags, description, path, discovered_at
   - DiscoveryResult(BaseModel): discovered_count, artifacts: List[DiscoveredArtifact], errors: List[str], scan_duration_ms

2. GitHub metadata schemas:
   - GitHubSourceSpec(BaseModel): owner, repo, path, version (Optional, default 'latest')
   - GitHubMetadata(BaseModel): title, description, author, license, topics: List[str], url, fetched_at, source: str = 'auto-populated'
   - MetadataFetchRequest(BaseModel): source: str
   - MetadataFetchResponse(BaseModel): success: bool, metadata: Optional[GitHubMetadata], error: Optional[str]

3. Bulk import schemas:
   - BulkImportArtifact(BaseModel): source, artifact_type, name (Optional), description (Optional), author (Optional), tags (Optional, default []), scope (Optional, default 'user')
   - BulkImportRequest(BaseModel): artifacts: List[BulkImportArtifact], auto_resolve_conflicts: bool = False
   - ImportResult(BaseModel): artifact_id, success, message, error (Optional)
   - BulkImportResult(BaseModel): total_requested, total_imported, total_failed, results: List[ImportResult], duration_ms

4. Parameter update schemas:
   - ArtifactParameters(BaseModel): source (Optional), version (Optional), scope (Optional), tags (Optional), aliases (Optional)
   - ParameterUpdateRequest(BaseModel): parameters: ArtifactParameters
   - ParameterUpdateResponse(BaseModel): success, artifact_id, updated_fields: List[str], message

Use Pydantic v2 syntax. Add model_config with json_schema_extra examples.")

Task("python-backend-engineer", "SID-005: Unit Tests for GitHub Metadata Service

Create skillmeat/core/tests/test_github_metadata.py.

Test coverage requirements (>80%):

1. URL parsing tests:
   - test_parse_standard_format(): 'user/repo/path'
   - test_parse_https_url(): 'https://github.com/user/repo/tree/main/path'
   - test_parse_with_version(): 'user/repo/path@v1.0.0', '@latest', '@abc1234'
   - test_parse_invalid_format(): raises ValueError

2. Metadata fetching tests (mock httpx):
   - test_fetch_metadata_success(): mocked successful response
   - test_fetch_metadata_github_error(): 404, 500 errors
   - test_fetch_metadata_rate_limited(): 429 response
   - test_fetch_metadata_timeout(): network timeout
   - test_fetch_metadata_with_cache_hit(): returns cached data
   - test_fetch_metadata_with_cache_miss(): fetches fresh data

3. Frontmatter extraction tests:
   - test_extract_frontmatter_valid(): extracts YAML correctly
   - test_extract_frontmatter_missing(): handles missing frontmatter
   - test_extract_frontmatter_malformed(): handles invalid YAML

Use pytest fixtures, respx or httpx mocking, and pytest-cov for coverage.")

Task("python-backend-engineer", "SID-006: Unit Tests for Artifact Discovery Service

Create skillmeat/core/tests/test_discovery_service.py.

Test coverage requirements (>80%):

1. Discovery tests (use tmp_path fixture):
   - test_discover_artifacts_success(): finds all valid artifacts
   - test_discover_artifacts_empty_directory(): returns empty list
   - test_discover_multiple_types(): finds skills, commands, agents
   - test_discover_nested_directories(): finds nested artifacts

2. Type detection tests:
   - test_detect_skill_type(): detects SKILL.md
   - test_detect_command_type(): detects COMMAND.md
   - test_detect_agent_type(): detects AGENT.md
   - test_detect_unknown_type(): handles unknown types

3. Metadata extraction tests:
   - test_extract_metadata_complete(): all fields present
   - test_extract_metadata_partial(): some fields missing
   - test_extract_metadata_invalid(): handles corrupted files

4. Error handling tests:
   - test_invalid_artifact_skipped(): logs warning, continues
   - test_permission_error_handled(): handles permission denied
   - test_missing_required_files(): detects incomplete artifacts

5. Performance test:
   - test_discovery_performance(): <2 seconds for 50+ artifacts

Use pytest tmp_path for test directories and pytest-benchmark for performance.")
```

---

## Success Criteria

- [ ] All services have >80% unit test coverage
- [ ] Error handling for invalid artifacts, GitHub API errors, missing directories
- [ ] Metadata cache correctly implements TTL
- [ ] All schemas validated against existing artifact structures
- [ ] Performance: discovery scan <2 seconds for 50+ artifacts

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
