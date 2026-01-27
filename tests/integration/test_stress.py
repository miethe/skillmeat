"""Stress tests for clone strategy selection and edge case handling.

This test suite verifies the robustness of the clone strategy system under
stress conditions, including large artifact counts, deeply nested paths,
special characters, concurrent operations, and edge case inputs.

Test Coverage:
    - Large artifact count processing (1000+ artifacts)
    - Deeply nested path handling (10+ levels)
    - Special characters in paths (spaces, unicode)
    - Concurrent operations safety (threading)
    - Empty and None value handling
    - Pattern generation stability

Note: Tests marked with @pytest.mark.slow may take several seconds to complete.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.core.clone_target import (
    CloneTarget,
    compute_clone_metadata,
    get_sparse_checkout_patterns,
    select_indexing_strategy,
)
from skillmeat.core.manifest_extractors import extract_deep_search_text

if TYPE_CHECKING:
    pass


# =============================================================================
# Stress Tests - Large Scale
# =============================================================================


@pytest.mark.slow
def test_large_artifact_count_no_crash() -> None:
    """Verify strategy selection handles 1000+ artifacts without crashing.

    Creates a large number of mock artifacts and verifies that strategy
    selection and pattern generation complete successfully without errors.
    """
    from unittest.mock import MagicMock

    # Create 1000 artifacts
    large_artifact_list = []
    for i in range(1000):
        artifact = DetectedArtifact(
            artifact_type="skill",
            name=f"skill-{i:04d}",
            path=f".claude/skills/skill-{i:04d}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill-{i:04d}",
            confidence_score=90,
        )
        large_artifact_list.append(artifact)

    # Create mock source
    mock_source = MagicMock()
    mock_source.clone_target = None

    # Verify strategy selection completes without error
    try:
        strategy = select_indexing_strategy(mock_source, large_artifact_list)
        assert strategy in ["sparse_manifest", "sparse_directory", "api"], (
            f"Unexpected strategy: {strategy}"
        )
    except Exception as e:
        pytest.fail(f"Strategy selection failed with 1000 artifacts: {e}")

    # Verify pattern generation doesn't crash (compute metadata first)
    metadata = compute_clone_metadata(large_artifact_list, "test_sha")
    try:
        patterns = get_sparse_checkout_patterns(
            strategy,
            large_artifact_list,
            metadata.get("artifacts_root"),
        )
        assert isinstance(patterns, list)
        # Should have patterns (count depends on strategy)
        if strategy in ["sparse_manifest", "sparse_directory"]:
            assert len(patterns) > 0, f"Expected patterns for strategy {strategy}"
    except Exception as e:
        pytest.fail(f"Pattern generation failed with 1000 artifacts: {e}")


@pytest.mark.slow
def test_deeply_nested_paths_handled() -> None:
    """Verify handling of paths 10+ levels deep without stack overflow.

    Creates artifacts with very deep directory structures and verifies
    all operations complete successfully.
    """
    from unittest.mock import MagicMock

    # Create artifacts with deeply nested paths (15 levels)
    nested_artifacts = []
    for i in range(10):
        # Build a 15-level deep path
        deep_path = "/".join([f"level{j}" for j in range(15)])
        artifact = DetectedArtifact(
            artifact_type="skill",
            name=f"deep-skill-{i}",
            path=f"{deep_path}/skills/deep-skill-{i}",
            upstream_url=f"https://github.com/test/repo/tree/main/{deep_path}/skills/deep-skill-{i}",
            confidence_score=90,
        )
        nested_artifacts.append(artifact)

    # Create mock source
    mock_source = MagicMock()
    mock_source.clone_target = None

    # Verify strategy selection works
    try:
        strategy = select_indexing_strategy(mock_source, nested_artifacts)
        assert strategy in ["sparse_manifest", "sparse_directory", "api"]
    except RecursionError:
        pytest.fail("RecursionError: Stack overflow with deeply nested paths")
    except Exception as e:
        pytest.fail(f"Unexpected error with nested paths: {e}")

    # Verify pattern generation works
    metadata = compute_clone_metadata(nested_artifacts, "test_sha")
    try:
        patterns = get_sparse_checkout_patterns(
            strategy,
            nested_artifacts,
            metadata.get("artifacts_root"),
        )
        assert isinstance(patterns, list)
        # Verify deep paths are in patterns (for sparse_manifest)
        if strategy == "sparse_manifest":
            for artifact in nested_artifacts:
                assert any(artifact.path in pattern for pattern in patterns), (
                    f"Path {artifact.path} not found in patterns"
                )
    except Exception as e:
        pytest.fail(f"Pattern generation failed with nested paths: {e}")


def test_special_characters_in_paths() -> None:
    """Verify handling of spaces and unicode in artifact paths.

    Creates artifacts with special characters and verifies operations
    don't crash or produce invalid patterns.
    """
    from unittest.mock import MagicMock

    # Create artifacts with special characters
    special_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="skill with spaces",
            path=".claude/skills/skill with spaces",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill%20with%20spaces",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="skill-日本語",
            path=".claude/skills/skill-日本語",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill-日本語",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="skill-café",
            path=".claude/skills/skill-café",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill-café",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="skill-with-émojis🎉",
            path=".claude/skills/skill-with-émojis🎉",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill-with-émojis🎉",
            confidence_score=90,
        ),
    ]

    # Create mock source
    mock_source = MagicMock()
    mock_source.clone_target = None

    # Verify strategy selection doesn't crash
    try:
        strategy = select_indexing_strategy(mock_source, special_artifacts)
        assert strategy in ["sparse_manifest", "sparse_directory", "api"]
    except UnicodeError as e:
        pytest.fail(f"UnicodeError with special characters: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error with special characters: {e}")

    # Verify pattern generation works
    metadata = compute_clone_metadata(special_artifacts, "test_sha")
    try:
        patterns = get_sparse_checkout_patterns(
            strategy,
            special_artifacts,
            metadata.get("artifacts_root"),
        )
        assert isinstance(patterns, list)
        if strategy in ["sparse_manifest", "sparse_directory"]:
            assert len(patterns) > 0
    except Exception as e:
        pytest.fail(f"Pattern generation failed with special characters: {e}")


@pytest.mark.slow
def test_concurrent_operations_safe() -> None:
    """Verify concurrent strategy selections don't cause race conditions.

    Runs multiple strategy selections in parallel threads and verifies
    all complete successfully without data corruption or deadlocks.
    """
    from unittest.mock import MagicMock

    # Create different artifact lists for concurrent processing
    def create_artifact_list(base_index: int, count: int) -> list[DetectedArtifact]:
        """Helper to create artifact list."""
        return [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill-{base_index}-{i}",
                path=f".claude/skills/skill-{base_index}-{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill-{base_index}-{i}",
                confidence_score=90,
            )
            for i in range(count)
        ]

    # Prepare multiple artifact lists of varying sizes
    artifact_lists = [
        create_artifact_list(0, 2),  # Small (API strategy)
        create_artifact_list(1, 5),  # Medium (sparse)
        create_artifact_list(2, 10),  # Larger (sparse)
        create_artifact_list(3, 50),  # Even larger
        create_artifact_list(4, 3),  # Boundary
    ]

    results = []
    errors = []

    def run_strategy_selection(artifacts: list[DetectedArtifact], idx: int) -> tuple[int, str]:
        """Run strategy selection and return result."""
        try:
            mock_source = MagicMock()
            mock_source.clone_target = None
            strategy = select_indexing_strategy(mock_source, artifacts)
            return (idx, strategy)
        except Exception as e:
            errors.append((idx, e))
            return (idx, "error")

    # Run concurrent strategy selections
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(run_strategy_selection, artifacts, idx)
            for idx, artifacts in enumerate(artifact_lists)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors in concurrent operations: {errors}"

    # Verify all operations completed
    assert len(results) == len(artifact_lists), (
        f"Expected {len(artifact_lists)} results, got {len(results)}"
    )

    # Verify results are valid strategies
    for idx, strategy in results:
        assert strategy in ["sparse_manifest", "sparse_directory", "api", "error"], (
            f"Invalid strategy at index {idx}: {strategy}"
        )


def test_empty_and_none_handling() -> None:
    """Verify graceful handling of empty lists and None values.

    Tests edge cases with empty artifact lists, None values, and other
    boundary conditions to ensure robust error handling.
    """
    from unittest.mock import MagicMock

    # Create mock source
    mock_source = MagicMock()
    mock_source.clone_target = None

    # Test empty artifact list
    try:
        strategy_empty = select_indexing_strategy(mock_source, [])
        # Should default to API or return a sensible default
        assert strategy_empty in ["api", "sparse_manifest", "sparse_directory"]
    except Exception as e:
        pytest.fail(f"Failed to handle empty artifact list: {e}")

    # Test empty patterns (should return empty list)
    try:
        patterns_empty = get_sparse_checkout_patterns("api", [], None)
        assert patterns_empty == [] or isinstance(patterns_empty, list)
    except Exception as e:
        pytest.fail(f"Failed to handle empty patterns list: {e}")

    # Test compute_clone_metadata with empty list
    try:
        metadata_empty = compute_clone_metadata([], "test_sha")
        assert isinstance(metadata_empty, dict)
        assert metadata_empty["artifact_paths"] == []
    except Exception as e:
        pytest.fail(f"Failed to handle empty metadata computation: {e}")


# =============================================================================
# Stress Tests - Deep Indexing
# =============================================================================


@pytest.mark.slow
def test_deep_indexing_with_many_small_files(tmp_path: Path) -> None:
    """Verify deep indexing handles many small files efficiently.

    Creates 500 small files and verifies extraction completes successfully
    without performance issues.
    """
    artifact_dir = tmp_path / "many-files-artifact"
    artifact_dir.mkdir()

    # Create 500 small files
    num_files = 500
    for i in range(num_files):
        file_path = artifact_dir / f"file_{i:03d}.md"
        content = f"Content for file {i}"
        file_path.write_text(content, encoding="utf-8")

    # Extract deep search text
    try:
        result_text, indexed_files = extract_deep_search_text(artifact_dir)
    except Exception as e:
        pytest.fail(f"Deep indexing failed with {num_files} files: {e}")

    # Verify extraction succeeded
    assert isinstance(result_text, str)
    assert isinstance(indexed_files, list)
    # May not index all due to size limits, but should handle gracefully
    assert len(indexed_files) > 0


@pytest.mark.slow
def test_deep_indexing_mixed_workload(tmp_path: Path) -> None:
    """Verify deep indexing handles mixed file sizes and types.

    Creates a realistic mix of small, medium, and large files with
    various types to test real-world scenarios.
    """
    artifact_dir = tmp_path / "mixed-artifact"
    artifact_dir.mkdir()

    # Create nested structure with mixed content
    nested_dir = artifact_dir / "nested" / "deep" / "structure"
    nested_dir.mkdir(parents=True)

    # Mix of file sizes and types
    test_files = {
        "README.md": "x" * 1000,  # 1KB
        "SKILL.md": "y" * 5000,  # 5KB
        "config.yaml": "z" * 2000,  # 2KB
        "data.json": "a" * 10000,  # 10KB
        "script.py": "b" * 3000,  # 3KB
        "nested/deep/structure/deep.md": "c" * 4000,  # 4KB nested
        "large.txt": "d" * 50000,  # 50KB
    }

    for rel_path, content in test_files.items():
        file_path = artifact_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    # Extract deep search text
    try:
        result_text, indexed_files = extract_deep_search_text(artifact_dir)
    except Exception as e:
        pytest.fail(f"Deep indexing failed with mixed workload: {e}")

    # Verify extraction succeeded
    assert isinstance(result_text, str)
    assert len(indexed_files) > 0

    # Verify at least some files were indexed
    assert len(indexed_files) >= len(test_files) - 2  # Allow for some to be skipped


def test_deep_indexing_with_unreadable_files(tmp_path: Path) -> None:
    """Verify deep indexing gracefully handles files that can't be read.

    Creates files with permission issues or other read failures and
    verifies the operation continues without crashing.
    """
    artifact_dir = tmp_path / "permission-artifact"
    artifact_dir.mkdir()

    # Create readable file
    readable = artifact_dir / "readable.md"
    readable.write_text("This is readable", encoding="utf-8")

    # Create unreadable file (on Unix systems)
    unreadable = artifact_dir / "unreadable.md"
    unreadable.write_text("This should be unreadable", encoding="utf-8")
    try:
        unreadable.chmod(0o000)  # Remove all permissions
    except (OSError, NotImplementedError):
        # Permission changes may not work on all systems
        pytest.skip("Cannot modify file permissions on this system")

    # Extract deep search text
    try:
        result_text, indexed_files = extract_deep_search_text(artifact_dir)
    finally:
        # Restore permissions for cleanup
        try:
            unreadable.chmod(0o644)
        except (OSError, NotImplementedError):
            pass

    # Verify extraction succeeded for readable file
    assert "This is readable" in result_text or len(indexed_files) >= 1


def test_clone_target_creation_with_large_metadata(tmp_path: Path) -> None:
    """Verify CloneTarget creation handles large metadata payloads.

    Creates a CloneTarget with extensive metadata and verifies it
    serializes/deserializes correctly.
    """
    from unittest.mock import MagicMock

    # Create large artifact list
    large_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name=f"skill-{i:04d}",
            path=f".claude/skills/category-{i // 10}/skill-{i:04d}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/category-{i // 10}/skill-{i:04d}",
            confidence_score=90,
        )
        for i in range(100)
    ]

    # Create mock source
    mock_source = MagicMock()
    mock_source.clone_target = None

    # Create clone target with large metadata
    try:
        # Compute metadata
        metadata = compute_clone_metadata(large_artifacts, "test_sha_abc123")

        # Select strategy
        strategy = select_indexing_strategy(mock_source, large_artifacts)

        # Get sparse patterns
        patterns = get_sparse_checkout_patterns(
            strategy,
            large_artifacts,
            metadata.get("artifacts_root"),
        )

        # Create CloneTarget
        clone_target = CloneTarget(
            strategy=strategy,
            sparse_patterns=patterns,
            artifacts_root=metadata.get("artifacts_root"),
            artifact_paths=metadata.get("artifact_paths", []),
            tree_sha="test_sha_abc123",
        )

        # Verify creation succeeded
        assert clone_target is not None
        assert len(clone_target.artifact_paths) == 100
        assert isinstance(clone_target.sparse_patterns, list)
        assert clone_target.tree_sha == "test_sha_abc123"

        # Verify serialization/deserialization
        clone_dict = clone_target.to_dict()
        assert isinstance(clone_dict, dict)

        # Verify can reconstruct from dict
        reconstructed = CloneTarget.from_dict(clone_dict)
        assert reconstructed.strategy == clone_target.strategy
        assert len(reconstructed.artifact_paths) == len(clone_target.artifact_paths)

    except Exception as e:
        pytest.fail(f"CloneTarget creation failed with large metadata: {e}")


def test_pattern_generation_deduplication() -> None:
    """Verify sparse patterns are deduplicated correctly.

    Creates artifacts with overlapping paths and verifies patterns
    are deduplicated to avoid redundancy.
    """
    # Create artifacts with overlapping paths
    overlapping_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="skill-a",
            path=".claude/skills/group/skill-a",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/group/skill-a",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="skill-b",
            path=".claude/skills/group/skill-b",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/group/skill-b",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="skill-c",
            path=".claude/skills/other/skill-c",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/other/skill-c",
            confidence_score=90,
        ),
    ]

    # Compute metadata
    metadata = compute_clone_metadata(overlapping_artifacts, "test_sha")

    # Get patterns using sparse_manifest strategy (will generate specific patterns)
    patterns = get_sparse_checkout_patterns(
        "sparse_manifest",
        overlapping_artifacts,
        metadata.get("artifacts_root"),
    )

    # Verify patterns exist and are deduplicated
    assert isinstance(patterns, list)
    assert len(patterns) > 0

    # Verify no exact duplicates
    unique_patterns = set(patterns)
    assert len(unique_patterns) == len(patterns), "Found duplicate patterns"

    # Verify expected pattern count (one per artifact for sparse_manifest)
    assert len(patterns) == len(overlapping_artifacts), (
        f"Expected {len(overlapping_artifacts)} patterns, got {len(patterns)}"
    )
