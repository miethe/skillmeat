---
type: progress
prd: "marketplace-github-ingestion"
phase: 4
title: "API Layer"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: ["backend-architect"]

tasks:
  - id: "API-001"
    description: "Marketplace sources router: POST/GET sources, GET source by ID, PATCH source"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVC-007"]
    estimated_effort: "3pts"
    priority: "high"

  - id: "API-002"
    description: "Marketplace rescan endpoint: POST sources/{id}/rescan with background job"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "2pts"
    priority: "high"

  - id: "API-003"
    description: "Marketplace artifacts listing: GET sources/{id}/artifacts with filtering and pagination"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "2pts"
    priority: "high"

  - id: "API-004"
    description: "Marketplace import endpoint: POST sources/{id}/import for single and bulk imports"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["SVC-006"]
    estimated_effort: "3pts"
    priority: "high"

  - id: "API-005"
    description: "Error handling and validation middleware for marketplace endpoints"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-004"]
    estimated_effort: "2pts"
    priority: "medium"

  - id: "API-006"
    description: "Authentication and authorization checks for marketplace operations"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["API-005"]
    estimated_effort: "2pts"
    priority: "high"

  - id: "API-007"
    description: "Background job integration for scans (Celery/APScheduler setup)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["API-002"]
    estimated_effort: "2pts"
    priority: "medium"

parallelization:
  batch_1: ["API-001"]
  batch_2: ["API-002", "API-003", "API-004"]
  batch_3: ["API-005", "API-007"]
  batch_4: ["API-006"]
  critical_path: ["API-001", "API-002", "API-004", "API-005", "API-006"]
  estimated_total_time: "16h"

blockers: []

success_criteria:
  - All marketplace endpoints implemented following FastAPI patterns
  - Endpoints return proper HTTP status codes and error responses
  - Background rescan job executes asynchronously with status tracking
  - Filtering and pagination work on artifact listings
  - Authentication enforces project-level access control
  - Input validation prevents malformed requests
  - Endpoints tested with unit and integration tests
  - OpenAPI documentation generated automatically

files_modified:
  - "skillmeat/api/routers/marketplace.py"
  - "skillmeat/api/schemas/marketplace.py"
  - "skillmeat/api/middleware/marketplace_auth.py"
  - "skillmeat/core/jobs/marketplace_scan.py"
  - "tests/integration/test_marketplace_api.py"
---

# Phase 4: API Layer

**Status:** Planning | **Owner:** python-backend-engineer | **Est. Effort:** 16 pts (16h)

## Overview

Expose marketplace functionality through RESTful API endpoints. This phase implements routers for managing sources, listing and filtering artifacts, rescanning catalogs, and importing artifacts into collections. Includes authentication, validation, and background job integration.

## Orchestration Quick Reference

**Batch 1:** API-001 (3h)
**Batch 2 (Parallel after Batch 1):** API-002, API-003, API-004 (2h + 2h + 3h)
**Batch 3 (Parallel):** API-005, API-007 (2h + 2h)
**Batch 4 (Final):** API-006 (2h)

### Task Delegation Commands

```
Task("python-backend-engineer", "API-001: Create marketplace router (skillmeat/api/routers/marketplace.py) with endpoints: (1) POST /marketplace/sources - create source, (2) GET /marketplace/sources - list sources for project with pagination, (3) GET /marketplace/sources/{id} - get source details with last_sync/error, (4) PATCH /marketplace/sources/{id} - update source (branch, root_hint, manual_map, visibility), (5) DELETE /marketplace/sources/{id} - delete source. Use FastAPI patterns, return SourceSchema responses. Include project isolation.")

Task("python-backend-engineer", "API-002: Implement POST /marketplace/sources/{id}/rescan endpoint that: (1) Accepts optional force=true to skip cache, (2) Enqueues async scan job, (3) Returns immediate 202 Accepted response with job_id, (4) Updates source.last_sync on completion, (5) Stores errors in last_error if scan fails, (6) Client polls GET /marketplace/sources/{id} for status. Integrate with job queue (Celery/APScheduler).")

Task("python-backend-engineer", "API-003: Build GET /marketplace/sources/{id}/artifacts endpoint with: (1) Query filters: type (skill/agent/etc), status (new/updated/removed), confidence (min-max), (2) Sorting: by_confidence, by_date, by_type, (3) Pagination: limit, offset, (4) Response includes artifact metadata, upstream URL, confidence, status, imported_at, (5) Return empty list if no entries, (6) Use CatalogSchema for consistent responses.")

Task("backend-architect", "API-004: Create POST /marketplace/sources/{id}/import endpoint that: (1) Accept payload with entry_ids (array) for bulk import or single entry_id, (2) Call ImportCoordinator for each entry, (3) Handle conflicts: return list of conflicts with rename suggestions, (4) Accept conflict_resolution (skip/rename/force) in follow-up request, (5) Return ImportResult with imported_count, conflict_count, error_count, (6) Mark entries as imported with timestamp, (7) Log import activity for audit.")

Task("python-backend-engineer", "API-005: Add error handling and validation: (1) Global exception handler for marketplace errors, (2) Input validation: URL format, path traversal checks, required fields, (3) Request body validators using Pydantic, (4) Return RFC 7807 problem details for errors, (5) Proper HTTP status codes (400 for validation, 404 for not found, 409 for conflicts), (6) Error messages include hints for user resolution.")

Task("backend-architect", "API-006: Implement authentication and authorization: (1) All marketplace endpoints require auth (existing middleware), (2) Project-level access control: users can only access sources in their projects, (3) Admin override for troubleshooting, (4) Check user permissions before mutations, (5) Audit log import/rescan operations, (6) Rate limiting for rescan: 1 per 5 minutes per source, (7) Graceful handling of permission denied (403 vs 401).")

Task("backend-architect", "API-007: Integrate background job system for rescans: (1) Choose job queue (Celery with Redis or APScheduler), (2) Create marketplace_scan job that: calls GitHubScanner, stores results via repositories, updates last_sync/error, (3) Job includes timeout (120s), retry logic (3x with exponential backoff), (4) Job tracks progress for long scans (especially large repos), (5) Emit job status events for UI polling, (6) Schedule periodic rescans (optional, configurable per source).")
```

## Success Criteria

| Criteria | Details |
|----------|---------|
| **Endpoints** | All 7 endpoints implemented with correct HTTP methods and status codes |
| **Filtering** | Artifact listing supports type, status, and confidence filters |
| **Pagination** | Endpoints support limit/offset pagination with defaults |
| **Background Jobs** | Rescan jobs execute asynchronously with status tracking |
| **Import Flow** | Imports handle single and bulk operations with conflict detection |
| **Validation** | Input validation prevents malformed requests and data corruption |
| **Authentication** | Project-level access control enforced consistently |
| **Documentation** | OpenAPI schema generated automatically for all endpoints |

## Tasks

| Task ID | Description | Agent | Status | Dependencies | Est. |
|---------|-------------|-------|--------|--------------|------|
| API-001 | Marketplace sources router | python-backend-engineer | ⏳ Pending | SVC-007 | 3pts |
| API-002 | Rescan endpoint with background jobs | python-backend-engineer | ⏳ Pending | API-001 | 2pts |
| API-003 | Artifacts listing with filters | python-backend-engineer | ⏳ Pending | API-001 | 2pts |
| API-004 | Import endpoint and coordinator | backend-architect | ⏳ Pending | SVC-006 | 3pts |
| API-005 | Error handling and validation | python-backend-engineer | ⏳ Pending | API-004 | 2pts |
| API-006 | Authentication and authorization | backend-architect | ⏳ Pending | API-005 | 2pts |
| API-007 | Background job integration | backend-architect | ⏳ Pending | API-002 | 2pts |

## Blockers

None identified.

## Next Session Agenda

1. Begin API-001 once Phase 3 (SVC-007) completes
2. Implement marketplace router with FastAPI patterns
3. Create rescan endpoint with async job support
4. Build artifact listing with advanced filtering
5. Implement import endpoint with conflict handling
6. Add comprehensive validation and error handling
7. Enforce project-level authentication and authorization
8. Integrate background job system for long-running scans
9. Test all endpoints with integration tests
10. Verify OpenAPI documentation is complete
