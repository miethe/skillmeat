---
type: progress
prd: "marketplace-source-detection-improvements"
phase: 3
phase_name: "API Layer"
status: in_progress
progress: 38
total_tasks: 13
completed_tasks: 5
effort: "12-18 pts"
created: 2026-01-05
updated: 2026-01-06

assigned_to: ["python-backend-engineer"]
dependencies: [2]

tasks:
  # PATCH Endpoint (5 tasks)
  - id: "P3.1a"
    name: "Add manual_map to request schema"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4d"]
    effort: "2 pts"
    completed_by: "aab5845"
    completed_at: 2026-01-06
    note: "Added manual_map field to UpdateSourceRequest schema with Optional[Dict[str, str]] type"

  - id: "P3.1b"
    name: "Validate directory paths"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1a"]
    effort: "3 pts"
    completed_by: "a11c94f"
    completed_at: 2026-01-06
    note: "Added path validation in router layer using GitHubScanner tree data, raises 422 for invalid paths"

  - id: "P3.1c"
    name: "Validate artifact types"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1a"]
    effort: "1 pt"
    completed_by: "a95cc94"
    completed_at: 2026-01-06
    note: "Added artifact type validation with ALLOWED_ARTIFACT_TYPES constant, raises 422 for invalid types"

  - id: "P3.1d"
    name: "Persist mappings"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1b", "P3.1c"]
    effort: "2 pts"
    completed_by: "a24e6bb"
    completed_at: 2026-01-06
    note: "Persisting manual_map to database using set_manual_map_dict() method, handles None/empty to clear mapping"

  - id: "P3.1e"
    name: "Update PATCH route handler"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1d"]
    effort: "2 pts"
    completed_by: "a6ac07c"
    completed_at: 2026-01-06
    note: "Completed PATCH endpoint integration with OpenAPI docs, docstring examples, and verified all validation/persistence flows"

  # GET Endpoint (2 tasks)
  - id: "P3.2a"
    name: "Include manual_map in response"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1e"]
    effort: "1 pt"

  - id: "P3.2b"
    name: "Test GET response"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.2a"]
    effort: "1 pt"

  # Rescan Endpoint (4 tasks)
  - id: "P3.3a"
    name: "Pass manual_map to detector"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.2b"]
    effort: "2 pts"

  - id: "P3.3b"
    name: "Return dedup counts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3a"]
    effort: "2 pts"

  - id: "P3.3c"
    name: "Update response schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3b"]
    effort: "2 pts"

  - id: "P3.3d"
    name: "Integration test"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3c"]
    effort: "2 pts"

  # Error Handling & Docs (2 tasks)
  - id: "P3.4a"
    name: "Add error responses"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3d"]
    effort: "2 pts"

  - id: "P3.4b"
    name: "Update OpenAPI docs"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.4a"]
    effort: "2 pts"

parallelization:
  batch_1: ["P3.1a"]
  batch_2: ["P3.1b", "P3.1c"]
  batch_3: ["P3.1d"]
  batch_4: ["P3.1e"]
  batch_5: ["P3.2a"]
  batch_6: ["P3.2b"]
  batch_7: ["P3.3a"]
  batch_8: ["P3.3b"]
  batch_9: ["P3.3c"]
  batch_10: ["P3.3d"]
  batch_11: ["P3.4a", "P3.4b"]
---

# Phase 3: API Layer

## Overview

Wire manual mapping and deduplication into API endpoints with validation and documentation.

**Duration**: 3-4 days
**Effort**: 12-18 pts
**Assigned**: python-backend-engineer
**Dependencies**: Phase 2 complete

## Orchestration Quick Reference

**Batch 3.1** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1a: Add manual_map field to MarketplaceSourceUpdate request schema in skillmeat/api/schemas/marketplace.py")
```

**Batch 3.2** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P3.1b: Validate directory paths in manual_map exist in source repository using GitHub API", model="sonnet")
Task("python-backend-engineer", "P3.1c: Validate artifact types in manual_map against allowed types (skill, command, agent, mcp_server, hook)", model="sonnet")
```

**Batch 3.3** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1d: Persist manual_map to MarketplaceSource.manual_map column as JSON")
```

**Batch 3.4** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1e: Update PATCH /api/v1/marketplace-sources/{id} route handler to accept and validate manual_map")
```

**Batch 3.5** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.2a: Include manual_map in GET /api/v1/marketplace-sources/{id} response schema", model="sonnet")
```

**Batch 3.6** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.2b: Test GET endpoint returns manual_map correctly", model="sonnet")
```

**Batch 3.7** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3a: Pass manual_map from database to detector in rescan endpoint")
```

**Batch 3.8** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3b: Return dedup counts in rescan response (duplicates_removed, cross_source_duplicates)", model="sonnet")
```

**Batch 3.9** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3c: Update MarketplaceRescanResponse schema to include dedup counts", model="sonnet")
```

**Batch 3.10** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3d: Integration test for rescan endpoint with manual mappings and deduplication", model="sonnet")
```

**Batch 3.11** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P3.4a: Add error responses for invalid directory paths and artifact types (400, 422)", model="sonnet")
Task("python-backend-engineer", "P3.4b: Update OpenAPI docs for PATCH, GET, and rescan endpoints with manual_map examples", model="sonnet")
```

## Quality Gates

- [ ] PATCH endpoint accepts and persists manual_map
- [ ] GET endpoint returns manual_map correctly
- [ ] Rescan endpoint uses manual_map and returns dedup counts
- [ ] OpenAPI docs updated and validated
- [ ] Error handling tested for all edge cases

## Key Files

- `skillmeat/api/schemas/marketplace.py` - Request/response schemas
- `skillmeat/api/routers/marketplace_sources.py` - PATCH/GET endpoints
- `skillmeat/api/routers/marketplace.py` - Rescan endpoint
- `tests/test_api_marketplace.py` - API integration tests

## Endpoints Modified

| Endpoint | Method | Changes |
|----------|--------|---------|
| `/api/v1/marketplace-sources/{id}` | PATCH | Accept manual_map, validate paths/types, persist |
| `/api/v1/marketplace-sources/{id}` | GET | Include manual_map in response |
| `/api/v1/marketplace/{source_id}/rescan` | POST | Pass manual_map to detector, return dedup counts |

## Notes

- **Validation**: Directory paths validated against GitHub tree API
- **Allowed Types**: skill, command, agent, mcp_server, hook
- **Error Codes**: 400 (bad request), 422 (validation error)
- **Response Fields**: duplicates_removed, cross_source_duplicates
