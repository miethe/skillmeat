---
type: progress
prd: "smart-import-discovery-v1"
phase: 2
title: "API Endpoints & Integration"
status: pending
started: null
updated: "2025-11-30T00:00:00Z"
completion: 0
total_tasks: 6
completed_tasks: 0

tasks:
  - id: "SID-007"
    title: "Implement Discovery Endpoint"
    description: "Add POST /api/v1/artifacts/discover endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-002", "SID-004"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "POST /discover returns discovered artifacts"
      - "Validates .claude/ path"
      - "Proper HTTP status codes (200, 400, 401, 500)"
      - "Logs discovery results"

  - id: "SID-008"
    title: "Implement Bulk Import Endpoint"
    description: "Add POST /api/v1/artifacts/discover/import endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-002", "SID-003", "SID-004"]
    estimated_time: "3h"
    story_points: 8
    acceptance_criteria:
      - "POST /discover/import validates batch"
      - "Imports atomically (all-or-nothing)"
      - "Returns per-artifact results"
      - "Updates manifest and lock file"

  - id: "SID-009"
    title: "Implement GitHub Metadata Endpoint"
    description: "Add GET /api/v1/artifacts/metadata/github endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-001", "SID-004"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "GET /metadata/github fetches metadata"
      - "Uses cache for repeated requests"
      - "Validates GitHub URL format"
      - "Handles errors gracefully"

  - id: "SID-010"
    title: "Implement Parameter Edit Endpoint"
    description: "Add PUT /api/v1/artifacts/{artifact_id}/parameters endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-004"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "PUT /{id}/parameters updates source/version/tags/scope"
      - "Validates input parameters"
      - "Atomic manifest/lock file update"
      - "Returns clear error messages"

  - id: "SID-011"
    title: "Integration Tests: API Endpoints"
    description: "Create skillmeat/api/tests/test_discovery_endpoints.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - ">70% endpoint coverage"
      - "Test all HTTP status codes"
      - "Test request/response validation"
      - "Test error scenarios"

  - id: "SID-012"
    title: "Error Handling & Validation"
    description: "Implement consistent error handling across all layers"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "Consistent error response format"
      - "User-friendly error messages"
      - "Proper HTTP status codes"
      - "Validation consistency: frontend mirrors backend"

parallelization:
  batch_1: ["SID-007", "SID-009", "SID-010"]
  batch_2: ["SID-008"]
  batch_3: ["SID-011", "SID-012"]
  critical_path: ["SID-007", "SID-008", "SID-011"]
  estimated_total_time: "9h"

blockers: []

quality_gates:
  - "All 4 endpoints implemented and tested"
  - "Atomic operations verified for bulk import"
  - "Error responses follow consistent format"
  - "GitHub rate limiting handled gracefully"
  - "Integration tests >70% coverage"
  - "Performance: bulk import <3 seconds for 20 artifacts"
---

# Phase 2: API Endpoints & Integration

**Plan:** `docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
**Status:** Pending (depends on Phase 1)
**Story Points:** 33 total

## Orchestration Quick Reference

**Batch 1** (Parallel after Phase 1 - 4h estimated):
- SID-007 → `python-backend-engineer` (2h) - Discovery Endpoint
- SID-009 → `python-backend-engineer` (2h) - GitHub Metadata Endpoint
- SID-010 → `python-backend-engineer` (2h) - Parameter Edit Endpoint

**Batch 2** (Sequential - 3h estimated):
- SID-008 → `python-backend-engineer` (3h) - Bulk Import Endpoint

**Batch 3** (Parallel after Batch 2 - 4h estimated):
- SID-011 → `python-backend-engineer` (2h) - Integration Tests
- SID-012 → `python-backend-engineer` (2h) - Error Handling

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "SID-007: Implement Discovery Endpoint

Add to skillmeat/api/routers/artifacts.py:

@router.post('/discover', response_model=DiscoveryResult)
async def discover_artifacts(
    request: DiscoveryRequest,
    artifact_mgr: ArtifactManagerDep
) -> DiscoveryResult:
    '''Scan .claude/ directory for existing artifacts.'''

Implementation:
1. Import ArtifactDiscoveryService from skillmeat.core.discovery
2. Get collection_path from artifact_mgr
3. Create service instance with collection path
4. Call discover_artifacts() method
5. Return DiscoveryResult
6. Log discovery results (count, duration)

Error handling:
- 200: Discovery completed (check errors list for per-artifact issues)
- 400: Invalid scan_path parameter
- 401: Unauthorized
- 500: Scan failed unexpectedly

Follow existing endpoint patterns in artifacts.py router.")

Task("python-backend-engineer", "SID-009: Implement GitHub Metadata Endpoint

Add to skillmeat/api/routers/artifacts.py:

@router.get('/metadata/github', response_model=MetadataFetchResponse)
async def fetch_github_metadata(
    source: str = Query(..., description='GitHub source: user/repo/path'),
    artifact_mgr: ArtifactManagerDep = None
) -> MetadataFetchResponse:
    '''Fetch metadata from GitHub for given source.'''

Implementation:
1. Import GitHubMetadataExtractor from skillmeat.core.github_metadata
2. Import MetadataCache from skillmeat.core.cache
3. Get or create cache instance (store in app.state)
4. Create extractor with cache
5. Parse and validate source format
6. Call fetch_metadata(source)
7. Return MetadataFetchResponse

Error handling:
- 200: Metadata fetched (check success field)
- 400: Invalid GitHub source format
- 401: Unauthorized
- 404: Repository not found
- 429: GitHub rate limit exceeded
- 500: Fetch failed

Consider storing cache in app.state.metadata_cache for reuse across requests.")

Task("python-backend-engineer", "SID-010: Implement Parameter Edit Endpoint

Add to skillmeat/api/routers/artifacts.py:

@router.put('/{artifact_id}/parameters', response_model=ParameterUpdateResponse)
async def update_artifact_parameters(
    artifact_id: str,
    request: ParameterUpdateRequest,
    artifact_mgr: ArtifactManagerDep
) -> ParameterUpdateResponse:
    '''Update artifact parameters after import.'''

Implementation:
1. Parse artifact_id (format: type:name or just name)
2. Find artifact in collection using artifact_mgr
3. Validate new parameters:
   - source: valid GitHub format
   - version: valid format (@latest, @v1.0.0, @sha)
   - scope: 'user' or 'local'
   - tags: list of non-empty strings
4. Update artifact metadata using artifact_mgr
5. Return ParameterUpdateResponse with updated_fields list

Error handling:
- 200: Parameters updated successfully
- 400: Invalid parameters
- 401: Unauthorized
- 404: Artifact not found
- 422: Parameter validation failed
- 500: Update failed

Use existing artifact_mgr.update_artifact() method if available.")
```

**Batch 2:**
```
Task("python-backend-engineer", "SID-008: Implement Bulk Import Endpoint

Add to skillmeat/api/routers/artifacts.py:

@router.post('/discover/import', response_model=BulkImportResult)
async def bulk_import_artifacts(
    request: BulkImportRequest,
    artifact_mgr: ArtifactManagerDep
) -> BulkImportResult:
    '''Bulk import multiple artifacts with atomic transaction.'''

Implementation:
1. Create ArtifactImporter service (new class in skillmeat/core/importer.py):
   - __init__(artifact_manager): store reference
   - bulk_import(request: BulkImportRequest) -> BulkImportResult
   - _validate_batch(): validate all artifacts before import
   - _check_duplicate(source): check if already imported
   - _atomic_import(): import all or rollback on error

2. Validation phase:
   - Check all sources are valid format
   - Check for duplicates in collection
   - Validate artifact_type values
   - Return validation errors before importing

3. Import phase (atomic):
   - Start transaction (backup manifest/lockfile)
   - For each artifact:
     - Resolve source to files
     - Add to collection using artifact_mgr.add_artifact()
     - Track result (success/failure)
   - If any failure: rollback all
   - Commit changes (update manifest/lockfile)

4. Return BulkImportResult:
   - total_requested: len(request.artifacts)
   - total_imported: count of successes
   - total_failed: count of failures
   - results: per-artifact status
   - duration_ms: timing

Error handling:
- 200: Import completed (check per-artifact status)
- 400: Validation failed (all artifacts rejected)
- 401: Unauthorized
- 422: Invalid artifact format
- 500: Import failed unexpectedly

Create skillmeat/core/importer.py for ArtifactImporter class.")
```

**Batch 3:**
```
Task("python-backend-engineer", "SID-011: Integration Tests for API Endpoints

Create skillmeat/api/tests/test_discovery_endpoints.py.

Test coverage requirements (>70%):

1. Discovery endpoint tests:
   - test_discover_success(): finds artifacts in test collection
   - test_discover_empty(): handles empty directory
   - test_discover_invalid_path(): 400 response
   - test_discover_unauthorized(): 401 without token

2. Bulk import endpoint tests:
   - test_bulk_import_success(): imports multiple artifacts
   - test_bulk_import_partial_failure(): atomic rollback
   - test_bulk_import_duplicate(): handles existing artifacts
   - test_bulk_import_invalid_format(): 422 response

3. GitHub metadata endpoint tests:
   - test_metadata_fetch_success(): returns metadata (mocked)
   - test_metadata_fetch_invalid_source(): 400 response
   - test_metadata_fetch_not_found(): 404 response
   - test_metadata_fetch_rate_limited(): 429 response

4. Parameter update endpoint tests:
   - test_parameter_update_success(): updates artifact
   - test_parameter_update_not_found(): 404 response
   - test_parameter_update_invalid(): 422 response

Use TestClient, pytest fixtures, and mock external services.")

Task("python-backend-engineer", "SID-012: Error Handling & Validation Consistency

Review and implement consistent error handling across all layers.

Implementation:

1. Create error response models in skillmeat/api/schemas/errors.py:
   - ErrorDetail(BaseModel): code, message, field (Optional)
   - ErrorResponse(BaseModel): error: str, details: List[ErrorDetail], request_id (Optional)

2. Create validation helpers in skillmeat/core/validation.py:
   - validate_github_source(source: str) -> GitHubSourceSpec
   - validate_artifact_type(type_str: str) -> ArtifactType
   - validate_scope(scope: str) -> str ('user' or 'local')
   - validate_version(version: str) -> str

3. Update all endpoints to use consistent error format:
   - Use HTTPException with ErrorResponse-compatible body
   - Include helpful error messages
   - Map exceptions to appropriate HTTP codes

4. Add validation to request handlers:
   - Validate early (before business logic)
   - Return all validation errors at once (not one at a time)
   - Mirror validation rules in frontend later

Error code mapping:
- ValueError, ValidationError → 400 Bad Request
- NotFoundError → 404 Not Found
- DuplicateError → 409 Conflict
- RateLimitError → 429 Too Many Requests
- Exception → 500 Internal Server Error")
```

---

## Success Criteria

- [ ] All 4 endpoints implemented and tested
- [ ] Atomic operations verified for bulk import
- [ ] Error responses follow consistent format
- [ ] GitHub rate limiting handled gracefully
- [ ] Integration tests >70% coverage
- [ ] Performance: bulk import <3 seconds for 20 artifacts

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
