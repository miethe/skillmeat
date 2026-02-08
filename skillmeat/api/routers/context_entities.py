"""Context entities API router for managing context artifacts.

This router provides endpoints for managing context entities - special artifacts
that define project structure, rules, specifications, and context for Claude Code
projects. Context entities support path-pattern matching for auto-loading and
categorization for progressive disclosure patterns.

Entity Types:
- ProjectConfig: CLAUDE.md configuration files
- SpecFile: .claude/specs/ specification documents
- RuleFile: .claude/rules/ path-scoped rules
- ContextFile: .claude/context/ knowledge documents
- ProgressTemplate: .claude/progress/ tracking templates

API Endpoints:
    GET /context-entities - List all context entities with filtering
    POST /context-entities - Create new context entity
    GET /context-entities/{entity_id} - Get entity by ID
    PUT /context-entities/{entity_id} - Update existing entity
    DELETE /context-entities/{entity_id} - Delete entity
    GET /context-entities/{entity_id}/content - Get raw markdown content
"""

import hashlib
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from skillmeat.api.schemas.context_entity import (
    ContextEntityCreateRequest,
    ContextEntityListResponse,
    ContextEntityResponse,
    ContextEntityType,
    ContextEntityUpdateRequest,
)
from skillmeat.api.schemas.common import PageInfo
from skillmeat.core.validators.context_entity import validate_context_entity
from skillmeat.core.validators.context_path_validator import validate_context_path

from skillmeat.cache.models import Artifact, Project, get_session

logger = logging.getLogger(__name__)

# Sentinel project ID for context entities (not tied to a real project)
CONTEXT_ENTITIES_PROJECT_ID = "ctx_project_global"


def ensure_context_entities_project(session) -> None:
    """Ensure the sentinel project for context entities exists.

    Context entities are stored as Artifacts but aren't tied to any real project.
    We use a sentinel project to satisfy the foreign key constraint.
    """
    project = session.query(Project).filter_by(id=CONTEXT_ENTITIES_PROJECT_ID).first()
    if not project:
        project = Project(
            id=CONTEXT_ENTITIES_PROJECT_ID,
            name="Context Entities",
            path="~/.skillmeat/context-entities",
            description="Virtual project for context entity storage",
            status="active",
        )
        session.add(project)
        session.commit()
        logger.info(f"Created sentinel project for context entities: {project.id}")


router = APIRouter(
    prefix="/context-entities",
    tags=["context-entities"],
)

# Context entity types mapped to Artifact types
CONTEXT_ENTITY_TYPES = {
    "project_config",
    "spec_file",
    "rule_file",
    "context_file",
    "progress_template",
}


def _as_target_platforms(raw: Optional[List[str]]) -> Optional[List[str]]:
    if raw is None:
        return None
    return [str(item) for item in raw]


def _empty_deployed_to() -> dict:
    # Phase 3 adds response shape; deployment aggregation wiring is added separately.
    return {}


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for change detection.

    Args:
        content: Content to hash

    Returns:
        Hexadecimal SHA-256 hash string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    import base64

    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

    Raises:
        HTTPException: If cursor is invalid
    """
    import base64

    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


# =============================================================================
# Context Entity CRUD Operations
# =============================================================================


@router.get(
    "",
    response_model=ContextEntityListResponse,
    summary="List all context entities",
    description="""
    Retrieve a paginated list of all context entities with optional filtering.

    Query parameters allow filtering by:
    - entity_type: Filter by type (project_config, spec_file, etc.)
    - category: Filter by category (api, web, debugging, etc.)
    - auto_load: Filter by auto-load setting (true/false)
    - search: Search in name, description, or path_pattern

    Results are returned with cursor-based pagination for efficient large-scale queries.
    """,
    responses={
        200: {"description": "Successfully retrieved context entities"},
        400: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_context_entities(
    entity_type: Optional[ContextEntityType] = Query(
        None, description="Filter by entity type"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    auto_load: Optional[bool] = Query(None, description="Filter by auto-load setting"),
    search: Optional[str] = Query(
        None, description="Search in name, description, or path_pattern"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
) -> ContextEntityListResponse:
    """List all context entities with filtering and pagination.

    Args:
        entity_type: Optional type filter
        category: Optional category filter
        auto_load: Optional auto-load filter
        search: Optional search term
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of context entities

    Raises:
        HTTPException: On error

    Note:
        This endpoint uses Artifact model with type filtering.
    """
    session = get_session()
    try:
        # Build query - filter by context entity types
        query = session.query(Artifact).filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))

        # Apply filters
        if entity_type:
            query = query.filter_by(type=entity_type.value)
        if category:
            query = query.filter_by(category=category)
        if auto_load is not None:
            query = query.filter_by(auto_load=auto_load)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Artifact.name.ilike(search_pattern))
                | (Artifact.description.ilike(search_pattern))
                | (Artifact.path_pattern.ilike(search_pattern))
            )

        # Decode cursor if provided
        if after:
            cursor_id = decode_cursor(after)
            query = query.filter(Artifact.id > cursor_id)

        # Order by ID for consistent pagination
        query = query.order_by(Artifact.id)

        # Fetch limit + 1 to check for next page
        artifacts = query.limit(limit + 1).all()

        # Check if there are more pages
        has_next = len(artifacts) > limit
        if has_next:
            artifacts = artifacts[:limit]

        # Build response
        items = [
            ContextEntityResponse(
                id=artifact.id,
                name=artifact.name,
                entity_type=artifact.type,
                content=artifact.content or "",
                path_pattern=artifact.path_pattern or "",
                description=artifact.description,
                category=artifact.category,
                auto_load=artifact.auto_load,
                version=artifact.deployed_version,
                target_platforms=_as_target_platforms(artifact.target_platforms),
                deployed_to=_empty_deployed_to(),
                content_hash=artifact.content_hash,
                created_at=artifact.created_at,
                updated_at=artifact.updated_at,
            )
            for artifact in artifacts
        ]

        # Build pagination info
        start_cursor = encode_cursor(items[0].id) if items else None
        end_cursor = encode_cursor(items[-1].id) if items else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=after is not None,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=None,  # Total count expensive for large datasets
        )

        logger.info(f"Listed {len(items)} context entities")
        return ContextEntityListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing context entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list context entities: {str(e)}",
        )
    finally:
        session.close()


@router.post(
    "",
    response_model=ContextEntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new context entity",
    description="""
    Create a new context entity with validation.

    The content will be validated according to the entity type:
    - ProjectConfig: Markdown with optional frontmatter
    - SpecFile: YAML frontmatter (with 'title') + markdown
    - RuleFile: Markdown with optional path scope comment
    - ContextFile: YAML frontmatter (with 'references') + markdown
    - ProgressTemplate: YAML frontmatter (with 'type: progress') + markdown

    Path pattern must start with '.claude/' and cannot contain '..' for security.
    Content hash is computed automatically for change detection.
    """,
    responses={
        201: {"description": "Context entity created successfully"},
        400: {"description": "Validation error"},
        422: {"description": "Unprocessable entity (schema validation failed)"},
        500: {"description": "Internal server error"},
    },
)
async def create_context_entity(
    request: ContextEntityCreateRequest,
) -> ContextEntityResponse:
    """Create a new context entity.

    Args:
        request: Context entity creation request

    Returns:
        Created context entity with metadata

    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails

    Note:
        This endpoint requires TASK-1.2 (database model) to be completed.
        Current implementation will raise 501 Not Implemented.
    """
    try:
        validate_context_path(
            request.path_pattern,
            allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Validate content using validators from TASK-1.3
    validation_errors = validate_context_entity(
        entity_type=request.entity_type.value,
        content=request.content,
        path=request.path_pattern,
        allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
    )

    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content validation failed: {'; '.join(validation_errors)}",
        )

    # Compute content hash
    content_hash = compute_content_hash(request.content)

    session = get_session()
    try:
        # Ensure sentinel project exists
        ensure_context_entities_project(session)

        # Create artifact with context entity type
        artifact = Artifact(
            id=f"ctx_{uuid.uuid4().hex[:12]}",
            project_id=CONTEXT_ENTITIES_PROJECT_ID,
            name=request.name,
            type=request.entity_type.value,
            content=request.content,
            path_pattern=request.path_pattern,
            description=request.description,
            category=request.category,
            auto_load=request.auto_load,
            deployed_version=request.version if request.version else None,
            target_platforms=(
                [platform.value for platform in request.target_platforms]
                if request.target_platforms is not None
                else None
            ),
            content_hash=content_hash,
        )

        session.add(artifact)
        session.commit()
        session.refresh(artifact)

        logger.info(
            f"Created context entity: {artifact.id} ('{artifact.name}') type={artifact.type}"
        )

        return ContextEntityResponse(
            id=artifact.id,
            name=artifact.name,
            entity_type=artifact.type,
            content=artifact.content or "",
            path_pattern=artifact.path_pattern or "",
            description=artifact.description,
            category=artifact.category,
            auto_load=artifact.auto_load,
            version=artifact.deployed_version,
            target_platforms=_as_target_platforms(artifact.target_platforms),
            deployed_to=_empty_deployed_to(),
            content_hash=artifact.content_hash,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating context entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Context entity with this name or path pattern already exists",
        ) from e
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create context entity: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create context entity",
        ) from e
    finally:
        session.close()


@router.get(
    "/{entity_id}",
    response_model=ContextEntityResponse,
    summary="Get context entity details",
    description="""
    Retrieve detailed information about a specific context entity by ID.

    Returns full entity metadata including:
    - Name, type, and description
    - Path pattern and auto-load settings
    - Category for progressive disclosure
    - Version and content hash
    - Created/updated timestamps
    """,
    responses={
        200: {"description": "Successfully retrieved context entity"},
        404: {"description": "Context entity not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_context_entity(entity_id: str) -> ContextEntityResponse:
    """Get a single context entity by ID.

    Args:
        entity_id: Context entity identifier

    Returns:
        Context entity details

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails

    Note:
        This endpoint uses Artifact model with type filtering.
    """
    session = get_session()
    try:
        artifact = (
            session.query(Artifact)
            .filter(Artifact.id == entity_id)
            .filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))
            .first()
        )
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        logger.info(f"Retrieved context entity {entity_id}")
        return ContextEntityResponse(
            id=artifact.id,
            name=artifact.name,
            entity_type=artifact.type,
            content=artifact.content or "",
            path_pattern=artifact.path_pattern or "",
            description=artifact.description,
            category=artifact.category,
            auto_load=artifact.auto_load,
            version=artifact.deployed_version,
            target_platforms=_as_target_platforms(artifact.target_platforms),
            deployed_to=_empty_deployed_to(),
            content_hash=artifact.content_hash,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context entity '{entity_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context entity: {str(e)}",
        )
    finally:
        session.close()


@router.put(
    "/{entity_id}",
    response_model=ContextEntityResponse,
    summary="Update context entity",
    description="""
    Update an existing context entity.

    All fields are optional - only provided fields will be updated.
    If content is updated, the content_hash will be recomputed automatically.
    Updated content is validated according to the entity type (or new type if changed).
    """,
    responses={
        200: {"description": "Context entity updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Context entity not found"},
        422: {"description": "Unprocessable entity (schema validation failed)"},
        500: {"description": "Internal server error"},
    },
)
async def update_context_entity(
    entity_id: str, request: ContextEntityUpdateRequest
) -> ContextEntityResponse:
    """Update a context entity's metadata and/or content.

    Args:
        entity_id: Context entity identifier
        request: Update request with optional fields

    Returns:
        Updated context entity

    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails

    Note:
        This endpoint uses Artifact model with type filtering.
    """
    session = get_session()
    try:
        artifact = (
            session.query(Artifact)
            .filter(Artifact.id == entity_id)
            .filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))
            .first()
        )
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        # Track if content changed
        content_changed = False

        # Update fields
        if request.name is not None:
            artifact.name = request.name
        if request.entity_type is not None:
            artifact.type = request.entity_type.value
        if request.content is not None:
            artifact.content = request.content
            content_changed = True
        if request.path_pattern is not None:
            try:
                validate_context_path(
                    request.path_pattern,
                    allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            artifact.path_pattern = request.path_pattern
        if request.description is not None:
            artifact.description = request.description
        if request.category is not None:
            artifact.category = request.category
        if request.auto_load is not None:
            artifact.auto_load = request.auto_load
        if request.version is not None:
            artifact.deployed_version = request.version
        if request.target_platforms is not None:
            artifact.target_platforms = [
                platform.value for platform in request.target_platforms
            ]

        # Validate content if changed or type changed
        if content_changed or request.entity_type is not None:
            validation_errors = validate_context_entity(
                entity_type=artifact.type,
                content=artifact.content or "",
                path=artifact.path_pattern or "",
                allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
            )
            if validation_errors:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Content validation failed: {'; '.join(validation_errors)}",
                )

        # Recompute content hash if content changed
        if content_changed:
            artifact.content_hash = compute_content_hash(artifact.content or "")

        session.commit()
        session.refresh(artifact)

        logger.info(f"Updated context entity {entity_id}")
        return ContextEntityResponse(
            id=artifact.id,
            name=artifact.name,
            entity_type=artifact.type,
            content=artifact.content or "",
            path_pattern=artifact.path_pattern or "",
            description=artifact.description,
            category=artifact.category,
            auto_load=artifact.auto_load,
            version=artifact.deployed_version,
            target_platforms=_as_target_platforms(artifact.target_platforms),
            deployed_to=_empty_deployed_to(),
            content_hash=artifact.content_hash,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error updating context entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Context entity with this name or path pattern already exists",
        ) from e
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update context entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update context entity",
        ) from e
    finally:
        session.close()


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete context entity",
    description="""
    Delete a context entity from the database.

    This is a permanent operation and cannot be undone.
    The entity's content will be lost unless backed up elsewhere.
    """,
    responses={
        204: {"description": "Context entity deleted successfully"},
        404: {"description": "Context entity not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_context_entity(entity_id: str) -> None:
    """Delete a context entity.

    Args:
        entity_id: Context entity identifier

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails

    Note:
        This endpoint uses Artifact model with type filtering.
    """
    session = get_session()
    try:
        artifact = (
            session.query(Artifact)
            .filter(Artifact.id == entity_id)
            .filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))
            .first()
        )
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        session.delete(artifact)
        session.commit()

        logger.info(f"Deleted context entity {entity_id}")

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to delete context entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete context entity",
        ) from e
    finally:
        session.close()


@router.get(
    "/{entity_id}/content",
    response_class=Response,
    summary="Get raw markdown content",
    description="""
    Retrieve the raw markdown content of a context entity.

    Returns the content as text/plain for easy downloading or previewing.
    Useful for:
    - Downloading entity content
    - Previewing in raw format
    - Integration with external tools
    """,
    responses={
        200: {
            "description": "Raw markdown content",
            "content": {
                "text/plain": {"example": "# My Context File\n\nContent here..."}
            },
        },
        404: {"description": "Context entity not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_context_entity_content(entity_id: str) -> Response:
    """Get raw markdown content of a context entity.

    Args:
        entity_id: Context entity identifier

    Returns:
        Response with text/plain content

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails

    Note:
        This endpoint uses Artifact model with type filtering.
    """
    session = get_session()
    try:
        artifact = (
            session.query(Artifact)
            .filter(Artifact.id == entity_id)
            .filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))
            .first()
        )
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        logger.info(f"Retrieved content for context entity {entity_id}")
        return Response(
            content=artifact.content or "",
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{artifact.name}.md"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting content for context entity '{entity_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context entity content: {str(e)}",
        )
    finally:
        session.close()
