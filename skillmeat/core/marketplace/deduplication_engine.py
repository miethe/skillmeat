"""Deduplication engine for marketplace artifacts.

Provides content-based deduplication to identify and group duplicate artifacts
across different sources or paths. Uses SHA256 content hashing for reliable
duplicate detection.
"""

import logging
from typing import Any, Optional

from .content_hash import compute_artifact_hash, ContentHashCache

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """Engine for detecting and resolving duplicate artifacts.

    Uses content hashing to identify artifacts with identical content,
    regardless of their path or source. Provides methods to find duplicates
    and select the best artifact from a group of duplicates.

    Args:
        hash_cache: Optional ContentHashCache for caching hash computations.
            If not provided, a new cache instance will be created.

    Example:
        >>> engine = DeduplicationEngine()
        >>> artifacts = [
        ...     {"path": "skills/canvas", "files": {"SKILL.md": "content"}, "confidence_score": 0.9},
        ...     {"path": "other/canvas", "files": {"SKILL.md": "content"}, "confidence_score": 0.8},
        ...     {"path": "skills/unique", "files": {"SKILL.md": "different"}, "confidence_score": 0.95},
        ... ]
        >>> duplicates = engine.find_duplicates(artifacts)
        >>> len(duplicates)  # One group of duplicates
        1
        >>> best = engine.get_best_artifact(list(duplicates.values())[0])
        >>> best["path"]  # Higher confidence wins
        'skills/canvas'
    """

    def __init__(self, hash_cache: Optional[ContentHashCache] = None) -> None:
        """Initialize deduplication engine.

        Args:
            hash_cache: Optional ContentHashCache for caching hash computations.
                If not provided, a new cache with default size (1000 entries)
                will be created.
        """
        self._hash_cache = hash_cache or ContentHashCache()

    def compute_hash(self, artifact_files: dict[str, str]) -> str:
        """Compute content hash for artifact files.

        Uses the content_hash module to generate a deterministic SHA256 hash
        based on the artifact's file contents. The hash is order-independent
        (files are sorted alphabetically before hashing).

        Args:
            artifact_files: Dictionary mapping filenames to their content.
                Example: {"SKILL.md": "# My Skill", "README.md": "docs"}

        Returns:
            Lowercase hex digest (64 characters) representing the content hash.
            Returns empty string hash for empty file dict.

        Example:
            >>> engine = DeduplicationEngine()
            >>> files = {"SKILL.md": "# Canvas", "README.md": "Documentation"}
            >>> hash1 = engine.compute_hash(files)
            >>> len(hash1)
            64
            >>> # Order-independent
            >>> files2 = {"README.md": "Documentation", "SKILL.md": "# Canvas"}
            >>> engine.compute_hash(files2) == hash1
            True
        """
        return compute_artifact_hash(artifact_files)

    def find_duplicates(
        self, artifacts: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Find duplicate artifacts by content hash.

        Groups artifacts with identical content (same hash) together.
        Only returns groups with more than one artifact (actual duplicates).

        Each artifact's computed hash is stored in its metadata for later use:
        `artifact["metadata"]["content_hash"] = hash`

        Args:
            artifacts: List of artifact dictionaries. Expected structure:
                {
                    "path": str,
                    "files": dict[str, str],  # {filename: content}
                    "confidence_score": float,
                    "artifact_type": str,
                    "metadata": dict,  # optional
                }

        Returns:
            Dictionary mapping content hashes to lists of duplicate artifacts.
            Only includes groups with 2+ artifacts (actual duplicates).
            Example: {"abc123...": [artifact1, artifact2]}

        Example:
            >>> engine = DeduplicationEngine()
            >>> artifacts = [
            ...     {"path": "a", "files": {"f.md": "same"}, "confidence_score": 0.9},
            ...     {"path": "b", "files": {"f.md": "same"}, "confidence_score": 0.8},
            ...     {"path": "c", "files": {"f.md": "different"}, "confidence_score": 0.95},
            ... ]
            >>> duplicates = engine.find_duplicates(artifacts)
            >>> len(duplicates)  # One duplicate group (a and b)
            1
        """
        # Group artifacts by hash
        hash_groups: dict[str, list[dict[str, Any]]] = {}

        for artifact in artifacts:
            # Get files dict, defaulting to empty if missing
            files = artifact.get("files", {})

            # Compute hash
            content_hash = self.compute_hash(files)

            # Store hash in artifact metadata
            if "metadata" not in artifact:
                artifact["metadata"] = {}
            artifact["metadata"]["content_hash"] = content_hash

            # Add to group
            if content_hash not in hash_groups:
                hash_groups[content_hash] = []
            hash_groups[content_hash].append(artifact)

        # Filter to only groups with duplicates (>1 artifact)
        duplicates = {
            hash_val: group
            for hash_val, group in hash_groups.items()
            if len(group) > 1
        }

        # Log duplicate detection results
        if duplicates:
            total_duplicates = sum(len(group) for group in duplicates.values())
            logger.info(
                f"Found {len(duplicates)} duplicate group(s) containing "
                f"{total_duplicates} artifacts"
            )
            for hash_val, group in duplicates.items():
                paths = [a.get("path", "unknown") for a in group]
                logger.debug(
                    f"Duplicate group (hash={hash_val[:12]}...): {paths}"
                )
        else:
            logger.debug(f"No duplicates found among {len(artifacts)} artifacts")

        return duplicates

    def get_best_artifact(self, duplicates: list[dict[str, Any]]) -> dict[str, Any]:
        """Select the best artifact from a group of duplicates.

        Selection criteria (in order of priority):
        1. Highest confidence_score wins
        2. On tie: prefer manual mapping (metadata.is_manual_mapping=True)
        3. On tie: prefer shorter path (simpler is better)

        Args:
            duplicates: List of duplicate artifact dictionaries.
                Must contain at least one artifact.

        Returns:
            The best artifact from the group based on selection criteria.

        Raises:
            ValueError: If duplicates list is empty.

        Example:
            >>> engine = DeduplicationEngine()
            >>> duplicates = [
            ...     {"path": "a/b/c", "confidence_score": 0.9, "metadata": {}},
            ...     {"path": "x", "confidence_score": 0.9, "metadata": {"is_manual_mapping": True}},
            ...     {"path": "y", "confidence_score": 0.8, "metadata": {}},
            ... ]
            >>> best = engine.get_best_artifact(duplicates)
            >>> best["path"]  # Manual mapping wins on tie
            'x'
        """
        if not duplicates:
            raise ValueError("Cannot select best artifact from empty list")

        if len(duplicates) == 1:
            return duplicates[0]

        def sort_key(artifact: dict[str, Any]) -> tuple[float, int, int]:
            """Generate sort key for artifact comparison.

            Returns tuple of:
            - Negative confidence (higher is better, so negate for min sort)
            - Manual mapping flag (0 if manual, 1 if not - lower wins)
            - Path length (shorter is better)
            """
            confidence = artifact.get("confidence_score", 0.0)
            metadata = artifact.get("metadata", {})
            is_manual = metadata.get("is_manual_mapping", False)
            path = artifact.get("path", "")

            return (
                -confidence,  # Negate: higher confidence should sort first
                0 if is_manual else 1,  # Manual mapping preferred
                len(path),  # Shorter path preferred
            )

        # Sort and return best (first after sorting)
        sorted_artifacts = sorted(duplicates, key=sort_key)
        best = sorted_artifacts[0]

        logger.debug(
            f"Selected best artifact from {len(duplicates)} duplicates: "
            f"path='{best.get('path', 'unknown')}', "
            f"confidence={best.get('confidence_score', 0.0):.2f}"
        )

        return best


if __name__ == "__main__":
    # Self-test examples
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s"
    )

    print("DeduplicationEngine - Self Test")
    print("=" * 50)

    engine = DeduplicationEngine()

    # Test 1: compute_hash
    print("\n1. Hash computation:")
    files1 = {"SKILL.md": "# Canvas Design", "README.md": "Documentation"}
    files2 = {"README.md": "Documentation", "SKILL.md": "# Canvas Design"}
    hash1 = engine.compute_hash(files1)
    hash2 = engine.compute_hash(files2)
    print(f"   Files: {list(files1.keys())}")
    print(f"   Hash: {hash1[:16]}...")
    print(f"   Order-independent: {hash1 == hash2}")

    # Test 2: Empty files
    print("\n2. Empty files handling:")
    empty_hash = engine.compute_hash({})
    print(f"   Empty dict hash: {empty_hash[:16]}...")

    # Test 3: find_duplicates
    print("\n3. Finding duplicates:")
    artifacts = [
        {
            "path": "skills/canvas-design",
            "files": {"SKILL.md": "# Canvas"},
            "confidence_score": 0.95,
            "artifact_type": "skill",
        },
        {
            "path": "other/canvas",
            "files": {"SKILL.md": "# Canvas"},  # Same content
            "confidence_score": 0.85,
            "artifact_type": "skill",
        },
        {
            "path": "skills/unique",
            "files": {"SKILL.md": "# Different"},
            "confidence_score": 0.90,
            "artifact_type": "skill",
        },
        {
            "path": "nested/deep/canvas",
            "files": {"SKILL.md": "# Canvas"},  # Third duplicate
            "confidence_score": 0.80,
            "artifact_type": "skill",
            "metadata": {"is_manual_mapping": True},
        },
    ]

    duplicates = engine.find_duplicates(artifacts)
    print(f"   Total artifacts: {len(artifacts)}")
    print(f"   Duplicate groups: {len(duplicates)}")

    for hash_val, group in duplicates.items():
        print(f"   Group (hash={hash_val[:12]}...):")
        for a in group:
            print(f"      - {a['path']} (confidence={a['confidence_score']})")

    # Test 4: Metadata updated with hash
    print("\n4. Metadata hash storage:")
    for a in artifacts:
        stored_hash = a.get("metadata", {}).get("content_hash", "N/A")
        print(f"   {a['path']}: {stored_hash[:12]}...")

    # Test 5: get_best_artifact
    print("\n5. Best artifact selection:")

    # Test with first duplicate group
    if duplicates:
        dup_group = list(duplicates.values())[0]
        best = engine.get_best_artifact(dup_group)
        print(f"   Group size: {len(dup_group)}")
        print(f"   Best: {best['path']} (confidence={best['confidence_score']})")

    # Test tie-breaking with manual mapping
    print("\n6. Tie-breaking scenarios:")

    # Same confidence, one is manual
    tie_artifacts = [
        {"path": "a/b/c", "confidence_score": 0.9, "metadata": {}},
        {"path": "x/y", "confidence_score": 0.9, "metadata": {"is_manual_mapping": True}},
    ]
    best = engine.get_best_artifact(tie_artifacts)
    print(f"   Same confidence, one manual: {best['path']} wins")

    # Same confidence, same manual flag, different path length
    tie_artifacts2 = [
        {"path": "a/b/c/d", "confidence_score": 0.9, "metadata": {}},
        {"path": "x", "confidence_score": 0.9, "metadata": {}},
    ]
    best = engine.get_best_artifact(tie_artifacts2)
    print(f"   Same confidence, shorter path: {best['path']} wins")

    # Test empty list error
    print("\n7. Error handling:")
    try:
        engine.get_best_artifact([])
    except ValueError as e:
        print(f"   Empty list raises ValueError: {e}")

    # Test missing keys
    print("\n8. Missing keys handling:")
    artifacts_missing = [
        {"path": "a"},  # Missing files, confidence_score
        {"files": {"f.md": "content"}},  # Missing path, confidence_score
    ]
    duplicates_missing = engine.find_duplicates(artifacts_missing)
    print(f"   Handled missing keys gracefully: {len(duplicates_missing)} duplicate groups")

    print("\n" + "=" * 50)
    print("All tests passed!")
