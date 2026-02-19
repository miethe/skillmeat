---
title: 'Phase 2: Backend API - Collections & Navigation Enhancement'
phase: 2
status: inferred_complete
assigned_to:
- python-backend-engineer
- backend-architect
dependencies:
- Phase 1 (Database Layer)
story_points: 12
duration: 1.5 weeks
schema_version: 2
doc_type: phase_plan
feature_slug: collections-navigation
prd_ref: null
plan_ref: null
---
# Phase 2: Backend API

**Complexity**: FastAPI router implementation with SQLAlchemy integration
**Story Points**: 12 | **Duration**: 1.5 weeks | **Status**: Pending

---

## Phase Objective

Implement FastAPI routers, Pydantic schemas, and service layer logic for Collections and Groups management. This phase bridges the database layer with frontend API consumers.

## Deliverables

### 1. Collections CRUD Router (TASK-2.1)
**Description**: FastAPI router for collection management endpoints

**Acceptance Criteria**:
- [ ] Router created at `/api/v1/collections` with proper prefix and tags
- [ ] `GET /api/v1/collections` - List all collections (with pagination)
  - [ ] Query params: page (int), page_size (int, max 100), search (str optional)
  - [ ] Response: 200 with list of collections and total count
  - [ ] Performance: Queries optimized with indexes
- [ ] `POST /api/v1/collections` - Create new collection
  - [ ] Request body: name (required, 1-255 chars), description (optional)
  - [ ] Response: 201 with created collection
  - [ ] Validation: Duplicate name returns 400
- [ ] `GET /api/v1/collections/{id}` - Get single collection with groups
  - [ ] Response: 200 with collection and nested groups
  - [ ] 404 if collection not found
- [ ] `PUT /api/v1/collections/{id}` - Update collection
  - [ ] Request body: name, description (optional, partial update)
  - [ ] Response: 200 with updated collection
  - [ ] 404 if not found
- [ ] `DELETE /api/v1/collections/{id}` - Delete collection
  - [ ] Deletes collection and cascades to groups/artifacts
  - [ ] Response: 204 No Content
  - [ ] 404 if not found
- [ ] Error handling: 400 (validation), 404 (not found), 500 (unexpected)
- [ ] All endpoints require authentication (token-based)
- [ ] CORS headers properly configured

**Files to Create/Modify**:
- Create: `/skillmeat/api/routers/collections.py`
- Modify: `/skillmeat/api/server.py` - Register router

**Estimated Effort**: 3 points

---

### 2. Groups CRUD Router (TASK-2.2)
**Description**: FastAPI router for group management endpoints

**Acceptance Criteria**:
- [ ] Router created at `/api/v1/groups` with proper prefix
- [ ] `POST /api/v1/groups` - Create group in collection
  - [ ] Request body: collection_id, name, description, position (optional)
  - [ ] Response: 201 with created group
  - [ ] Validation: Duplicate name in collection returns 400
- [ ] `GET /api/v1/groups?collection_id={id}` - List groups in collection
  - [ ] Query param: collection_id (required)
  - [ ] Response: 200 with groups ordered by position
  - [ ] Optional: name search filter
- [ ] `GET /api/v1/groups/{id}` - Get single group with artifacts
  - [ ] Response: 200 with group and artifact list
  - [ ] 404 if not found
- [ ] `PUT /api/v1/groups/{id}` - Update group
  - [ ] Request body: name, description, position (optional)
  - [ ] Response: 200 with updated group
  - [ ] 404 if not found
- [ ] `DELETE /api/v1/groups/{id}` - Delete group
  - [ ] Cascades artifacts removed from group (not deleted)
  - [ ] Response: 204 No Content
  - [ ] 404 if not found
- [ ] `PUT /api/v1/groups/{id}/reorder` - Bulk reorder groups
  - [ ] Request body: list of {id, position} pairs
  - [ ] Response: 200 with reordered groups
- [ ] All error handling and auth consistent with Collections router

**Files to Create/Modify**:
- Create: `/skillmeat/api/routers/groups.py`
- Modify: `/skillmeat/api/server.py` - Register router

**Estimated Effort**: 3 points

---

### 3. Collection-Artifact Association Endpoints (TASK-2.3)
**Description**: Endpoints for managing artifact membership in collections

**Acceptance Criteria**:
- [ ] `POST /api/v1/collections/{collectionId}/artifacts` - Add artifact to collection
  - [ ] Request body: artifact_id (required) or list of artifact_ids
  - [ ] Response: 201 with association created
  - [ ] Idempotent: Adding existing artifact returns 200 (no error)
  - [ ] Validation: artifact_id format, collection exists
- [ ] `DELETE /api/v1/collections/{collectionId}/artifacts/{artifactId}` - Remove artifact
  - [ ] Response: 204 No Content
  - [ ] Idempotent: Removing non-existent association returns 204
- [ ] `POST /api/v1/collections/{collectionId}/move-artifacts` - Move artifacts
  - [ ] Request body: artifact_ids, target_collection_id
  - [ ] Response: 200 with updated associations
  - [ ] Validation: Both collections must exist
  - [ ] Transactional: All or nothing
- [ ] `POST /api/v1/collections/{collectionId}/copy-artifacts` - Copy artifacts
  - [ ] Request body: artifact_ids, target_collection_id
  - [ ] Response: 200 with new associations
  - [ ] Original associations unchanged
- [ ] Error handling: 400 (validation), 404 (not found)

**Files to Create/Modify**:
- Modify: `/skillmeat/api/routers/collections.py` - Add association endpoints

**Estimated Effort**: 2 points

---

### 4. Group-Artifact Association Endpoints (TASK-2.4)
**Description**: Endpoints for managing artifact membership in groups

**Acceptance Criteria**:
- [ ] `POST /api/v1/groups/{groupId}/artifacts` - Add artifact to group
  - [ ] Request body: artifact_id or list of artifact_ids
  - [ ] Optional: position field to insert at specific position
  - [ ] Response: 201 with association created
  - [ ] Idempotent: Adding existing artifact updates position if provided
- [ ] `DELETE /api/v1/groups/{groupId}/artifacts/{artifactId}` - Remove artifact
  - [ ] Response: 204 No Content
  - [ ] Reorder remaining artifacts automatically
  - [ ] Idempotent: Non-existent association returns 204
- [ ] `PUT /api/v1/groups/{groupId}/artifacts/{artifactId}` - Update artifact position
  - [ ] Request body: position (int)
  - [ ] Response: 200 with updated association
  - [ ] Validation: position within valid range
- [ ] `POST /api/v1/groups/{groupId}/reorder-artifacts` - Bulk reorder artifacts
  - [ ] Request body: list of {artifact_id, position} pairs
  - [ ] Response: 200 with reordered artifacts
  - [ ] Transactional: All or nothing
- [ ] Error handling: 400 (validation), 404 (not found)

**Files to Create/Modify**:
- Modify: `/skillmeat/api/routers/groups.py` - Add association endpoints

**Estimated Effort**: 2 points

---

### 5. Deployment Summary Endpoints (TASK-2.5)
**Description**: API endpoints for deployment dashboard data

**Acceptance Criteria**:
- [ ] `GET /api/v1/deployments/summary` - Aggregated deployment summary
  - [ ] Response: 200 with:
    - [ ] Total deployments count
    - [ ] Status breakdown (active, inactive, error)
    - [ ] Per-artifact deployment counts
    - [ ] Per-project deployment counts
  - [ ] Performance: Cached/optimized query (< 100ms)
  - [ ] Pagination optional for large datasets
- [ ] `GET /api/v1/deployments?artifact_id={id}` - Deployments for specific artifact
  - [ ] Query param: artifact_id (required)
  - [ ] Response: 200 with list of deployments across all projects
  - [ ] Fields: project_id, project_name, deployed_version, latest_version, status, deployed_at
- [ ] `GET /api/v1/deployments?project_id={id}` - Deployments in specific project
  - [ ] Query param: project_id (required)
  - [ ] Response: 200 with artifacts deployed to project
  - [ ] Include deployment status and version info
- [ ] `POST /api/v1/deployments` - Create new deployment
  - [ ] Request body: artifact_id, project_id, deployed_version (optional)
  - [ ] Response: 201 with created deployment
  - [ ] Validation: Both artifact and project exist
- [ ] `PUT /api/v1/deployments/{id}` - Update deployment
  - [ ] Request body: status, deployed_version (optional)
  - [ ] Response: 200 with updated deployment
- [ ] Error handling: 400 (validation), 404 (not found)

**Files to Create/Modify**:
- Create: `/skillmeat/api/routers/deployments_enhanced.py`
- Modify: `/skillmeat/api/server.py` - Register router

**Estimated Effort**: 2 points

---

### 6. Pydantic Schemas (TASK-2.6)
**Description**: Request/response models for all new endpoints

**Acceptance Criteria**:
- [ ] Request models created:
  - [ ] `CollectionCreateRequest` (name, description)
  - [ ] `CollectionUpdateRequest` (name, description - optional)
  - [ ] `GroupCreateRequest` (collection_id, name, description, position)
  - [ ] `GroupUpdateRequest` (name, description, position - optional)
  - [ ] `AddArtifactsRequest` (artifact_ids: list[str])
  - [ ] `MoveArtifactsRequest` (artifact_ids, target_collection_id)
  - [ ] `CopyArtifactsRequest` (artifact_ids, target_collection_id)
  - [ ] `DeploymentCreateRequest` (artifact_id, project_id, deployed_version)
  - [ ] `DeploymentUpdateRequest` (status, deployed_version - optional)
- [ ] Response models created:
  - [ ] `CollectionResponse` (id, name, description, created_at, updated_at, group_count, artifact_count)
  - [ ] `GroupResponse` (id, collection_id, name, description, position, artifact_count, created_at, updated_at)
  - [ ] `DeploymentResponse` (id, artifact_id, project_id, deployed_version, latest_version, status, deployed_at)
  - [ ] `DeploymentSummaryResponse` (total_count, by_status, by_artifact, by_project)
- [ ] All models have:
  - [ ] Proper type hints (no `Any`)
  - [ ] Example values in Field descriptions
  - [ ] Config with `from_attributes = True`
  - [ ] Validation with meaningful error messages
- [ ] Enums created: `DeploymentStatus` (active, inactive, error, pending)

**Files to Create/Modify**:
- Create: `/skillmeat/api/schemas/collections.py`
- Create: `/skillmeat/api/schemas/groups.py`
- Create: `/skillmeat/api/schemas/deployments.py`

**Estimated Effort**: 2 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Acceptance Criteria Count | Story Points | Assigned To | Status |
|---------|-----------|-------------|--------------------------|---------------|-------------|--------|
| TASK-2.1 | Collections Router | FastAPI CRUD endpoints for collections | 10 | 3 | python-backend-engineer | Pending |
| TASK-2.2 | Groups Router | FastAPI CRUD endpoints for groups | 10 | 3 | python-backend-engineer | Pending |
| TASK-2.3 | Collection-Artifact Endpoints | Link/unlink, move, copy artifacts | 8 | 2 | python-backend-engineer | Pending |
| TASK-2.4 | Group-Artifact Endpoints | Link/unlink, position, reorder artifacts | 8 | 2 | python-backend-engineer | Pending |
| TASK-2.5 | Deployment Summary Endpoints | Aggregated deployment data | 10 | 2 | python-backend-engineer | Pending |
| TASK-2.6 | Pydantic Schemas | Request/response models | 15 | 1 | python-backend-engineer | Pending |

**Total**: 12 story points

---

## API Specification

### Collections Endpoints

```python
# List collections (paginated)
GET /api/v1/collections
  Query: page=1, page_size=50, search="my"
  Response: {
    "collections": [
      {
        "id": "col-123",
        "name": "My Collection",
        "description": "...",
        "group_count": 3,
        "artifact_count": 15,
        "created_at": "2025-12-12T10:00:00Z",
        "updated_at": "2025-12-12T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }

# Create collection
POST /api/v1/collections
  Body: { "name": "New Collection", "description": "..." }
  Response: 201 { collection object }

# Get single collection
GET /api/v1/collections/{id}
  Response: 200 { collection object with nested groups }

# Update collection
PUT /api/v1/collections/{id}
  Body: { "name": "Updated", "description": "..." }
  Response: 200 { updated collection }

# Delete collection
DELETE /api/v1/collections/{id}
  Response: 204 No Content

# Add artifacts to collection
POST /api/v1/collections/{id}/artifacts
  Body: { "artifact_ids": ["art-1", "art-2"] }
  Response: 201 { created associations }

# Remove artifact from collection
DELETE /api/v1/collections/{id}/artifacts/{artifactId}
  Response: 204 No Content

# Move artifacts between collections
POST /api/v1/collections/{id}/move-artifacts
  Body: { "artifact_ids": [...], "target_collection_id": "col-456" }
  Response: 200 { updated associations }

# Copy artifacts between collections
POST /api/v1/collections/{id}/copy-artifacts
  Body: { "artifact_ids": [...], "target_collection_id": "col-456" }
  Response: 200 { new associations }
```

### Groups Endpoints

```python
# Create group
POST /api/v1/groups
  Body: {
    "collection_id": "col-123",
    "name": "Important Skills",
    "description": "...",
    "position": 0
  }
  Response: 201 { group object }

# List groups in collection
GET /api/v1/groups?collection_id={id}
  Response: 200 { "groups": [...] }

# Get single group
GET /api/v1/groups/{id}
  Response: 200 { group object with artifacts }

# Update group
PUT /api/v1/groups/{id}
  Body: { "name": "...", "position": 0 }
  Response: 200 { updated group }

# Delete group
DELETE /api/v1/groups/{id}
  Response: 204 No Content

# Reorder groups
PUT /api/v1/groups/reorder
  Body: {
    "groups": [
      { "id": "grp-1", "position": 0 },
      { "id": "grp-2", "position": 1 }
    ]
  }
  Response: 200 { reordered groups }

# Add artifact to group
POST /api/v1/groups/{id}/artifacts
  Body: { "artifact_ids": ["art-1"], "position": 0 }
  Response: 201 { created associations }

# Remove artifact from group
DELETE /api/v1/groups/{id}/artifacts/{artifactId}
  Response: 204 No Content

# Update artifact position
PUT /api/v1/groups/{id}/artifacts/{artifactId}
  Body: { "position": 5 }
  Response: 200 { updated association }

# Reorder artifacts in group
POST /api/v1/groups/{id}/reorder-artifacts
  Body: {
    "artifacts": [
      { "artifact_id": "art-1", "position": 0 },
      { "artifact_id": "art-2", "position": 1 }
    ]
  }
  Response: 200 { reordered artifacts }
```

### Deployments Endpoints

```python
# Get deployment summary
GET /api/v1/deployments/summary
  Response: 200 {
    "total_deployments": 45,
    "by_status": {
      "active": 40,
      "inactive": 4,
      "error": 1
    },
    "by_artifact": [
      { "artifact_id": "art-1", "count": 5, "status": "active" }
    ],
    "by_project": [
      { "project_id": "proj-1", "count": 10, "active": 9 }
    ]
  }

# Get deployments for artifact
GET /api/v1/deployments?artifact_id={id}
  Response: 200 {
    "deployments": [
      {
        "id": "dep-1",
        "artifact_id": "art-1",
        "project_id": "proj-1",
        "deployed_version": "1.2.0",
        "latest_version": "1.3.0",
        "status": "active",
        "deployed_at": "2025-12-12T10:00:00Z"
      }
    ]
  }

# Get deployments in project
GET /api/v1/deployments?project_id={id}
  Response: 200 { "deployments": [...] }

# Create deployment
POST /api/v1/deployments
  Body: {
    "artifact_id": "art-1",
    "project_id": "proj-1",
    "deployed_version": "1.2.0"
  }
  Response: 201 { deployment object }

# Update deployment
PUT /api/v1/deployments/{id}
  Body: { "status": "inactive", "deployed_version": "1.3.0" }
  Response: 200 { updated deployment }
```

---

## Service Layer Design

### CollectionService

```python
class CollectionService:
    """Service for collection business logic."""

    def __init__(self, session: Session):
        self.session = session

    def create_collection(self, name: str, description: str = None) -> Collection:
        """Create new collection."""
        # Generate UUID, validate inputs, save to DB

    def list_collections(self, page: int = 1, page_size: int = 50, search: str = None):
        """List collections with pagination."""
        # Query with filters, return paginated results

    def get_collection(self, collection_id: str) -> Collection:
        """Get single collection with relationships."""
        # Eager load groups and artifacts

    def update_collection(self, collection_id: str, **kwargs) -> Collection:
        """Update collection fields."""
        # Validate, update, save

    def delete_collection(self, collection_id: str) -> None:
        """Delete collection (cascades to groups)."""
        # Verify exists, delete, commit

    def add_artifacts(self, collection_id: str, artifact_ids: List[str]) -> None:
        """Add artifacts to collection."""
        # Create CollectionArtifact associations

    def remove_artifact(self, collection_id: str, artifact_id: str) -> None:
        """Remove artifact from collection."""
        # Delete association

    def move_artifacts(self, from_id: str, to_id: str, artifact_ids: List[str]) -> None:
        """Move artifacts between collections."""
        # Transactional: remove from old, add to new
```

### GroupService

Similar structure for group operations with additional position/ordering logic.

### DeploymentService

```python
class DeploymentService:
    """Service for deployment aggregation and updates."""

    def get_summary(self) -> Dict:
        """Get aggregated deployment summary."""
        # Query across all deployments, aggregate by status/artifact/project

    def get_artifact_deployments(self, artifact_id: str) -> List[Deployment]:
        """Get all deployments for specific artifact."""

    def get_project_deployments(self, project_id: str) -> List[Deployment]:
        """Get all deployments in specific project."""

    def create_deployment(self, artifact_id: str, project_id: str, version: str) -> Deployment:
        """Create new deployment record."""

    def update_deployment(self, deployment_id: str, **kwargs) -> Deployment:
        """Update deployment status/version."""
```

---

## Error Handling

### Standard HTTP Status Codes

```python
# 200 OK - Successful GET/PUT
response.status_code = 200

# 201 Created - Successful POST
response.status_code = 201

# 204 No Content - Successful DELETE
response.status_code = 204

# 400 Bad Request - Validation error
raise HTTPException(
    status_code=400,
    detail="Collection name must be 1-255 characters"
)

# 404 Not Found
raise HTTPException(
    status_code=404,
    detail=f"Collection '{collection_id}' not found"
)

# 409 Conflict - Duplicate entry
raise HTTPException(
    status_code=409,
    detail="A group with this name already exists in this collection"
)

# 500 Internal Server Error - Unexpected
try:
    # operation
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

---

## Testing Strategy

### Integration Tests

**File**: `/skillmeat/api/tests/test_collections_router.py`

```python
def test_create_collection(test_client, db_session):
    """Test creating a collection."""
    response = test_client.post(
        "/api/v1/collections",
        json={"name": "Test Collection"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Collection"

def test_duplicate_collection_name(test_client, db_session):
    """Test that duplicate names are rejected."""
    # Create first collection, then try duplicate

def test_list_collections_pagination(test_client, db_session):
    """Test pagination of collection list."""
    # Create multiple collections, verify page_size respected

def test_add_artifacts_to_collection(test_client, db_session):
    """Test adding artifacts to collection."""
    # Create collection and artifacts, link them

def test_move_artifacts_between_collections(test_client, db_session):
    """Test moving artifacts transactionally."""
    # Verify old collection no longer has artifacts
```

### Performance Tests

```python
def test_list_large_collection(test_client, db_session):
    """Test performance with 1000+ artifacts."""
    # Measure response time, should be < 1 second with caching

def test_deployment_summary_performance(test_client, db_session):
    """Test aggregation query performance."""
    # Should complete in < 100ms even with 10K deployments
```

---

## Quality Gates

### API Review Checklist
- [ ] All endpoints follow RESTful conventions
- [ ] HTTP status codes are correct and consistent
- [ ] Error messages are descriptive and actionable
- [ ] All query params and request bodies validated
- [ ] Response models include all necessary fields
- [ ] Pagination implemented for large result sets
- [ ] CORS headers properly configured
- [ ] Authentication/authorization enforced

### Performance Checklist
- [ ] N+1 query problems identified and fixed
- [ ] Queries have execution time < 100ms (with indexes)
- [ ] Deployment summary < 100ms even with 10K rows
- [ ] No unnecessary data fetching in responses
- [ ] Indexes created for all filter/sort columns

### Documentation Checklist
- [ ] All endpoints documented with examples
- [ ] Request/response schemas documented
- [ ] Error responses documented
- [ ] Query params documented
- [ ] Authentication requirements documented
- [ ] OpenAPI/Swagger docs generated and accurate

---

## Files to Create

### New Router Files

1. `/skillmeat/api/routers/collections.py` (~200 lines)
2. `/skillmeat/api/routers/groups.py` (~200 lines)
3. `/skillmeat/api/routers/deployments_enhanced.py` (~150 lines)

### New Schema Files

1. `/skillmeat/api/schemas/collections.py` (~60 lines)
2. `/skillmeat/api/schemas/groups.py` (~50 lines)
3. `/skillmeat/api/schemas/deployments.py` (~40 lines)

### New Service Files

1. `/skillmeat/api/services/collection_service.py` (~150 lines)
2. `/skillmeat/api/services/group_service.py` (~150 lines)
3. `/skillmeat/api/services/deployment_service.py` (~120 lines)

### Modified Files

1. `/skillmeat/api/server.py` - Register new routers
2. Existing test files - Add integration tests

---

## Dependencies

### Runtime
- FastAPI (already in project)
- SQLAlchemy (already in project)
- Pydantic (already in project)

### Development
- pytest, pytest-asyncio (for testing)

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Collections Router | 8 | CRUD + associations + validation |
| Groups Router | 8 | Similar to Collections |
| Deployment Endpoints | 6 | Aggregation and summary queries |
| Pydantic Schemas | 4 | Models for requests/responses |
| Service Layer | 6 | Business logic separation |
| Testing | 8 | Integration and performance tests |
| Code Review | 2 | Feedback and revisions |
| **Total** | **42 hours** | ~5 days actual work, ~10 business days calendar |

---

## Orchestration Quick Reference

### Task Delegation Commands

Batch 1 (Parallel):
- **TASK-2.1** → `python-backend-engineer` (3h) - Collections router
- **TASK-2.2** → `python-backend-engineer` (3h) - Groups router

Batch 2 (Sequential, after Batch 1):
- **TASK-2.3** → `python-backend-engineer` (2h) - Collection-artifact endpoints
- **TASK-2.4** → `python-backend-engineer` (2h) - Group-artifact endpoints

Batch 3 (Parallel, after Batch 2):
- **TASK-2.5** → `python-backend-engineer` (2h) - Deployment endpoints
- **TASK-2.6** → `python-backend-engineer` (1h) - Pydantic schemas

---

## Success Criteria

Phase 2 is complete when:

1. **Routers**: All CRUD routers implemented and tested
2. **Associations**: Link/unlink/move/copy operations working
3. **Deployments**: Summary endpoints returning correct data
4. **Schemas**: All Pydantic models created and validated
5. **Error Handling**: Consistent error responses across all endpoints
6. **Testing**: 90%+ coverage of router code
7. **Performance**: All endpoints < 100ms (deployment summary < 100ms)
8. **Documentation**: OpenAPI docs auto-generated and accurate
9. **Code Review**: Approved by backend-architect

---

## Next Phase

Phase 3 (Frontend Foundation) depends on Phase 2 being complete. It will:
- Create TypeScript types matching API schemas
- Implement TanStack Query hooks for API calls
- Set up CollectionContext for shared state
- Integrate API client with React components

**Phase 2 → Phase 3 Handoff**:
- Provide API endpoint reference (OpenAPI JSON)
- Share example requests/responses for each endpoint
- Document any special auth requirements
- Provide list of dependencies for frontend integration
