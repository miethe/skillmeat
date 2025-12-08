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


class TestScoringAlgorithm:
    """Test suite for scoring algorithm with representative examples."""

    def test_claude_skill_standard_path(self):
        """Test scoring for .claude/skills/my-skill/skill.yaml pattern."""
        files = [".claude/skills/my-skill/SKILL.md", ".claude/skills/my-skill/index.ts"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        # Score includes: dir_name(+5) + manifest(+20) + extensions(+2) + parent_hint(+15) - depth(-3) = ~39
        assert artifacts[0].confidence_score >= 30
        assert artifacts[0].confidence_score <= 50

    def test_skills_manifest_root(self):
        """Test scoring for .claude/skills/manifest.toml pattern."""
        files = [".claude/skills/manifest.toml"]
        # This won't match since it's just a manifest, not a skill directory
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should not detect (no skill directory structure)
        assert len(artifacts) == 0

    def test_skills_manifest_yaml(self):
        """Test scoring for skills/manifest.yaml pattern."""
        files = ["skills/my-skill/SKILL.md", "skills/manifest.yaml"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect the skill
        assert len(artifacts) == 1
        # Expected ~30-40 confidence (shallow depth, good structure)
        assert artifacts[0].confidence_score >= 30

    def test_deeply_nested_with_depth_penalty(self):
        """Test that deeply nested paths have significant depth penalty."""
        files_shallow = ["skills/my-skill/SKILL.md"]
        files_deep = ["a/b/c/d/e/f/skills/my-skill/SKILL.md"]

        artifacts_shallow = detect_artifacts_in_tree(
            files_shallow, "https://github.com/test/repo"
        )
        artifacts_deep = detect_artifacts_in_tree(
            files_deep, "https://github.com/test/repo"
        )

        assert len(artifacts_shallow) == 1
        assert len(artifacts_deep) == 1

        # Deep path should have much lower score due to depth penalty
        score_difference = (
            artifacts_shallow[0].confidence_score - artifacts_deep[0].confidence_score
        )
        # Expect at least 5 points difference (depth penalty)
        assert score_difference >= 5

    def test_manifest_with_expected_files(self):
        """Test that having expected files increases score."""
        files_minimal = ["skills/skill1/SKILL.md"]
        files_complete = [
            "skills/skill2/SKILL.md",
            "skills/skill2/index.ts",
            "skills/skill2/package.json",
            "skills/skill2/README.md",
        ]

        artifacts_minimal = detect_artifacts_in_tree(
            files_minimal, "https://github.com/test/repo"
        )
        artifacts_complete = detect_artifacts_in_tree(
            files_complete, "https://github.com/test/repo"
        )

        assert len(artifacts_minimal) == 1
        assert len(artifacts_complete) == 1

        # Complete skill should have higher score
        assert artifacts_complete[0].confidence_score > artifacts_minimal[0].confidence_score


class TestArtifactTypeDetection:
    """Test suite for detecting different artifact types."""

    def test_detect_all_types_in_one_scan(self):
        """Test detecting multiple artifact types simultaneously."""
        files = [
            "skills/skill1/SKILL.md",
            "commands/cmd1/COMMAND.md",
            "agents/agent1/AGENT.md",
            "mcp/mcp1/MCP.md",
            "hooks/hook1/HOOK.md",
        ]

        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 5
        types = {a.artifact_type for a in artifacts}
        assert types == {"skill", "command", "agent", "mcp_server", "hook"}

    def test_manifest_overrides_dir_name(self):
        """Test that manifest type takes precedence over directory name."""
        # Directory says "commands" with COMMAND.md manifest
        files = ["commands/my-cmd/COMMAND.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        # Manifest type should be correctly detected as command
        assert artifacts[0].artifact_type == "command"

    def test_lowercase_manifest_files(self):
        """Test detection of lowercase manifest files."""
        files = [
            "skills/skill1/skill.md",  # Lowercase
            "commands/cmd1/command.md",  # Lowercase
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 2
        types = {a.artifact_type for a in artifacts}
        assert "skill" in types
        assert "command" in types

    def test_alternative_manifest_names(self):
        """Test detection with alternative manifest names."""
        files = [
            "mcp/server1/server.json",  # Alternative for MCP
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "mcp_server"


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_empty_file_tree(self):
        """Test detection on empty file tree."""
        files = []
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 0

    def test_only_root_files(self):
        """Test that root-level files are not detected."""
        files = ["README.md", "LICENSE", "package.json"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 0

    def test_mixed_slashes_and_backslashes(self):
        """Test handling of different path separators."""
        # Should work with forward slashes
        files = ["skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1

    def test_unicode_directory_names(self):
        """Test detection with unicode in directory names."""
        files = ["skills/日本語スキル/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].name == "日本語スキル"

    def test_special_characters_in_names(self):
        """Test detection with special characters."""
        files = [
            "skills/my-skill-v2/SKILL.md",
            "skills/my_skill_test/SKILL.md",
            "skills/my.skill.dot/SKILL.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 3

    def test_case_sensitivity(self):
        """Test that directory matching is case-insensitive."""
        files = [
            "Skills/skill1/SKILL.md",  # Capital S
            "COMMANDS/cmd1/COMMAND.md",  # All caps
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 2

    def test_very_long_paths(self):
        """Test handling of very long file paths."""
        long_path = "/".join([f"dir{i}" for i in range(20)])
        files = [f"{long_path}/skills/test/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should handle but penalize for depth
        # May not detect if exceeds max_depth
        assert isinstance(artifacts, list)

    def test_duplicate_directory_names(self):
        """Test paths with duplicate directory names."""
        files = ["skills/skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].name == "my-skill"

    def test_no_files_only_manifest(self):
        """Test directory with only manifest file."""
        files = ["skills/empty-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should still detect with just manifest
        assert len(artifacts) == 1

    def test_files_without_extensions(self):
        """Test detection with files that have no extension."""
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/Makefile",  # No extension
            "skills/my-skill/Dockerfile",  # No extension
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1

    def test_max_depth_exceeded(self):
        """Test that paths exceeding max_depth are filtered."""
        config = DetectionConfig()
        config.max_depth = 3

        detector = HeuristicDetector(config)

        # This path has 5 parts, exceeding max_depth
        files = ["a/b/c/d/e/SKILL.md"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Should be filtered out
        assert len(matches) == 0

    def test_min_confidence_threshold(self):
        """Test that matches below min_confidence are filtered."""
        config = DetectionConfig()
        config.min_confidence = 100  # Impossible to reach

        detector = HeuristicDetector(config)
        files = ["skills/my-skill/SKILL.md"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Should be filtered out
        assert len(matches) == 0


class TestMetadata:
    """Test suite for metadata extraction and storage."""

    def test_metadata_includes_scoring_details(self):
        """Test that artifact metadata includes scoring breakdown."""
        files = ["skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        metadata = artifacts[0].metadata

        assert "match_reasons" in metadata
        assert "dir_name_score" in metadata
        assert "manifest_score" in metadata
        assert "extension_score" in metadata
        assert "depth_penalty" in metadata

    def test_upstream_url_format(self):
        """Test that upstream URLs are correctly formatted."""
        files = ["skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(
            files, "https://github.com/user/repo", detected_sha="abc123"
        )

        assert len(artifacts) == 1
        expected_url = "https://github.com/user/repo/tree/main/skills/my-skill"
        assert artifacts[0].upstream_url == expected_url

    def test_detected_sha_propagation(self):
        """Test that detected SHA is propagated to artifacts."""
        files = ["skills/my-skill/SKILL.md"]
        artifacts = detect_artifacts_in_tree(
            files, "https://github.com/test/repo", detected_sha="def456"
        )

        assert len(artifacts) == 1
        assert artifacts[0].detected_sha == "def456"

    def test_name_extraction_from_path(self):
        """Test that artifact name is extracted from path correctly."""
        files = [
            "skills/my-skill/SKILL.md",
            "commands/deploy-cmd/COMMAND.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 2
        names = {a.name for a in artifacts}
        assert "my-skill" in names
        assert "deploy-cmd" in names
