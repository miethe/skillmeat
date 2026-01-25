"""Unit tests for skillmeat.core.clone_target module."""

from datetime import datetime, timezone

import pytest

from skillmeat.core.clone_target import (
    CloneTarget,
    get_changed_artifacts,
    get_deep_sparse_patterns,
)


class MockDetectedArtifact:
    """Mock DetectedArtifact for testing."""

    def __init__(self, path: str, artifact_type: str = "skill"):
        self.path = path
        self.artifact_type = artifact_type


class TestGetChangedArtifacts:
    """Tests for get_changed_artifacts function."""

    def test_first_time_indexing_returns_all_artifacts(self):
        """Test that first-time indexing (no cache) returns all artifacts."""
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = get_changed_artifacts(None, current_artifacts)

        assert len(result) == 2
        assert result == current_artifacts

    def test_no_changes_returns_empty_list(self):
        """Test that when all artifacts are cached, returns empty list."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 0
        assert result == []

    def test_new_artifact_added_returns_only_new(self):
        """Test that adding a new artifact returns only the new one."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/skills/baz"),
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 1
        assert result[0].path == ".claude/skills/baz"

    def test_artifact_removed_returns_empty(self):
        """Test that artifact removal doesn't create changed artifacts."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 0

    def test_multiple_new_artifacts_returns_all_new(self):
        """Test that multiple new artifacts are all returned."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/skills/baz"),
            MockDetectedArtifact(".claude/skills/qux"),
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 3
        new_paths = {a.path for a in result}
        assert new_paths == {
            ".claude/skills/bar",
            ".claude/skills/baz",
            ".claude/skills/qux",
        }

    def test_empty_current_artifacts_returns_empty(self):
        """Test that empty current artifacts returns empty list."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = []

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 0

    def test_empty_cache_with_empty_current_returns_empty(self):
        """Test that first-time indexing with no artifacts returns empty."""
        current_artifacts = []

        result = get_changed_artifacts(None, current_artifacts)

        assert len(result) == 0

    def test_different_artifact_types(self):
        """Test that function works with different artifact types."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[
                ".claude/skills/foo",
                ".claude/commands/bar",
            ],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(".claude/commands/bar", "command"),
            MockDetectedArtifact(".claude/agents/baz", "agent"),
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 1
        assert result[0].path == ".claude/agents/baz"
        assert result[0].artifact_type == "agent"

    def test_path_comparison_is_exact(self):
        """Test that path comparison is exact (no partial matches)."""
        cached = CloneTarget(
            strategy="sparse_manifest",
            artifact_paths=[".claude/skills/foo"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )
        current_artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/foobar"),  # Similar but different
        ]

        result = get_changed_artifacts(cached, current_artifacts)

        assert len(result) == 1
        assert result[0].path == ".claude/skills/foobar"


class TestGetDeepSparsePatterns:
    """Tests for get_deep_sparse_patterns function."""

    def test_empty_list_returns_empty_patterns(self):
        """Test that empty artifact list returns empty patterns."""
        result = get_deep_sparse_patterns([])

        assert result == []

    def test_single_artifact_returns_directory_pattern(self):
        """Test that single artifact returns directory pattern with /**."""
        artifacts = [MockDetectedArtifact(".claude/skills/foo")]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 1
        assert result[0] == ".claude/skills/foo/**"

    def test_multiple_artifacts_return_multiple_patterns(self):
        """Test that multiple artifacts return multiple directory patterns."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/commands/baz"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 3
        assert ".claude/skills/foo/**" in result
        assert ".claude/skills/bar/**" in result
        assert ".claude/commands/baz/**" in result

    def test_path_separators_normalized_to_forward_slashes(self):
        """Test that Windows-style path separators are normalized."""
        artifacts = [
            MockDetectedArtifact(".claude\\skills\\foo"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 2
        assert ".claude/skills/foo/**" in result
        assert ".claude/skills/bar/**" in result

    def test_duplicate_paths_are_deduplicated(self):
        """Test that duplicate artifact paths result in single pattern."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 2
        assert ".claude/skills/foo/**" in result
        assert ".claude/skills/bar/**" in result

    def test_path_already_ending_with_double_star_not_duplicated(self):
        """Test that paths already ending with /** are not modified."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo/**"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 2
        assert ".claude/skills/foo/**" in result
        assert ".claude/skills/bar/**" in result

    def test_different_artifact_types(self):
        """Test that function works with different artifact types."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(".claude/commands/bar", "command"),
            MockDetectedArtifact(".claude/agents/baz", "agent"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 3
        assert ".claude/skills/foo/**" in result
        assert ".claude/commands/bar/**" in result
        assert ".claude/agents/baz/**" in result

    def test_nested_paths(self):
        """Test that deeply nested paths are handled correctly."""
        artifacts = [
            MockDetectedArtifact("path/to/deep/nested/artifact"),
            MockDetectedArtifact("another/very/deep/path/artifact"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 2
        assert "path/to/deep/nested/artifact/**" in result
        assert "another/very/deep/path/artifact/**" in result

    def test_root_level_artifacts(self):
        """Test that root-level artifacts work correctly."""
        artifacts = [
            MockDetectedArtifact("artifact1"),
            MockDetectedArtifact("artifact2"),
        ]

        result = get_deep_sparse_patterns(artifacts)

        assert len(result) == 2
        assert "artifact1/**" in result
        assert "artifact2/**" in result
