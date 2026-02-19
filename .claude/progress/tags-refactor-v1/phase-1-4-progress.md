---
type: progress
prd: tags-refactor-v1
phase: 1-4
title: Backend - Database, Repository, Service, and API Layers
status: pending
completed_at: null
progress: 0
total_tasks: 17
completed_tasks: 0
total_story_points: 19
completed_story_points: 0
tasks:
- id: DB-001
  title: Tags Table
  description: Create tags table with id, name, slug, color, created_at
  status: pending
  story_points: 2
  assigned_to:
  - data-layer-expert
  dependencies: []
  created_at: '2025-12-18'
- id: DB-002
  title: Artifact-Tags Junction
  description: Create artifact_tags junction table with FKs and unique constraint
  status: pending
  story_points: 1
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-001
  created_at: '2025-12-18'
- id: DB-003
  title: Alembic Migration
  description: Create migration for tags schema
  status: pending
  story_points: 1
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-002
  created_at: '2025-12-18'
- id: REPO-001
  title: Tag CRUD Methods
  description: Implement create, read, update, delete for tags
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-003
  created_at: '2025-12-18'
- id: REPO-002
  title: Tag Search & List
  description: Implement tag listing with cursor pagination and search by name
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-001
  created_at: '2025-12-18'
- id: REPO-003
  title: Artifact-Tag Association
  description: Implement add/remove tags from artifacts, get tags for artifact
  status: pending
  story_points: 2
  assigned_to:
  - data-layer-expert
  dependencies:
  - REPO-001
  created_at: '2025-12-18'
- id: REPO-004
  title: Tag Statistics
  description: Implement tag count query (artifacts per tag)
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-003
  created_at: '2025-12-18'
- id: SVC-001
  title: Tag DTOs
  description: Create Pydantic schemas for tag request/response
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-004
  created_at: '2025-12-18'
- id: SVC-002
  title: Tag Service
  description: Implement tag service with business logic
  status: pending
  story_points: 3
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-001
  created_at: '2025-12-18'
- id: SVC-003
  title: Artifact-Tag Service
  description: Implement artifact tag association service
  status: pending
  story_points: 2
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-002
  created_at: '2025-12-18'
- id: SVC-004
  title: Error Handling
  description: Implement error patterns for tag operations
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-003
  created_at: '2025-12-18'
- id: SVC-005
  title: Observability
  description: Add OpenTelemetry spans for tag operations
  status: pending
  story_points: 1
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-004
  created_at: '2025-12-18'
- id: API-001
  title: Tag Router Setup
  description: Create FastAPI router for tag endpoints
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-005
  created_at: '2025-12-18'
- id: API-002
  title: Tag CRUD Endpoints
  description: Implement GET /tags, POST /tags, PUT /tags/{id}, DELETE /tags/{id}
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-001
  created_at: '2025-12-18'
- id: API-003
  title: Artifact-Tag Endpoints
  description: Implement GET /artifacts/{id}/tags, POST /artifacts/{id}/tags/{tag_id},
    DELETE /artifacts/{id}/tags/{tag_id}
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-002
  created_at: '2025-12-18'
- id: API-004
  title: Response Formatting
  description: Standardize tag response formats with pagination
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-003
  created_at: '2025-12-18'
- id: API-005
  title: OpenAPI Documentation
  description: Document all tag endpoints in Swagger
  status: pending
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-004
  created_at: '2025-12-18'
parallelization:
  batch_1:
  - DB-001
  batch_2:
  - DB-002
  batch_3:
  - DB-003
  batch_4:
  - REPO-001
  batch_5:
  - REPO-002
  - REPO-003
  batch_6:
  - REPO-004
  batch_7:
  - SVC-001
  batch_8:
  - SVC-002
  batch_9:
  - SVC-003
  batch_10:
  - SVC-004
  batch_11:
  - SVC-005
  batch_12:
  - API-001
  batch_13:
  - API-002
  batch_14:
  - API-003
  batch_15:
  - API-004
  batch_16:
  - API-005
context_files:
- skillmeat/cache/models.py
- skillmeat/core/
- skillmeat/api/
- skillmeat/storage/
blockers: []
notes: Backend implementation for tags system. Phases 1-4 establish database, data
  access, business logic, and API layers. Phase 0 (bug fix) must complete first.
schema_version: 2
doc_type: progress
feature_slug: tags-refactor-v1
---

# Phases 1-4: Backend Implementation

Backend implementation of the tags system across database, repository, service, and API layers. This section establishes the complete backend infrastructure for tag management and artifact-tag associations.

**Total Duration**: 6-7 days
**Total Story Points**: 19
**Dependencies**: Phase 0 complete
**Assigned Agents**: data-layer-expert, python-backend-engineer, backend-architect

---

## Phase 1: Database Foundation - Tags Schema

**Duration**: 2 days
**Story Points**: 4
**Objective**: Create database schema for tags and artifact-tag associations.

### DB-001: Tags Table (2 pts)

```markdown
Task("data-layer-expert", "DB-001: Create tags table

File: skillmeat/storage/models/tag.py (new)

Create SQLAlchemy ORM model:
- name: Tag
- fields:
  - id (Integer, primary key)
  - name (String(255), required, unique, indexed)
  - slug (String(255), required, unique, indexed, lowercase)
  - color (String(7), optional, default '#808080', hex color code)
  - created_at (DateTime, default now, indexed)
  - updated_at (DateTime, default now, onupdate now)
- relationships: artifacts (via artifact_tags association table)

Add indexes:
- (name) - for unique constraint and search
- (slug) - for URL-friendly queries
- (created_at) - for sorting/filtering by date

Location: Add to skillmeat/storage/models/ structure")
```

### DB-002: Artifact-Tags Junction (1 pt)

```markdown
Task("data-layer-expert", "DB-002: Create artifact_tags junction table

File: skillmeat/storage/models/tag.py (same as DB-001)

Create SQLAlchemy association table:
- name: artifact_tags (table) and ArtifactTag (model if needed)
- fields:
  - artifact_id (ForeignKey to Artifact.id, primary key part)
  - tag_id (ForeignKey to Tag.id, primary key part)
  - created_at (DateTime, default now)
- constraints:
  - Composite primary key on (artifact_id, tag_id)
  - Foreign key constraints with CASCADE delete on tag deletion
  - Unique constraint on (artifact_id, tag_id)

Add indexes:
- (artifact_id) - for finding tags on an artifact
- (tag_id) - for finding artifacts with a tag
- (created_at) - for temporal queries

Relationship setup:
- Add relationship to Artifact model
- Add relationship to Tag model")
```

### DB-003: Alembic Migration (1 pt)

```markdown
Task("data-layer-expert", "DB-003: Create Alembic migration for tags schema

Files:
  - Create new migration in skillmeat/storage/migrations/versions/
  - Name: {timestamp}_add_tags_schema.py

Migration requirements:
1. Create tags table with all columns and indexes
2. Create artifact_tags junction table with constraints
3. Verify migration works with: alembic upgrade head
4. Verify rollback works with: alembic downgrade -1
5. Test on clean database

Include:
- Docstring explaining purpose
- Proper dependency declaration (if any)
- Error handling for existing tables")
```

---

## Phase 2: Repository Layer - Tag Data Access

**Duration**: 2 days
**Story Points**: 7
**Objective**: Implement database access patterns for tags and artifact-tag associations.

### REPO-001: Tag CRUD Methods (2 pts)

```markdown
Task("python-backend-engineer", "REPO-001: Implement tag CRUD repository methods

File: skillmeat/core/storage/repositories/tag_repository.py (new)

Implement TagRepository class with methods:
- create_tag(session, name: str, color: str = None) -> Tag
  * Validates unique name (case-insensitive check)
  * Auto-generates slug from name
  * Returns Tag ORM instance

- get_tag(session, tag_id: int) -> Tag | None
  * Retrieves tag by ID

- update_tag(session, tag_id: int, name: str = None, color: str = None) -> Tag
  * Updates tag fields
  * Regenerates slug if name changes
  * Returns updated Tag

- delete_tag(session, tag_id: int) -> None
  * Deletes tag and cascade-deletes artifact associations

- tag_exists(session, name: str) -> bool
  * Check if tag name exists (case-insensitive)

Error handling:
- Raise IntegrityError for duplicate names
- Raise NoResultFound for missing IDs
- Log all operations at INFO level

Tests: >80% coverage required")
```

### REPO-002: Tag Search & List (2 pts)

```markdown
Task("python-backend-engineer", "REPO-002: Implement tag search and pagination

File: skillmeat/core/storage/repositories/tag_repository.py (update)

Implement methods:
- list_tags(session, limit: int = 50, after_cursor: str = None, search: str = None) -> tuple[List[Tag], str | None]
  * Returns paginated list of tags with cursor for next page
  * Filter by name substring if search provided (case-insensitive)
  * Order by created_at DESC (newest first)
  * Cursor format: base64-encoded last tag ID
  * Return: (tags_list, next_cursor)

- search_tags(session, query: str, limit: int = 10) -> List[Tag]
  * Quick search by name prefix or substring
  * Used for autocomplete/typeahead
  * Return top N matches ordered by relevance

Pagination format:
- cursor = base64.b64encode(f'{last_id}:{last_created_at}'.encode()).decode()
- Decode cursor in next request to get starting point

Tests: Test pagination boundaries, search edge cases")
```

### REPO-003: Artifact-Tag Association (2 pts)

```markdown
Task("data-layer-expert", "REPO-003: Implement artifact-tag association methods

File: skillmeat/core/storage/repositories/tag_repository.py (update)

Implement methods:
- add_tag_to_artifact(session, artifact_id: str, tag_id: int) -> None
  * Adds tag to artifact via artifact_tags junction
  * Validates artifact exists
  * Validates tag exists
  * Raises IntegrityError if already associated

- remove_tag_from_artifact(session, artifact_id: str, tag_id: int) -> None
  * Removes tag from artifact
  * Raises NoResultFound if association doesn't exist

- get_artifact_tags(session, artifact_id: str) -> List[Tag]
  * Returns all tags for an artifact
  * Order by created_at DESC

- clear_artifact_tags(session, artifact_id: str) -> None
  * Remove all tags from artifact (useful for updates)

Tests: Test association constraints, cascade behavior")
```

### REPO-004: Tag Statistics (1 pt)

```markdown
Task("python-backend-engineer", "REPO-004: Implement tag statistics queries

File: skillmeat/core/storage/repositories/tag_repository.py (update)

Implement methods:
- get_tag_artifact_count(session, tag_id: int) -> int
  * Returns count of artifacts associated with tag

- get_all_tag_counts(session) -> List[tuple[Tag, int]]
  * Returns all tags with artifact counts
  * Used for dashboard/analytics
  * Order by count DESC

- get_artifact_count_by_tag_ids(session, tag_ids: List[int]) -> Dict[int, int]
  * Returns count map for multiple tag IDs
  * Used for filter UI showing counts

Tests: Test accuracy of counts, edge cases")
```

---

## Phase 3: Service Layer - Tag Business Logic

**Duration**: 2 days
**Story Points**: 8
**Objective**: Implement business logic and error handling for tag operations.

### SVC-001: Tag DTOs (1 pt)

```markdown
Task("python-backend-engineer", "SVC-001: Create Pydantic DTO schemas

File: skillmeat/api/app/schemas/tag.py (new)

Create Pydantic models:
- TagResponse
  * id: int
  * name: str
  * slug: str
  * color: str
  * created_at: datetime
  * updated_at: datetime
  * artifact_count: int (optional, for listings)

- TagCreateRequest
  * name: str (required, min 1, max 255)
  * color: str (optional, hex format validation)

- TagUpdateRequest
  * name: str (optional)
  * color: str (optional)

- TagListResponse
  * items: List[TagResponse]
  * next_cursor: str | None (for pagination)

- ArtifactTagResponse
  * artifact_id: str
  * tag_id: int
  * created_at: datetime

- ArtifactTagsResponse
  * artifact_id: str
  * tags: List[TagResponse]

Add validation:
- Color must be valid hex (#RRGGBB format)
- Name must be non-empty, max 255 chars
- Use field validators for format checks")
```

### SVC-002: Tag Service (3 pts)

```markdown
Task("backend-architect", "SVC-002: Implement tag service with business logic

File: skillmeat/core/services/tag_service.py (new)

Create TagService class:

Methods:
- create_tag(session, request: TagCreateRequest) -> TagResponse
  * Validate name uniqueness (case-insensitive)
  * Auto-generate slug from name
  * Call repository.create_tag()
  * Log at INFO level
  * Return TagResponse

- update_tag(session, tag_id: int, request: TagUpdateRequest) -> TagResponse
  * Validate tag exists
  * Update fields if provided
  * Regenerate slug if name changed
  * Return TagResponse

- delete_tag(session, tag_id: int) -> None
  * Validate tag exists
  * Call repository.delete_tag()
  * Log deletion at WARNING level

- list_tags(session, limit: int, after_cursor: str, search: str) -> TagListResponse
  * Call repository.list_tags()
  * Map results to TagResponse
  * Return with pagination cursor

- get_tag(session, tag_id: int) -> TagResponse
  * Call repository.get_tag()
  * Raise 404 if not found

- search_tags(session, query: str) -> List[TagResponse]
  * Call repository.search_tags()
  * Used for autocomplete

Error handling:
- Raise ValueError for validation errors
- Raise NotFoundError (404) for missing resources
- Raise ConflictError (409) for duplicates
- Log all errors at appropriate levels

Tests: >80% coverage, test edge cases")
```

### SVC-003: Artifact-Tag Service (2 pts)

```markdown
Task("backend-architect", "SVC-003: Implement artifact-tag service

File: skillmeat/core/services/artifact_tag_service.py (new)

Create ArtifactTagService class:

Methods:
- add_tag_to_artifact(session, artifact_id: str, tag_id: int) -> ArtifactTagResponse
  * Validate artifact exists (check in artifact repository)
  * Validate tag exists
  * Call repository.add_tag_to_artifact()
  * Log at INFO level
  * Return ArtifactTagResponse

- remove_tag_from_artifact(session, artifact_id: str, tag_id: int) -> None
  * Validate association exists
  * Call repository.remove_tag_from_artifact()
  * Log at INFO level

- get_artifact_tags(session, artifact_id: str) -> ArtifactTagsResponse
  * Validate artifact exists
  * Call repository.get_artifact_tags()
  * Return with artifact_id and tags list

- update_artifact_tags(session, artifact_id: str, tag_ids: List[int]) -> ArtifactTagsResponse
  * Replace all artifact tags with new set
  * Call repository.clear_artifact_tags()
  * Add new tag associations
  * Return updated tags

- filter_artifacts_by_tags(session, tag_ids: List[int], limit: int = 50) -> List[str]
  * Find all artifacts with ALL specified tags (AND logic)
  * Used for filtering in artifact list

Error handling:
- 404 if artifact not found
- 404 if tag not found
- 409 if tag already associated
- Log all operations")
```

### SVC-004: Error Handling (1 pt)

```markdown
Task("python-backend-engineer", "SVC-004: Implement error patterns

File: skillmeat/core/exceptions.py (update) and SVC files

Define custom exceptions:
- TagNotFoundError (404): When tag doesn't exist
- TagAlreadyExistsError (409): When tag name is duplicate
- ArtifactTagAlreadyExistsError (409): When tag already on artifact
- InvalidTagError (400): For validation failures

Use in services:
- All CRUD operations raise appropriate exceptions
- Map exceptions to HTTP status codes in API layer
- Include descriptive error messages for users

Error response format:
{
  'error': 'conflict',
  'detail': 'Tag with name \"python\" already exists',
  'code': 'TAG_ALREADY_EXISTS'
}")
```

### SVC-005: Observability (1 pt)

```markdown
Task("backend-architect", "SVC-005: Add OpenTelemetry instrumentation

File: skillmeat/core/services/tag_service.py and artifact_tag_service.py (update)

Add OpenTelemetry spans:
- Span for each service method
- Span attributes:
  * tag.id, tag.name
  * artifact.id
  * operation (create, update, delete, list)
  * result (success, error)

Use tracer from observability module:
from skillmeat.observability import get_tracer
tracer = get_tracer(__name__)

with tracer.start_as_current_span('tag_service.create_tag') as span:
  span.set_attribute('tag.name', name)
  # operation
  span.set_attribute('tag.id', tag.id)

Log patterns:
- Create: INFO level
- Update: INFO level
- Delete: WARNING level
- Search: DEBUG level
- Errors: ERROR level with exception info")
```

---

## Phase 4: API Layer - Tag Endpoints

**Duration**: 2 days
**Story Points**: 7
**Objective**: Create FastAPI router and endpoints for tag management.

### API-001: Tag Router Setup (1 pt)

```markdown
Task("python-backend-engineer", "API-001: Create tag router

File: skillmeat/api/app/routers/tags.py (new)

Create FastAPI router:
- router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    description="Tag management endpoints"
  )

- Register in skillmeat/api/app/server.py:
  app.include_router(tags.router, prefix="/api/v1")

Router will include:
- Tag CRUD endpoints
- Artifact-tag association endpoints
- Proper HTTP methods and status codes
- Request/response validation
- Error handling with HTTPException")
```

### API-002: Tag CRUD Endpoints (2 pts)

```markdown
Task("python-backend-engineer", "API-002: Implement tag CRUD endpoints

File: skillmeat/api/app/routers/tags.py (update)

Implement endpoints:

GET /api/v1/tags
- List all tags with pagination
- Query params: limit, after_cursor, search
- Response: 200 TagListResponse
- Use cursor-based pagination

POST /api/v1/tags
- Create new tag
- Request body: TagCreateRequest
- Response: 201 TagResponse
- Set Location header to /api/v1/tags/{tag_id}

GET /api/v1/tags/{tag_id}
- Get single tag
- Response: 200 TagResponse
- Return 404 if not found

PUT /api/v1/tags/{tag_id}
- Update tag
- Request body: TagUpdateRequest
- Response: 200 TagResponse
- Return 404 if not found

DELETE /api/v1/tags/{tag_id}
- Delete tag
- Response: 204 No Content
- Return 404 if not found

Error responses (400/404/409):
{
  'error': 'error_type',
  'detail': 'User-friendly message',
  'code': 'ERROR_CODE'
}")
```

### API-003: Artifact-Tag Endpoints (2 pts)

```markdown
Task("python-backend-engineer", "API-003: Implement artifact-tag endpoints

File: skillmeat/api/app/routers/tags.py (update)

Implement endpoints:

GET /api/v1/artifacts/{artifact_id}/tags
- Get all tags for artifact
- Response: 200 ArtifactTagsResponse
- Return 404 if artifact not found

POST /api/v1/artifacts/{artifact_id}/tags/{tag_id}
- Add tag to artifact
- Response: 201 ArtifactTagResponse
- Return 404 if artifact/tag not found
- Return 409 if already associated

DELETE /api/v1/artifacts/{artifact_id}/tags/{tag_id}
- Remove tag from artifact
- Response: 204 No Content
- Return 404 if association not found

PUT /api/v1/artifacts/{artifact_id}/tags
- Replace all artifact tags (bulk update)
- Request body: { 'tag_ids': [1, 2, 3] }
- Response: 200 ArtifactTagsResponse
- Validates all tag IDs exist before transaction

Error handling:
- Validate artifact_id exists
- Validate tag_id exists
- Return appropriate HTTP status codes
- Include error detail in response")
```

### API-004: Response Formatting (1 pt)

```markdown
Task("python-backend-engineer", "API-004: Standardize response formatting

File: skillmeat/api/app/routers/tags.py (update)

Implement consistent response envelope:

Success responses:
{
  'data': TagResponse | List[TagResponse],
  'meta': {
    'next_cursor': 'base64...' | null,  # for paginated responses
    'count': 5,                          # for list responses
    'total': 50                          # estimated total (optional)
  }
}

For single resource (POST, PUT, GET):
{
  'data': TagResponse
}

For lists (GET /tags):
{
  'data': [TagResponse, ...],
  'meta': {
    'next_cursor': '...',
    'count': 50
  }
}

Error responses (via HTTPException):
{
  'error': 'validation_error',
  'detail': 'Name is required',
  'code': 'VALIDATION_ERROR'
}

Use pydantic Config to enforce consistency:
- model_config = ConfigDict(populate_by_name=True)
- response_model parameter on each route")
```

### API-005: OpenAPI Documentation (1 pt)

```markdown
Task("python-backend-engineer", "API-005: Document tag endpoints in OpenAPI

File: skillmeat/api/app/routers/tags.py (update)

Add documentation to each endpoint:

@router.get(
  '/tags',
  summary='List all tags',
  description='Retrieve paginated list of tags with optional search',
  response_description='List of tags with pagination',
  responses={
    200: {'model': TagListResponse, 'description': 'Tags retrieved successfully'},
    400: {'model': ErrorResponse, 'description': 'Invalid parameters'}
  }
)

Include for each endpoint:
- summary: One-line description
- description: Multi-line explanation of behavior
- response_description: What the response contains
- responses: Dict of status code examples
- tags: ['tags'] for grouping
- deprecated: false (unless applicable)

Request/response models:
- Use Pydantic models with Field() descriptions
- Tag examples in responses
- Document pagination format

Examples in OpenAPI:
- Example tag response with all fields
- Example list response with pagination
- Example error responses (400, 404, 409)

Verify in /api/v1/docs (Swagger UI)")
```

---

## Quality Gates

### Phase 1 - Database
- [ ] Migration creates tags and artifact_tags tables
- [ ] Unique constraints enforced (tag name, artifact_id+tag_id)
- [ ] Indexes created for query performance
- [ ] Rollback migration works cleanly

### Phase 2 - Repository
- [ ] All CRUD operations working with proper error handling
- [ ] Cursor pagination implemented correctly
- [ ] Search by tag name functional
- [ ] Tag statistics queries accurate
- [ ] Repository tests >80% coverage

### Phase 3 - Service
- [ ] Business logic unit tests pass (>80% coverage)
- [ ] DTOs validate correctly
- [ ] ErrorResponse envelope used consistently
- [ ] OpenTelemetry instrumentation complete
- [ ] Service returns proper error codes

### Phase 4 - API
- [ ] All endpoints return correct HTTP status codes
- [ ] OpenAPI documentation complete and accurate
- [ ] Request/response validation working
- [ ] Error responses consistent
- [ ] Integration tests pass (>80% coverage)

---

## Dependencies Summary

**Sequential Path** (must complete in order):
1. DB-001 → DB-002 → DB-003 (database schema)
2. DB-003 → REPO-001 → REPO-002 (repository CRUD)
3. REPO-002 → REPO-003 → REPO-004 (associations & stats)
4. REPO-004 → SVC-001 (DTOs)
5. SVC-001 → SVC-002 (tag service)
6. SVC-002 → SVC-003 (artifact-tag service)
7. SVC-003 → SVC-004 (error handling)
8. SVC-004 → SVC-005 (observability)
9. SVC-005 → API-001 (router setup)
10. API-001 → API-002 → API-003 → API-004 → API-005

**Parallelization Opportunities**:
- REPO-002 and REPO-003 can run in parallel (both depend on REPO-001)
- SVC-004 and SVC-005 can run after SVC-003
- API-002, API-003, API-004 can be developed in parallel

---

## Orchestration Quick Reference

### Batch 1-3: Database Schema (Sequential, 2 days)

```markdown
Task("data-layer-expert", "DB-001-DB-003: Create tags database schema

Phase 1: Create Tags Table (DB-001)
- File: skillmeat/storage/models/tag.py
- Fields: id, name (unique), slug (unique), color, created_at, updated_at
- Indexes: name, slug, created_at

Phase 2: Create Artifact-Tags Junction (DB-002)
- File: skillmeat/storage/models/tag.py (update)
- Fields: artifact_id (FK), tag_id (FK), created_at
- Constraint: Unique(artifact_id, tag_id)
- Indexes: artifact_id, tag_id, created_at

Phase 3: Create Alembic Migration (DB-003)
- File: skillmeat/storage/migrations/versions/{timestamp}_add_tags_schema.py
- Includes both tables and indexes
- Verify up and down migrations work")
```

### Batch 4-6: Repository Layer (Sequential, 2 days)

```markdown
Task("python-backend-engineer", "REPO-001-REPO-004: Implement tag repository

REPO-001: Tag CRUD (create, read, update, delete, exists)
REPO-002: Tag search and cursor pagination (list_tags, search_tags)
REPO-003: Artifact-tag association (add, remove, get for artifact)
REPO-004: Tag statistics (artifact count per tag, bulk counts)

File: skillmeat/core/storage/repositories/tag_repository.py
All CRUD operations with proper error handling and logging
Tests: >80% coverage required")
```

### Batch 7-11: Service Layer (Sequential, 2 days)

```markdown
Task("backend-architect", "SVC-001-SVC-005: Implement tag service layer

SVC-001: Create Pydantic DTOs (TagResponse, TagCreateRequest, etc.)
SVC-002: Tag business logic service (validate, create, update, delete, list)
SVC-003: Artifact-tag association service (add, remove, get, filter)
SVC-004: Error handling patterns (custom exceptions, error responses)
SVC-005: OpenTelemetry instrumentation (spans for all operations)

Files:
  - skillmeat/api/app/schemas/tag.py (DTOs)
  - skillmeat/core/services/tag_service.py (tag logic)
  - skillmeat/core/services/artifact_tag_service.py (associations)
  - skillmeat/core/exceptions.py (update with tag exceptions)

Tests: >80% coverage, validate all edge cases")
```

### Batch 12-16: API Layer (Sequential, 2 days)

```markdown
Task("python-backend-engineer", "API-001-API-005: Create tag API endpoints

Files: skillmeat/api/app/routers/tags.py

API-001: Router setup (APIRouter with proper tags and prefix)
API-002: Tag CRUD endpoints (GET /tags, POST, GET/{id}, PUT, DELETE)
API-003: Artifact-tag endpoints (GET/POST/DELETE /artifacts/{id}/tags)
API-004: Response formatting (consistent envelope, pagination)
API-005: OpenAPI documentation (Swagger specs, examples)

Register router in: skillmeat/api/app/server.py

All endpoints with:
- Proper HTTP methods and status codes
- Request/response validation
- Error handling
- OpenAPI documentation
- Integration tests >80% coverage")
```

---

## Context Files for Implementation

**Backend Architecture**:
- `skillmeat/cache/models.py` - SQLAlchemy base models
- `skillmeat/core/storage/` - Repository layer
- `skillmeat/core/services/` - Service layer
- `skillmeat/api/app/routers/` - API routers
- `skillmeat/storage/migrations/` - Alembic migrations

**Key Patterns**:
- Repository pattern for data access
- Service layer for business logic
- Pydantic schemas for validation
- HTTPException for API errors
- OpenTelemetry for observability

**Related Files**:
- `.claude/rules/api/routers.md` - FastAPI router patterns
- `skillmeat/api/CLAUDE.md` - Backend architecture guide
