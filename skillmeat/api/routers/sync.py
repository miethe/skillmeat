"""Sync API endpoints for upstream/collection/project synchronization."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import CollectionManagerDep, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.drift import DriftArtifact, DriftResponse
from skillmeat.api.schemas.sync import ConflictEntry, SyncRequest, SyncResponse
from skillmeat.api.schemas.version_history import VersionEntry, VersionHistoryResponse
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


def _drift_to_response(drift_results) -> DriftResponse:
    items = []
    for r in drift_results:
        items.append(
            DriftArtifact(
                artifact_name=r.artifact_name,
                artifact_type=r.artifact_type,
                drift_type=r.drift_type,
                collection_sha=r.collection_sha,
                project_sha=r.project_sha,
                collection_version=r.collection_version,
                project_version=r.project_version,
                recommendation=r.recommendation,
                sync_status=r.sync_status.value if hasattr(r.sync_status, "value") else r.sync_status,
            )
        )
    return DriftResponse(
        drift_detected=len(items) > 0,
        drift_count=len(items),
        artifacts=items,
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


@router.post(
    "/drift",
    response_model=DriftResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect drift between project and collection",
    responses={
        200: {"description": "Drift detection completed"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Drift detection failed"},
    },
)
async def sync_drift(
    request: SyncRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
):
    """Check drift for a project."""
    if not request.project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required for drift detection",
        )


@router.get(
    "/version-history",
    response_model=VersionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get version lineage for an artifact (project or collection)",
    responses={
        200: {"description": "Version history returned"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Failed to load version history"},
    },
)
async def version_history(
    artifact_name: str,
    artifact_type: str,
    scope: str = "collection",
    project_path: str = "",
    collection: str = None,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
) -> VersionHistoryResponse:
    """Return version lineage for a specified artifact.

    scope: collection|project determines which tier to inspect.
    """
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.artifact import ArtifactType as ArtifactTypeEnum

    try:
        atype = ArtifactTypeEnum(artifact_type)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact_type: {artifact_type}",
        )

    try:
        versions: list[VersionEntry] = []
        if scope == "collection":
            collection_mgr = sync_mgr.collection_mgr or CollectionManager()
            coll = collection_mgr.load_collection(collection)
            art = coll.find_artifact(artifact_name, atype)
            if not art:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact {artifact_type}/{artifact_name} not found in collection",
                )
            history = getattr(art, "version_lineage", []) or []
            for entry in history:
                versions.append(
                    VersionEntry(
                        hash=entry if isinstance(entry, str) else entry.get("hash"),
                        timestamp=datetime.utcnow(),
                        source="collection",
                        parent_hash=None,
                    )
                )
        elif scope == "project":
            if not project_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="project_path is required when scope=project",
                )
            from skillmeat.storage.deployment import DeploymentTracker

            deployments = DeploymentTracker.read_deployments(Path(project_path))
            deployment = next(
                (
                    d
                    for d in deployments
                    if d.artifact_name == artifact_name
                    and d.artifact_type == artifact_type
                ),
                None,
            )
            if not deployment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact {artifact_type}/{artifact_name} not deployed in project",
                )
            history = deployment.version_lineage or []
            for entry in history:
                versions.append(
                    VersionEntry(
                        hash=entry,
                        timestamp=deployment.deployed_at,
                        source="project",
                        parent_hash=None,
                    )
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope must be 'collection' or 'project'",
            )

        return VersionHistoryResponse(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            versions=versions,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Version history retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    try:
        project_path = Path(request.project_path)
        drift_results = sync_mgr.check_drift(
            project_path=project_path,
            collection_name=request.collection,
        )
        # Optional filter by artifacts
        if request.artifacts:
            allowed = set(request.artifacts)
            drift_results = [d for d in drift_results if d.artifact_name in allowed]
        return _drift_to_response(drift_results)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Drift detection failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
