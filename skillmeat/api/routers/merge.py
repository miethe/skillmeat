"""Merge operation API endpoints.

Provides endpoints for analyzing merge safety, previewing merge changes,
executing merges with conflict detection, and resolving conflicts.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.merge import (
    ConflictResolveRequest,
    ConflictResolveResponse,
    MergeAnalyzeRequest,
    MergeExecuteRequest,
    MergeExecuteResponse,
    MergePreviewRequest,
    MergePreviewResponse,
    MergeSafetyResponse,
)
from skillmeat.api.schemas.version import ConflictMetadataResponse
from skillmeat.core.version_merge import VersionMergeService
from skillmeat.models import ConflictMetadata

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/merge",
    tags=["merge"],
    dependencies=[Depends(verify_api_key)],
)


def get_version_merge_service() -> VersionMergeService:
    """Get VersionMergeService dependency.

    Returns:
        VersionMergeService instance
    """
    return VersionMergeService()


VersionMergeServiceDep = Annotated[
    VersionMergeService, Depends(get_version_merge_service)
]


@router.post(
    "/analyze",
    response_model=MergeSafetyResponse,
    summary="Analyze merge safety",
    description=(
        "Analyze whether merge is safe before attempting. "
        "Performs a dry-run three-way diff to identify potential conflicts "
        "without modifying any files."
    ),
    responses={
        200: {"description": "Successfully analyzed merge safety"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request parameters",
        },
        404: {
            "model": ErrorResponse,
            "description": "Snapshot or collection not found",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_merge(
    request: MergeAnalyzeRequest,
    merge_service: VersionMergeServiceDep,
    token: TokenDep,
) -> MergeSafetyResponse:
    """Analyze merge safety (dry run).

    Args:
        request: Merge analysis request parameters
        merge_service: VersionMergeService dependency
        token: Authentication token

    Returns:
        Merge safety analysis with conflict detection results

    Raises:
        HTTPException: If snapshot not found or analysis fails
    """
    try:
        logger.info(
            f"Analyzing merge safety: base={request.base_snapshot_id}, "
            f"local={request.local_collection}, remote={request.remote_snapshot_id}"
        )

        analysis = merge_service.analyze_merge_safety(
            base_snapshot_id=request.base_snapshot_id,
            local_collection=request.local_collection,
            remote_snapshot_id=request.remote_snapshot_id,
            remote_collection=request.remote_collection,
        )

        # Convert ConflictMetadata to ConflictMetadataResponse
        conflicts = [
            ConflictMetadataResponse(
                file_path=c.file_path,
                conflict_type=c.conflict_type,
                auto_mergeable=c.auto_mergeable,
                is_binary=c.is_binary,
            )
            for c in analysis.conflicts
        ]

        logger.info(
            f"Merge analysis complete: can_auto_merge={analysis.can_auto_merge}, "
            f"conflicts={len(conflicts)}"
        )

        return MergeSafetyResponse(
            can_auto_merge=analysis.can_auto_merge,
            auto_mergeable_count=analysis.auto_mergeable_count,
            conflict_count=analysis.conflict_count,
            conflicts=conflicts,
            warnings=analysis.warnings,
        )

    except ValueError as e:
        logger.error(f"Invalid merge parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to analyze merge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze merge: {str(e)}",
        )


@router.post(
    "/preview",
    response_model=MergePreviewResponse,
    summary="Preview merge changes",
    description=(
        "Get preview of merge changes without executing the merge. "
        "Shows what files will be added, removed, or changed."
    ),
    responses={
        200: {"description": "Successfully generated merge preview"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request parameters",
        },
        404: {
            "model": ErrorResponse,
            "description": "Snapshot or collection not found",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def preview_merge(
    request: MergePreviewRequest,
    merge_service: VersionMergeServiceDep,
    token: TokenDep,
) -> MergePreviewResponse:
    """Preview merge changes without executing.

    Args:
        request: Merge preview request parameters
        merge_service: VersionMergeService dependency
        token: Authentication token

    Returns:
        Merge preview with detailed change information

    Raises:
        HTTPException: If snapshot not found or preview fails
    """
    try:
        logger.info(
            f"Generating merge preview: base={request.base_snapshot_id}, "
            f"local={request.local_collection}, remote={request.remote_snapshot_id}"
        )

        preview = merge_service.get_merge_preview(
            base_snapshot_id=request.base_snapshot_id,
            local_collection=request.local_collection,
            remote_snapshot_id=request.remote_snapshot_id,
            remote_collection=request.remote_collection,
        )

        # Convert ConflictMetadata to ConflictMetadataResponse
        potential_conflicts = [
            ConflictMetadataResponse(
                file_path=c.file_path,
                conflict_type=c.conflict_type,
                auto_mergeable=c.auto_mergeable,
                is_binary=c.is_binary,
            )
            for c in preview.potential_conflicts
        ]

        logger.info(
            f"Merge preview complete: added={len(preview.files_added)}, "
            f"removed={len(preview.files_removed)}, changed={len(preview.files_changed)}"
        )

        return MergePreviewResponse(
            files_added=preview.files_added,
            files_removed=preview.files_removed,
            files_changed=preview.files_changed,
            potential_conflicts=potential_conflicts,
            can_auto_merge=preview.can_auto_merge,
        )

    except ValueError as e:
        logger.error(f"Invalid merge parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to generate merge preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate merge preview: {str(e)}",
        )


@router.post(
    "/execute",
    response_model=MergeExecuteResponse,
    summary="Execute merge operation",
    description=(
        "Execute merge with full conflict detection. "
        "Automatically creates safety snapshot before merge for rollback capability."
    ),
    responses={
        200: {"description": "Merge executed successfully or with conflicts"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request parameters",
        },
        404: {
            "model": ErrorResponse,
            "description": "Snapshot or collection not found",
        },
        409: {
            "model": ErrorResponse,
            "description": "Merge cannot be completed due to unresolved conflicts",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {
            "model": ErrorResponse,
            "description": "Validation errors",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def execute_merge(
    request: MergeExecuteRequest,
    merge_service: VersionMergeServiceDep,
    token: TokenDep,
) -> MergeExecuteResponse:
    """Execute merge with conflict detection.

    Args:
        request: Merge execution request parameters
        merge_service: VersionMergeService dependency
        token: Authentication token

    Returns:
        Merge execution result with files merged and any conflicts

    Raises:
        HTTPException: If snapshot not found, merge fails, or conflicts prevent completion
    """
    try:
        logger.info(
            f"Executing merge: base={request.base_snapshot_id}, "
            f"local={request.local_collection}, remote={request.remote_snapshot_id}, "
            f"auto_snapshot={request.auto_snapshot}"
        )

        result = merge_service.merge_with_conflict_detection(
            base_snapshot_id=request.base_snapshot_id,
            local_collection=request.local_collection,
            remote_snapshot_id=request.remote_snapshot_id,
            remote_collection=request.remote_collection,
            auto_snapshot=request.auto_snapshot,
        )

        # Convert ConflictMetadata to ConflictMetadataResponse
        conflicts = [
            ConflictMetadataResponse(
                file_path=c.file_path,
                conflict_type=c.conflict_type,
                auto_mergeable=c.auto_mergeable,
                is_binary=c.is_binary,
            )
            for c in result.conflicts
        ]

        logger.info(
            f"Merge execution complete: success={result.success}, "
            f"files_merged={len(result.files_merged)}, conflicts={len(conflicts)}"
        )

        # If merge has unresolved conflicts, return 409 Conflict
        if not result.success and conflicts:
            logger.warning(f"Merge has {len(conflicts)} unresolved conflicts")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Merge has {len(conflicts)} unresolved conflicts",
            )

        return MergeExecuteResponse(
            success=result.success,
            files_merged=result.files_merged,
            conflicts=conflicts,
            pre_merge_snapshot_id=result.pre_merge_snapshot_id,
            error=result.error,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid merge parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to execute merge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute merge: {str(e)}",
        )


@router.post(
    "/resolve",
    response_model=ConflictResolveResponse,
    summary="Resolve merge conflict",
    description=(
        "Resolve a single merge conflict by specifying which version to use "
        "or providing custom content."
    ),
    responses={
        200: {"description": "Conflict resolved successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid resolution parameters",
        },
        404: {
            "model": ErrorResponse,
            "description": "Conflict or file not found",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {
            "model": ErrorResponse,
            "description": "Validation errors",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def resolve_conflict(
    request: ConflictResolveRequest,
    merge_service: VersionMergeServiceDep,
    token: TokenDep,
) -> ConflictResolveResponse:
    """Resolve a single merge conflict.

    Args:
        request: Conflict resolution request parameters
        merge_service: VersionMergeService dependency
        token: Authentication token

    Returns:
        Conflict resolution result

    Raises:
        HTTPException: If resolution fails or parameters are invalid
    """
    try:
        logger.info(
            f"Resolving conflict: file={request.file_path}, "
            f"resolution={request.resolution}"
        )

        # Validate custom content if resolution is 'custom'
        if request.resolution == "custom" and request.custom_content is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="custom_content required when resolution='custom'",
            )

        # Create ConflictMetadata from request
        # Note: This is a simplified version - in production, you'd need to retrieve
        # the actual conflict metadata from the merge state or a conflict store
        conflict_metadata = ConflictMetadata(
            file_path=request.file_path,
            conflict_type="content",  # Would be retrieved from actual conflict
            auto_mergeable=False,
            is_binary=False,
        )

        # Resolve conflict
        success = merge_service.resolve_conflict(
            conflict=conflict_metadata,
            resolution=request.resolution,
            custom_content=request.custom_content,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resolve conflict for {request.file_path}",
            )

        logger.info(f"Conflict resolved successfully: {request.file_path}")

        return ConflictResolveResponse(
            success=True,
            file_path=request.file_path,
            resolution_applied=request.resolution,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid resolution parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to resolve conflict: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}",
        )
