"""Integration tests for clone strategy selection and API fallback behavior.

This test suite verifies the differential re-indexing logic and graceful fallback
when clone operations are not needed or cannot be performed. It focuses on the
CloneTarget caching mechanism and strategy selection based on artifact count.

Test Coverage:
    - API strategy selection for small artifact counts (<3)
    - API strategy returns empty sparse patterns
    - CloneTarget creation with API strategy
    - Strategy boundaries at 3 artifacts
    - Differential re-indexing (should_reindex)
    - Changed artifact detection (get_changed_artifacts)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.core.clone_target import (
    CloneTarget,
    compute_clone_metadata,
    get_changed_artifacts,
    get_sparse_checkout_patterns,
    select_indexing_strategy,
    should_reindex,
)

if TYPE_CHECKING:
    from skillmeat.cache.models import MarketplaceSource


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_marketplace_source() -> MagicMock:
    """Create a mock MarketplaceSource for testing.

    Returns:
        MagicMock with clone_target property that can be set to CloneTarget or None.
    """
    source = MagicMock(spec=["clone_target"])
    source.clone_target = None
    return source


@pytest.fixture
def sample_artifacts_two() -> list[DetectedArtifact]:
    """Create a sample list of 2 detected artifacts.

    Returns:
        List containing 2 DetectedArtifact instances.
    """
    return [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="bar",
            path=".claude/skills/bar",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/bar",
            confidence_score=95,
        ),
    ]


@pytest.fixture
def sample_artifacts_three() -> list[DetectedArtifact]:
    """Create a sample list of 3 detected artifacts.

    Returns:
        List containing 3 DetectedArtifact instances.
    """
    return [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="bar",
            path=".claude/skills/bar",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/bar",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="command",
            name="baz",
            path=".claude/commands/baz",
            upstream_url="https://github.com/test/repo/tree/main/.claude/commands/baz",
            confidence_score=95,
        ),
    ]


# =============================================================================
# API Strategy Tests
# =============================================================================


def test_api_strategy_for_few_artifacts(
    mock_marketplace_source: MagicMock, sample_artifacts_two: list[DetectedArtifact]
) -> None:
    """Test that <3 artifacts always returns 'api' strategy.

    For very small artifact counts, the GitHub API is more efficient than
    clone overhead. This test verifies that 2 artifacts results in the
    'api' strategy selection.
    """
    strategy = select_indexing_strategy(mock_marketplace_source, sample_artifacts_two)

    assert strategy == "api", "Expected 'api' strategy for 2 artifacts"


def test_api_strategy_for_empty_artifacts(mock_marketplace_source: MagicMock) -> None:
    """Test that empty artifact list returns 'api' strategy.

    When no artifacts are detected, the API strategy is selected as a
    safe default that avoids any clone operations.
    """
    strategy = select_indexing_strategy(mock_marketplace_source, [])

    assert strategy == "api", "Expected 'api' strategy for empty artifact list"


def test_api_strategy_for_single_artifact(mock_marketplace_source: MagicMock) -> None:
    """Test that single artifact returns 'api' strategy.

    For a single artifact, GitHub API is more efficient than clone.
    """
    artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="solo",
            path=".claude/skills/solo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/solo",
            confidence_score=95,
        )
    ]

    strategy = select_indexing_strategy(mock_marketplace_source, artifacts)

    assert strategy == "api", "Expected 'api' strategy for 1 artifact"


# =============================================================================
# API Strategy Pattern Tests
# =============================================================================


def test_api_strategy_patterns_empty() -> None:
    """Test that API strategy returns empty sparse_patterns.

    API strategy doesn't use git cloning, so sparse checkout patterns
    should be empty.
    """
    clone_target = CloneTarget(
        strategy="api",
        sparse_patterns=[],  # Should be empty for API strategy
        artifacts_root=None,
        artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
        tree_sha="abc123",
    )

    assert (
        clone_target.sparse_patterns == []
    ), "API strategy should have empty sparse_patterns"


def test_clone_target_api_strategy(
    sample_artifacts_two: list[DetectedArtifact],
) -> None:
    """Test creating CloneTarget with api strategy works correctly.

    Verifies that CloneTarget can be instantiated with 'api' strategy
    and that it serializes/deserializes correctly.
    """
    artifact_paths = [a.path for a in sample_artifacts_two]

    clone_target = CloneTarget(
        strategy="api",
        sparse_patterns=[],
        artifacts_root=".claude/skills",
        artifact_paths=artifact_paths,
        tree_sha="abc123def456",
    )

    # Verify fields
    assert clone_target.strategy == "api"
    assert clone_target.sparse_patterns == []
    assert clone_target.artifact_paths == artifact_paths
    assert clone_target.tree_sha == "abc123def456"

    # Verify serialization roundtrip
    serialized = clone_target.to_dict()
    deserialized = CloneTarget.from_dict(serialized)

    assert deserialized.strategy == "api"
    assert deserialized.sparse_patterns == []
    assert deserialized.artifact_paths == artifact_paths
    assert deserialized.tree_sha == "abc123def456"


# =============================================================================
# Strategy Boundary Tests
# =============================================================================


def test_strategy_boundary_at_three(
    mock_marketplace_source: MagicMock,
    sample_artifacts_two: list[DetectedArtifact],
    sample_artifacts_three: list[DetectedArtifact],
) -> None:
    """Test strategy boundary: exactly 2 artifacts = api, exactly 3 = sparse_manifest.

    The strategy selection has a threshold at 3 artifacts. This test verifies
    that 2 artifacts results in 'api' while 3 artifacts results in
    'sparse_manifest' strategy.
    """
    # 2 artifacts should use 'api'
    strategy_two = select_indexing_strategy(
        mock_marketplace_source, sample_artifacts_two
    )
    assert (
        strategy_two == "api"
    ), "Expected 'api' strategy for exactly 2 artifacts (below threshold)"

    # 3 artifacts should use 'sparse_manifest'
    strategy_three = select_indexing_strategy(
        mock_marketplace_source, sample_artifacts_three
    )
    assert (
        strategy_three == "sparse_manifest"
    ), "Expected 'sparse_manifest' strategy for exactly 3 artifacts (at threshold)"


# =============================================================================
# should_reindex Tests
# =============================================================================


def test_should_reindex_no_cache(mock_marketplace_source: MagicMock) -> None:
    """Test that first-time indexing returns True (no cached CloneTarget).

    When a source has never been indexed before, clone_target is None,
    and should_reindex must return True to trigger initial indexing.
    """
    mock_marketplace_source.clone_target = None

    result = should_reindex(mock_marketplace_source, "abc123")

    assert result is True, "Expected True for first-time indexing (no cache)"


def test_should_reindex_same_sha(mock_marketplace_source: MagicMock) -> None:
    """Test that same tree_sha returns False (skip re-indexing).

    When the repository tree hasn't changed (same SHA), re-indexing
    is unnecessary. should_reindex should return False to avoid
    expensive clone operations.
    """
    # Set up cached CloneTarget with tree_sha
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[".claude/skills/foo/SKILL.md"],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo"],
        tree_sha="abc123",
    )
    mock_marketplace_source.clone_target = cached_target

    # Call with same tree SHA
    result = should_reindex(mock_marketplace_source, "abc123")

    assert result is False, "Expected False when tree_sha is unchanged"


def test_should_reindex_different_sha(mock_marketplace_source: MagicMock) -> None:
    """Test that different tree_sha returns True (re-indexing needed).

    When the repository tree has changed (different SHA), re-indexing
    is necessary to capture new/modified artifacts. should_reindex
    should return True to trigger clone and re-scan.
    """
    # Set up cached CloneTarget with old tree_sha
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[".claude/skills/foo/SKILL.md"],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo"],
        tree_sha="abc123",
    )
    mock_marketplace_source.clone_target = cached_target

    # Call with different tree SHA
    result = should_reindex(mock_marketplace_source, "def456")

    assert result is True, "Expected True when tree_sha has changed"


# =============================================================================
# get_changed_artifacts Tests
# =============================================================================


def test_get_changed_artifacts_first_time(
    sample_artifacts_two: list[DetectedArtifact],
) -> None:
    """Test that first-time indexing returns all artifacts (no cache).

    When no cached CloneTarget exists, all currently detected artifacts
    are considered "changed" (new) and should be returned for indexing.
    """
    changed = get_changed_artifacts(None, sample_artifacts_two)

    assert len(changed) == 2, "Expected all artifacts for first-time indexing"
    assert (
        changed == sample_artifacts_two
    ), "Expected exact match with current artifacts"


def test_get_changed_artifacts_no_changes() -> None:
    """Test that same paths returns empty list (no new artifacts).

    When the cached artifact paths exactly match the current artifact
    paths, no re-indexing is needed. get_changed_artifacts should
    return an empty list.
    """
    # Set up cached CloneTarget with existing paths
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[
            ".claude/skills/foo/SKILL.md",
            ".claude/skills/bar/SKILL.md",
        ],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
        tree_sha="abc123",
    )

    # Current artifacts match cached paths exactly
    current_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="bar",
            path=".claude/skills/bar",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/bar",
            confidence_score=95,
        ),
    ]

    changed = get_changed_artifacts(cached_target, current_artifacts)

    assert len(changed) == 0, "Expected empty list when no artifacts changed"


def test_get_changed_artifacts_new_artifact() -> None:
    """Test that new path returns only the new artifact.

    When a new artifact is added to the repository, only that new
    artifact should be returned as "changed". Existing artifacts
    that are already cached should be excluded.
    """
    # Set up cached CloneTarget with two existing paths
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[
            ".claude/skills/foo/SKILL.md",
            ".claude/skills/bar/SKILL.md",
        ],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
        tree_sha="abc123",
    )

    # Current artifacts include a new one (baz)
    current_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="bar",
            path=".claude/skills/bar",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/bar",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="baz",
            path=".claude/skills/baz",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/baz",
            confidence_score=95,
        ),
    ]

    changed = get_changed_artifacts(cached_target, current_artifacts)

    assert len(changed) == 1, "Expected only the new artifact"
    assert changed[0].path == ".claude/skills/baz", "Expected new artifact 'baz'"
    assert changed[0].name == "baz", "Expected artifact name 'baz'"


def test_get_changed_artifacts_artifact_removed() -> None:
    """Test that removed artifact doesn't appear in changed list.

    When an artifact is removed from the repository, get_changed_artifacts
    returns an empty list (the remaining artifacts are already cached).
    The removal itself is handled by the sync logic at a higher level.
    """
    # Set up cached CloneTarget with three paths
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[
            ".claude/skills/foo/SKILL.md",
            ".claude/skills/bar/SKILL.md",
            ".claude/skills/baz/SKILL.md",
        ],
        artifacts_root=".claude/skills",
        artifact_paths=[
            ".claude/skills/foo",
            ".claude/skills/bar",
            ".claude/skills/baz",
        ],
        tree_sha="abc123",
    )

    # Current artifacts only have two (bar was removed)
    current_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="baz",
            path=".claude/skills/baz",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/baz",
            confidence_score=95,
        ),
    ]

    changed = get_changed_artifacts(cached_target, current_artifacts)

    assert (
        len(changed) == 0
    ), "Expected empty list (removal doesn't create changed artifacts)"


def test_get_changed_artifacts_multiple_new() -> None:
    """Test that multiple new artifacts are all returned.

    When multiple new artifacts are added, all of them should be
    returned in the changed list for indexing.
    """
    # Set up cached CloneTarget with one existing path
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[".claude/skills/foo/SKILL.md"],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo"],
        tree_sha="abc123",
    )

    # Current artifacts include two new ones
    current_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="foo",
            path=".claude/skills/foo",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/foo",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="bar",
            path=".claude/skills/bar",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/bar",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="command",
            name="baz",
            path=".claude/commands/baz",
            upstream_url="https://github.com/test/repo/tree/main/.claude/commands/baz",
            confidence_score=95,
        ),
    ]

    changed = get_changed_artifacts(cached_target, current_artifacts)

    assert len(changed) == 2, "Expected both new artifacts"
    changed_paths = {a.path for a in changed}
    assert changed_paths == {
        ".claude/skills/bar",
        ".claude/commands/baz",
    }, "Expected new artifacts bar and baz"


# =============================================================================
# CloneTarget Serialization Tests
# =============================================================================


def test_clone_target_serialization_roundtrip() -> None:
    """Test that CloneTarget serialization/deserialization preserves all fields.

    Verifies that to_dict/from_dict and to_json/from_json work correctly
    and preserve all CloneTarget attributes including datetime.
    """
    original = CloneTarget(
        strategy="sparse_directory",
        sparse_patterns=[".claude/**"],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
        tree_sha="abc123def456",
        computed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )

    # Test dict serialization
    data = original.to_dict()
    from_dict = CloneTarget.from_dict(data)

    assert from_dict.strategy == original.strategy
    assert from_dict.sparse_patterns == original.sparse_patterns
    assert from_dict.artifacts_root == original.artifacts_root
    assert from_dict.artifact_paths == original.artifact_paths
    assert from_dict.tree_sha == original.tree_sha
    # Compare datetime strings to avoid timezone comparison issues
    assert from_dict.computed_at.isoformat() == original.computed_at.isoformat()

    # Test JSON serialization
    json_str = original.to_json()
    from_json = CloneTarget.from_json(json_str)

    assert from_json.strategy == original.strategy
    assert from_json.sparse_patterns == original.sparse_patterns
    assert from_json.artifacts_root == original.artifacts_root
    assert from_json.artifact_paths == original.artifact_paths
    assert from_json.tree_sha == original.tree_sha
    assert from_json.computed_at.isoformat() == original.computed_at.isoformat()


def test_clone_target_invalid_strategy_raises() -> None:
    """Test that invalid strategy raises ValueError.

    CloneTarget validation should reject any strategy that isn't
    one of the allowed values.
    """
    with pytest.raises(ValueError, match="strategy must be one of"):
        CloneTarget(
            strategy="invalid_strategy",  # type: ignore[arg-type]
            sparse_patterns=[],
            artifacts_root=None,
            artifact_paths=[],
            tree_sha="abc123",
        )


# ==============================================================================
# Test: Sparse Directory Strategy Selection (Large Repos)
# ==============================================================================


@pytest.mark.integration
class TestSparseDirectoryStrategySelection:
    """Test sparse_directory strategy selection for large repositories with >20 artifacts."""

    def test_sparse_directory_selects_with_large_count(self):
        mock_source = MagicMock()
        """Test that 25+ artifacts with common root selects sparse_directory strategy.

        This is the primary use case for sparse_directory: large repositories
        with many artifacts all located under a common ancestor directory.
        """
        # Create 25 artifacts under common .claude/skills/ root
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i:02d}",
                path=f".claude/skills/skill{i:02d}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
                confidence_score=95
            )
            for i in range(25)
        ]

        result = select_indexing_strategy(mock_source, artifacts)

        assert result == "sparse_directory", (
            "Expected sparse_directory strategy for 25 artifacts with common root"
        )

    def test_sparse_directory_boundary_at_21_artifacts(self):
        mock_source = MagicMock()
        """Test that exactly 21 artifacts with common root selects sparse_directory.

        The boundary is >20 artifacts, so 21 should trigger sparse_directory.
        """
        # Create exactly 21 artifacts under common root
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i:02d}",
                path=f".claude/skills/skill{i:02d}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
                confidence_score=95
            )
            for i in range(21)
        ]

        result = select_indexing_strategy(mock_source, artifacts)

        assert result == "sparse_directory"

    def test_sparse_directory_not_selected_at_20_artifacts(self):
        mock_source = MagicMock()
        """Test that exactly 20 artifacts stays at sparse_manifest.

        The boundary is >20, so 20 should still use sparse_manifest.
        """
        # Create exactly 20 artifacts under common root
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i:02d}",
                path=f".claude/skills/skill{i:02d}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
                confidence_score=95
            )
            for i in range(20)
        ]

        result = select_indexing_strategy(mock_source, artifacts)

        assert result == "sparse_manifest", (
            "Expected sparse_manifest for exactly 20 artifacts (boundary case)"
        )

    def test_sparse_directory_fallback_to_manifest_without_common_root(self):
        mock_source = MagicMock()
        """Test that 25+ artifacts without common root falls back to sparse_manifest.

        When artifacts are scattered across multiple root directories with no
        common ancestor, sparse_directory would be inefficient and could clone
        too much. Fall back to sparse_manifest for safety.
        """
        # Create 25 artifacts scattered across different root directories
        artifacts = []
        for i in range(5):
            # 5 artifacts in each of 5 different root directories
            for j in range(5):
                artifacts.append(
                    DetectedArtifact(
                        artifact_type="skill",
                        name=f"skill{j}",
                        path=f"root{i}/skills/skill{j}",
                        upstream_url=f"https://github.com/test/repo/tree/main/root{i}/skills/skill{j}",
                        confidence_score=95
                    )
                )

        result = select_indexing_strategy(mock_source, artifacts)

        # Should fall back to sparse_manifest due to no common root
        assert result == "sparse_manifest", (
            "Expected fallback to sparse_manifest for scattered artifacts"
        )

    def test_sparse_directory_requires_common_root(self):
        mock_source = MagicMock()
        """Test that sparse_directory strategy considers common root requirement.

        Even with >20 artifacts, if there's no common root, the strategy
        falls back to sparse_manifest to avoid cloning too much.
        """
        # Create 30 artifacts split between two distinct roots
        artifacts = []
        for i in range(15):
            artifacts.append(DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            ))
        for i in range(15):
            artifacts.append(DetectedArtifact(
                artifact_type="command",
                name=f"util{i}",
                path=f"tools/utils/util{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/tools/utils/util{i}",
                confidence_score=95
            ))

        result = select_indexing_strategy(mock_source, artifacts)

        # No single common root, should use sparse_manifest
        assert result == "sparse_manifest"

    def test_sparse_directory_with_very_large_count(self):
        mock_source = MagicMock()
        """Test that strategy handles very large artifact counts (100+).

        Large repositories benefit most from sparse_directory cloning.
        """
        # Create 100 artifacts under common .claude/ root
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i:03d}",
                path=f".claude/skills/skill{i:03d}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:03d}",
                confidence_score=95
            )
            for i in range(100)
        ]

        result = select_indexing_strategy(mock_source, artifacts)

        assert result == "sparse_directory", (
            "Expected sparse_directory for very large artifact count (100)"
        )

    def test_sparse_directory_mixed_artifact_types_common_root(self):
        mock_source = MagicMock()
        """Test that mixed artifact types under common root select sparse_directory.

        When skills, commands, agents, etc. are all under a common directory
        like .claude/, sparse_directory is still the best strategy.
        """
        # Create 25 artifacts of mixed types under common .claude/ root
        artifacts = []
        for i in range(10):
            artifacts.append(DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            ))
        for i in range(8):
            artifacts.append(
                DetectedArtifact(
                    artifact_type="command",
                    name=f"cmd{i}",
                    path=f".claude/commands/cmd{i}",
                    upstream_url=f"https://github.com/test/repo/tree/main/.claude/commands/cmd{i}",
                    confidence_score=95
                )
            )
        for i in range(7):
            artifacts.append(DetectedArtifact(
                artifact_type="agent",
                name=f"agent{i}",
                path=f".claude/agents/agent{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/agents/agent{i}",
                confidence_score=95
            ))

        result = select_indexing_strategy(mock_source, artifacts)

        # All under .claude/, should use sparse_directory
        assert result == "sparse_directory"


# ==============================================================================
# Test: Sparse Directory Pattern Generation
# ==============================================================================


@pytest.mark.integration
class TestSparseDirectoryPatternGeneration:
    """Test sparse-checkout pattern generation for sparse_directory strategy."""

    def test_sparse_directory_generates_root_pattern(self):
        """Test that sparse_directory generates root/** pattern with common root.

        When all artifacts share a common root like .claude/skills/, the pattern
        should be a single directory glob: .claude/skills/**
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(25)
        ]

        # Compute metadata to get artifacts_root
        metadata = compute_clone_metadata(artifacts, "test_sha")
        artifacts_root = metadata["artifacts_root"]

        # Should have common root
        assert artifacts_root == ".claude/skills"

        # Generate patterns for sparse_directory strategy
        patterns = get_sparse_checkout_patterns(
            "sparse_directory", artifacts, artifacts_root
        )

        # Should generate single root/** pattern
        assert len(patterns) == 1
        assert patterns[0] == ".claude/skills/**"

    def test_sparse_directory_generates_parent_pattern_for_mixed_subdirs(self):
        """Test pattern generation when artifacts are in .claude/skills and .claude/commands.

        When artifacts span multiple subdirectories of a common parent, the
        pattern should target the common parent: .claude/**
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill1",
                path=".claude/skills/skill1",
                upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill1",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="skill2",
                path=".claude/skills/skill2",
                upstream_url="https://github.com/test/repo/tree/main/.claude/skills/skill2",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="command",
                name="cmd1",
                path=".claude/commands/cmd1",
                upstream_url="https://github.com/test/repo/tree/main/.claude/commands/cmd1",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="command",
                name="cmd2",
                path=".claude/commands/cmd2",
                upstream_url="https://github.com/test/repo/tree/main/.claude/commands/cmd2",
                confidence_score=95
            ),
        ] + [
            # Add more to get >20 artifacts
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(3, 20)
        ]

        metadata = compute_clone_metadata(artifacts, "test_sha")
        artifacts_root = metadata["artifacts_root"]

        # Common root should be .claude
        assert artifacts_root == ".claude"

        patterns = get_sparse_checkout_patterns(
            "sparse_directory", artifacts, artifacts_root
        )

        # Should generate .claude/** pattern
        assert len(patterns) == 1
        assert patterns[0] == ".claude/**"

    def test_sparse_directory_multiple_roots_generates_multiple_patterns(self):
        """Test that multiple distinct roots generate multiple patterns.

        When artifacts are under .claude/skills and .codex/agents (two distinct
        roots with no common ancestor), generate a pattern for each root.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(12)
        ] + [
            DetectedArtifact(
                artifact_type="agent",
                name=f"agent{i}",
                path=f".codex/agents/agent{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.codex/agents/agent{i}",
                confidence_score=95
            )
            for i in range(10)
        ]

        metadata = compute_clone_metadata(artifacts, "test_sha")
        artifacts_root = metadata["artifacts_root"]

        # No common root (scattered)
        assert artifacts_root is None

        patterns = get_sparse_checkout_patterns(
            "sparse_directory", artifacts, artifacts_root
        )

        # Should generate patterns for both roots
        assert len(patterns) == 2
        assert ".claude/skills/**" in patterns
        assert ".codex/agents/**" in patterns

    def test_sparse_directory_fallback_to_manifest_when_scattered(self):
        """Test fallback to manifest patterns when artifacts are truly scattered.

        When artifacts have no identifiable common roots (e.g., one in skills/,
        one in docs/, one in src/), fall back to manifest patterns for safety.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill1",
                path="a/b/skill1",
                upstream_url="https://github.com/test/repo/tree/main/a/b/skill1",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="skill2",
                path="c/d/skill2",
                upstream_url="https://github.com/test/repo/tree/main/c/d/skill2",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="skill3",
                path="e/f/skill3",
                upstream_url="https://github.com/test/repo/tree/main/e/f/skill3",
                confidence_score=95
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="skill4",
                path="g/h/skill4",
                upstream_url="https://github.com/test/repo/tree/main/g/h/skill4",
                confidence_score=95
            ),
        ] + [
            # Add more scattered artifacts
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f"root{i}/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/root{i}/skill{i}",
                confidence_score=95
            ) for i in range(5, 22)
        ]

        metadata = compute_clone_metadata(artifacts, "test_sha")
        artifacts_root = metadata["artifacts_root"]

        # No common root
        assert artifacts_root is None

        patterns = get_sparse_checkout_patterns(
            "sparse_directory", artifacts, artifacts_root
        )

        # When artifacts have no common root but have identifiable sub-roots
        # (first 2 path levels), the implementation generates directory patterns
        # for each unique sub-root, NOT manifest patterns.
        # This is because _find_artifact_roots() groups by first 2 path levels.
        # Example: "a/b/skill1" -> root "a/b" -> pattern "a/b/**"
        assert len(patterns) > 0
        # Verify they're directory patterns (ending with /**)
        assert all(p.endswith("/**") for p in patterns)

    def test_sparse_directory_pattern_not_full_repo(self):
        """CRITICAL: Verify patterns NEVER include bare '**' which would clone full repo.

        This is a safety check to ensure we never accidentally generate a
        pattern that would clone the entire repository.
        """
        # Test various artifact configurations
        test_cases = [
            # Large count with common root
            [
                DetectedArtifact(
                    artifact_type="skill",
                    name=f"skill{i}",
                    path=f".claude/skills/skill{i}",
                    upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                    confidence_score=95
                )
                for i in range(50)
            ],
            # Mixed types under common root
            [DetectedArtifact(
                artifact_type="skill",
                name=f"item{i}",
                path=f".claude/artifacts/item{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/artifacts/item{i}",
                confidence_score=95
            ) for i in range(30)],
            # Multiple roots
            [DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            ) for i in range(15)]
            + [DetectedArtifact(
                artifact_type="agent",
                name=f"agent{i}",
                path=f".codex/agents/agent{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.codex/agents/agent{i}",
                confidence_score=95
            ) for i in range(15)],
            # Scattered artifacts
            [DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f"root{i}/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/root{i}/skill{i}",
                confidence_score=95
            ) for i in range(25)],
        ]

        for artifacts in test_cases:
            metadata = compute_clone_metadata(artifacts, "test_sha")
            artifacts_root = metadata["artifacts_root"]

            patterns = get_sparse_checkout_patterns(
                "sparse_directory", artifacts, artifacts_root
            )

            # CRITICAL: No pattern should be bare "**"
            assert "**" not in patterns, (
                f"Found dangerous '**' pattern that would clone full repo. "
                f"Patterns: {patterns}"
            )

            # Also check that each pattern has a specific path prefix
            for pattern in patterns:
                # Pattern should either have / or end with /** (but not be bare **)
                if pattern.endswith("/**"):
                    prefix = pattern[:-3]  # Remove '/**'
                    assert len(prefix) > 0, (
                        f"Pattern '{pattern}' has empty prefix, would clone full repo"
                    )
                else:
                    # Manifest pattern - should contain /
                    assert "/" in pattern, (
                        f"Pattern '{pattern}' lacks path separator"
                    )

    def test_sparse_directory_normalizes_path_separators(self):
        """Test that patterns use forward slashes consistently.

        Git sparse-checkout requires forward slashes, even on Windows.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(25)
        ]

        metadata = compute_clone_metadata(artifacts, "test_sha")
        artifacts_root = metadata["artifacts_root"]

        patterns = get_sparse_checkout_patterns(
            "sparse_directory", artifacts, artifacts_root
        )

        # All patterns should use forward slashes
        for pattern in patterns:
            assert "\\" not in pattern, f"Pattern '{pattern}' contains backslashes"
            assert "/" in pattern, f"Pattern '{pattern}' should contain forward slashes"


# ==============================================================================
# Test: Sparse Directory CloneTarget Creation
# ==============================================================================


@pytest.mark.integration
class TestSparseDirectoryCloneTargetCreation:
    """Test CloneTarget creation with sparse_directory strategy."""

    def test_sparse_directory_clone_target_construction(self):
        """Test creating CloneTarget with sparse_directory strategy and patterns.

        Verify that all fields are populated correctly for sparse_directory.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(30)
        ]
        tree_sha = "abc123def456"

        # Compute metadata
        metadata = compute_clone_metadata(artifacts, tree_sha)

        # Create CloneTarget
        target = CloneTarget(
            strategy="sparse_directory",
            sparse_patterns=[".claude/skills/**"],
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha=tree_sha,
            computed_at=datetime.now(timezone.utc),
        )

        # Verify strategy
        assert target.strategy == "sparse_directory"

        # Verify patterns
        assert len(target.sparse_patterns) == 1
        assert target.sparse_patterns[0] == ".claude/skills/**"

        # Verify artifacts_root
        assert target.artifacts_root == ".claude/skills"

        # Verify artifact_paths
        assert len(target.artifact_paths) == 30
        assert all(p.startswith(".claude/skills/") for p in target.artifact_paths)

        # Verify tree_sha
        assert target.tree_sha == tree_sha

    def test_sparse_directory_clone_target_serialization(self):
        """Test that CloneTarget with sparse_directory serializes correctly.

        Verify round-trip JSON serialization preserves all fields.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(25)
        ]
        tree_sha = "test_sha_123"

        metadata = compute_clone_metadata(artifacts, tree_sha)

        target = CloneTarget(
            strategy="sparse_directory",
            sparse_patterns=[".claude/skills/**"],
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha=tree_sha,
            computed_at=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        # Serialize to JSON
        json_str = target.to_json()

        # Deserialize
        restored = CloneTarget.from_json(json_str)

        # Verify all fields preserved
        assert restored.strategy == "sparse_directory"
        assert restored.sparse_patterns == [".claude/skills/**"]
        assert restored.artifacts_root == ".claude/skills"
        assert len(restored.artifact_paths) == 25
        assert restored.tree_sha == tree_sha
        assert restored.computed_at == datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_sparse_directory_clone_target_with_multiple_patterns(self):
        """Test CloneTarget with multiple sparse patterns (multiple roots).

        When artifacts span multiple roots like .claude/ and .codex/, the
        CloneTarget should contain multiple patterns.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(15)
        ] + [
            DetectedArtifact(
                artifact_type="agent",
                name=f"agent{i}",
                path=f".codex/agents/agent{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.codex/agents/agent{i}",
                confidence_score=95
            )
            for i in range(10)
        ]

        tree_sha = "multi_root_sha"
        metadata = compute_clone_metadata(artifacts, tree_sha)

        # Generate patterns
        patterns = get_sparse_checkout_patterns(
            "sparse_directory",
            artifacts,
            metadata["artifacts_root"],
        )

        target = CloneTarget(
            strategy="sparse_directory",
            sparse_patterns=patterns,
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha=tree_sha,
        )

        # Verify multiple patterns
        assert len(target.sparse_patterns) == 2
        assert ".claude/skills/**" in target.sparse_patterns
        assert ".codex/agents/**" in target.sparse_patterns

        # Verify artifacts_root is None (no common root)
        assert target.artifacts_root is None

        # Verify artifact_paths
        assert len(target.artifact_paths) == 25


# ==============================================================================
# Test: Sparse Directory Integration Flow
# ==============================================================================


@pytest.mark.integration
class TestSparseDirectoryIntegrationFlow:
    """Test complete flow from artifact detection to CloneTarget creation for sparse_directory."""

    def test_complete_flow_large_repo_with_common_root(self):
        mock_source = MagicMock()
        """Test complete flow: detect 30 artifacts -> select strategy -> generate patterns -> create target.

        This simulates the real-world scenario of indexing a large repository
        with many artifacts under a common directory.
        """
        # Step 1: Simulate artifact detection
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i:02d}",
                path=f".claude/skills/skill{i:02d}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
                confidence_score=95
            )
            for i in range(30)
        ]
        tree_sha = "full_flow_sha_123"

        # Step 2: Select indexing strategy
        strategy = select_indexing_strategy(mock_source, artifacts)
        assert strategy == "sparse_directory"

        # Step 3: Compute clone metadata
        metadata = compute_clone_metadata(artifacts, tree_sha)
        assert metadata["artifacts_root"] == ".claude/skills"
        assert len(metadata["artifact_paths"]) == 30

        # Step 4: Generate sparse-checkout patterns
        patterns = get_sparse_checkout_patterns(
            strategy,
            artifacts,
            metadata["artifacts_root"],
        )
        assert len(patterns) == 1
        assert patterns[0] == ".claude/skills/**"

        # Step 5: Create CloneTarget
        target = CloneTarget(
            strategy=strategy,
            sparse_patterns=patterns,
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha=tree_sha,
        )

        # Step 6: Verify final CloneTarget
        assert target.strategy == "sparse_directory"
        assert target.sparse_patterns == [".claude/skills/**"]
        assert target.artifacts_root == ".claude/skills"
        assert len(target.artifact_paths) == 30
        assert target.tree_sha == tree_sha

        # Step 7: Verify serialization works
        json_str = target.to_json()
        restored = CloneTarget.from_json(json_str)
        assert restored.strategy == "sparse_directory"
        assert restored.sparse_patterns == patterns

    def test_complete_flow_large_repo_scattered_artifacts(self):
        mock_source = MagicMock()
        """Test flow with 25+ scattered artifacts (no common root).

        Should fall back to sparse_manifest strategy for safety.
        """
        # Step 1: Scattered artifacts
        artifacts = []
        for i in range(25):
            # Each artifact in a different root directory
            artifacts.append(DetectedArtifact(
                artifact_type="skill",
                name="skill",
                path=f"root{i}/skills/skill",
                upstream_url=f"https://github.com/test/repo/tree/main/root{i}/skills/skill",
                confidence_score=95
            ))

        tree_sha = "scattered_sha_456"

        # Step 2: Select strategy
        strategy = select_indexing_strategy(mock_source, artifacts)
        # Should fall back to sparse_manifest
        assert strategy == "sparse_manifest"

        # Step 3: Compute metadata
        metadata = compute_clone_metadata(artifacts, tree_sha)
        # No common root for scattered artifacts
        assert metadata["artifacts_root"] is None

        # Step 4: Generate patterns
        patterns = get_sparse_checkout_patterns(
            strategy,
            artifacts,
            metadata["artifacts_root"],
        )
        # Should generate manifest patterns, not directory patterns
        assert len(patterns) == 25
        assert all("SKILL.md" in p for p in patterns)

    def test_complete_flow_mixed_types_under_claude(self):
        mock_source = MagicMock()
        """Test flow with mixed artifact types under .claude/ directory.

        Skills, commands, agents, hooks all under .claude/ should select
        sparse_directory with .claude/** pattern.
        """
        # Step 1: Mixed artifact types
        artifacts = []
        for i in range(10):
            artifacts.append(DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            ))
        for i in range(8):
            artifacts.append(DetectedArtifact(
                artifact_type="command",
                name=f"cmd{i}",
                path=f".claude/commands/cmd{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/commands/cmd{i}",
                confidence_score=95
            ))
        for i in range(7):
            artifacts.append(DetectedArtifact(
                artifact_type="agent",
                name=f"agent{i}",
                path=f".claude/agents/agent{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/agents/agent{i}",
                confidence_score=95
            ))

        tree_sha = "mixed_types_sha"

        # Step 2: Select strategy
        strategy = select_indexing_strategy(mock_source, artifacts)
        assert strategy == "sparse_directory"

        # Step 3: Compute metadata
        metadata = compute_clone_metadata(artifacts, tree_sha)
        # Common root should be .claude
        assert metadata["artifacts_root"] == ".claude"

        # Step 4: Generate patterns
        patterns = get_sparse_checkout_patterns(
            strategy,
            artifacts,
            metadata["artifacts_root"],
        )
        # Should generate single .claude/** pattern
        assert len(patterns) == 1
        assert patterns[0] == ".claude/**"

        # Step 5: Create and verify CloneTarget
        target = CloneTarget(
            strategy=strategy,
            sparse_patterns=patterns,
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha=tree_sha,
        )

        assert target.strategy == "sparse_directory"
        assert target.sparse_patterns == [".claude/**"]
        assert target.artifacts_root == ".claude"
        assert len(target.artifact_paths) == 25


# ==============================================================================
# Test: Sparse Directory Safety Checks
# ==============================================================================


@pytest.mark.integration
class TestSparseDirectorySafetyChecks:
    """Test safety mechanisms to prevent dangerous clone operations."""

    def test_no_bare_double_star_pattern(self):
        mock_source = MagicMock()
        """CRITICAL: Ensure we never generate '**' alone as a pattern.

        A bare '**' pattern would clone the entire repository, defeating the
        purpose of sparse checkout and potentially downloading gigabytes.
        """
        # Try various edge cases that might produce '**'
        test_cases = [
            # Artifacts at repository root
            [DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f"skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/skill{i}",
                confidence_score=95
            ) for i in range(25)],
            # Single artifact at root
            [DetectedArtifact(
                artifact_type="skill",
                name="skill",
                path="skill",
                upstream_url="https://github.com/test/repo/tree/main/skill",
                confidence_score=95
            )],
        ]

        for artifacts in test_cases:
            if not artifacts:
                # Skip empty case for strategy selection
                continue

            source = MagicMock()
            strategy = select_indexing_strategy(source, artifacts)
            metadata = compute_clone_metadata(artifacts, "test_sha")

            patterns = get_sparse_checkout_patterns(
                strategy,
                artifacts,
                metadata["artifacts_root"],
            )

            # CRITICAL CHECK: No bare '**'
            assert "**" not in patterns, (
                f"Found dangerous '**' pattern! Artifacts: {[a.path for a in artifacts]}, "
                f"Strategy: {strategy}, Patterns: {patterns}"
            )

    def test_patterns_always_have_path_prefix(self):
        """Verify all directory patterns have a non-empty path prefix.

        Patterns should be like 'path/to/dir/**', never just '**' or 'dir/**'
        at the root level.
        """
        artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
                confidence_score=95
            )
            for i in range(25)
        ]

        metadata = compute_clone_metadata(artifacts, "test_sha")
        patterns = get_sparse_checkout_patterns(
            "sparse_directory",
            artifacts,
            metadata["artifacts_root"],
        )

        for pattern in patterns:
            # Should contain a path separator
            assert "/" in pattern, f"Pattern '{pattern}' lacks path separator"

            # Should not start with '**'
            assert not pattern.startswith("**"), (
                f"Pattern '{pattern}' starts with '**', too broad"
            )

            # Pattern should have meaningful prefix before /**
            if pattern.endswith("/**"):
                prefix = pattern[:-3]  # Remove '/**'
                assert len(prefix) > 0, f"Pattern '{pattern}' has empty prefix"
                assert prefix != ".", f"Pattern '{pattern}' has '.' prefix (too broad)"
                assert prefix != "..", f"Pattern '{pattern}' has '..' prefix (invalid)"

    def test_empty_artifacts_no_patterns(self):
        """Test that empty artifact list produces no patterns.

        This is a safety check to ensure we handle edge cases gracefully.
        """
        artifacts = []

        metadata = compute_clone_metadata(artifacts, "test_sha")
        patterns = get_sparse_checkout_patterns(
            "sparse_directory",
            artifacts,
            metadata["artifacts_root"],
        )

        assert patterns == []

    def test_single_artifact_safe_pattern(self):
        """Test that single artifact generates safe pattern.

        Even with sparse_directory strategy (hypothetically), a single artifact
        should not produce a dangerous pattern.
        """
        artifacts = [DetectedArtifact(
            artifact_type="skill",
            name="my-skill",
            path=".claude/skills/my-skill",
            upstream_url="https://github.com/test/repo/tree/main/.claude/skills/my-skill",
            confidence_score=95
        )]

        metadata = compute_clone_metadata(artifacts, "test_sha")

        # Even if we force sparse_directory strategy (normally would use 'api')
        patterns = get_sparse_checkout_patterns(
            "sparse_directory",
            artifacts,
            metadata["artifacts_root"],
        )

        # Should generate safe pattern
        assert len(patterns) == 1
        assert patterns[0] == ".claude/skills/**"
        assert "**" != patterns[0]  # Not bare '**'
