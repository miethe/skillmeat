---
type: progress
prd: "collection-refresh"
phase: 3
title: "API Endpoint Implementation"
status: pending
progress: 0
created: 2025-01-21
updated: 2025-01-21

tasks:
  # 3.1: API Schemas & Models
  - id: "BE-301"
    name: "Create RefreshRequest schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["Phase 1"]
    estimate: "0.5 pts"

  - id: "BE-302"
    name: "Create RefreshResponse schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["Phase 1"]
    estimate: "0.75 pts"

  - id: "BE-303"
    name: "Create RefreshError schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["Phase 1"]
    estimate: "0.25 pts"

  # 3.2: API Endpoint Implementation
  - id: "BE-304"
    name: "Add refresh endpoint signature"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-301", "BE-302"]
    estimate: "0.75 pts"

  - id: "BE-305"
    name: "Implement collection validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.5 pts"

  - id: "BE-306"
    name: "Implement query parameter support"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.5 pts"

  - id: "BE-307"
    name: "Wire CollectionRefresher to endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.75 pts"

  - id: "BE-308"
    name: "Implement result serialization"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.5 pts"

  - id: "BE-309"
    name: "Add error handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.75 pts"

  - id: "BE-310"
    name: "Add logging"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.5 pts"

  # 3.3: API Tests
  - id: "BE-311"
    name: "Unit test: endpoint signature"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "0.75 pts"

  - id: "BE-312"
    name: "Unit test: collection validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-305"]
    estimate: "0.5 pts"

  - id: "BE-313"
    name: "Unit test: request body handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-301"]
    estimate: "0.75 pts"

  - id: "BE-314"
    name: "Unit test: query parameter handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-306"]
    estimate: "0.75 pts"

  - id: "BE-315"
    name: "Integration test: full endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "1.5 pts"

  - id: "BE-316"
    name: "Integration test: error handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-309"]
    estimate: "1 pt"

  - id: "BE-317"
    name: "Performance test: scalability"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["BE-304"]
    estimate: "1 pt"

parallelization:
  batch_1: ["BE-301", "BE-302", "BE-303"]
  batch_2: ["BE-304"]
  batch_3: ["BE-305", "BE-306", "BE-307", "BE-308", "BE-309", "BE-310"]
  batch_4: ["BE-311", "BE-312", "BE-313", "BE-314", "BE-315", "BE-316", "BE-317"]

quality_gates:
  - "RefreshRequest and RefreshResponse schemas valid and documented"
  - "POST /api/v1/collections/{collection_id}/refresh endpoint registered"
  - "Collection validation returns 404 for invalid IDs"
  - "Query parameter mode override works correctly"
  - "CollectionRefresher integrated and called correctly"
  - "Results serialized to JSON with all fields present"
  - "Error handling returns appropriate status codes (400, 422, 404, 500)"
  - "Refresh operations logged with collection_id and duration"
  - "Unit tests pass with >85% endpoint coverage"
  - "Performance acceptable for large collections (<30s)"
  - "OpenAPI spec updated with new endpoint"
---

# Phase 3: API Endpoint Implementation

**Duration**: 3-4 days | **Total Effort**: 12 story points | **Status**: Pending

## Overview

Implement the REST API endpoint for refreshing collection artifacts, enabling frontend integration and programmatic access to the refresh functionality.

## Key Files

| File | Action | Purpose |
|------|--------|---------|
| `skillmeat/api/routers/collections.py` | MODIFY | Add refresh endpoint |
| `skillmeat/api/schemas/collections.py` | MODIFY | Add request/response schemas |
| `skillmeat/api/openapi.json` | AUTO | Updated via spec generation |
| `tests/integration/test_refresh_api.py` | CREATE | API integration tests |

## Dependencies

- Phase 1 must be complete (CollectionRefresher tested and ready)
- Can run in parallel with Phase 2 (CLI)

## API Design

```
POST /api/v1/collections/{collection_id}/refresh
  ?mode=metadata    # Refresh metadata only (default)
  ?mode=check       # Check for updates without applying
  ?mode=sync        # Full sync (future)

Request Body (optional):
{
  "mode": "metadata_only",
  "artifact_filter": {
    "type": "skill",
    "name_pattern": "canvas*"
  }
}

Response:
{
  "status": "success",
  "timestamp": "2025-01-21T...",
  "request_id": "uuid",
  "result": {
    "refreshed_count": 15,
    "unchanged_count": 3,
    "skipped_count": 5,
    "error_count": 2,
    "entries": [...],
    "duration_ms": 1234.5
  },
  "took_ms": 1250.0
}
```

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-refresh/phase-3-progress.md \
  -t BE-301 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-refresh/phase-3-progress.md \
  --updates "BE-301:completed,BE-302:completed"
```

## Delegation Commands

```python
# API schemas (batch_1)
Task("python-backend-engineer", """
Implement Phase 3 batch_1 for collection-refresh API:
- BE-301: Create RefreshRequest schema (mode, artifact_filter)
- BE-302: Create RefreshResponse schema (status, timestamp, result)
- BE-303: Create RefreshError schema

Use Pydantic patterns from existing API schemas.
Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")

# API endpoint (batch_2 + batch_3)
Task("python-backend-engineer", """
Implement Phase 3 API endpoint for collection-refresh:
- BE-304: POST /api/v1/collections/{collection_id}/refresh
- BE-305: Collection validation (404 if not found)
- BE-306: Query parameter ?mode= support
- BE-307: Wire CollectionRefresher
- BE-308: Result JSON serialization
- BE-309: Error handling (400, 422, 404, 500)
- BE-310: Logging

Follow FastAPI patterns from existing routers.
Reference: skillmeat/api/routers/collections.py
""")
```

## Notes

- Follow existing API patterns in collections.py router
- Ensure OpenAPI spec is regenerated after adding endpoint
- Consider response streaming for large collections (future)
