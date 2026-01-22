# Phase 1: Backend Infrastructure & Field Registry (5 days)

**Story Points**: 25 | **Duration**: 5 days | **Team**: Backend Engineer

---

## Phase Overview

Phase 1 establishes the backend foundation for the Global Fields Management feature. This phase focuses on creating the field registry system, implementing the FieldsService wrapper, defining API schemas, and building the `/api/v1/fields/*` router. All work follows the MeatyPrompts layered architecture: Database → Repository → Service → API Router.

### Phase Goals

1. Create Field Registry to enumerate manageable fields per object type
2. Implement FieldsService wrapping existing TagService
3. Create `/api/v1/fields/*` router with full CRUD endpoints
4. Define Pydantic request/response DTOs
5. Establish error handling patterns with proper validation
6. Achieve >80% unit test coverage

### Deliverables

- `skillmeat/core/registry/field_registry.py` - Field registry configuration
- `skillmeat/core/services/fields_service.py` - Fields business logic service
- `skillmeat/api/schemas/fields.py` - Request/response DTOs
- `skillmeat/api/routers/fields.py` - API endpoints
- `tests/unit/core/services/test_fields_service.py` - Unit test suite
- `tests/api/routers/test_fields_router.py` - Integration test suite

---

## Detailed Task Breakdown

### Task GFM-IMPL-1.1: Create Field Registry

**Objective**: Define FieldRegistry class to enumerate manageable fields per object type

**Technical Specification**:

Create `skillmeat/core/registry/field_registry.py` with:

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class ObjectType(str, Enum):
    """Object types that have manageable fields."""
    ARTIFACTS = "artifacts"
    MARKETPLACE_SOURCES = "marketplace_sources"

class FieldType(str, Enum):
    """Field data types."""
    TAG = "tag"
    ENUM = "enum"
    STRING = "string"

@dataclass
class FieldMetadata:
    """Metadata for a manageable field."""
    name: str
    object_type: ObjectType
    field_type: FieldType
    readonly: bool
    description: str
    enum_values: Optional[List[str]] = None  # For ENUM fields
    validation_rules: Optional[Dict[str, any]] = None

class FieldRegistry:
    """Central registry for all manageable fields."""

    _fields: Dict[tuple[ObjectType, str], FieldMetadata] = {
        (ObjectType.ARTIFACTS, "tags"): FieldMetadata(
            name="tags",
            object_type=ObjectType.ARTIFACTS,
            field_type=FieldType.TAG,
            readonly=False,
            description="Artifact tags for organization",
        ),
        (ObjectType.ARTIFACTS, "origin"): FieldMetadata(
            name="origin",
            object_type=ObjectType.ARTIFACTS,
            field_type=FieldType.ENUM,
            readonly=True,  # View-only in Phase 1
            description="Artifact origin (local, github, marketplace)",
            enum_values=["local", "github", "marketplace"],
        ),
        # Marketplace source fields
        (ObjectType.MARKETPLACE_SOURCES, "tags"): FieldMetadata(
            name="tags",
            object_type=ObjectType.MARKETPLACE_SOURCES,
            field_type=FieldType.TAG,
            readonly=False,
            description="Marketplace source tags",
        ),
        (ObjectType.MARKETPLACE_SOURCES, "trust_level"): FieldMetadata(
            name="trust_level",
            object_type=ObjectType.MARKETPLACE_SOURCES,
            field_type=FieldType.ENUM,
            readonly=True,
            description="Trust level (High, Medium, Low)",
            enum_values=["High", "Medium", "Low"],
        ),
        (ObjectType.MARKETPLACE_SOURCES, "visibility"): FieldMetadata(
            name="visibility",
            object_type=ObjectType.MARKETPLACE_SOURCES,
            field_type=FieldType.ENUM,
            readonly=True,
            description="Visibility setting (Public, Private)",
            enum_values=["Public", "Private"],
        ),
        (ObjectType.MARKETPLACE_SOURCES, "auto_tags"): FieldMetadata(
            name="auto_tags",
            object_type=ObjectType.MARKETPLACE_SOURCES,
            field_type=FieldType.TAG,
            readonly=True,
            description="System-generated tags from GitHub topics",
        ),
    }

    @classmethod
    def get_fields(cls, object_type: ObjectType) -> List[FieldMetadata]:
        """Get all fields for an object type."""
        return [meta for key, meta in cls._fields.items() if key[0] == object_type]

    @classmethod
    def get_field(cls, object_type: ObjectType, field_name: str) -> Optional[FieldMetadata]:
        """Get specific field metadata."""
        return cls._fields.get((object_type, field_name))

    @classmethod
    def is_valid_field(cls, object_type: ObjectType, field_name: str) -> bool:
        """Check if field exists for object type."""
        return (object_type, field_name) in cls._fields
```

**Acceptance Criteria**:

- [ ] Registry loads from config without errors
- [ ] Returns field metadata (name, type, readonly, enum_values)
- [ ] Supports lookup by object_type + field_name
- [ ] Clearly marks read-only fields
- [ ] Includes enum values for system fields

**Implementation Notes**:

- Hardcode field definitions in Phase 1; make configurable in future phase if needed
- Read-only status controls UI and API behavior (no edit/remove for readonly)
- Enum values for marketplace fields are currently fixed; future phase can make user-editable

---

### Task GFM-IMPL-1.2: Create FieldsService

**Objective**: Implement FieldsService wrapping existing TagService for field operations

**Technical Specification**:

Create `skillmeat/core/services/fields_service.py` with:

```python
from typing import List, Optional
from skillmeat.core.registry.field_registry import FieldRegistry, ObjectType, FieldType
from skillmeat.core.services.tag_service import TagService
from skillmeat.api.schemas.fields import FieldOptionResponse
from skillmeat.cache.repositories import RepositoryError

class FieldsService:
    """Service for managing field options across the system."""

    def __init__(self, db_path: Optional[str] = None):
        self.registry = FieldRegistry()
        self.tag_service = TagService(db_path=db_path)
        self.logger = logging.getLogger(__name__)

    def list_field_options(
        self,
        object_type: str,
        field_name: str,
        limit: int = 50,
        after_cursor: Optional[str] = None,
    ) -> List[FieldOptionResponse]:
        """List options for a specific field with pagination."""
        # Validate field
        obj_type = ObjectType(object_type)
        if not self.registry.is_valid_field(obj_type, field_name):
            raise ValueError(f"Invalid field: {object_type}/{field_name}")

        # For tags, delegate to TagService
        if field_name == "tags":
            result = self.tag_service.list_tags(limit=limit, after_cursor=after_cursor)
            return result.items  # Return FieldOptionResponse items

        # For enum fields (read-only), return enum values
        field_meta = self.registry.get_field(obj_type, field_name)
        if field_meta.field_type == FieldType.ENUM and field_meta.enum_values:
            return [
                FieldOptionResponse(
                    id=val,
                    name=val,
                    color=None,
                    usage_count=0,  # Placeholder
                    readonly=True,
                )
                for val in field_meta.enum_values
            ]

        return []

    def create_field_option(
        self,
        object_type: str,
        field_name: str,
        name: str,
        color: Optional[str] = None,
    ) -> FieldOptionResponse:
        """Create a new field option."""
        obj_type = ObjectType(object_type)
        field_meta = self.registry.get_field(obj_type, field_name)

        if not field_meta:
            raise ValueError(f"Invalid field: {object_type}/{field_name}")

        if field_meta.readonly:
            raise ValueError(f"Field '{field_name}' is read-only")

        # For tags, delegate to TagService
        if field_meta.field_type == FieldType.TAG:
            from skillmeat.api.schemas.tags import TagCreateRequest
            request = TagCreateRequest(
                name=name,
                slug=self.tag_service._slugify(name),
                color=color,
            )
            tag = self.tag_service.create_tag(request)
            return FieldOptionResponse.from_tag(tag)

        raise ValueError(f"Unsupported field type: {field_meta.field_type}")

    def update_field_option(
        self,
        object_type: str,
        field_name: str,
        option_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
    ) -> FieldOptionResponse:
        """Update a field option."""
        obj_type = ObjectType(object_type)
        field_meta = self.registry.get_field(obj_type, field_name)

        if not field_meta:
            raise ValueError(f"Invalid field: {object_type}/{field_name}")

        if field_meta.readonly:
            raise ValueError(f"Field '{field_name}' is read-only")

        # For tags, delegate to TagService
        if field_meta.field_type == FieldType.TAG:
            from skillmeat.api.schemas.tags import TagUpdateRequest
            request = TagUpdateRequest(name=name, color=color)
            tag = self.tag_service.update_tag(option_id, request)
            return FieldOptionResponse.from_tag(tag)

        raise ValueError(f"Unsupported field type: {field_meta.field_type}")

    def delete_field_option(
        self,
        object_type: str,
        field_name: str,
        option_id: str,
    ) -> int:
        """Delete a field option; returns cascade_count for tags."""
        obj_type = ObjectType(object_type)
        field_meta = self.registry.get_field(obj_type, field_name)

        if not field_meta:
            raise ValueError(f"Invalid field: {object_type}/{field_name}")

        if field_meta.readonly:
            raise ValueError(f"Field '{field_name}' is read-only")

        # For tags, cascade delete from artifacts
        if field_meta.field_type == FieldType.TAG:
            # Get usage count before deleting
            tag = self.tag_service.get_tag(option_id)
            cascade_count = tag.artifact_count if tag else 0

            # Delete tag (cascades to artifacts)
            deleted = self.tag_service.delete_tag(option_id)

            if deleted:
                self.logger.info(
                    f"Deleted tag {option_id}; cascaded to {cascade_count} artifacts"
                )
                return cascade_count
            else:
                raise ValueError(f"Tag not found: {option_id}")

        raise ValueError(f"Unsupported field type: {field_meta.field_type}")

    def validate_option_name(self, name: str, field_name: str) -> None:
        """Validate option name for a field."""
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        if len(name) > 100:
            raise ValueError("Name cannot exceed 100 characters")

    def validate_option_color(self, color: Optional[str]) -> None:
        """Validate hex color code."""
        if not color:
            return  # Optional

        # Hex color pattern: #RRGGBB or #RGB
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color):
            raise ValueError("Color must be valid hex code (#RRGGBB or #RGB)")
```

**Acceptance Criteria**:

- [ ] FieldsService methods: list, create, update, delete for field options
- [ ] Delegates to TagService for tag operations
- [ ] Validates readonly fields (prevent edit/remove)
- [ ] Handles validation errors with clear messages
- [ ] Returns cascade_count for tag deletions
- [ ] Logs operations with trace_id (future integration with OpenTelemetry)

---

### Task GFM-IMPL-1.3: Create Field Schemas

**Objective**: Define Pydantic request/response models

**Technical Specification**:

Create `skillmeat/api/schemas/fields.py` with:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from skillmeat.api.schemas.common import PageInfo

class FieldOptionResponse(BaseModel):
    """Response model for a field option (tag or enum value)."""
    id: str
    name: str
    color: Optional[str] = None
    usage_count: int = 0
    readonly: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_tag(cls, tag):
        """Convert Tag ORM to FieldOptionResponse."""
        return cls(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            usage_count=tag.artifact_count or 0,
            readonly=False,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )

class FieldListResponse(BaseModel):
    """Response model for listing field options."""
    items: List[FieldOptionResponse]
    page_info: PageInfo

class CreateFieldOptionRequest(BaseModel):
    """Request model for creating a field option."""
    object_type: str = Field(..., description="Object type (artifacts or marketplace_sources)")
    field_name: str = Field(..., description="Field name (tags, origin, trust_level, etc.)")
    name: str = Field(..., min_length=1, max_length=100, description="Option name")
    color: Optional[str] = Field(None, description="Hex color code for tags")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        if not v:
            return None
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
            raise ValueError("Color must be valid hex code (#RRGGBB or #RGB)")
        return v

class UpdateFieldOptionRequest(BaseModel):
    """Request model for updating a field option."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        if not v:
            return None
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
            raise ValueError("Color must be valid hex code")
        return v

class DeleteFieldOptionResponse(BaseModel):
    """Response model for deletion."""
    success: bool
    cascade_count: int = 0  # Number of artifacts affected (for tags)
    message: str
```

**Acceptance Criteria**:

- [ ] All schemas include proper validation rules
- [ ] Color format validated as hex
- [ ] Name required and non-empty
- [ ] Pydantic validation errors descriptive
- [ ] Schemas support from_attributes for ORM conversion

---

### Task GFM-IMPL-1.4: Create Fields Router

**Objective**: Implement `/api/v1/fields` router with full CRUD endpoints

**Technical Specification**:

Create `skillmeat/api/routers/fields.py` with:

```python
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.fields import (
    CreateFieldOptionRequest,
    UpdateFieldOptionRequest,
    FieldListResponse,
    FieldOptionResponse,
    DeleteFieldOptionResponse,
)
from skillmeat.api.schemas.common import PageInfo
from skillmeat.core.services.fields_service import FieldsService
from skillmeat.core.registry.field_registry import FieldRegistry, ObjectType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/fields",
    tags=["fields"],
)

@router.get(
    "",
    response_model=FieldListResponse,
    summary="List field options",
    description="Get options for a specific field with pagination",
    responses={
        200: {"description": "Field options retrieved successfully"},
        400: {"description": "Invalid field or pagination"},
        500: {"description": "Internal server error"},
    },
)
async def list_field_options(
    object_type: str = Query(..., description="Object type (artifacts or marketplace_sources)"),
    field_name: str = Query(..., description="Field name (tags, origin, trust_level, etc.)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    after: Optional[str] = Query(None, description="Cursor for pagination"),
) -> FieldListResponse:
    """List field options with pagination."""
    service = FieldsService()

    try:
        logger.info(f"Listing {object_type}/{field_name} (limit={limit})")

        items = service.list_field_options(
            object_type=object_type,
            field_name=field_name,
            limit=limit,
            after_cursor=after,
        )

        # Build pagination info (simplified; enhance with actual pagination)
        page_info = PageInfo(
            has_next_page=len(items) >= limit,
            has_previous_page=after is not None,
            start_cursor=items[0].id if items else None,
            end_cursor=items[-1].id if items else None,
        )

        return FieldListResponse(items=items, page_info=page_info)

    except ValueError as e:
        logger.warning(f"Invalid field: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list field options: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

@router.post(
    "/options",
    response_model=FieldOptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create field option",
    description="Create a new option for a field (tags only in Phase 1)",
    responses={
        201: {"description": "Option created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Option already exists"},
        422: {"description": "Validation failed"},
        500: {"description": "Internal server error"},
    },
)
async def create_field_option(request: CreateFieldOptionRequest) -> FieldOptionResponse:
    """Create new field option."""
    service = FieldsService()

    try:
        logger.info(f"Creating {request.object_type}/{request.field_name}: {request.name}")

        option = service.create_field_option(
            object_type=request.object_type,
            field_name=request.field_name,
            name=request.name,
            color=request.color,
        )

        logger.info(f"Created option: {option.id}")
        return option

    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            logger.warning(f"Duplicate option: {e}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        else:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to create option: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

@router.put(
    "/options/{option_id}",
    response_model=FieldOptionResponse,
    summary="Update field option",
    responses={
        200: {"description": "Option updated successfully"},
        404: {"description": "Option not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def update_field_option(
    option_id: str,
    request: UpdateFieldOptionRequest,
    object_type: str = Query(...),
    field_name: str = Query(...),
) -> FieldOptionResponse:
    """Update field option."""
    service = FieldsService()

    try:
        logger.info(f"Updating option {option_id}")

        option = service.update_field_option(
            object_type=object_type,
            field_name=field_name,
            option_id=option_id,
            name=request.name,
            color=request.color,
        )

        logger.info(f"Updated option: {option.id}")
        return option

    except ValueError as e:
        logger.warning(f"Update failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update option: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

@router.delete(
    "/options/{option_id}",
    response_model=DeleteFieldOptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete field option",
    responses={
        200: {"description": "Option deleted successfully"},
        404: {"description": "Option not found"},
        400: {"description": "Cannot delete (in use or read-only)"},
        500: {"description": "Internal server error"},
    },
)
async def delete_field_option(
    option_id: str,
    object_type: str = Query(...),
    field_name: str = Query(...),
) -> DeleteFieldOptionResponse:
    """Delete field option."""
    service = FieldsService()

    try:
        logger.info(f"Deleting option {option_id}")

        cascade_count = service.delete_field_option(
            object_type=object_type,
            field_name=field_name,
            option_id=option_id,
        )

        logger.info(f"Deleted option; cascade_count={cascade_count}")

        return DeleteFieldOptionResponse(
            success=True,
            cascade_count=cascade_count,
            message=f"Option deleted; affected {cascade_count} records",
        )

    except ValueError as e:
        logger.warning(f"Delete failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete option: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")
```

**Acceptance Criteria**:

- [ ] GET /fields returns field options with pagination
- [ ] POST /fields/options creates option (201 Created)
- [ ] PUT /fields/options/{id} updates option (200 OK)
- [ ] DELETE /fields/options/{id} deletes option (200 OK with cascade_count)
- [ ] All endpoints validate input and return proper status codes
- [ ] Error responses include descriptive detail

---

### Task GFM-IMPL-1.5: Error Handling & Validation

**Objective**: Implement validation layer and error handling patterns

**Acceptance Criteria**:

- [ ] 409 Conflict returned for duplicate tag names
- [ ] 422 Unprocessable Entity for validation failures (color format, empty name)
- [ ] 400 Bad Request for in-use field errors
- [ ] 404 Not Found for missing options
- [ ] All errors logged before raising HTTPException
- [ ] Cascade delete operations logged with unique trace_id
- [ ] Validation messages are user-friendly

**Implementation Notes**:

- Use consistent error message format: "{action} failed: {reason}"
- Validate at both schema (Pydantic) and service layers
- Log full exception stack on 500 errors

---

### Task GFM-IMPL-1.6: Unit Tests: FieldsService

**Objective**: Write comprehensive tests for FieldsService

**File**: `tests/unit/core/services/test_fields_service.py`

**Test Coverage**:

```python
def test_create_tag():
    """Test creating a tag via FieldsService."""
    service = FieldsService()
    option = service.create_field_option("artifacts", "tags", "python", color="#3776AB")
    assert option.name == "python"
    assert option.color == "#3776AB"

def test_create_duplicate_tag_rejected():
    """Test duplicate tag names are rejected."""
    service = FieldsService()
    service.create_field_option("artifacts", "tags", "python")
    with pytest.raises(ValueError, match="already exists"):
        service.create_field_option("artifacts", "tags", "python")

def test_invalid_color_rejected():
    """Test invalid color format is rejected."""
    service = FieldsService()
    with pytest.raises(ValueError, match="valid hex"):
        service.create_field_option("artifacts", "tags", "tag", color="invalid")

def test_tag_normalization():
    """Test tag name normalization (trim, lowercase, underscores)."""
    service = FieldsService()
    option = service.create_field_option("artifacts", "tags", "  Python 3  ")
    assert option.name == "Python 3"  # Name preserved; slug normalized

def test_readonly_field_create_rejected():
    """Test creating read-only fields is rejected."""
    service = FieldsService()
    with pytest.raises(ValueError, match="read-only"):
        service.create_field_option("artifacts", "origin", "custom")

def test_list_options_pagination():
    """Test listing options with pagination."""
    service = FieldsService()
    # Create multiple tags
    for i in range(5):
        service.create_field_option("artifacts", "tags", f"tag-{i}")

    result = service.list_field_options("artifacts", "tags", limit=3)
    assert len(result) <= 3

def test_delete_tag_cascade():
    """Test deleting tag cascades to artifacts."""
    service = FieldsService()
    tag = service.create_field_option("artifacts", "tags", "test-tag")

    # Mock artifact association (add tag to artifact)
    # ... (requires artifact repository integration)

    cascade_count = service.delete_field_option("artifacts", "tags", tag.id)
    assert cascade_count >= 0

def test_invalid_field_rejected():
    """Test invalid field raises error."""
    service = FieldsService()
    with pytest.raises(ValueError, match="Invalid field"):
        service.list_field_options("artifacts", "invalid_field")
```

**Acceptance Criteria**:

- [ ] >80% line coverage for FieldsService
- [ ] All CRUD operations tested
- [ ] Validation failures tested
- [ ] Edge cases covered (empty lists, pagination boundaries)
- [ ] Tests run in CI/CD pipeline

---

## API Integration Summary

The `/api/v1/fields` endpoints integrate with existing API infrastructure:

**Endpoint Summary**:

| Method | Path | Status | Response |
|--------|------|--------|----------|
| GET | `/api/v1/fields?object_type=artifacts&field_name=tags` | 200 | FieldListResponse |
| POST | `/api/v1/fields/options` | 201 | FieldOptionResponse |
| PUT | `/api/v1/fields/options/{option_id}?object_type=artifacts&field_name=tags` | 200 | FieldOptionResponse |
| DELETE | `/api/v1/fields/options/{option_id}?object_type=artifacts&field_name=tags` | 200 | DeleteFieldOptionResponse |

**Error Responses**:

```json
{
  "detail": "Tag 'python' already exists"
}
```

---

## Phase 1 Quality Checklist

- [ ] FieldRegistry defines all manageable fields
- [ ] FieldsService wraps TagService correctly
- [ ] API schemas validate input properly
- [ ] Router endpoints implement correct HTTP methods/status codes
- [ ] Error handling returns proper status codes
- [ ] Unit tests achieve >80% coverage
- [ ] Backward compatibility with existing Tag API maintained
- [ ] No breaking changes to existing endpoints

---

**Phase 1 ready for implementation. Backend engineer should start with FieldRegistry, then FieldsService, then router and tests in parallel.**
