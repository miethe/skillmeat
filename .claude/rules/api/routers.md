# Router Layer Patterns

<!-- Path Scope: skillmeat/api/routers/**/*.py -->

FastAPI router layer patterns for request handling and response serialization.

## Layer Contract

✓ **Routers should**:
- Define HTTP endpoints and route handlers
- Parse requests (path/query params, request body)
- Serialize responses (Pydantic models)
- Call service/manager layer for business logic
- Handle HTTP-specific concerns (status codes, headers)
- Document endpoints (OpenAPI tags, descriptions)

✗ **Routers must NOT**:
- Access database directly (use service/manager layer)
- Implement business logic (delegate to core/)
- Validate complex domain rules (use service layer)
- Handle file I/O directly (use managers)
- Perform data transformations (use schemas/services)

## Layered Architecture

```
routers/ (HTTP layer)
    ↓ calls
managers/services (business logic)
    ↓ calls
repositories (data access)
    ↓ calls
database/filesystem
```

**Example Flow**:
```python
# Router → Manager → Repository
@router.post("/user-collections")
async def create_collection(
    request: UserCollectionCreateRequest,
    session: DbSessionDep,
) -> UserCollectionResponse:
    # 1. Parse request (router layer)
    collection_data = request.model_dump()

    # 2. Business logic (manager/service layer)
    collection = create_user_collection(session, collection_data)

    # 3. Serialize response (router layer)
    return UserCollectionResponse.model_validate(collection)
```

## Router Definition

### Structure

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/resource-name",      # e.g., "/user-collections"
    tags=["resource-name"],        # OpenAPI grouping
)
```

### Registration

**File**: `skillmeat/api/server.py`

```python
from skillmeat.api.routers import artifacts, collections, user_collections

# Health check (no prefix)
app.include_router(health.router)

# API routes (with prefix)
app.include_router(
    collections.router,
    prefix=settings.api_prefix,  # "/api/v1"
    tags=["collections"]
)
app.include_router(
    user_collections.router,
    prefix=settings.api_prefix,
    tags=["user-collections"]
)
```

## Available Routers

| Router | Prefix | Purpose | Layer Type |
|--------|--------|---------|------------|
| `health` | `/health` | Health checks | Simple |
| `artifacts` | `/api/v1/artifacts` | Artifact CRUD | Manager-based |
| `collections` | `/api/v1/collections` | Read-only file-based collections | Manager-based |
| `user_collections` | `/api/v1/user-collections` | Database CRUD collections | Database-backed |
| `deployments` | `/api/v1/deployments` | Deployment operations | Manager-based |
| `projects` | `/api/v1/projects` | Project registry | Manager-based |
| `analytics` | `/api/v1/analytics` | Usage analytics | Manager-based |
| `marketplace` | `/api/v1/marketplace` | Claude marketplace | Manager-based |
| `marketplace_sources` | `/api/v1/marketplace-sources` | Marketplace source CRUD | Database-backed |
| `mcp` | `/api/v1/mcp` | MCP server management | Manager-based |
| `bundles` | `/api/v1/bundles` | Artifact bundles | Manager-based |
| `groups` | `/api/v1/groups` | Collection groups | Database-backed |
| `cache` | `/api/v1/cache` | Cache management | Manager-based |

## HTTP Methods & Status Codes

### Standard Mappings

```python
# GET: Retrieve resource(s) → 200 OK
@router.get("/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(artifacts=artifacts)

# POST: Create resource → 201 Created
@router.post("/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(...) -> ArtifactResponse:
    artifact = manager.create_artifact(...)
    return ArtifactResponse.model_validate(artifact)

# PUT: Update resource → 200 OK
@router.put("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(...) -> ArtifactResponse:
    artifact = manager.update_artifact(...)
    return ArtifactResponse.model_validate(artifact)

# DELETE: Remove resource → 204 No Content
@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(...) -> None:
    manager.delete_artifact(artifact_id)
    return None  # or omit return statement
```

## HTTPException Patterns

### Standard Error Codes

```python
from fastapi import HTTPException, status

# 400 Bad Request: Client sent invalid data
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid cursor format: must be base64-encoded"
)

# 404 Not Found: Resource doesn't exist
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Collection '{collection_id}' not found"
)

# 422 Unprocessable Entity: Validation failed
# (Automatically raised by Pydantic for schema validation)
# Only raise manually for domain-specific validation:
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Cannot add artifact: already exists in collection"
)

# 500 Internal Server Error: Unexpected failure
try:
    result = dangerous_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create collection: {str(e)}"
    )
```

### Error Response Schema

```python
from skillmeat.api.schemas.common import ErrorResponse

# All error responses follow ErrorResponse schema
class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: Optional[str] = None  # ErrorCodes enum
```

## Response Models

### response_model Parameter

```python
# Explicit response model (recommended)
@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(...) -> ArtifactResponse:
    return ArtifactResponse(...)

# List response with pagination
@router.get("/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(
        items=[...],
        page_info=PageInfo(...)
    )

# No response body (204)
@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(...) -> None:
    return None
```

### Model Validation

```python
# From dict
return ArtifactResponse(**artifact_dict)

# From ORM model (SQLAlchemy)
return ArtifactResponse.model_validate(orm_object)

# From Pydantic model
return ArtifactResponse.model_validate(request_model)
```

## Dependency Injection

### Type Aliases with Annotated

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

# Database session
DbSessionDep = Annotated[Session, Depends(get_db_session)]

# Manager dependencies (from dependencies.py)
from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    ConfigManagerDep,
)

# Auth token
from skillmeat.api.middleware.auth import TokenDep
```

### Usage in Routes

```python
@router.get("/artifacts")
async def list_artifacts(
    # Manager dependency
    artifact_mgr: ArtifactManagerDep,
    # Database session
    session: DbSessionDep,
    # Auth token (optional)
    token: TokenDep = Depends(verify_api_key),
    # Query parameters
    artifact_type: Optional[str] = Query(None),
) -> ArtifactListResponse:
    artifacts = artifact_mgr.list_artifacts(artifact_type)
    return ArtifactListResponse(artifacts=artifacts)
```

### Database Session Dependency

```python
def get_db_session():
    """Get database session with proper cleanup.

    Yields:
        SQLAlchemy session instance

    Note:
        Session is automatically closed after request completes
    """
    session = get_session()  # from cache.models
    try:
        yield session
    finally:
        session.close()
```

## Request Parameters

### Path Parameters

```python
from fastapi import Path

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str = Path(..., description="Artifact identifier"),
) -> ArtifactResponse:
    ...
```

### Query Parameters

```python
from fastapi import Query

@router.get("/artifacts")
async def list_artifacts(
    # Optional filter
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    # Search
    search: Optional[str] = Query(None, min_length=1, max_length=100),
) -> ArtifactListResponse:
    ...
```

### Request Body

```python
from fastapi import Body

@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,  # Pydantic model
    # OR with Body() for additional validation
    request: ArtifactCreateRequest = Body(..., description="Artifact data"),
) -> ArtifactCreateResponse:
    ...
```

## OpenAPI Documentation

### Tags and Descriptions

```python
@router.get(
    "/artifacts",
    summary="List all artifacts",
    description="Retrieve paginated list of artifacts with optional filtering",
    response_description="List of artifacts with pagination info",
    tags=["artifacts"],  # Override router-level tag if needed
)
async def list_artifacts(...):
    ...
```

### Response Examples

```python
@router.get(
    "/artifacts/{artifact_id}",
    responses={
        200: {
            "description": "Artifact found",
            "content": {
                "application/json": {
                    "example": {
                        "id": "abc123",
                        "name": "canvas-design",
                        "type": "skill",
                    }
                }
            }
        },
        404: {
            "description": "Artifact not found",
            "model": ErrorResponse,
        }
    }
)
async def get_artifact(...):
    ...
```

## Best Practices

### Async Handlers

All route handlers should be async for consistency:

```python
# ✓ Good
@router.get("/artifacts")
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(...)

# ✗ Avoid (use async even if not awaiting)
@router.get("/artifacts")
def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(...)
```

### Error Logging

Always log before raising exceptions:

```python
try:
    result = manager.dangerous_operation()
except ValueError as e:
    logger.warning(f"Validation error: {e}")
    raise HTTPException(400, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(500, detail="Internal server error")
```

### Separation of Concerns

```python
# ✓ Good: Router delegates to manager
@router.post("/collections")
async def create_collection(
    request: CollectionCreateRequest,
    manager: CollectionManagerDep,
) -> CollectionResponse:
    collection = manager.create_collection(request.model_dump())
    return CollectionResponse.model_validate(collection)

# ✗ Bad: Router implements business logic
@router.post("/collections")
async def create_collection(request: CollectionCreateRequest) -> CollectionResponse:
    # Don't do validation, file I/O, etc. in router
    path = Path(request.path)
    path.mkdir(parents=True, exist_ok=True)
    manifest = {"name": request.name}
    (path / "manifest.toml").write_text(toml.dumps(manifest))
    ...
```

### Type Hints

Always use explicit type hints for clarity and OpenAPI generation:

```python
# ✓ Good
async def get_artifact(
    artifact_id: str,
    manager: ArtifactManagerDep,
) -> ArtifactResponse:
    ...

# ✗ Bad
async def get_artifact(artifact_id, manager):
    ...
```
