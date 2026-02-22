"""Analytics and usage statistics API endpoints.

Provides REST API for querying artifact usage analytics, enterprise metrics,
and observability exports (JSON, Prometheus, OTLP-style JSON).
"""

import asyncio
import base64
import json
import logging
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from skillmeat.api.dependencies import ConfigManagerDep, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.analytics import (
    AnalyticsEventItem,
    AnalyticsEventsResponse,
    AnalyticsSummaryResponse,
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
from skillmeat.api.schemas.common import ErrorResponse, PageInfo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)

CHANGE_EVENT_TYPES = {"deploy", "sync", "update"}
SUCCESS_RESULTS = {"success", "synced", "ok", "completed"}
FAILURE_RESULTS = {"failed", "failure", "error", "conflict", "cancelled", "canceled"}


# ====================
# Cursor Utilities
# ====================


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64."""
    return base64.b64encode(value.encode()).decode()



def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value."""
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


# ====================
# Shared Helpers
# ====================


def get_analytics_db(config_mgr: ConfigManagerDep):
    """Get analytics database instance."""
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



def _model_dump(model: Any) -> Dict[str, Any]:
    """Compat dump for Pydantic v1/v2 objects."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()



def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Best-effort timestamp parsing with UTC normalization."""
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

        if dt is None:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



def _parse_metadata(raw: Any) -> Dict[str, Any]:
    """Parse analytics metadata payload from DB rows."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}



def _normalize_outcome(metadata: Dict[str, Any]) -> Optional[str]:
    """Normalize event outcome from metadata."""
    if "success" in metadata and isinstance(metadata["success"], bool):
        return "success" if metadata["success"] else "failure"

    result = metadata.get("result")
    if isinstance(result, str):
        normalized = result.strip().lower()
        if normalized in SUCCESS_RESULTS:
            return "success"
        if normalized in FAILURE_RESULTS:
            return "failure"

    return None



def _normalize_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize raw analytics event row into a predictable structure."""
    ts = _parse_timestamp(row.get("timestamp"))
    if ts is None:
        return None

    metadata = _parse_metadata(row.get("metadata"))
    return {
        "id": int(row.get("id", 0)),
        "event_type": str(row.get("event_type", "unknown")),
        "artifact_name": str(row.get("artifact_name", "unknown")),
        "artifact_type": str(row.get("artifact_type", "unknown")),
        "collection_name": row.get("collection_name"),
        "project_path": row.get("project_path"),
        "timestamp": ts,
        "metadata": metadata,
        "outcome": _normalize_outcome(metadata),
    }



def _window_events(
    events: List[Dict[str, Any]],
    window_days: int,
    now: datetime,
) -> List[Dict[str, Any]]:
    cutoff = now - timedelta(days=window_days)
    return [event for event in events if event["timestamp"] >= cutoff]



def _build_window_metrics(
    events: List[Dict[str, Any]],
    window_days: int,
    now: datetime,
) -> EnterpriseMetricWindow:
    window = _window_events(events, window_days, now)
    event_counts = Counter(event["event_type"] for event in window)

    success_count = sum(1 for event in window if event.get("outcome") == "success")
    failure_count = sum(1 for event in window if event.get("outcome") == "failure")
    outcome_total = success_count + failure_count

    unique_artifacts = {
        f"{event['artifact_type']}:{event['artifact_name']}" for event in window
    }
    unique_projects = {
        event["project_path"]
        for event in window
        if isinstance(event.get("project_path"), str) and event.get("project_path")
    }
    unique_collections = {
        event["collection_name"]
        for event in window
        if isinstance(event.get("collection_name"), str) and event.get("collection_name")
    }

    return EnterpriseMetricWindow(
        window_days=window_days,
        total_events=len(window),
        deploy_events=event_counts.get("deploy", 0),
        sync_events=event_counts.get("sync", 0),
        update_events=event_counts.get("update", 0),
        remove_events=event_counts.get("remove", 0),
        search_events=event_counts.get("search", 0),
        success_count=success_count,
        failure_count=failure_count,
        success_rate=(success_count / outcome_total) if outcome_total else 1.0,
        unique_artifacts=len(unique_artifacts),
        unique_projects=len(unique_projects),
        unique_collections=len(unique_collections),
        deploy_frequency_per_day=(event_counts.get("deploy", 0) / window_days)
        if window_days > 0
        else 0.0,
    )



def _build_delivery_metrics(
    window_7: List[Dict[str, Any]],
    window_30: List[Dict[str, Any]],
) -> EnterpriseDeliveryMetrics:
    deploy_events_30 = [event for event in window_30 if event["event_type"] == "deploy"]
    deploy_events_30.sort(key=lambda event: event["timestamp"])

    intervals_minutes: List[float] = []
    for idx in range(1, len(deploy_events_30)):
        delta = (
            deploy_events_30[idx]["timestamp"] - deploy_events_30[idx - 1]["timestamp"]
        ).total_seconds() / 60.0
        if delta > 0:
            intervals_minutes.append(delta)

    unique_artifacts = {
        f"{event['artifact_type']}:{event['artifact_name']}" for event in deploy_events_30
    }

    deploy_7 = sum(1 for event in window_7 if event["event_type"] == "deploy")
    deploy_30 = sum(1 for event in window_30 if event["event_type"] == "deploy")

    return EnterpriseDeliveryMetrics(
        deployment_frequency_7d=deploy_7 / 7.0,
        deployment_frequency_30d=deploy_30 / 30.0,
        median_deploy_interval_minutes_30d=(
            float(statistics.median(intervals_minutes)) if intervals_minutes else None
        ),
        unique_artifacts_deployed_30d=len(unique_artifacts),
    )



def _build_reliability_metrics(
    window_7: List[Dict[str, Any]],
    window_30: List[Dict[str, Any]],
) -> EnterpriseReliabilityMetrics:
    change_events_30 = [
        event for event in window_30 if event["event_type"] in CHANGE_EVENT_TYPES
    ]
    failed_changes_30 = [
        event for event in change_events_30 if event.get("outcome") == "failure"
    ]

    sync_events_7 = [event for event in window_7 if event["event_type"] == "sync"]
    sync_success_7 = [event for event in sync_events_7 if event.get("outcome") == "success"]

    rollback_count_30 = sum(
        1
        for event in window_30
        if event["event_type"] == "update" and event["metadata"].get("rollback") is True
    )

    # MTTR approximation: failed change -> next successful change on same artifact
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in change_events_30:
        key = f"{event['artifact_type']}:{event['artifact_name']}"
        grouped[key].append(event)

    recovery_hours: List[float] = []
    for artifact_events in grouped.values():
        artifact_events.sort(key=lambda event: event["timestamp"])
        pending_failures: List[datetime] = []

        for event in artifact_events:
            outcome = event.get("outcome")
            if outcome == "failure":
                pending_failures.append(event["timestamp"])
            elif outcome == "success" and pending_failures:
                success_time = event["timestamp"]
                for failure_time in pending_failures:
                    delta_hours = (success_time - failure_time).total_seconds() / 3600.0
                    if delta_hours >= 0:
                        recovery_hours.append(delta_hours)
                pending_failures.clear()

    return EnterpriseReliabilityMetrics(
        change_failure_rate_30d=(len(failed_changes_30) / len(change_events_30))
        if change_events_30
        else 0.0,
        sync_success_rate_7d=(len(sync_success_7) / len(sync_events_7))
        if sync_events_7
        else 1.0,
        rollback_rate_30d=(rollback_count_30 / len(change_events_30))
        if change_events_30
        else 0.0,
        mean_time_to_recovery_hours_30d=(
            float(statistics.mean(recovery_hours)) if recovery_hours else None
        ),
    )



def _build_adoption_metrics(
    window_7: List[Dict[str, Any]],
    window_30: List[Dict[str, Any]],
) -> EnterpriseAdoptionMetrics:
    active_projects_7 = {
        event["project_path"]
        for event in window_7
        if isinstance(event.get("project_path"), str) and event.get("project_path")
    }
    active_projects_30 = {
        event["project_path"]
        for event in window_30
        if isinstance(event.get("project_path"), str) and event.get("project_path")
    }
    active_collections_30 = {
        event["collection_name"]
        for event in window_30
        if isinstance(event.get("collection_name"), str) and event.get("collection_name")
    }

    deploy_count_30 = sum(1 for event in window_30 if event["event_type"] == "deploy")
    search_count_30 = sum(1 for event in window_30 if event["event_type"] == "search")

    return EnterpriseAdoptionMetrics(
        active_projects_7d=len(active_projects_7),
        active_projects_30d=len(active_projects_30),
        active_collections_30d=len(active_collections_30),
        search_to_deploy_conversion_30d=(deploy_count_30 / search_count_30)
        if search_count_30 > 0
        else 0.0,
    )



def _build_project_activity(events: List[Dict[str, Any]]) -> List[ProjectActivityItem]:
    project_rows: Dict[str, Dict[str, Any]] = {}

    for event in events:
        project_path = event.get("project_path")
        if not isinstance(project_path, str) or not project_path:
            continue

        row = project_rows.setdefault(
            project_path,
            {
                "event_count": 0,
                "deploy_count": 0,
                "sync_count": 0,
                "last_activity": event["timestamp"],
            },
        )
        row["event_count"] += 1
        if event["event_type"] == "deploy":
            row["deploy_count"] += 1
        if event["event_type"] == "sync":
            row["sync_count"] += 1
        if event["timestamp"] > row["last_activity"]:
            row["last_activity"] = event["timestamp"]

    sorted_projects = sorted(
        project_rows.items(),
        key=lambda item: (item[1]["event_count"], item[1]["last_activity"]),
        reverse=True,
    )

    return [
        ProjectActivityItem(
            project_path=path,
            event_count=row["event_count"],
            deploy_count=row["deploy_count"],
            sync_count=row["sync_count"],
            last_activity=row["last_activity"],
        )
        for path, row in sorted_projects[:10]
    ]



def _build_history_summary(events: List[Dict[str, Any]]) -> ArtifactHistorySummary:
    version_events = sum(
        1 for event in events if event["event_type"] in {"deploy", "sync", "update"}
    )

    merge_events = sum(
        1
        for event in events
        if (
            event["metadata"].get("rollback") is True
            or event["metadata"].get("sync_type") == "merge"
            or event["metadata"].get("strategy") == "merge"
            or int(event["metadata"].get("conflicts_detected") or 0) > 0
        )
    )

    deployment_events = sum(1 for event in events if event["event_type"] == "deploy")

    return ArtifactHistorySummary(
        version_events=version_events,
        merge_events=merge_events,
        deployment_events=deployment_events,
    )



def _build_top_artifact_items(
    usage_summary: Iterable[Dict[str, Any]],
    config_mgr: ConfigManagerDep,
    limit: int,
) -> List[TopArtifactItem]:
    page_artifacts = list(usage_summary)[:limit]

    # Resolve collection membership for each artifact
    containing_map: Dict[tuple[str, str], List[str]] = {}
    try:
        from skillmeat.core.artifact import ArtifactManager, ArtifactType
        from skillmeat.core.collection import CollectionManager

        collection_mgr = CollectionManager(config=config_mgr)
        artifact_mgr = ArtifactManager(collection_mgr=collection_mgr)
        collections = collection_mgr.list_collections()

        for summary in page_artifacts:
            artifact_name = summary.get("artifact_name", "")
            artifact_type_val = summary.get("artifact_type", "")
            key = (artifact_name, artifact_type_val)
            containing_map[key] = []

            for coll_name in collections:
                try:
                    artifact = artifact_mgr.show(
                        artifact_name=artifact_name,
                        artifact_type=ArtifactType(artifact_type_val),
                        collection_name=coll_name,
                    )
                    if artifact:
                        containing_map[key].append(coll_name)
                except Exception:
                    continue
    except Exception:
        # Best-effort enrichment; fall back to empty collection lists.
        containing_map = {
            (summary.get("artifact_name", ""), summary.get("artifact_type", "")): []
            for summary in page_artifacts
        }

    items: List[TopArtifactItem] = []
    now = datetime.now(timezone.utc)

    for summary in page_artifacts:
        artifact_name = summary.get("artifact_name", "")
        artifact_type_val = summary.get("artifact_type", "")

        last_used = _parse_timestamp(summary.get("last_used")) or now

        items.append(
            TopArtifactItem(
                artifact_name=artifact_name,
                artifact_type=artifact_type_val,
                deployment_count=int(summary.get("deploy_count", 0) or 0),
                usage_count=int(summary.get("total_events", 0) or 0),
                last_used=last_used,
                collections=containing_map.get((artifact_name, artifact_type_val), []),
            )
        )

    return items



def _build_legacy_summary(
    config_mgr: ConfigManagerDep,
    db,
) -> AnalyticsSummaryResponse:
    """Build legacy analytics summary for existing dashboard consumers."""
    stats = db.get_stats()

    from skillmeat.core.artifact import ArtifactManager
    from skillmeat.core.collection import CollectionManager

    collection_mgr = CollectionManager(config=config_mgr)
    collections = collection_mgr.list_collections()
    total_collections = len(collections)

    artifact_mgr = ArtifactManager(collection_mgr=collection_mgr)
    total_artifacts = 0
    for coll_name in collections:
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            total_artifacts += len(artifacts)
        except Exception as e:
            logger.debug(
                "Error counting artifacts in collection '%s': %s",
                coll_name,
                e,
            )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    recent_events = db.get_events(limit=50000)
    normalized_recent = [
        normalized
        for normalized in (_normalize_event(event) for event in recent_events)
        if normalized is not None and normalized["timestamp"] >= cutoff
    ]

    top_artifacts = db.get_top_artifacts(limit=1)
    most_deployed_artifact = top_artifacts[0]["artifact_name"] if top_artifacts else "none"

    last_activity = _parse_timestamp(stats.get("newest_event")) or now

    return AnalyticsSummaryResponse(
        total_collections=total_collections,
        total_artifacts=total_artifacts,
        total_deployments=int(stats.get("event_type_counts", {}).get("deploy", 0)),
        total_events=int(stats.get("total_events", 0)),
        artifacts_by_type={
            str(key): int(value) for key, value in stats.get("artifact_type_counts", {}).items()
        },
        recent_activity_count=len(normalized_recent),
        most_deployed_artifact=most_deployed_artifact,
        last_activity=last_activity,
    )



def _build_enterprise_summary(
    config_mgr: ConfigManagerDep,
    db,
) -> EnterpriseAnalyticsSummaryResponse:
    """Build enterprise-grade analytics summary from live event data."""
    now = datetime.now(timezone.utc)
    stats = db.get_stats()

    raw_events = db.get_events(limit=200000)
    events: List[Dict[str, Any]] = [
        normalized
        for normalized in (_normalize_event(event) for event in raw_events)
        if normalized is not None
    ]

    windows = [_build_window_metrics(events, days, now) for days in (1, 7, 30, 90)]

    window_7 = _window_events(events, 7, now)
    window_30 = _window_events(events, 30, now)

    delivery = _build_delivery_metrics(window_7, window_30)
    reliability = _build_reliability_metrics(window_7, window_30)
    adoption = _build_adoption_metrics(window_7, window_30)
    top_projects = _build_project_activity(window_30)
    history_summary = _build_history_summary(events)

    usage_summary = db.get_usage_summary()
    top_artifacts = _build_top_artifact_items(usage_summary, config_mgr=config_mgr, limit=10)

    total_projects = len(
        {
            event["project_path"]
            for event in events
            if isinstance(event.get("project_path"), str) and event.get("project_path")
        }
    )

    total_collections = len(
        {
            event["collection_name"]
            for event in events
            if isinstance(event.get("collection_name"), str)
            and event.get("collection_name")
        }
    )

    if total_collections == 0:
        try:
            from skillmeat.core.collection import CollectionManager

            total_collections = len(CollectionManager(config=config_mgr).list_collections())
        except Exception:
            total_collections = 0

    return EnterpriseAnalyticsSummaryResponse(
        generated_at=now,
        total_events=int(stats.get("total_events", 0)),
        total_artifacts=int(stats.get("total_artifacts", 0)),
        total_projects=total_projects,
        total_collections=total_collections,
        event_type_counts={
            str(key): int(value) for key, value in stats.get("event_type_counts", {}).items()
        },
        windows=windows,
        delivery=delivery,
        reliability=reliability,
        adoption=adoption,
        top_projects=top_projects,
        top_artifacts=top_artifacts,
        history_summary=history_summary,
    )



def _build_prometheus_export(summary: EnterpriseAnalyticsSummaryResponse) -> str:
    """Render enterprise analytics summary in Prometheus exposition format."""
    lines = [
        "# HELP skillmeat_analytics_total_events Total analytics events stored",
        "# TYPE skillmeat_analytics_total_events gauge",
        f"skillmeat_analytics_total_events {summary.total_events}",
        "# HELP skillmeat_analytics_total_artifacts Total unique artifacts observed",
        "# TYPE skillmeat_analytics_total_artifacts gauge",
        f"skillmeat_analytics_total_artifacts {summary.total_artifacts}",
        "# HELP skillmeat_analytics_total_projects Total projects observed",
        "# TYPE skillmeat_analytics_total_projects gauge",
        f"skillmeat_analytics_total_projects {summary.total_projects}",
        "# HELP skillmeat_analytics_total_collections Total collections observed",
        "# TYPE skillmeat_analytics_total_collections gauge",
        f"skillmeat_analytics_total_collections {summary.total_collections}",
        "# HELP skillmeat_analytics_event_type_total Event totals by type",
        "# TYPE skillmeat_analytics_event_type_total counter",
    ]

    for event_type, count in sorted(summary.event_type_counts.items()):
        lines.append(
            f'skillmeat_analytics_event_type_total{{event_type="{event_type}"}} {count}'
        )

    lines.extend(
        [
            "# HELP skillmeat_analytics_window_events_total Rolling-window total events",
            "# TYPE skillmeat_analytics_window_events_total gauge",
            "# HELP skillmeat_analytics_window_success_rate Rolling-window success rate",
            "# TYPE skillmeat_analytics_window_success_rate gauge",
            "# HELP skillmeat_analytics_window_deploy_frequency_per_day Rolling-window deploy frequency",
            "# TYPE skillmeat_analytics_window_deploy_frequency_per_day gauge",
        ]
    )

    for window in summary.windows:
        label = f'window_days="{window.window_days}"'
        lines.append(
            f"skillmeat_analytics_window_events_total{{{label}}} {window.total_events}"
        )
        lines.append(
            f"skillmeat_analytics_window_success_rate{{{label}}} {window.success_rate:.6f}"
        )
        lines.append(
            "skillmeat_analytics_window_deploy_frequency_per_day"
            f"{{{label}}} {window.deploy_frequency_per_day:.6f}"
        )

    lines.extend(
        [
            "# HELP skillmeat_analytics_change_failure_rate_30d Change failure rate over 30 days",
            "# TYPE skillmeat_analytics_change_failure_rate_30d gauge",
            (
                "skillmeat_analytics_change_failure_rate_30d "
                f"{summary.reliability.change_failure_rate_30d:.6f}"
            ),
            "# HELP skillmeat_analytics_sync_success_rate_7d Sync success rate over 7 days",
            "# TYPE skillmeat_analytics_sync_success_rate_7d gauge",
            (
                "skillmeat_analytics_sync_success_rate_7d "
                f"{summary.reliability.sync_success_rate_7d:.6f}"
            ),
            "# HELP skillmeat_analytics_rollback_rate_30d Rollback rate over 30 days",
            "# TYPE skillmeat_analytics_rollback_rate_30d gauge",
            (
                "skillmeat_analytics_rollback_rate_30d "
                f"{summary.reliability.rollback_rate_30d:.6f}"
            ),
            "# HELP skillmeat_analytics_deployment_frequency_7d Deployments/day over 7 days",
            "# TYPE skillmeat_analytics_deployment_frequency_7d gauge",
            (
                "skillmeat_analytics_deployment_frequency_7d "
                f"{summary.delivery.deployment_frequency_7d:.6f}"
            ),
            "# HELP skillmeat_analytics_deployment_frequency_30d Deployments/day over 30 days",
            "# TYPE skillmeat_analytics_deployment_frequency_30d gauge",
            (
                "skillmeat_analytics_deployment_frequency_30d "
                f"{summary.delivery.deployment_frequency_30d:.6f}"
            ),
        ]
    )

    return "\n".join(lines) + "\n"



def _as_unix_nanos(dt: datetime) -> str:
    """Convert datetime to unix nanoseconds string."""
    return str(int(dt.timestamp() * 1_000_000_000))



def _otel_attr_value(value: Any) -> Dict[str, Any]:
    """Convert Python scalar value to OTLP JSON attribute value object."""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}



def _otel_attributes(attrs: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if not attrs:
        return []
    return [
        {"key": key, "value": _otel_attr_value(value)}
        for key, value in attrs.items()
        if value is not None
    ]



def _otel_gauge_metric(
    now: datetime,
    name: str,
    description: str,
    value: float,
    unit: str = "1",
    attrs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "unit": unit,
        "gauge": {
            "dataPoints": [
                {
                    "timeUnixNano": _as_unix_nanos(now),
                    "attributes": _otel_attributes(attrs),
                    "asDouble": float(value),
                }
            ]
        },
    }



def _otel_sum_metric(
    now: datetime,
    name: str,
    description: str,
    value: int,
    unit: str = "1",
    attrs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "unit": unit,
        "sum": {
            "aggregationTemporality": 2,  # CUMULATIVE
            "isMonotonic": True,
            "dataPoints": [
                {
                    "startTimeUnixNano": _as_unix_nanos(now),
                    "timeUnixNano": _as_unix_nanos(now),
                    "attributes": _otel_attributes(attrs),
                    "asInt": str(int(value)),
                }
            ],
        },
    }



def _build_otel_export(summary: EnterpriseAnalyticsSummaryResponse) -> Dict[str, Any]:
    """Build OTLP-style JSON payload for external observability pipelines."""
    now = summary.generated_at

    metrics: List[Dict[str, Any]] = [
        _otel_sum_metric(
            now,
            "skillmeat.analytics.events.total",
            "Total analytics events stored",
            summary.total_events,
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.artifacts.total",
            "Total unique artifacts observed",
            float(summary.total_artifacts),
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.projects.total",
            "Total projects observed",
            float(summary.total_projects),
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.collections.total",
            "Total collections observed",
            float(summary.total_collections),
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.reliability.change_failure_rate_30d",
            "Change failure rate over 30 days",
            summary.reliability.change_failure_rate_30d,
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.reliability.sync_success_rate_7d",
            "Sync success rate over 7 days",
            summary.reliability.sync_success_rate_7d,
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.delivery.deploy_frequency_7d",
            "Average deploys per day over 7 days",
            summary.delivery.deployment_frequency_7d,
            unit="{deploy}/d",
        ),
        _otel_gauge_metric(
            now,
            "skillmeat.analytics.delivery.deploy_frequency_30d",
            "Average deploys per day over 30 days",
            summary.delivery.deployment_frequency_30d,
            unit="{deploy}/d",
        ),
    ]

    for event_type, count in summary.event_type_counts.items():
        metrics.append(
            _otel_sum_metric(
                now,
                "skillmeat.analytics.events.by_type",
                "Event counts partitioned by event type",
                int(count),
                attrs={"event.type": event_type},
            )
        )

    for window in summary.windows:
        attrs = {"window.days": window.window_days}
        metrics.append(
            _otel_gauge_metric(
                now,
                "skillmeat.analytics.window.events_total",
                "Rolling-window event totals",
                float(window.total_events),
                attrs=attrs,
            )
        )
        metrics.append(
            _otel_gauge_metric(
                now,
                "skillmeat.analytics.window.success_rate",
                "Rolling-window success rate",
                window.success_rate,
                attrs=attrs,
            )
        )

    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "skillmeat-analytics"},
                        },
                        {
                            "key": "service.namespace",
                            "value": {"stringValue": "skillmeat"},
                        },
                    ]
                },
                "scopeMetrics": [
                    {
                        "scope": {
                            "name": "skillmeat.analytics.api",
                            "version": "1.0.0",
                        },
                        "metrics": metrics,
                    }
                ],
            }
        ]
    }


# ====================
# API Endpoints
# ====================


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
    """Get overall analytics summary for existing dashboard widgets."""
    try:
        logger.info("Fetching analytics summary")
        db = get_analytics_db(config_mgr)
        try:
            return _build_legacy_summary(config_mgr=config_mgr, db=db)
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
    "/enterprise-summary",
    response_model=EnterpriseAnalyticsSummaryResponse,
    summary="Get enterprise analytics summary",
    description=(
        "Retrieve enterprise-grade analytics for SDLC, reliability, adoption, "
        "and provenance dashboards"
    ),
    responses={
        200: {"description": "Successfully retrieved enterprise analytics summary"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def get_enterprise_summary(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
) -> EnterpriseAnalyticsSummaryResponse:
    """Get enterprise analytics summary optimized for operations and observability."""
    try:
        logger.info("Fetching enterprise analytics summary")
        db = get_analytics_db(config_mgr)
        try:
            return _build_enterprise_summary(config_mgr=config_mgr, db=db)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching enterprise analytics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch enterprise analytics summary: {str(e)}",
        )


@router.get(
    "/events",
    response_model=AnalyticsEventsResponse,
    summary="List analytics events",
    description="Retrieve normalized analytics events with cursor pagination",
    responses={
        200: {"description": "Successfully retrieved analytics events"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def list_analytics_events(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Number of events per page (max 500)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (encoded offset)",
    ),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    artifact_name: Optional[str] = Query(
        default=None,
        description="Filter by artifact name",
    ),
    artifact_type: Optional[str] = Query(
        default=None,
        description="Filter by artifact type",
    ),
    collection_name: Optional[str] = Query(
        default=None,
        description="Filter by collection name",
    ),
) -> AnalyticsEventsResponse:
    """List analytics events with normalized metadata and outcome fields."""
    try:
        db = get_analytics_db(config_mgr)
        try:
            offset = 0
            if after:
                decoded = decode_cursor(after)
                try:
                    offset = int(decoded)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid cursor: expected encoded integer offset",
                    )
                if offset < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid cursor: offset must be non-negative",
                    )

            rows = db.get_events(
                event_type=event_type,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                collection_name=collection_name,
                limit=limit,
                offset=offset,
            )

            items: List[AnalyticsEventItem] = []
            for row in rows:
                normalized = _normalize_event(row)
                if normalized is None:
                    continue
                items.append(
                    AnalyticsEventItem(
                        id=normalized["id"],
                        event_type=normalized["event_type"],
                        artifact_name=normalized["artifact_name"],
                        artifact_type=normalized["artifact_type"],
                        collection_name=normalized["collection_name"],
                        project_path=normalized["project_path"],
                        timestamp=normalized["timestamp"],
                        metadata=normalized["metadata"],
                        outcome=normalized["outcome"] or "unknown",
                    )
                )

            has_next = len(rows) == limit
            next_offset = offset + len(rows)

            page_info = PageInfo(
                has_next_page=has_next,
                has_previous_page=offset > 0,
                start_cursor=encode_cursor(str(offset)) if rows else None,
                end_cursor=encode_cursor(str(next_offset)) if has_next else None,
                total_count=None,
            )

            return AnalyticsEventsResponse(items=items, page_info=page_info)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing analytics events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list analytics events: {str(e)}",
        )


@router.get(
    "/export",
    summary="Export analytics for external observability systems",
    description=(
        "Export analytics in JSON, Prometheus exposition format, or OTLP-style JSON "
        "for ingestion into OTel, Grafana/Prometheus, and downstream pipelines"
    ),
    responses={
        200: {"description": "Successfully exported analytics"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def export_analytics(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    format: str = Query(
        default="json",
        description="Export format: json, prometheus, or otel",
    ),
    include_events: bool = Query(
        default=False,
        description="Include raw normalized events (json format only)",
    ),
    event_limit: int = Query(
        default=5000,
        ge=1,
        le=50000,
        description="Maximum number of raw events included in JSON export",
    ),
):
    """Export enterprise analytics in observability-friendly formats."""
    normalized_format = format.strip().lower()
    if normalized_format not in {"json", "prometheus", "otel"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be one of: json, prometheus, otel",
        )

    try:
        db = get_analytics_db(config_mgr)
        try:
            summary = _build_enterprise_summary(config_mgr=config_mgr, db=db)

            if normalized_format == "prometheus":
                payload = _build_prometheus_export(summary)
                return PlainTextResponse(
                    content=payload,
                    media_type="text/plain; version=0.0.4; charset=utf-8",
                )

            if normalized_format == "otel":
                return JSONResponse(content=_build_otel_export(summary))

            # JSON export (default)
            result: Dict[str, Any] = {
                "export_format": "json",
                "generated_at": summary.generated_at.isoformat(),
                "summary": _model_dump(summary),
            }

            if include_events:
                raw_events = db.get_events(limit=event_limit)
                events: List[Dict[str, Any]] = []
                for row in raw_events:
                    normalized = _normalize_event(row)
                    if normalized is None:
                        continue
                    events.append(
                        {
                            **normalized,
                            "timestamp": normalized["timestamp"].isoformat(),
                        }
                    )
                result["events"] = events

            return JSONResponse(content=result)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export analytics: {str(e)}",
        )


@router.get(
    "/stream",
    summary="Stream analytics updates",
    description="Server-sent events stream for live analytics dashboards",
    responses={
        200: {"description": "Streaming analytics updates"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
)
async def stream_analytics(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    interval_seconds: int = Query(
        default=10,
        ge=3,
        le=60,
        description="Polling interval used by stream publisher",
    ),
):
    """Stream enterprise analytics changes via SSE."""
    db = get_analytics_db(config_mgr)

    async def event_generator():
        last_total_events: Optional[int] = None
        try:
            while True:
                stats = db.get_stats()
                total_events = int(stats.get("total_events", 0))

                if last_total_events is None or total_events != last_total_events:
                    payload = {
                        "type": "summary_update",
                        "data": {
                            "total_events": total_events,
                            "event_type_counts": stats.get("event_type_counts", {}),
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\\n\\n"
                    last_total_events = total_events
                else:
                    # Keepalive comment frame
                    yield ": heartbeat\\n\\n"

                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
    """Get top artifacts by usage."""
    try:
        logger.info(
            "Fetching top artifacts (limit=%s, after=%s, type=%s)",
            limit,
            after,
            artifact_type,
        )

        db = get_analytics_db(config_mgr)

        try:
            usage_summary = db.get_usage_summary(artifact_type=artifact_type)
            usage_summary.sort(key=lambda item: item.get("total_events", 0), reverse=True)

            start_idx = 0
            if after:
                cursor_value = decode_cursor(after)
                artifact_keys = [
                    f"{summary['artifact_name']}:{summary['artifact_type']}"
                    for summary in usage_summary
                ]
                try:
                    start_idx = artifact_keys.index(cursor_value) + 1
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid cursor: artifact not found",
                    )

            end_idx = start_idx + limit
            page_artifacts = usage_summary[start_idx:end_idx]

            items = _build_top_artifact_items(
                usage_summary=page_artifacts,
                config_mgr=config_mgr,
                limit=limit,
            )

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

            logger.info("Retrieved %s top artifacts", len(items))
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
    """Get usage trends over time."""
    try:
        logger.info("Fetching usage trends (period=%s, days=%s)", period, days)

        valid_periods = ["hour", "day", "week", "month"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
            )

        db = get_analytics_db(config_mgr)

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            all_events = db.get_events(limit=200000)
            filtered_events = []
            for row in all_events:
                normalized = _normalize_event(row)
                if normalized is None:
                    continue
                if normalized["timestamp"] >= start_date:
                    filtered_events.append(normalized)

            period_data: Dict[datetime, Dict[str, Any]] = {}

            for event in filtered_events:
                timestamp = event["timestamp"]

                if period == "hour":
                    bucket = timestamp.replace(minute=0, second=0, microsecond=0)
                elif period == "day":
                    bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                elif period == "week":
                    days_since_monday = timestamp.weekday()
                    bucket = (timestamp - timedelta(days=days_since_monday)).replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                else:  # month
                    bucket = timestamp.replace(
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )

                if bucket not in period_data:
                    period_data[bucket] = {
                        "deployment_count": 0,
                        "usage_count": 0,
                        "artifacts": set(),
                        "artifact_counts": Counter(),
                    }

                period_data[bucket]["usage_count"] += 1
                if event["event_type"] == "deploy":
                    period_data[bucket]["deployment_count"] += 1

                artifact_key = f"{event['artifact_type']}:{event['artifact_name']}"
                period_data[bucket]["artifacts"].add(artifact_key)
                period_data[bucket]["artifact_counts"][artifact_key] += 1

            data_points: List[TrendDataPoint] = []
            for bucket in sorted(period_data.keys()):
                data = period_data[bucket]

                top_artifact = "none"
                if data["artifact_counts"]:
                    top_artifact_key = data["artifact_counts"].most_common(1)[0][0]
                    top_artifact = top_artifact_key.split(":", 1)[1]

                data_points.append(
                    TrendDataPoint(
                        timestamp=bucket,
                        period=period,
                        deployment_count=int(data["deployment_count"]),
                        usage_count=int(data["usage_count"]),
                        unique_artifacts=len(data["artifacts"]),
                        top_artifact=top_artifact,
                    )
                )

            logger.info("Retrieved %s trend data points", len(data_points))
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
