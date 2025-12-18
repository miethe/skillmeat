"""Version tracking utilities for artifact deployments and syncs.

This module provides helper functions for creating and managing ArtifactVersion
records during deployment and sync operations.
"""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import ArtifactVersion


def create_deployment_version(
    session: Session,
    artifact_id: str,
    content_hash: str,
) -> ArtifactVersion:
    """Create version record for initial artifact deployment.

    Deployments have no parent (parent_hash=NULL) because they represent
    the introduction of a new artifact to the project. The version_lineage
    contains only the current hash.

    Args:
        session: SQLAlchemy database session
        artifact_id: The deployed artifact's ID
        content_hash: SHA-256 hash of the deployed artifact content

    Returns:
        ArtifactVersion record (existing or newly created)

    Note:
        This function is idempotent - calling it with the same content_hash
        will return the existing version record rather than creating a duplicate.
    """
    # Check if version already exists (content-based dedup)
    existing = (
        session.query(ArtifactVersion)
        .filter_by(content_hash=content_hash)
        .first()
    )

    if existing:
        return existing

    # Create new version record
    version = ArtifactVersion(
        artifact_id=artifact_id,
        content_hash=content_hash,
        parent_hash=None,  # Root version - no parent
        change_origin="deployment",
        version_lineage=json.dumps([content_hash]),
    )
    session.add(version)
    session.flush()  # Ensure ID is generated
    return version


def create_sync_version(
    session: Session,
    artifact_id: str,
    content_hash: str,
    parent_hash: str,
) -> ArtifactVersion:
    """Create version record for artifact sync from collection.

    Syncs have a parent (the previous deployed version) because they represent
    an update from the upstream collection.

    Args:
        session: SQLAlchemy database session
        artifact_id: The synced artifact's ID
        content_hash: SHA-256 hash of the synced artifact content
        parent_hash: Content hash of the parent version (previous deployment)

    Returns:
        ArtifactVersion record (existing or newly created)

    Note:
        This function is idempotent - calling it with the same content_hash
        will return the existing version record rather than creating a duplicate.
    """
    # Check if version already exists (content-based dedup)
    existing = (
        session.query(ArtifactVersion)
        .filter_by(content_hash=content_hash)
        .first()
    )

    if existing:
        return existing

    # Build lineage: parent's lineage + current hash
    parent_version = (
        session.query(ArtifactVersion)
        .filter_by(content_hash=parent_hash)
        .first()
    )

    if parent_version and parent_version.version_lineage:
        parent_lineage = json.loads(parent_version.version_lineage)
        lineage = [content_hash] + parent_lineage
    else:
        # Fallback: just parent + current
        lineage = [content_hash, parent_hash]

    # Create new version record
    version = ArtifactVersion(
        artifact_id=artifact_id,
        content_hash=content_hash,
        parent_hash=parent_hash,
        change_origin="sync",
        version_lineage=json.dumps(lineage),
    )
    session.add(version)
    session.flush()  # Ensure ID is generated
    return version


def create_local_modification_version(
    session: Session,
    artifact_id: str,
    content_hash: str,
    parent_hash: str,
) -> ArtifactVersion:
    """Create version record for local modification of deployed artifact.

    Local modifications have a parent (the previously deployed/synced version)
    because they represent user edits to an existing artifact.

    Args:
        session: SQLAlchemy database session
        artifact_id: The modified artifact's ID
        content_hash: SHA-256 hash of the modified artifact content
        parent_hash: Content hash of the parent version (before modification)

    Returns:
        ArtifactVersion record (existing or newly created)

    Note:
        This function is idempotent - calling it with the same content_hash
        will return the existing version record rather than creating a duplicate.
    """
    # Check if version already exists (content-based dedup)
    existing = (
        session.query(ArtifactVersion)
        .filter_by(content_hash=content_hash)
        .first()
    )

    if existing:
        return existing

    # Build lineage: parent's lineage + current hash
    parent_version = (
        session.query(ArtifactVersion)
        .filter_by(content_hash=parent_hash)
        .first()
    )

    if parent_version and parent_version.version_lineage:
        parent_lineage = json.loads(parent_version.version_lineage)
        lineage = [content_hash] + parent_lineage
    else:
        # Fallback: just parent + current
        lineage = [content_hash, parent_hash]

    # Create new version record
    version = ArtifactVersion(
        artifact_id=artifact_id,
        content_hash=content_hash,
        parent_hash=parent_hash,
        change_origin="local_modification",
        version_lineage=json.dumps(lineage),
    )
    session.add(version)
    session.flush()  # Ensure ID is generated
    return version


def get_latest_version(
    session: Session,
    artifact_id: str,
) -> Optional[ArtifactVersion]:
    """Get the most recent version for an artifact.

    Args:
        session: SQLAlchemy database session
        artifact_id: The artifact's ID

    Returns:
        Most recent ArtifactVersion or None if no versions exist
    """
    return (
        session.query(ArtifactVersion)
        .filter_by(artifact_id=artifact_id)
        .order_by(ArtifactVersion.created_at.desc())
        .first()
    )


def get_version_by_hash(
    session: Session,
    content_hash: str,
) -> Optional[ArtifactVersion]:
    """Get version record by content hash.

    Args:
        session: SQLAlchemy database session
        content_hash: SHA-256 hash of artifact content

    Returns:
        ArtifactVersion or None if not found
    """
    return (
        session.query(ArtifactVersion)
        .filter_by(content_hash=content_hash)
        .first()
    )
