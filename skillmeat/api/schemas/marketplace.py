"""Marketplace API schemas.

Provides Pydantic models for marketplace listing feeds, installation requests,
publish operations, and broker information.
"""

import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .common import PageInfo


class ListingResponse(BaseModel):
    """Response model for a single marketplace listing.

    Represents a marketplace listing with essential metadata for browsing.
    """

    listing_id: str = Field(
        description="Unique identifier for the listing",
        examples=["skillmeat-123"],
    )
    name: str = Field(
        description="Human-readable name of the bundle",
        examples=["Python Testing Suite"],
    )
    publisher: str = Field(
        description="Publisher name or organization",
        examples=["anthropics"],
    )
    license: str = Field(
        description="License identifier",
        examples=["MIT"],
    )
    artifact_count: int = Field(
        description="Number of artifacts in the bundle",
        ge=0,
        examples=[5],
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization",
        examples=[["testing", "python", "pytest"]],
    )
    created_at: datetime = Field(
        description="Timestamp when listing was created",
        examples=["2025-01-15T10:30:00Z"],
    )
    source_url: str = Field(
        description="URL to listing details page",
        examples=["https://marketplace.skillmeat.dev/listings/123"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional short description",
        examples=["Comprehensive testing utilities for Python projects"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Optional version string",
        examples=["1.2.0"],
    )
    downloads: Optional[int] = Field(
        default=None,
        description="Download count",
        ge=0,
        examples=[1024],
    )
    rating: Optional[float] = Field(
        default=None,
        description="Rating from 0.0 to 5.0",
        ge=0.0,
        le=5.0,
        examples=[4.5],
    )
    price: int = Field(
        default=0,
        description="Price in cents (0 for free)",
        ge=0,
        examples=[0],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "listing_id": "skillmeat-python-testing-123",
                "name": "Python Testing Suite",
                "publisher": "anthropics",
                "license": "MIT",
                "artifact_count": 5,
                "tags": ["testing", "python", "pytest"],
                "created_at": "2025-01-15T10:30:00Z",
                "source_url": "https://marketplace.skillmeat.dev/listings/123",
                "description": "Comprehensive testing utilities",
                "version": "1.2.0",
                "downloads": 1024,
                "rating": 4.5,
                "price": 0,
            }
        }


class ListingDetailResponse(BaseModel):
    """Detailed response model for a single marketplace listing.

    Includes all available metadata for a listing, including bundle URL
    and signature information.
    """

    listing_id: str = Field(
        description="Unique identifier for the listing",
    )
    name: str = Field(
        description="Human-readable name of the bundle",
    )
    publisher: str = Field(
        description="Publisher name or organization",
    )
    license: str = Field(
        description="License identifier",
    )
    artifact_count: int = Field(
        description="Number of artifacts in the bundle",
        ge=0,
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    created_at: datetime = Field(
        description="Timestamp when listing was created",
    )
    source_url: str = Field(
        description="URL to listing details page",
    )
    bundle_url: str = Field(
        description="URL to download the bundle file",
    )
    signature: str = Field(
        description="Base64-encoded Ed25519 signature",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional detailed description",
    )
    version: Optional[str] = Field(
        default=None,
        description="Optional version string",
    )
    homepage: Optional[str] = Field(
        default=None,
        description="Optional URL to project homepage",
    )
    repository: Optional[str] = Field(
        default=None,
        description="Optional URL to source repository",
    )
    downloads: Optional[int] = Field(
        default=None,
        description="Download count",
        ge=0,
    )
    rating: Optional[float] = Field(
        default=None,
        description="Rating from 0.0 to 5.0",
        ge=0.0,
        le=5.0,
    )
    price: int = Field(
        default=0,
        description="Price in cents (0 for free)",
        ge=0,
    )


class ListingsPageResponse(BaseModel):
    """Paginated response for marketplace listings.

    Uses cursor-based pagination for efficient browsing of large datasets.
    """

    items: List[ListingResponse] = Field(
        description="List of listings for this page",
    )
    page_info: PageInfo = Field(
        description="Pagination metadata",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "listing_id": "skillmeat-123",
                        "name": "Python Testing Suite",
                        "publisher": "anthropics",
                        "license": "MIT",
                        "artifact_count": 5,
                        "tags": ["testing", "python"],
                        "created_at": "2025-01-15T10:30:00Z",
                        "source_url": "https://marketplace.skillmeat.dev/listings/123",
                        "price": 0,
                    }
                ],
                "page_info": {
                    "has_next_page": True,
                    "has_previous_page": False,
                    "start_cursor": "Y3Vyc29yOjA=",
                    "end_cursor": "Y3Vyc29yOjE5",
                    "total_count": 100,
                },
            }
        }


class InstallRequest(BaseModel):
    """Request model for installing a marketplace listing.

    Specifies the listing to install and conflict resolution strategy.
    """

    listing_id: str = Field(
        description="Listing ID to install",
        examples=["skillmeat-123"],
    )
    broker: Optional[str] = Field(
        default=None,
        description="Broker name (auto-detect if not provided)",
        examples=["skillmeat"],
    )
    strategy: Literal["merge", "fork", "skip"] = Field(
        default="merge",
        description="Conflict resolution strategy",
        examples=["merge"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "listing_id": "skillmeat-python-testing-123",
                "broker": "skillmeat",
                "strategy": "merge",
            }
        }


class InstallResponse(BaseModel):
    """Response model for installation operations.

    Indicates success status and lists imported artifacts.
    """

    success: bool = Field(
        description="Whether installation succeeded",
        examples=[True],
    )
    artifacts_imported: List[str] = Field(
        description="List of artifact names that were imported",
        examples=[["pytest-skill", "coverage-skill"]],
    )
    message: str = Field(
        description="Status message",
        examples=["Successfully installed 5 artifacts from bundle"],
    )
    listing_id: str = Field(
        description="The listing ID that was installed",
        examples=["skillmeat-123"],
    )
    broker: str = Field(
        description="The broker used for installation",
        examples=["skillmeat"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "artifacts_imported": ["pytest-skill", "coverage-skill"],
                "message": "Successfully installed 2 artifacts",
                "listing_id": "skillmeat-123",
                "broker": "skillmeat",
            }
        }


class PublishRequest(BaseModel):
    """Request model for publishing a bundle to marketplace.

    Specifies the bundle path and additional metadata for the listing.
    """

    bundle_path: str = Field(
        description="Path to the bundle file to publish",
        examples=["/path/to/bundle.tar.gz"],
    )
    broker: str = Field(
        default="skillmeat",
        description="Broker to publish to",
        examples=["skillmeat"],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (description, tags, etc.)",
        examples=[
            {
                "description": "A comprehensive testing suite",
                "tags": ["testing", "python"],
                "homepage": "https://github.com/example/testing-suite",
            }
        ],
    )

    @field_validator("bundle_path")
    @classmethod
    def validate_bundle_path(cls, v: str) -> str:
        """Validate bundle path is not empty.

        Args:
            v: Bundle path value

        Returns:
            Validated bundle path

        Raises:
            ValueError: If path is empty
        """
        if not v or not v.strip():
            raise ValueError("bundle_path cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "bundle_path": "/home/user/.skillmeat/bundles/my-bundle.tar.gz",
                "broker": "skillmeat",
                "metadata": {
                    "description": "Comprehensive testing utilities for Python",
                    "tags": ["testing", "python", "pytest"],
                    "homepage": "https://github.com/anthropics/testing-suite",
                },
            }
        }


class PublishResponse(BaseModel):
    """Response model for publish operations.

    Contains submission details and status information.
    """

    submission_id: str = Field(
        description="Unique identifier for the submission",
        examples=["sub-abc123"],
    )
    status: Literal["pending", "approved", "rejected"] = Field(
        description="Submission status",
        examples=["pending"],
    )
    message: str = Field(
        description="Status message",
        examples=["Bundle submitted for review"],
    )
    broker: str = Field(
        description="Broker the bundle was published to",
        examples=["skillmeat"],
    )
    listing_url: Optional[str] = Field(
        default=None,
        description="URL to view the listing (if approved)",
        examples=["https://marketplace.skillmeat.dev/listings/123"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "submission_id": "sub-abc123def456",
                "status": "pending",
                "message": "Bundle submitted successfully. Pending review.",
                "broker": "skillmeat",
                "listing_url": None,
            }
        }


class BrokerInfo(BaseModel):
    """Information about an available marketplace broker.

    Describes broker capabilities and configuration.
    """

    name: str = Field(
        description="Broker name",
        examples=["skillmeat"],
    )
    enabled: bool = Field(
        description="Whether the broker is currently enabled",
        examples=[True],
    )
    endpoint: str = Field(
        description="Base endpoint URL for the broker API",
        examples=["https://marketplace.skillmeat.dev/api"],
    )
    supports_publish: bool = Field(
        description="Whether the broker supports publishing",
        examples=[True],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional broker description",
        examples=["Official SkillMeat marketplace"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "skillmeat",
                "enabled": True,
                "endpoint": "https://marketplace.skillmeat.dev/api",
                "supports_publish": True,
                "description": "Official SkillMeat marketplace",
            }
        }


class BrokerListResponse(BaseModel):
    """Response model for listing available brokers.

    Contains a list of all configured brokers with their status.
    """

    brokers: List[BrokerInfo] = Field(
        description="List of available brokers",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "brokers": [
                    {
                        "name": "skillmeat",
                        "enabled": True,
                        "endpoint": "https://marketplace.skillmeat.dev/api",
                        "supports_publish": True,
                        "description": "Official SkillMeat marketplace",
                    },
                    {
                        "name": "claudehub",
                        "enabled": True,
                        "endpoint": "https://claude.ai/marketplace/api",
                        "supports_publish": False,
                        "description": "Claude Hub public catalogs (read-only)",
                    },
                ]
            }
        }


# ============================================================================
# GitHub Source Management DTOs
# ============================================================================


class CreateSourceRequest(BaseModel):
    """Request to add a GitHub repository source.

    Specifies repository URL, branch/tag/SHA, and scanning options.
    """

    repo_url: str = Field(
        description="Full GitHub repository URL",
        examples=["https://github.com/anthropics/anthropic-quickstarts"],
    )
    ref: str = Field(
        default="main",
        description="Branch, tag, or SHA to scan",
        examples=["main", "v1.0.0", "abc123"],
    )
    root_hint: Optional[str] = Field(
        default=None,
        description="Subdirectory path within repository to start scanning",
        examples=["skills", "src/artifacts"],
    )
    access_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token for private repos (not stored, used for initial scan)",
    )
    manual_map: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Manual override: artifact_type -> list of paths",
        examples=[{"skill": ["skills/my-skill", "skills/other-skill"]}],
    )
    trust_level: Literal["untrusted", "basic", "verified", "official"] = Field(
        default="basic",
        description="Trust level for artifacts from this source",
    )

    @field_validator("root_hint")
    @classmethod
    def validate_root_hint(cls, v: str | None) -> str | None:
        """Validate root_hint to prevent path traversal attacks.

        Args:
            v: Root hint value to validate

        Returns:
            Validated and stripped root hint

        Raises:
            ValueError: If path contains traversal sequences, absolute paths,
                       null bytes, or invalid characters
        """
        if v is None:
            return v

        # URL decode first to catch encoded attacks
        decoded = urllib.parse.unquote(v)

        # Block path traversal sequences
        if ".." in decoded:
            raise ValueError(
                "root_hint cannot contain parent directory references (..)"
            )

        # Block absolute paths (Unix and Windows)
        if decoded.startswith("/") or (len(decoded) > 1 and decoded[1] == ":"):
            raise ValueError("root_hint must be a relative path")

        # Block null bytes
        if "\x00" in decoded:
            raise ValueError("root_hint cannot contain null bytes")

        # Block other dangerous patterns
        if re.search(r'[<>"|?*]', decoded):
            raise ValueError("root_hint contains invalid characters")

        return v.strip()

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
                "ref": "main",
                "root_hint": "skills",
                "trust_level": "verified",
            }
        }


class SourceResponse(BaseModel):
    """Response model for a GitHub repository source.

    Contains source metadata, scan status, and artifact statistics.
    """

    id: str = Field(
        description="Unique identifier for the source",
        examples=["src_abc123"],
    )
    repo_url: str = Field(
        description="Full GitHub repository URL",
        examples=["https://github.com/anthropics/anthropic-quickstarts"],
    )
    owner: str = Field(
        description="Repository owner username",
        examples=["anthropics"],
    )
    repo_name: str = Field(
        description="Repository name",
        examples=["anthropic-quickstarts"],
    )
    ref: str = Field(
        description="Branch, tag, or SHA being tracked",
        examples=["main"],
    )
    root_hint: Optional[str] = Field(
        default=None,
        description="Subdirectory path for scanning",
        examples=["skills"],
    )
    trust_level: str = Field(
        description="Trust level for artifacts from this source",
        examples=["verified"],
    )
    visibility: str = Field(
        description="Repository visibility (public/private)",
        examples=["public"],
    )
    scan_status: Literal["pending", "scanning", "success", "error"] = Field(
        description="Current scan status",
        examples=["success"],
    )
    artifact_count: int = Field(
        description="Number of artifacts detected in this source",
        ge=0,
        examples=[12],
    )
    last_sync_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful scan",
        examples=["2025-12-06T10:30:00Z"],
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message if scan failed",
    )
    created_at: datetime = Field(
        description="Timestamp when source was added",
        examples=["2025-12-05T09:00:00Z"],
    )
    updated_at: datetime = Field(
        description="Timestamp when source was last modified",
        examples=["2025-12-06T10:30:00Z"],
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "src_anthropics_quickstarts",
                "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
                "owner": "anthropics",
                "repo_name": "anthropic-quickstarts",
                "ref": "main",
                "root_hint": "skills",
                "trust_level": "verified",
                "visibility": "public",
                "scan_status": "success",
                "artifact_count": 12,
                "last_sync_at": "2025-12-06T10:30:00Z",
                "last_error": None,
                "created_at": "2025-12-05T09:00:00Z",
                "updated_at": "2025-12-06T10:30:00Z",
            }
        }


class SourceListResponse(BaseModel):
    """Paginated list of GitHub repository sources.

    Uses cursor-based pagination for efficient browsing.
    """

    items: List[SourceResponse] = Field(
        description="List of sources for this page",
    )
    page_info: PageInfo = Field(
        description="Pagination metadata",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "src_anthropics_quickstarts",
                        "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
                        "owner": "anthropics",
                        "repo_name": "anthropic-quickstarts",
                        "ref": "main",
                        "trust_level": "verified",
                        "visibility": "public",
                        "scan_status": "success",
                        "artifact_count": 12,
                        "created_at": "2025-12-05T09:00:00Z",
                        "updated_at": "2025-12-06T10:30:00Z",
                    }
                ],
                "page_info": {
                    "has_next_page": True,
                    "has_previous_page": False,
                    "start_cursor": "Y3Vyc29yOjA=",
                    "end_cursor": "Y3Vyc29yOjE5",
                    "total_count": 50,
                },
            }
        }


# ============================================================================
# Catalog Entry DTOs
# ============================================================================


class CatalogEntryResponse(BaseModel):
    """Response model for a detected artifact in the catalog.

    Represents an artifact discovered during repository scanning.
    """

    id: str = Field(
        description="Unique identifier for the catalog entry",
        examples=["cat_abc123"],
    )
    source_id: str = Field(
        description="ID of the source this artifact was detected in",
        examples=["src_anthropics_quickstarts"],
    )
    artifact_type: Literal["skill", "command", "agent", "mcp_server", "hook"] = Field(
        description="Type of artifact detected",
        examples=["skill"],
    )
    name: str = Field(
        description="Artifact name extracted from manifest or inferred",
        examples=["canvas-design"],
    )
    path: str = Field(
        description="Path to artifact within repository",
        examples=["skills/canvas-design"],
    )
    upstream_url: str = Field(
        description="Full URL to artifact in source repository",
        examples=["https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design"],
    )
    detected_version: Optional[str] = Field(
        default=None,
        description="Version extracted from manifest or inferred",
        examples=["1.2.0"],
    )
    detected_sha: Optional[str] = Field(
        default=None,
        description="Git commit SHA at time of detection",
        examples=["abc123def456"],
    )
    detected_at: datetime = Field(
        description="Timestamp when artifact was first detected",
        examples=["2025-12-06T10:30:00Z"],
    )
    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Confidence score of detection (0-100)",
        examples=[95],
    )
    status: Literal["new", "updated", "removed", "imported"] = Field(
        description="Lifecycle status of the catalog entry",
        examples=["new"],
    )
    import_date: Optional[datetime] = Field(
        default=None,
        description="Timestamp when artifact was imported to collection",
    )
    import_id: Optional[str] = Field(
        default=None,
        description="ID of import operation if imported",
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "cat_canvas_design",
                "source_id": "src_anthropics_quickstarts",
                "artifact_type": "skill",
                "name": "canvas-design",
                "path": "skills/canvas-design",
                "upstream_url": "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design",
                "detected_version": "1.2.0",
                "detected_sha": "abc123def456",
                "detected_at": "2025-12-06T10:30:00Z",
                "confidence_score": 95,
                "status": "new",
                "import_date": None,
                "import_id": None,
            }
        }


class CatalogListResponse(BaseModel):
    """Paginated list of catalog entries with statistics.

    Includes aggregated counts by status and artifact type.
    """

    items: List[CatalogEntryResponse] = Field(
        description="List of catalog entries for this page",
    )
    page_info: PageInfo = Field(
        description="Pagination metadata",
    )
    counts_by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of entries by status",
        examples=[{"new": 45, "updated": 12, "imported": 33}],
    )
    counts_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of entries by artifact type",
        examples=[{"skill": 60, "command": 20, "agent": 10}],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "cat_canvas_design",
                        "source_id": "src_anthropics_quickstarts",
                        "artifact_type": "skill",
                        "name": "canvas-design",
                        "path": "skills/canvas-design",
                        "upstream_url": "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design",
                        "confidence_score": 95,
                        "status": "new",
                        "detected_at": "2025-12-06T10:30:00Z",
                    }
                ],
                "page_info": {
                    "has_next_page": True,
                    "has_previous_page": False,
                    "start_cursor": "Y3Vyc29yOjA=",
                    "end_cursor": "Y3Vyc29yOjE5",
                    "total_count": 90,
                },
                "counts_by_status": {"new": 45, "updated": 12, "imported": 33},
                "counts_by_type": {"skill": 60, "command": 20, "agent": 10},
            }
        }


# ============================================================================
# Scan Operation DTOs
# ============================================================================


class ScanRequest(BaseModel):
    """Request to trigger a rescan of a source.

    Allows forcing a rescan even if recently scanned.
    """

    force: bool = Field(
        default=False,
        description="Force rescan even if recently scanned",
        examples=[False],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "force": False,
            }
        }


class ScanResultDTO(BaseModel):
    """Result of scanning a GitHub repository.

    Contains scan statistics, duration, and any errors encountered.
    """

    source_id: str = Field(
        description="ID of the source that was scanned",
        examples=["src_anthropics_quickstarts"],
    )
    status: Literal["success", "error", "partial"] = Field(
        description="Scan result status",
        examples=["success"],
    )
    artifacts_found: int = Field(
        description="Total number of artifacts detected",
        ge=0,
        examples=[12],
    )
    new_count: int = Field(
        description="Number of new artifacts detected",
        ge=0,
        examples=[3],
    )
    updated_count: int = Field(
        description="Number of artifacts with changes detected",
        ge=0,
        examples=[2],
    )
    removed_count: int = Field(
        description="Number of artifacts no longer present",
        ge=0,
        examples=[1],
    )
    unchanged_count: int = Field(
        description="Number of artifacts with no changes",
        ge=0,
        examples=[6],
    )
    scan_duration_ms: float = Field(
        description="Scan duration in milliseconds",
        ge=0,
        examples=[1234.56],
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages encountered during scan",
        examples=[["Failed to parse manifest in skills/broken-skill"]],
    )
    scanned_at: datetime = Field(
        description="Timestamp when scan completed",
        examples=["2025-12-06T10:35:00Z"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "source_id": "src_anthropics_quickstarts",
                "status": "success",
                "artifacts_found": 12,
                "new_count": 3,
                "updated_count": 2,
                "removed_count": 1,
                "unchanged_count": 6,
                "scan_duration_ms": 1234.56,
                "errors": [],
                "scanned_at": "2025-12-06T10:35:00Z",
            }
        }


# ============================================================================
# Import Operation DTOs
# ============================================================================


class ImportRequest(BaseModel):
    """Request to import artifacts from catalog to collection.

    Specifies which entries to import and how to handle conflicts.
    """

    entry_ids: List[str] = Field(
        description="List of catalog entry IDs to import",
        min_length=1,
        examples=[["cat_canvas_design", "cat_another_skill"]],
    )
    conflict_strategy: Literal["skip", "overwrite", "rename"] = Field(
        default="skip",
        description="Strategy for handling conflicts with existing artifacts",
        examples=["skip"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "entry_ids": ["cat_canvas_design", "cat_another_skill"],
                "conflict_strategy": "skip",
            }
        }


class ImportResultDTO(BaseModel):
    """Result of importing artifacts from catalog.

    Contains import statistics and details of any errors.
    """

    imported_count: int = Field(
        description="Number of artifacts successfully imported",
        ge=0,
        examples=[5],
    )
    skipped_count: int = Field(
        description="Number of artifacts skipped due to conflicts or other reasons",
        ge=0,
        examples=[2],
    )
    error_count: int = Field(
        description="Number of artifacts that failed to import",
        ge=0,
        examples=[1],
    )
    imported_ids: List[str] = Field(
        description="List of entry IDs that were successfully imported",
        examples=[["cat_canvas_design", "cat_another_skill"]],
    )
    skipped_ids: List[str] = Field(
        description="List of entry IDs that were skipped",
        examples=[["cat_existing_skill"]],
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of {entry_id, error} for failed imports",
        examples=[[{"entry_id": "cat_broken_skill", "error": "Invalid manifest format"}]],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "imported_count": 5,
                "skipped_count": 2,
                "error_count": 1,
                "imported_ids": ["cat_canvas_design", "cat_another_skill"],
                "skipped_ids": ["cat_existing_skill"],
                "errors": [
                    {"entry_id": "cat_broken_skill", "error": "Invalid manifest format"}
                ],
            }
        }


# ============================================================================
# Detection DTOs (Internal Service Models)
# ============================================================================


class DetectedArtifact(BaseModel):
    """An artifact detected during scanning.

    Internal model used by scanning service, not directly exposed via API.
    """

    artifact_type: str = Field(
        description="Type of artifact detected",
        examples=["skill"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["canvas-design"],
    )
    path: str = Field(
        description="Path to artifact within repository",
        examples=["skills/canvas-design"],
    )
    upstream_url: str = Field(
        description="Full URL to artifact in source repository",
        examples=["https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design"],
    )
    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Confidence score of detection (0-100)",
        examples=[95],
    )
    detected_sha: Optional[str] = Field(
        default=None,
        description="Git commit SHA at time of detection",
        examples=["abc123def456"],
    )
    detected_version: Optional[str] = Field(
        default=None,
        description="Version extracted from manifest",
        examples=["1.2.0"],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata extracted during detection",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_type": "skill",
                "name": "canvas-design",
                "path": "skills/canvas-design",
                "upstream_url": "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design",
                "confidence_score": 95,
                "detected_sha": "abc123def456",
                "detected_version": "1.2.0",
                "metadata": {"description": "Canvas design skill"},
            }
        }


class HeuristicMatch(BaseModel):
    """Result of heuristic matching on a file/directory.

    Internal model used by scanning heuristics, includes score breakdown.
    """

    path: str = Field(
        description="Path that was evaluated",
        examples=["skills/canvas-design"],
    )
    artifact_type: Optional[str] = Field(
        default=None,
        description="Detected artifact type (None if no match)",
        examples=["skill"],
    )
    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Overall confidence score (0-100)",
        examples=[95],
    )
    match_reasons: List[str] = Field(
        default_factory=list,
        description="List of reasons why this path matched",
        examples=[["Directory name matches 'skill' pattern", "Contains skill.xml manifest"]],
    )
    # Scoring breakdown
    dir_name_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Score contribution from directory name",
        examples=[30],
    )
    manifest_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Score contribution from manifest presence/validity",
        examples=[50],
    )
    extension_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Score contribution from file extensions",
        examples=[10],
    )
    depth_penalty: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Score penalty for being too deep in directory tree",
        examples=[5],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "path": "skills/canvas-design",
                "artifact_type": "skill",
                "confidence_score": 95,
                "match_reasons": [
                    "Directory name matches 'skill' pattern",
                    "Contains skill.xml manifest",
                ],
                "dir_name_score": 30,
                "manifest_score": 50,
                "extension_score": 10,
                "depth_penalty": 5,
            }
        }
