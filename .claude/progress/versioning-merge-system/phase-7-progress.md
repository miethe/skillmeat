---
type: progress
prd: "versioning-merge-system"
phase: 7
title: "API Layer - Version & Merge Endpoints"
status: "pending"
started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 13
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["python-backend-engineer", "backend-architect"]
contributors: ["python-backend-engineer", "backend-architect"]

tasks:
  - id: "APIVM-001"
    description: "GET /api/v1/artifacts/{id}/versions - List version history with pagination"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-004"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-002"
    description: "GET /api/v1/artifacts/{id}/versions/{version_id} - Get version details"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-003"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-003"
    description: "GET /api/v1/artifacts/{id}/versions/{version_id}/files - Get version files"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-006"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-004"
    description: "GET /api/v1/artifacts/{id}/versions/{v1}/diff/{v2} - Diff two versions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-012"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-005"
    description: "POST /api/v1/artifacts/{id}/versions/{version_id}/restore - Restore to version"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-006"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-006"
    description: "POST /api/v1/artifacts/{id}/merge/preview - Preview merge operation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-007"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-007"
    description: "POST /api/v1/artifacts/{id}/merge/analyze - Analyze merge (three-way)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["MERGE-001", "MERGE-006"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-008"
    description: "POST /api/v1/artifacts/{id}/merge/apply - Apply merge with conflict resolution"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-008"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-009"
    description: "Define request/response schemas for all endpoints using Pydantic"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["APIVM-001"]
    estimated_effort: "3h"
    priority: "high"

  - id: "APIVM-010"
    description: "Standardize error responses across all endpoints (400, 404, 409, 422, 500)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["APIVM-001"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-011"
    description: "Generate OpenAPI spec and enable Swagger UI documentation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["APIVM-009"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-012"
    description: "Regenerate TypeScript SDK from OpenAPI spec"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["APIVM-011"]
    estimated_effort: "2h"
    priority: "high"

  - id: "APIVM-013"
    description: "Create API integration tests for all endpoints (>85% coverage)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["APIVM-012"]
    estimated_effort: "5h"
    priority: "high"

parallelization:
  batch_1: ["APIVM-001", "APIVM-002", "APIVM-003", "APIVM-004"]
  batch_2: ["APIVM-005", "APIVM-006", "APIVM-007", "APIVM-008"]
  batch_3: ["APIVM-009", "APIVM-010"]
  batch_4: ["APIVM-011", "APIVM-012", "APIVM-013"]
  critical_path: ["APIVM-001", "APIVM-009", "APIVM-011", "APIVM-012", "APIVM-013"]
  estimated_total_time: "3-4d"

blockers: []

success_criteria:
  - id: "SC-7.1"
    description: "All endpoints return correct HTTP status codes (200, 201, 400, 404, 409, 422, 500)"
    status: "pending"
  - id: "SC-7.2"
    description: "OpenAPI schema is complete, valid, and includes all endpoints with examples"
    status: "pending"
  - id: "SC-7.3"
    description: "Pagination works correctly on list endpoints with limit/offset parameters"
    status: "pending"
  - id: "SC-7.4"
    description: "Error responses contain consistent structure with error_code and message"
    status: "pending"
  - id: "SC-7.5"
    description: "TypeScript SDK generates without errors and compiles successfully"
    status: "pending"
  - id: "SC-7.6"
    description: "Integration tests achieve >85% coverage of all endpoints"
    status: "pending"
  - id: "SC-7.7"
    description: "Performance: version list endpoint <100ms, merge preview <2s for 10MB artifact"
    status: "pending"
  - id: "SC-7.8"
    description: "Swagger UI accessible at /docs with complete endpoint documentation"
    status: "pending"
---

# versioning-merge-system - Phase 7: API Layer - Version & Merge Endpoints

**Phase**: 7 of 10
**Status**: ⏳ Pending (0% complete)
**Duration**: Estimated 3-4 days
**Owner**: python-backend-engineer, backend-architect
**Contributors**: python-backend-engineer, backend-architect

**Dependencies**: Phase 4 (Version CRUD), Phase 5 (Merge Engine), Phase 6 (Version Comparison) must be complete before starting

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file. Copy-paste Task() commands directly.

### Parallelization Strategy

**Batch 1** (Parallel - GET Endpoints, Depends on core services):
- APIVM-001 → `python-backend-engineer` (3h) - List version history
- APIVM-002 → `python-backend-engineer` (2h) - Get version details
- APIVM-003 → `python-backend-engineer` (2h) - Get version files
- APIVM-004 → `python-backend-engineer` (2h) - Diff two versions

**Batch 2** (Parallel - POST Endpoints, Depends on services):
- APIVM-005 → `python-backend-engineer` (3h) - Restore to version
- APIVM-006 → `python-backend-engineer` (3h) - Preview merge
- APIVM-007 → `backend-architect` (3h) - Analyze merge (three-way)
- APIVM-008 → `python-backend-engineer` (3h) - Apply merge

**Batch 3** (Sequential - Schemas & Errors):
- APIVM-009 → `python-backend-engineer` (3h) - Define request/response schemas - **Blocks**: APIVM-011
- APIVM-010 → `python-backend-engineer` (2h) - Standardize error responses - **Blocks**: APIVM-011

**Batch 4** (Sequential - OpenAPI, SDK, Tests):
- APIVM-011 → `python-backend-engineer` (2h) - Generate OpenAPI spec - **Blocks**: APIVM-012
- APIVM-012 → `python-backend-engineer` (2h) - Regenerate TypeScript SDK - **Blocks**: APIVM-013
- APIVM-013 → `backend-architect` (5h) - Create integration tests - **Final step**

**Critical Path**: APIVM-001 → APIVM-009 → APIVM-011 → APIVM-012 → APIVM-013 (15h total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel after Phase 4, 5, 6 complete)
Task("python-backend-engineer", "APIVM-001: Implement GET /api/v1/artifacts/{id}/versions endpoint. Return list of versions with pagination (limit/offset). Include: version_id, created_at, created_by, change_summary, file_count. Performance target: <100ms.")
Task("python-backend-engineer", "APIVM-002: Implement GET /api/v1/artifacts/{id}/versions/{version_id} endpoint. Return complete version metadata: id, created_at, created_by, source_hash, files_changed, change_summary, parent_versions, artifact_size.")
Task("python-backend-engineer", "APIVM-003: Implement GET /api/v1/artifacts/{id}/versions/{version_id}/files endpoint. Return list of files in version with size, hash, and relative path. Support pagination.")
Task("python-backend-engineer", "APIVM-004: Implement GET /api/v1/artifacts/{id}/versions/{v1}/diff/{v2} endpoint. Return diff summary: files_added, files_removed, files_modified with file counts.")

# Batch 2 (Launch in parallel)
Task("python-backend-engineer", "APIVM-005: Implement POST /api/v1/artifacts/{id}/versions/{version_id}/restore endpoint. Restore artifact to specified version. Return restored artifact metadata. Handle validation: version must exist, artifact must exist.")
Task("python-backend-engineer", "APIVM-006: Implement POST /api/v1/artifacts/{id}/merge/preview endpoint. Preview merge result without applying. Accept current_version, other_version, base_version parameters. Return merge statistics: conflicts_count, files_affected, result_size.")
Task("backend-architect", "APIVM-007: Implement POST /api/v1/artifacts/{id}/merge/analyze endpoint. Perform three-way merge analysis. Accept current, other, base versions. Return: merge_strategy recommendation, conflicts array with (file, conflict_type, content), resolvable_count, manual_review_needed boolean.")
Task("python-backend-engineer", "APIVM-008: Implement POST /api/v1/artifacts/{id}/merge/apply endpoint. Apply merge with conflict resolution. Accept merge_strategy and conflict_resolutions parameters. Return: merge_result with version_id, files_merged, conflicts_resolved.")

# Batch 3 (Sequential - after Batch 1 & 2 complete)
Task("python-backend-engineer", "APIVM-009: Define Pydantic request/response schemas for all 8 endpoints. Include: VersionListResponse, VersionDetailsResponse, VersionFilesResponse, DiffResponse, MergePreviewRequest/Response, MergeAnalyzeRequest/Response, MergeApplyRequest/Response. Include field validation, examples.")
Task("python-backend-engineer", "APIVM-010: Standardize error responses across all endpoints. Define ErrorResponse schema with error_code (string) and message. Return: 400 (bad request), 404 (not found), 409 (conflict), 422 (validation error), 500 (server error) with proper messages.")

# Batch 4 (Sequential - critical path)
Task("python-backend-engineer", "APIVM-011: Generate OpenAPI spec from FastAPI endpoints. Enable Swagger UI at /docs. Verify all endpoints, parameters, schemas are documented. Include example requests/responses for each endpoint.")
Task("python-backend-engineer", "APIVM-012: Regenerate TypeScript SDK from OpenAPI spec using openapi-generator. Verify SDK compiles without errors. Update skillmeat/web with new SDK version. Test SDK import in Next.js.")
Task("backend-architect", "APIVM-013: Create comprehensive API integration tests. Test: all 8 endpoints with valid/invalid inputs, pagination boundaries, error responses, merge conflict scenarios. Target: >85% coverage. Measure endpoint performance: version list <100ms, merge preview <2s.")
```

---

## Overview

Phase 7 implements the FastAPI endpoints for version management and merge operations. This phase exposes the core versioning and merge functionality built in Phases 4-6 through a REST API that the frontend will consume.

**Why This Phase**: The versioning system is currently backend-only. Phase 7 creates the bridge between backend logic and frontend consumption, enabling users to browse version history, preview merges, and manage conflicts through the web UI.

**Scope**:
- ✅ **IN SCOPE**: 8 REST endpoints (4 GET, 4 POST), request/response schemas, error standardization, OpenAPI spec, TypeScript SDK generation, integration tests
- ❌ **OUT OF SCOPE**: UI components (Phase 8-9), performance optimization beyond success criteria, WebSocket streaming

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-7.1 | All endpoints return correct HTTP status codes (200, 201, 400, 404, 409, 422, 500) | ⏳ Pending |
| SC-7.2 | OpenAPI schema is complete, valid, and includes all endpoints with examples | ⏳ Pending |
| SC-7.3 | Pagination works correctly on list endpoints with limit/offset parameters | ⏳ Pending |
| SC-7.4 | Error responses contain consistent structure with error_code and message | ⏳ Pending |
| SC-7.5 | TypeScript SDK generates without errors and compiles successfully | ⏳ Pending |
| SC-7.6 | Integration tests achieve >85% coverage of all endpoints | ⏳ Pending |
| SC-7.7 | Performance: version list endpoint <100ms, merge preview <2s for 10MB artifact | ⏳ Pending |
| SC-7.8 | Swagger UI accessible at /docs with complete endpoint documentation | ⏳ Pending |

---

## Endpoints Summary

### GET Endpoints (Batch 1)

| Endpoint | Method | Task | Purpose |
|----------|--------|------|---------|
| `/api/v1/artifacts/{id}/versions` | GET | APIVM-001 | List all versions with pagination |
| `/api/v1/artifacts/{id}/versions/{version_id}` | GET | APIVM-002 | Get complete version metadata |
| `/api/v1/artifacts/{id}/versions/{version_id}/files` | GET | APIVM-003 | List files in specific version |
| `/api/v1/artifacts/{id}/versions/{v1}/diff/{v2}` | GET | APIVM-004 | Compare two versions |

### POST Endpoints (Batch 2)

| Endpoint | Method | Task | Purpose |
|----------|--------|------|---------|
| `/api/v1/artifacts/{id}/versions/{version_id}/restore` | POST | APIVM-005 | Restore artifact to version |
| `/api/v1/artifacts/{id}/merge/preview` | POST | APIVM-006 | Preview merge result |
| `/api/v1/artifacts/{id}/merge/analyze` | POST | APIVM-007 | Analyze three-way merge |
| `/api/v1/artifacts/{id}/merge/apply` | POST | APIVM-008 | Apply merge with conflicts |

### Cross-Cutting Concerns (Batch 3-4)

| Task | Purpose |
|------|---------|
| APIVM-009 | Pydantic schemas for all endpoints |
| APIVM-010 | Standardized error responses |
| APIVM-011 | OpenAPI spec generation |
| APIVM-012 | TypeScript SDK regeneration |
| APIVM-013 | Integration test suite |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| APIVM-001 | GET /versions - List version history | ⏳ | python-backend-engineer | SVCV-004 | 3h | Pagination, <100ms perf |
| APIVM-002 | GET /versions/{id} - Version details | ⏳ | python-backend-engineer | REPO-003 | 2h | Complete metadata |
| APIVM-003 | GET /versions/{id}/files - Version files | ⏳ | python-backend-engineer | REPO-006 | 2h | With pagination |
| APIVM-004 | GET /diff - Diff two versions | ⏳ | python-backend-engineer | REPO-012 | 2h | Summary format |
| APIVM-005 | POST /restore - Restore to version | ⏳ | python-backend-engineer | SVCV-006 | 3h | With validation |
| APIVM-006 | POST /merge/preview - Preview merge | ⏳ | python-backend-engineer | MERGE-007 | 3h | Statistics output |
| APIVM-007 | POST /merge/analyze - Three-way analysis | ⏳ | backend-architect | MERGE-001, MERGE-006 | 3h | Conflicts array |
| APIVM-008 | POST /merge/apply - Apply merge | ⏳ | python-backend-engineer | MERGE-008 | 3h | Resolution handling |
| APIVM-009 | Schemas - Pydantic models | ⏳ | python-backend-engineer | APIVM-001 | 3h | All endpoints |
| APIVM-010 | Error responses - Standardize | ⏳ | python-backend-engineer | APIVM-001 | 2h | Consistent format |
| APIVM-011 | OpenAPI - Generate spec | ⏳ | python-backend-engineer | APIVM-009 | 2h | With Swagger UI |
| APIVM-012 | SDK - Regenerate TypeScript | ⏳ | python-backend-engineer | APIVM-011 | 2h | Compile verified |
| APIVM-013 | Tests - Integration suite | ⏳ | backend-architect | APIVM-012 | 5h | >85% coverage |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Endpoint Patterns

All endpoints follow RESTful conventions with consistent response structures:

**Request Pattern**:
```http
{METHOD} /api/v1/artifacts/{artifact_id}/{resource_path}
Content-Type: application/json
Authorization: Bearer {token}

{request_body}
```

**Response Pattern (Success - 200/201)**:
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2025-12-03T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

**Response Pattern (Error - 400/404/409/422/500)**:
```json
{
  "success": false,
  "error": {
    "error_code": "CONFLICT_NOT_RESOLVABLE",
    "message": "Cannot automatically resolve conflict in file: SKILL.md",
    "details": {
      "file": "SKILL.md",
      "conflict_type": "content_conflict"
    }
  },
  "meta": {
    "timestamp": "2025-12-03T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Integration with Previous Phases

**Phase 4 (Version CRUD)**: APIVM-001, 002, 003, 005 depend on version services
**Phase 5 (Merge Engine)**: APIVM-006, 007, 008 depend on merge analysis and application
**Phase 6 (Comparison)**: APIVM-004 depends on diff generation

### File Locations

Expected files to create/modify:

```
skillmeat/api/routers/
├── versions.py          # APIVM-001, 002, 003, 004, 005
├── merge.py             # APIVM-006, 007, 008
└── __init__.py          # Register routers

skillmeat/api/schemas/
├── version_schemas.py   # APIVM-009
├── merge_schemas.py     # APIVM-009
└── error_schemas.py     # APIVM-010

tests/api/
├── test_versions_endpoints.py  # APIVM-013
├── test_merge_endpoints.py     # APIVM-013
└── test_error_handling.py      # APIVM-013
```

---

## Performance Targets

| Endpoint | Target | Notes |
|----------|--------|-------|
| GET /versions | <100ms | With pagination, 50 items default |
| GET /versions/{id} | <50ms | Single version metadata |
| GET /versions/{id}/files | <100ms | With pagination |
| GET /diff | <200ms | For 10MB artifacts |
| POST /merge/preview | <2s | For 10MB artifacts, no file I/O |
| POST /merge/analyze | <3s | For 10MB artifacts, three-way analysis |
| POST /merge/apply | <5s | For 10MB artifacts, with conflict resolution |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Performance degradation on large artifacts | Medium | High | Early performance testing in APIVM-013 |
| Merge conflicts difficult to represent in API | Low | High | Clear conflict schema in APIVM-009 |
| OpenAPI generation missing endpoints | Low | Medium | Manual verification before release |
| TypeScript SDK compilation errors | Low | Medium | Early regeneration test in APIVM-012 |

---

## Dependencies

**Phase 4 Prerequisites**:
- Version CRUD operations complete (services exist)
- Version metadata schema finalized

**Phase 5 Prerequisites**:
- Merge engine implementation complete
- Three-way merge analysis available

**Phase 6 Prerequisites**:
- Diff generation fully functional
- Performance acceptable for large artifacts

---

## Notes for Future Phases

**Phase 8 (Frontend - Version Browser)**: Will consume APIVM-001, 002, 003, 004 endpoints
**Phase 9 (Frontend - Merge UI)**: Will consume APIVM-006, 007, 008 endpoints
**Phase 10 (Deployment & Polish)**: Will verify SDK usage in frontend, performance under load

---

## Status History

| Date | Status | Notes |
|------|--------|-------|
| 2025-12-03 | Created | Initial progress file with full task breakdown |
