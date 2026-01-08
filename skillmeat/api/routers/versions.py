"""Version management API endpoints.

Provides snapshot and rollback operations for collection versioning.
"""

import base64
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.version import (
    ConflictMetadataResponse,
    RollbackRequest,
    RollbackResponse,
    RollbackSafetyAnalysisResponse,
    SnapshotCreateRequest,
    SnapshotCreateResponse,
    SnapshotListResponse,
    SnapshotResponse,
    VersionDiffRequest,
    VersionDiffResponse,
)
from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.version import VersionManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/versions",
    tags=["versions"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


# ====================
# Dependency Injection
# ====================


def get_version_manager() -> VersionManager:
    """Get VersionManager dependency.

    Returns:
        VersionManager instance
    """
    return VersionManager()


def get_diff_engine() -> DiffEngine:
    """Get DiffEngine dependency.

    Returns:
        DiffEngine instance
    """
    return DiffEngine()


# Type aliases for dependency injection
VersionManagerDep = Annotated[VersionManager, Depends(get_version_manager)]
DiffEngineDep = Annotated[DiffEngine, Depends(get_diff_engine)]


# ====================
# Cursor Utilities
# ====================


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


# ====================
# Snapshot Endpoints
# ====================


@router.get(
    "/snapshots",
    response_model=SnapshotListResponse,
    summary="List snapshots",
    description="Retrieve a paginated list of collection snapshots",
    responses={
        200: {"description": "Successfully retrieved snapshots"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_snapshots(
    version_mgr: VersionManagerDep,
    token: TokenDep,
    collection_name: Optional[str] = Query(
        default=None,
        description="Collection name (uses active collection if not specified)",
    ),
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
) -> SnapshotListResponse:
    """List all snapshots with cursor-based pagination.

    Args:
        version_mgr: Version manager dependency
        token: Authentication token
        collection_name: Optional collection name
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of snapshots

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(
            f"Listing snapshots (collection={collection_name}, limit={limit}, after={after})"
        )

        # Decode cursor if provided
        cursor = decode_cursor(after) if after else None

        # Get snapshots from VersionManager
        snapshots, next_cursor = version_mgr.list_snapshots(
            collection_name=collection_name,
            limit=limit,
            cursor=cursor,
        )

        # Convert to response models
        items: List[SnapshotResponse] = [
            SnapshotResponse(
                id=snapshot.id,
                timestamp=snapshot.timestamp,
                message=snapshot.message,
                collection_name=snapshot.collection_name,
                artifact_count=snapshot.artifact_count,
            )
            for snapshot in snapshots
        ]

        # Build pagination info
        has_next = next_cursor is not None
        has_previous = cursor is not None

        start_cursor = encode_cursor(snapshots[0].id) if snapshots else None
        end_cursor = encode_cursor(next_cursor) if next_cursor else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=None,  # Total count not efficiently available
        )

        logger.info(f"Retrieved {len(items)} snapshots")
        return SnapshotListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing snapshots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list snapshots: {str(e)}",
        )


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    summary="Get snapshot details",
    description="Retrieve detailed information about a specific snapshot",
    responses={
        200: {"description": "Successfully retrieved snapshot"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Snapshot not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_snapshot(
    snapshot_id: str,
    version_mgr: VersionManagerDep,
    token: TokenDep,
    collection_name: Optional[str] = Query(
        default=None,
        description="Collection name (uses active collection if not specified)",
    ),
) -> SnapshotResponse:
    """Get details for a specific snapshot.

    Args:
        snapshot_id: Snapshot identifier
        version_mgr: Version manager dependency
        token: Authentication token
        collection_name: Optional collection name

    Returns:
        Snapshot details

    Raises:
        HTTPException: If snapshot not found or on error
    """
    try:
        logger.info(f"Getting snapshot: {snapshot_id} (collection={collection_name})")

        snapshot = version_mgr.get_snapshot(snapshot_id, collection_name)

        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' not found",
            )

        return SnapshotResponse(
            id=snapshot.id,
            timestamp=snapshot.timestamp,
            message=snapshot.message,
            collection_name=snapshot.collection_name,
            artifact_count=snapshot.artifact_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting snapshot '{snapshot_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get snapshot: {str(e)}",
        )


@router.post(
    "/snapshots",
    response_model=SnapshotCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create snapshot",
    description="Create a new snapshot of a collection",
    responses={
        201: {"description": "Successfully created snapshot"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_snapshot(
    request: SnapshotCreateRequest,
    version_mgr: VersionManagerDep,
    token: TokenDep,
) -> SnapshotCreateResponse:
    """Create a new snapshot of a collection.

    Args:
        request: Snapshot creation request
        version_mgr: Version manager dependency
        token: Authentication token

    Returns:
        Created snapshot details

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Creating snapshot (collection={request.collection_name}, message={request.message})"
        )

        snapshot = version_mgr.create_snapshot(
            collection_name=request.collection_name,
            message=request.message,
        )

        logger.info(f"Snapshot created: {snapshot.id}")
        return SnapshotCreateResponse(
            snapshot=SnapshotResponse(
                id=snapshot.id,
                timestamp=snapshot.timestamp,
                message=snapshot.message,
                collection_name=snapshot.collection_name,
                artifact_count=snapshot.artifact_count,
            ),
            created=True,
        )

    except ValueError as e:
        logger.warning(f"Snapshot creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create snapshot: {str(e)}",
        )


@router.delete(
    "/snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete snapshot",
    description="Delete a specific snapshot",
    responses={
        204: {"description": "Successfully deleted snapshot"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Snapshot not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_snapshot(
    snapshot_id: str,
    version_mgr: VersionManagerDep,
    token: TokenDep,
    collection_name: Optional[str] = Query(
        default=None,
        description="Collection name (uses active collection if not specified)",
    ),
) -> None:
    """Delete a specific snapshot.

    Args:
        snapshot_id: Snapshot identifier
        version_mgr: Version manager dependency
        token: Authentication token
        collection_name: Optional collection name

    Raises:
        HTTPException: If snapshot not found or on error
    """
    try:
        logger.info(f"Deleting snapshot: {snapshot_id} (collection={collection_name})")

        version_mgr.delete_snapshot(snapshot_id, collection_name)

        logger.info(f"Snapshot deleted: {snapshot_id}")
        return None

    except ValueError as e:
        logger.warning(f"Snapshot deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting snapshot '{snapshot_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete snapshot: {str(e)}",
        )


# ====================
# Rollback Endpoints
# ====================


@router.get(
    "/snapshots/{snapshot_id}/rollback-analysis",
    response_model=RollbackSafetyAnalysisResponse,
    summary="Analyze rollback safety",
    description="Analyze potential conflicts and safety before executing rollback",
    responses={
        200: {"description": "Successfully analyzed rollback safety"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Snapshot not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_rollback_safety(
    snapshot_id: str,
    version_mgr: VersionManagerDep,
    token: TokenDep,
    collection_name: Optional[str] = Query(
        default=None,
        description="Collection name (uses active collection if not specified)",
    ),
) -> RollbackSafetyAnalysisResponse:
    """Analyze whether rollback is safe before attempting.

    Performs a dry-run analysis to detect potential conflicts BEFORE
    attempting rollback. This helps users understand what will happen
    and avoid data loss from bad rollbacks.

    Args:
        snapshot_id: Snapshot identifier
        version_mgr: Version manager dependency
        token: Authentication token
        collection_name: Optional collection name

    Returns:
        Rollback safety analysis

    Raises:
        HTTPException: If snapshot not found or on error
    """
    try:
        logger.info(
            f"Analyzing rollback safety: {snapshot_id} (collection={collection_name})"
        )

        analysis = version_mgr.analyze_rollback_safety(snapshot_id, collection_name)

        return RollbackSafetyAnalysisResponse(
            is_safe=analysis.is_safe,
            files_with_conflicts=analysis.files_with_conflicts,
            files_safe_to_restore=analysis.files_safe_to_restore,
            warnings=analysis.warnings,
        )

    except ValueError as e:
        logger.warning(f"Rollback analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Error analyzing rollback safety for '{snapshot_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze rollback safety: {str(e)}",
        )


@router.post(
    "/snapshots/{snapshot_id}/rollback",
    response_model=RollbackResponse,
    summary="Execute rollback",
    description="Rollback to a specific snapshot with optional intelligent merge",
    responses={
        200: {"description": "Successfully executed rollback"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Snapshot not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def rollback(
    snapshot_id: str,
    request: RollbackRequest,
    version_mgr: VersionManagerDep,
    token: TokenDep,
) -> RollbackResponse:
    """Rollback to a specific snapshot.

    Supports both simple rollback and intelligent merge-based rollback
    with selective path restoration.

    Args:
        snapshot_id: Snapshot identifier
        request: Rollback request
        version_mgr: Version manager dependency
        token: Authentication token

    Returns:
        Rollback result

    Raises:
        HTTPException: If snapshot not found or on error
    """
    try:
        logger.info(
            f"Executing rollback: {snapshot_id} "
            f"(collection={request.collection_name}, "
            f"preserve_changes={request.preserve_changes}, "
            f"selective_paths={request.selective_paths})"
        )

        # Use intelligent rollback with merge support
        result = version_mgr.intelligent_rollback(
            snapshot_id=snapshot_id,
            collection_name=request.collection_name,
            preserve_changes=request.preserve_changes,
            selective_paths=request.selective_paths,
            confirm=False,  # API doesn't support interactive confirmation
        )

        # Convert conflicts to response models
        conflicts = [
            ConflictMetadataResponse(
                file_path=conflict.file_path,
                conflict_type=conflict.conflict_type,
                auto_mergeable=conflict.auto_mergeable,
                is_binary=conflict.is_binary,
            )
            for conflict in result.conflicts
        ]

        logger.info(
            f"Rollback completed: {snapshot_id} "
            f"(success={result.success}, "
            f"files_merged={len(result.files_merged)}, "
            f"files_restored={len(result.files_restored)}, "
            f"conflicts={len(conflicts)})"
        )

        return RollbackResponse(
            success=result.success,
            files_merged=result.files_merged,
            files_restored=result.files_restored,
            conflicts=conflicts,
            safety_snapshot_id=result.safety_snapshot_id,
        )

    except ValueError as e:
        logger.warning(f"Rollback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error executing rollback to '{snapshot_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute rollback: {str(e)}",
        )


# ====================
# Diff Endpoints
# ====================


@router.post(
    "/snapshots/diff",
    response_model=VersionDiffResponse,
    summary="Compare snapshots",
    description="Generate a diff showing changes between two snapshots",
    responses={
        200: {"description": "Successfully generated diff"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Snapshot not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def diff_snapshots(
    request: VersionDiffRequest,
    version_mgr: VersionManagerDep,
    diff_engine: DiffEngineDep,
    token: TokenDep,
) -> VersionDiffResponse:
    """Compare two snapshots and generate a diff.

    Args:
        request: Diff request with snapshot IDs
        version_mgr: Version manager dependency
        diff_engine: Diff engine dependency
        token: Authentication token

    Returns:
        Diff result with changes summary

    Raises:
        HTTPException: If snapshots not found or on error
    """
    try:
        logger.info(
            f"Generating diff between snapshots: "
            f"{request.snapshot_id_1} -> {request.snapshot_id_2} "
            f"(collection={request.collection_name})"
        )

        # Get both snapshots
        snapshot1 = version_mgr.get_snapshot(
            request.snapshot_id_1, request.collection_name
        )
        snapshot2 = version_mgr.get_snapshot(
            request.snapshot_id_2, request.collection_name
        )

        if not snapshot1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{request.snapshot_id_1}' not found",
            )
        if not snapshot2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{request.snapshot_id_2}' not found",
            )

        # Extract both snapshots to temporary directories
        with (
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
        ):
            tmpdir1_path = Path(tmpdir1)
            tmpdir2_path = Path(tmpdir2)

            # Extract tarballs
            with tarfile.open(snapshot1.tarball_path, "r:gz") as tar:
                tar.extractall(tmpdir1_path)

            with tarfile.open(snapshot2.tarball_path, "r:gz") as tar:
                tar.extractall(tmpdir2_path)

            # Find the extracted collection directories
            # (tarball contains collection_name as root directory)
            extracted1 = tmpdir1_path / snapshot1.collection_name
            extracted2 = tmpdir2_path / snapshot2.collection_name

            # Run diff engine
            diff_result = diff_engine.diff_directories(extracted1, extracted2)

            # Get modified file paths from FileDiff objects
            modified_files = [fd.path for fd in diff_result.files_modified]

            logger.info(
                f"Diff completed: "
                f"added={len(diff_result.files_added)}, "
                f"removed={len(diff_result.files_removed)}, "
                f"modified={len(modified_files)}, "
                f"lines_added={diff_result.total_lines_added}, "
                f"lines_removed={diff_result.total_lines_removed}"
            )

            return VersionDiffResponse(
                files_added=diff_result.files_added,
                files_removed=diff_result.files_removed,
                files_modified=modified_files,
                total_lines_added=diff_result.total_lines_added,
                total_lines_removed=diff_result.total_lines_removed,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating diff between '{request.snapshot_id_1}' "
            f"and '{request.snapshot_id_2}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate diff: {str(e)}",
        )
