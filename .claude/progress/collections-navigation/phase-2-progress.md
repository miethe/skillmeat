---
type: progress
prd: collections-navigation
phase: 2
title: Backend API - Collections & Groups CRUD
status: pending
overall_progress: 0
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- backend-architect
tasks:
- id: TASK-2.1
  name: Collections CRUD Router
  description: FastAPI router for collection management endpoints
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: TASK-2.2
  name: Groups CRUD Router
  description: FastAPI router for group management endpoints
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: TASK-2.3
  name: Collection-Artifact Association Endpoints
  description: Endpoints for managing artifact membership in collections (add, remove,
    move, copy)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 2h
  priority: high
- id: TASK-2.4
  name: Group-Artifact Association Endpoints
  description: Endpoints for managing artifact membership in groups with position/reordering
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.2
  estimated_effort: 2h
  priority: high
- id: TASK-2.5
  name: Deployment Summary Endpoints
  description: API endpoints for deployment dashboard data (aggregations and summaries)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2h
  priority: medium
- id: TASK-2.6
  name: Pydantic Schemas
  description: Request/response models for all new endpoints
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1h
  priority: high
parallelization:
  batch_1:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.5
  - TASK-2.6
  batch_2:
  - TASK-2.3
  - TASK-2.4
  critical_path:
  - TASK-2.1
  - TASK-2.3
  estimated_total_time: 1.5w
blockers: []
success_criteria:
- id: SC-1
  description: All CRUD routers implemented and tested
  status: pending
- id: SC-2
  description: Link/unlink/move/copy operations working correctly
  status: pending
- id: SC-3
  description: Deployment summary endpoints returning correct aggregations
  status: pending
- id: SC-4
  description: All Pydantic models created with proper validation
  status: pending
- id: SC-5
  description: Consistent error handling across all endpoints
  status: pending
- id: SC-6
  description: Test coverage >90% for router code
  status: pending
- id: SC-7
  description: All endpoints respond in <100ms (deployment summary <100ms)
  status: pending
- id: SC-8
  description: OpenAPI docs auto-generated and accurate
  status: pending
files_modified: []
schema_version: 2
doc_type: progress
feature_slug: collections-navigation
---

# collections-navigation - Phase 2: Backend API

**Phase**: 2 of 6
**Status**: Pending (0% complete)
**Owner**: python-backend-engineer
**Contributors**: backend-architect
**Dependencies**: Phase 1 (Database Layer)

---

## Phase Objective

Implement FastAPI routers, Pydantic schemas, and service layer logic for Collections and Groups management. This phase bridges the database layer with frontend API consumers.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Routers and Schemas):
- TASK-2.1 → `python-backend-engineer` (3h) - Collections CRUD router
- TASK-2.2 → `python-backend-engineer` (3h) - Groups CRUD router
- TASK-2.5 → `python-backend-engineer` (2h) - Deployment summary endpoints
- TASK-2.6 → `python-backend-engineer` (1h) - Pydantic schemas

**Batch 2** (Parallel - Associations, after Batch 1):
- TASK-2.3 → `python-backend-engineer` (2h) - Collection-artifact endpoints
- TASK-2.4 → `python-backend-engineer` (2h) - Group-artifact endpoints

### Task Delegation Commands

```
# Batch 1 (Parallel)
Task("python-backend-engineer", "TASK-2.1: Create FastAPI router at /api/v1/collections with endpoints: GET / (list with pagination, search), POST / (create), GET /{id} (get with groups), PUT /{id} (update), DELETE /{id} (cascade delete). Include proper validation, error handling (400/404/500), auth, and CORS. Files: /skillmeat/api/routers/collections.py, update /skillmeat/api/server.py")

Task("python-backend-engineer", "TASK-2.2: Create FastAPI router at /api/v1/groups with endpoints: POST / (create in collection), GET ?collection_id={id} (list by collection), GET /{id} (get with artifacts), PUT /{id} (update), DELETE /{id} (cascade), PUT /reorder (bulk reorder). Include validation for unique names per collection, position ordering, error handling, auth. Files: /skillmeat/api/routers/groups.py, update /skillmeat/api/server.py")

Task("python-backend-engineer", "TASK-2.5: Create deployment summary endpoints at /api/v1/deployments with: GET /summary (aggregated stats by status/artifact/project), GET ?artifact_id={id} (deployments for artifact), GET ?project_id={id} (deployments in project), POST / (create), PUT /{id} (update). Optimize queries for <100ms performance. Files: /skillmeat/api/routers/deployments_enhanced.py, update /skillmeat/api/server.py")

Task("python-backend-engineer", "TASK-2.6: Create Pydantic schemas for Collections (CollectionCreateRequest, CollectionUpdateRequest, CollectionResponse), Groups (GroupCreateRequest, GroupUpdateRequest, GroupResponse), Deployments (DeploymentCreateRequest, DeploymentUpdateRequest, DeploymentResponse, DeploymentSummaryResponse), and common requests (AddArtifactsRequest, MoveArtifactsRequest, CopyArtifactsRequest). Include proper type hints, validation, examples, and from_attributes=True. Files: /skillmeat/api/schemas/collections.py, groups.py, deployments.py")

# Batch 2 (Parallel, after Batch 1)
Task("python-backend-engineer", "TASK-2.3: Add collection-artifact association endpoints to collections router: POST /{collectionId}/artifacts (add artifacts, idempotent), DELETE /{collectionId}/artifacts/{artifactId} (remove, idempotent), POST /{collectionId}/move-artifacts (transactional move), POST /{collectionId}/copy-artifacts (copy to target). Include validation, error handling. File: /skillmeat/api/routers/collections.py")

Task("python-backend-engineer", "TASK-2.4: Add group-artifact association endpoints to groups router: POST /{groupId}/artifacts (add with position), DELETE /{groupId}/artifacts/{artifactId} (remove and reorder), PUT /{groupId}/artifacts/{artifactId} (update position), POST /{groupId}/reorder-artifacts (bulk reorder, transactional). Include position validation, auto-reordering. File: /skillmeat/api/routers/groups.py")
```

---

## Task Details

### TASK-2.1: Collections CRUD Router
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 3h
- **Priority**: high

**Description**: FastAPI router for collection management endpoints

**Acceptance Criteria**:
- [ ] Router created at `/api/v1/collections` with proper prefix and tags
- [ ] `GET /api/v1/collections` - List all collections (with pagination)
- [ ] `POST /api/v1/collections` - Create new collection
- [ ] `GET /api/v1/collections/{id}` - Get single collection with groups
- [ ] `PUT /api/v1/collections/{id}` - Update collection
- [ ] `DELETE /api/v1/collections/{id}` - Delete collection
- [ ] Error handling: 400 (validation), 404 (not found), 500 (unexpected)
- [ ] All endpoints require authentication (token-based)
- [ ] CORS headers properly configured

**Files**: `/skillmeat/api/routers/collections.py`, `/skillmeat/api/server.py`

---

### TASK-2.2: Groups CRUD Router
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 3h
- **Priority**: high

**Description**: FastAPI router for group management endpoints

**Acceptance Criteria**:
- [ ] Router created at `/api/v1/groups` with proper prefix
- [ ] `POST /api/v1/groups` - Create group in collection
- [ ] `GET /api/v1/groups?collection_id={id}` - List groups in collection
- [ ] `GET /api/v1/groups/{id}` - Get single group with artifacts
- [ ] `PUT /api/v1/groups/{id}` - Update group
- [ ] `DELETE /api/v1/groups/{id}` - Delete group
- [ ] `PUT /api/v1/groups/reorder` - Bulk reorder groups
- [ ] All error handling and auth consistent with Collections router

**Files**: `/skillmeat/api/routers/groups.py`, `/skillmeat/api/server.py`

---

### TASK-2.3: Collection-Artifact Association Endpoints
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 2h
- **Priority**: high
- **Dependencies**: TASK-2.1

**Description**: Endpoints for managing artifact membership in collections

**Acceptance Criteria**:
- [ ] `POST /api/v1/collections/{collectionId}/artifacts` - Add artifact to collection (idempotent)
- [ ] `DELETE /api/v1/collections/{collectionId}/artifacts/{artifactId}` - Remove artifact (idempotent)
- [ ] `POST /api/v1/collections/{collectionId}/move-artifacts` - Move artifacts (transactional)
- [ ] `POST /api/v1/collections/{collectionId}/copy-artifacts` - Copy artifacts
- [ ] Error handling: 400 (validation), 404 (not found)

**Files**: `/skillmeat/api/routers/collections.py`

---

### TASK-2.4: Group-Artifact Association Endpoints
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 2h
- **Priority**: high
- **Dependencies**: TASK-2.2

**Description**: Endpoints for managing artifact membership in groups

**Acceptance Criteria**:
- [ ] `POST /api/v1/groups/{groupId}/artifacts` - Add artifact to group (with position)
- [ ] `DELETE /api/v1/groups/{groupId}/artifacts/{artifactId}` - Remove artifact (auto-reorder)
- [ ] `PUT /api/v1/groups/{groupId}/artifacts/{artifactId}` - Update artifact position
- [ ] `POST /api/v1/groups/{groupId}/reorder-artifacts` - Bulk reorder artifacts (transactional)
- [ ] Error handling: 400 (validation), 404 (not found)

**Files**: `/skillmeat/api/routers/groups.py`

---

### TASK-2.5: Deployment Summary Endpoints
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 2h
- **Priority**: medium

**Description**: API endpoints for deployment dashboard data

**Acceptance Criteria**:
- [ ] `GET /api/v1/deployments/summary` - Aggregated deployment summary (<100ms)
- [ ] `GET /api/v1/deployments?artifact_id={id}` - Deployments for specific artifact
- [ ] `GET /api/v1/deployments?project_id={id}` - Deployments in specific project
- [ ] `POST /api/v1/deployments` - Create new deployment
- [ ] `PUT /api/v1/deployments/{id}` - Update deployment
- [ ] Error handling: 400 (validation), 404 (not found)

**Files**: `/skillmeat/api/routers/deployments_enhanced.py`, `/skillmeat/api/server.py`

---

### TASK-2.6: Pydantic Schemas
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 1h
- **Priority**: high

**Description**: Request/response models for all new endpoints

**Acceptance Criteria**:
- [ ] Request models: CollectionCreateRequest, CollectionUpdateRequest, GroupCreateRequest, GroupUpdateRequest
- [ ] Response models: CollectionResponse, GroupResponse, DeploymentResponse, DeploymentSummaryResponse
- [ ] Common models: AddArtifactsRequest, MoveArtifactsRequest, CopyArtifactsRequest
- [ ] All models have proper type hints (no `Any`)
- [ ] Example values in Field descriptions
- [ ] Config with `from_attributes = True`
- [ ] Validation with meaningful error messages
- [ ] Enums: DeploymentStatus (active, inactive, error, pending)

**Files**: `/skillmeat/api/schemas/collections.py`, `/skillmeat/api/schemas/groups.py`, `/skillmeat/api/schemas/deployments.py`

---

## Progress Summary

**Completed**: 0/6 tasks (0%)
**In Progress**: 0/6 tasks
**Blocked**: 0/6 tasks
**Pending**: 6/6 tasks

---

## API Endpoints Summary

### Collections Router (`/api/v1/collections`)
- `GET /` - List collections (paginated, searchable)
- `POST /` - Create collection
- `GET /{id}` - Get collection with groups
- `PUT /{id}` - Update collection
- `DELETE /{id}` - Delete collection (cascade)
- `POST /{id}/artifacts` - Add artifacts
- `DELETE /{id}/artifacts/{artifactId}` - Remove artifact
- `POST /{id}/move-artifacts` - Move artifacts
- `POST /{id}/copy-artifacts` - Copy artifacts

### Groups Router (`/api/v1/groups`)
- `POST /` - Create group
- `GET /?collection_id={id}` - List groups by collection
- `GET /{id}` - Get group with artifacts
- `PUT /{id}` - Update group
- `DELETE /{id}` - Delete group
- `PUT /reorder` - Bulk reorder groups
- `POST /{id}/artifacts` - Add artifacts with position
- `DELETE /{id}/artifacts/{artifactId}` - Remove artifact
- `PUT /{id}/artifacts/{artifactId}` - Update position
- `POST /{id}/reorder-artifacts` - Bulk reorder artifacts

### Deployments Router (`/api/v1/deployments`)
- `GET /summary` - Aggregated deployment stats
- `GET /?artifact_id={id}` - Deployments for artifact
- `GET /?project_id={id}` - Deployments in project
- `POST /` - Create deployment
- `PUT /{id}` - Update deployment

---

## Testing Requirements

### Integration Tests
**Files**: `/skillmeat/api/tests/test_collections_router.py`, `/skillmeat/api/tests/test_groups_router.py`, `/skillmeat/api/tests/test_deployments_router.py`

- Create, list, get, update, delete operations
- Pagination and search functionality
- Association management (add, remove, move, copy)
- Position and reordering logic
- Error handling (400, 404, 500)
- Validation edge cases
- Idempotency verification
- Transactional operations

### Performance Tests
- List large collections (<100ms)
- Deployment summary with 10K+ records (<100ms)
- N+1 query prevention

---

## Phase Completion Criteria

Phase 2 is complete when:

1. **Routers**: All CRUD routers implemented and tested
2. **Associations**: Link/unlink/move/copy operations working
3. **Deployments**: Summary endpoints returning correct data
4. **Schemas**: All Pydantic models created and validated
5. **Error Handling**: Consistent error responses across all endpoints
6. **Testing**: 90%+ coverage of router code
7. **Performance**: All endpoints <100ms (deployment summary <100ms)
8. **Documentation**: OpenAPI docs auto-generated and accurate
9. **Code Review**: Approved by backend-architect
