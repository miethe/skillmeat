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
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.projects import (
    DeployedArtifact,
    ProjectDetail,
    ProjectListResponse,
    ProjectSummary,
)
from skillmeat.storage.deployment import DeploymentTracker

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
