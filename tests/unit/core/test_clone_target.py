"""Unit tests for skillmeat.core.clone_target module."""

from datetime import datetime, timezone

import pytest

from skillmeat.core.clone_target import CloneTarget, get_changed_artifacts


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
