"""Deployment management API endpoints.

Provides REST API for deploying artifacts to projects and managing deployments.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    CollectionManagerDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.deployments import (
    DeploymentInfo,
    DeploymentListResponse,
    DeploymentResponse,
    DeployRequest,
    UndeployRequest,
    UndeployResponse,
)
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.deployment import DeploymentManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/deploy",
    tags=["deployments"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


def get_deployment_manager(
    collection_mgr: CollectionManagerDep,
) -> DeploymentManager:
    """Get DeploymentManager dependency.

    Args:
        collection_mgr: Collection manager dependency

    Returns:
        DeploymentManager instance
    """
    return DeploymentManager(collection_mgr=collection_mgr)


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Deploy artifact to project",
    description="Deploy an artifact from collection to a project's .claude directory",
    responses={
        200: {"description": "Artifact deployed successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or artifact not found",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {
            "model": ErrorResponse,
            "description": "Artifact or collection not found",
        },
        500: {"model": ErrorResponse, "description": "Deployment failed"},
    },
)
async def deploy_artifact(
    request: DeployRequest,
    deployment_mgr: DeploymentManager = Depends(get_deployment_manager),
    token: TokenDep = None,
) -> DeploymentResponse:
    """Deploy an artifact to a project.

    Copies an artifact from the collection to the project's .claude directory,
    maintaining proper structure (skills/, commands/, agents/).

    Args:
        request: Deployment request with artifact and project details
        deployment_mgr: Deployment manager dependency
        token: Authentication token

    Returns:
        DeploymentResponse with deployment details

    Raises:
        HTTPException: On validation or deployment failure
    """
    try:
        logger.info(
            f"Deploying artifact: {request.artifact_id} "
            f"(project={request.project_path or 'CWD'})"
        )

        # Parse artifact type
        try:
            artifact_type = ArtifactType(request.artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}",
            )

        # Resolve project path
        project_path = (
            Path(request.project_path) if request.project_path else Path.cwd()
        )
        project_path = project_path.resolve()

        # Check if project has .claude directory
        claude_dir = project_path / ".claude"
        if not claude_dir.exists():
            logger.info(f"Creating .claude directory at {project_path}")
            claude_dir.mkdir(parents=True, exist_ok=True)

        # Deploy artifact (non-interactive mode for API)
        # We'll need to handle overwrite without prompting
        try:
            # For API, we need to check if artifact exists first
            from skillmeat.storage.deployment import DeploymentTracker

            existing_deployment = DeploymentTracker.get_deployment(
                project_path, request.artifact_name, request.artifact_type
            )

            if existing_deployment:
                if not request.overwrite:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Artifact '{request.artifact_name}' already deployed. "
                        "Set overwrite=true to replace.",
                    )
                else:
                    # Remove existing deployment first (to avoid interactive prompt)
                    logger.info(f"Removing existing deployment before overwrite")
                    deployment_mgr.undeploy(
                        artifact_name=request.artifact_name,
                        artifact_type=artifact_type,
                        project_path=project_path,
                    )

            # Perform deployment
            deployments = deployment_mgr.deploy_artifacts(
                artifact_names=[request.artifact_name],
                collection_name=request.collection_name,
                project_path=project_path,
                artifact_type=artifact_type,
            )

            if not deployments:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{request.artifact_name}' not found in collection",
                )

            deployment = deployments[0]

            # Build response
            response = DeploymentResponse(
                success=True,
                message=f"Artifact '{request.artifact_name}' deployed successfully",
                deployment_id=f"{deployment.artifact_type}:{deployment.artifact_name}",
                stream_url=None,  # SSE streaming not yet implemented
                artifact_name=deployment.artifact_name,
                artifact_type=deployment.artifact_type,
                project_path=str(project_path),
                deployed_path=str(deployment.artifact_path),
                deployed_at=deployment.deployed_at,
            )

            logger.info(
                f"Deployment successful: {deployment.artifact_name} "
                f"({deployment.artifact_type}) to {project_path}"
            )
            return response

        except ValueError as e:
            # Artifact not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}",
        )


@router.post(
    "/undeploy",
    response_model=UndeployResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove deployed artifact",
    description="Remove an artifact from a project's .claude directory",
    responses={
        200: {"description": "Artifact removed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not deployed"},
        500: {"model": ErrorResponse, "description": "Removal failed"},
    },
)
async def undeploy_artifact(
    request: UndeployRequest,
    deployment_mgr: DeploymentManager = Depends(get_deployment_manager),
    token: TokenDep = None,
) -> UndeployResponse:
    """Remove a deployed artifact from a project.

    Removes the artifact from the project's .claude directory and updates
    the deployment tracking metadata.

    Args:
        request: Undeploy request with artifact details
        deployment_mgr: Deployment manager dependency
        token: Authentication token

    Returns:
        UndeployResponse with removal confirmation

    Raises:
        HTTPException: On validation or removal failure
    """
    try:
        logger.info(
            f"Undeploying artifact: {request.artifact_name} "
            f"({request.artifact_type}, project={request.project_path or 'CWD'})"
        )

        # Parse artifact type
        try:
            artifact_type = ArtifactType(request.artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}",
            )

        # Resolve project path
        project_path = (
            Path(request.project_path) if request.project_path else Path.cwd()
        )
        project_path = project_path.resolve()

        # Undeploy artifact
        try:
            deployment_mgr.undeploy(
                artifact_name=request.artifact_name,
                artifact_type=artifact_type,
                project_path=project_path,
            )

            response = UndeployResponse(
                success=True,
                message=f"Artifact '{request.artifact_name}' removed successfully",
                artifact_name=request.artifact_name,
                artifact_type=request.artifact_type,
                project_path=str(project_path),
            )

            logger.info(
                f"Undeploy successful: {request.artifact_name} "
                f"({request.artifact_type}) from {project_path}"
            )
            return response

        except ValueError as e:
            # Artifact not deployed
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Undeploy failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Undeploy failed: {str(e)}",
        )


@router.get(
    "",
    response_model=DeploymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List deployments",
    description="List all deployed artifacts in a project",
    responses={
        200: {"description": "Deployments retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Failed to retrieve deployments"},
    },
)
async def list_deployments(
    deployment_mgr: DeploymentManager = Depends(get_deployment_manager),
    token: TokenDep = None,
    project_path: Optional[str] = Query(
        default=None,
        description="Path to project directory (uses CWD if not specified)",
    ),
) -> DeploymentListResponse:
    """List all deployed artifacts in a project.

    Retrieves deployment metadata for all artifacts in the project's
    .claude directory, including sync status.

    Args:
        deployment_mgr: Deployment manager dependency
        token: Authentication token
        project_path: Optional project path

    Returns:
        DeploymentListResponse with list of deployments

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Resolve project path
        resolved_path = Path(project_path) if project_path else Path.cwd()
        resolved_path = resolved_path.resolve()

        logger.info(f"Listing deployments for project: {resolved_path}")

        # Get deployments
        deployments = deployment_mgr.list_deployments(project_path=resolved_path)

        # Get sync status for each deployment
        status_map = deployment_mgr.check_deployment_status(project_path=resolved_path)

        # Convert to response format
        deployment_infos = []
        for deployment in deployments:
            key = f"{deployment.artifact_name}::{deployment.artifact_type}"
            sync_status = status_map.get(key, "unknown")

            deployment_infos.append(
                DeploymentInfo(
                    artifact_name=deployment.artifact_name,
                    artifact_type=deployment.artifact_type,
                    from_collection=deployment.from_collection,
                    deployed_at=deployment.deployed_at,
                    artifact_path=str(deployment.artifact_path),
                    collection_sha=deployment.collection_sha,
                    local_modifications=deployment.local_modifications,
                    sync_status=sync_status,
                )
            )

        response = DeploymentListResponse(
            project_path=str(resolved_path),
            deployments=deployment_infos,
            total=len(deployment_infos),
        )

        logger.info(f"Retrieved {len(deployment_infos)} deployments")
        return response

    except Exception as e:
        logger.error(f"Failed to list deployments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deployments: {str(e)}",
        )
