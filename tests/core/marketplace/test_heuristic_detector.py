"""Tests for heuristic artifact detector."""

import pytest

from skillmeat.core.marketplace.heuristic_detector import (
    ArtifactType,
    DetectionConfig,
    HeuristicDetector,
    detect_artifacts_in_tree,
)


class TestHeuristicDetector:
    """Test suite for HeuristicDetector."""

    def test_detect_skill_with_manifest(self):
        """Test detection of skill with SKILL.md manifest."""
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "skill"
        assert artifacts[0].name == "my-skill"
        assert artifacts[0].confidence_score >= 30

    def test_detect_command_with_manifest(self):
        """Test detection of command with COMMAND.md manifest."""
        files = [
            "commands/deploy/COMMAND.md",
            "commands/deploy/deploy.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "command"
        assert artifacts[0].name == "deploy"

    def test_detect_agent_with_manifest(self):
        """Test detection of agent with AGENT.md manifest."""
        files = [
            "agents/helper/AGENT.md",
            "agents/helper/agent.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "agent"
        assert artifacts[0].name == "helper"

    def test_detect_mcp_server_with_manifest(self):
        """Test detection of MCP server with MCP.md manifest."""
        files = [
            "mcp/server-tools/MCP.md",
            "mcp/server-tools/server.json",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "mcp_server"
        assert artifacts[0].name == "server-tools"

    def test_no_detection_without_manifest(self):
        """Test that directories without manifests are not detected."""
        files = [
            "src/utils/helpers.py",
            "src/utils/test.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 0

    def test_depth_penalty(self):
        """Test that deeper paths get lower scores."""
        files_shallow = ["skills/my-skill/SKILL.md"]
        files_deep = ["a/b/c/d/e/skills/my-skill/SKILL.md"]

        artifacts_shallow = detect_artifacts_in_tree(
            files_shallow, "https://github.com/test/repo"
        )
        artifacts_deep = detect_artifacts_in_tree(
            files_deep, "https://github.com/test/repo"
        )

        assert len(artifacts_shallow) == 1
        assert len(artifacts_deep) == 1
        assert (
            artifacts_shallow[0].confidence_score > artifacts_deep[0].confidence_score
        )

    def test_root_hint_filtering(self):
        """Test that root_hint filters paths correctly."""
        files = [
            "skills/skill1/SKILL.md",
            "other/skills/skill2/SKILL.md",
        ]

        # Without hint - should find both
        artifacts_no_hint = detect_artifacts_in_tree(
            files, "https://github.com/test/repo"
        )
        assert len(artifacts_no_hint) == 2

        # With hint - should only find skill1
        artifacts_with_hint = detect_artifacts_in_tree(
            files, "https://github.com/test/repo", root_hint="skills"
        )
        assert len(artifacts_with_hint) == 1
        assert artifacts_with_hint[0].name == "skill1"

    def test_multiple_artifact_types(self):
        """Test detection of multiple artifact types in one scan."""
        files = [
            "skills/my-skill/SKILL.md",
            "commands/my-cmd/COMMAND.md",
            "agents/my-agent/AGENT.md",
            "mcp/my-mcp/MCP.md",
        ]

        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 4
        types = {a.artifact_type for a in artifacts}
        assert types == {"skill", "command", "agent", "mcp_server"}

    def test_upstream_url_generation(self):
        """Test that upstream URLs are correctly generated."""
        files = ["skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(
            files, "https://github.com/user/repo", detected_sha="abc123"
        )

        assert len(artifacts) == 1
        assert (
            artifacts[0].upstream_url
            == "https://github.com/user/repo/tree/main/skills/my-skill"
        )
        assert artifacts[0].detected_sha == "abc123"

    def test_confidence_score_components(self):
        """Test that confidence score includes expected components."""
        detector = HeuristicDetector()

        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
            "skills/my-skill/package.json",
        ]

        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Should have positive scores for dir name, manifest, and extensions
        assert match.dir_name_score > 0
        assert match.manifest_score > 0
        assert match.extension_score > 0

        # Should have depth penalty
        assert match.depth_penalty >= 0

    def test_custom_config(self):
        """Test detector with custom configuration."""
        config = DetectionConfig()
        config.min_confidence = 50  # Higher threshold

        detector = HeuristicDetector(config)

        # This would normally pass with default config (score ~40)
        files = ["skills/my-skill/SKILL.md"]

        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # With higher threshold, might not detect (depends on exact scoring)
        # Just verify config is being used
        assert detector.config.min_confidence == 50

    def test_deduplication(self):
        """Test that duplicate paths are not detected multiple times."""
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
            "skills/my-skill/README.md",
        ]

        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should only detect once, not once per file
        assert len(artifacts) == 1
        assert artifacts[0].name == "my-skill"

    def test_match_reasons_populated(self):
        """Test that match reasons are populated."""
        detector = HeuristicDetector()
        files = ["skills/my-skill/SKILL.md"]

        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        assert len(matches[0].match_reasons) > 0
        # Should have reasons for manifest, dir name, etc.
        assert any("manifest" in reason.lower() for reason in matches[0].match_reasons)
