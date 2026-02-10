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
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import CollectionArtifact

logger = logging.getLogger(__name__)

# Default TTL for artifact metadata cache: 30 minutes
DEFAULT_METADATA_TTL_SECONDS = 30 * 60


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
    """
    assoc = (
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection_id, artifact_id=artifact_id)
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
            artifact_id=artifact_id,
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
            "deployments_json": None,  # Populated at collection level, not per-artifact
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
        create_or_update_collection_artifact(
            session, collection_id, artifact_id, metadata
        )

        # Sync tags to Tag ORM tables
        if file_artifact.tags:
            try:
                from skillmeat.core.services import TagService

                TagService().sync_artifact_tags(artifact_id, file_artifact.tags)
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

    # Read filesystem for fields not available in ImportEntry
    # (author, license, tools, version, resolved_sha, resolved_version)
    file_artifact = artifact_mgr.show(entry.name)

    # Combine ImportEntry data (already in memory) with filesystem data
    metadata = {
        "description": entry.description,
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

    # Sync tags to Tag ORM tables
    tags = entry.tags or (file_artifact.tags if file_artifact else None)
    if tags:
        try:
            from skillmeat.core.services import TagService

            TagService().sync_artifact_tags(artifact_id, tags)
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
        assoc = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=artifact_id)
            .first()
        )
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
        assoc = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=artifact_id)
            .first()
        )
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
