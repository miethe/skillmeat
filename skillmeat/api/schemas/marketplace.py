"""Marketplace API schemas.

Provides Pydantic models for marketplace listing feeds, installation requests,
publish operations, and broker information.
"""

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
