"""IDP (Internal Developer Portal) integration API router.

Provides endpoints for Backstage/IDP scaffold generation and deployment
registration operations.

API Endpoints:
    POST /integrations/idp/scaffold             - Render template files in-memory
    POST /integrations/idp/register-deployment  - Register/update an IDP deployment set
"""

import json
import logging
import uuid
from base64 import b64encode
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from skillmeat.api.dependencies import APIKeyDep, SettingsDep
from skillmeat.api.schemas.idp_integration import (
    IDPRegisterDeploymentRequest,
    IDPRegisterDeploymentResponse,
    IDPScaffoldRequest,
    IDPScaffoldResponse,
    RenderedFile,
)
from skillmeat.cache.models import DeploymentSet, get_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/integrations/idp",
    tags=["integrations-idp"],
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
# API Endpoints
# =============================================================================


@router.post(
    "/scaffold",
    response_model=IDPScaffoldResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate scaffold files for an IDP target",
    description=(
        "Renders a composite or skill artifact in-memory and returns the generated "
        "files as base64-encoded content.  Intended for use by Backstage software "
        "template actions and other IDP scaffolders."
    ),
    responses={
        200: {"description": "Scaffold files rendered successfully"},
        422: {"description": "Invalid target_id or variable validation error"},
        404: {"description": "Target artifact not found"},
        500: {"description": "Internal rendering error"},
    },
)
async def scaffold(
    request: IDPScaffoldRequest,
    session: DbSessionDep,
    _auth: APIKeyDep,
) -> IDPScaffoldResponse:
    """Render scaffold files for a given artifact target.

    Delegates to :func:`skillmeat.core.services.template_service.render_in_memory`
    to produce rendered file content without any disk writes.

    Args:
        request: Scaffold request containing target_id and optional variables
        session: Database session
        _auth: API key authentication (enforced when auth is enabled)

    Returns:
        IDPScaffoldResponse with list of base64-encoded rendered files

    Raises:
        HTTPException: 422 if target_id or variables are invalid,
                       404 if the target artifact does not exist,
                       500 for unexpected rendering errors
    """
    from skillmeat.core.services.template_service import render_in_memory

    logger.info(
        "IDP scaffold requested: target_id=%s variables=%s",
        request.target_id,
        list(request.variables.keys()),
    )

    try:
        rendered = render_in_memory(
            session=session,
            target_id=request.target_id,
            variables=request.variables,
        )
    except ValueError as exc:
        logger.warning(
            "IDP scaffold validation error for target_id=%s: %s",
            request.target_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": str(exc)},
        )
    except LookupError as exc:
        # render_in_memory raises LookupError / KeyError when the target is not found
        logger.warning(
            "IDP scaffold target not found: target_id=%s: %s",
            request.target_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target artifact '{request.target_id}' not found",
        )
    except Exception as exc:
        logger.exception(
            "IDP scaffold unexpected error for target_id=%s: %s",
            request.target_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render scaffold files",
        )

    files = [
        RenderedFile(
            path=rf.path,
            content_base64=b64encode(rf.content).decode("ascii"),
        )
        for rf in rendered
    ]

    logger.info(
        "IDP scaffold completed: target_id=%s files=%d",
        request.target_id,
        len(files),
    )

    return IDPScaffoldResponse(files=files)


@router.post(
    "/register-deployment",
    response_model=IDPRegisterDeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or update an IDP deployment",
    description=(
        "Records that a repository has deployed a given artifact target.  "
        "The operation is idempotent: re-submitting the same repo_url + target_id "
        "pair updates the existing DeploymentSet record instead of creating a duplicate."
    ),
    responses={
        200: {"description": "Deployment registered or updated"},
        422: {"description": "Invalid request payload"},
        500: {"description": "Internal error persisting the deployment record"},
    },
)
async def register_deployment(
    request: IDPRegisterDeploymentRequest,
    session: DbSessionDep,
    _auth: APIKeyDep,
) -> IDPRegisterDeploymentResponse:
    """Register or idempotently update an IDP deployment set record.

    Looks up an existing ``DeploymentSet`` by ``(remote_url, name)`` — where
    *name* is derived from ``target_id`` — to enforce the idempotency constraint.
    If a match is found the record is updated; otherwise a new record is created.

    The request ``metadata`` dict is serialised as JSON and stored in the
    ``description`` field of the ``DeploymentSet`` (no dedicated metadata column
    exists on the model at this schema version).

    Args:
        request: Register-deployment request containing repo_url, target_id,
                 and optional metadata
        session: Database session
        _auth: API key authentication (enforced when auth is enabled)

    Returns:
        IDPRegisterDeploymentResponse with deployment_set_id and created flag

    Raises:
        HTTPException: 500 if the database operation fails
    """
    logger.info(
        "IDP register-deployment: repo_url=%s target_id=%s",
        request.repo_url,
        request.target_id,
    )

    # Serialise the caller-supplied metadata for storage.
    metadata_json: str | None = (
        json.dumps(request.metadata) if request.metadata else None
    )

    try:
        # Idempotency check: match on (remote_url, name) where name == target_id.
        existing: DeploymentSet | None = (
            session.query(DeploymentSet)
            .filter(
                DeploymentSet.remote_url == request.repo_url,
                DeploymentSet.name == request.target_id,
            )
            .first()
        )

        if existing is not None:
            # Update existing record.
            existing.provisioned_by = "idp"
            existing.updated_at = datetime.utcnow()
            if metadata_json is not None:
                existing.description = metadata_json
            session.commit()

            logger.info(
                "IDP register-deployment: updated existing set id=%s", existing.id
            )
            return IDPRegisterDeploymentResponse(
                deployment_set_id=existing.id,
                created=False,
            )

        # Create new DeploymentSet record.
        new_set = DeploymentSet(
            id=uuid.uuid4().hex,
            name=request.target_id,
            remote_url=request.repo_url,
            provisioned_by="idp",
            owner_id="idp",
            description=metadata_json,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(new_set)
        session.commit()

        logger.info(
            "IDP register-deployment: created new set id=%s", new_set.id
        )
        return IDPRegisterDeploymentResponse(
            deployment_set_id=new_set.id,
            created=True,
        )

    except Exception as exc:
        session.rollback()
        logger.exception(
            "IDP register-deployment failed for repo_url=%s target_id=%s: %s",
            request.repo_url,
            request.target_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register deployment",
        )
