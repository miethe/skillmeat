"""Content hashing service for change detection.

This module provides content hashing functionality for detecting changes between
collection entities and deployed files:
- SHA256 hash computation for entity content
- Change detection comparing collection vs deployed file hashes
- Graceful handling of missing files

Security:
    - Uses SHA256 from Python's hashlib (cryptographically secure)
    - Deterministic hashing (same content = same hash)
    - No external dependencies or network calls

Usage:
    >>> from pathlib import Path
    >>> from skillmeat.core.services.content_hash import compute_content_hash, detect_changes
    >>>
    >>> # Compute hash for content
    >>> content = "# My Skill\\n\\nThis is my skill content."
    >>> content_hash = compute_content_hash(content)
    >>>
    >>> # Detect if deployed file has changed
    >>> deployed_file = Path(".claude/skills/user/my-skill/SKILL.md")
    >>> has_changed = detect_changes(content_hash, deployed_file)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content.

    Uses SHA256 for cryptographically secure, deterministic hashing.
    Same content will always produce the same hash.

    Args:
        content: String content to hash (typically file content)

    Returns:
        Hex-encoded SHA256 hash (64 characters)

    Example:
        >>> content = "Hello, World!"
        >>> hash_value = compute_content_hash(content)
        >>> len(hash_value)
        64
        >>> # Same content produces same hash
        >>> compute_content_hash("Hello") == compute_content_hash("Hello")
        True
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def detect_changes(collection_hash: str, deployed_file_path: str | Path) -> bool:
    """Detect if deployed file differs from collection entity.

    Compares the hash of the deployed file content with the collection
    entity's content hash. Returns True if they differ (change detected).

    Args:
        collection_hash: SHA256 hash from collection entity (64 hex chars)
        deployed_file_path: Path to deployed file to check

    Returns:
        True if file differs from collection (change detected)
        False if file matches collection or doesn't exist

    Note:
        Returns False (no change) if file doesn't exist, as this is not
        considered a "local modification" - it's a missing deployment.

    Example:
        >>> from pathlib import Path
        >>> collection_hash = compute_content_hash("original content")
        >>> deployed_file = Path("/tmp/test.md")
        >>>
        >>> # File doesn't exist - no change
        >>> detect_changes(collection_hash, deployed_file)
        False
        >>>
        >>> # File exists with different content - change detected
        >>> deployed_file.write_text("modified content")
        >>> detect_changes(collection_hash, deployed_file)
        True
        >>>
        >>> # File exists with same content - no change
        >>> deployed_file.write_text("original content")
        >>> detect_changes(collection_hash, deployed_file)
        False
    """
    deployed_path = Path(deployed_file_path)

    # File doesn't exist - not considered a change
    if not deployed_path.exists():
        return False

    # File is not a regular file (directory, symlink, etc.)
    if not deployed_path.is_file():
        return False

    # Read deployed file and compute hash
    try:
        deployed_content = deployed_path.read_text(encoding="utf-8")
        deployed_hash = compute_content_hash(deployed_content)
    except (OSError, UnicodeDecodeError):
        # Cannot read file - treat as no change (safer default)
        return False

    # Compare hashes
    return deployed_hash != collection_hash


def read_file_with_hash(file_path: str | Path) -> tuple[str, str]:
    """Read file content and compute its hash.

    Convenience function for reading a file and computing its hash
    in a single operation.

    Args:
        file_path: Path to file to read

    Returns:
        Tuple of (content, hash) where hash is SHA256 hex digest

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be read
        UnicodeDecodeError: If file is not valid UTF-8 text

    Example:
        >>> from pathlib import Path
        >>> test_file = Path("/tmp/test.md")
        >>> test_file.write_text("# Test\\n\\nContent here.")
        >>> content, hash_value = read_file_with_hash(test_file)
        >>> len(content) > 0
        True
        >>> len(hash_value)
        64
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    content_hash = compute_content_hash(content)
    return content, content_hash


def update_artifact_hash(
    artifact_content: str,
) -> str:
    """Compute hash for artifact content to be stored in database.

    Helper function for updating artifact content_hash field when
    content changes (during import, sync, update operations).

    Args:
        artifact_content: Full content of the artifact (e.g., SKILL.md content)

    Returns:
        SHA256 hash to store in artifact.content_hash field

    Example:
        >>> from skillmeat.cache.models import Artifact
        >>> artifact = Artifact(
        ...     id="art_abc123",
        ...     name="my-skill",
        ...     type="skill",
        ...     project_id="proj_123"
        ... )
        >>> content = Path(".claude/skills/user/my-skill/SKILL.md").read_text()
        >>> artifact.content_hash = update_artifact_hash(content)
    """
    return compute_content_hash(artifact_content)


def verify_content_integrity(expected_hash: str, actual_content: str) -> bool:
    """Verify content matches expected hash.

    Useful for validating content integrity after downloads,
    imports, or other operations where content may have been
    corrupted or tampered with.

    Args:
        expected_hash: Expected SHA256 hash (64 hex chars)
        actual_content: Actual content to verify

    Returns:
        True if content matches expected hash, False otherwise

    Example:
        >>> content = "# My Skill"
        >>> expected = compute_content_hash(content)
        >>> verify_content_integrity(expected, content)
        True
        >>> verify_content_integrity(expected, "# Modified Skill")
        False
    """
    actual_hash = compute_content_hash(actual_content)
    return actual_hash == expected_hash
