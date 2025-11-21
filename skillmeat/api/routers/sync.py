"""Sync API endpoints for upstream/collection/project synchronization."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import CollectionManagerDep, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.drift import DriftArtifact, DriftResponse
from skillmeat.api.schemas.sync_jobs import (
    SyncJobCreateRequest,
    SyncJobStatusResponse,
)
from skillmeat.api.schemas.sync import (
    ConflictEntry,
    ResolveRequest,
    ResolveResponse,
    SyncRequest,
    SyncResponse,
)
from skillmeat.api.schemas.version_history import VersionEntry, VersionHistoryResponse
from skillmeat.config import ConfigManager
from skillmeat.core.sync import SyncManager
from skillmeat.core.sync_jobs import InProcessJobService
from skillmeat.models import SyncJobRecord, SyncJobState

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


def _job_to_status(job: SyncJobRecord) -> SyncJobStatusResponse:
    """Convert job record to API status response."""
    duration_ms = None
    if job.started_at and job.ended_at:
        duration_ms = int((job.ended_at - job.started_at).total_seconds() * 1000)
    conflicts_payload = []
    for c in job.conflicts or []:
        if hasattr(c, "to_dict"):
            conflicts_payload.append(c.to_dict())  # type: ignore[attr-defined]
        elif isinstance(c, dict):
            conflicts_payload.append(c)
        else:
            conflicts_payload.append(getattr(c, "__dict__", {}))
    return SyncJobStatusResponse(
        job_id=job.id,
        direction=job.direction,
        state=job.state.value if hasattr(job.state, "value") else str(job.state),
        pct_complete=job.pct_complete,
        duration_ms=duration_ms,
        started_at=job.started_at,
        ended_at=job.ended_at,
        trace_id=job.trace_id,
        log_excerpt=job.log_excerpt,
        conflicts=conflicts_payload,
        artifacts=job.artifacts or [],
        project_path=job.project_path,
        collection=job.collection,
        strategy=job.strategy,
    )


def get_sync_manager(collection_mgr: CollectionManagerDep) -> SyncManager:
    """Provide SyncManager with injected CollectionManager."""
    return SyncManager(collection_manager=collection_mgr)


# Job runner singleton (in-process)
_job_service: Optional[InProcessJobService] = None


def get_job_service(sync_mgr: SyncManager = Depends(get_sync_manager)) -> InProcessJobService:
    """Initialize and return job service."""
    global _job_service  # noqa: PLW0603
    if _job_service is None:
        # bind sync function that adapts SyncManager methods
        def run_job(job: SyncJobRecord) -> SyncJobRecord:
            """Execute a job according to direction."""
            job.log_excerpt = None
            job.conflicts = []
            started = datetime.now(timezone.utc)
            try:
                if job.direction == "upstream_to_collection":
                    result = sync_mgr.sync_collection_from_upstream(
                        collection_name=job.collection,
                        artifact_names=job.artifacts,
                        dry_run=job.dry_run,
                    )
                elif job.direction == "collection_to_project":
                    if not job.project_path:
                        raise ValueError("project_path required for collection_to_project")
                    result = sync_mgr.sync_project_from_collection(
                        project_path=Path(job.project_path),
                        collection_name=job.collection,
                        artifact_names=job.artifacts,
                        dry_run=job.dry_run,
                    )
                elif job.direction == "project_to_collection":
                    if not job.project_path:
                        raise ValueError("project_path required for project_to_collection")
                    strategy = job.strategy or "overwrite"
                    result = sync_mgr.sync_from_project(
                        project_path=Path(job.project_path),
                        artifact_names=job.artifacts,
                        strategy=strategy,
                        dry_run=job.dry_run,
                        interactive=False,
                    )
                else:
                    raise ValueError(f"Unsupported direction: {job.direction}")

                job.pct_complete = 1.0
                job.ended_at = datetime.now(timezone.utc)
                job.log_excerpt = getattr(result, "message", None)
                conflicts = getattr(result, "conflicts", []) or []
                job.conflicts = [
                    c if isinstance(c, dict) else getattr(c, "__dict__", {}) for c in conflicts
                ]
                if conflicts:
                    job.state = SyncJobState.CONFLICT
                else:
                    job.state = SyncJobState.SUCCESS
                return job
            except Exception as exc:  # noqa: BLE001
                job.state = SyncJobState.ERROR
                job.log_excerpt = str(exc)
                job.ended_at = datetime.now(timezone.utc)
                return job
            finally:
                if not job.ended_at:
                    job.ended_at = datetime.now(timezone.utc)
                elapsed_ms = (job.ended_at - started).total_seconds() * 1000
                logger.info(
                    "Sync job completed",
                    extra={
                        "job_id": job.id,
                        "state": job.state.value if hasattr(job.state, "value") else job.state,
                        "elapsed_ms": elapsed_ms,
                        "direction": job.direction,
                    },
                )

        _job_service = InProcessJobService(sync_fn=run_job)
    return _job_service


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


@router.post(
    "/resolve",
    response_model=ResolveResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Resolve conflicts (placeholder)",
    responses={
        501: {"description": "Resolution not implemented yet"},
    },
)
async def resolve_conflicts(
    request: ResolveRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    token: TokenDep = None,
) -> ResolveResponse:
    """Placeholder endpoint for conflict resolution.

    Currently supports coarse resolutions:
    - ours: overwrite project with collection version
    - theirs: overwrite collection with project version
    """
    if not request.project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required for conflict resolution",
        )

    try:
        result = sync_mgr.resolve_conflicts(
            project_path=Path(request.project_path),
            artifact_name=request.artifact_name,
            artifact_type=request.artifact_type,
            resolution=request.resolution,
            collection_name=request.collection,
        )
        return ResolveResponse(
            status=result.status,
            message=result.message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Conflict resolution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/jobs",
    response_model=SyncJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create async sync job",
    responses={
        202: {"description": "Job created"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Async sync disabled"},
    },
)
async def create_sync_job(
    request: SyncJobCreateRequest,
    sync_mgr: SyncManager = Depends(get_sync_manager),
    job_service: InProcessJobService = Depends(get_job_service),
    token: TokenDep = None,
) -> SyncJobStatusResponse:
    """Create a new async sync job."""
    config = ConfigManager()
    if not config.is_sync_async_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Async sync disabled by configuration",
        )

    if request.direction in {"collection_to_project", "project_to_collection"} and not request.project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required for project directions",
        )

    try:
        job = job_service.create_job(
            direction=request.direction,
            artifacts=request.artifacts,
            project_path=request.project_path,
            collection=request.collection,
            strategy=request.strategy,
            dry_run=request.dry_run,
            trace_id=None,
        )
        return _job_to_status(job)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create sync job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get(
    "/jobs/{job_id}",
    response_model=SyncJobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sync job status",
    responses={
        200: {"description": "Job status returned"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_sync_job_status(
    job_id: str,
    job_service: InProcessJobService = Depends(get_job_service),
    token: TokenDep = None,
) -> SyncJobStatusResponse:
    """Return job status."""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return _job_to_status(job)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Drift detection failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
