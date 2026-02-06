---
type: progress
prd: memory-context-system-v1
phase: 2
title: Service + API Layer
status: pending
started: '2026-02-05'
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 13
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- backend-architect
- python-backend-engineer
contributors:
- api-documenter
- api-librarian
tasks:
- id: SVC-2.1
  description: MemoryService - Core
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - REPO-1.6
  estimated_effort: 3 pts
  priority: critical
- id: SVC-2.2
  description: MemoryService - Lifecycle
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-2.1
  estimated_effort: 3 pts
  priority: critical
- id: SVC-2.3
  description: MemoryService - Merge
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.1
  estimated_effort: 2 pts
  priority: high
- id: SVC-2.4
  description: ContextModuleService
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-1.5
  estimated_effort: 2 pts
  priority: high
- id: SVC-2.5
  description: ContextPackerService
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-2.1
  - SVC-2.4
  estimated_effort: 3 pts
  priority: critical
- id: API-2.6
  description: Memory Items Router - CRUD
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.1
  estimated_effort: 2 pts
  priority: critical
- id: API-2.7
  description: Memory Items Router - Lifecycle
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.2
  estimated_effort: 2 pts
  priority: high
- id: API-2.8
  description: Memory Items Router - Merge
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.3
  estimated_effort: 1 pt
  priority: medium
- id: API-2.9
  description: Context Modules Router
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.4
  estimated_effort: 2 pts
  priority: high
- id: API-2.10
  description: Context Packing API
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-2.5
  estimated_effort: 2 pts
  priority: critical
- id: API-2.11
  description: OpenAPI Documentation
  status: pending
  assigned_to:
  - api-documenter
  dependencies:
  - API-2.10
  estimated_effort: 1 pt
  priority: medium
- id: TEST-2.12
  description: API Integration Tests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-2.10
  estimated_effort: 3 pts
  priority: high
- id: TEST-2.13
  description: End-to-End Service Test
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-2.12
  estimated_effort: 1 pt
  priority: medium
parallelization:
  batch_1:
  - SVC-2.1
  - SVC-2.4
  batch_2:
  - SVC-2.2
  - SVC-2.3
  - SVC-2.5
  batch_3:
  - API-2.6
  - API-2.7
  - API-2.8
  - API-2.9
  - API-2.10
  batch_4:
  - API-2.11
  - TEST-2.12
  batch_5:
  - TEST-2.13
  critical_path:
  - SVC-2.1
  - SVC-2.5
  - API-2.10
  - TEST-2.12
  - TEST-2.13
  estimated_total_time: 18 pts
blockers: []
success_criteria:
- id: SC-2.1
  description: All services passing unit tests (80%+ coverage)
  status: pending
- id: SC-2.2
  description: All API endpoints returning correct responses
  status: pending
- id: SC-2.3
  description: Cursor pagination working
  status: pending
- id: SC-2.4
  description: DTOs never expose ORM models
  status: pending
- id: SC-2.5
  description: ErrorResponse envelope consistent
  status: pending
- id: SC-2.6
  description: OpenAPI documentation complete
  status: pending
- id: SC-2.7
  description: Integration tests passing
  status: pending
files_modified: []
progress: 38
updated: '2026-02-05'
---

# memory-context-system-v1 - Phase 2: Service + API Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/memory-context-system-v1/phase-2-progress.md -t SVC-2.1 -s completed
```

---

## Objective

Implement business logic services and FastAPI routers that expose memory and context management functionality. This phase builds the service layer orchestrating repository operations, and the API layer providing RESTful endpoints with proper request/response DTOs, error handling, and OpenAPI documentation.

---

## Implementation Notes

### Architectural Decisions

- Service layer in `skillmeat/core/services/` handles business logic
- API routers in `skillmeat/api/routers/` delegate to services
- DTOs defined in `skillmeat/api/schemas/` never expose ORM models directly
- Dependency injection pattern for service instantiation
- Cursor-based pagination for list endpoints
- Consistent error envelope pattern using `ErrorResponse`

### Patterns and Best Practices

- Follow existing router patterns from `.claude/context/key-context/router-patterns.md`
- Services use repositories via dependency injection
- API endpoints return Pydantic models (DTOs), not ORM instances
- Use FastAPI dependency injection for service instances
- HTTP status codes: 200 (success), 201 (created), 204 (no content), 400 (validation), 404 (not found), 500 (server error)
- OpenAPI documentation uses tags for grouping: "Memory Items", "Context Modules", "Context Packing"

### Known Gotchas

- Avoid N+1 queries - use eager loading in repositories when needed
- DTOs must not leak ORM model internals (use `.model_dump()` carefully)
- Cursor pagination requires stable sort order and opaque cursor encoding
- Service layer exceptions should map to appropriate HTTP status codes
- Transaction boundaries should be at service layer, not repository layer
- OpenAPI schema generation requires proper Pydantic model examples

### Development Setup

```bash
# Run API server in development mode
skillmeat web dev --api-only

# Test specific router
pytest tests/api/test_memory_router.py -v

# Regenerate OpenAPI schema
python scripts/generate_openapi.py

# View OpenAPI docs
open http://localhost:8000/docs
```

---

## Completion Notes

*Fill in when phase is complete*

- What was built:
- Key learnings:
- Unexpected challenges:
- Recommendations for next phase:
