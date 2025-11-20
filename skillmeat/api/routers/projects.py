"""Project management API endpoints.

Provides REST API for browsing and managing projects with deployed artifacts.
"""

import base64
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    DeploymentModificationStatus,
    ModificationCheckResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.projects import (
    DeployedArtifact,
    ModifiedArtifactsResponse,
    ProjectDetail,
    ProjectListResponse,
    ProjectSummary,
)
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


def encode_project_id(path: str) -> str:
    """Encode a project path to base64 for use as ID.

    Args:
        path: Absolute project path

    Returns:
        Base64 encoded project ID
    """
    return base64.b64encode(path.encode()).decode()


def decode_project_id(project_id: str) -> str:
    """Decode a base64 project ID to path.

    Args:
        project_id: Base64 encoded project ID

    Returns:
        Decoded project path

    Raises:
        HTTPException: If project ID is invalid
    """
    try:
        return base64.b64decode(project_id.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project ID format: {str(e)}",
        )


def discover_projects(search_paths: Optional[List[Path]] = None) -> List[Path]:
    """Discover projects with .claude/.skillmeat-deployed.toml files.

    This function scans configured search paths for projects that have
    deployment tracking files, indicating they contain deployed artifacts.

    Args:
        search_paths: Optional list of paths to search (defaults to common locations)

    Returns:
        List of project paths with deployments
    """
    if search_paths is None:
        # Default search locations
        # TODO: Make this configurable via settings
        home = Path.home()
        search_paths = [
            home / "projects",
            home / "dev",
            home / "workspace",
            home / "src",
            Path.cwd(),  # Current working directory
        ]

    discovered = []

    for search_path in search_paths:
        if not search_path.exists() or not search_path.is_dir():
            continue

        # Search for .skillmeat-deployed.toml files up to 3 levels deep
        # This prevents excessive filesystem scanning
        try:
            for deployment_file in search_path.rglob(".claude/.skillmeat-deployed.toml"):
                # Get project root (parent of .claude)
                project_path = deployment_file.parent.parent
                if project_path not in discovered:
                    discovered.append(project_path)
        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning {search_path}: {e}")
            continue

    return discovered


def build_project_summary(project_path: Path) -> ProjectSummary:
    """Build a ProjectSummary from a project path.

    Args:
        project_path: Absolute path to project directory

    Returns:
        ProjectSummary object
    """
    deployments = DeploymentTracker.read_deployments(project_path)

    # Find most recent deployment
    last_deployment = None
    if deployments:
        last_deployment = max(d.deployed_at for d in deployments)

    return ProjectSummary(
        id=encode_project_id(str(project_path)),
        path=str(project_path),
        name=project_path.name,
        deployment_count=len(deployments),
        last_deployment=last_deployment,
    )


def build_project_detail(project_path: Path) -> ProjectDetail:
    """Build a ProjectDetail from a project path.

    Args:
        project_path: Absolute path to project directory

    Returns:
        ProjectDetail object
    """
    deployments = DeploymentTracker.read_deployments(project_path)

    # Convert to API schema
    deployed_artifacts = [
        DeployedArtifact(
            artifact_name=d.artifact_name,
            artifact_type=d.artifact_type,
            from_collection=d.from_collection,
            deployed_at=d.deployed_at,
            artifact_path=str(d.artifact_path),
            version=None,  # Version not currently stored in deployment
            collection_sha=d.collection_sha,
            local_modifications=d.local_modifications,
        )
        for d in deployments
    ]

    # Calculate statistics
    by_type = defaultdict(int)
    by_collection = defaultdict(int)
    modified_count = 0

    for d in deployments:
        by_type[d.artifact_type] += 1
        by_collection[d.from_collection] += 1
        if d.local_modifications:
            modified_count += 1

    stats = {
        "by_type": dict(by_type),
        "by_collection": dict(by_collection),
        "modified_count": modified_count,
    }

    # Find most recent deployment
    last_deployment = None
    if deployments:
        last_deployment = max(d.deployed_at for d in deployments)

    return ProjectDetail(
        id=encode_project_id(str(project_path)),
        path=str(project_path),
        name=project_path.name,
        deployment_count=len(deployments),
        last_deployment=last_deployment,
        deployments=deployed_artifacts,
        stats=stats,
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Discover and list all projects with deployed artifacts",
    responses={
        200: {"description": "Successfully retrieved projects"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_projects(
    token: TokenDep,
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
) -> ProjectListResponse:
    """List all projects with deployed artifacts.

    This endpoint discovers projects by scanning configured paths for
    .claude/.skillmeat-deployed.toml files and returns summary information
    about each project.

    Args:
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of projects

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Listing projects (limit={limit}, after={after})")

        # Discover all projects
        project_paths = discover_projects()
        logger.info(f"Discovered {len(project_paths)} projects")

        # Build project summaries
        all_projects = []
        for project_path in project_paths:
            try:
                summary = build_project_summary(project_path)
                all_projects.append(summary)
            except Exception as e:
                logger.error(f"Error processing project {project_path}: {e}")
                continue

        # Sort by last deployment (most recent first)
        all_projects.sort(
            key=lambda p: p.last_deployment or datetime.min,
            reverse=True,
        )

        # Apply pagination
        start_idx = 0
        if after:
            # Decode cursor to get project path
            cursor_path = decode_project_id(after)
            try:
                cursor_idx = next(
                    i for i, p in enumerate(all_projects) if p.path == cursor_path
                )
                start_idx = cursor_idx + 1
            except StopIteration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: project not found",
                )

        end_idx = start_idx + limit
        page_projects = all_projects[start_idx:end_idx]

        # Build pagination info
        has_next = end_idx < len(all_projects)
        has_previous = start_idx > 0

        start_cursor = page_projects[0].id if page_projects else None
        end_cursor = page_projects[-1].id if page_projects else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_projects),
        )

        logger.info(f"Retrieved {len(page_projects)} projects")
        return ProjectListResponse(items=page_projects, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Get project details",
    description="Retrieve detailed information about a specific project including all deployments",
    responses={
        200: {"description": "Successfully retrieved project"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_project(
    project_id: str,
    token: TokenDep,
) -> ProjectDetail:
    """Get details for a specific project.

    Returns complete information about a project including all deployed
    artifacts, versions, and statistics.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        Project details with full deployment list

    Raises:
        HTTPException: If project not found or on error
    """
    try:
        logger.info(f"Getting project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Check if project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Build project detail
        project_detail = build_project_detail(project_path)

        logger.info(
            f"Retrieved project '{project_detail.name}' with {project_detail.deployment_count} deployments"
        )
        return project_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project '{project_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}",
        )


@router.post(
    "/{project_id}/check-modifications",
    response_model=ModificationCheckResponse,
    summary="Check for artifact modifications",
    description="Scan all deployments in a project and detect local modifications by comparing content hashes",
    responses={
        200: {"description": "Successfully checked for modifications"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def check_project_modifications(
    project_id: str,
    token: TokenDep,
) -> ModificationCheckResponse:
    """Check for modifications in all deployed artifacts.

    Compares the current content hash of each deployed artifact with
    the hash recorded at deployment time to detect local modifications.

    This operation updates the deployment metadata with modification
    timestamps when changes are first detected.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        Modification check results with status for each deployment

    Raises:
        HTTPException: If project not found or on error

    Example:
        POST /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/check-modifications

        Returns:
        {
            "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
            "checked_at": "2025-11-20T16:00:00Z",
            "modifications_detected": 2,
            "deployments": [
                {
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "deployed_sha": "abc123...",
                    "current_sha": "def456...",
                    "is_modified": true,
                    "modification_detected_at": "2025-11-20T15:45:00Z"
                }
            ]
        }
    """
    try:
        logger.info(f"Checking modifications for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Load current deployments
        deployments = DeploymentTracker.read_deployments(project_path)

        # Check each deployment for modifications
        modification_statuses: List[DeploymentModificationStatus] = []
        modifications_count = 0
        checked_at = datetime.utcnow()

        for deployment in deployments:
            # Compute current content hash
            artifact_full_path = project_path / ".claude" / deployment.artifact_path

            if not artifact_full_path.exists():
                # Artifact has been deleted
                logger.warning(
                    f"Deployed artifact not found: {deployment.artifact_name} at {artifact_full_path}"
                )
                # Skip deleted artifacts
                continue

            try:
                current_sha = compute_content_hash(artifact_full_path)
            except Exception as e:
                logger.error(
                    f"Failed to compute hash for {deployment.artifact_name}: {e}"
                )
                # Use a placeholder to indicate error
                current_sha = "error"

            # Compare with deployed SHA
            is_modified = current_sha != deployment.collection_sha

            # Update deployment metadata if modification detected
            modification_detected_at = deployment.modification_detected_at
            if is_modified and not deployment.local_modifications:
                # First time detecting this modification
                modification_detected_at = checked_at
                deployment.local_modifications = True
                deployment.modification_detected_at = modification_detected_at
            elif not is_modified and deployment.local_modifications:
                # Modification was reverted
                deployment.local_modifications = False
                deployment.modification_detected_at = None
                modification_detected_at = None

            # Track last check time
            deployment.last_modified_check = checked_at

            if is_modified:
                modifications_count += 1

            modification_statuses.append(
                DeploymentModificationStatus(
                    artifact_name=deployment.artifact_name,
                    artifact_type=deployment.artifact_type,
                    deployed_sha=deployment.collection_sha,
                    current_sha=current_sha,
                    is_modified=is_modified,
                    modification_detected_at=modification_detected_at,
                )
            )

        # Save updated deployment metadata
        DeploymentTracker.write_deployments(project_path, deployments)

        logger.info(
            f"Modification check complete: {modifications_count} of {len(modification_statuses)} artifacts modified"
        )

        return ModificationCheckResponse(
            project_id=project_id,
            checked_at=checked_at,
            modifications_detected=modifications_count,
            deployments=modification_statuses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error checking modifications for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check modifications: {str(e)}",
        )


@router.get(
    "/{project_id}/modified-artifacts",
    response_model=ModifiedArtifactsResponse,
    summary="Get modified artifacts",
    description="List all artifacts in a project that have been modified since deployment",
    responses={
        200: {"description": "Successfully retrieved modified artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_modified_artifacts(
    project_id: str,
    token: TokenDep,
) -> ModifiedArtifactsResponse:
    """Get list of all modified artifacts in a project.

    This is a convenience endpoint that filters the results from
    check-modifications to return only modified artifacts.

    Note: This performs a live check of all deployments. Results
    are not cached between calls.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        List of modified artifacts with their current and deployed hashes

    Raises:
        HTTPException: If project not found or on error

    Example:
        GET /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/modified-artifacts

        Returns:
        {
            "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
            "modified_artifacts": [
                {
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "deployed_sha": "abc123...",
                    "current_sha": "def456...",
                    "modification_detected_at": "2025-11-20T15:45:00Z"
                }
            ],
            "total_count": 2,
            "last_checked": "2025-11-20T16:00:00Z"
        }
    """
    try:
        logger.info(f"Getting modified artifacts for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Load current deployments
        deployments = DeploymentTracker.read_deployments(project_path)

        # Find modified artifacts
        from skillmeat.api.schemas.projects import ModifiedArtifactInfo

        modified_artifacts: List[ModifiedArtifactInfo] = []
        checked_at = datetime.utcnow()

        for deployment in deployments:
            # Compute current content hash
            artifact_full_path = project_path / ".claude" / deployment.artifact_path

            if not artifact_full_path.exists():
                # Skip deleted artifacts
                continue

            try:
                current_sha = compute_content_hash(artifact_full_path)
            except Exception as e:
                logger.error(
                    f"Failed to compute hash for {deployment.artifact_name}: {e}"
                )
                continue

            # Check if modified
            if current_sha != deployment.collection_sha:
                modified_artifacts.append(
                    ModifiedArtifactInfo(
                        artifact_name=deployment.artifact_name,
                        artifact_type=deployment.artifact_type,
                        deployed_sha=deployment.collection_sha,
                        current_sha=current_sha,
                        modification_detected_at=deployment.modification_detected_at,
                    )
                )

        logger.info(
            f"Found {len(modified_artifacts)} modified artifacts in project '{project_path.name}'"
        )

        return ModifiedArtifactsResponse(
            project_id=project_id,
            modified_artifacts=modified_artifacts,
            total_count=len(modified_artifacts),
            last_checked=checked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting modified artifacts for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get modified artifacts: {str(e)}",
        )
