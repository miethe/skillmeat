"""Context sync API endpoints.

API endpoints for bi-directional synchronization of context entities between
user collections and deployed projects.

Endpoints:
    POST /context-sync/pull - Pull changes from project to collection
    POST /context-sync/push - Push collection changes to project
    GET /context-sync/status - Get sync status for project
    POST /context-sync/resolve - Resolve a sync conflict
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import ContextSyncServiceDep, verify_api_key
from skillmeat.api.schemas.context_sync import (
    SyncConflictResponse,
    SyncPullRequest,
    SyncPushRequest,
    SyncResolveRequest,
    SyncResultResponse,
    SyncStatusResponse,
)
from skillmeat.core.services.context_sync import ContextSyncService, SyncConflict

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/context-sync",
    tags=["context-sync"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


@router.post(
    "/pull",
    response_model=List[SyncResultResponse],
    summary="Pull changes from project",
    description="Pull changes from project deployed files to collection entities",
    responses={
        200: {
            "description": "Successfully pulled changes",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "entity_id": "spec_file:api-patterns",
                            "entity_name": "api-patterns",
                            "action": "pulled",
                            "message": "Successfully pulled changes from api-patterns.md",
                        }
                    ]
                }
            },
        },
        404: {
            "description": "Project path not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Project path not found: /invalid/path"}
                }
            },
        },
        500: {
            "description": "Sync operation failed",
            "content": {
                "application/json": {"example": {"detail": "Sync failed: <error>"}}
            },
        },
    },
)
async def pull_changes(
    request: SyncPullRequest,
    sync_service: ContextSyncServiceDep,
) -> List[SyncResultResponse]:
    """Pull changes from project to collection.

    Reads deployed files and updates collection entities with new content.
    This captures manual edits made to deployed files in the project.

    Args:
        request: Pull request with project path and optional entity IDs
        sync_service: ContextSyncService dependency

    Returns:
        List of sync results

    Raises:
        HTTPException: If project path not found or sync fails
    """
    logger.info(f"Pull request for project: {request.project_path}")

    # Validate project path exists
    project_path = Path(request.project_path)
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project path not found: {request.project_path}",
        )

    try:
        # Pull changes
        results = sync_service.pull_changes(
            project_path=request.project_path,
            entity_ids=request.entity_ids,
        )

        # Convert to response models
        response = [
            SyncResultResponse(
                entity_id=r.entity_id,
                entity_name=r.entity_name,
                action=r.action,
                message=r.message,
            )
            for r in results
        ]

        logger.info(f"Pull completed: {len(response)} entities processed")
        return response

    except FileNotFoundError as e:
        logger.error(f"File not found during pull: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Pull failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.post(
    "/push",
    response_model=List[SyncResultResponse],
    summary="Push changes to project",
    description="Push collection entity changes to project deployed files",
    responses={
        200: {
            "description": "Successfully pushed changes",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "entity_id": "spec_file:api-patterns",
                            "entity_name": "api-patterns",
                            "action": "pushed",
                            "message": "Successfully pushed changes to api-patterns.md",
                        }
                    ]
                }
            },
        },
        404: {"description": "Project path not found"},
        409: {
            "description": "Conflict detected (file modified locally)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "entity_id": "spec_file:api-patterns",
                            "entity_name": "api-patterns",
                            "action": "conflict",
                            "message": "Both collection and project modified, use overwrite=True to force",
                        }
                    ]
                }
            },
        },
        500: {"description": "Sync operation failed"},
    },
)
async def push_changes(
    request: SyncPushRequest,
    sync_service: ContextSyncServiceDep,
) -> List[SyncResultResponse]:
    """Push collection changes to project.

    Writes collection entity content to deployed files. If overwrite=False
    and file has been modified, returns conflict instead of overwriting.

    Args:
        request: Push request with project path, entity IDs, and overwrite flag
        sync_service: ContextSyncService dependency

    Returns:
        List of sync results

    Raises:
        HTTPException: If project path not found or sync fails
    """
    logger.info(
        f"Push request for project: {request.project_path} (overwrite={request.overwrite})"
    )

    # Validate project path exists
    project_path = Path(request.project_path)
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project path not found: {request.project_path}",
        )

    try:
        # Push changes
        results = sync_service.push_changes(
            project_path=request.project_path,
            entity_ids=request.entity_ids,
            overwrite=request.overwrite,
        )

        # Convert to response models
        response = [
            SyncResultResponse(
                entity_id=r.entity_id,
                entity_name=r.entity_name,
                action=r.action,
                message=r.message,
            )
            for r in results
        ]

        logger.info(f"Push completed: {len(response)} entities processed")
        return response

    except FileNotFoundError as e:
        logger.error(f"File not found during push: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Push failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Get sync status",
    description="Get sync status for a project (modified entities and conflicts)",
    responses={
        200: {
            "description": "Sync status retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "modified_in_project": ["spec_file:api-patterns"],
                        "modified_in_collection": ["rule_file:debugging"],
                        "conflicts": [
                            {
                                "entity_id": "spec_file:api-patterns",
                                "entity_name": "api-patterns",
                                "entity_type": "spec_file",
                                "collection_hash": "abc123",
                                "deployed_hash": "def456",
                                "collection_content": "# API Patterns...",
                                "deployed_content": "# API Patterns (modified)...",
                                "collection_path": "/collection/path",
                                "deployed_path": "/project/.claude/specs/api-patterns.md",
                            }
                        ],
                    }
                }
            },
        },
        404: {"description": "Project path not found"},
        500: {"description": "Status check failed"},
    },
)
async def get_sync_status(
    sync_service: ContextSyncServiceDep,
    project_path: str = Query(
        ..., description="Absolute path to project directory"
    ),
) -> SyncStatusResponse:
    """Get sync status for a project.

    Detects modified entities and conflicts between collection and project.

    Args:
        project_path: Absolute path to project directory
        sync_service: ContextSyncService dependency

    Returns:
        Sync status with modified entities and conflicts

    Raises:
        HTTPException: If project path not found or status check fails
    """
    logger.info(f"Status request for project: {project_path}")

    # Validate project path exists
    path = Path(project_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project path not found: {project_path}",
        )

    try:
        # Get modified entities
        modified = sync_service.detect_modified_entities(project_path)

        # Separate by modification location
        modified_in_project = [
            e["entity_id"]
            for e in modified
            if e["modified_in"] in ("project", "both")
        ]
        modified_in_collection = [
            e["entity_id"]
            for e in modified
            if e["modified_in"] in ("collection", "both")
        ]

        # Get conflicts
        conflicts = sync_service.detect_conflicts(project_path)

        # Convert to response models
        conflict_responses = [
            SyncConflictResponse(
                entity_id=c.entity_id,
                entity_name=c.entity_name,
                entity_type=c.entity_type,
                collection_hash=c.collection_hash,
                deployed_hash=c.deployed_hash,
                collection_content=c.collection_content,
                deployed_content=c.deployed_content,
                collection_path=c.collection_path,
                deployed_path=c.deployed_path,
            )
            for c in conflicts
        ]

        logger.info(
            f"Status check complete: {len(modified_in_project)} project, "
            f"{len(modified_in_collection)} collection, {len(conflicts)} conflicts"
        )

        return SyncStatusResponse(
            modified_in_project=modified_in_project,
            modified_in_collection=modified_in_collection,
            conflicts=conflict_responses,
        )

    except Exception as e:
        logger.exception(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}",
        )


@router.post(
    "/resolve",
    response_model=SyncResultResponse,
    summary="Resolve sync conflict",
    description="Resolve a sync conflict using user-selected strategy",
    responses={
        200: {
            "description": "Conflict resolved",
            "content": {
                "application/json": {
                    "example": {
                        "entity_id": "spec_file:api-patterns",
                        "entity_name": "api-patterns",
                        "action": "resolved",
                        "message": "Conflict resolved using strategy: keep_local",
                    }
                }
            },
        },
        400: {
            "description": "Invalid request (e.g., merge without content)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "merged_content required when resolution='merge'"
                    }
                }
            },
        },
        404: {"description": "Project path or entity not found"},
        500: {"description": "Resolution failed"},
    },
)
async def resolve_conflict(
    request: SyncResolveRequest,
    sync_service: ContextSyncServiceDep,
) -> SyncResultResponse:
    """Resolve sync conflict.

    Applies user-selected resolution strategy:
    - keep_local: Update collection from project (project wins)
    - keep_remote: Update project from collection (collection wins)
    - merge: Use provided merged_content for both

    Args:
        request: Resolve request with project path, entity ID, and resolution
        sync_service: ContextSyncService dependency

    Returns:
        Sync result with resolution outcome

    Raises:
        HTTPException: If validation fails or resolution fails
    """
    logger.info(
        f"Resolve request for {request.entity_id} in {request.project_path}: "
        f"strategy={request.resolution}"
    )

    # Validate project path exists
    project_path = Path(request.project_path)
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project path not found: {request.project_path}",
        )

    # Validate merge has content
    if request.resolution == "merge" and not request.merged_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merged_content required when resolution='merge'",
        )

    try:
        # Find conflict for this entity
        conflicts = sync_service.detect_conflicts(request.project_path)
        conflict = next(
            (c for c in conflicts if c.entity_id == request.entity_id), None
        )

        if not conflict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No conflict found for entity: {request.entity_id}",
            )

        # Resolve conflict
        result = sync_service.resolve_conflict(
            conflict=conflict,
            resolution=request.resolution,
            merged_content=request.merged_content,
        )

        logger.info(
            f"Conflict resolved for {request.entity_id}: {result.action}"
        )

        return SyncResultResponse(
            entity_id=result.entity_id,
            entity_name=result.entity_name,
            action=result.action,
            message=result.message,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Conflict resolution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resolution failed: {str(e)}",
        )
