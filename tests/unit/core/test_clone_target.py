"""Unit tests for skillmeat.core.clone_target module."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from skillmeat.core.clone_target import (
    CloneTarget,
    compute_clone_metadata,
    get_changed_artifacts,
    get_deep_sparse_patterns,
    select_indexing_strategy,
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


class TestSelectIndexingStrategy:
    """Tests for select_indexing_strategy function."""

    def test_strategy_empty_returns_api(self):
        """Test that empty artifact list returns 'api' strategy."""
        source = MagicMock()
        artifacts = []

        result = select_indexing_strategy(source, artifacts)

        assert result == "api"

    def test_strategy_one_artifact_returns_api(self):
        """Test that single artifact returns 'api' strategy."""
        source = MagicMock()
        artifacts = [MockDetectedArtifact(".claude/skills/foo")]

        result = select_indexing_strategy(source, artifacts)

        assert result == "api"

    def test_strategy_two_artifacts_returns_api(self):
        """Test that two artifacts returns 'api' strategy."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "api"

    def test_strategy_three_artifacts_returns_sparse_manifest(self):
        """Test that exactly 3 artifacts returns 'sparse_manifest' strategy."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/skills/baz"),
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_manifest"

    def test_strategy_ten_artifacts_returns_sparse_manifest(self):
        """Test that 10 artifacts returns 'sparse_manifest' strategy."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(f".claude/skills/artifact{i}") for i in range(10)
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_manifest"

    def test_strategy_twenty_artifacts_returns_sparse_manifest(self):
        """Test that exactly 20 artifacts returns 'sparse_manifest' strategy."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(f".claude/skills/artifact{i}") for i in range(20)
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_manifest"

    def test_strategy_twentyone_common_root_returns_sparse_directory(self):
        """Test that 21+ artifacts with common root returns 'sparse_directory'."""
        source = MagicMock()
        # All artifacts share .claude/skills/ as common root
        artifacts = [
            MockDetectedArtifact(f".claude/skills/artifact{i}") for i in range(21)
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_directory"

    def test_strategy_twentyone_scattered_returns_sparse_manifest(self):
        """Test that 21+ scattered artifacts returns 'sparse_manifest'."""
        source = MagicMock()
        # Mix artifacts across different root directories - no common root
        artifacts = []
        for i in range(11):
            artifacts.append(MockDetectedArtifact(f".claude/skills/artifact{i}"))
        for i in range(10):
            artifacts.append(MockDetectedArtifact(f"tools/scripts/artifact{i}"))

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_manifest"

    def test_strategy_is_deterministic(self):
        """Test that same input always produces same output."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/skills/baz"),
        ]

        result1 = select_indexing_strategy(source, artifacts)
        result2 = select_indexing_strategy(source, artifacts)
        result3 = select_indexing_strategy(source, artifacts)

        assert result1 == result2 == result3 == "sparse_manifest"

    def test_strategy_large_count_with_root(self):
        """Test that 50 artifacts with common root returns 'sparse_directory'."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(f".claude/skills/artifact{i}") for i in range(50)
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == "sparse_directory"

    @pytest.mark.parametrize(
        "count,expected",
        [
            (0, "api"),
            (1, "api"),
            (2, "api"),
            (3, "sparse_manifest"),
            (10, "sparse_manifest"),
            (20, "sparse_manifest"),
        ],
    )
    def test_boundary_conditions(self, count, expected):
        """Test boundary conditions for strategy selection."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(f".claude/skills/artifact{i}") for i in range(count)
        ]

        result = select_indexing_strategy(source, artifacts)

        assert result == expected

    def test_different_artifact_types(self):
        """Test that strategy works with mixed artifact types."""
        source = MagicMock()
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(".claude/skills/bar", "skill"),
            MockDetectedArtifact(".claude/commands/cmd1", "command"),
            MockDetectedArtifact(".claude/agents/agent1", "agent"),
        ]

        result = select_indexing_strategy(source, artifacts)

        # 4 artifacts under common .claude/ root should be sparse_manifest
        assert result == "sparse_manifest"

    def test_large_scattered_artifacts_no_common_root(self):
        """Test that 100 artifacts with no common root returns 'sparse_manifest'."""
        source = MagicMock()
        # Create artifacts scattered across 10 different root directories
        artifacts = []
        for root_idx in range(10):
            for i in range(10):
                artifacts.append(
                    MockDetectedArtifact(f"root{root_idx}/path/artifact{i}")
                )

        result = select_indexing_strategy(source, artifacts)

        # Even with 100 artifacts, no common root means sparse_manifest
        assert result == "sparse_manifest"


class TestComputeCloneMetadata:
    """Tests for compute_clone_metadata function."""

    def test_compute_empty_list(self):
        """Test that empty artifact list returns expected structure."""
        result = compute_clone_metadata([], "abc123")

        assert result == {
            "artifacts_root": None,
            "artifact_paths": [],
            "sparse_patterns": [],
        }

    def test_compute_single_artifact(self):
        """Test that single artifact returns parent directory as root."""
        artifacts = [MockDetectedArtifact(".claude/skills/foo")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/skills"
        assert result["artifact_paths"] == [".claude/skills/foo"]
        assert len(result["sparse_patterns"]) == 1

    def test_compute_single_artifact_skill(self):
        """Test that skill type generates SKILL.md pattern."""
        artifacts = [MockDetectedArtifact(".claude/skills/my-skill", "skill")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/skills"
        assert result["artifact_paths"] == [".claude/skills/my-skill"]
        assert result["sparse_patterns"] == [".claude/skills/my-skill/SKILL.md"]

    def test_compute_single_artifact_command(self):
        """Test that command type generates command.yaml pattern."""
        artifacts = [MockDetectedArtifact(".claude/commands/my-cmd", "command")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/commands"
        assert result["artifact_paths"] == [".claude/commands/my-cmd"]
        assert result["sparse_patterns"] == [".claude/commands/my-cmd/command.yaml"]

    def test_compute_multiple_common_root(self):
        """Test that multiple artifacts under same parent share root."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact(".claude/skills/bar"),
            MockDetectedArtifact(".claude/skills/baz"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/skills"
        assert len(result["artifact_paths"]) == 3
        assert ".claude/skills/foo" in result["artifact_paths"]
        assert ".claude/skills/bar" in result["artifact_paths"]
        assert ".claude/skills/baz" in result["artifact_paths"]

    def test_compute_scattered_no_common_root(self):
        """Test that artifacts in different trees return artifacts_root=None."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo"),
            MockDetectedArtifact("tools/commands/bar"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] is None
        assert len(result["artifact_paths"]) == 2

    def test_compute_nested_paths(self):
        """Test deep nesting like .claude/skills/category/subcategory."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/category/subcategory/foo"),
            MockDetectedArtifact(".claude/skills/category/subcategory/bar"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/skills/category/subcategory"
        assert len(result["artifact_paths"]) == 2

    def test_compute_mixed_artifact_types(self):
        """Test skill, command, agent, hook, mcp together."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/my-skill", "skill"),
            MockDetectedArtifact(".claude/commands/my-cmd", "command"),
            MockDetectedArtifact(".claude/agents/my-agent", "agent"),
            MockDetectedArtifact(".claude/hooks/my-hook", "hook"),
            MockDetectedArtifact(".claude/mcp/my-server", "mcp"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        # Common root is .claude
        assert result["artifacts_root"] == ".claude"
        assert len(result["artifact_paths"]) == 5

        # Verify each type generates correct manifest pattern
        assert ".claude/skills/my-skill/SKILL.md" in result["sparse_patterns"]
        assert ".claude/commands/my-cmd/command.yaml" in result["sparse_patterns"]
        assert ".claude/agents/my-agent/agent.yaml" in result["sparse_patterns"]
        assert ".claude/hooks/my-hook/hook.yaml" in result["sparse_patterns"]
        assert ".claude/mcp/my-server/mcp.json" in result["sparse_patterns"]

    def test_compute_sparse_patterns_format(self):
        """Test patterns use forward slashes and correct manifest files."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(".claude/commands/bar", "command"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        # All patterns should use forward slashes
        for pattern in result["sparse_patterns"]:
            assert "\\" not in pattern
            assert "/" in pattern

        # Verify correct manifest files
        assert ".claude/skills/foo/SKILL.md" in result["sparse_patterns"]
        assert ".claude/commands/bar/command.yaml" in result["sparse_patterns"]

    def test_compute_unknown_artifact_type(self):
        """Test that unknown type generates directory/** pattern."""
        artifacts = [MockDetectedArtifact(".claude/custom/foo", "unknown_type")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["artifacts_root"] == ".claude/custom"
        assert result["artifact_paths"] == [".claude/custom/foo"]
        # Unknown types get directory/** pattern
        assert ".claude/custom/foo/**" in result["sparse_patterns"]

    def test_compute_single_artifact_at_root(self):
        """Test single artifact at repository root."""
        artifacts = [MockDetectedArtifact("skill-name", "skill")]

        result = compute_clone_metadata(artifacts, "abc123")

        # Parent of "skill-name" is empty string, which should be None
        assert result["artifacts_root"] is None
        assert result["artifact_paths"] == ["skill-name"]
        assert result["sparse_patterns"] == ["skill-name/SKILL.md"]

    def test_compute_paths_normalized_to_forward_slash(self):
        """Test that patterns use forward slashes consistently."""
        # Use forward-slash paths (the expected input format)
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(".claude/commands/bar", "command"),
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        # All sparse patterns should use forward slashes
        for pattern in result["sparse_patterns"]:
            assert "\\" not in pattern
            # Verify forward slashes are present in paths
            if pattern != "":
                assert "/" in pattern

    def test_compute_agent_type_uses_yaml(self):
        """Test that agent type generates agent.yaml pattern."""
        artifacts = [MockDetectedArtifact(".claude/agents/my-agent", "agent")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["sparse_patterns"] == [".claude/agents/my-agent/agent.yaml"]

    def test_compute_hook_type_uses_yaml(self):
        """Test that hook type generates hook.yaml pattern."""
        artifacts = [MockDetectedArtifact(".claude/hooks/pre-commit", "hook")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["sparse_patterns"] == [".claude/hooks/pre-commit/hook.yaml"]

    def test_compute_mcp_type_uses_json(self):
        """Test that mcp type generates mcp.json pattern."""
        artifacts = [MockDetectedArtifact(".claude/mcp/server", "mcp")]

        result = compute_clone_metadata(artifacts, "abc123")

        assert result["sparse_patterns"] == [".claude/mcp/server/mcp.json"]

    def test_compute_multiple_artifacts_different_depths(self):
        """Test artifacts at different nesting levels."""
        artifacts = [
            MockDetectedArtifact(".claude/skills/foo", "skill"),
            MockDetectedArtifact(
                ".claude/skills/category/bar", "skill"
            ),  # One level deeper
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        # Common root should be .claude/skills
        assert result["artifacts_root"] == ".claude/skills"
        assert len(result["artifact_paths"]) == 2

    def test_compute_common_path_is_artifact_itself(self):
        """Test when common path is one of the artifacts (edge case)."""
        # This can happen if artifacts are at the same exact level
        # For example, artifacts at paths "foo" and "foo" (duplicates)
        # os.path.commonpath would return "foo" which is in artifact_paths
        artifacts = [
            MockDetectedArtifact("path/to/artifact"),
            MockDetectedArtifact("path/to/artifact"),  # Duplicate path
        ]

        result = compute_clone_metadata(artifacts, "abc123")

        # The common path "path/to/artifact" is in artifact_paths,
        # so parent should be used: "path/to"
        assert result["artifacts_root"] == "path/to"
        assert len(result["artifact_paths"]) == 2


class TestCloneTargetSerialization:
    """Tests for CloneTarget serialization and deserialization methods."""

    def test_clone_target_to_json_structure(self):
        """Verify JSON output has all expected keys."""
        target = CloneTarget(
            strategy="sparse_manifest",
            sparse_patterns=[".claude/skills/foo/SKILL.md"],
            artifacts_root=".claude/skills",
            artifact_paths=[".claude/skills/foo"],
            tree_sha="abc123def456",
            computed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        json_str = target.to_json()
        data = json.loads(json_str)

        # Verify all expected keys are present
        assert "strategy" in data
        assert "sparse_patterns" in data
        assert "artifacts_root" in data
        assert "artifact_paths" in data
        assert "tree_sha" in data
        assert "computed_at" in data

        # Verify values
        assert data["strategy"] == "sparse_manifest"
        assert data["sparse_patterns"] == [".claude/skills/foo/SKILL.md"]
        assert data["artifacts_root"] == ".claude/skills"
        assert data["artifact_paths"] == [".claude/skills/foo"]
        assert data["tree_sha"] == "abc123def456"
        assert data["computed_at"] == "2024-01-15T10:30:00+00:00"

    def test_clone_target_from_json_roundtrip(self):
        """Test that to_json() -> from_json() preserves all data."""
        original = CloneTarget(
            strategy="sparse_directory",
            sparse_patterns=[".claude/**"],
            artifacts_root=".claude",
            artifact_paths=[".claude/skills/foo", ".claude/skills/bar"],
            tree_sha="xyz789",
            computed_at=datetime(2024, 6, 1, 14, 45, 30, tzinfo=timezone.utc),
        )

        json_str = original.to_json()
        restored = CloneTarget.from_json(json_str)

        # Verify all fields match
        assert restored.strategy == original.strategy
        assert restored.sparse_patterns == original.sparse_patterns
        assert restored.artifacts_root == original.artifacts_root
        assert restored.artifact_paths == original.artifact_paths
        assert restored.tree_sha == original.tree_sha
        assert restored.computed_at == original.computed_at

    def test_clone_target_to_dict_structure(self):
        """Verify dict has correct types."""
        target = CloneTarget(
            strategy="api",
            sparse_patterns=[],
            artifacts_root=None,
            artifact_paths=[".claude/skills/foo"],
            tree_sha="sha123",
            computed_at=datetime(2024, 3, 10, 8, 0, 0, tzinfo=timezone.utc),
        )

        data = target.to_dict()

        # Verify types
        assert isinstance(data["strategy"], str)
        assert isinstance(data["sparse_patterns"], list)
        assert data["artifacts_root"] is None
        assert isinstance(data["artifact_paths"], list)
        assert isinstance(data["tree_sha"], str)
        assert isinstance(data["computed_at"], str)  # Should be ISO format string

        # Verify datetime is ISO format
        assert data["computed_at"] == "2024-03-10T08:00:00+00:00"

    def test_clone_target_from_dict_with_all_fields(self):
        """Test reconstruction from complete dict."""
        data = {
            "strategy": "sparse_manifest",
            "sparse_patterns": [".claude/skills/test/SKILL.md"],
            "artifacts_root": ".claude/skills",
            "artifact_paths": [".claude/skills/test"],
            "tree_sha": "test_sha",
            "computed_at": "2024-02-20T12:00:00+00:00",
        }

        target = CloneTarget.from_dict(data)

        assert target.strategy == "sparse_manifest"
        assert target.sparse_patterns == [".claude/skills/test/SKILL.md"]
        assert target.artifacts_root == ".claude/skills"
        assert target.artifact_paths == [".claude/skills/test"]
        assert target.tree_sha == "test_sha"
        assert target.computed_at == datetime(
            2024, 2, 20, 12, 0, 0, tzinfo=timezone.utc
        )

    def test_clone_target_all_strategies(self):
        """Test serialization with all valid strategy values."""
        strategies = ["api", "sparse_manifest", "sparse_directory"]

        for strategy in strategies:
            target = CloneTarget(
                strategy=strategy,
                sparse_patterns=[],
                tree_sha="sha",
            )

            # Should serialize/deserialize without error
            json_str = target.to_json()
            restored = CloneTarget.from_json(json_str)

            assert restored.strategy == strategy

    def test_clone_target_empty_lists(self):
        """Handle empty sparse_patterns and artifact_paths."""
        target = CloneTarget(
            strategy="api",
            sparse_patterns=[],
            artifact_paths=[],
            tree_sha="empty_test",
        )

        # Verify serialization preserves empty lists
        data = target.to_dict()
        assert data["sparse_patterns"] == []
        assert data["artifact_paths"] == []

        # Verify roundtrip
        json_str = target.to_json()
        restored = CloneTarget.from_json(json_str)
        assert restored.sparse_patterns == []
        assert restored.artifact_paths == []

    def test_clone_target_none_artifacts_root(self):
        """Handle artifacts_root=None."""
        target = CloneTarget(
            strategy="sparse_manifest",
            artifacts_root=None,
            tree_sha="none_test",
        )

        # Verify serialization preserves None
        data = target.to_dict()
        assert data["artifacts_root"] is None

        # Verify roundtrip
        json_str = target.to_json()
        restored = CloneTarget.from_json(json_str)
        assert restored.artifacts_root is None

    def test_clone_target_datetime_iso_format(self):
        """Verify computed_at serializes as ISO string."""
        dt = datetime(2024, 12, 25, 15, 30, 45, 123456, tzinfo=timezone.utc)
        target = CloneTarget(
            strategy="api",
            tree_sha="dt_test",
            computed_at=dt,
        )

        data = target.to_dict()
        # Verify ISO format with microseconds
        assert data["computed_at"] == "2024-12-25T15:30:45.123456+00:00"

    def test_clone_target_datetime_with_z_suffix(self):
        """Test that from_json handles 'Z' UTC suffix."""
        json_str = """
        {
            "strategy": "api",
            "sparse_patterns": [],
            "artifacts_root": null,
            "artifact_paths": [],
            "tree_sha": "z_suffix_test",
            "computed_at": "2024-01-01T00:00:00Z"
        }
        """

        target = CloneTarget.from_json(json_str)

        # Verify Z suffix is handled correctly as UTC
        assert target.computed_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_clone_target_invalid_strategy_raises(self):
        """Invalid strategy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CloneTarget(
                strategy="invalid_strategy",
                tree_sha="invalid_test",
            )

        assert "strategy must be one of" in str(exc_info.value)
        assert "invalid_strategy" in str(exc_info.value)

    def test_clone_target_from_dict_missing_required_field(self):
        """Test that missing required field raises KeyError."""
        data = {
            "sparse_patterns": [],
            "artifacts_root": None,
            "artifact_paths": [],
            "tree_sha": "missing_strategy",
        }

        with pytest.raises(KeyError):
            CloneTarget.from_dict(data)

    def test_clone_target_from_dict_defaults(self):
        """Test that from_dict applies defaults for optional fields."""
        # Minimal dict with only required strategy field
        data = {
            "strategy": "api",
        }

        target = CloneTarget.from_dict(data)

        # Verify defaults are applied
        assert target.strategy == "api"
        assert target.sparse_patterns == []
        assert target.artifacts_root is None
        assert target.artifact_paths == []
        assert target.tree_sha == ""
        # computed_at should be set to current time (within 1 second)
        assert isinstance(target.computed_at, datetime)
        assert target.computed_at.tzinfo == timezone.utc

    def test_clone_target_from_dict_invalid_strategy(self):
        """Test that invalid strategy in dict raises ValueError."""
        data = {
            "strategy": "not_a_valid_strategy",
            "tree_sha": "invalid",
        }

        with pytest.raises(ValueError) as exc_info:
            CloneTarget.from_dict(data)

        assert "strategy must be one of" in str(exc_info.value)

    def test_clone_target_from_dict_invalid_datetime_type(self):
        """Test that invalid datetime type raises ValueError."""
        data = {
            "strategy": "api",
            "computed_at": 12345,  # Invalid: should be string or datetime
        }

        with pytest.raises(ValueError) as exc_info:
            CloneTarget.from_dict(data)

        assert "computed_at must be a datetime or ISO string" in str(exc_info.value)

    def test_clone_target_json_pretty_formatting(self):
        """Test that to_json() produces pretty-formatted output."""
        target = CloneTarget(
            strategy="sparse_manifest",
            sparse_patterns=[".claude/skills/foo/SKILL.md"],
            tree_sha="pretty_test",
        )

        json_str = target.to_json()

        # Verify indentation (pretty formatting)
        assert "\n" in json_str
        assert "  " in json_str  # 2-space indentation

        # Verify it's still valid JSON
        data = json.loads(json_str)
        assert data["strategy"] == "sparse_manifest"

    def test_clone_target_from_json_malformed_raises(self):
        """Test that malformed JSON raises JSONDecodeError."""
        malformed_json = '{"strategy": "api", invalid json}'

        with pytest.raises(json.JSONDecodeError):
            CloneTarget.from_json(malformed_json)

    def test_clone_target_roundtrip_with_datetime_instance(self):
        """Test that from_dict accepts datetime instance directly."""
        dt = datetime(2024, 7, 15, 9, 0, 0, tzinfo=timezone.utc)
        data = {
            "strategy": "sparse_directory",
            "computed_at": dt,  # Pass datetime instance, not string
        }

        target = CloneTarget.from_dict(data)

        assert target.computed_at == dt

    def test_clone_target_complex_artifact_paths(self):
        """Test serialization with complex nested artifact paths."""
        target = CloneTarget(
            strategy="sparse_directory",
            sparse_patterns=[
                ".claude/skills/**",
                ".claude/commands/**",
                ".codex/agents/**",
            ],
            artifacts_root=None,
            artifact_paths=[
                ".claude/skills/deep/nested/artifact1",
                ".claude/commands/another/deep/path",
                ".codex/agents/different/root",
            ],
            tree_sha="complex_test",
        )

        # Roundtrip test
        json_str = target.to_json()
        restored = CloneTarget.from_json(json_str)

        assert restored.sparse_patterns == target.sparse_patterns
        assert restored.artifact_paths == target.artifact_paths
        assert restored.artifacts_root is None
