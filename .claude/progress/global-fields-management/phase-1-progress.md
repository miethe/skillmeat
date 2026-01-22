---
type: progress
prd: "global-fields-management"
phase: 1
status: pending
progress: 0

tasks:
  - id: "GFM-IMPL-1.1"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    model: "opus"

  - id: "GFM-IMPL-1.2"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["GFM-IMPL-1.1"]
    model: "opus"

  - id: "GFM-IMPL-1.3"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    model: "sonnet"

  - id: "GFM-IMPL-1.4"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["GFM-IMPL-1.2", "GFM-IMPL-1.3"]
    model: "opus"

  - id: "GFM-IMPL-1.5"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["GFM-IMPL-1.4"]
    model: "sonnet"

  - id: "GFM-IMPL-1.6"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["GFM-IMPL-1.2"]
    model: "sonnet"

parallelization:
  batch_1: ["GFM-IMPL-1.1", "GFM-IMPL-1.3"]
  batch_2: ["GFM-IMPL-1.2"]
  batch_3: ["GFM-IMPL-1.4", "GFM-IMPL-1.6"]
  batch_4: ["GFM-IMPL-1.5"]
---

# Phase 1: Backend Infrastructure & Field Registry

**Duration:** 5 days | **Effort:** 25 points

## Phase Goals

1. Create Field Registry system defining manageable fields per object type
2. Implement FieldsService wrapping existing TagService
3. Create `/api/v1/fields/*` router with CRUD endpoints
4. Define API schemas (request/response DTOs)
5. Establish error handling and validation patterns

## Tasks

### GFM-IMPL-1.1: Create Field Registry
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 5 pts

Define FieldRegistry class to enumerate manageable fields per object type (Artifacts: Tags, Origin; Marketplace Sources: Tags, Trust Level, Visibility, Auto Tags).

**Acceptance Criteria:**
- Registry loads from config, returns field metadata with constraints (name, type, readonly, enum values)

---

### GFM-IMPL-1.2: Create FieldsService
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 5 pts

Implement FieldsService wrapping TagService for tag operations; add validation for field constraints (uniqueness, in-use checks, cascade deletes).

**Acceptance Criteria:**
- Service methods: list_field_options(), create_option(), update_option(), delete_option()
- Handles tag normalization via TagService._slugify()

**Dependencies:** GFM-IMPL-1.1

---

### GFM-IMPL-1.3: Create Field Schemas
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 3 pts

Define Pydantic request/response models: FieldOptionResponse, FieldListResponse, CreateFieldOptionRequest, UpdateFieldOptionRequest with proper validation rules.

**Acceptance Criteria:**
- All schemas include validation (color format, name constraints, enum validation)
- Use PageInfo for pagination

---

### GFM-IMPL-1.4: Create Fields Router
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 5 pts

Implement `/api/v1/fields` router with endpoints: GET /fields, POST /fields/options, PUT /fields/options/{id}, DELETE /fields/options/{id}; integrate with FieldsService.

**Acceptance Criteria:**
- All endpoints return proper status codes (201 create, 204 delete)
- Errors return ErrorResponse envelope
- Pagination cursor-based

**Dependencies:** GFM-IMPL-1.2, GFM-IMPL-1.3

---

### GFM-IMPL-1.5: Error Handling & Validation
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 3 pts

Implement validation layer for field operations (name uniqueness, color format, in-use prevention, cascade audit logging).

**Acceptance Criteria:**
- 409 Conflict for duplicates
- 422 Unprocessable for validation
- 400 for in-use errors
- Logs trace_id for cascade operations

**Dependencies:** GFM-IMPL-1.4

---

### GFM-IMPL-1.6: Unit Tests: FieldsService
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 4 pts

Write tests covering FieldsService methods: tag creation, normalization, cascade validation, in-use detection.

**Acceptance Criteria:**
- >80% line coverage
- Test cases: create tag, duplicate rejection, cascade delete, usage count

**Dependencies:** GFM-IMPL-1.2

---

## Quality Gates

- [ ] All FieldsService methods tested with >80% coverage
- [ ] API endpoints return correct status codes and error envelopes
- [ ] Tag normalization behaves identically to existing TagService._slugify()
- [ ] Cascade operations logged with trace_id
- [ ] Documentation (docstrings) for FieldRegistry and FieldsService

## Dependencies

- Existing TagService (no changes required)
- SQLAlchemy ORM models (Tag, ArtifactTag, MarketplaceSource)
- Pydantic schemas infrastructure

## Notes

This phase establishes the backend foundation. Batches 1 and 3 can run in parallel to maximize velocity.
