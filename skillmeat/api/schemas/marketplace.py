"""Marketplace API schemas.

Pydantic models for marketplace listing feed API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

from skillmeat.api.schemas.common import PageInfo


class PublisherResponse(BaseModel):
    """Publisher information in API responses."""

    name: str = Field(..., description="Publisher name or organization")
    email: Optional[str] = Field(None, description="Publisher contact email")
    website: Optional[HttpUrl] = Field(None, description="Publisher website")
    verified: bool = Field(False, description="Whether publisher is verified")


class ListingResponse(BaseModel):
    """Marketplace listing in API responses."""

    listing_id: str = Field(..., description="Unique listing identifier")
    name: str = Field(..., description="Artifact/bundle name")
    description: str = Field(..., description="Human-readable description")
    category: str = Field(..., description="Artifact category")
    version: str = Field(..., description="Version string")
    publisher: PublisherResponse = Field(..., description="Publisher information")
    license: str = Field(..., description="License identifier")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    artifact_count: int = Field(..., description="Number of artifacts in listing")
    downloads: int = Field(0, description="Total download count")
    created_at: datetime = Field(..., description="Listing creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    homepage: Optional[HttpUrl] = Field(None, description="Project homepage")
    repository: Optional[HttpUrl] = Field(None, description="Source repository URL")


class ListingDetailResponse(ListingResponse):
    """Detailed marketplace listing with additional metadata."""

    source_url: HttpUrl = Field(..., description="Marketplace listing URL")
    bundle_url: HttpUrl = Field(..., description="Bundle download URL")
    price: float = Field(0.0, description="Price (0.0 = free)")
    signature: Optional[str] = Field(None, description="Bundle signature")


class ListingFeedResponse(BaseModel):
    """Paginated feed of marketplace listings."""

    items: List[ListingResponse] = Field(..., description="List of listings")
    page_info: PageInfo = Field(..., description="Pagination metadata")


class InstallRequest(BaseModel):
    """Request to install a marketplace listing."""

    listing_id: str = Field(..., description="Marketplace listing identifier")
    collection_name: Optional[str] = Field(
        None, description="Target collection name (default: use default collection)"
    )
    verify_signature: bool = Field(
        True, description="Whether to verify bundle signature"
    )


class InstallResponse(BaseModel):
    """Response from marketplace install operation."""

    success: bool = Field(..., description="Whether installation succeeded")
    listing_id: str = Field(..., description="Installed listing ID")
    artifacts_installed: int = Field(..., description="Number of artifacts installed")
    collection_name: str = Field(..., description="Collection name")
    message: str = Field(..., description="Result message")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(
        default_factory=list, description="Warning messages if any"
    )


class PublishBundleRequest(BaseModel):
    """Request to publish a bundle to marketplace."""

    bundle_path: str = Field(..., description="Path to bundle file")
    name: str = Field(..., description="Listing name")
    description: str = Field(..., description="Listing description")
    category: str = Field(..., description="Artifact category")
    version: str = Field(..., description="Version string")
    license: str = Field("MIT", description="License identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    homepage: Optional[HttpUrl] = Field(None, description="Project homepage")
    repository: Optional[HttpUrl] = Field(None, description="Source repository")
    price: float = Field(0.0, ge=0.0, description="Price (0.0 = free)")
    sign_bundle: bool = Field(True, description="Whether to sign bundle")
    publisher_key_id: Optional[str] = Field(
        None, description="Key ID to use for signing"
    )


class PublishBundleResponse(BaseModel):
    """Response from marketplace publish operation."""

    success: bool = Field(..., description="Whether publish succeeded")
    listing_id: Optional[str] = Field(None, description="Created listing ID")
    listing_url: Optional[HttpUrl] = Field(None, description="Marketplace listing URL")
    message: str = Field(..., description="Result message")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(
        default_factory=list, description="Warning messages if any"
    )
