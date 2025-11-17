"""API schemas (DTOs) for request and response models.

This module provides Pydantic models for API endpoints, separate from ORM models.
"""

from .common import (
    ErrorResponse,
    PageInfo,
    PaginatedResponse,
    ValidationErrorDetail,
)
from .collections import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    CollectionListResponse,
    CollectionArtifactsResponse,
)
from .artifacts import (
    ArtifactResponse,
    ArtifactListResponse,
    ArtifactUpstreamResponse,
)
from .analytics import (
    AnalyticsSummaryResponse,
    TopArtifactItem,
    TopArtifactsResponse,
    TrendDataPoint,
    TrendsResponse,
)
from .marketplace import (
    ListingResponse,
    ListingDetailResponse,
    ListingsPageResponse,
    InstallRequest,
    InstallResponse,
    PublishRequest,
    PublishResponse,
    BrokerInfo,
    BrokerListResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    "PageInfo",
    "PaginatedResponse",
    "ValidationErrorDetail",
    # Collections
    "CollectionCreateRequest",
    "CollectionResponse",
    "CollectionUpdateRequest",
    "CollectionListResponse",
    "CollectionArtifactsResponse",
    # Artifacts
    "ArtifactResponse",
    "ArtifactListResponse",
    "ArtifactUpstreamResponse",
    # Analytics
    "AnalyticsSummaryResponse",
    "TopArtifactItem",
    "TopArtifactsResponse",
    "TrendDataPoint",
    "TrendsResponse",
    # Marketplace
    "ListingResponse",
    "ListingDetailResponse",
    "ListingsPageResponse",
    "InstallRequest",
    "InstallResponse",
    "PublishRequest",
    "PublishResponse",
    "BrokerInfo",
    "BrokerListResponse",
]
