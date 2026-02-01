"""Artifact metadata lookup service with fallback sequence.

This service provides a robust lookup mechanism for artifact metadata by
checking multiple sources in sequence:
1. Artifact cache table
2. Marketplace catalog entries
3. Minimal fallback with artifact_id

The service also retrieves associated metadata (description, author, tags)
and collection memberships to support consistent frontend Entity rendering.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from skillmeat.api.schemas.artifacts import ArtifactCollectionInfo
from skillmeat.api.schemas.user_collections import ArtifactSummary
from skillmeat.cache.models import (
    Artifact,
    Collection,
    CollectionArtifact,
    MarketplaceCatalogEntry,
)

logger = logging.getLogger(__name__)


def _parse_artifact_id(artifact_id: str) -> tuple[str, str]:
    """Parse artifact_id into (type, name).

    Artifact IDs follow format 'type:name' (e.g., 'agent:my-agent').
    Falls back to ('unknown', artifact_id) if format doesn't match.

    Args:
        artifact_id: Artifact identifier to parse

    Returns:
        Tuple of (artifact_type, artifact_name)
    """
    if ":" in artifact_id:
        parts = artifact_id.split(":", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
    return "unknown", artifact_id


def _lookup_in_cache(session: Session, artifact_id: str) -> Optional[Artifact]:
    """Look up artifact in cache table by ID.

    Args:
        session: Database session
        artifact_id: Artifact identifier to search for

    Returns:
        Artifact record if found, None otherwise
    """
    return session.query(Artifact).filter(Artifact.id == artifact_id).first()


def _lookup_in_marketplace(
    session: Session, artifact_id: str
) -> Optional[MarketplaceCatalogEntry]:
    """Look up artifact in marketplace catalog.

    Searches MarketplaceCatalogEntry by:
    - id matches artifact_id
    - import_id matches artifact_id
    - path contains artifact_id

    Args:
        session: Database session
        artifact_id: Artifact identifier to search for

    Returns:
        MarketplaceCatalogEntry if found, None otherwise
    """
    return (
        session.query(MarketplaceCatalogEntry)
        .filter(
            (MarketplaceCatalogEntry.id == artifact_id)
            | (MarketplaceCatalogEntry.import_id == artifact_id)
            | (MarketplaceCatalogEntry.path.contains(artifact_id))
        )
        .first()
    )


def _get_artifact_collections(
    session: Session, artifact_id: str
) -> List[ArtifactCollectionInfo]:
    """Get collections that an artifact belongs to.

    Queries the CollectionArtifact association table to find all
    collections containing this artifact.

    Args:
        session: Database session
        artifact_id: Artifact identifier to look up

    Returns:
        List of ArtifactCollectionInfo objects for each collection
    """
    # Query collection associations with collection details
    associations = (
        session.query(CollectionArtifact, Collection)
        .join(Collection, CollectionArtifact.collection_id == Collection.id)
        .filter(CollectionArtifact.artifact_id == artifact_id)
        .all()
    )

    collections = []
    for assoc, collection in associations:
        # Count artifacts in collection (using cached count would be better)
        artifact_count = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection.id)
            .count()
        )
        collections.append(
            ArtifactCollectionInfo(
                id=collection.id,
                name=collection.name,
                artifact_count=artifact_count,
            )
        )

    return collections


def _extract_artifact_tags(artifact: Artifact) -> Optional[List[str]]:
    """Extract tags from an artifact.

    Args:
        artifact: Artifact ORM instance with tags relationship

    Returns:
        List of tag names or None if no tags
    """
    if artifact.tags:
        return [tag.name for tag in artifact.tags]
    return None


def _extract_artifact_description(artifact: Artifact) -> Optional[str]:
    """Extract description from an artifact.

    Checks both the direct description field and the artifact_metadata
    relationship.

    Args:
        artifact: Artifact ORM instance

    Returns:
        Description string or None
    """
    # First check direct description field
    if artifact.description:
        return artifact.description

    # Fall back to artifact_metadata relationship
    if artifact.artifact_metadata and artifact.artifact_metadata.description:
        return artifact.artifact_metadata.description

    return None


def get_artifact_metadata(session: Session, artifact_id: str) -> ArtifactSummary:
    """Get artifact metadata with fallback sequence.

    Implements a 3-step lookup:
    1. Check Artifact cache table
    2. Check MarketplaceCatalogEntry
    3. Return minimal fallback

    Also retrieves associated metadata (description, author, tags) and
    collection memberships to support consistent frontend Entity rendering
    including collection badges.

    Args:
        session: Database session
        artifact_id: Artifact identifier to look up

    Returns:
        ArtifactSummary with metadata from first successful lookup or fallback

    Example:
        >>> metadata = get_artifact_metadata(session, "canvas-design")
        >>> print(metadata.name, metadata.type, metadata.version)
        canvas-design skill v1.2.0
    """
    # Get collection memberships (used for all cases)
    collections = _get_artifact_collections(session, artifact_id)

    # Step 1: Try cache table
    artifact = _lookup_in_cache(session, artifact_id)
    if artifact:
        logger.debug(f"Cache hit for artifact_id={artifact_id}")

        # Extract description from artifact or its metadata
        description = _extract_artifact_description(artifact)

        # Extract tags from relationship
        tags = _extract_artifact_tags(artifact)

        # Extract author from metadata if available
        author = None
        if artifact.artifact_metadata:
            # Check if metadata_json contains author field
            if artifact.artifact_metadata.metadata_json:
                import json

                try:
                    metadata_dict = json.loads(artifact.artifact_metadata.metadata_json)
                    author = metadata_dict.get("author")
                except (json.JSONDecodeError, TypeError):
                    pass

        return ArtifactSummary(
            id=artifact_id,
            name=artifact.name,
            type=artifact.type,
            version=artifact.deployed_version or artifact.upstream_version,
            source=artifact.source or artifact_id,
            description=description,
            author=author,
            tags=tags,
            collections=collections if collections else None,
        )

    # Step 2: Try marketplace catalog
    entry = _lookup_in_marketplace(session, artifact_id)
    if entry:
        logger.debug(f"Marketplace hit for artifact_id={artifact_id}")

        # Marketplace entries may have description in detected_metadata
        description = None
        tags = None
        author = None
        if entry.detected_metadata:
            import json

            try:
                metadata_dict = (
                    json.loads(entry.detected_metadata)
                    if isinstance(entry.detected_metadata, str)
                    else entry.detected_metadata
                )
                description = metadata_dict.get("description")
                author = metadata_dict.get("author")
                tags = metadata_dict.get("tags")
            except (json.JSONDecodeError, TypeError):
                pass

        return ArtifactSummary(
            id=artifact_id,
            name=entry.name,
            type=entry.artifact_type,
            version=entry.detected_version,
            source=entry.upstream_url,
            description=description,
            author=author,
            tags=tags,
            collections=collections if collections else None,
        )

    # Step 3: Fallback to minimal metadata
    logger.debug(f"Fallback metadata for artifact_id={artifact_id}")
    parsed_type, parsed_name = _parse_artifact_id(artifact_id)
    return ArtifactSummary(
        id=artifact_id,
        name=parsed_name,
        type=parsed_type,
        version=None,
        source=artifact_id,
        description=None,
        author=None,
        tags=None,
        collections=collections if collections else None,
    )
