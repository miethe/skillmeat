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
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from skillmeat.api.config import APISettings, get_settings
from skillmeat.api.dependencies import ContextEntityRepoDep
from skillmeat.api.schemas.context_entity import (
    ContextEntityCreateRequest,
    ContextEntityDeployRequest,
    ContextEntityDeployResponse,
    ContextEntityListResponse,
    ContextEntityResponse,
    ContextEntityType,
    ContextEntityUpdateRequest,
)
from skillmeat.api.schemas.common import PageInfo
from skillmeat.cache.repositories import DeploymentProfileRepository
from skillmeat.core.content_assembly import assemble_content
from skillmeat.core.interfaces.dtos import ContextEntityDTO
from skillmeat.core.path_resolver import default_project_config_filenames
from skillmeat.core.validators.context_entity import validate_context_entity
from skillmeat.core.validators.context_path_validator import (
    normalize_context_prefixes,
    resolve_project_profile,
    rewrite_path_for_profile,
    validate_context_path,
)

# Type alias for injected settings dependency
SettingsDep = Annotated[APISettings, Depends(get_settings)]

logger = logging.getLogger(__name__)

# Sentinel project ID for context entities (not tied to a real project)
CONTEXT_ENTITIES_PROJECT_ID = "ctx_project_global"


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


def _profile_platform(profile: object) -> str:
    platform = getattr(profile, "platform", None)
    if hasattr(platform, "value"):
        return str(platform.value)
    return str(platform or "")


def _profile_id(profile: object) -> str:
    return str(getattr(profile, "profile_id", "claude_code"))


def _resolve_deploy_profiles(
    *,
    project_path: Path,
    deployment_profile_id: Optional[str],
    all_profiles: bool,
) -> List[object]:
    if not all_profiles:
        return [resolve_project_profile(project_path, deployment_profile_id)]

    repo = DeploymentProfileRepository()
    project_id = repo.get_project_id_by_path(str(project_path))
    if project_id:
        profiles = repo.list_all_profiles(project_id)
        if profiles:
            # Deduplicate by profile_id in case repository data includes stale duplicates.
            seen: set[str] = set()
            unique_profiles = []
            for profile in profiles:
                pid = _profile_id(profile)
                if pid in seen:
                    continue
                seen.add(pid)
                unique_profiles.append(profile)
            return unique_profiles

    # Legacy projects may not have persisted deployment profiles.
    return [resolve_project_profile(project_path, deployment_profile_id)]


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


def _dto_to_response(dto: ContextEntityDTO) -> ContextEntityResponse:
    """Convert a ContextEntityDTO to a ContextEntityResponse.

    Args:
        dto: Repository DTO

    Returns:
        API response model
    """
    return ContextEntityResponse(
        id=dto.id,
        name=dto.name,
        entity_type=dto.entity_type,
        content=dto.content,
        path_pattern=dto.path_pattern,
        description=dto.description,
        category=dto.category,
        auto_load=dto.auto_load,
        version=dto.version,
        target_platforms=_as_target_platforms(dto.target_platforms) if dto.target_platforms else None,
        deployed_to=_empty_deployed_to(),
        content_hash=dto.content_hash,
        category_ids=list(dto.category_ids),
        created_at=dto.created_at,
        updated_at=dto.updated_at,
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
    repo: ContextEntityRepoDep,
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
        repo: Context entity repository (injected)
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
    """
    try:
        # Build filters dict for the repository
        filters: dict = {}
        if entity_type:
            filters["entity_type"] = entity_type.value
        if category:
            filters["category"] = category
        if auto_load is not None:
            filters["auto_load"] = auto_load
        if search:
            filters["search"] = search

        # Fetch limit + 1 to detect next page
        dtos = repo.list(filters=filters, limit=limit + 1, after=after)

        has_next = len(dtos) > limit
        if has_next:
            dtos = dtos[:limit]

        items = [_dto_to_response(dto) for dto in dtos]

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
    repo: ContextEntityRepoDep,
    settings: SettingsDep,
) -> ContextEntityResponse:
    """Create a new context entity.

    Args:
        request: Context entity creation request
        repo: Context entity repository (injected)
        settings: API settings (injected)

    Returns:
        Created context entity with metadata

    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails
    """
    try:
        validate_context_path(
            request.path_pattern,
            allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"field": "path_pattern", "hint": str(exc)}],
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
            detail=validation_errors,
        )

    # Determine stored content values.
    # When modular_content_architecture is enabled we split the incoming
    # content into core_content (platform-agnostic) and content (assembled
    # for the default/first target platform).  The assembled value is used
    # for backward-compatible reads; the deploy endpoint re-assembles at
    # deploy time.
    stored_core_content: Optional[str] = None
    assembled_content: str = request.content

    if settings.modular_content_architecture:
        stored_core_content = request.content
        # Determine the default platform for initial assembly
        entity_type_config = {"slug": request.entity_type.value}
        default_platform: str = "claude-code"
        if request.target_platforms:
            default_platform = request.target_platforms[0].value
        assembled_content = assemble_content(
            core_content=stored_core_content,
            entity_type_config=entity_type_config,
            platform=default_platform,
        )
        logger.debug(
            "modular_content_architecture: assembled content for platform=%r "
            "(entity_type=%r)",
            default_platform,
            request.entity_type.value,
        )

    try:
        dto = repo.create(
            name=request.name,
            entity_type=request.entity_type.value,
            content=assembled_content,
            path_pattern=request.path_pattern,
            description=request.description,
            category=request.category,
            auto_load=request.auto_load if request.auto_load is not None else False,
            version=request.version if request.version else None,
            target_platforms=(
                [platform.value for platform in request.target_platforms]
                if request.target_platforms is not None
                else None
            ),
            category_ids=request.category_ids,
        )

        # If modular content architecture is enabled, update core_content separately
        # since the create() method doesn't expose a core_content parameter.
        # We rely on the repo's update() to set it when present.
        if settings.modular_content_architecture and stored_core_content is not None:
            dto = repo.update(dto.id, {"core_content": stored_core_content})

        logger.info(
            f"Created context entity: {dto.id} ('{dto.name}') type={dto.entity_type}"
        )
        return _dto_to_response(dto)

    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error creating context entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Context entity with this name or path pattern already exists",
        ) from e
    except ValueError as e:
        logger.error(f"Validation error creating context entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Failed to create context entity: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create context entity",
        ) from e


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
async def get_context_entity(
    entity_id: str,
    repo: ContextEntityRepoDep,
) -> ContextEntityResponse:
    """Get a single context entity by ID.

    Args:
        entity_id: Context entity identifier
        repo: Context entity repository (injected)

    Returns:
        Context entity details

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails
    """
    try:
        dto = repo.get(entity_id)
        if not dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        logger.info(f"Retrieved context entity {entity_id}")
        return _dto_to_response(dto)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context entity '{entity_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context entity: {str(e)}",
        )


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
    entity_id: str,
    request: ContextEntityUpdateRequest,
    repo: ContextEntityRepoDep,
    settings: SettingsDep,
) -> ContextEntityResponse:
    """Update a context entity's metadata and/or content.

    Args:
        entity_id: Context entity identifier
        request: Update request with optional fields
        repo: Context entity repository (injected)
        settings: API settings (injected)

    Returns:
        Updated context entity

    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails
    """
    try:
        # Fetch current state for validation
        current = repo.get(entity_id)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        # Validate path_pattern if being updated
        if request.path_pattern is not None:
            try:
                validate_context_path(
                    request.path_pattern,
                    allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=[{"field": "path_pattern", "hint": str(exc)}],
                ) from exc

        # Determine effective type and content for validation
        effective_type = (
            request.entity_type.value
            if request.entity_type is not None
            else current.entity_type
        )
        content_changed = request.content is not None

        # Build the updates dict for the repository
        updates: dict = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.entity_type is not None:
            updates["entity_type"] = request.entity_type.value
        if request.content is not None:
            if settings.modular_content_architecture:
                # Store the raw author-supplied content as core_content and
                # assemble the default platform-specific version into content.
                updates["core_content"] = request.content
                entity_type_config = {"slug": effective_type}
                platforms = _as_target_platforms(current.target_platforms)
                default_platform = platforms[0] if platforms else "claude-code"
                assembled = assemble_content(
                    core_content=request.content,
                    entity_type_config=entity_type_config,
                    platform=default_platform,
                )
                updates["content"] = assembled
                logger.debug(
                    "modular_content_architecture: re-assembled content for "
                    "platform=%r (entity_type=%r, entity_id=%r)",
                    default_platform,
                    effective_type,
                    entity_id,
                )
            else:
                updates["content"] = request.content
        if request.path_pattern is not None:
            updates["path_pattern"] = request.path_pattern
        if request.description is not None:
            updates["description"] = request.description
        if request.category is not None:
            updates["category"] = request.category
        if request.auto_load is not None:
            updates["auto_load"] = request.auto_load
        if request.version is not None:
            updates["version"] = request.version
        if request.target_platforms is not None:
            updates["target_platforms"] = [
                platform.value for platform in request.target_platforms
            ]
        if request.category_ids is not None:
            updates["category_ids"] = request.category_ids

        # Validate content if changed or type changed
        if content_changed or request.entity_type is not None:
            effective_content = updates.get("content", current.content) or ""
            effective_path = updates.get("path_pattern", current.path_pattern) or ""
            validation_errors = validate_context_entity(
                entity_type=effective_type,
                content=effective_content,
                path=effective_path,
                allowed_prefixes=[".claude/", ".codex/", ".gemini/", ".cursor/"],
            )
            if validation_errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_errors,
                )

        dto = repo.update(entity_id, updates)

        logger.info(f"Updated context entity {entity_id}")
        return _dto_to_response(dto)

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context entity '{entity_id}' not found",
        ) from e
    except IntegrityError as e:
        logger.error(f"Integrity error updating context entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Context entity with this name or path pattern already exists",
        ) from e
    except Exception as e:
        logger.error(f"Failed to update context entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update context entity",
        ) from e


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
async def delete_context_entity(
    entity_id: str,
    repo: ContextEntityRepoDep,
) -> None:
    """Delete a context entity.

    Args:
        entity_id: Context entity identifier
        repo: Context entity repository (injected)

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails
    """
    try:
        repo.delete(entity_id)
        logger.info(f"Deleted context entity {entity_id}")

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context entity '{entity_id}' not found",
        ) from e
    except Exception as e:
        logger.error(f"Failed to delete context entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete context entity",
        ) from e


@router.post(
    "/{entity_id}/deploy",
    response_model=ContextEntityDeployResponse,
    summary="Deploy context entity to a project",
    description=(
        "Deploy a context entity to the target project using a selected deployment "
        "profile or all configured profiles."
    ),
    responses={
        200: {"description": "Context entity deployed successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Context entity not found"},
        409: {"description": "Destination file exists and overwrite=false"},
        500: {"description": "Internal server error"},
    },
)
async def deploy_context_entity(
    entity_id: str,
    request: ContextEntityDeployRequest,
    repo: ContextEntityRepoDep,
    settings: SettingsDep,
) -> ContextEntityDeployResponse:
    if request.all_profiles and request.deployment_profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deployment_profile_id cannot be set when all_profiles=true",
        )

    project_path = Path(request.project_path).expanduser().resolve()
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project path does not exist: {project_path}",
        )

    try:
        dto = repo.get(entity_id)
        if not dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )
        if not dto.path_pattern:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Context entity '{entity_id}' has no path_pattern",
            )

        profiles = _resolve_deploy_profiles(
            project_path=project_path,
            deployment_profile_id=request.deployment_profile_id,
            all_profiles=request.all_profiles,
        )

        target_platforms = _as_target_platforms(dto.target_platforms) if dto.target_platforms else None
        # Base content used when no per-profile assembly is needed.
        # The per-profile assembly (below) may override this for each profile.
        _base_content = dto.content or ""
        deployment_targets: List[tuple[str, str, Path]] = []

        # Validate all targets before writing files to avoid partial multi-profile deploys.
        for profile in profiles:
            profile_id = _profile_id(profile)
            profile_platform = _profile_platform(profile)

            if (
                target_platforms
                and profile_platform not in target_platforms
                and not request.force
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Entity target_platforms does not include selected profile platform "
                        f"for profile '{profile_id}'"
                    ),
                )

            selected_path = rewrite_path_for_profile(dto.path_pattern, profile)
            config_filenames = list(getattr(profile, "config_filenames", []) or [])
            config_filenames.extend(
                default_project_config_filenames(getattr(profile, "platform", None))
            )

            try:
                validated = validate_context_path(
                    selected_path,
                    project=project_path,
                    profile=profile,
                    profile_id=profile_id,
                    allowed_prefixes=normalize_context_prefixes(profile),
                    config_filenames=config_filenames,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc

            if validated.resolved_path is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to resolve deployment target path",
                )
            deployment_targets.append((profile_id, profile_platform, validated.resolved_path))

        deployed_paths: List[str] = []
        deployed_profiles: List[str] = []
        for profile_id, profile_platform, target_path in deployment_targets:
            # Assemble platform-specific content when the flag is enabled and
            # core_content is available; fall back to the pre-assembled content
            # stored in dto.content for backward compatibility.
            if settings.modular_content_architecture and dto.core_content is not None:
                entity_type_config = {"slug": dto.entity_type}
                content = assemble_content(
                    core_content=dto.core_content,
                    entity_type_config=entity_type_config,
                    platform=profile_platform,
                )
                logger.debug(
                    "modular_content_architecture: assembled deploy content for "
                    "platform=%r (entity_type=%r, entity_id=%r)",
                    profile_platform,
                    dto.entity_type,
                    entity_id,
                )
            else:
                content = _base_content

            should_write = True
            if target_path.exists():
                existing_content = target_path.read_text(encoding="utf-8")
                if existing_content != content and not request.overwrite:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"File already exists: {target_path}",
                    )
                if existing_content == content and not request.overwrite:
                    should_write = False

            if should_write:
                # TODO: migrate to repository — direct filesystem write; IContextEntityRepository
                # would expose deploy(entity_id, target_path, content) to abstract this.
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")

            relative_path = target_path.relative_to(project_path).as_posix()
            deployed_paths.append(relative_path)
            deployed_profiles.append(profile_id)

        profile_label = (
            "all configured profiles" if request.all_profiles else deployed_profiles[0]
        )
        logger.info(
            "Deployed context entity %s to %s (%s)",
            entity_id,
            project_path,
            profile_label,
        )

        return ContextEntityDeployResponse(
            success=True,
            entity_id=entity_id,
            project_path=str(project_path),
            deployed_paths=deployed_paths,
            deployed_profiles=deployed_profiles,
            message=(
                f"Deployed '{dto.name}' to {len(deployed_profiles)} profile(s)"
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed deploying context entity '%s' to '%s': %s",
            entity_id,
            project_path,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy context entity",
        ) from e


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
async def get_context_entity_content(
    entity_id: str,
    repo: ContextEntityRepoDep,
) -> Response:
    """Get raw markdown content of a context entity.

    Args:
        entity_id: Context entity identifier
        repo: Context entity repository (injected)

    Returns:
        Response with text/plain content

    Raises:
        HTTPException 404: If entity not found
        HTTPException 500: If database operation fails
    """
    try:
        # First get the entity to retrieve the name for Content-Disposition
        dto = repo.get(entity_id)
        if not dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context entity '{entity_id}' not found",
            )

        logger.info(f"Retrieved content for context entity {entity_id}")
        return Response(
            content=dto.content or "",
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{dto.name}.md"'
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
