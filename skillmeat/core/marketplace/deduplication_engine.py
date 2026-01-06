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

    def deduplicate_within_source(
        self, artifacts: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Deduplicate artifacts within a single source scan.

        Stage 1 deduplication: removes duplicates found within the same
        marketplace source. For each group of duplicates (same content hash),
        keeps the best artifact and marks others for exclusion.

        Args:
            artifacts: List of artifact dictionaries from a single source scan.
                Expected structure:
                {
                    "path": str,
                    "files": dict[str, str],
                    "confidence_score": float,
                    "artifact_type": str,
                    "metadata": dict,  # optional
                }

        Returns:
            Tuple of (kept_artifacts, excluded_artifacts):
            - kept_artifacts: Unique artifacts + best from each duplicate group
            - excluded_artifacts: Duplicates marked with exclusion metadata:
                - excluded = True
                - excluded_reason = "duplicate_within_source"
                - duplicate_of = path of the kept artifact
                - content_hash = hash value for reference

        Example:
            >>> engine = DeduplicationEngine()
            >>> artifacts = [
            ...     {"path": "skills/a", "files": {"SKILL.md": "same"}, "confidence_score": 0.8},
            ...     {"path": "skills/b", "files": {"SKILL.md": "same"}, "confidence_score": 0.9},
            ...     {"path": "other/c", "files": {"SKILL.md": "different"}, "confidence_score": 0.7},
            ... ]
            >>> kept, excluded = engine.deduplicate_within_source(artifacts)
            >>> len(kept)  # skills/b (winner) + other/c (unique)
            2
            >>> len(excluded)  # skills/a (duplicate of skills/b)
            1
            >>> excluded[0]["excluded"]
            True
            >>> excluded[0]["duplicate_of"]
            'skills/b'
        """
        if not artifacts:
            logger.debug("No artifacts to deduplicate")
            return [], []

        # Build hash groups for all artifacts (including unique ones)
        hash_groups: dict[str, list[dict[str, Any]]] = {}

        for artifact in artifacts:
            files = artifact.get("files", {})
            content_hash = self.compute_hash(files)

            # Store hash in artifact metadata
            if "metadata" not in artifact:
                artifact["metadata"] = {}
            artifact["metadata"]["content_hash"] = content_hash

            if content_hash not in hash_groups:
                hash_groups[content_hash] = []
            hash_groups[content_hash].append(artifact)

        kept_artifacts: list[dict[str, Any]] = []
        excluded_artifacts: list[dict[str, Any]] = []

        for content_hash, group in hash_groups.items():
            if len(group) == 1:
                # Unique artifact - keep as-is
                kept_artifacts.append(group[0])
            else:
                # Duplicate group - select best, exclude others
                best = self.get_best_artifact(group)
                best_path = best.get("path", "unknown")

                kept_artifacts.append(best)

                # Mark others as excluded
                for artifact in group:
                    if artifact is not best:
                        artifact["excluded"] = True
                        artifact["excluded_reason"] = "duplicate_within_source"
                        artifact["duplicate_of"] = best_path
                        artifact["content_hash"] = content_hash
                        excluded_artifacts.append(artifact)

        # Log summary
        total = len(artifacts)
        kept_count = len(kept_artifacts)
        excluded_count = len(excluded_artifacts)

        logger.info(
            f"Deduplicated {total} artifacts within source, "
            f"kept {kept_count}, excluded {excluded_count}"
        )

        if excluded_count > 0:
            logger.debug(
                f"Excluded duplicates: "
                f"{[a.get('path', 'unknown') for a in excluded_artifacts]}"
            )

        return kept_artifacts, excluded_artifacts


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

    # Test 9: deduplicate_within_source
    print("\n9. Within-source deduplication:")
    engine2 = DeduplicationEngine()  # Fresh engine
    source_artifacts = [
        {
            "path": "skills/a",
            "files": {"SKILL.md": "same content"},
            "confidence_score": 0.8,
            "artifact_type": "skill",
        },
        {
            "path": "skills/b",
            "files": {"SKILL.md": "same content"},  # Duplicate of a
            "confidence_score": 0.9,  # Higher score - should win
            "artifact_type": "skill",
        },
        {
            "path": "other/c",
            "files": {"SKILL.md": "different content"},  # Unique
            "confidence_score": 0.7,
            "artifact_type": "skill",
        },
        {
            "path": "nested/d",
            "files": {"SKILL.md": "same content"},  # Third duplicate
            "confidence_score": 0.85,
            "artifact_type": "skill",
        },
    ]

    kept, excluded = engine2.deduplicate_within_source(source_artifacts)
    print(f"   Input: {len(source_artifacts)} artifacts")
    print(f"   Kept: {len(kept)} artifacts")
    print(f"   Excluded: {len(excluded)} artifacts")

    print("\n   Kept artifacts:")
    for a in kept:
        print(f"      - {a['path']} (confidence={a['confidence_score']})")

    print("\n   Excluded artifacts:")
    for a in excluded:
        print(f"      - {a['path']}")
        print(f"        excluded={a.get('excluded')}")
        print(f"        excluded_reason={a.get('excluded_reason')}")
        print(f"        duplicate_of={a.get('duplicate_of')}")
        print(f"        content_hash={a.get('content_hash', 'N/A')[:12]}...")

    # Verify expected results
    kept_paths = [a["path"] for a in kept]
    assert "skills/b" in kept_paths, "Best duplicate should be kept"
    assert "other/c" in kept_paths, "Unique artifact should be kept"
    assert len(excluded) == 2, f"Expected 2 excluded, got {len(excluded)}"

    for excl in excluded:
        assert excl.get("excluded") is True
        assert excl.get("excluded_reason") == "duplicate_within_source"
        assert excl.get("duplicate_of") == "skills/b"
        assert excl.get("content_hash") is not None

    print("\n   Verification: All assertions passed!")

    # Test 10: Empty input
    print("\n10. Empty input handling:")
    kept_empty, excluded_empty = engine2.deduplicate_within_source([])
    print(f"    Empty list returns: kept={len(kept_empty)}, excluded={len(excluded_empty)}")
    assert kept_empty == [] and excluded_empty == []

    # Test 11: All unique
    print("\n11. All unique artifacts:")
    unique_artifacts = [
        {"path": "a", "files": {"f.md": "content1"}, "confidence_score": 0.9},
        {"path": "b", "files": {"f.md": "content2"}, "confidence_score": 0.8},
        {"path": "c", "files": {"f.md": "content3"}, "confidence_score": 0.7},
    ]
    kept_all, excluded_none = engine2.deduplicate_within_source(unique_artifacts)
    print(f"    All unique: kept={len(kept_all)}, excluded={len(excluded_none)}")
    assert len(kept_all) == 3 and len(excluded_none) == 0

    print("\n" + "=" * 50)
    print("All tests passed!")
