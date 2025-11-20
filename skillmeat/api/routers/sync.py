"""Sync API endpoints for upstream/collection/project synchronization."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import CollectionManagerDep, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.sync import ConflictEntry, SyncRequest, SyncResponse
from skillmeat.core.sync import SyncManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sync",
    tags=["sync"],
    dependencies=[Depends(verify_api_key)],
)


def _build_conflicts(conflicts) -> List[ConflictEntry]:
    entries: List[ConflictEntry] = []
    for c in conflicts or []:
        name = getattr(c, "artifact_name", "unknown")
        error = getattr(c, "error", None)
        conflict_files = getattr(c, "conflict_files", []) or []
        entries.append(ConflictEntry(artifact_name=name, error=error, conflict_files=conflict_files))
    return entries


def _result_to_response(result) -> SyncResponse:
    return SyncResponse(
        status=result.status,
        message=getattr(result, "message", None),
        artifacts_synced=result.artifacts_synced,
        conflicts=_build_conflicts(result.conflicts),
    )


def get_sync_manager(collection_mgr: CollectionManagerDep) -> SyncManager:
    """Provide SyncManager with injected CollectionManager."""
    return SyncManager(collection_manager=collection_mgr)


@router.post(
    "/upstream",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync collection from upstream",
    responses={
        200: {"description": "Sync completed"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Sync failed"},
    },
)
async def sync_upstream(
    request: SyncRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
) -> SyncResponse:
    """Sync upstream → collection."""
    try:
        result = sync_mgr.sync_collection_from_upstream(
            collection_name=request.collection,
            artifact_names=request.artifacts,
            dry_run=request.dry_run,
        )
        return _result_to_response(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upstream sync failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/push",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync collection to project",
    responses={
        200: {"description": "Sync completed"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Sync failed"},
    },
)
async def sync_push(
    request: SyncRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
) -> SyncResponse:
    """Sync collection → project."""
    if not request.project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required for push",
        )

    try:
        project_path = Path(request.project_path)
        result = sync_mgr.sync_project_from_collection(
            project_path=project_path,
            collection_name=request.collection,
            artifact_names=request.artifacts,
            dry_run=request.dry_run,
        )
        return _result_to_response(result)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Push sync failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/pull",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync project changes back to collection",
    responses={
        200: {"description": "Sync completed"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Sync failed"},
    },
)
async def sync_pull(
    request: SyncRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
) -> SyncResponse:
    """Sync project → collection."""
    if not request.project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required for pull",
        )

    strategy = request.strategy or "overwrite"
    try:
        project_path = Path(request.project_path)
        result = sync_mgr.sync_from_project(
            project_path=project_path,
            artifact_names=request.artifacts,
            strategy=strategy,
            dry_run=request.dry_run,
            interactive=False,
        )
        return _result_to_response(result)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pull sync failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
