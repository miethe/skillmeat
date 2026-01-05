---
prd: path-based-tag-extraction-v1
phase: 1
name: "Backend Foundation & API"
status: completed
created: 2026-01-04
updated: 2026-01-04
completed_at: 2026-01-04T21:15:00Z
completion: 100

tasks:
  - id: "TASK-1.1"
    name: "Database Migration"
    status: "completed"
    assigned_to: ["data-layer-expert"]
    model: "sonnet"
    dependencies: []
    estimated_effort: "1h"

  - id: "TASK-1.2"
    name: "Update Models"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.1"]
    estimated_effort: "1h"

  - id: "TASK-1.3"
    name: "PathTagConfig & ExtractedSegment Dataclasses"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    estimated_effort: "2h"

  - id: "TASK-1.4"
    name: "PathSegmentExtractor Service"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.3"]
    estimated_effort: "3h"

  - id: "TASK-1.5"
    name: "Scanner Integration"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.2", "TASK-1.4"]
    estimated_effort: "2h"

  - id: "TASK-1.6"
    name: "API Schemas"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.3"]
    estimated_effort: "1h"

  - id: "TASK-1.7"
    name: "GET Path Tags Endpoint"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.2", "TASK-1.6"]
    estimated_effort: "1.5h"

  - id: "TASK-1.8"
    name: "PATCH Path Tags Endpoint"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.7"]
    estimated_effort: "1.5h"

  - id: "TASK-1.9"
    name: "Unit Tests - Extractor"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.4"]
    estimated_effort: "2h"

  - id: "TASK-1.10"
    name: "Unit Tests - API"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.7", "TASK-1.8"]
    estimated_effort: "2h"

  - id: "TASK-1.11"
    name: "Integration Tests"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-1.5", "TASK-1.8"]
    estimated_effort: "2h"

  - id: "TASK-1.12"
    name: "Documentation"
    status: "completed"
    assigned_to: ["documentation-writer"]
    model: "haiku"
    dependencies: ["TASK-1.11"]
    estimated_effort: "1h"

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.3"]
  batch_2: ["TASK-1.2", "TASK-1.4", "TASK-1.6"]
  batch_3: ["TASK-1.5", "TASK-1.7", "TASK-1.9"]
  batch_4: ["TASK-1.8", "TASK-1.10"]
  batch_5: ["TASK-1.11"]
  batch_6: ["TASK-1.12"]
---

# Phase 1: Backend Foundation & API

## Overview

Implement backend infrastructure for path-based tag extraction, including database schema, extractor service, scanner integration, and API endpoints.

## Progress Summary

- **Total Tasks**: 12
- **Completed**: 0
- **In Progress**: 0
- **Blocked**: 0
- **Not Started**: 12

## Task Details

### Batch 1 (Parallel - Independent)

#### TASK-1.1: Database Migration
**Status**: Pending
**Owner**: data-layer-expert (sonnet)
**Effort**: 1h

Add `path_tags` JSONB column to `marketplace_sources` table.

**Deliverables**:
- Alembic migration file: `add_path_tags_column.py`
- Column: `path_tags JSONB DEFAULT '{}'::jsonb NOT NULL`
- Migration tested with up/down

#### TASK-1.3: PathTagConfig & ExtractedSegment Dataclasses
**Status**: Pending
**Owner**: python-backend-engineer (opus)
**Effort**: 2h

Create core dataclasses for path segment extraction.

**Deliverables**:
- `skillmeat/core/marketplace/path_tags.py`:
  - `PathTagConfig` dataclass with `pattern`, `segment_type`, `transform`
  - `ExtractedSegment` dataclass with `value`, `segment_type`, `original_value`
  - Constants: `DEFAULT_PATH_TAG_PATTERNS`
- Type hints for all fields
- Docstrings with examples

---

### Batch 2 (Parallel - After Batch 1)

#### TASK-1.2: Update Models
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 1h
**Dependencies**: TASK-1.1

Add `path_tags` field to SQLAlchemy model.

**Deliverables**:
- Update `skillmeat/api/models/marketplace_source.py`:
  - Add `path_tags = Column(JSONB, default=dict, nullable=False)`
- Update corresponding schema if needed

#### TASK-1.4: PathSegmentExtractor Service
**Status**: Pending
**Owner**: python-backend-engineer (opus)
**Effort**: 3h
**Dependencies**: TASK-1.3

Implement core extraction logic.

**Deliverables**:
- `skillmeat/core/marketplace/extractor.py`:
  - `PathSegmentExtractor` class
  - `extract_segments(path: str, configs: list[PathTagConfig])` method
  - Regex pattern matching logic
  - Transform functions (lowercase, titlecase, etc.)
- Error handling for malformed patterns
- Comprehensive docstrings

#### TASK-1.6: API Schemas
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 1h
**Dependencies**: TASK-1.3

Create Pydantic schemas for API requests/responses.

**Deliverables**:
- `skillmeat/api/schemas/marketplace.py` updates:
  - `PathTagSegmentResponse` schema
  - `PathTagsResponse` schema
  - `PathTagsPatchRequest` schema
- Include examples in docstrings

---

### Batch 3 (Parallel - After Batch 2)

#### TASK-1.5: Scanner Integration
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-1.2, TASK-1.4

Integrate extractor into marketplace scanner workflow.

**Deliverables**:
- Update `skillmeat/core/marketplace/scanner.py`:
  - Call `PathSegmentExtractor.extract_segments()` during scan
  - Store extracted segments in `path_tags` column
  - Log extraction results
- Handle extraction failures gracefully

#### TASK-1.7: GET Path Tags Endpoint
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 1.5h
**Dependencies**: TASK-1.2, TASK-1.6

Create API endpoint to retrieve path tags for a source.

**Deliverables**:
- `skillmeat/api/routers/marketplace.py` update:
  - `GET /api/v1/marketplace-sources/{source_id}/path-tags`
  - Return `PathTagsResponse`
  - Handle 404 if source not found
- OpenAPI documentation

#### TASK-1.9: Unit Tests - Extractor
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-1.4

Test extraction logic in isolation.

**Deliverables**:
- `tests/unit/test_path_extractor.py`:
  - Test default patterns (org, repo, category, skill-name)
  - Test custom patterns
  - Test transform functions
  - Test edge cases (missing segments, malformed paths)
  - >80% coverage

---

### Batch 4 (Parallel - After Batch 3)

#### TASK-1.8: PATCH Path Tags Endpoint
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 1.5h
**Dependencies**: TASK-1.7

Create API endpoint to manually override path tags.

**Deliverables**:
- `skillmeat/api/routers/marketplace.py` update:
  - `PATCH /api/v1/marketplace-sources/{source_id}/path-tags`
  - Accept `PathTagsPatchRequest`
  - Merge with existing tags (override mode)
  - Return updated `PathTagsResponse`
- OpenAPI documentation

#### TASK-1.10: Unit Tests - API
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-1.7, TASK-1.8

Test API endpoints.

**Deliverables**:
- `tests/unit/test_marketplace_path_tags_api.py`:
  - Test GET endpoint (success, 404)
  - Test PATCH endpoint (success, validation errors, 404)
  - Mock database interactions
  - >80% coverage

---

### Batch 5 (Sequential - After Batch 4)

#### TASK-1.11: Integration Tests
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-1.5, TASK-1.8

End-to-end tests for scanner + API workflow.

**Deliverables**:
- `tests/integration/test_path_tags_workflow.py`:
  - Test: Scan source → verify path_tags populated
  - Test: GET path tags → verify response
  - Test: PATCH path tags → verify persistence
  - Test: Re-scan preserves manual overrides
- Use test database

---

### Batch 6 (Sequential - After Batch 5)

#### TASK-1.12: Documentation
**Status**: Pending
**Owner**: documentation-writer (haiku)
**Effort**: 1h
**Dependencies**: TASK-1.11

Document API endpoints and usage patterns.

**Deliverables**:
- Update `docs/api/marketplace.md`:
  - Document GET/PATCH endpoints
  - Include examples
  - Describe default patterns
- Update `README.md` if needed

---

## Orchestration Quick Reference

### Batch 1 (Parallel)
```
Task("data-layer-expert", "TASK-1.1: Create Alembic migration for path_tags JSONB column in marketplace_sources table. Column should be NOT NULL with default empty JSON object. Include up/down migration.", model="sonnet")
Task("python-backend-engineer", "TASK-1.3: Create PathTagConfig and ExtractedSegment dataclasses in skillmeat/core/marketplace/path_tags.py. Include DEFAULT_PATH_TAG_PATTERNS constant with org, repo, category, skill-name patterns. Add transform functions (lowercase, titlecase). Full type hints and docstrings.", model="opus")
```

### Batch 2 (Parallel - After Batch 1)
```
Task("python-backend-engineer", "TASK-1.2: Add path_tags JSONB column to MarketplaceSource SQLAlchemy model in skillmeat/api/models/marketplace_source.py. Use Column(JSONB, default=dict, nullable=False).", model="sonnet")
Task("python-backend-engineer", "TASK-1.4: Implement PathSegmentExtractor service in skillmeat/core/marketplace/extractor.py. Class should have extract_segments(path, configs) method that uses regex to extract segments based on PathTagConfig patterns. Include transform logic. Handle errors gracefully.", model="opus")
Task("python-backend-engineer", "TASK-1.6: Create Pydantic schemas for path tags API in skillmeat/api/schemas/marketplace.py: PathTagSegmentResponse, PathTagsResponse, PathTagsPatchRequest. Include docstring examples.", model="sonnet")
```

### Batch 3 (Parallel - After Batch 2)
```
Task("python-backend-engineer", "TASK-1.5: Integrate PathSegmentExtractor into marketplace scanner (skillmeat/core/marketplace/scanner.py). Call extractor during scan, store results in path_tags column, log extraction. Handle failures gracefully.", model="sonnet")
Task("python-backend-engineer", "TASK-1.7: Create GET /api/v1/marketplace-sources/{source_id}/path-tags endpoint in skillmeat/api/routers/marketplace.py. Return PathTagsResponse. Handle 404. Add OpenAPI docs.", model="sonnet")
Task("python-backend-engineer", "TASK-1.9: Write unit tests for PathSegmentExtractor in tests/unit/test_path_extractor.py. Test default patterns, custom patterns, transforms, edge cases. >80% coverage.", model="sonnet")
```

### Batch 4 (Parallel - After Batch 3)
```
Task("python-backend-engineer", "TASK-1.8: Create PATCH /api/v1/marketplace-sources/{source_id}/path-tags endpoint in skillmeat/api/routers/marketplace.py. Accept PathTagsPatchRequest, merge with existing tags, return updated PathTagsResponse. Add OpenAPI docs.", model="sonnet")
Task("python-backend-engineer", "TASK-1.10: Write unit tests for path tags API endpoints in tests/unit/test_marketplace_path_tags_api.py. Test GET (success, 404), PATCH (success, validation, 404). Mock DB. >80% coverage.", model="sonnet")
```

### Batch 5 (Sequential - After Batch 4)
```
Task("python-backend-engineer", "TASK-1.11: Write integration tests in tests/integration/test_path_tags_workflow.py. Test: scan→verify path_tags, GET endpoint, PATCH endpoint, re-scan preserves overrides. Use test DB.", model="sonnet")
```

### Batch 6 (Sequential - After Batch 5)
```
Task("documentation-writer", "TASK-1.12: Document path tags API endpoints in docs/api/marketplace.md. Include GET/PATCH examples, describe default patterns. Update README.md if needed.", model="haiku")
```

---

## Critical Files

### Database Layer
- `skillmeat/api/migrations/versions/{timestamp}_add_path_tags_column.py`
- `skillmeat/api/models/marketplace_source.py`

### Business Logic
- `skillmeat/core/marketplace/path_tags.py`
- `skillmeat/core/marketplace/extractor.py`
- `skillmeat/core/marketplace/scanner.py`

### API Layer
- `skillmeat/api/schemas/marketplace.py`
- `skillmeat/api/routers/marketplace.py`

### Tests
- `tests/unit/test_path_extractor.py`
- `tests/unit/test_marketplace_path_tags_api.py`
- `tests/integration/test_path_tags_workflow.py`

---

## Success Criteria

- [ ] Migration runs cleanly (up/down)
- [ ] Extractor extracts segments from sample paths
- [ ] Scanner populates path_tags during scan
- [ ] GET endpoint returns extracted tags
- [ ] PATCH endpoint persists manual overrides
- [ ] All tests pass (>80% coverage)
- [ ] API endpoints documented

---

## Notes

- Use Sonnet for straightforward implementation tasks (migrations, schemas, simple endpoints)
- Use Opus for complex logic (extractor service, dataclass design)
- Use Haiku for documentation (low complexity)
- All parallel batches can run simultaneously for maximum efficiency
