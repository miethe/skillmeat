---
type: progress
prd: "smart-import-discovery"
phase: 2
title: "API Endpoints & Integration"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: ["backend-architect"]

tasks:
  - id: "SID-007"
    description: "Implement Discovery Endpoint - POST /discover returns discovered artifacts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "5h"
    priority: "high"

  - id: "SID-008"
    description: "Implement Bulk Import Endpoint - POST /discover/import validates batch, imports atomically"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1 day"
    priority: "high"

  - id: "SID-009"
    description: "Implement GitHub Metadata Endpoint - GET /metadata/github fetches metadata, caches response"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "5h"
    priority: "high"

  - id: "SID-010"
    description: "Implement Parameter Edit Endpoint - PUT /{id}/parameters updates source/version/tags/scope"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: []
    estimated_effort: "5h"
    priority: "high"

  - id: "SID-011"
    description: "Integration Tests: API Endpoints - Test all endpoints, error scenarios, validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_effort: "5h"
    priority: "medium"

  - id: "SID-012"
    description: "Error Handling & Validation - Consistent error codes, user-friendly messages"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_effort: "5h"
    priority: "medium"

parallelization:
  batch_1: ["SID-007", "SID-008", "SID-009", "SID-010"]
  batch_2: ["SID-011", "SID-012"]
  critical_path: ["SID-008", "SID-011"]
  estimated_total_time: "2.5 days"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "All 4 endpoints implemented and tested"
    status: "pending"
  - id: "SC-2"
    description: "Atomic operations verified for bulk import"
    status: "pending"
  - id: "SC-3"
    description: "Error responses follow consistent format"
    status: "pending"
  - id: "SC-4"
    description: "GitHub rate limiting handled gracefully"
    status: "pending"
  - id: "SC-5"
    description: "Integration tests >70% coverage"
    status: "pending"
  - id: "SC-6"
    description: "Performance: bulk import <3 seconds for 20 artifacts"
    status: "pending"

files_modified:
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/api/schemas/discovery.py"
  - "tests/integration/test_discovery_api.py"
---

# smart-import-discovery - Phase 2: API Endpoints & Integration

**Phase**: 2 of 5
**Status**: ⏳ Planning (0% complete)
**Duration**: Not started, estimated 1 week
**Owner**: python-backend-engineer
**Contributors**: backend-architect

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- SID-007 → `python-backend-engineer` (5h) - Discovery Endpoint
- SID-008 → `python-backend-engineer` (1 day) - Bulk Import Endpoint
- SID-009 → `python-backend-engineer` (5h) - GitHub Metadata Endpoint
- SID-010 → `backend-architect` (5h) - Parameter Edit Endpoint

**Batch 2** (Sequential - Depends on Batch 1):
- SID-011 → `python-backend-engineer` (5h) - **Blocked by**: SID-007, SID-008, SID-009, SID-010
- SID-012 → `backend-architect` (5h) - **Blocked by**: SID-007, SID-008, SID-009, SID-010

**Critical Path**: SID-008 → SID-011 (2.5 days)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("python-backend-engineer", "SID-007: Implement Discovery Endpoint - POST /api/v1/artifacts/discover returns discovered artifacts. Files: skillmeat/api/routers/artifacts.py")

Task("python-backend-engineer", "SID-008: Implement Bulk Import Endpoint - POST /api/v1/artifacts/discover/import validates batch, imports atomically. Files: skillmeat/api/routers/artifacts.py")

Task("python-backend-engineer", "SID-009: Implement GitHub Metadata Endpoint - GET /api/v1/artifacts/metadata/github fetches metadata, caches response. Files: skillmeat/api/routers/artifacts.py")

Task("backend-architect", "SID-010: Implement Parameter Edit Endpoint - PUT /api/v1/artifacts/{id}/parameters updates source/version/tags/scope. Files: skillmeat/api/routers/artifacts.py")

# Batch 2 (After Batch 1 completes)
Task("python-backend-engineer", "SID-011: Integration Tests for all API endpoints. Files: tests/integration/test_discovery_api.py")

Task("backend-architect", "SID-012: Implement consistent error handling & validation across all endpoints. Files: skillmeat/api/routers/artifacts.py")
```

---

## Overview

Phase 2 implements the API layer for Smart Import & Discovery, exposing four new REST endpoints that enable discovery, bulk import, metadata fetching, and parameter editing functionality.

**Why This Phase**: The API layer bridges the service layer (Phase 1) with the frontend (Phase 3). Without these endpoints, the UI cannot leverage the discovery and metadata services.

**Scope**:
- **IN SCOPE**:
  - 4 new API endpoints
  - Integration with existing artifact manager
  - Request/response validation
  - Error handling and rollback logic
  - Integration tests (>70% coverage)

- **OUT OF SCOPE**:
  - Frontend components (Phase 3)
  - E2E testing (Phase 4)
  - Feature flags and monitoring (Phase 5)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All 4 endpoints implemented and tested | ⏳ Pending |
| SC-2 | Atomic operations verified for bulk import | ⏳ Pending |
| SC-3 | Error responses follow consistent format | ⏳ Pending |
| SC-4 | GitHub rate limiting handled gracefully | ⏳ Pending |
| SC-5 | Integration tests >70% coverage | ⏳ Pending |
| SC-6 | Performance: bulk import <3 seconds for 20 artifacts | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| SID-007 | Implement Discovery Endpoint | ⏳ | python-backend-engineer | None | 5h | POST /discover |
| SID-008 | Implement Bulk Import Endpoint | ⏳ | python-backend-engineer | None | 1d | POST /discover/import |
| SID-009 | Implement GitHub Metadata Endpoint | ⏳ | python-backend-engineer | None | 5h | GET /metadata/github |
| SID-010 | Implement Parameter Edit Endpoint | ⏳ | backend-architect | None | 5h | PUT /{id}/parameters |
| SID-011 | Integration Tests: API Endpoints | ⏳ | python-backend-engineer | SID-007-010 | 5h | >70% coverage |
| SID-012 | Error Handling & Validation | ⏳ | backend-architect | SID-007-010 | 5h | Consistent errors |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State

SkillMeat API currently has:
- `/api/v1/artifacts` router with CRUD operations
- `/api/v1/projects` router
- Pydantic schema validation
- Error handling middleware

**Key Files**:
- `skillmeat/api/routers/artifacts.py` - Existing artifact endpoints
- `skillmeat/api/schemas/artifact.py` - Existing schemas
- `skillmeat/api/dependencies.py` - Dependency injection

### Reference Patterns

**Endpoint Pattern**:
- Follow existing CRUD endpoint structure in `/api/v1/artifacts`
- Use dependency injection for ArtifactManager
- Consistent error handling with HTTPException

**Schema Pattern**:
- Pydantic BaseModel for request/response
- Validation in schemas, not controllers
- Nested schemas for complex objects

---

## Implementation Details

### Technical Approach

**Endpoint 1: POST /api/v1/artifacts/discover**
```python
@router.post("/discover", response_model=DiscoveryResult)
async def discover_artifacts(
    request: DiscoveryRequest,
    artifact_mgr: ArtifactManagerDep,
) -> DiscoveryResult:
    service = ArtifactDiscoveryService(artifact_mgr.collection_path)
    result = service.discover_artifacts()
    return result
```

**Endpoint 2: POST /api/v1/artifacts/discover/import**
```python
@router.post("/discover/import", response_model=BulkImportResult)
async def bulk_import_artifacts(
    request: BulkImportRequest,
    artifact_mgr: ArtifactManagerDep,
) -> BulkImportResult:
    importer = ArtifactImporter(artifact_mgr)
    result = importer.bulk_import(request)
    return result
```

**Endpoint 3: GET /api/v1/artifacts/metadata/github**
```python
@router.get("/metadata/github", response_model=MetadataFetchResponse)
async def fetch_github_metadata(
    source: str = Query(...),
    artifact_mgr: ArtifactManagerDep = None,
) -> MetadataFetchResponse:
    extractor = GitHubMetadataExtractor(cache)
    metadata = extractor.fetch_metadata(source)
    return MetadataFetchResponse(success=True, metadata=metadata)
```

**Endpoint 4: PUT /api/v1/artifacts/{artifact_id}/parameters**
```python
@router.put("/{artifact_id}/parameters", response_model=ParameterUpdateResponse)
async def update_artifact_parameters(
    artifact_id: str,
    request: ParameterUpdateRequest,
    artifact_mgr: ArtifactManagerDep,
) -> ParameterUpdateResponse:
    validator = ParameterValidator()
    validator.validate_parameters(request.parameters)
    # Update logic...
    return ParameterUpdateResponse(success=True, artifact_id=artifact_id, ...)
```

### Known Gotchas

- **Atomic Operations**: Bulk import must be all-or-nothing. Use transaction-like semantics.
- **GitHub Rate Limiting**: Return 429 with Retry-After header when rate limited.
- **Partial Failures**: Bulk import should report per-artifact success/failure, not just fail entirely.
- **Path Security**: Validate artifact paths to prevent directory traversal attacks.
- **Cache Coordination**: GitHub metadata cache must be shared across requests.

### Development Setup

- FastAPI server running: `skillmeat web dev --api-only`
- Test with curl or HTTPie
- OpenAPI docs at http://localhost:8000/docs

---

## Blockers

### Active Blockers

None currently.

### Resolved Blockers

None yet.

---

## Dependencies

### External Dependencies

- **Phase 1**: All services from Phase 1 must be complete and tested
- **GitHub API**: Endpoint 3 depends on GitHub API availability

### Internal Integration Points

- **ArtifactManager**: All endpoints integrate with existing artifact manager
- **Manifest/Lock Files**: Bulk import updates manifest and lock files
- **Error Middleware**: Consistent error handling across all endpoints

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Integration | All 4 endpoints | >70% | ⏳ |
| Integration | Error scenarios | All error codes | ⏳ |
| Integration | Validation | Invalid inputs | ⏳ |
| Performance | Bulk import 20 artifacts | <3s | ⏳ |
| Performance | Discovery 50+ artifacts | <2s | ⏳ |

**Test Scenarios**:
- Valid discovery request
- Bulk import with all valid artifacts
- Bulk import with some invalid artifacts (partial failure)
- GitHub metadata fetch success
- GitHub metadata fetch failure (404, rate limit)
- Parameter update success
- Parameter update with invalid values
- Concurrent requests

---

## Next Session Agenda

### Immediate Actions (Next Session)
1. [ ] Implement all 4 endpoints in skillmeat/api/routers/artifacts.py
2. [ ] Create schema definitions in skillmeat/api/schemas/discovery.py
3. [ ] Write integration tests in tests/integration/test_discovery_api.py

### Upcoming Critical Items

- **After Phase 2**: Frontend components (Phase 3) will consume these endpoints
- **Error Handling**: Must be consistent and user-friendly for UI integration

### Context for Continuing Agent

**Key Implementation Notes**:
- Reuse existing FastAPI patterns from `/api/v1/artifacts`
- All endpoints must handle errors gracefully and return consistent format
- Bulk import must be atomic - all succeed or all fail (with rollback)
- GitHub metadata caching must persist across requests
- Validate all inputs to prevent security issues

---

## Additional Resources

- **PRD**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
- **Implementation Plan**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Existing API**: `skillmeat/api/routers/artifacts.py`
