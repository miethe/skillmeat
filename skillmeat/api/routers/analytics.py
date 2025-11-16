"""Analytics and usage statistics API endpoints.

Provides REST API for querying artifact usage analytics and trends.
"""

import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import APIKeyDep, ConfigManagerDep
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.analytics import (
    AnalyticsSummaryResponse,
    TopArtifactItem,
    TopArtifactsResponse,
    TrendDataPoint,
    TrendsResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(APIKeyDep)],  # All endpoints require API key
)


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


def get_analytics_db(config_mgr: ConfigManagerDep):
    """Get analytics database instance.

    Args:
        config_mgr: Configuration manager dependency

    Returns:
        AnalyticsDB instance or None if analytics disabled

    Raises:
        HTTPException: If analytics is disabled
    """
    if not config_mgr.is_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics is disabled. Enable it in config to use this endpoint.",
        )

    try:
        from skillmeat.storage.analytics import AnalyticsDB

        db_path = config_mgr.get_analytics_db_path()
        return AnalyticsDB(db_path=db_path)
    except Exception as e:
        logger.error(f"Failed to initialize analytics database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics database unavailable",
        )


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get analytics summary",
    description="Retrieve overall statistics and analytics summary",
    responses={
        200: {"description": "Successfully retrieved analytics summary"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def get_analytics_summary(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
) -> AnalyticsSummaryResponse:
    """Get overall analytics summary.

    Provides high-level statistics about collections, artifacts, deployments,
    and recent activity.

    Args:
        config_mgr: Configuration manager dependency
        token: Authentication token

    Returns:
        Analytics summary

    Raises:
        HTTPException: If analytics is disabled or on error
    """
    try:
        logger.info("Fetching analytics summary")

        db = get_analytics_db(config_mgr)

        try:
            # Get database statistics
            stats = db.get_stats()

            # Get collections count
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager(config=config_mgr)
            collections = collection_mgr.list_collections()
            total_collections = len(collections)

            # Get total artifacts across all collections
            from skillmeat.core.artifact import ArtifactManager

            artifact_mgr = ArtifactManager(collection_mgr=collection_mgr)
            total_artifacts = 0
            for coll_name in collections:
                try:
                    artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
                    total_artifacts += len(artifacts)
                except Exception as e:
                    logger.error(
                        f"Error counting artifacts in collection '{coll_name}': {e}"
                    )
                    continue

            # Get recent activity (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            recent_events = db.get_events(limit=10000)  # Get all recent
            recent_activity_count = len(
                [e for e in recent_events if datetime.fromisoformat(e["timestamp"]) > cutoff]
            )

            # Get most deployed artifact
            top_artifacts = db.get_top_artifacts(limit=1)
            most_deployed_artifact = (
                top_artifacts[0]["artifact_name"] if top_artifacts else "none"
            )

            # Get artifacts by type
            artifacts_by_type = stats.get("artifact_type_counts", {})

            # Get total deployments (deploy events)
            deploy_events = stats.get("event_type_counts", {}).get("deploy", 0)

            # Get last activity timestamp
            last_activity_str = stats.get("newest_event")
            last_activity = (
                datetime.fromisoformat(last_activity_str)
                if last_activity_str
                else datetime.now()
            )

            return AnalyticsSummaryResponse(
                total_collections=total_collections,
                total_artifacts=total_artifacts,
                total_deployments=deploy_events,
                total_events=stats.get("total_events", 0),
                artifacts_by_type=artifacts_by_type,
                recent_activity_count=recent_activity_count,
                most_deployed_artifact=most_deployed_artifact,
                last_activity=last_activity,
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics summary: {str(e)}",
        )


@router.get(
    "/top-artifacts",
    response_model=TopArtifactsResponse,
    summary="Get top artifacts by usage",
    description="Retrieve most used artifacts sorted by usage frequency",
    responses={
        200: {"description": "Successfully retrieved top artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def get_top_artifacts(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
    artifact_type: Optional[str] = Query(
        default=None,
        description="Filter by artifact type (skill, command, agent)",
    ),
) -> TopArtifactsResponse:
    """Get top artifacts by usage.

    Returns artifacts sorted by total usage count with pagination support.

    Args:
        config_mgr: Configuration manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional type filter

    Returns:
        Paginated list of top artifacts

    Raises:
        HTTPException: If analytics is disabled or on error
    """
    try:
        logger.info(
            f"Fetching top artifacts (limit={limit}, after={after}, type={artifact_type})"
        )

        db = get_analytics_db(config_mgr)

        try:
            # Get usage summary
            usage_summary = db.get_usage_summary(artifact_type=artifact_type)

            # Sort by total events (descending)
            usage_summary.sort(key=lambda x: x["total_events"], reverse=True)

            # Decode cursor if provided
            start_idx = 0
            if after:
                cursor_value = decode_cursor(after)
                # Cursor format: "artifact_name:artifact_type"
                artifact_keys = [
                    f"{s['artifact_name']}:{s['artifact_type']}" for s in usage_summary
                ]
                try:
                    start_idx = artifact_keys.index(cursor_value) + 1
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid cursor: artifact not found",
                    )

            # Paginate
            end_idx = start_idx + limit
            page_artifacts = usage_summary[start_idx:end_idx]

            # Get collections for each artifact (simplified - just check all collections)
            from skillmeat.core.artifact import ArtifactManager
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager(config=config_mgr)
            artifact_mgr = ArtifactManager(collection_mgr=collection_mgr)

            # Build response items
            items: List[TopArtifactItem] = []
            for summary in page_artifacts:
                artifact_name = summary["artifact_name"]
                artifact_type_val = summary["artifact_type"]

                # Find which collections contain this artifact
                containing_collections = []
                for coll_name in collection_mgr.list_collections():
                    try:
                        from skillmeat.core.artifact import ArtifactType

                        artifact = artifact_mgr.show(
                            artifact_name=artifact_name,
                            artifact_type=ArtifactType(artifact_type_val),
                            collection_name=coll_name,
                        )
                        if artifact:
                            containing_collections.append(coll_name)
                    except Exception:
                        continue

                # Parse last used timestamp
                last_used_str = summary.get("last_used")
                last_used = (
                    datetime.fromisoformat(last_used_str)
                    if last_used_str
                    else datetime.now()
                )

                items.append(
                    TopArtifactItem(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type_val,
                        deployment_count=summary.get("deploy_count", 0),
                        usage_count=summary.get("total_events", 0),
                        last_used=last_used,
                        collections=containing_collections,
                    )
                )

            # Build pagination info
            has_next = end_idx < len(usage_summary)
            has_previous = start_idx > 0

            start_cursor = (
                encode_cursor(
                    f"{page_artifacts[0]['artifact_name']}:{page_artifacts[0]['artifact_type']}"
                )
                if page_artifacts
                else None
            )
            end_cursor = (
                encode_cursor(
                    f"{page_artifacts[-1]['artifact_name']}:{page_artifacts[-1]['artifact_type']}"
                )
                if page_artifacts
                else None
            )

            page_info = PageInfo(
                has_next_page=has_next,
                has_previous_page=has_previous,
                start_cursor=start_cursor,
                end_cursor=end_cursor,
                total_count=len(usage_summary),
            )

            logger.info(f"Retrieved {len(items)} top artifacts")
            return TopArtifactsResponse(items=items, page_info=page_info)

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching top artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top artifacts: {str(e)}",
        )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Get usage trends over time",
    description="Retrieve time-series usage data for trend analysis",
    responses={
        200: {"description": "Successfully retrieved usage trends"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def get_usage_trends(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    period: str = Query(
        default="day",
        description="Aggregation period (hour, day, week, month)",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days of history (max 365)",
    ),
) -> TrendsResponse:
    """Get usage trends over time.

    Returns time-series aggregated usage data for the specified period.

    Args:
        config_mgr: Configuration manager dependency
        token: Authentication token
        period: Aggregation period (hour, day, week, month)
        days: Number of days of history

    Returns:
        Usage trends data

    Raises:
        HTTPException: If analytics is disabled or on error
    """
    try:
        logger.info(f"Fetching usage trends (period={period}, days={days})")

        # Validate period
        valid_periods = ["hour", "day", "week", "month"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
            )

        db = get_analytics_db(config_mgr)

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Get all events in the range
            all_events = db.get_events(limit=100000)  # Get all events
            filtered_events = [
                e
                for e in all_events
                if datetime.fromisoformat(e["timestamp"]) >= start_date
            ]

            # Aggregate events by period
            period_data: Dict[datetime, Dict] = {}

            for event in filtered_events:
                timestamp = datetime.fromisoformat(event["timestamp"])

                # Determine period bucket
                if period == "hour":
                    bucket = timestamp.replace(minute=0, second=0, microsecond=0)
                elif period == "day":
                    bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                elif period == "week":
                    # Start of week (Monday)
                    days_since_monday = timestamp.weekday()
                    bucket = (timestamp - timedelta(days=days_since_monday)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                else:  # month
                    bucket = timestamp.replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )

                # Initialize bucket if needed
                if bucket not in period_data:
                    period_data[bucket] = {
                        "deployment_count": 0,
                        "usage_count": 0,
                        "artifacts": set(),
                        "artifact_counts": {},
                    }

                # Update counts
                period_data[bucket]["usage_count"] += 1
                if event["event_type"] == "deploy":
                    period_data[bucket]["deployment_count"] += 1

                # Track unique artifacts
                artifact_key = f"{event['artifact_type']}:{event['artifact_name']}"
                period_data[bucket]["artifacts"].add(artifact_key)

                # Count per artifact
                if artifact_key not in period_data[bucket]["artifact_counts"]:
                    period_data[bucket]["artifact_counts"][artifact_key] = 0
                period_data[bucket]["artifact_counts"][artifact_key] += 1

            # Convert to data points
            data_points: List[TrendDataPoint] = []
            for bucket in sorted(period_data.keys()):
                data = period_data[bucket]

                # Find top artifact in this period
                top_artifact = "none"
                if data["artifact_counts"]:
                    top_artifact_key = max(
                        data["artifact_counts"], key=data["artifact_counts"].get
                    )
                    # Extract just the artifact name
                    top_artifact = top_artifact_key.split(":", 1)[1]

                data_points.append(
                    TrendDataPoint(
                        timestamp=bucket,
                        period=period,
                        deployment_count=data["deployment_count"],
                        usage_count=data["usage_count"],
                        unique_artifacts=len(data["artifacts"]),
                        top_artifact=top_artifact,
                    )
                )

            logger.info(f"Retrieved {len(data_points)} trend data points")
            return TrendsResponse(
                period_type=period,
                start_date=start_date,
                end_date=end_date,
                data_points=data_points,
                total_periods=len(data_points),
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage trends: {str(e)}",
        )
