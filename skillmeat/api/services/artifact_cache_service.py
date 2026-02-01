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
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import CollectionArtifact

logger = logging.getLogger(__name__)


def refresh_single_artifact_cache(
    session: Session,
    artifact_mgr,
    artifact_id: str,
    collection_id: str = "default",
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

        # Find or create CollectionArtifact row
        assoc = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=artifact_id)
            .first()
        )

        # Build metadata fields from file artifact
        metadata_fields = {
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
                json.dumps(file_artifact.metadata.tags)
                if file_artifact.metadata and file_artifact.metadata.tags
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
            "synced_at": datetime.utcnow(),
        }

        if assoc:
            # Update existing row
            for key, value in metadata_fields.items():
                setattr(assoc, key, value)
            logger.debug(f"Updated cache for artifact: {artifact_id}")
        else:
            # Create new row
            new_assoc = CollectionArtifact(
                collection_id=collection_id,
                artifact_id=artifact_id,
                added_at=datetime.utcnow(),
                **metadata_fields,
            )
            session.add(new_assoc)
            logger.debug(f"Created cache entry for artifact: {artifact_id}")

        session.commit()
        logger.debug(f"Refreshed cache for artifact: {artifact_id}")
        return True

    except Exception as e:
        logger.warning(f"Failed to refresh cache for {artifact_id}: {e}")
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return False


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
