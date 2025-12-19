"""Version lineage utilities for tracking artifact version history.

The version lineage is a list of content hashes representing the ancestry
of a version, ordered from oldest to newest (root to current).

This module provides utilities for:
- Building version lineage by extending parent lineage
- Finding common ancestors for three-way merge
- Querying version chains and history
- Checking version existence

These functions operate on the ArtifactVersion ORM model from cache.models
and are used by deployment and sync operations to maintain version history.
"""

import json
from typing import List, Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import ArtifactVersion


def build_version_lineage(
    session: Session,
    parent_hash: Optional[str],
    current_hash: str,
) -> List[str]:
    """Build version lineage by extending parent's lineage.

    The version lineage is an ordered list of content hashes from root to current,
    enabling fast ancestry queries for three-way merge operations.

    Algorithm:
    - If parent_hash is None (root version): lineage = [current_hash]
    - If parent exists with lineage: lineage = parent_lineage + [current_hash]
    - If parent exists without lineage (legacy): lineage = [parent_hash, current_hash]

    Args:
        session: Database session
        parent_hash: Content hash of parent version (None for root)
        current_hash: Content hash of current version

    Returns:
        List of content hashes from root to current (oldest to newest)

    Example:
        >>> # Root version (deployment)
        >>> lineage = build_version_lineage(session, None, "abc123")
        >>> assert lineage == ["abc123"]

        >>> # Child version (sync)
        >>> lineage = build_version_lineage(session, "abc123", "def456")
        >>> assert lineage == ["abc123", "def456"]
    """
    if parent_hash is None:
        # Root version - lineage is just self
        return [current_hash]

    # Get parent version to access its lineage
    parent = session.query(ArtifactVersion).filter_by(content_hash=parent_hash).first()

    if parent and parent.version_lineage:
        # Extend parent's lineage
        parent_lineage = json.loads(parent.version_lineage)
        return parent_lineage + [current_hash]
    elif parent:
        # Parent exists but doesn't have lineage (legacy) - create minimal chain
        return [parent_hash, current_hash]
    else:
        # Parent doesn't exist - treat as orphaned child
        # This can happen if parent version was never recorded (legacy data)
        return [current_hash]


def find_common_ancestor(
    session: Session,
    hash_a: str,
    hash_b: str,
) -> Optional[str]:
    """Find most recent common ancestor between two versions.

    Used for three-way merge to identify the base version. Compares version
    lineages to find the most recent shared ancestor hash.

    Algorithm:
    1. Load both versions from database
    2. Parse their lineages (lists of ancestor hashes)
    3. Find intersection of lineages
    4. Return most recent common hash (latest in both lineages)

    Args:
        session: Database session
        hash_a: Content hash of first version
        hash_b: Content hash of second version

    Returns:
        Content hash of most recent common ancestor, or None if unrelated

    Example:
        >>> # Two versions with shared history
        >>> # Version A: ["root", "v1", "v2-local"]
        >>> # Version B: ["root", "v1", "v2-remote"]
        >>> ancestor = find_common_ancestor(session, "v2-local", "v2-remote")
        >>> assert ancestor == "v1"  # Most recent common ancestor

        >>> # Unrelated versions
        >>> ancestor = find_common_ancestor(session, "orphan-a", "orphan-b")
        >>> assert ancestor is None
    """
    version_a = session.query(ArtifactVersion).filter_by(content_hash=hash_a).first()
    version_b = session.query(ArtifactVersion).filter_by(content_hash=hash_b).first()

    if not version_a or not version_b:
        return None

    # Parse lineages (handle missing lineage gracefully)
    lineage_a = version_a.get_lineage_list() or []
    lineage_b = version_b.get_lineage_list() or []

    # If either lineage is empty, no common ancestor
    if not lineage_a or not lineage_b:
        return None

    # Convert to sets for efficient lookup
    set_a = set(lineage_a)
    set_b = set(lineage_b)

    # Find common hashes
    common = set_a & set_b

    if not common:
        return None

    # Return most recent common ancestor (last one in both lineages)
    # Walk lineage_a backwards to find first common hash
    for hash_ in reversed(lineage_a):
        if hash_ in common:
            return hash_

    return None


def get_version_chain(
    session: Session,
    artifact_id: str,
) -> List[ArtifactVersion]:
    """Get all versions for an artifact in chronological order.

    Returns complete version history for an artifact, useful for
    visualizing version trees or auditing changes.

    Args:
        session: Database session
        artifact_id: Artifact identifier

    Returns:
        List of ArtifactVersion records ordered by creation time (oldest first)

    Example:
        >>> versions = get_version_chain(session, "artifact_abc123")
        >>> for v in versions:
        ...     print(f"{v.created_at}: {v.change_origin} -> {v.content_hash[:8]}")
        2025-12-17 10:00:00: deployment -> abc12345
        2025-12-17 10:30:00: sync -> def67890
        2025-12-17 11:00:00: local_modification -> ghi11111
    """
    return (
        session.query(ArtifactVersion)
        .filter_by(artifact_id=artifact_id)
        .order_by(ArtifactVersion.created_at)
        .all()
    )


def get_latest_version(
    session: Session,
    artifact_id: str,
) -> Optional[ArtifactVersion]:
    """Get most recent version for an artifact.

    Useful for finding current state when processing updates or syncs.

    Args:
        session: Database session
        artifact_id: Artifact identifier

    Returns:
        Most recent ArtifactVersion or None if no versions exist

    Example:
        >>> latest = get_latest_version(session, "artifact_abc123")
        >>> if latest:
        ...     print(f"Current hash: {latest.content_hash}")
        ...     print(f"Last change: {latest.change_origin}")
    """
    return (
        session.query(ArtifactVersion)
        .filter_by(artifact_id=artifact_id)
        .order_by(ArtifactVersion.created_at.desc())
        .first()
    )


def version_exists(session: Session, content_hash: str) -> bool:
    """Check if a version with given content hash exists.

    Useful for deduplication - avoid creating duplicate version records
    for identical content.

    Args:
        session: Database session
        content_hash: Content hash to check

    Returns:
        True if version exists, False otherwise

    Example:
        >>> if not version_exists(session, new_hash):
        ...     create_version_record(session, new_hash)
    """
    return session.query(
        session.query(ArtifactVersion).filter_by(content_hash=content_hash).exists()
    ).scalar()


def get_version_by_hash(
    session: Session,
    content_hash: str,
) -> Optional[ArtifactVersion]:
    """Get version record by content hash.

    Retrieves a specific version by its content hash. Used when you have
    a hash from deployment records or lineage and need full version details.

    Args:
        session: Database session
        content_hash: Content hash of version to retrieve

    Returns:
        ArtifactVersion if found, None otherwise

    Example:
        >>> version = get_version_by_hash(session, "abc123...")
        >>> if version:
        ...     print(f"Origin: {version.change_origin}")
        ...     print(f"Parent: {version.parent_hash}")
    """
    return session.query(ArtifactVersion).filter_by(content_hash=content_hash).first()


def get_lineage_depth(
    session: Session,
    content_hash: str,
) -> int:
    """Get depth of version in lineage tree.

    Calculates how many generations separate this version from the root.
    Depth 0 = root version, depth 1 = direct child, etc.

    Args:
        session: Database session
        content_hash: Content hash of version

    Returns:
        Lineage depth (0 for root, 1+ for descendants)
        Returns 0 if version not found

    Example:
        >>> depth = get_lineage_depth(session, "abc123")
        >>> print(f"This version is {depth} generations from root")
    """
    version = (
        session.query(ArtifactVersion).filter_by(content_hash=content_hash).first()
    )

    if not version:
        return 0

    lineage = version.get_lineage_list()
    # Lineage includes current hash, so depth = len - 1
    return max(0, len(lineage) - 1) if lineage else 0


def get_root_version(
    session: Session,
    artifact_id: str,
) -> Optional[ArtifactVersion]:
    """Get root version (first version) for an artifact.

    Finds the earliest version record for an artifact. This is typically
    the initial deployment version.

    Args:
        session: Database session
        artifact_id: Artifact identifier

    Returns:
        Root ArtifactVersion or None if no versions exist

    Example:
        >>> root = get_root_version(session, "artifact_abc123")
        >>> if root:
        ...     print(f"Initial deployment: {root.created_at}")
        ...     print(f"Original hash: {root.content_hash}")
    """
    return (
        session.query(ArtifactVersion)
        .filter_by(artifact_id=artifact_id)
        .order_by(ArtifactVersion.created_at)
        .first()
    )


def trace_lineage_path(
    session: Session,
    from_hash: str,
    to_hash: str,
) -> Optional[List[str]]:
    """Trace path between two versions in lineage.

    Finds the sequence of hashes connecting two versions, if they're
    in the same lineage. Returns None if they're in different branches.

    Args:
        session: Database session
        from_hash: Starting content hash
        to_hash: Target content hash

    Returns:
        List of hashes from start to end (inclusive), or None if no path

    Example:
        >>> path = trace_lineage_path(session, "root", "current")
        >>> if path:
        ...     print(f"Path: {' -> '.join([h[:8] for h in path])}")
        Path: abc12345 -> def67890 -> ghi11111
    """
    # Get both versions
    from_version = (
        session.query(ArtifactVersion).filter_by(content_hash=from_hash).first()
    )
    to_version = session.query(ArtifactVersion).filter_by(content_hash=to_hash).first()

    if not from_version or not to_version:
        return None

    from_lineage = from_version.get_lineage_list() or []
    to_lineage = to_version.get_lineage_list() or []

    # Check if both hashes are in to_lineage (forward path)
    if from_hash in to_lineage and to_hash in to_lineage:
        from_index = to_lineage.index(from_hash)
        to_index = to_lineage.index(to_hash)
        return to_lineage[from_index : to_index + 1]

    # Check if both hashes are in from_lineage (backward path)
    if from_hash in from_lineage and to_hash in from_lineage:
        from_index = from_lineage.index(from_hash)
        to_index = from_lineage.index(to_hash)
        # Reverse the path since we're going backward
        return list(reversed(from_lineage[to_index : from_index + 1]))

    # No path exists
    return None
