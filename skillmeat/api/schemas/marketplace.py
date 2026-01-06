"""Marketplace API schemas.

Provides Pydantic models for marketplace listing feeds, installation requests,
publish operations, and broker information.
"""

import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .common import PageInfo

# Allowed artifact types for validation
ALLOWED_ARTIFACT_TYPES = {"skill", "command", "agent", "mcp_server", "hook"}


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
    description: Optional[str] = Field(
        default=None,
        description="User-provided description for this source (max 500 chars)",
        max_length=500,
        examples=["My company's internal skills repository"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Internal notes/documentation for this source (max 2000 chars)",
        max_length=2000,
        examples=["Contact: team@example.com for access issues"],
    )
    enable_frontmatter_detection: bool = Field(
        default=False,
        description="Enable parsing markdown frontmatter for artifact type hints",
    )

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str | None) -> str | None:
        """Validate description length.

        Args:
            v: Description value to validate

        Returns:
            Validated description

        Raises:
            ValueError: If description exceeds 500 characters
        """
        if v is not None and len(v) > 500:
            raise ValueError("Description must be 500 characters or less")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes_length(cls, v: str | None) -> str | None:
        """Validate notes length.

        Args:
            v: Notes value to validate

        Returns:
            Validated notes

        Raises:
            ValueError: If notes exceed 2000 characters
        """
        if v is not None and len(v) > 2000:
            raise ValueError("Notes must be 2000 characters or less")
        return v

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
                "description": "Anthropic's official quickstart examples",
                "notes": "Contains high-quality reference implementations",
            }
        }


class InferUrlRequest(BaseModel):
    """Request to infer GitHub source structure from a full URL.

    Supports parsing GitHub URLs to extract repository, ref, and subdirectory.
    """

    url: str = Field(
        description="GitHub URL to parse (full URL with branch/path or basic repo URL)",
        examples=[
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo/tree/main/path/to/dir",
        ],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "url": "https://github.com/davila7/claude-code-templates/tree/main/cli-tool/components"
            }
        }


class InferUrlResponse(BaseModel):
    """Response containing inferred GitHub source structure.

    Returns parsed components or error message if parsing failed.
    """

    success: bool = Field(
        description="Whether URL was successfully parsed",
        examples=[True],
    )
    repo_url: Optional[str] = Field(
        default=None,
        description="Base repository URL (e.g., https://github.com/owner/repo)",
        examples=["https://github.com/owner/repo"],
    )
    ref: Optional[str] = Field(
        default=None,
        description="Branch, tag, or SHA extracted from URL (defaults to 'main' if not specified)",
        examples=["main", "v1.0.0", "abc123"],
    )
    root_hint: Optional[str] = Field(
        default=None,
        description="Subdirectory path within repository (None if URL points to repo root)",
        examples=["cli-tool/components", "skills"],
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if parsing failed (None on success)",
        examples=["Invalid GitHub URL format"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "repo_url": "https://github.com/davila7/claude-code-templates",
                "ref": "main",
                "root_hint": "cli-tool/components",
                "error": None,
            }
        }


class UpdateSourceRequest(BaseModel):
    """Request to update a GitHub repository source.

    All fields are optional - only provided fields will be updated.
    Uses PATCH semantics for partial updates.
    """

    ref: Optional[str] = Field(
        default=None,
        description="Branch, tag, or SHA to scan",
        examples=["main", "v1.0.0", "abc123"],
    )
    root_hint: Optional[str] = Field(
        default=None,
        description="Subdirectory path within repository to start scanning",
        examples=["skills", "src/artifacts"],
    )
    manual_map: Optional[Dict[str, str]] = Field(
        default=None,
        description='Manual directory-to-type mappings (directory path → artifact_type). '
        'Example: {"path/to/dir": "skill", "other/path": "command"}',
        examples=[{"skills/python": "skill", "commands/dev": "command"}],
    )
    trust_level: Optional[Literal["untrusted", "basic", "verified", "official"]] = (
        Field(
            default=None,
            description="Trust level for artifacts from this source",
        )
    )
    description: Optional[str] = Field(
        default=None,
        description="User-provided description for this source (max 500 chars)",
        max_length=500,
        examples=["Official Anthropic skills repository"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Internal notes/documentation for this source (max 2000 chars)",
        max_length=2000,
        examples=["Contains verified skills. Contact: team@example.com"],
    )
    enable_frontmatter_detection: Optional[bool] = Field(
        default=None,
        description="Enable parsing markdown frontmatter for artifact type hints",
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

    @field_validator("manual_map")
    @classmethod
    def validate_manual_map_types(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Validate artifact types in manual_map.

        Args:
            v: Manual map dictionary to validate

        Returns:
            Validated manual map

        Raises:
            ValueError: If any artifact type is invalid
        """
        if v is None:
            return v

        for path, artifact_type in v.items():
            if artifact_type not in ALLOWED_ARTIFACT_TYPES:
                allowed_types = ", ".join(sorted(ALLOWED_ARTIFACT_TYPES))
                raise ValueError(
                    f"Invalid artifact type: {artifact_type}. Allowed: {allowed_types}"
                )

        return v

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str | None) -> str | None:
        """Validate description does not exceed maximum length.

        Args:
            v: Description value to validate

        Returns:
            Validated description

        Raises:
            ValueError: If description exceeds 500 characters
        """
        if v is not None and len(v) > 500:
            raise ValueError("Description must be 500 characters or less")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes_length(cls, v: str | None) -> str | None:
        """Validate notes do not exceed maximum length.

        Args:
            v: Notes value to validate

        Returns:
            Validated notes

        Raises:
            ValueError: If notes exceed 2000 characters
        """
        if v is not None and len(v) > 2000:
            raise ValueError("Notes must be 2000 characters or less")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "ref": "v2.0.0",
                "description": "Updated description for repository",
                "notes": "Updated internal notes about this source",
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
    description: Optional[str] = Field(
        default=None,
        description="User-provided description for this source",
        max_length=500,
        examples=["Official Anthropic skills repository"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Internal notes/documentation for this source",
        max_length=2000,
        examples=["Contains verified skills from Anthropic team. Updated weekly."],
    )
    enable_frontmatter_detection: bool = Field(
        description="Whether frontmatter detection is enabled for this source",
    )
    manual_map: Optional[Dict[str, str]] = Field(
        default=None,
        description="Manual directory-to-type mappings (directory path → artifact_type). "
        "None if no manual mapping configured.",
        examples=[{"skills/python": "skill", "commands/dev": "command"}],
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
                "description": "Official skills repository",
                "notes": "Contains verified skills from Anthropic",
                "manual_map": None,
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
        examples=[
            "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design"
        ],
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
    raw_score: Optional[int] = Field(
        default=None,
        description="Raw score before normalization (0-120 typical)",
        examples=[60],
    )
    score_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Detailed signal breakdown: dir_name_score (0-10), manifest_score (0-20), "
        "extensions_score (0-5), parent_hint_score (0-15), frontmatter_score (0-15), "
        "depth_penalty (negative), raw_total, normalized_score (0-100)",
        examples=[
            {
                "dir_name_score": 10,
                "manifest_score": 20,
                "extensions_score": 5,
                "parent_hint_score": 15,
                "frontmatter_score": 15,
                "depth_penalty": -5,
                "raw_total": 60,
                "normalized_score": 92,
            }
        ],
    )
    status: Literal["new", "updated", "removed", "imported", "excluded"] = Field(
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
    excluded_at: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp when artifact was marked as excluded from catalog. "
        "Null if not excluded.",
        examples=["2025-12-07T14:30:00Z", None],
    )
    excluded_reason: Optional[str] = Field(
        default=None,
        description="User-provided reason for exclusion (max 500 chars). "
        "Null if not excluded or no reason provided.",
        max_length=500,
        examples=[
            "Not a valid skill - documentation only",
            "False positive detection",
            "Duplicate artifact",
        ],
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
                "raw_score": 60,
                "score_breakdown": {
                    "dir_name_score": 10,
                    "manifest_score": 20,
                    "extensions_score": 5,
                    "parent_hint_score": 15,
                    "frontmatter_score": 15,
                    "depth_penalty": -5,
                    "raw_total": 60,
                    "normalized_score": 92,
                },
                "status": "new",
                "import_date": None,
                "import_id": None,
                "excluded_at": None,
                "excluded_reason": None,
            }
        }


class UpdateCatalogEntryNameRequest(BaseModel):
    """Request body for updating the display name of a catalog entry."""

    name: str = Field(
        description="Updated artifact name to use for display and import",
        min_length=1,
        max_length=100,
        examples=["custom-skill-name"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "custom-skill-name",
            }
        }


class ExcludeArtifactRequest(BaseModel):
    """Request body for excluding or restoring a catalog entry.

    Used to mark artifacts as excluded from the catalog (e.g., false positives,
    documentation files, non-Claude artifacts) or to restore previously excluded
    entries.

    When `excluded=True`: Marks the entry as excluded with optional reason.
    Excluded artifacts are hidden from default catalog views but can be restored.

    When `excluded=False`: Removes exclusion status and restores entry to default
    view (status changes to "new" or "imported" depending on history).

    Both operations are idempotent - calling multiple times succeeds.
    """

    excluded: bool = Field(
        description="True to mark as excluded, False to restore",
        examples=[True, False],
    )
    reason: Optional[str] = Field(
        default=None,
        description="User-provided reason for exclusion (max 500 chars, optional)",
        max_length=500,
        examples=[
            "Not a valid artifact - documentation file",
            "False positive detection",
            "Not a Claude artifact",
        ],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "excluded": True,
                "reason": "This is a documentation file, not an actual skill",
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
        examples=[{"new": 45, "updated": 12, "imported": 33, "excluded": 5}],
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
                        "raw_score": 60,
                        "score_breakdown": {
                            "dir_name_score": 10,
                            "manifest_score": 20,
                            "extensions_score": 5,
                            "parent_hint_score": 15,
                            "frontmatter_score": 15,
                            "depth_penalty": -5,
                            "raw_total": 60,
                            "normalized_score": 92,
                        },
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
                "counts_by_status": {"new": 45, "updated": 12, "imported": 33, "excluded": 5},
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
    artifacts: List["DetectedArtifact"] = Field(
        default_factory=list,
        description="List of detected artifacts",
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
    duplicates_within_source: int = Field(
        default=0,
        description="Number of duplicate artifacts detected within this source and "
        "excluded from catalog. These are artifacts with identical content (same SHA256 "
        "hash) found multiple times in the same repository scan.",
        ge=0,
        examples=[2],
    )
    duplicates_cross_source: int = Field(
        default=0,
        description="Number of duplicate artifacts detected that already exist in the "
        "collection (from other sources or previous scans) and excluded from catalog. "
        "These are artifacts matching existing collection entries by content hash.",
        ge=0,
        examples=[3],
    )
    total_detected: int = Field(
        default=0,
        description="Total number of artifacts initially detected before deduplication. "
        "Equals: total_unique + duplicates_within_source + duplicates_cross_source",
        ge=0,
        examples=[15],
    )
    total_unique: int = Field(
        default=0,
        description="Number of unique artifacts after deduplication that were added to "
        "the catalog. These are new artifacts not previously seen in this source or the "
        "existing collection.",
        ge=0,
        examples=[10],
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

    @model_validator(mode="after")
    def validate_dedup_counts(self) -> "ScanResultDTO":
        """Validate that deduplication counts add up correctly.

        The relationship should be:
        total_detected = total_unique + duplicates_within_source + duplicates_cross_source

        Returns:
            Validated model instance

        Raises:
            ValueError: If counts don't add up correctly
        """
        expected = (
            self.total_unique
            + self.duplicates_within_source
            + self.duplicates_cross_source
        )

        if self.total_detected != expected:
            raise ValueError(
                f"Deduplication counts mismatch: total_detected={self.total_detected}, but "
                f"total_unique ({self.total_unique}) + duplicates_within_source "
                f"({self.duplicates_within_source}) + duplicates_cross_source "
                f"({self.duplicates_cross_source}) = {expected}"
            )

        return self

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
                "duplicates_within_source": 2,
                "duplicates_cross_source": 3,
                "total_detected": 15,
                "total_unique": 10,
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
        examples=[
            [{"entry_id": "cat_broken_skill", "error": "Invalid manifest format"}]
        ],
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
        examples=[
            "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design"
        ],
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
    raw_score: Optional[int] = Field(
        default=None,
        description="Raw unscaled confidence score before normalization (0-120 typical)",
    )
    score_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Detailed breakdown of heuristic signal scores",
    )
    # Deduplication fields (added by DeduplicationEngine)
    excluded: Optional[bool] = Field(
        default=None,
        description="Whether this artifact was excluded during deduplication",
    )
    excluded_reason: Optional[str] = Field(
        default=None,
        description="Reason for exclusion (e.g., 'within_source_duplicate', 'cross_source_duplicate')",
    )
    excluded_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when artifact was marked as excluded",
    )
    duplicate_of: Optional[str] = Field(
        default=None,
        description="Path of the artifact this is a duplicate of (for within-source duplicates)",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA256 content hash of artifact files (for deduplication)",
    )
    status: Optional[str] = Field(
        default=None,
        description="Artifact status (e.g., 'new', 'excluded')",
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
    organization_path: Optional[str] = Field(
        default=None,
        description="Path segments between container directory and artifact",
        examples=["dev", "ui-ux", "dev/subgroup"],
    )
    match_reasons: List[str] = Field(
        default_factory=list,
        description="List of reasons why this path matched",
        examples=[
            ["Directory name matches 'skill' pattern", "Contains skill.xml manifest"]
        ],
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
    raw_score: int = Field(
        default=0,
        ge=0,
        le=150,  # Higher limit to accommodate container_hint + frontmatter_type signals
        description="Raw score before normalization (0-120 typical)",
        examples=[60],
    )
    breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Detailed signal breakdown dictionary",
        examples=[
            {
                "dir_name_score": 10,
                "manifest_score": 20,
                "extensions_score": 5,
                "parent_hint_score": 15,
                "frontmatter_score": 15,
                "depth_penalty": 5,
                "raw_total": 60,
                "normalized_score": 92,
            }
        ],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the match, including manual mapping info",
        examples=[{"is_manual_mapping": True, "match_type": "exact"}],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "path": "commands/dev/execute-phase",
                "artifact_type": "command",
                "confidence_score": 95,
                "organization_path": "dev",
                "match_reasons": [
                    "Directory name matches 'command' pattern",
                    "Contains COMMAND.md manifest",
                ],
                "dir_name_score": 30,
                "manifest_score": 50,
                "extension_score": 10,
                "depth_penalty": 5,
                "raw_score": 60,
                "breakdown": {
                    "dir_name_score": 10,
                    "manifest_score": 20,
                    "extensions_score": 5,
                    "parent_hint_score": 15,
                    "frontmatter_score": 15,
                    "depth_penalty": 5,
                    "raw_total": 60,
                    "normalized_score": 92,
                },
            }
        }


# ============================================================================
# File Tree DTOs
# ============================================================================


class FileTreeEntry(BaseModel):
    """A single entry in a file tree (file or directory).

    Represents a file or directory from the GitHub repository tree,
    used for browsing artifact file structures in the catalog modal.
    """

    path: str = Field(
        description="File path relative to artifact root",
        examples=["README.md", "src/main.py"],
    )
    type: Literal["file", "tree"] = Field(
        description="Entry type: 'file' for files, 'tree' for directories",
        examples=["file"],
    )
    size: Optional[int] = Field(
        default=None,
        description="File size in bytes (only for blobs/files)",
        ge=0,
        examples=[1024],
    )
    sha: str = Field(
        description="Git SHA for the blob or tree",
        examples=["abc123def456789"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "path": "SKILL.md",
                "type": "file",
                "size": 2048,
                "sha": "abc123def456789",
            }
        }


class FileTreeResponse(BaseModel):
    """Response containing file tree entries for an artifact.

    Returns the list of files and directories within a marketplace
    artifact, used for file browsing in the catalog entry modal.
    """

    entries: List[FileTreeEntry] = Field(
        description="List of file and directory entries",
    )
    artifact_path: str = Field(
        description="Path to artifact within repository",
        examples=["skills/canvas-design"],
    )
    source_id: str = Field(
        description="Marketplace source ID",
        examples=["src_abc123"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "entries": [
                    {
                        "path": "SKILL.md",
                        "type": "blob",
                        "size": 2048,
                        "sha": "abc123def456",
                    },
                    {
                        "path": "src",
                        "type": "tree",
                        "size": None,
                        "sha": "def789abc123",
                    },
                ],
                "artifact_path": "skills/canvas-design",
                "source_id": "src_anthropics_quickstarts",
            }
        }


# ============================================================================
# File Content DTOs
# ============================================================================


class FileContentResponse(BaseModel):
    """Response model for file content from a marketplace artifact.

    Contains the file content along with metadata for rendering in the UI.
    Binary files will have base64-encoded content with is_binary=True.
    Large files (>1MB) are truncated to 10,000 lines with truncated=True.
    """

    content: str = Field(
        description="File content (text or base64-encoded for binary files)",
        examples=["# My Skill\n\nThis is a sample skill..."],
    )
    encoding: str = Field(
        description="Content encoding: 'none' for text, 'base64' for binary",
        examples=["none", "base64"],
    )
    size: int = Field(
        description="File size in bytes (may be truncated size if truncated=True)",
        ge=0,
        examples=[1024],
    )
    sha: str = Field(
        description="Git blob SHA",
        examples=["abc123def456789..."],
    )
    name: str = Field(
        description="File name",
        examples=["SKILL.md"],
    )
    path: str = Field(
        description="Full path within repository",
        examples=["skills/canvas/SKILL.md"],
    )
    is_binary: bool = Field(
        description="Whether the file is binary (content is base64)",
        examples=[False],
    )
    artifact_path: str = Field(
        description="Path to the artifact this file belongs to",
        examples=["skills/canvas"],
    )
    source_id: str = Field(
        description="ID of the marketplace source",
        examples=["src_abc123"],
    )
    truncated: bool = Field(
        default=False,
        description="Whether the content was truncated due to size (>1MB)",
        examples=[False],
    )
    original_size: Optional[int] = Field(
        default=None,
        description="Original file size in bytes (only set when truncated=True)",
        ge=0,
        examples=[2097152],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "content": "# Canvas Design Skill\n\nA skill for designing...",
                "encoding": "none",
                "size": 2048,
                "sha": "abc123def456789abcdef0123456789abcdef01",
                "name": "SKILL.md",
                "path": "skills/canvas/SKILL.md",
                "is_binary": False,
                "artifact_path": "skills/canvas",
                "source_id": "src_anthropics_quickstarts",
                "truncated": False,
                "original_size": None,
            }
        }


# ============================================================================
# Path Tag Extraction DTOs
# ============================================================================


class ExtractedSegmentResponse(BaseModel):
    """Single extracted path segment with approval status.

    Represents a single segment from an artifact path with its normalized
    value and approval/rejection status for tag creation.
    """

    segment: str = Field(
        description="Original segment from path",
        examples=["canvas-design", "UI-UX", "test_utils"],
    )
    normalized: str = Field(
        description="Normalized segment value",
        examples=["canvas-design", "ui-ux", "test-utils"],
    )
    status: Literal["pending", "approved", "rejected", "excluded"] = Field(
        description="Approval status",
        examples=["pending"],
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason if excluded",
        examples=["Excluded: too generic"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "segment": "canvas-design",
                "normalized": "canvas-design",
                "status": "pending",
                "reason": None,
            }
        }


class PathSegmentsResponse(BaseModel):
    """All path segments for a catalog entry.

    Contains the full path and all extracted segments with their approval
    status for tag management.
    """

    entry_id: str = Field(
        description="Catalog entry ID",
        examples=["cat_canvas_design"],
    )
    raw_path: str = Field(
        description="Full artifact path",
        examples=["skills/ui-ux/canvas-design"],
    )
    extracted: list[ExtractedSegmentResponse] = Field(
        description="Extracted segments with status",
    )
    extracted_at: datetime = Field(
        description="Extraction timestamp",
        examples=["2025-12-07T14:30:00Z"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "entry_id": "cat_canvas_design",
                "raw_path": "skills/ui-ux/canvas-design",
                "extracted": [
                    {
                        "segment": "ui-ux",
                        "normalized": "ui-ux",
                        "status": "pending",
                        "reason": None,
                    },
                    {
                        "segment": "canvas-design",
                        "normalized": "canvas-design",
                        "status": "pending",
                        "reason": None,
                    },
                ],
                "extracted_at": "2025-12-07T14:30:00Z",
            }
        }


class UpdateSegmentStatusRequest(BaseModel):
    """Request to update a segment's approval status.

    Used to approve or reject a path segment for tag creation.
    """

    segment: str = Field(
        description="Original segment value to update",
        min_length=1,
        examples=["ui-ux", "canvas-design"],
    )
    status: Literal["approved", "rejected"] = Field(
        description="New status (approved or rejected)",
        examples=["approved"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "segment": "ui-ux",
                "status": "approved",
            }
        }


class UpdateSegmentStatusResponse(BaseModel):
    """Response after updating segment status.

    Returns the updated entry with all segments and their new statuses.
    """

    entry_id: str = Field(
        description="Catalog entry ID",
        examples=["cat_canvas_design"],
    )
    raw_path: str = Field(
        description="Full artifact path",
        examples=["skills/ui-ux/canvas-design"],
    )
    extracted: list[ExtractedSegmentResponse] = Field(
        description="Updated segments with status",
    )
    updated_at: datetime = Field(
        description="Update timestamp",
        examples=["2025-12-07T15:00:00Z"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "entry_id": "cat_canvas_design",
                "raw_path": "skills/ui-ux/canvas-design",
                "extracted": [
                    {
                        "segment": "ui-ux",
                        "normalized": "ui-ux",
                        "status": "approved",
                        "reason": None,
                    },
                    {
                        "segment": "canvas-design",
                        "normalized": "canvas-design",
                        "status": "pending",
                        "reason": None,
                    },
                ],
                "updated_at": "2025-12-07T15:00:00Z",
            }
        }


# ============================================================================
# Manual Mapping and Deduplication DTOs (Phase 1-3)
# ============================================================================


class ManualMapEntry(BaseModel):
    """Single directory to artifact type mapping.

    Used for manual override of artifact type detection in GitHub repositories.
    Validates that both directory path and artifact type are valid.
    """

    directory_path: str = Field(
        description="Unix-style path like 'skills/python' (no leading/trailing slashes)",
        examples=["skills/python", "commands/dev", "agents/research"],
    )
    artifact_type: Literal["skill", "command", "agent", "mcp_server", "hook"] = Field(
        description="Artifact type for this directory",
        examples=["skill"],
    )

    @field_validator("directory_path")
    @classmethod
    def validate_directory_path(cls, v: str) -> str:
        """Validate directory path format.

        Args:
            v: Directory path value

        Returns:
            Normalized directory path

        Raises:
            ValueError: If path format is invalid
        """
        if not v or not v.strip():
            raise ValueError("directory_path cannot be empty")

        # Normalize: strip leading/trailing slashes
        normalized = v.strip().strip("/")

        # Block absolute paths
        if normalized.startswith("/"):
            raise ValueError("directory_path must be a relative path (no leading /)")

        # Block path traversal
        if ".." in normalized:
            raise ValueError(
                "directory_path cannot contain parent directory references (..)"
            )

        # Block double slashes
        if "//" in normalized:
            raise ValueError("directory_path cannot contain double slashes (//)")

        return normalized

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "directory_path": "skills/python",
                "artifact_type": "skill",
            }
        }


class ManualMapRequest(BaseModel):
    """Request to set manual directory mappings for a source.

    Allows overriding automatic artifact type detection by mapping
    specific directory paths to artifact types.
    """

    manual_map: Dict[str, str] = Field(
        description="Mapping of directory paths to artifact types",
        examples=[
            {
                "skills/python": "skill",
                "commands": "command",
                "agents/research": "agent",
            }
        ],
    )

    @field_validator("manual_map")
    @classmethod
    def validate_manual_map(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate manual_map structure and values.

        Args:
            v: Manual map dictionary to validate

        Returns:
            Validated and normalized manual map

        Raises:
            ValueError: If map contains invalid paths or types
        """
        valid_types = {"skill", "command", "agent", "mcp_server", "hook"}
        normalized = {}

        for path, artifact_type in v.items():
            # Validate path
            if not path or not path.strip():
                raise ValueError("Directory paths cannot be empty")

            # Normalize path (strip leading/trailing slashes)
            normalized_path = path.strip().strip("/")

            # Block absolute paths
            if normalized_path.startswith("/"):
                raise ValueError(
                    f"Path '{path}' must be relative (no leading /)"
                )

            # Block path traversal
            if ".." in normalized_path:
                raise ValueError(
                    f"Path '{path}' cannot contain parent directory references (..)"
                )

            # Block double slashes
            if "//" in normalized_path:
                raise ValueError(
                    f"Path '{path}' cannot contain double slashes (//)"
                )

            # Validate artifact type
            if artifact_type not in valid_types:
                raise ValueError(
                    f"Invalid artifact type '{artifact_type}' for path '{path}'. "
                    f"Must be one of: {', '.join(sorted(valid_types))}"
                )

            normalized[normalized_path] = artifact_type

        return normalized

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "manual_map": {
                    "skills/python": "skill",
                    "commands": "command",
                    "agents/research": "agent",
                }
            }
        }


class DeduplicationStats(BaseModel):
    """Statistics from deduplication process.

    Tracks how many artifacts were excluded as duplicates during
    repository scanning, both within the source and across sources.
    """

    duplicates_within_source: int = Field(
        default=0,
        ge=0,
        description="Number of duplicates found within this source",
        examples=[3],
    )
    cross_source_duplicates: int = Field(
        default=0,
        ge=0,
        description="Number of duplicates matching other sources/collection",
        examples=[5],
    )
    total_excluded: int = Field(
        default=0,
        ge=0,
        description="Total artifacts excluded as duplicates",
        examples=[8],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "duplicates_within_source": 3,
                "cross_source_duplicates": 5,
                "total_excluded": 8,
            }
        }


# Rebuild models to resolve forward references
ScanResultDTO.model_rebuild()
