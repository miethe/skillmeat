"""Pydantic models for marketplace operations.

This module defines the data structures used for marketplace listings,
queries, publication requests, and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ArtifactCategory(str, Enum):
    """Categories for marketplace artifacts."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    MCP_SERVER = "mcp-server"
    BUNDLE = "bundle"


class ListingSortOrder(str, Enum):
    """Sort order options for marketplace listings."""

    NEWEST = "newest"
    POPULAR = "popular"
    UPDATED = "updated"
    NAME = "name"
    DOWNLOADS = "downloads"


class PublisherInfo(BaseModel):
    """Information about a marketplace publisher."""

    name: str = Field(..., description="Publisher name or organization")
    email: Optional[str] = Field(None, description="Publisher contact email")
    website: Optional[HttpUrl] = Field(None, description="Publisher website")
    verified: bool = Field(False, description="Whether publisher is verified")
    key_fingerprint: Optional[str] = Field(
        None, description="Ed25519 public key fingerprint for signature verification"
    )


class Listing(BaseModel):
    """Marketplace listing for an artifact or bundle.

    Represents a published artifact available for download from a marketplace.
    Includes metadata, pricing, signature, and download information.
    """

    listing_id: str = Field(..., description="Unique listing identifier")
    name: str = Field(..., description="Artifact/bundle name")
    description: str = Field(..., description="Human-readable description")
    category: ArtifactCategory = Field(..., description="Artifact category")
    version: str = Field(..., description="Version string (semver recommended)")
    publisher: PublisherInfo = Field(..., description="Publisher information")
    license: str = Field("MIT", description="License identifier (e.g., MIT, Apache-2.0)")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    artifact_count: int = Field(1, description="Number of artifacts in listing")
    created_at: datetime = Field(..., description="Listing creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    downloads: int = Field(0, description="Total download count")
    price: float = Field(0.0, description="Price (0.0 = free)")
    signature: Optional[str] = Field(
        None, description="Base64-encoded Ed25519 signature"
    )
    source_url: HttpUrl = Field(..., description="Marketplace listing URL")
    bundle_url: HttpUrl = Field(..., description="Bundle download URL")
    homepage: Optional[HttpUrl] = Field(None, description="Project homepage")
    repository: Optional[HttpUrl] = Field(None, description="Source repository URL")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class ListingQuery(BaseModel):
    """Query parameters for searching marketplace listings."""

    search: Optional[str] = Field(None, description="Search query string")
    category: Optional[ArtifactCategory] = Field(
        None, description="Filter by category"
    )
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    publisher: Optional[str] = Field(None, description="Filter by publisher name")
    free_only: bool = Field(False, description="Only show free listings")
    verified_only: bool = Field(False, description="Only show verified publishers")
    sort: ListingSortOrder = Field(
        ListingSortOrder.NEWEST, description="Sort order"
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")

    model_config = ConfigDict(use_enum_values=True)


class ListingPage(BaseModel):
    """Paginated response for marketplace listings."""

    listings: List[Listing] = Field(..., description="List of listings on this page")
    total_count: int = Field(..., description="Total number of matching listings")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PublishRequest(BaseModel):
    """Request to publish an artifact to a marketplace."""

    bundle_path: str = Field(..., description="Path to bundle file")
    name: str = Field(..., description="Listing name")
    description: str = Field(..., description="Listing description")
    category: ArtifactCategory = Field(..., description="Artifact category")
    version: str = Field(..., description="Version string")
    license: str = Field("MIT", description="License identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    homepage: Optional[HttpUrl] = Field(None, description="Project homepage")
    repository: Optional[HttpUrl] = Field(None, description="Source repository")
    price: float = Field(0.0, ge=0.0, description="Price (0.0 = free)")
    sign_bundle: bool = Field(
        True, description="Whether to sign bundle before publishing"
    )
    publisher_key_id: Optional[str] = Field(
        None, description="Key ID to use for signing (default uses active key)"
    )

    model_config = ConfigDict(use_enum_values=True)


class PublishResult(BaseModel):
    """Result of a marketplace publish operation."""

    success: bool = Field(..., description="Whether publish succeeded")
    listing_id: Optional[str] = Field(None, description="Created listing ID")
    listing_url: Optional[HttpUrl] = Field(None, description="Marketplace listing URL")
    message: str = Field(..., description="Result message")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(
        default_factory=list, description="Warning messages if any"
    )


class DownloadResult(BaseModel):
    """Result of downloading a bundle from marketplace."""

    success: bool = Field(..., description="Whether download succeeded")
    bundle_path: Optional[str] = Field(None, description="Path to downloaded bundle")
    listing: Optional[Listing] = Field(None, description="Listing metadata")
    verified: bool = Field(False, description="Whether signature was verified")
    message: str = Field(..., description="Result message")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
