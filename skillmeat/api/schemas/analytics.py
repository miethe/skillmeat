"""Analytics API schemas for statistics and usage data."""

from datetime import datetime
from typing import Dict, List

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
