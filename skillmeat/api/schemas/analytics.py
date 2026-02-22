"""Analytics API schemas for statistics and usage data."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import PaginatedResponse


class AnalyticsSummaryResponse(BaseModel):
    """Overall analytics summary.

    Provides high-level statistics about the collection and usage patterns.
    """

    total_collections: int = Field(
        description="Total number of collections",
        examples=[1],
    )
    total_artifacts: int = Field(
        description="Total number of artifacts across all collections",
        examples=[15],
    )
    total_deployments: int = Field(
        description="Total number of deployments",
        examples=[42],
    )
    total_events: int = Field(
        description="Total number of tracked events",
        examples=[1337],
    )
    artifacts_by_type: Dict[str, int] = Field(
        description="Count of artifacts by type",
        examples=[{"skill": 10, "command": 3, "agent": 2}],
    )
    recent_activity_count: int = Field(
        description="Number of events in the last 24 hours",
        examples=[23],
    )
    most_deployed_artifact: str = Field(
        description="Name of the most frequently deployed artifact",
        examples=["pdf-skill"],
    )
    last_activity: datetime = Field(
        description="Timestamp of most recent activity",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "total_collections": 1,
                "total_artifacts": 15,
                "total_deployments": 42,
                "total_events": 1337,
                "artifacts_by_type": {"skill": 10, "command": 3, "agent": 2},
                "recent_activity_count": 23,
                "most_deployed_artifact": "pdf-skill",
                "last_activity": "2024-11-16T15:30:00Z",
            }
        }


class TopArtifactItem(BaseModel):
    """Single artifact in the top artifacts list.

    Represents an artifact with its usage statistics.
    """

    artifact_name: str = Field(
        description="Artifact name",
        examples=["pdf-skill"],
    )
    artifact_type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    deployment_count: int = Field(
        description="Number of times deployed",
        examples=[25],
    )
    usage_count: int = Field(
        description="Total usage events",
        examples=[150],
    )
    last_used: datetime = Field(
        description="Timestamp of last usage",
    )
    collections: List[str] = Field(
        description="Collections containing this artifact",
        examples=[["default", "work"]],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-skill",
                "artifact_type": "skill",
                "deployment_count": 25,
                "usage_count": 150,
                "last_used": "2024-11-16T15:30:00Z",
                "collections": ["default"],
            }
        }


class TopArtifactsResponse(PaginatedResponse[TopArtifactItem]):
    """Paginated response for top artifacts by usage.

    Returns artifacts sorted by usage frequency with pagination support.
    """

    pass


class TrendDataPoint(BaseModel):
    """Single data point in a usage trend.

    Represents aggregated usage data for a specific time period.
    """

    timestamp: datetime = Field(
        description="Start of time period",
    )
    period: str = Field(
        description="Time period type (hour, day, week, month)",
        examples=["day"],
    )
    deployment_count: int = Field(
        description="Number of deployments in this period",
        examples=[5],
    )
    usage_count: int = Field(
        description="Total usage events in this period",
        examples=[42],
    )
    unique_artifacts: int = Field(
        description="Number of unique artifacts used in this period",
        examples=[3],
    )
    top_artifact: str = Field(
        description="Most used artifact in this period",
        examples=["pdf-skill"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "timestamp": "2024-11-16T00:00:00Z",
                "period": "day",
                "deployment_count": 5,
                "usage_count": 42,
                "unique_artifacts": 3,
                "top_artifact": "pdf-skill",
            }
        }


class TrendsResponse(BaseModel):
    """Response for usage trends over time.

    Provides time-series data for usage patterns and trends.
    """

    period_type: str = Field(
        description="Aggregation period (hour, day, week, month)",
        examples=["day"],
    )
    start_date: datetime = Field(
        description="Start of trend period",
    )
    end_date: datetime = Field(
        description="End of trend period",
    )
    data_points: List[TrendDataPoint] = Field(
        description="Time-series data points",
    )
    total_periods: int = Field(
        description="Number of periods in the response",
        examples=[30],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "period_type": "day",
                "start_date": "2024-10-17T00:00:00Z",
                "end_date": "2024-11-16T00:00:00Z",
                "data_points": [
                    {
                        "timestamp": "2024-11-16T00:00:00Z",
                        "period": "day",
                        "deployment_count": 5,
                        "usage_count": 42,
                        "unique_artifacts": 3,
                        "top_artifact": "pdf-skill",
                    }
                ],
                "total_periods": 30,
            }
        }


class EnterpriseMetricWindow(BaseModel):
    """Aggregated analytics metrics for a rolling time window."""

    window_days: int = Field(
        description="Window size in days",
        examples=[7],
    )
    total_events: int = Field(
        description="Total events observed in the window",
        examples=[185],
    )
    deploy_events: int = Field(
        description="Deploy events in the window",
        examples=[42],
    )
    sync_events: int = Field(
        description="Sync events in the window",
        examples=[64],
    )
    update_events: int = Field(
        description="Update events in the window",
        examples=[31],
    )
    remove_events: int = Field(
        description="Remove events in the window",
        examples=[9],
    )
    search_events: int = Field(
        description="Search events in the window",
        examples=[39],
    )
    success_count: int = Field(
        description="Events with explicit success outcome",
        examples=[120],
    )
    failure_count: int = Field(
        description="Events with explicit failure outcome",
        examples=[11],
    )
    success_rate: float = Field(
        description="Success ratio across events with explicit outcomes (0-1)",
        examples=[0.916],
    )
    unique_artifacts: int = Field(
        description="Unique artifact keys observed in the window",
        examples=[27],
    )
    unique_projects: int = Field(
        description="Unique projects observed in the window",
        examples=[8],
    )
    unique_collections: int = Field(
        description="Unique collections observed in the window",
        examples=[3],
    )
    deploy_frequency_per_day: float = Field(
        description="Average deploy events per day in the window",
        examples=[6.0],
    )


class ProjectActivityItem(BaseModel):
    """Per-project activity summary for analytics reporting."""

    project_path: str = Field(
        description="Project path as reported in analytics events",
        examples=["~/workspace/my-project"],
    )
    event_count: int = Field(
        description="Total events for this project",
        examples=[54],
    )
    deploy_count: int = Field(
        description="Deploy events for this project",
        examples=[12],
    )
    sync_count: int = Field(
        description="Sync events for this project",
        examples=[21],
    )
    last_activity: datetime = Field(
        description="Most recent activity timestamp",
    )


class ArtifactHistorySummary(BaseModel):
    """Lightweight artifact history/provenance summary for dashboard analytics."""

    version_events: int = Field(
        description="Number of version provenance events observed",
        examples=[133],
    )
    merge_events: int = Field(
        description="Number of merge or rollback-related events observed",
        examples=[7],
    )
    deployment_events: int = Field(
        description="Number of deployment-related events observed",
        examples=[42],
    )


class EnterpriseDeliveryMetrics(BaseModel):
    """Delivery metrics useful for SDLC analytics."""

    deployment_frequency_7d: float = Field(
        description="Average deploys/day over the last 7 days",
        examples=[4.71],
    )
    deployment_frequency_30d: float = Field(
        description="Average deploys/day over the last 30 days",
        examples=[3.26],
    )
    median_deploy_interval_minutes_30d: Optional[float] = Field(
        default=None,
        description="Median minutes between deploy events in the last 30 days",
        examples=[92.5],
    )
    unique_artifacts_deployed_30d: int = Field(
        description="Number of unique artifacts deployed in the last 30 days",
        examples=[19],
    )


class EnterpriseReliabilityMetrics(BaseModel):
    """Reliability metrics derived from sync/deploy/update outcomes."""

    change_failure_rate_30d: float = Field(
        description=(
            "Fraction of failed change events (deploy/sync/update) in the last 30 days (0-1)"
        ),
        examples=[0.12],
    )
    sync_success_rate_7d: float = Field(
        description="Sync success rate over the last 7 days (0-1)",
        examples=[0.94],
    )
    rollback_rate_30d: float = Field(
        description="Ratio of rollback-marked updates to change events in last 30 days (0-1)",
        examples=[0.04],
    )
    mean_time_to_recovery_hours_30d: Optional[float] = Field(
        default=None,
        description=(
            "Average hours from failed change event to next successful change on same artifact"
        ),
        examples=[3.5],
    )


class EnterpriseAdoptionMetrics(BaseModel):
    """Adoption and usage analytics for enterprises and teams."""

    active_projects_7d: int = Field(
        description="Distinct projects with activity in the last 7 days",
        examples=[6],
    )
    active_projects_30d: int = Field(
        description="Distinct projects with activity in the last 30 days",
        examples=[14],
    )
    active_collections_30d: int = Field(
        description="Distinct collections with activity in the last 30 days",
        examples=[4],
    )
    search_to_deploy_conversion_30d: float = Field(
        description="Deploy event count divided by search event count in the last 30 days",
        examples=[0.56],
    )


class EnterpriseAnalyticsSummaryResponse(BaseModel):
    """Enterprise-grade analytics summary for dashboards and reporting pipelines."""

    generated_at: datetime = Field(description="Generation timestamp")
    total_events: int = Field(description="Total analytics events stored", examples=[1337])
    total_artifacts: int = Field(
        description="Total unique artifacts observed in analytics",
        examples=[56],
    )
    total_projects: int = Field(
        description="Total distinct projects observed in analytics",
        examples=[18],
    )
    total_collections: int = Field(
        description="Total distinct collections observed in analytics",
        examples=[5],
    )
    event_type_counts: Dict[str, int] = Field(
        description="Raw event totals by type",
        examples=[{"deploy": 411, "sync": 298, "update": 222, "search": 406}],
    )
    windows: List[EnterpriseMetricWindow] = Field(
        description="Rolling-window aggregates (1d, 7d, 30d, 90d)",
    )
    delivery: EnterpriseDeliveryMetrics = Field(
        description="Delivery and throughput metrics",
    )
    reliability: EnterpriseReliabilityMetrics = Field(
        description="Reliability and incident posture metrics",
    )
    adoption: EnterpriseAdoptionMetrics = Field(
        description="Adoption/engagement metrics",
    )
    top_projects: List[ProjectActivityItem] = Field(
        description="Most active projects in the last 30 days",
    )
    top_artifacts: List[TopArtifactItem] = Field(
        description="Most active artifacts by usage",
    )
    history_summary: ArtifactHistorySummary = Field(
        description="Cross-artifact provenance and history summary",
    )


class AnalyticsEventItem(BaseModel):
    """Normalized analytics event for API consumers and export pipelines."""

    id: int = Field(description="Event identifier")
    event_type: str = Field(description="Event type")
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    collection_name: Optional[str] = Field(
        default=None,
        description="Collection name if present",
    )
    project_path: Optional[str] = Field(
        default=None,
        description="Project path if present",
    )
    timestamp: datetime = Field(description="Event timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed metadata payload",
    )
    outcome: Optional[str] = Field(
        default=None,
        description="Normalized outcome (success, failure, unknown)",
        examples=["success"],
    )


class AnalyticsEventsResponse(PaginatedResponse[AnalyticsEventItem]):
    """Paginated analytics event stream response."""

    pass
