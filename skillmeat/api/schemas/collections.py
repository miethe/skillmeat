"""Collection API schemas for request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import PageInfo, PaginatedResponse


class CollectionCreateRequest(BaseModel):
    """Request schema for creating a new collection.

    This schema is currently minimal as collections are auto-initialized.
    Future versions may support custom collection settings.
    """

    name: str = Field(
        description="Collection name (must be unique)",
        min_length=1,
        max_length=100,
        examples=["my-collection"],
    )


class CollectionUpdateRequest(BaseModel):
    """Request schema for updating collection metadata.

    Currently supports minimal updates. Future versions will add
    more configuration options.
    """

    name: Optional[str] = Field(
        default=None,
        description="New collection name",
        min_length=1,
        max_length=100,
        examples=["renamed-collection"],
    )


class ArtifactSummary(BaseModel):
    """Summary of an artifact within a collection.

    Lightweight artifact representation for collection listings.
    """

    id: str = Field(
        description="Artifact unique identifier",
        examples=["pdf-skill"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["pdf-skill"],
    )
    type: str = Field(
        description="Artifact type (skill, command, agent)",
        examples=["skill"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Current version",
        examples=["1.2.3"],
    )
    source: str = Field(
        description="Source specification",
        examples=["anthropics/skills/pdf"],
    )


class CollectionResponse(BaseModel):
    """Response schema for a single collection.

    Provides complete collection metadata including artifact count
    and timestamps.
    """

    id: str = Field(
        description="Collection unique identifier",
        examples=["default"],
    )
    name: str = Field(
        description="Collection name",
        examples=["default"],
    )
    version: str = Field(
        description="Collection format version",
        examples=["1.0.0"],
    )
    artifact_count: int = Field(
        description="Number of artifacts in collection",
        examples=[5],
    )
    created: datetime = Field(
        description="Collection creation timestamp",
    )
    updated: datetime = Field(
        description="Last update timestamp",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "default",
                "name": "default",
                "version": "1.0.0",
                "artifact_count": 5,
                "created": "2024-11-16T12:00:00Z",
                "updated": "2024-11-16T15:30:00Z",
            }
        }


class CollectionListResponse(PaginatedResponse[CollectionResponse]):
    """Paginated response for collection listings.

    Extends the generic paginated response with collection-specific items.
    """

    pass


class CollectionArtifactsResponse(PaginatedResponse[ArtifactSummary]):
    """Paginated response for artifacts within a collection.

    Returns lightweight artifact summaries for efficient collection browsing.
    """

    pass


# ============================================================================
# Collection Refresh Schemas
# ============================================================================


class RefreshModeEnum(str, Enum):
    """Refresh mode for collection artifact metadata updates.

    Controls the scope and behavior of metadata refresh operations.
    """

    METADATA_ONLY = "metadata_only"
    CHECK_ONLY = "check_only"
    SYNC = "sync"


class RefreshRequest(BaseModel):
    """Request schema for refreshing collection artifact metadata.

    Supports dry-run preview mode and selective artifact filtering.
    """

    mode: RefreshModeEnum = Field(
        default=RefreshModeEnum.METADATA_ONLY,
        description=(
            "Refresh mode: 'metadata_only' updates metadata fields only, "
            "'check_only' previews changes without applying, "
            "'sync' performs full synchronization including version updates"
        ),
        examples=[RefreshModeEnum.METADATA_ONLY],
    )

    artifact_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional filter to target specific artifacts. "
            "Supports 'type' (artifact type) and 'name' (glob pattern) keys."
        ),
        examples=[{"type": "skill"}, {"name": "canvas-*"}],
    )

    dry_run: bool = Field(
        default=False,
        description="Preview changes without applying them (overrides mode)",
        examples=[False],
    )

    fields: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of specific fields to refresh. "
            "Valid fields: description, tags, author, license, origin_source. "
            "If not provided, all fields will be refreshed."
        ),
        examples=[["description", "tags"], ["author"]],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "mode": "metadata_only",
                "artifact_filter": {"type": "skill"},
                "dry_run": False,
            }
        }


class RefreshEntryResponse(BaseModel):
    """Response schema for a single artifact refresh operation.

    Provides detailed change tracking for individual artifacts.
    """

    artifact_id: str = Field(
        description="Unique identifier for the artifact (format: 'type:name')",
        examples=["skill:canvas-design"],
    )

    status: str = Field(
        description=(
            "Refresh outcome: 'refreshed' (updated), 'unchanged' (no changes), "
            "'skipped' (no GitHub source), 'error' (failed)"
        ),
        examples=["refreshed"],
    )

    changes: List[str] = Field(
        default_factory=list,
        description="List of field names that were changed",
        examples=[["description", "tags"]],
    )

    old_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Previous values for changed fields",
        examples=[{"description": "Old description", "tags": []}],
    )

    new_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="New values applied for changed fields",
        examples=[{"description": "New description", "tags": ["design", "ui"]}],
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if status is 'error'",
        examples=["Rate limit exceeded"],
    )

    reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation for skip/error status",
        examples=["No GitHub source"],
    )

    duration_ms: float = Field(
        default=0.0,
        description="Time taken to refresh this artifact in milliseconds",
        examples=[150.5],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:canvas-design",
                "status": "refreshed",
                "changes": ["description", "tags"],
                "old_values": {"description": "Old desc", "tags": []},
                "new_values": {
                    "description": "New desc",
                    "tags": ["design", "ui"],
                },
                "error": None,
                "reason": None,
                "duration_ms": 150.5,
            }
        }


class RefreshSummary(BaseModel):
    """Summary statistics for a collection refresh operation.

    Aggregates counts and success rate across all processed artifacts.
    """

    total_processed: int = Field(
        description="Total number of artifacts processed",
        examples=[18],
    )

    refreshed_count: int = Field(
        description="Number of artifacts successfully updated",
        examples=[5],
    )

    unchanged_count: int = Field(
        description="Number of artifacts with no changes needed",
        examples=[10],
    )

    skipped_count: int = Field(
        description="Number of artifacts skipped (e.g., no GitHub source)",
        examples=[2],
    )

    error_count: int = Field(
        description="Number of artifacts that failed with errors",
        examples=[1],
    )

    success_rate: float = Field(
        description="Percentage of successful operations (refreshed + unchanged)",
        examples=[83.33],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "total_processed": 18,
                "refreshed_count": 5,
                "unchanged_count": 10,
                "skipped_count": 2,
                "error_count": 1,
                "success_rate": 83.33,
            }
        }


class RefreshResponse(BaseModel):
    """Response schema for collection refresh operations.

    Provides comprehensive results including summary statistics and
    per-artifact details.
    """

    collection_id: str = Field(
        description="Unique identifier for the refreshed collection",
        examples=["default"],
    )

    status: str = Field(
        description=(
            "Overall operation status: 'completed' (all successful), "
            "'partial' (some errors), 'failed' (all failed)"
        ),
        examples=["completed"],
    )

    timestamp: datetime = Field(
        description="When the refresh operation completed",
    )

    mode: RefreshModeEnum = Field(
        description="Refresh mode used for this operation",
        examples=[RefreshModeEnum.METADATA_ONLY],
    )

    dry_run: bool = Field(
        description="Whether this was a dry-run (preview) operation",
        examples=[False],
    )

    summary: RefreshSummary = Field(
        description="Aggregated summary statistics",
    )

    details: List[RefreshEntryResponse] = Field(
        description="Individual results for each processed artifact",
    )

    duration_ms: float = Field(
        description="Total time for the refresh operation in milliseconds",
        examples=[2500.0],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "collection_id": "default",
                "status": "completed",
                "timestamp": "2024-11-16T15:30:00Z",
                "mode": "metadata_only",
                "dry_run": False,
                "summary": {
                    "total_processed": 18,
                    "refreshed_count": 5,
                    "unchanged_count": 10,
                    "skipped_count": 2,
                    "error_count": 1,
                    "success_rate": 83.33,
                },
                "details": [
                    {
                        "artifact_id": "skill:canvas-design",
                        "status": "refreshed",
                        "changes": ["description", "tags"],
                        "old_values": {"description": "Old desc", "tags": []},
                        "new_values": {
                            "description": "New desc",
                            "tags": ["design"],
                        },
                        "error": None,
                        "reason": None,
                        "duration_ms": 150.5,
                    }
                ],
                "duration_ms": 2500.0,
            }
        }

    @classmethod
    def from_refresh_result(
        cls,
        collection_id: str,
        result: Any,  # RefreshResult type (avoiding import)
        mode: RefreshModeEnum,
        dry_run: bool,
    ) -> "RefreshResponse":
        """Create RefreshResponse from core RefreshResult.

        Args:
            collection_id: Collection identifier
            result: RefreshResult from CollectionRefresher
            mode: Refresh mode used
            dry_run: Whether this was a dry-run operation

        Returns:
            RefreshResponse with all fields populated
        """
        # Convert RefreshEntryResult list to RefreshEntryResponse list
        details = [
            RefreshEntryResponse(
                artifact_id=entry.artifact_id,
                status=entry.status,
                changes=entry.changes,
                old_values=entry.old_values,
                new_values=entry.new_values,
                error=entry.error,
                reason=entry.reason,
                duration_ms=entry.duration_ms,
            )
            for entry in result.entries
        ]

        # Create summary
        summary = RefreshSummary(
            total_processed=result.total_processed,
            refreshed_count=result.refreshed_count,
            unchanged_count=result.unchanged_count,
            skipped_count=result.skipped_count,
            error_count=result.error_count,
            success_rate=result.success_rate,
        )

        # Determine overall status
        if result.error_count == 0:
            status = "completed"
        elif result.error_count == result.total_processed:
            status = "failed"
        else:
            status = "partial"

        return cls(
            collection_id=collection_id,
            status=status,
            timestamp=datetime.now(),
            mode=mode,
            dry_run=dry_run,
            summary=summary,
            details=details,
            duration_ms=result.duration_ms,
        )


# ============================================================================
# Update Check Schemas
# ============================================================================


class UpdateCheckResultResponse(BaseModel):
    """Response schema for a single artifact update check.

    Provides information about whether an update is available for an artifact.
    """

    artifact_id: str = Field(
        description="Unique identifier for the artifact (format: 'type:name')",
        examples=["skill:canvas-design"],
    )

    artifact_name: str = Field(
        description="Human-readable name of the artifact",
        examples=["canvas-design"],
    )

    current_sha: Optional[str] = Field(
        default=None,
        description="Current resolved SHA of the artifact",
        examples=["abc123def456"],
    )

    upstream_sha: Optional[str] = Field(
        default=None,
        description="Latest SHA from upstream GitHub source",
        examples=["def456abc789"],
    )

    update_available: bool = Field(
        description="Whether an update is available (SHAs differ)",
        examples=[True],
    )

    reason: Optional[str] = Field(
        default=None,
        description=(
            "Explanation of the result (e.g., 'SHA mismatch', "
            "'No GitHub source', 'Up to date')"
        ),
        examples=["SHA mismatch"],
    )

    has_local_changes: bool = Field(
        default=False,
        description="Whether local modifications exist that might conflict with update",
        examples=[False],
    )

    merge_strategy: str = Field(
        description=(
            "Recommended action: 'safe_update' (no conflicts), "
            "'review_required' (local changes exist), "
            "'conflict' (both changed), 'no_update' (no update available)"
        ),
        examples=["safe_update"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:canvas-design",
                "artifact_name": "canvas-design",
                "current_sha": "abc123def456",
                "upstream_sha": "def456abc789",
                "update_available": True,
                "reason": "SHA mismatch",
                "has_local_changes": False,
                "merge_strategy": "safe_update",
            }
        }


class UpdateCheckResponse(BaseModel):
    """Response schema for collection update check operation.

    Provides a list of update availability results for artifacts in a collection.
    """

    collection_id: str = Field(
        description="Unique identifier for the checked collection",
        examples=["default"],
    )

    timestamp: datetime = Field(
        description="When the update check operation completed",
    )

    results: List[UpdateCheckResultResponse] = Field(
        description="Update availability results for each artifact",
    )

    updates_available: int = Field(
        description="Total number of artifacts with updates available",
        examples=[3],
    )

    up_to_date: int = Field(
        description="Total number of artifacts already up to date",
        examples=[12],
    )

    skipped: int = Field(
        description="Total number of artifacts skipped (e.g., no GitHub source)",
        examples=[2],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "collection_id": "default",
                "timestamp": "2024-11-16T15:30:00Z",
                "results": [
                    {
                        "artifact_id": "skill:canvas-design",
                        "artifact_name": "canvas-design",
                        "current_sha": "abc123",
                        "upstream_sha": "def456",
                        "update_available": True,
                        "reason": "SHA mismatch",
                        "has_local_changes": False,
                        "merge_strategy": "safe_update",
                    }
                ],
                "updates_available": 3,
                "up_to_date": 12,
                "skipped": 2,
            }
        }

    @classmethod
    def from_update_results(
        cls,
        collection_id: str,
        results: List[Any],  # List[UpdateAvailableResult] (avoiding import)
    ) -> "UpdateCheckResponse":
        """Create UpdateCheckResponse from core UpdateAvailableResult list.

        Args:
            collection_id: Collection identifier
            results: List of UpdateAvailableResult from CollectionRefresher.check_updates()

        Returns:
            UpdateCheckResponse with all fields populated
        """
        # Convert UpdateAvailableResult list to UpdateCheckResultResponse list
        result_responses = [
            UpdateCheckResultResponse(
                artifact_id=result.artifact_id,
                artifact_name=result.artifact_name,
                current_sha=result.current_sha,
                upstream_sha=result.upstream_sha,
                update_available=result.update_available,
                reason=result.reason,
                has_local_changes=result.has_local_changes,
                merge_strategy=result.merge_strategy,
            )
            for result in results
        ]

        # Calculate summary counts
        updates_available = sum(1 for r in results if r.update_available)
        skipped = sum(1 for r in results if r.reason and "No GitHub source" in r.reason)
        up_to_date = len(results) - updates_available - skipped

        return cls(
            collection_id=collection_id,
            timestamp=datetime.now(),
            results=result_responses,
            updates_available=updates_available,
            up_to_date=up_to_date,
            skipped=skipped,
        )
