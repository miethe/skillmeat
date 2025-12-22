"""Artifact metadata lookup service with fallback sequence.

This service provides a robust lookup mechanism for artifact metadata by
checking multiple sources in sequence:
1. Artifact cache table
2. Marketplace catalog entries
3. Minimal fallback with artifact_id
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.api.schemas.user_collections import ArtifactSummary
from skillmeat.cache.models import Artifact, MarketplaceCatalogEntry

logger = logging.getLogger(__name__)


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


def get_artifact_metadata(session: Session, artifact_id: str) -> ArtifactSummary:
    """Get artifact metadata with fallback sequence.

    Implements a 3-step lookup:
    1. Check Artifact cache table
    2. Check MarketplaceCatalogEntry
    3. Return minimal fallback

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
    # Step 1: Try cache table
    artifact = _lookup_in_cache(session, artifact_id)
    if artifact:
        logger.debug(f"Cache hit for artifact_id={artifact_id}")
        return ArtifactSummary(
            name=artifact.name,
            type=artifact.type,
            version=artifact.deployed_version or artifact.upstream_version,
            source=artifact.source or artifact_id,
        )

    # Step 2: Try marketplace catalog
    entry = _lookup_in_marketplace(session, artifact_id)
    if entry:
        logger.debug(f"Marketplace hit for artifact_id={artifact_id}")
        return ArtifactSummary(
            name=entry.name,
            type=entry.artifact_type,
            version=entry.detected_version,
            source=entry.upstream_url,
        )

    # Step 3: Fallback to minimal metadata
    logger.debug(f"Fallback metadata for artifact_id={artifact_id}")
    return ArtifactSummary(
        name=artifact_id,
        type="unknown",
        version=None,
        source=artifact_id,
    )
