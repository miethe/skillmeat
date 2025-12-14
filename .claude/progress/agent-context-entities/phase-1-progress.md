---
type: progress
prd: "agent-context-entities"
phase: 1
phase_title: "Core Infrastructure"
status: pending
progress: 0
total_tasks: 9
completed_tasks: 0
created: "2025-12-14"
updated: "2025-12-14"

tasks:
  - id: "TASK-1.1"
    name: "Extend ArtifactType Enum"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimate: 1

  - id: "TASK-1.2"
    name: "Database Schema Migration"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-1.1"]
    estimate: 3

  - id: "TASK-1.3"
    name: "Context Entity Validation Module"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimate: 5

  - id: "TASK-1.4"
    name: "Markdown Parser with Frontmatter"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: 3

  - id: "TASK-1.5"
    name: "API Schemas for Context Entities"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimate: 3

  - id: "TASK-1.6"
    name: "Context Entities Router"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2", "TASK-1.3", "TASK-1.4", "TASK-1.5"]
    estimate: 5

  - id: "TASK-1.7"
    name: "Unit Tests for Validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3", "TASK-1.4"]
    estimate: 3

  - id: "TASK-1.8"
    name: "Integration Tests for API"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.6"]
    estimate: 2

  - id: "TASK-1.9"
    name: "Register Router in Server"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.6"]
    estimate: 1

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.3", "TASK-1.4"]
  batch_2: ["TASK-1.2"]
  batch_3: ["TASK-1.5", "TASK-1.7"]
  batch_4: ["TASK-1.6"]
  batch_5: ["TASK-1.8", "TASK-1.9"]
---

# Phase 1: Core Infrastructure

## Orchestration Quick Reference

**Batch 1** (Parallel):
- TASK-1.1 → `data-layer-expert` (1h)
- TASK-1.3 → `python-backend-engineer` (5h)
- TASK-1.4 → `python-backend-engineer` (3h)

**Batch 2** (Sequential):
- TASK-1.2 → `data-layer-expert` (3h)

**Batch 3** (Parallel):
- TASK-1.5 → `python-backend-engineer` (3h)
- TASK-1.7 → `python-backend-engineer` (3h)

**Batch 4** (Sequential):
- TASK-1.6 → `python-backend-engineer` (5h)

**Batch 5** (Parallel):
- TASK-1.8 → `python-backend-engineer` (2h)
- TASK-1.9 → `python-backend-engineer` (1h)

### Task Delegation Commands

**Batch 1**:
```python
Task("data-layer-expert", "TASK-1.1: Extend ArtifactType enum with 5 new context entity types (project_config, spec_file, rule_file, context_file, progress_template). File: skillmeat/core/artifact.py. Add docstrings for each type.")

Task("python-backend-engineer", "TASK-1.3: Create context entity validation module with validators for all 5 entity types. File: skillmeat/core/validators/context_entity.py. Include path traversal prevention, frontmatter validation, and structure validation per type.")

Task("python-backend-engineer", "TASK-1.4: Create markdown parser with frontmatter support. File: skillmeat/core/parsers/markdown_parser.py. Extract YAML frontmatter, validate structure, preserve original content for hashing.")
```

**Batch 2**:
```python
Task("data-layer-expert", "TASK-1.2: Create Alembic migration to add 4 columns to artifacts table (path_pattern, auto_load, category, content_hash). Update ArtifactType constraint. Create indexes for type+category and auto_load queries.")
```

**Batch 3**:
```python
Task("python-backend-engineer", "TASK-1.5: Create Pydantic schemas for context entities. File: skillmeat/api/schemas/context_entity.py. Implement ContextEntityCreateRequest, UpdateRequest, Response, ListResponse, ContentResponse with validators.")

Task("python-backend-engineer", "TASK-1.7: Create unit tests for validation and markdown parsing. Files: tests/unit/test_context_entity_validators.py, tests/unit/test_markdown_parser.py. Target 90%+ coverage. Test all 5 entity types and path traversal prevention.")
```

**Batch 4**:
```python
Task("python-backend-engineer", "TASK-1.6: Create FastAPI router with 7 endpoints for context entities (list, get, create, update, delete, get content, update content). File: skillmeat/api/routers/context_entities.py. Follow patterns from .claude/rules/api/routers.md.")
```

**Batch 5**:
```python
Task("python-backend-engineer", "TASK-1.8: Create integration tests for context entities API. File: tests/integration/test_context_entities_api.py. Test all endpoints, validation, error cases, path traversal rejection.")

Task("python-backend-engineer", "TASK-1.9: Register context entities router in server.py with prefix /api/v1/context-entities.")
```

## Quality Gates

- [ ] All tasks complete
- [ ] Database migration runs successfully (up and down)
- [ ] All 5 context entity types have validators
- [ ] API endpoints return correct status codes
- [ ] 90%+ test coverage for new code
- [ ] OpenAPI spec generates without errors
- [ ] No critical security issues (path traversal tests pass)
- [ ] Code review completed
- [ ] Documentation strings complete

## Notes

_Session notes go here_
