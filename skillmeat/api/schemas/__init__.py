"""API schemas (DTOs) for request and response models.

This module provides Pydantic models for API endpoints, separate from ORM models.
"""

from .common import (
    ErrorResponse,
    PageInfo,
    PaginatedResponse,
    ValidationErrorDetail,
)
from .errors import (
    ErrorDetail,
    ErrorResponse as StandardErrorResponse,
    ErrorCodes,
)
from .collections import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    CollectionListResponse,
    CollectionArtifactsResponse,
)
from .user_collections import (
    UserCollectionCreateRequest,
    UserCollectionResponse,
    UserCollectionUpdateRequest,
    UserCollectionListResponse,
    UserCollectionWithGroupsResponse,
    AddArtifactsRequest,
    GroupSummary,
)
from .artifacts import (
    ArtifactHistoryEventResponse,
    ArtifactHistoryResponse,
    ArtifactResponse,
    ArtifactListResponse,
    ArtifactUpstreamResponse,
)
from .analytics import (
    AnalyticsSummaryResponse,
    AnalyticsEventItem,
    AnalyticsEventsResponse,
    ArtifactHistorySummary,
    EnterpriseAdoptionMetrics,
    EnterpriseAnalyticsSummaryResponse,
    EnterpriseDeliveryMetrics,
    EnterpriseMetricWindow,
    EnterpriseReliabilityMetrics,
    ProjectActivityItem,
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
from .context_entity import (
    ContextEntityType,
    ContextEntityCreateRequest,
    ContextEntityUpdateRequest,
    ContextEntityResponse,
    ContextEntityListResponse,
)
from .context_sync import (
    SyncPullRequest,
    SyncPushRequest,
    SyncConflictResponse,
    SyncResultResponse,
    SyncStatusResponse,
    SyncResolveRequest,
)
from .project_template import (
    TemplateEntitySchema,
    ProjectTemplateBase,
    ProjectTemplateCreateRequest,
    ProjectTemplateUpdateRequest,
    ProjectTemplateResponse,
    ProjectTemplateListResponse,
    TemplateVariableValue,
    DeployTemplateRequest,
    DeployTemplateResponse,
)
from .version import (
    SnapshotResponse,
    SnapshotListResponse,
    SnapshotCreateRequest,
    SnapshotCreateResponse,
    ConflictMetadataResponse,
    RollbackSafetyAnalysisResponse,
    RollbackRequest,
    RollbackResponse,
    VersionDiffRequest,
    VersionDiffResponse,
)
from .merge import (
    MergeAnalyzeRequest,
    MergeSafetyResponse,
    MergePreviewRequest,
    MergePreviewResponse,
    MergeExecuteRequest,
    MergeExecuteResponse,
    ConflictResolveRequest,
    ConflictResolveResponse,
)
from .drift import (
    DriftDetectionResponse,
    DriftSummaryResponse,
)
from .tags import (
    TagBase,
    TagCreateRequest,
    TagUpdateRequest,
    TagResponse,
    TagListResponse,
    ArtifactTagRequest,
)
from .match import (
    ScoreBreakdown,
    MatchedArtifact,
    MatchResponse,
)
from .memory import (
    MemoryType,
    MemoryStatus,
    MemoryItemCreateRequest,
    MemoryItemUpdateRequest,
    MemoryItemResponse,
    MemoryItemListResponse,
    PromoteRequest,
    DeprecateRequest,
    BulkPromoteRequest,
    BulkDeprecateRequest,
    BulkActionResponse,
    MergeRequest as MemoryMergeRequest,
    MergeResponse as MemoryMergeResponse,
)
from .context_module import (
    ContextModuleCreateRequest,
    ContextModuleUpdateRequest,
    ContextModuleResponse,
    ContextModuleListResponse,
    AddMemoryToModuleRequest,
    ContextPackPreviewRequest,
    ContextPackPreviewResponse,
    ContextPackGenerateRequest,
    ContextPackGenerateResponse,
)
from .deployment_profiles import (
    DeploymentProfileCreate,
    DeploymentProfileRead,
    DeploymentProfileUpdate,
)

__all__ = [
    # Common
    "ErrorResponse",
    "PageInfo",
    "PaginatedResponse",
    "ValidationErrorDetail",
    # Error handling
    "ErrorDetail",
    "StandardErrorResponse",
    "ErrorCodes",
    # Collections
    "CollectionCreateRequest",
    "CollectionResponse",
    "CollectionUpdateRequest",
    "CollectionListResponse",
    "CollectionArtifactsResponse",
    # User Collections
    "UserCollectionCreateRequest",
    "UserCollectionResponse",
    "UserCollectionUpdateRequest",
    "UserCollectionListResponse",
    "UserCollectionWithGroupsResponse",
    "AddArtifactsRequest",
    "GroupSummary",
    # Artifacts
    "ArtifactResponse",
    "ArtifactListResponse",
    "ArtifactUpstreamResponse",
    "ArtifactHistoryEventResponse",
    "ArtifactHistoryResponse",
    # Analytics
    "AnalyticsSummaryResponse",
    "AnalyticsEventItem",
    "AnalyticsEventsResponse",
    "ArtifactHistorySummary",
    "EnterpriseAdoptionMetrics",
    "EnterpriseAnalyticsSummaryResponse",
    "EnterpriseDeliveryMetrics",
    "EnterpriseMetricWindow",
    "EnterpriseReliabilityMetrics",
    "ProjectActivityItem",
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
    # Context Entities
    "ContextEntityType",
    "ContextEntityCreateRequest",
    "ContextEntityUpdateRequest",
    "ContextEntityResponse",
    "ContextEntityListResponse",
    # Context Sync
    "SyncPullRequest",
    "SyncPushRequest",
    "SyncConflictResponse",
    "SyncResultResponse",
    "SyncStatusResponse",
    "SyncResolveRequest",
    # Project Templates
    "TemplateEntitySchema",
    "ProjectTemplateBase",
    "ProjectTemplateCreateRequest",
    "ProjectTemplateUpdateRequest",
    "ProjectTemplateResponse",
    "ProjectTemplateListResponse",
    "TemplateVariableValue",
    "DeployTemplateRequest",
    "DeployTemplateResponse",
    # Version Management
    "SnapshotResponse",
    "SnapshotListResponse",
    "SnapshotCreateRequest",
    "SnapshotCreateResponse",
    "ConflictMetadataResponse",
    "RollbackSafetyAnalysisResponse",
    "RollbackRequest",
    "RollbackResponse",
    "VersionDiffRequest",
    "VersionDiffResponse",
    # Merge Operations
    "MergeAnalyzeRequest",
    "MergeSafetyResponse",
    "MergePreviewRequest",
    "MergePreviewResponse",
    "MergeExecuteRequest",
    "MergeExecuteResponse",
    "ConflictResolveRequest",
    "ConflictResolveResponse",
    # Drift Detection
    "DriftDetectionResponse",
    "DriftSummaryResponse",
    # Tags
    "TagBase",
    "TagCreateRequest",
    "TagUpdateRequest",
    "TagResponse",
    "TagListResponse",
    "ArtifactTagRequest",
    # Match
    "ScoreBreakdown",
    "MatchedArtifact",
    "MatchResponse",
    # Memory Items
    "MemoryType",
    "MemoryStatus",
    "MemoryItemCreateRequest",
    "MemoryItemUpdateRequest",
    "MemoryItemResponse",
    "MemoryItemListResponse",
    "PromoteRequest",
    "DeprecateRequest",
    "BulkPromoteRequest",
    "BulkDeprecateRequest",
    "BulkActionResponse",
    "MemoryMergeRequest",
    "MemoryMergeResponse",
    # Context Modules
    "ContextModuleCreateRequest",
    "ContextModuleUpdateRequest",
    "ContextModuleResponse",
    "ContextModuleListResponse",
    "AddMemoryToModuleRequest",
    # Context Packing
    "ContextPackPreviewRequest",
    "ContextPackPreviewResponse",
    "ContextPackGenerateRequest",
    "ContextPackGenerateResponse",
    # Deployment Profiles
    "DeploymentProfileCreate",
    "DeploymentProfileRead",
    "DeploymentProfileUpdate",
]
