---
type: progress
prd: request-log-viewer-v1
phase: 1
title: Backend API Foundation
status: pending
progress: 0
total_tasks: 6
completed_tasks: 0
blocked_tasks: 0
created: '2025-01-30'
updated: '2025-01-30'
tasks:
- id: TASK-1.1
  title: Create RequestLogManager class
  status: pending
  priority: high
  estimate: 2d
  assigned_to:
  - python-backend-engineer
  dependencies: []
  file_targets:
  - skillmeat/api/app/managers/request_log_manager.py
  notes: Subprocess wrapper for meatycapture CLI commands (list, view, search)
- id: TASK-1.2
  title: Create Pydantic DTOs/schemas
  status: pending
  priority: high
  estimate: 1d
  assigned_to:
  - python-backend-engineer
  dependencies: []
  file_targets:
  - skillmeat/api/app/schemas/request_log.py
  notes: RequestLogListItem, RequestLogDetail, RequestLogSearchQuery schemas
- id: TASK-1.3
  title: Create list endpoint
  status: pending
  priority: high
  estimate: 1d
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  - TASK-1.2
  file_targets:
  - skillmeat/api/app/routers/request_logs.py
  notes: GET /api/v1/request-logs - list all logs with pagination, type/status filtering
- id: TASK-1.4
  title: Create detail endpoint
  status: pending
  priority: high
  estimate: 1d
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  - TASK-1.2
  file_targets:
  - skillmeat/api/app/routers/request_logs.py
  notes: GET /api/v1/request-logs/{log_id} - return full log details
- id: TASK-1.5
  title: Create search endpoint
  status: pending
  priority: high
  estimate: 1.5d
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  - TASK-1.2
  file_targets:
  - skillmeat/api/app/routers/request_logs.py
  notes: POST /api/v1/request-logs/search - advanced search with filters, date ranges,
    text query
- id: TASK-1.6
  title: Write API integration tests
  status: pending
  priority: medium
  estimate: 1d
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
  file_targets:
  - skillmeat/api/tests/routers/test_request_logs.py
  notes: Test all endpoints, error cases, filtering, pagination. Target >80% coverage
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.2
  batch_2:
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
  batch_3:
  - TASK-1.6
blockers: []
references:
  prd: .claude/prds/request-log-viewer-v1.md
  meatycapture_spec: .claude/skills/meatycapture-capture/SKILL.md
schema_version: 2
doc_type: progress
feature_slug: request-log-viewer-v1
---

# Phase 1: Backend API Foundation

## Summary

Phase 1 establishes the backend API infrastructure for request log viewing. This phase creates the RequestLogManager for subprocess integration with meatycapture CLI, defines Pydantic schemas for request/response contracts, and implements three core endpoints (list, detail, search) with comprehensive test coverage.

**Estimated Effort**: 7.5 days (sequential batches)
**Dependencies**: None (foundational phase)
**Assigned Agents**: python-backend-engineer

## Success Criteria

- SC-1: RequestLogManager subprocess integration works with meatycapture CLI
- SC-2: All three endpoints return valid JSON responses
- SC-3: API tests achieve >80% coverage
- SC-4: Error handling for missing CLI implemented

## Orchestration Quick Reference

### Batch 1 (Parallel - Foundation)

**TASK-1.1** and **TASK-1.2** can run in parallel.

**TASK-1.1** → `python-backend-engineer` (2d)

```
Task("python-backend-engineer", "TASK-1.1: Create RequestLogManager class.

File: skillmeat/api/app/managers/request_log_manager.py

Create manager class that wraps meatycapture CLI via subprocess:

Methods:
1. list_logs(type: str | None, status: str | None, limit: int, offset: int) -> list[dict]
   - Calls: meatycapture log list --format json [filters]
   - Returns parsed JSON list

2. get_log_detail(log_id: str) -> dict
   - Calls: meatycapture log view {log_id} --format json
   - Returns parsed JSON detail

3. search_logs(query: str, filters: dict) -> list[dict]
   - Calls: meatycapture log search {query} --format json [filters]
   - Returns parsed JSON results

Error handling:
- Catch subprocess failures (CLI not found, invalid log_id)
- Raise domain exceptions (RequestLogNotFound, RequestLogCLIError)

Follow patterns in existing managers for subprocess execution.
Use subprocess.run() with capture_output=True, text=True.")
```

**TASK-1.2** → `python-backend-engineer` (1d)

```
Task("python-backend-engineer", "TASK-1.2: Create Pydantic DTOs/schemas.

File: skillmeat/api/app/schemas/request_log.py

Create schemas:

1. RequestLogListItem (response schema for list endpoint):
   - id: str
   - type: str (enhancement, bug, idea, task, question)
   - status: str (pending, in_progress, completed, declined)
   - title: str
   - created_at: datetime
   - updated_at: datetime | None
   - domain: str | None
   - subdomain: str | None
   - priority: str | None

2. RequestLogDetail (response schema for detail endpoint):
   - All fields from RequestLogListItem
   - problem: str
   - goal: str
   - notes: str | None
   - context: str | None
   - project: str | None
   - tags: list[str]

3. RequestLogSearchQuery (request schema for search endpoint):
   - query: str (text to search)
   - type: str | None
   - status: str | None
   - domain: str | None
   - subdomain: str | None
   - priority: str | None
   - date_from: datetime | None
   - date_to: datetime | None

Follow existing schema patterns in skillmeat/api/app/schemas/.
Use Field() for validation and descriptions.")
```

### Batch 2 (Parallel - Depends on Batch 1)

**TASK-1.3**, **TASK-1.4**, and **TASK-1.5** all depend on TASK-1.1 and TASK-1.2 completing. They can run in parallel.

**TASK-1.3** → `python-backend-engineer` (1d)

```
Task("python-backend-engineer", "TASK-1.3: Create list endpoint.

File: skillmeat/api/app/routers/request_logs.py

Create router with GET /api/v1/request-logs endpoint:

@router.get('/request-logs', response_model=list[RequestLogListItem])
async def list_request_logs(
    type: str | None = None,
    status: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
) -> list[RequestLogListItem]:
    \"\"\"List request logs with optional filters and pagination.\"\"\"
    manager = RequestLogManager()
    logs = manager.list_logs(type, status, limit, offset)
    return [RequestLogListItem(**log) for log in logs]

Error handling:
- Catch RequestLogCLIError → 503 Service Unavailable
- Log errors before raising HTTPException

Follow router patterns from existing routers.
Import RequestLogManager from TASK-1.1, schemas from TASK-1.2.")
```

**TASK-1.4** → `python-backend-engineer` (1d)

```
Task("python-backend-engineer", "TASK-1.4: Create detail endpoint.

File: skillmeat/api/app/routers/request_logs.py

Add GET /api/v1/request-logs/{log_id} endpoint to router:

@router.get('/request-logs/{log_id}', response_model=RequestLogDetail)
async def get_request_log(log_id: str) -> RequestLogDetail:
    \"\"\"Get full details for a specific request log.\"\"\"
    manager = RequestLogManager()
    log = manager.get_log_detail(log_id)
    return RequestLogDetail(**log)

Error handling:
- Catch RequestLogNotFound → 404 Not Found
- Catch RequestLogCLIError → 503 Service Unavailable
- Log errors before raising HTTPException

Import RequestLogManager and schemas.
Add to same router file as TASK-1.3.")
```

**TASK-1.5** → `python-backend-engineer` (1.5d)

```
Task("python-backend-engineer", "TASK-1.5: Create search endpoint.

File: skillmeat/api/app/routers/request_logs.py

Add POST /api/v1/request-logs/search endpoint to router:

@router.post('/request-logs/search', response_model=list[RequestLogListItem])
async def search_request_logs(
    search_query: RequestLogSearchQuery
) -> list[RequestLogListItem]:
    \"\"\"Advanced search for request logs with filters and date ranges.\"\"\"
    manager = RequestLogManager()

    # Build filter dict from search_query
    filters = {
        'type': search_query.type,
        'status': search_query.status,
        'domain': search_query.domain,
        'subdomain': search_query.subdomain,
        'priority': search_query.priority,
        'date_from': search_query.date_from,
        'date_to': search_query.date_to
    }

    logs = manager.search_logs(search_query.query, filters)
    return [RequestLogListItem(**log) for log in logs]

Error handling:
- Catch RequestLogCLIError → 503 Service Unavailable
- Validate date ranges (date_from < date_to)
- Log errors before raising HTTPException

Import RequestLogManager and schemas.
Add to same router file as TASK-1.3 and TASK-1.4.")
```

### Batch 3 (Sequential - Depends on Batch 2)

**TASK-1.6** → `python-backend-engineer` (1d)

```
Task("python-backend-engineer", "TASK-1.6: Write API integration tests.

File: skillmeat/api/tests/routers/test_request_logs.py

Test cases:

List endpoint (GET /api/v1/request-logs):
1. List all logs - success (200)
2. List with type filter - success (200)
3. List with status filter - success (200)
4. List with pagination (limit, offset) - success (200)
5. CLI not available - service unavailable (503)

Detail endpoint (GET /api/v1/request-logs/{log_id}):
6. Get existing log - success (200)
7. Get non-existent log - not found (404)
8. CLI not available - service unavailable (503)

Search endpoint (POST /api/v1/request-logs/search):
9. Search with text query - success (200)
10. Search with all filters - success (200)
11. Search with date range - success (200)
12. Invalid date range (from > to) - validation error (422)
13. CLI not available - service unavailable (503)

Mock RequestLogManager methods.
Use pytest-mock for mocking.
Follow patterns from existing router tests.
Run: pytest tests/routers/test_request_logs.py -v --cov=skillmeat.api.app.routers.request_logs --cov-report=term
Target: >80% coverage")
```

## Key Files

| File | Purpose | LOC Est. |
|------|---------|----------|
| `managers/request_log_manager.py` | CLI subprocess wrapper | ~150 |
| `schemas/request_log.py` | Pydantic DTOs | ~80 |
| `routers/request_logs.py` | FastAPI router with 3 endpoints | ~120 |
| `tests/routers/test_request_logs.py` | Integration tests | ~200 |

## Acceptance Criteria

- [ ] RequestLogManager successfully calls meatycapture CLI commands
- [ ] RequestLogManager handles subprocess errors gracefully
- [ ] All three Pydantic schemas validate correctly
- [ ] List endpoint supports type/status filtering and pagination
- [ ] Detail endpoint returns 404 for non-existent logs
- [ ] Search endpoint supports all filter parameters
- [ ] All tests pass with >80% coverage
- [ ] HTTPException error handling follows router patterns
- [ ] CLI unavailability returns 503 Service Unavailable

## Notes

- **CLI Dependency**: meatycapture CLI must be installed and available in PATH
- **JSON Format**: All CLI commands must use `--format json` flag
- **Error Handling**: Distinguish between CLI not found (503) vs log not found (404)
- **Pattern Reference**: Existing managers for subprocess patterns
- **Pattern Reference**: Existing routers for error handling and response models
- **Future Work**: Phase 2 will add frontend components consuming these APIs
