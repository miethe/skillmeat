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
import uuid
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
from skillmeat.cache.models import (
    Artifact,
    ProjectTemplate,
    TemplateEntity,
    get_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/project-templates",
    tags=["project-templates"],
)


# =============================================================================
# Database Session Dependency
# =============================================================================


def get_db_session():
    """Get database session with proper cleanup.

    Yields:
        SQLAlchemy session instance

    Note:
        Session is automatically closed after request completes
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]


# =============================================================================
# Helper Functions
# =============================================================================


def _build_template_response(
    template: ProjectTemplate, session: Session
) -> ProjectTemplateResponse:
    """Build ProjectTemplateResponse from database model.

    Args:
        template: ProjectTemplate database model
        session: Database session for entity queries

    Returns:
        ProjectTemplateResponse with complete entity details
    """
    # Query template entities with artifact details, ordered by deploy_order
    template_entities = (
        session.query(TemplateEntity)
        .filter(TemplateEntity.template_id == template.id)
        .order_by(TemplateEntity.deploy_order)
        .all()
    )

    # Build entity schema list
    entities = []
    for te in template_entities:
        artifact = session.query(Artifact).filter(Artifact.id == te.artifact_id).first()
        if artifact:
            entities.append(
                TemplateEntitySchema(
                    artifact_id=artifact.id,
                    name=artifact.name,
                    type=artifact.artifact_type,
                    deploy_order=te.deploy_order,
                    required=te.required,
                    path_pattern=artifact.path_pattern,
                )
            )

    return ProjectTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        collection_id=template.collection_id,
        default_project_config_id=template.default_project_config_id,
        entities=entities,
        entity_count=len(entities),
        created_at=template.created_at,
        updated_at=template.updated_at,
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
    session: DbSessionDep,
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of templates to return"
    ),
    offset: int = Query(0, ge=0, description="Number of templates to skip"),
) -> ProjectTemplateListResponse:
    """List all project templates with pagination.

    Args:
        session: Database session
        limit: Maximum number of templates to return (1-100)
        offset: Number of templates to skip

    Returns:
        ProjectTemplateListResponse with paginated templates

    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        # Query templates with pagination
        templates = (
            session.query(ProjectTemplate)
            .order_by(ProjectTemplate.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Build response list
        items = []
        for template in templates:
            # Get entity count for each template
            entity_count = (
                session.query(TemplateEntity)
                .filter(TemplateEntity.template_id == template.id)
                .count()
            )

            items.append(
                ProjectTemplateResponse(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    collection_id=template.collection_id,
                    default_project_config_id=template.default_project_config_id,
                    entities=[],  # Not loaded in list view for performance
                    entity_count=entity_count,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                )
            )

        # Build pagination info
        total_count = session.query(ProjectTemplate).count()
        has_next = (offset + limit) < total_count

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
    session: DbSessionDep,
) -> ProjectTemplateResponse:
    """Get project template by ID with full entity details.

    Args:
        template_id: Template identifier
        session: Database session

    Returns:
        ProjectTemplateResponse with complete entity details

    Raises:
        HTTPException: 404 if template not found, 500 if database query fails
    """
    try:
        # Query template
        template = (
            session.query(ProjectTemplate)
            .filter(ProjectTemplate.id == template_id)
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        return _build_template_response(template, session)

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
    session: DbSessionDep,
) -> ProjectTemplateResponse:
    """Create new project template from entity list.

    Args:
        request: Template creation request with entity IDs
        session: Database session

    Returns:
        ProjectTemplateResponse with complete entity details

    Raises:
        HTTPException: 400 if entity IDs invalid, 422 if validation fails, 500 if creation fails
    """
    try:
        # Validate all entity IDs exist
        artifacts = (
            session.query(Artifact).filter(Artifact.id.in_(request.entity_ids)).all()
        )
        found_ids = {a.id for a in artifacts}
        missing_ids = set(request.entity_ids) - found_ids

        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity IDs: {', '.join(sorted(missing_ids))}",
            )

        # Validate default_project_config_id if provided
        if request.default_project_config_id:
            config = (
                session.query(Artifact)
                .filter(Artifact.id == request.default_project_config_id)
                .first()
            )
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid default_project_config_id: {request.default_project_config_id}",
                )

        # Create template
        template = ProjectTemplate(
            id=uuid.uuid4().hex,
            name=request.name,
            description=request.description,
            collection_id=request.collection_id,
            default_project_config_id=request.default_project_config_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(template)

        # Create template entity associations
        for idx, entity_id in enumerate(request.entity_ids):
            template_entity = TemplateEntity(
                template_id=template.id,
                artifact_id=entity_id,
                deploy_order=idx,
                required=True,  # Default all to required
            )
            session.add(template_entity)

        session.commit()

        logger.info(
            f"Created template '{template.name}' with {len(request.entity_ids)} entities"
        )
        return _build_template_response(template, session)

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
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
    session: DbSessionDep,
) -> ProjectTemplateResponse:
    """Update existing project template.

    Args:
        template_id: Template identifier
        request: Template update request (partial update)
        session: Database session

    Returns:
        ProjectTemplateResponse with updated entity details

    Raises:
        HTTPException: 404 if template not found, 400 if entity IDs invalid, 500 if update fails
    """
    try:
        # Query template
        template = (
            session.query(ProjectTemplate)
            .filter(ProjectTemplate.id == template_id)
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # Update basic fields if provided
        if request.name is not None:
            template.name = request.name
        if request.description is not None:
            template.description = request.description

        # Update entity associations if provided
        if request.entity_ids is not None:
            # Validate all entity IDs exist
            artifacts = (
                session.query(Artifact)
                .filter(Artifact.id.in_(request.entity_ids))
                .all()
            )
            found_ids = {a.id for a in artifacts}
            missing_ids = set(request.entity_ids) - found_ids

            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid entity IDs: {', '.join(sorted(missing_ids))}",
                )

            # Delete existing associations
            session.query(TemplateEntity).filter(
                TemplateEntity.template_id == template_id
            ).delete()

            # Create new associations
            for idx, entity_id in enumerate(request.entity_ids):
                template_entity = TemplateEntity(
                    template_id=template_id,
                    artifact_id=entity_id,
                    deploy_order=idx,
                    required=True,
                )
                session.add(template_entity)

        template.updated_at = datetime.utcnow()
        session.commit()

        logger.info(f"Updated template '{template.name}'")
        return _build_template_response(template, session)

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
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
    session: DbSessionDep,
) -> None:
    """Delete project template and cascade to entity associations.

    Args:
        template_id: Template identifier
        session: Database session

    Raises:
        HTTPException: 404 if template not found, 500 if deletion fails
    """
    try:
        # Query template
        template = (
            session.query(ProjectTemplate)
            .filter(ProjectTemplate.id == template_id)
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # Delete template (cascade will handle template_entities)
        session.delete(template)
        session.commit()

        logger.info(f"Deleted template '{template.name}'")

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
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
    description="Deploy template entities to target project with variable substitution (Phase 5)",
    responses={
        201: {"description": "Template deployed"},
        404: {"description": "Template not found"},
        400: {"description": "Invalid project path or deployment failed"},
        501: {"description": "Deployment service not yet implemented (Phase 5)"},
    },
)
async def deploy_template(
    template_id: str,
    request: DeployTemplateRequest,
    session: DbSessionDep,
) -> DeployTemplateResponse:
    """Deploy project template to target project path.

    This endpoint deploys template entities to a specified project path with
    variable substitution. The deployment service handles file creation,
    variable substitution, and conflict resolution.

    Args:
        template_id: Template identifier
        request: Deployment request with project path and variables
        session: Database session

    Returns:
        DeployTemplateResponse with deployment results

    Raises:
        HTTPException: 404 if template not found, 400 if deployment fails,
                      501 if deployment service not yet implemented (Phase 5)
    """
    # TODO: Phase 5 - Implement deployment service
    # This endpoint is stubbed for Phase 4 API completion
    # Implementation will use template_service.deploy_template()

    try:
        # Verify template exists
        template = (
            session.query(ProjectTemplate)
            .filter(ProjectTemplate.id == template_id)
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # TODO: Import and call template_service.deploy_template()
        # from skillmeat.core.template_service import deploy_template
        # result = deploy_template(
        #     session=session,
        #     template_id=template_id,
        #     project_path=request.project_path,
        #     variables=request.variables.model_dump(),
        #     selected_entity_ids=request.selected_entity_ids,
        #     overwrite=request.overwrite,
        # )
        # return result

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Template deployment service not yet implemented (Phase 5)",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to deploy template '{template_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy template: {str(e)}",
        )
