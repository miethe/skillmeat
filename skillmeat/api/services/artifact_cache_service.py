"""Service for refreshing artifact metadata cache after file operations.

This service provides functions to keep the DB cache (CollectionArtifact table)
in sync with the filesystem after artifact operations like deploy, sync, create,
update, and delete.

The cache refresh is designed to be non-blocking - failures are logged but do not
break the main operation. This ensures that artifact operations succeed even if
the cache update fails.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.api.schemas.deployments import DeploymentSummary
from skillmeat.cache.models import (
    Artifact,
    CollectionArtifact,
    CompositeArtifact,
    Project,
)

logger = logging.getLogger(__name__)

# Default TTL for artifact metadata cache: 30 minutes
DEFAULT_METADATA_TTL_SECONDS = 30 * 60


# =============================================================================
# Internal helpers — resolve type:name identifiers to artifact_uuid (CAI-P5-05)
# =============================================================================


def _resolve_artifact_uuid(session: Session, artifact_id: str) -> Optional[str]:
    """Resolve a type:name artifact_id string to its artifacts.uuid value.

    Args:
        session: Database session
        artifact_id: Artifact identifier in 'type:name' format

    Returns:
        UUID hex string if found, None otherwise
    """
    row = session.query(Artifact.uuid).filter(Artifact.id == artifact_id).first()
    return row[0] if row else None


def _get_collection_artifact(
    session: Session,
    collection_id: str,
    artifact_id: str,
) -> Optional[CollectionArtifact]:
    """Fetch a CollectionArtifact row by collection_id and type:name artifact_id.

    Joins through the Artifact table to resolve artifact_id → artifact_uuid
    since the collection_artifacts PK uses uuid (not the type:name string).

    Args:
        session: Database session
        collection_id: Collection identifier
        artifact_id: Artifact identifier in 'type:name' format

    Returns:
        CollectionArtifact ORM instance if found, None otherwise
    """
    return (
        session.query(CollectionArtifact)
        .join(Artifact, Artifact.uuid == CollectionArtifact.artifact_uuid)
        .filter(
            CollectionArtifact.collection_id == collection_id,
            Artifact.id == artifact_id,
        )
        .first()
    )


# Sentinel project_id used for Artifact rows that represent collection-level
# (non-deployed) artifacts.  Must match the constant in user_collections.py.
_COLLECTION_ARTIFACTS_PROJECT_ID = "collection_artifacts_global"


def _ensure_collection_project_sentinel(session: Session) -> None:
    """Ensure the sentinel Project row exists for collection-scoped artifacts."""
    existing = (
        session.query(Project.id)
        .filter(Project.id == _COLLECTION_ARTIFACTS_PROJECT_ID)
        .first()
    )
    if existing:
        return

    sentinel = Project(
        id=_COLLECTION_ARTIFACTS_PROJECT_ID,
        name="Collection Artifacts",
        path="~/.skillmeat/collections",
        description="Sentinel project for collection artifacts",
        status="active",
    )
    session.add(sentinel)
    session.flush()
    logger.debug(
        "Created sentinel Project row '%s' during import",
        _COLLECTION_ARTIFACTS_PROJECT_ID,
    )


def _ensure_artifact_row(
    session: Session,
    artifact_id: str,
    artifact_type: str,
    artifact_name: str,
    source: Optional[str] = None,
) -> str:
    """Ensure an Artifact row exists for the given type:name id and return its UUID.

    Creates the row if it is absent.  This is needed for artifact types that
    are not surfaced by ``ArtifactManager.list_artifacts()`` (e.g. composite)
    so that ``create_or_update_collection_artifact()`` can resolve the UUID
    required by the collection_artifacts FK.

    Args:
        session: Database session
        artifact_id: Full artifact id in ``type:name`` format
        artifact_type: Artifact type string (e.g. ``"composite"``)
        artifact_name: Bare artifact name without type prefix
        source: Optional upstream URL for the artifact

    Returns:
        UUID hex string for the existing or newly created Artifact row
    """
    existing_uuid = _resolve_artifact_uuid(session, artifact_id)
    if existing_uuid:
        return existing_uuid

    _ensure_collection_project_sentinel(session)

    new_uuid = uuid.uuid4().hex
    artifact_row = Artifact(
        id=artifact_id,
        uuid=new_uuid,
        project_id=_COLLECTION_ARTIFACTS_PROJECT_ID,
        name=artifact_name,
        type=artifact_type,
        source=source,
    )
    session.add(artifact_row)
    session.flush()  # Flush so FK resolution works in the same transaction
    logger.debug(
        "Created Artifact row for '%s' (uuid=%s) during import", artifact_id, new_uuid
    )
    return new_uuid


def _upsert_composite_artifact_row(
    session: Session,
    composite_id: str,
    collection_id: str,
    description: Optional[str] = None,
    display_name: Optional[str] = None,
    composite_type: str = "plugin",
) -> CompositeArtifact:
    """Create or update a CompositeArtifact row for a freshly imported composite.

    Args:
        session: Database session
        composite_id: Composite artifact id in ``composite:name`` format
        collection_id: Owning collection id (e.g. ``"default"``)
        description: Optional human-readable description
        display_name: Optional display name (defaults to bare artifact name)
        composite_type: Composite variant — ``"plugin"``, ``"stack"``, or ``"suite"``

    Returns:
        CompositeArtifact ORM instance (not yet committed — caller commits)
    """
    existing = (
        session.query(CompositeArtifact)
        .filter(CompositeArtifact.id == composite_id)
        .first()
    )

    if existing:
        existing.collection_id = collection_id
        if description is not None:
            existing.description = description
        if display_name is not None:
            existing.display_name = display_name
        existing.updated_at = datetime.utcnow()
        logger.debug("Updated CompositeArtifact row for '%s'", composite_id)
        return existing

    composite_row = CompositeArtifact(
        id=composite_id,
        collection_id=collection_id,
        composite_type=composite_type,
        description=description,
        display_name=display_name,
    )
    session.add(composite_row)
    logger.debug("Created CompositeArtifact row for '%s'", composite_id)
    return composite_row


def create_or_update_collection_artifact(
    session: Session,
    collection_id: str,
    artifact_id: str,
    metadata: dict,
) -> CollectionArtifact:
    """Create or update a CollectionArtifact row with full metadata.

    Pure DB upsert -- no filesystem reads, no manager dependencies.
    Sets synced_at = utcnow() automatically. On create, also sets added_at.

    Args:
        session: DB session
        collection_id: Collection ID (e.g., "default")
        artifact_id: Full artifact ID (e.g., "skill:1password")
        metadata: Dict with metadata fields (description, source, origin,
                  origin_source, tags_json, author, license, tools_json,
                  version, resolved_sha, resolved_version, etc.)

    Returns:
        CollectionArtifact ORM instance (committed)

    Raises:
        ValueError: If artifact_id cannot be resolved to an artifact UUID.
    """
    # Resolve type:name → uuid via the Artifact table (CAI-P5-05)
    artifact_uuid = _resolve_artifact_uuid(session, artifact_id)
    if not artifact_uuid:
        raise ValueError(
            f"Cannot upsert CollectionArtifact: artifact '{artifact_id}' not found "
            "in the artifacts cache. Ensure the artifact is imported before caching."
        )

    assoc = (
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection_id, artifact_uuid=artifact_uuid)
        .first()
    )

    metadata_with_timestamp = {
        **metadata,
        "synced_at": datetime.utcnow(),
    }

    if assoc:
        for key, value in metadata_with_timestamp.items():
            setattr(assoc, key, value)
        logger.debug(f"Updated cache for artifact: {artifact_id}")
    else:
        assoc = CollectionArtifact(
            collection_id=collection_id,
            artifact_uuid=artifact_uuid,
            added_at=datetime.utcnow(),
            **metadata_with_timestamp,
        )
        session.add(assoc)
        logger.debug(f"Created cache entry for artifact: {artifact_id}")

    session.commit()
    return assoc


def refresh_single_artifact_cache(
    session: Session,
    artifact_mgr,
    artifact_id: str,
    collection_id: str = "default",
    deployment_profile_id: Optional[str] = None,
) -> bool:
    """Refresh cache for a single artifact after file operation.

    Reads the artifact from the filesystem via artifact_mgr and updates
    the CollectionArtifact row with current metadata. If no row exists,
    creates one.

    Args:
        session: Database session
        artifact_mgr: ArtifactManager instance with show() method
        artifact_id: Artifact ID in 'type:name' format
        collection_id: Collection to update (defaults to 'default')
        deployment_profile_id: Optional profile context for logging/tracing

    Returns:
        True if refresh succeeded, False otherwise

    Note:
        This function commits the session on success. On failure, it logs
        a warning but does not raise - callers should handle the False
        return value if needed.
    """
    if ":" not in artifact_id:
        logger.warning(f"Invalid artifact_id format: {artifact_id}")
        return False

    artifact_type, artifact_name = artifact_id.split(":", 1)

    try:
        file_artifact = artifact_mgr.show(artifact_name)
        if not file_artifact:
            logger.warning(f"Artifact not found in file system: {artifact_id}")
            return False

        # Build metadata dict from file artifact
        metadata = {
            "description": (
                file_artifact.metadata.description if file_artifact.metadata else None
            ),
            "author": (
                file_artifact.metadata.author if file_artifact.metadata else None
            ),
            "license": (
                file_artifact.metadata.license if file_artifact.metadata else None
            ),
            "tags_json": (
                json.dumps(file_artifact.tags) if file_artifact.tags else None
            ),
            "tools_json": (
                json.dumps(file_artifact.metadata.tools)
                if file_artifact.metadata and file_artifact.metadata.tools
                else None
            ),
            "version": (
                file_artifact.metadata.version if file_artifact.metadata else None
            ),
            "source": getattr(file_artifact, "upstream", None),
            "origin": getattr(file_artifact, "origin", None),
            "origin_source": getattr(file_artifact, "origin_source", None),
            "resolved_sha": getattr(file_artifact, "resolved_sha", None),
            "resolved_version": getattr(file_artifact, "resolved_version", None),
        }

        # Delegate to shared upsert
        assoc = create_or_update_collection_artifact(
            session, collection_id, artifact_id, metadata
        )

        # Sync tags to Tag ORM tables — pass artifact_uuid (ADR-007), not type:name
        if file_artifact.tags:
            try:
                from skillmeat.core.services import TagService

                TagService().sync_artifact_tags(assoc.artifact_uuid, file_artifact.tags)
            except Exception as e:
                logger.warning(f"Tag ORM sync failed for {artifact_id}: {e}")

        logger.debug(
            "Refreshed cache for artifact: %s (profile=%s)",
            artifact_id,
            deployment_profile_id or "all",
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to refresh cache for {artifact_id}: {e}")
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return False


def populate_collection_artifact_from_import(
    session: Session,
    artifact_mgr,
    collection_id: str,
    entry,
) -> CollectionArtifact:
    """Populate a CollectionArtifact from an import result and filesystem data.

    Import-specific helper that combines data already available in memory
    (from the ImportEntry) with filesystem artifact metadata (via
    artifact_mgr.show()) to create a fully populated DB cache row in a
    single operation.

    For composite artifacts, ``artifact_mgr.show()`` is skipped entirely
    because the ArtifactManager does not understand the composite type.
    Metadata is built solely from the ImportEntry fields, the Artifact row
    is created on-the-fly if absent, and a CompositeArtifact row is also
    created/updated so that the composite is queryable via the DB.

    Args:
        session: DB session
        artifact_mgr: ArtifactManager instance with show() method
        collection_id: Collection ID (e.g., "default")
        entry: An ImportEntry object with .name, .artifact_type, .description,
               .upstream_url, .tags fields

    Returns:
        CollectionArtifact ORM instance (committed)

    Raises:
        Exception: If artifact_mgr.show() fails or DB commit fails.
                   Callers should handle exceptions appropriately.
    """
    artifact_id = f"{entry.artifact_type}:{entry.name}"

    # Ensure the Artifact FK target exists for all imported artifact types.
    _ensure_artifact_row(
        session,
        artifact_id=artifact_id,
        artifact_type=entry.artifact_type,
        artifact_name=entry.name,
        source=entry.upstream_url,
    )

    # --- Composite branch -----------------------------------------------
    # ArtifactManager.show() does not handle the "composite" type. For
    # composites we build metadata purely from ImportEntry fields and
    # ensure that the required Artifact row exists before delegating to the
    # shared upsert helper.
    if entry.artifact_type == "composite":
        # Also create/update the CompositeArtifact record so that the
        # composite is visible through the composite-specific endpoints.
        _upsert_composite_artifact_row(
            session,
            composite_id=artifact_id,
            collection_id=collection_id,
            description=entry.description,
            display_name=entry.name,
            composite_type="plugin",  # Marketplace composites are plugins by default
        )

        metadata = {
            "description": entry.description,
            "source": entry.upstream_url,
            "origin": "marketplace",
            "origin_source": "github",
            "tags_json": json.dumps(entry.tags) if entry.tags else None,
            # Filesystem-only fields are unavailable for composites; leave as None
            "author": None,
            "license": None,
            "tools_json": None,
            "version": None,
            "resolved_sha": None,
            "resolved_version": None,
        }

        result = create_or_update_collection_artifact(
            session, collection_id, artifact_id, metadata
        )

        if entry.tags:
            try:
                from skillmeat.core.services import TagService

                TagService().sync_artifact_tags(result.artifact_uuid, entry.tags)
            except Exception as e:
                logger.warning(f"Tag ORM sync failed for {artifact_id}: {e}")

        return result
    # --- End composite branch -------------------------------------------

    # Read filesystem for fields not available in ImportEntry
    # (author, license, tools, version, resolved_sha, resolved_version)
    file_artifact = artifact_mgr.show(entry.name)

    # Combine ImportEntry data (already in memory) with filesystem data
    metadata = {
        "description": entry.description
        or (
            file_artifact.metadata.description
            if file_artifact and file_artifact.metadata
            else None
        ),
        "source": entry.upstream_url,
        "origin": "marketplace",
        "origin_source": "github",
        "tags_json": json.dumps(entry.tags) if entry.tags else None,
        # Fields only available from filesystem:
        "author": (
            file_artifact.metadata.author
            if file_artifact and file_artifact.metadata
            else None
        ),
        "license": (
            file_artifact.metadata.license
            if file_artifact and file_artifact.metadata
            else None
        ),
        "tools_json": (
            json.dumps(file_artifact.metadata.tools)
            if file_artifact and file_artifact.metadata and file_artifact.metadata.tools
            else None
        ),
        "version": (
            file_artifact.metadata.version
            if file_artifact and file_artifact.metadata
            else None
        ),
        "resolved_sha": (
            getattr(file_artifact, "resolved_sha", None) if file_artifact else None
        ),
        "resolved_version": (
            getattr(file_artifact, "resolved_version", None) if file_artifact else None
        ),
    }

    result = create_or_update_collection_artifact(
        session, collection_id, artifact_id, metadata
    )

    # Sync tags to Tag ORM tables — pass artifact_uuid (ADR-007), not type:name
    tags = entry.tags or (file_artifact.tags if file_artifact else None)
    if tags:
        try:
            from skillmeat.core.services import TagService

            TagService().sync_artifact_tags(result.artifact_uuid, tags)
        except Exception as e:
            logger.warning(f"Tag ORM sync failed for {artifact_id}: {e}")

    return result


def invalidate_artifact_cache(
    session: Session,
    artifact_id: str,
    collection_id: str = "default",
) -> bool:
    """Invalidate (mark stale) cache for an artifact.

    Sets synced_at to NULL, marking the cache as needing refresh.
    Used when we know the file has changed but don't have new data yet,
    or when an artifact is deleted.

    Args:
        session: Database session
        artifact_id: Artifact ID in 'type:name' format
        collection_id: Collection to update (defaults to 'default')

    Returns:
        True if invalidation succeeded (or row didn't exist), False on error
    """
    try:
        assoc = _get_collection_artifact(session, collection_id, artifact_id)
        if assoc:
            assoc.synced_at = None
            session.commit()
            logger.debug(f"Invalidated cache for artifact: {artifact_id}")
            return True
        else:
            # No cache entry to invalidate - that's fine
            logger.debug(f"No cache entry to invalidate for artifact: {artifact_id}")
            return True
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for {artifact_id}: {e}")
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return False


def delete_artifact_cache(
    session: Session,
    artifact_id: str,
    collection_id: str = "default",
) -> bool:
    """Delete cache entry for an artifact.

    Completely removes the CollectionArtifact row. Used after artifact deletion
    to clean up the cache.

    Args:
        session: Database session
        artifact_id: Artifact ID in 'type:name' format
        collection_id: Collection to update (defaults to 'default')

    Returns:
        True if deletion succeeded (or row didn't exist), False on error
    """
    try:
        assoc = _get_collection_artifact(session, collection_id, artifact_id)
        if assoc:
            session.delete(assoc)
            session.commit()
            logger.debug(f"Deleted cache entry for artifact: {artifact_id}")
            return True
        else:
            # No cache entry to delete - that's fine
            logger.debug(f"No cache entry to delete for artifact: {artifact_id}")
            return True
    except Exception as e:
        logger.warning(f"Failed to delete cache for {artifact_id}: {e}")
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return False


def find_stale_artifacts(
    session: Session,
    ttl_seconds: int = DEFAULT_METADATA_TTL_SECONDS,
) -> list:
    """Find artifacts where cached metadata is stale.

    An artifact is considered stale if:
    - synced_at is NULL (never synced)
    - synced_at < now - TTL

    Args:
        session: Database session
        ttl_seconds: Time-to-live for cached metadata (default 30 min)

    Returns:
        List of CollectionArtifact objects with stale metadata
    """
    cutoff_time = datetime.utcnow() - timedelta(seconds=ttl_seconds)

    stale_artifacts = (
        session.query(CollectionArtifact)
        .filter(
            (CollectionArtifact.synced_at.is_(None))
            | (CollectionArtifact.synced_at < cutoff_time)
        )
        .all()
    )

    return stale_artifacts


def get_staleness_stats(
    session: Session,
    ttl_seconds: int = DEFAULT_METADATA_TTL_SECONDS,
) -> dict:
    """Get statistics about cache staleness.

    Args:
        session: Database session
        ttl_seconds: Time-to-live for cached metadata (default 30 min)

    Returns:
        dict with: total_artifacts, stale_count, fresh_count,
                   oldest_sync_age_seconds, percentage_stale, ttl_seconds
    """
    total = session.query(CollectionArtifact).count()

    if total == 0:
        return {
            "total_artifacts": 0,
            "stale_count": 0,
            "fresh_count": 0,
            "oldest_sync_age_seconds": 0,
            "percentage_stale": 0.0,
            "ttl_seconds": ttl_seconds,
        }

    stale = find_stale_artifacts(session, ttl_seconds)

    # Find oldest sync time
    oldest = (
        session.query(CollectionArtifact.synced_at)
        .filter(CollectionArtifact.synced_at.isnot(None))
        .order_by(CollectionArtifact.synced_at.asc())
        .first()
    )

    oldest_age = None
    if oldest and oldest[0]:
        oldest_age = (datetime.utcnow() - oldest[0]).total_seconds()

    return {
        "total_artifacts": total,
        "stale_count": len(stale),
        "fresh_count": total - len(stale),
        "oldest_sync_age_seconds": oldest_age or 0,
        "percentage_stale": round((len(stale) / total * 100), 1) if total > 0 else 0.0,
        "ttl_seconds": ttl_seconds,
    }


def invalidate_collection_artifacts(
    session: Session,
    collection_id: str,
) -> int:
    """Invalidate cache for all artifacts in a collection.

    Sets synced_at to NULL for all artifacts in the collection,
    marking them as needing refresh.

    Args:
        session: Database session
        collection_id: Collection ID

    Returns:
        Number of artifacts invalidated
    """
    try:
        # Update all artifacts in the collection
        updated_count = (
            session.query(CollectionArtifact)
            .filter(CollectionArtifact.collection_id == collection_id)
            .update({CollectionArtifact.synced_at: None})
        )
        session.commit()
        logger.debug(
            f"Invalidated cache for {updated_count} artifacts in collection: {collection_id}"
        )
        return updated_count
    except Exception as e:
        logger.warning(
            f"Failed to invalidate cache for collection {collection_id}: {e}"
        )
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return 0


# =============================================================================
# Cache Monitoring Metrics (TASK-3.4)
# =============================================================================


def log_cache_metrics(
    session: Session,
    ttl_seconds: int = DEFAULT_METADATA_TTL_SECONDS,
) -> dict:
    """Log cache health metrics for monitoring.

    Logs cache staleness statistics at INFO level and returns the stats dict.
    This function is useful for periodic health checks and observability.

    Args:
        session: Database session
        ttl_seconds: TTL in seconds for staleness calculation (default 30 min)

    Returns:
        Dictionary with staleness statistics (same as get_staleness_stats)

    Example:
        >>> stats = log_cache_metrics(session)
        Cache metrics: total=42, fresh=40, stale=2 (4.8%), oldest_age=1200s
    """
    stats = get_staleness_stats(session, ttl_seconds)

    logger.info(
        f"Cache metrics: "
        f"total={stats['total_artifacts']}, "
        f"fresh={stats['fresh_count']}, "
        f"stale={stats['stale_count']} ({stats['percentage_stale']}%), "
        f"oldest_age={stats['oldest_sync_age_seconds']:.0f}s"
    )

    return stats


# =============================================================================
# Deployment JSON Parsing
# =============================================================================


def parse_deployments(
    deployments_json: Optional[str],
) -> Optional[list[DeploymentSummary]]:
    """Parse deployments_json field from CollectionArtifact into DeploymentSummary list.

    Handles both old-format JSON (project_path, project_name, deployed_at only)
    and new-format JSON (with content_hash, deployment_profile_id,
    local_modifications, platform).

    Args:
        deployments_json: JSON string containing deployment data

    Returns:
        List of DeploymentSummary objects, or None if empty/invalid
    """
    if not deployments_json:
        return None

    try:
        deployments_data = json.loads(deployments_json)
        if not deployments_data or not isinstance(deployments_data, list):
            return None

        # Parse each deployment dict into DeploymentSummary
        deployments = []
        for dep in deployments_data:
            try:
                # Parse deployed_at timestamp if it's a string
                deployed_at = dep.get("deployed_at")
                if isinstance(deployed_at, str):
                    deployed_at = datetime.fromisoformat(
                        deployed_at.replace("Z", "+00:00")
                    )
                elif not isinstance(deployed_at, datetime):
                    continue  # Skip invalid entries

                deployments.append(
                    DeploymentSummary(
                        project_path=dep.get("project_path", ""),
                        project_name=dep.get("project_name", ""),
                        deployed_at=deployed_at,
                        content_hash=dep.get("content_hash"),
                        deployment_profile_id=dep.get("deployment_profile_id"),
                        local_modifications=dep.get("local_modifications"),
                        platform=dep.get("platform"),
                    )
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid deployment entry: {e}")
                continue

        return deployments if deployments else None

    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"Failed to parse deployments_json: {e}")
        return None


# =============================================================================
# Surgical Deployment Cache Helpers
# =============================================================================


def add_deployment_to_cache(
    session: Session,
    artifact_id: str,
    project_path: str,
    project_name: str,
    deployed_at: datetime | str,
    content_hash: Optional[str] = None,
    deployment_profile_id: Optional[str] = None,
    local_modifications: bool = False,
    platform: Optional[str] = None,
    collection_id: str = "default",
) -> bool:
    """Add or update a deployment entry in an artifact's deployments_json cache.

    Performs a surgical update of the deployments_json column without requiring
    a full cache refresh. If an entry with matching project_path +
    deployment_profile_id already exists, it is updated in-place; otherwise a
    new entry is appended.

    Args:
        session: Database session
        artifact_id: Artifact ID in 'type:name' format
        project_path: Filesystem path of the project deployment target
        project_name: Human-readable project name
        deployed_at: Deployment timestamp (datetime or ISO string)
        content_hash: Optional hash of deployed content
        deployment_profile_id: Optional deployment profile identifier
        local_modifications: Whether local modifications exist
        platform: Optional platform identifier
        collection_id: Collection to update (defaults to 'default')

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        assoc = _get_collection_artifact(session, collection_id, artifact_id)
        if not assoc:
            logger.warning(
                "Cannot add deployment cache — artifact not found: %s (collection=%s)",
                artifact_id,
                collection_id,
            )
            return False

        # Parse existing deployments
        deployments: list[dict] = []
        if assoc.deployments_json:
            try:
                deployments = json.loads(assoc.deployments_json)
                if not isinstance(deployments, list):
                    logger.warning(
                        "Malformed deployments_json for %s — resetting to empty list",
                        artifact_id,
                    )
                    deployments = []
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Unparseable deployments_json for %s — resetting to empty list",
                    artifact_id,
                )
                deployments = []

        # Normalize deployed_at to ISO string
        if isinstance(deployed_at, datetime):
            deployed_at_str = deployed_at.isoformat()
        else:
            deployed_at_str = str(deployed_at)

        # Build entry dict
        entry = {
            "project_path": project_path,
            "project_name": project_name,
            "deployed_at": deployed_at_str,
            "content_hash": content_hash,
            "deployment_profile_id": deployment_profile_id,
            "local_modifications": local_modifications,
            "platform": platform,
        }

        # Check for existing entry with matching project_path + profile
        found = False
        for i, existing in enumerate(deployments):
            if (
                existing.get("project_path") == project_path
                and existing.get("deployment_profile_id") == deployment_profile_id
            ):
                deployments[i] = entry
                found = True
                break

        if not found:
            deployments.append(entry)

        assoc.deployments_json = json.dumps(deployments)
        session.flush()

        logger.debug(
            "Added deployment to cache for %s → %s (profile=%s)",
            artifact_id,
            project_path,
            deployment_profile_id or "none",
        )
        return True

    except Exception as e:
        logger.warning("Failed to add deployment to cache for %s: %s", artifact_id, e)
        try:
            session.rollback()
        except Exception:
            pass
        return False


def remove_deployment_from_cache(
    session: Session,
    artifact_id: str,
    project_path: str,
    collection_id: str = "default",
    profile_id: Optional[str] = None,
) -> bool:
    """Remove a deployment entry from an artifact's deployments_json cache.

    Filters out entries matching the given project_path (and optionally
    profile_id) without requiring a full cache refresh.

    Args:
        session: Database session
        artifact_id: Artifact ID in 'type:name' format
        project_path: Filesystem path to match for removal
        collection_id: Collection to update (defaults to 'default')
        profile_id: If provided, only remove entries that also match this
                     deployment_profile_id

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        assoc = _get_collection_artifact(session, collection_id, artifact_id)
        if not assoc:
            logger.warning(
                "Cannot remove deployment cache — artifact not found: %s (collection=%s)",
                artifact_id,
                collection_id,
            )
            return False

        if not assoc.deployments_json:
            # Nothing to remove
            return True

        try:
            deployments = json.loads(assoc.deployments_json)
            if not isinstance(deployments, list):
                deployments = []
        except (json.JSONDecodeError, TypeError):
            # Malformed — treat as already empty
            return True

        # Filter out matching entries
        filtered = [
            d
            for d in deployments
            if not (
                d.get("project_path") == project_path
                and (profile_id is None or d.get("deployment_profile_id") == profile_id)
            )
        ]

        assoc.deployments_json = json.dumps(filtered) if filtered else None
        session.flush()

        removed_count = len(deployments) - len(filtered)
        logger.debug(
            "Removed %d deployment(s) from cache for %s (path=%s, profile=%s)",
            removed_count,
            artifact_id,
            project_path,
            profile_id or "any",
        )
        return True

    except Exception as e:
        logger.warning(
            "Failed to remove deployment from cache for %s: %s", artifact_id, e
        )
        try:
            session.rollback()
        except Exception:
            pass
        return False
