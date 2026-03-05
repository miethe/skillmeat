"""Project Templates API router for managing template CRUD operations.

This router provides endpoints for managing project templates - reusable collections
of context entities that can be deployed together to initialize Claude Code project
structures. Templates support variable substitution for customization and selective
entity deployment.

API Endpoints:
    GET /project-templates - List all templates with pagination
    GET /project-templates/{template_id} - Get template by ID with entity details
    POST /project-templates - Create new template from entity list
    PUT /project-templates/{template_id} - Update existing template
    DELETE /project-templates/{template_id} - Delete template
    POST /project-templates/{template_id}/deploy - Deploy template to project (Phase 5)
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.dependencies import DbSessionDep, ProjectTemplateRepoDep
from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.project_template import (
    DeployTemplateRequest,
    DeployTemplateResponse,
    ProjectTemplateCreateRequest,
    ProjectTemplateListResponse,
    ProjectTemplateResponse,
    ProjectTemplateUpdateRequest,
    TemplateEntitySchema,
)
from skillmeat.core.interfaces.dtos import ProjectTemplateDTO, TemplateEntityDTO

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/project-templates",
    tags=["project-templates"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _entity_dto_to_schema(dto: TemplateEntityDTO) -> TemplateEntitySchema:
    """Convert a TemplateEntityDTO to a TemplateEntitySchema response model.

    Args:
        dto: TemplateEntityDTO from the repository layer.

    Returns:
        TemplateEntitySchema suitable for API responses.
    """
    return TemplateEntitySchema(
        artifact_id=dto.artifact_id,
        name=dto.name,
        type=dto.artifact_type,
        deploy_order=dto.deploy_order,
        required=dto.required,
        path_pattern=dto.path_pattern,
    )


def _template_dto_to_response(dto: ProjectTemplateDTO) -> ProjectTemplateResponse:
    """Convert a ProjectTemplateDTO to a ProjectTemplateResponse.

    Args:
        dto: ProjectTemplateDTO from the repository layer.

    Returns:
        ProjectTemplateResponse with entity details.
    """
    entities: List[TemplateEntitySchema] = [
        _entity_dto_to_schema(e) for e in dto.entities
    ]
    return ProjectTemplateResponse(
        id=dto.id,
        name=dto.name,
        description=dto.description,
        collection_id=dto.collection_id,
        default_project_config_id=dto.default_project_config_id,
        entities=entities,
        entity_count=dto.entity_count,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ProjectTemplateListResponse,
    summary="List all project templates",
    description="Retrieve paginated list of project templates with entity counts",
)
async def list_templates(
    repo: ProjectTemplateRepoDep,
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of templates to return"
    ),
    offset: int = Query(0, ge=0, description="Number of templates to skip"),
) -> ProjectTemplateListResponse:
    """List all project templates with pagination.

    Args:
        repo: Project template repository (injected).
        limit: Maximum number of templates to return (1-100)
        offset: Number of templates to skip

    Returns:
        ProjectTemplateListResponse with paginated templates

    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        templates = repo.list(limit=limit, offset=offset)
        total_count = repo.count()
        has_next = (offset + limit) < total_count

        items = [_template_dto_to_response(t) for t in templates]

        return ProjectTemplateListResponse(
            items=items,
            page_info=PageInfo(
                has_next_page=has_next,
                has_previous_page=offset > 0,
                total_count=total_count,
            ),
        )

    except Exception as e:
        logger.exception(f"Failed to list templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}",
        )


@router.get(
    "/{template_id}",
    response_model=ProjectTemplateResponse,
    summary="Get project template by ID",
    description="Retrieve full template details including entity list",
    responses={
        200: {"description": "Template found"},
        404: {"description": "Template not found"},
    },
)
async def get_template(
    template_id: str,
    repo: ProjectTemplateRepoDep,
) -> ProjectTemplateResponse:
    """Get project template by ID with full entity details.

    Args:
        template_id: Template identifier
        repo: Project template repository (injected).

    Returns:
        ProjectTemplateResponse with complete entity details

    Raises:
        HTTPException: 404 if template not found, 500 if database query fails
    """
    try:
        dto = repo.get(template_id)

        if dto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        return _template_dto_to_response(dto)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}",
        )


@router.post(
    "",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new project template",
    description="Create new template from list of entity IDs",
    responses={
        201: {"description": "Template created"},
        400: {"description": "Invalid entity IDs"},
        422: {"description": "Validation error"},
    },
)
async def create_template(
    request: ProjectTemplateCreateRequest,
    repo: ProjectTemplateRepoDep,
) -> ProjectTemplateResponse:
    """Create new project template from entity list.

    Args:
        request: Template creation request with entity IDs
        repo: Project template repository (injected).

    Returns:
        ProjectTemplateResponse with complete entity details

    Raises:
        HTTPException: 400 if entity IDs invalid, 422 if validation fails, 500 if creation fails
    """
    try:
        dto = repo.create(
            name=request.name,
            entity_ids=request.entity_ids,
            description=request.description,
            collection_id=request.collection_id,
            default_project_config_id=request.default_project_config_id,
        )
        logger.info(
            f"Created template '{dto.name}' with {len(request.entity_ids)} entities"
        )
        return _template_dto_to_response(dto)

    except ValueError as e:
        logger.warning(f"Invalid entity IDs in template creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}",
        )


@router.put(
    "/{template_id}",
    response_model=ProjectTemplateResponse,
    summary="Update project template",
    description="Update template name, description, or entity list",
    responses={
        200: {"description": "Template updated"},
        404: {"description": "Template not found"},
        400: {"description": "Invalid entity IDs"},
    },
)
async def update_template(
    template_id: str,
    request: ProjectTemplateUpdateRequest,
    repo: ProjectTemplateRepoDep,
) -> ProjectTemplateResponse:
    """Update existing project template.

    Args:
        template_id: Template identifier
        request: Template update request (partial update)
        repo: Project template repository (injected).

    Returns:
        ProjectTemplateResponse with updated entity details

    Raises:
        HTTPException: 404 if template not found, 400 if entity IDs invalid, 500 if update fails
    """
    try:
        updates: dict = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.entity_ids is not None:
            updates["entity_ids"] = request.entity_ids

        dto = repo.update(template_id, updates)
        logger.info(f"Updated template '{dto.name}'")
        return _template_dto_to_response(dto)

    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    except ValueError as e:
        logger.warning(f"Invalid entity IDs in template update: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to update template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}",
        )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project template",
    description="Delete template and all entity associations",
    responses={
        204: {"description": "Template deleted"},
        404: {"description": "Template not found"},
    },
)
async def delete_template(
    template_id: str,
    repo: ProjectTemplateRepoDep,
) -> None:
    """Delete project template and cascade to entity associations.

    Args:
        template_id: Template identifier
        repo: Project template repository (injected).

    Raises:
        HTTPException: 404 if template not found, 500 if deletion fails
    """
    try:
        repo.delete(template_id)
        logger.info(f"Deleted template '{template_id}'")

    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    except Exception as e:
        logger.exception(f"Failed to delete template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}",
        )


@router.post(
    "/{template_id}/deploy",
    response_model=DeployTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy project template to project path",
    description="Deploy template entities to target project with variable substitution (optimized for performance)",
    responses={
        201: {"description": "Template deployed"},
        404: {"description": "Template not found"},
        400: {"description": "Invalid project path or deployment failed"},
    },
)
async def deploy_template_endpoint(
    template_id: str,
    request: DeployTemplateRequest,
    repo: ProjectTemplateRepoDep,
    session: DbSessionDep,
) -> DeployTemplateResponse:
    """Deploy project template to target project path with performance optimizations.

    This endpoint deploys template entities to a specified project path with
    variable substitution. The deployment service uses:
    - Eager loading to eliminate N+1 database queries
    - Async file I/O with concurrent writes for fast deployment
    - Cached regex patterns for efficient variable substitution
    - Atomic deployment with rollback on failure

    Performance: Deploys 10 entities in < 5 seconds (P95).

    Args:
        template_id: Template identifier
        request: Deployment request with project path and variables
        repo: Project template repository (injected).

    Returns:
        DeployTemplateResponse with deployment results

    Raises:
        HTTPException: 404 if template not found, 400 if deployment fails
    """
    from skillmeat.core.services.template_service import deploy_template_async

    try:
        # Verify template exists via repository before the expensive deployment.
        dto = repo.get(template_id)
        if dto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # Execute optimized async deployment via the service directly.
        # The injected session (DbSessionDep) is used for the async deployment
        # coroutine, which manages its own transaction lifecycle.
        result = await deploy_template_async(
            session=session,
            template_id=template_id,
            project_path=request.project_path,
            variables=request.variables.model_dump(),
            selected_entity_ids=request.selected_entity_ids,
            overwrite=request.overwrite,
            deployment_profile_id=request.deployment_profile_id,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )

        # Convert DeploymentResult to DeployTemplateResponse
        return DeployTemplateResponse(
            template_id=template_id,
            project_path=result.project_path,
            deployed_files=result.deployed_files,
            skipped_files=result.skipped_files,
            message=result.message,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error deploying template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        logger.warning(f"Permission error deploying template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to deploy template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy template: {str(e)}",
        )
