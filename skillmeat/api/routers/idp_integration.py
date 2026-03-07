"""IDP (Internal Developer Portal) integration API router.

Provides endpoints for Backstage/IDP scaffold generation and deployment
registration operations.

API Endpoints:
    POST /integrations/idp/scaffold             - Render template files in-memory
    POST /integrations/idp/register-deployment  - Register/update an IDP deployment set
"""

import json
import logging
from base64 import b64encode

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import (
    APIKeyDep,
    DbSessionDep,
    DeploymentRepoDep,
    get_auth_context,
    require_auth,
)
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.api.schemas.idp_integration import (
    IDPRegisterDeploymentRequest,
    IDPRegisterDeploymentResponse,
    IDPScaffoldRequest,
    IDPScaffoldResponse,
    RenderedFile,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/integrations/idp",
    tags=["integrations-idp"],
)


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
    auth_context: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
) -> IDPScaffoldResponse:
    """Render scaffold files for a given artifact target.

    Delegates to :func:`skillmeat.core.services.template_service.render_in_memory`
    to produce rendered file content without any disk writes.

    Args:
        request: Scaffold request containing target_id and optional variables
        session: Database session (required by render_in_memory service)
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
    deployment_repo: DeploymentRepoDep,
    _auth: APIKeyDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
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
        deployment_repo: Deployment repository (injected via DI)
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
        deployment_set_id, created = deployment_repo.upsert_idp_deployment_set(
            remote_url=request.repo_url,
            name=request.target_id,
            provisioned_by="idp",
            description=metadata_json,
        )
    except Exception as exc:
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

    logger.info(
        "IDP register-deployment: %s set id=%s",
        "created new" if created else "updated existing",
        deployment_set_id,
    )

    return IDPRegisterDeploymentResponse(
        deployment_set_id=deployment_set_id,
        created=created,
    )
