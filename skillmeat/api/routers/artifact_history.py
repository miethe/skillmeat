"""Artifact provenance and history API endpoints.

Provides unified history timelines for artifacts by merging data from:
- Cache DB artifact_versions lineage records
- Analytics event stream
- Deployment tracker records
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import ConfigManagerDep, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    ArtifactHistoryEventResponse,
    ArtifactHistoryResponse,
)
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.cache.models import Artifact as CacheArtifact
from skillmeat.cache.models import ArtifactVersion, Project, get_session
from skillmeat.storage.deployment import DeploymentTracker

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(verify_api_key)],
)

_ARTIFACT_ID_EXTENSIONS = (".md", ".txt", ".json", ".yaml", ".yml")



def _normalize_artifact_name(name: str) -> str:
    """Normalize artifact names by stripping common text extensions."""
    normalized = name
    for ext in _ARTIFACT_ID_EXTENSIONS:
        if normalized.endswith(ext):
            normalized = normalized[: -len(ext)]
            break
    return normalized



def _parse_artifact_id(artifact_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse artifact path parameter as either 'type:name' or UUID.

    Returns:
        Tuple of (artifact_type, artifact_name, artifact_uuid)
    """
    if ":" in artifact_id:
        artifact_type, artifact_name = artifact_id.split(":", 1)
        return artifact_type, _normalize_artifact_name(artifact_name), None
    return None, None, artifact_id



def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Best-effort timestamp parser with UTC normalization."""
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
    """Parse optional metadata payload into a dictionary."""
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



def _build_version_events(
    artifacts: List[CacheArtifact],
    include_versions: bool,
) -> List[ArtifactHistoryEventResponse]:
    """Build timeline events from artifact_versions lineage records."""
    if not include_versions:
        return []

    artifact_map = {artifact.id: artifact for artifact in artifacts}
    artifact_ids = list(artifact_map.keys())
    if not artifact_ids:
        return []

    session = get_session()
    try:
        versions = (
            session.query(ArtifactVersion)
            .filter(ArtifactVersion.artifact_id.in_(artifact_ids))
            .order_by(ArtifactVersion.created_at.desc())
            .all()
        )

        result: List[ArtifactHistoryEventResponse] = []
        for version in versions:
            ts = _parse_timestamp(version.created_at) or datetime.now(timezone.utc)
            lineage = version.get_lineage_list()
            metadata = version.get_metadata_dict() or {}

            cache_artifact = artifact_map.get(version.artifact_id)
            project_path = None
            if cache_artifact and cache_artifact.project:
                project_path = cache_artifact.project.path

            result.append(
                ArtifactHistoryEventResponse(
                    id=f"version:{version.id}",
                    timestamp=ts,
                    event_category="version",
                    event_type=version.change_origin,
                    source="artifact_versions",
                    artifact_name=cache_artifact.name if cache_artifact else "unknown",
                    artifact_type=cache_artifact.type if cache_artifact else "unknown",
                    collection_name=None,
                    project_path=project_path,
                    content_sha=version.content_hash,
                    parent_sha=version.parent_hash,
                    version_lineage=lineage if lineage else None,
                    metadata=metadata,
                )
            )

        return result
    finally:
        session.close()



def _build_analytics_events(
    config_mgr: ConfigManagerDep,
    artifact_name: str,
    artifact_type: str,
    include_analytics: bool,
) -> List[ArtifactHistoryEventResponse]:
    """Build timeline events from analytics event stream."""
    if not include_analytics or not config_mgr.is_analytics_enabled():
        return []

    try:
        from skillmeat.storage.analytics import AnalyticsDB

        db = AnalyticsDB(db_path=config_mgr.get_analytics_db_path())
    except Exception:
        return []

    try:
        rows = db.get_events(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            limit=10000,
            offset=0,
        )

        result: List[ArtifactHistoryEventResponse] = []
        for row in rows:
            ts = _parse_timestamp(row.get("timestamp"))
            if ts is None:
                continue

            metadata = _parse_metadata(row.get("metadata"))
            content_sha = metadata.get("sha_after") or metadata.get("sha")
            parent_sha = metadata.get("sha_before")

            result.append(
                ArtifactHistoryEventResponse(
                    id=f"analytics:{row.get('id')}",
                    timestamp=ts,
                    event_category="analytics",
                    event_type=str(row.get("event_type") or "unknown"),
                    source="analytics_events",
                    artifact_name=str(row.get("artifact_name") or artifact_name),
                    artifact_type=str(row.get("artifact_type") or artifact_type),
                    collection_name=row.get("collection_name"),
                    project_path=row.get("project_path"),
                    content_sha=content_sha,
                    parent_sha=parent_sha,
                    version_lineage=None,
                    metadata=metadata,
                )
            )

        return result
    finally:
        db.close()



def _build_deployment_events(
    artifacts: List[CacheArtifact],
    artifact_name: str,
    artifact_type: str,
    include_deployments: bool,
) -> List[ArtifactHistoryEventResponse]:
    """Build timeline events from deployment tracker records."""
    if not include_deployments:
        return []

    # Restrict scanning to projects already associated with this artifact in cache.
    project_paths = {
        artifact.project.path
        for artifact in artifacts
        if artifact.project and isinstance(artifact.project.path, str)
    }

    result: List[ArtifactHistoryEventResponse] = []

    for project_path in sorted(project_paths):
        try:
            deployments = DeploymentTracker.read_deployments(Path(project_path))
        except Exception:
            continue

        for deployment in deployments:
            dep_name = _normalize_artifact_name(deployment.artifact_name)
            if dep_name != artifact_name or deployment.artifact_type != artifact_type:
                continue

            ts = _parse_timestamp(deployment.deployed_at) or datetime.now(timezone.utc)
            metadata = {
                "artifact_path": str(deployment.artifact_path),
                "deployment_profile_id": deployment.deployment_profile_id,
                "platform": deployment.platform,
                "local_modifications": deployment.local_modifications,
                "merge_base_snapshot": deployment.merge_base_snapshot,
                "artifact_uuid": deployment.artifact_uuid,
            }

            result.append(
                ArtifactHistoryEventResponse(
                    id=(
                        "deployment:"
                        f"{project_path}:{deployment.deployed_at.isoformat()}:{deployment.artifact_type}:{deployment.artifact_name}"
                    ),
                    timestamp=ts,
                    event_category="deployment",
                    event_type="deploy_record",
                    source="deployment_tracker",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=deployment.from_collection,
                    project_path=project_path,
                    content_sha=deployment.collection_sha,
                    parent_sha=deployment.merge_base_snapshot,
                    version_lineage=deployment.version_lineage or None,
                    metadata=metadata,
                )
            )

            if deployment.merge_base_snapshot:
                result.append(
                    ArtifactHistoryEventResponse(
                        id=(
                            "snapshot:"
                            f"{project_path}:{deployment.merge_base_snapshot}"
                        ),
                        timestamp=ts,
                        event_category="snapshot",
                        event_type="merge_base_snapshot",
                        source="deployment_tracker",
                        artifact_name=artifact_name,
                        artifact_type=artifact_type,
                        collection_name=deployment.from_collection,
                        project_path=project_path,
                        content_sha=deployment.merge_base_snapshot,
                        parent_sha=None,
                        version_lineage=None,
                        metadata={
                            "merge_base_snapshot": deployment.merge_base_snapshot,
                            "deployment_profile_id": deployment.deployment_profile_id,
                        },
                    )
                )

    return result



def _compute_statistics(events: List[ArtifactHistoryEventResponse]) -> Dict[str, Any]:
    """Compute aggregate provenance statistics for history timelines."""
    lineage_depths = [
        len(event.version_lineage)
        for event in events
        if event.version_lineage and isinstance(event.version_lineage, list)
    ]

    return {
        "total_events": len(events),
        "version_events": sum(1 for event in events if event.event_category == "version"),
        "analytics_events": sum(
            1 for event in events if event.event_category == "analytics"
        ),
        "deployment_events": sum(
            1 for event in events if event.event_category == "deployment"
        ),
        "snapshot_events": sum(
            1 for event in events if event.event_category == "snapshot"
        ),
        "lineage_depth_max": max(lineage_depths) if lineage_depths else 0,
        "unique_projects": len(
            {
                event.project_path
                for event in events
                if isinstance(event.project_path, str) and event.project_path
            }
        ),
        "unique_collections": len(
            {
                event.collection_name
                for event in events
                if isinstance(event.collection_name, str) and event.collection_name
            }
        ),
    }


@router.get(
    "/{artifact_id}/history",
    response_model=ArtifactHistoryResponse,
    summary="Get artifact history and provenance timeline",
    description=(
        "Retrieve a unified artifact timeline with version lineage, operational "
        "events, deployments, and snapshot provenance"
    ),
    responses={
        200: {"description": "Successfully retrieved artifact history"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
    },
)
async def get_artifact_history(
    artifact_id: str,
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    include_versions: bool = Query(
        default=True,
        description="Include version lineage records from artifact_versions",
    ),
    include_analytics: bool = Query(
        default=True,
        description="Include analytics events for this artifact",
    ),
    include_deployments: bool = Query(
        default=True,
        description="Include deployment tracker records and snapshot anchors",
    ),
    limit: int = Query(
        default=300,
        ge=1,
        le=2000,
        description="Maximum number of events returned",
    ),
) -> ArtifactHistoryResponse:
    """Get unified artifact history timeline for modal History tabs."""
    artifact_type, artifact_name, artifact_uuid = _parse_artifact_id(artifact_id)

    session = get_session()
    try:
        artifact_query = session.query(CacheArtifact)

        if artifact_uuid:
            anchor = artifact_query.filter(CacheArtifact.uuid == artifact_uuid).first()
            if anchor is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found",
                )
            artifact_name = _normalize_artifact_name(anchor.name)
            artifact_type = anchor.type

        assert artifact_name is not None
        assert artifact_type is not None

        artifacts = (
            artifact_query.filter(CacheArtifact.name == artifact_name)
            .filter(CacheArtifact.type == artifact_type)
            .all()
        )

        if not artifacts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        version_events = _build_version_events(artifacts, include_versions=include_versions)
        analytics_events = _build_analytics_events(
            config_mgr=config_mgr,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            include_analytics=include_analytics,
        )
        deployment_events = _build_deployment_events(
            artifacts=artifacts,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            include_deployments=include_deployments,
        )

        timeline = version_events + analytics_events + deployment_events
        timeline.sort(key=lambda event: (event.timestamp, event.id), reverse=True)
        timeline = timeline[:limit]

        statistics = _compute_statistics(timeline)

        return ArtifactHistoryResponse(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            timeline=timeline,
            statistics=statistics,
            last_updated=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving artifact history for '%s': %s", artifact_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve artifact history: {str(e)}",
        )
    finally:
        session.close()
