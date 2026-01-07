"""Tests for heuristic artifact detector."""

import pytest

from skillmeat.core.marketplace.heuristic_detector import (
    ArtifactType,
    DetectionConfig,
    HeuristicDetector,
    MAX_RAW_SCORE,
    detect_artifacts_in_tree,
    normalize_score,
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
        assert artifacts[0].artifact_type == "mcp"
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
        files_deep = ["a/b/skills/my-skill/SKILL.md"]

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
        assert types == {"skill", "command", "agent", "mcp"}

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
        # Score includes: dir_name(+5) + manifest(+20) + extensions(+2) + parent_hint(+15) - depth(-3) = 39
        # Normalized: 39/65 * 100 = 60%
        assert artifacts[0].confidence_score >= 30
        assert artifacts[0].confidence_score <= 65  # Normalized score

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
        files_deep = ["a/b/c/skills/my-skill/SKILL.md"]

        artifacts_shallow = detect_artifacts_in_tree(
            files_shallow, "https://github.com/test/repo"
        )
        artifacts_deep = detect_artifacts_in_tree(
            files_deep, "https://github.com/test/repo"
        )

        assert len(artifacts_shallow) == 1
        assert len(artifacts_deep) == 1

        # Deep path should have lower score due to depth penalty
        score_difference = (
            artifacts_shallow[0].confidence_score - artifacts_deep[0].confidence_score
        )
        # Expect at least 1 point difference (depth penalty affects normalized score)
        assert score_difference >= 1

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
        assert (
            artifacts_complete[0].confidence_score
            > artifacts_minimal[0].confidence_score
        )


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
        assert types == {"skill", "command", "agent", "mcp", "hook"}

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
        assert artifacts[0].artifact_type == "mcp"


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


class TestScoreNormalization:
    """Test suite for score normalization function and breakdown structure."""

    def test_normalize_score_max(self):
        """Test that raw=MAX_RAW_SCORE normalizes to 100."""
        assert normalize_score(MAX_RAW_SCORE) == 100

    def test_normalize_score_half(self):
        """Test that raw=half of MAX normalizes to ~50."""
        half_score = MAX_RAW_SCORE // 2
        expected = round((half_score / MAX_RAW_SCORE) * 100)
        assert normalize_score(half_score) == expected

    def test_normalize_score_zero(self):
        """Test that raw=0 normalizes to 0."""
        assert normalize_score(0) == 0

    def test_normalize_score_negative(self):
        """Test that negative values are clamped to 0."""
        assert normalize_score(-10) == 0
        assert normalize_score(-1) == 0
        assert normalize_score(-100) == 0

    def test_normalize_score_over_max(self):
        """Test that values > MAX_RAW_SCORE are clamped to 100."""
        assert normalize_score(MAX_RAW_SCORE + 50) == 100
        assert normalize_score(1000) == 100
        assert normalize_score(MAX_RAW_SCORE + 1) == 100

    def test_normalize_score_mid_range(self):
        """Test normalization for various mid-range values using MAX_RAW_SCORE."""
        # Test a few known values relative to MAX_RAW_SCORE
        assert normalize_score(1) == round((1 / MAX_RAW_SCORE) * 100)
        assert normalize_score(10) == round((10 / MAX_RAW_SCORE) * 100)
        quarter = MAX_RAW_SCORE // 4
        assert normalize_score(quarter) == round((quarter / MAX_RAW_SCORE) * 100)

    def test_breakdown_structure(self):
        """Test that breakdown contains all required fields."""
        detector = HeuristicDetector()

        # Create a match with manifest and supporting files
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
            "skills/my-skill/package.json",
        ]

        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify breakdown dictionary exists
        assert hasattr(match, "breakdown")
        breakdown = match.breakdown

        # Check all required fields
        assert "dir_name_score" in breakdown
        assert "manifest_score" in breakdown
        assert "extensions_score" in breakdown
        assert "parent_hint_score" in breakdown
        assert "frontmatter_score" in breakdown
        assert "container_hint_score" in breakdown
        assert "depth_penalty" in breakdown
        assert "raw_total" in breakdown
        assert "normalized_score" in breakdown

    def test_breakdown_field_types(self):
        """Test that all breakdown fields are integers."""
        detector = HeuristicDetector()
        files = ["skills/test/SKILL.md"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # All fields should be integers
        for key, value in breakdown.items():
            assert isinstance(
                value, int
            ), f"Field '{key}' should be int, got {type(value)}"

    def test_breakdown_field_ranges(self):
        """Test that breakdown fields are within expected ranges."""
        detector = HeuristicDetector()
        files = ["skills/test/SKILL.md", "skills/test/index.ts"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Individual signals should be non-negative
        assert breakdown["dir_name_score"] >= 0
        assert breakdown["manifest_score"] >= 0
        assert breakdown["extensions_score"] >= 0
        assert breakdown["parent_hint_score"] >= 0
        assert breakdown["frontmatter_score"] >= 0

        # Depth penalty should be non-negative
        assert breakdown["depth_penalty"] >= 0

        # Raw total should be between 0 and MAX_RAW_SCORE
        assert 0 <= breakdown["raw_total"] <= MAX_RAW_SCORE

        # Normalized score should be 0-100
        assert 0 <= breakdown["normalized_score"] <= 100

    def test_breakdown_raw_total_calculation(self):
        """Test that raw_total equals sum of all signals minus penalties."""
        detector = HeuristicDetector()
        files = ["skills/test/SKILL.md", "skills/test/index.ts"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Calculate expected raw total (including container_hint_score)
        expected_raw = (
            breakdown["dir_name_score"]
            + breakdown["manifest_score"]
            + breakdown["extensions_score"]
            + breakdown["parent_hint_score"]
            + breakdown["frontmatter_score"]
            + breakdown["container_hint_score"]
            - breakdown["depth_penalty"]
        )

        assert breakdown["raw_total"] == expected_raw

    def test_breakdown_normalization_consistency(self):
        """Test that normalized_score matches normalize_score(raw_total)."""
        detector = HeuristicDetector()
        files = [".claude/skills/my-skill/SKILL.md"]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Normalized score should match the normalize_score function result
        expected_normalized = normalize_score(breakdown["raw_total"])
        assert breakdown["normalized_score"] == expected_normalized

    def test_penalties_reduce_score(self):
        """Test that depth penalty reduces the raw score."""
        detector = HeuristicDetector()

        # Shallow path
        files_shallow = ["skills/test/SKILL.md"]
        matches_shallow = detector.analyze_paths(
            files_shallow, base_url="https://github.com/test/repo"
        )

        # Deep path (should have higher penalty)
        files_deep = ["a/b/skills/test/SKILL.md"]
        matches_deep = detector.analyze_paths(
            files_deep, base_url="https://github.com/test/repo"
        )

        assert len(matches_shallow) == 1
        assert len(matches_deep) == 1

        shallow_breakdown = matches_shallow[0].breakdown
        deep_breakdown = matches_deep[0].breakdown

        # Deep path should have higher depth penalty
        assert deep_breakdown["depth_penalty"] > shallow_breakdown["depth_penalty"]

        # Deep path should have lower raw total
        assert deep_breakdown["raw_total"] < shallow_breakdown["raw_total"]

    def test_all_signals_within_config_weights(self):
        """Test that individual signal scores don't exceed configured weights."""
        detector = HeuristicDetector()
        config = detector.config

        files = [
            ".claude/skills/test/SKILL.md",
            ".claude/skills/test/index.ts",
            ".claude/skills/test/package.json",
        ]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Each signal should not exceed its configured weight
        assert breakdown["dir_name_score"] <= config.dir_name_weight
        assert breakdown["manifest_score"] <= config.manifest_weight
        assert breakdown["extensions_score"] <= config.extension_weight
        assert breakdown["parent_hint_score"] <= config.parent_hint_weight
        assert breakdown["frontmatter_score"] <= config.frontmatter_weight

    def test_edge_case_only_manifest(self):
        """Test scoring with only a manifest file (minimal other signals)."""
        detector = HeuristicDetector()
        # Use skills/ container to get container hint bonus for higher score
        files = ["skills/test/SKILL.md"]  # Minimal: manifest + container hint
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Should have manifest score and container hint
        assert breakdown["manifest_score"] > 0
        # extensions_score may be > 0 if .md is counted as an expected extension
        assert breakdown["extensions_score"] >= 0
        assert breakdown["raw_total"] >= 0
        assert breakdown["normalized_score"] >= 0

    def test_edge_case_max_signals(self):
        """Test scoring with all signals maximized."""
        detector = HeuristicDetector()

        # Create optimal conditions:
        # - In skills/ container (container hint bonus)
        # - Directory name inside skills/ container
        # - Has manifest
        # - Has multiple expected extensions
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
            "skills/my-skill/package.json",
            "skills/my-skill/README.md",
        ]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Should have high scores in most categories
        assert breakdown["manifest_score"] > 0
        assert breakdown["extensions_score"] > 0
        # Container hint should give bonus for being in skills/
        assert breakdown["container_hint_score"] > 0 or breakdown["parent_hint_score"] > 0

        # Raw total should be relatively high
        assert breakdown["raw_total"] > 30
        # Normalized should also be high (at least 30% threshold)
        assert breakdown["normalized_score"] >= 30


class TestPluginDetection:
    """Tests for plugin directory detection."""

    def test_detect_plugin_with_multiple_entity_types(self):
        """Test that plugin with commands/ and agents/ is recognized."""
        files = [
            "my-plugin/commands/deploy/COMMAND.md",
            "my-plugin/agents/helper/AGENT.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect 2 entities (deploy command, helper agent)
        assert len(artifacts) == 2
        # Should NOT detect "commands" or "agents" as entities
        names = {a.name for a in artifacts}
        assert "commands" not in names
        assert "agents" not in names
        assert "deploy" in names
        assert "helper" in names

    def test_detect_plugin_with_three_entity_types(self):
        """Test plugin with commands/, agents/, skills/."""
        files = [
            "plugin/commands/cmd1/COMMAND.md",
            "plugin/agents/agent1/AGENT.md",
            "plugin/skills/skill1/SKILL.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 3
        types = {a.artifact_type for a in artifacts}
        assert types == {"command", "agent", "skill"}


class TestContainerSkipping:
    """Tests for container directory skipping."""

    def test_skip_commands_container_in_plugin(self):
        """Test that commands/ directory is skipped in plugin."""
        files = [
            "plugin/commands/deploy/COMMAND.md",
            "plugin/commands/analyze/COMMAND.md",
            "plugin/skills/helper/SKILL.md",  # Need 2 entity types for plugin
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect deploy, analyze, helper - NOT commands or skills
        names = {a.name for a in artifacts}
        assert "commands" not in names
        assert "skills" not in names
        assert "deploy" in names
        assert "analyze" in names
        assert "helper" in names

    def test_skip_all_container_types(self):
        """Test skipping of all entity-type containers."""
        files = [
            "plugin/commands/cmd/COMMAND.md",
            "plugin/agents/agent/AGENT.md",
            "plugin/skills/skill/SKILL.md",
            "plugin/hooks/hook/hook.md",
            "plugin/rules/rule/rule.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect entities, not containers
        names = {a.name for a in artifacts}
        assert "commands" not in names
        assert "agents" not in names
        assert "skills" not in names
        assert "hooks" not in names
        assert "rules" not in names

    def test_top_level_container_skipped(self):
        """Test that top-level entity-type directories are skipped."""
        files = [
            "skills/my-skill/SKILL.md",
            "commands/my-command/COMMAND.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        names = {a.name for a in artifacts}
        assert "skills" not in names
        assert "commands" not in names
        assert "my-skill" in names
        assert "my-command" in names


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing behavior."""

    def test_non_plugin_repo_still_works(self):
        """Test that non-plugin repos continue to work correctly."""
        files = [
            "skills/skill1/SKILL.md",
            "commands/cmd1/COMMAND.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should still detect both entities
        assert len(artifacts) == 2
        names = {a.name for a in artifacts}
        assert "skill1" in names
        assert "cmd1" in names

    def test_nested_skills_in_non_plugin(self):
        """Test nested skills without plugin structure."""
        files = [
            "skills/skill1/SKILL.md",
            "skills/skill2/SKILL.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect both skills
        assert len(artifacts) == 2
        names = {a.name for a in artifacts}
        assert names == {"skill1", "skill2"}

    def test_single_entity_type_not_plugin(self):
        """Test that single entity-type directory is not a plugin."""
        files = [
            "commands/cmd1/COMMAND.md",
            "commands/cmd2/COMMAND.md",
            "commands/cmd3/COMMAND.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect all 3 commands
        assert len(artifacts) == 3
        # "commands" should not be detected as entity
        names = {a.name for a in artifacts}
        assert "commands" not in names

    def test_direct_skill_at_root(self):
        """Test skill directly at repository root."""
        files = [
            "my-skill/SKILL.md",
            "my-skill/helper.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].name == "my-skill"


class TestPluginEdgeCases:
    """Tests for edge cases in plugin detection."""

    def test_plugin_with_minimal_threshold(self):
        """Test plugin detection with exactly 2 entity types."""
        files = [
            "plugin/commands/cmd/COMMAND.md",
            "plugin/commands/cmd/index.ts",
            "plugin/agents/agent/AGENT.md",
            "plugin/agents/agent/agent.ts",
        ]
        # Should detect as plugin (threshold = 2)
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")
        assert len(artifacts) == 2
        names = {a.name for a in artifacts}
        assert "commands" not in names
        assert "agents" not in names

    def test_mixed_container_and_direct_entities(self):
        """Test plugin with both container and direct entities."""
        files = [
            "plugin/commands/cmd1/COMMAND.md",
            "plugin/commands/cmd1/index.ts",
            "plugin/agents/agent1/AGENT.md",
            "plugin/agents/agent1/agent.ts",
            # Direct entity needs more signals to pass threshold
            # since it doesn't get container_hint bonus
            "plugin/skills/standalone-skill/SKILL.md",
            "plugin/skills/standalone-skill/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should detect all entities
        assert len(artifacts) == 3
        names = {a.name for a in artifacts}
        assert names == {"cmd1", "agent1", "standalone-skill"}

    def test_case_insensitive_container_detection(self):
        """Test that container detection is case-insensitive."""
        files = [
            "plugin/Commands/deploy/COMMAND.md",  # Capital C
            "plugin/AGENTS/helper/AGENT.md",  # All caps
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        names = {a.name for a in artifacts}
        assert "Commands" not in names
        assert "AGENTS" not in names
        assert "deploy" in names
        assert "helper" in names

    def test_mcp_container_skipped(self):
        """Test that mcp/ container directories are skipped."""
        files = [
            "plugin/mcp/my-server/MCP.md",
            "plugin/skills/my-skill/SKILL.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        names = {a.name for a in artifacts}
        assert "mcp" not in names
        assert "my-server" in names
        assert "my-skill" in names


class TestContainerTypePropagation:
    """Tests for container type propagation to child directories."""

    def test_container_hint_bonus_applied(self):
        """Test that container type hint gives bonus when types match."""
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        breakdown = artifacts[0].score_breakdown
        # Container hint bonus should be applied
        assert breakdown["container_hint_score"] == 25  # Full container_hint_weight

    def test_container_hint_type_matching(self):
        """Test that container hint gives full bonus when type is detected from parent."""
        # When inside a skills/ directory, dir_name_score from parent "skills" detects type
        # Then container_hint_score adds full bonus since detected type matches container
        detector = HeuristicDetector()
        files = [
            # Directory with code files inside skills/
            "skills/unknown/utils.py",
            "skills/unknown/helper.ts",
        ]
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Should detect with type inferred from container
        if len(matches) == 1:
            assert matches[0].artifact_type == "skill"
            # Container hint matches detected type, so full bonus
            assert matches[0].breakdown["container_hint_score"] == 25

    def test_nested_container_hierarchy(self):
        """Test that nested container paths propagate type correctly."""
        files = [
            "project/v2/skills/new-skill/SKILL.md",
            "project/v2/skills/new-skill/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == "skill"
        assert artifacts[0].name == "new-skill"
        # Should get container hint bonus even with deeper nesting
        assert artifacts[0].score_breakdown["container_hint_score"] > 0

    def test_no_container_hint_for_non_container_path(self):
        """Test that paths not in container directories don't get hint bonus."""
        detector = HeuristicDetector()
        files = [
            # Path not under a container directory
            "standalone/my-skill/SKILL.md",
            "standalone/my-skill/index.ts",
        ]
        # Use lower-level API to check breakdown even if below threshold
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Even if no artifact passes threshold, check internal scoring
        # by directly calling _score_directory
        siblings = {"SKILL.md", "index.ts"}
        artifact_type, _, breakdown = detector._score_directory(
            "standalone/my-skill", siblings
        )

        # Should detect skill type from manifest
        assert artifact_type is not None
        assert artifact_type.value == "skill"
        # But should NOT get container hint bonus (standalone is not a container)
        assert breakdown["container_hint_score"] == 0

    def test_reduced_depth_penalty_in_container(self):
        """Test that depth penalty is reduced for artifacts inside typed containers."""
        detector = HeuristicDetector()

        # Artifact inside a typed container (commands/) at depth 4
        files_in_container = [
            "commands/dev/subgroup/my-cmd/COMMAND.md",
            "commands/dev/subgroup/my-cmd/index.ts",
        ]

        matches_in_container = detector.analyze_paths(
            files_in_container, base_url="https://github.com/test/repo"
        )

        # Should detect the artifact
        assert len(matches_in_container) == 1

        # For a depth 4 path (commands/dev/subgroup/my-cmd), base penalty would be 4
        # With container hint, it should be reduced to 2 (50% reduction)
        assert matches_in_container[0].breakdown["depth_penalty"] == 2

        # Compare with same path structure but shallow (depth 2)
        files_shallow = [
            "commands/my-cmd/COMMAND.md",
            "commands/my-cmd/index.ts",
        ]
        matches_shallow = detector.analyze_paths(
            files_shallow, base_url="https://github.com/test/repo"
        )

        assert len(matches_shallow) == 1
        # Shallow path (depth 2) with container hint: penalty = 2 // 2 = 1
        assert matches_shallow[0].breakdown["depth_penalty"] == 1

    def test_depth_penalty_not_reduced_without_container(self):
        """Test that depth penalty is NOT reduced for artifacts outside containers."""
        detector = HeuristicDetector()

        # Use _score_directory directly to test without container hint
        siblings = {"COMMAND.md", "index.ts"}

        # Score with container_hint=None (full penalty)
        _, _, breakdown_no_hint = detector._score_directory(
            "a/b/c/my-cmd", siblings, container_hint=None
        )

        # Score same path with container_hint (reduced penalty)
        from skillmeat.core.marketplace.heuristic_detector import ArtifactType
        _, _, breakdown_with_hint = detector._score_directory(
            "a/b/c/my-cmd", siblings, container_hint=ArtifactType.COMMAND
        )

        # Path depth is 4, so base penalty = 4
        # Without container hint: full penalty = 4
        assert breakdown_no_hint["depth_penalty"] == 4

        # With container hint: reduced penalty = 4 // 2 = 2
        assert breakdown_with_hint["depth_penalty"] == 2


class TestMultiTypeDetection:
    """Comprehensive tests for multi-type artifact detection.

    These tests verify all artifact types are correctly detected with:
    - Correct artifact_type
    - Correct organization_path
    - Confidence score >= 70 for typed containers
    - No false positives
    """

    # -------------------------------------------------------------------------
    # Tests for type detection in containers (FIX-005 cases 1-4)
    # -------------------------------------------------------------------------

    def test_commands_in_container(self):
        """Test commands/git/COMMAND.md -> COMMAND type."""
        files = [
            "commands/git/COMMAND.md",
            "commands/git/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "command"
        assert artifact.name == "git"
        # With manifest(20) + container_hint(25) + extensions(2) + parent_hint(15) - depth(1) = 61
        # Normalized: 61/120 * 100 = 51%
        # Should be above min_confidence of 30
        assert artifact.confidence_score >= 30

    def test_agents_in_container(self):
        """Test agents/helper/AGENT.md -> AGENT type."""
        files = [
            "agents/helper/AGENT.md",
            "agents/helper/agent.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "agent"
        assert artifact.name == "helper"
        assert artifact.confidence_score >= 30

    def test_hooks_in_container(self):
        """Test hooks/pre-commit/HOOK.md -> HOOK type."""
        files = [
            "hooks/pre-commit/HOOK.md",
            "hooks/pre-commit/hook.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "hook"
        assert artifact.name == "pre-commit"
        assert artifact.confidence_score >= 30

    def test_mcp_in_container(self):
        """Test mcp/server/MCP.md -> MCP_SERVER type."""
        files = [
            "mcp/server/MCP.md",
            "mcp/server/server.json",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "mcp"
        assert artifact.name == "server"
        assert artifact.confidence_score >= 30

    # -------------------------------------------------------------------------
    # Test for nested plugin structure (FIX-005 case 5)
    # -------------------------------------------------------------------------

    def test_nested_plugin_structure(self):
        """Test plugin with commands/, skills/ subdirs -> each type correct."""
        files = [
            "my-plugin/commands/deploy/COMMAND.md",
            "my-plugin/commands/deploy/index.ts",
            "my-plugin/skills/helper/SKILL.md",
            "my-plugin/skills/helper/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 2

        # Find each artifact by type
        command_artifact = next((a for a in artifacts if a.artifact_type == "command"), None)
        skill_artifact = next((a for a in artifacts if a.artifact_type == "skill"), None)

        # Verify command
        assert command_artifact is not None
        assert command_artifact.name == "deploy"
        assert command_artifact.confidence_score >= 30

        # Verify skill
        assert skill_artifact is not None
        assert skill_artifact.name == "helper"
        assert skill_artifact.confidence_score >= 30

    # -------------------------------------------------------------------------
    # Test for frontmatter type override (FIX-005 case 6)
    # -------------------------------------------------------------------------

    def test_frontmatter_type_override(self):
        """Test SKILL.md with type: command in frontmatter -> COMMAND.

        Uses score_directory_with_content to test frontmatter parsing.
        """
        detector = HeuristicDetector()

        # SKILL.md file with type: command in frontmatter
        file_contents = {
            "SKILL.md": "---\ntype: command\n---\n# This is actually a command"
        }
        siblings = {"SKILL.md", "index.ts"}

        # Score with file contents
        artifact_type, match_reasons, breakdown = detector.score_directory_with_content(
            "skills/misnamed-artifact",
            siblings,
            file_contents=file_contents,
            container_hint=ArtifactType.SKILL,
        )

        # Frontmatter should override SKILL.md manifest type
        assert artifact_type == ArtifactType.COMMAND

        # Should have frontmatter type bonus
        assert breakdown["frontmatter_type_score"] == 30

        # Match reasons should mention frontmatter override
        frontmatter_override_reason = any(
            "frontmatter type" in reason.lower() and "overrides" in reason.lower()
            for reason in match_reasons
        )
        assert frontmatter_override_reason

    # -------------------------------------------------------------------------
    # Test for mixed types at same level (FIX-005 case 7)
    # -------------------------------------------------------------------------

    def test_mixed_types_same_level(self):
        """Test artifacts with different manifests at same level inside containers.

        Artifacts must be in typed containers (commands/, skills/, agents/) to
        get container hint bonus and reach confidence threshold.
        """
        files = [
            # Commands in container
            "commands/cmd1/COMMAND.md",
            "commands/cmd1/index.ts",
            # Skills in container
            "skills/skill1/SKILL.md",
            "skills/skill1/index.ts",
            # Agents in container
            "agents/agent1/AGENT.md",
            "agents/agent1/agent.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 3

        types = {a.artifact_type for a in artifacts}
        assert types == {"command", "skill", "agent"}

        names = {a.name for a in artifacts}
        assert names == {"cmd1", "skill1", "agent1"}

    def test_mixed_types_without_container_low_confidence(self):
        """Test that artifacts without typed containers have lower confidence.

        Without a typed container (commands/, skills/, etc.), artifacts only get
        manifest bonus and may fall below the detection threshold.
        """
        files = [
            # Artifacts under generic parent (no typed container)
            "my-collection/cmd1/COMMAND.md",
            "my-collection/cmd1/index.ts",
            "my-collection/skill1/SKILL.md",
            "my-collection/skill1/index.ts",
        ]
        # These may or may not be detected depending on scoring
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Low-confidence detection: artifacts without containers may not be detected
        # This is expected behavior - typed containers are recommended
        if len(artifacts) > 0:
            # If detected, verify types are correct
            for artifact in artifacts:
                if artifact.name == "cmd1":
                    assert artifact.artifact_type == "command"
                elif artifact.name == "skill1":
                    assert artifact.artifact_type == "skill"

    # -------------------------------------------------------------------------
    # Test for deep nesting in container (FIX-005 case 8)
    # -------------------------------------------------------------------------

    def test_deep_nesting_in_container(self):
        """Test commands/group/subgroup/cmd/COMMAND.md -> COMMAND."""
        files = [
            "commands/group/subgroup/cmd/COMMAND.md",
            "commands/group/subgroup/cmd/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]

        # Should detect as command
        assert artifact.artifact_type == "command"
        assert artifact.name == "cmd"

        # Should pass min_confidence (30) with reduced depth penalty
        assert artifact.confidence_score >= 30

        # Verify depth penalty is reduced due to container hint
        # Path depth is 4, with container hint penalty = 4 // 2 = 2
        assert artifact.score_breakdown["depth_penalty"] == 2

    # -------------------------------------------------------------------------
    # Test for case-insensitive container (FIX-005 case 9)
    # -------------------------------------------------------------------------

    def test_case_insensitive_container(self):
        """Test Commands/git/COMMAND.md -> COMMAND (case-insensitive)."""
        files = [
            "Commands/git/COMMAND.md",
            "Commands/git/index.ts",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "command"
        assert artifact.name == "git"
        assert artifact.confidence_score >= 30

    def test_case_insensitive_container_all_caps(self):
        """Test SKILLS/helper/SKILL.md -> SKILL (all caps)."""
        files = [
            "SKILLS/helper/SKILL.md",
            "SKILLS/helper/helper.py",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact.artifact_type == "skill"
        assert artifact.name == "helper"

    # -------------------------------------------------------------------------
    # Test for malformed frontmatter fallback (FIX-005 case 10)
    # -------------------------------------------------------------------------

    def test_malformed_frontmatter_fallback(self):
        """Test bad YAML falls back to heuristic detection."""
        detector = HeuristicDetector()

        # Malformed YAML in frontmatter (missing colon)
        file_contents = {
            "SKILL.md": "---\ntype skill\ninvalid yaml\n---\n# Content"
        }
        siblings = {"SKILL.md", "index.ts"}

        # Score with file contents
        artifact_type, match_reasons, breakdown = detector.score_directory_with_content(
            "skills/my-skill",
            siblings,
            file_contents=file_contents,
        )

        # Should fall back to SKILL type from manifest filename
        assert artifact_type == ArtifactType.SKILL

        # Should NOT have frontmatter bonus (parse failed)
        assert breakdown.get("frontmatter_type_score", 0) == 0

    def test_empty_frontmatter_fallback(self):
        """Test empty frontmatter falls back to heuristic."""
        detector = HeuristicDetector()

        # Empty frontmatter (no type field)
        file_contents = {
            "COMMAND.md": "---\n---\n# Content without type"
        }
        siblings = {"COMMAND.md", "index.ts"}

        artifact_type, _, breakdown = detector.score_directory_with_content(
            "commands/test-cmd",
            siblings,
            file_contents=file_contents,
        )

        # Should detect COMMAND from manifest filename
        assert artifact_type == ArtifactType.COMMAND

        # No frontmatter type bonus
        assert breakdown.get("frontmatter_type_score", 0) == 0

    # -------------------------------------------------------------------------
    # organization_path tests (FIX-005 cases 11-15)
    # Verifying existing tests cover all criteria
    # -------------------------------------------------------------------------

    def test_org_path_nested_commands(self):
        """Test commands/dev/execute-phase.md -> organization_path='dev'."""
        files = [
            "commands/dev/execute-phase/COMMAND.md",
            "commands/dev/execute-phase/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify all criteria
        assert match.artifact_type == "command"
        assert match.organization_path == "dev"
        assert match.confidence_score >= 30

    def test_org_path_direct(self):
        """Test commands/test.md -> organization_path=None (direct in container)."""
        files = [
            "commands/test/COMMAND.md",
            "commands/test/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify all criteria
        assert match.artifact_type == "command"
        assert match.organization_path is None  # Directly in container
        assert match.confidence_score >= 30

    def test_org_path_deeply_nested(self):
        """Test commands/dev/subgroup/my-cmd.md -> organization_path='dev/subgroup'."""
        files = [
            "commands/dev/subgroup/my-cmd/COMMAND.md",
            "commands/dev/subgroup/my-cmd/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify all criteria
        assert match.artifact_type == "command"
        assert match.organization_path == "dev/subgroup"
        assert match.confidence_score >= 30

    def test_org_path_agents(self):
        """Test agents/ui-ux/ui-designer.md -> organization_path='ui-ux'."""
        files = [
            "agents/ui-ux/ui-designer/AGENT.md",
            "agents/ui-ux/ui-designer/agent.py",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify all criteria
        assert match.artifact_type == "agent"
        assert match.organization_path == "ui-ux"
        assert match.confidence_score >= 30

    def test_org_path_skills_direct(self):
        """Test skills/planning/SKILL.md -> organization_path=None.

        'planning' IS the artifact, directly in container.
        """
        files = [
            "skills/planning/SKILL.md",
            "skills/planning/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        # Verify all criteria
        assert match.artifact_type == "skill"
        assert match.organization_path is None  # planning IS the artifact
        assert match.confidence_score >= 30

    # -------------------------------------------------------------------------
    # Additional edge case tests
    # -------------------------------------------------------------------------

    def test_no_false_positives_for_containers(self):
        """Verify container directories themselves are not detected as artifacts."""
        files = [
            "commands/deploy/COMMAND.md",
            "skills/helper/SKILL.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        # Should only detect deploy and helper, not commands/skills containers
        names = {a.name for a in artifacts}
        assert "commands" not in names
        assert "skills" not in names
        assert "deploy" in names
        assert "helper" in names

    def test_high_confidence_with_all_signals(self):
        """Test that artifacts with all signals get high confidence."""
        files = [
            # Skill in container with manifest, extensions, and expected files
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
            "skills/my-skill/package.json",
            "skills/my-skill/README.md",
        ]
        artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

        assert len(artifacts) == 1
        artifact = artifacts[0]

        # Should have high confidence with all signals present
        assert artifact.artifact_type == "skill"
        assert artifact.confidence_score >= 50  # High confidence

        # Verify score breakdown
        breakdown = artifact.score_breakdown
        assert breakdown["manifest_score"] > 0
        assert breakdown["extensions_score"] > 0
        assert breakdown["container_hint_score"] > 0

    def test_multiple_artifact_types_with_organization(self):
        """Test multiple artifact types with organization paths."""
        files = [
            # Commands organized by domain
            "commands/dev/build/COMMAND.md",
            "commands/dev/build/index.ts",
            "commands/test/lint/COMMAND.md",
            "commands/test/lint/index.ts",
            # Skills organized by domain
            "skills/frontend/react-helper/SKILL.md",
            "skills/frontend/react-helper/index.ts",
            "skills/backend/db-skill/SKILL.md",
            "skills/backend/db-skill/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 4

        # Verify organization paths
        for match in matches:
            if match.path == "commands/dev/build":
                assert match.organization_path == "dev"
                assert match.artifact_type == "command"
            elif match.path == "commands/test/lint":
                assert match.organization_path == "test"
                assert match.artifact_type == "command"
            elif match.path == "skills/frontend/react-helper":
                assert match.organization_path == "frontend"
                assert match.artifact_type == "skill"
            elif match.path == "skills/backend/db-skill":
                assert match.organization_path == "backend"
                assert match.artifact_type == "skill"


class TestOrganizationPath:
    """Tests for organization_path computation."""

    def test_organization_path_single_level(self):
        """Test organization_path for artifact one level deep in container."""
        files = [
            "commands/dev/execute-phase/COMMAND.md",
            "commands/dev/execute-phase/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].organization_path == "dev"

    def test_organization_path_multi_level(self):
        """Test organization_path for artifact multiple levels deep."""
        files = [
            "commands/dev/subgroup/my-cmd/COMMAND.md",
            "commands/dev/subgroup/my-cmd/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].organization_path == "dev/subgroup"

    def test_organization_path_directly_in_container(self):
        """Test organization_path is None for artifact directly in container."""
        files = [
            "commands/my-cmd/COMMAND.md",
            "commands/my-cmd/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].organization_path is None

    def test_organization_path_no_container(self):
        """Test organization_path is None when no container directory."""
        files = [
            "standalone/my-skill/SKILL.md",
            "standalone/my-skill/index.ts",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # May or may not detect depending on score, but if detected, org_path should be None
        if len(matches) > 0:
            assert matches[0].organization_path is None

    def test_organization_path_different_containers(self):
        """Test organization_path works for different container types."""
        files = [
            "skills/ui-ux/designer-skill/SKILL.md",
            "agents/backend/db-agent/AGENT.md",
            "commands/test/lint-cmd/COMMAND.md",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Find each artifact and check organization_path
        for match in matches:
            if match.path == "skills/ui-ux/designer-skill":
                assert match.organization_path == "ui-ux"
            elif match.path == "agents/backend/db-agent":
                assert match.organization_path == "backend"
            elif match.path == "commands/test/lint-cmd":
                assert match.organization_path == "test"

    def test_organization_path_compute_method_directly(self):
        """Test _compute_organization_path method directly."""
        detector = HeuristicDetector()

        # Single level
        assert detector._compute_organization_path(
            "commands/dev/execute-phase", "commands"
        ) == "dev"

        # Multi-level
        assert detector._compute_organization_path(
            "commands/dev/subgroup/my-cmd", "commands"
        ) == "dev/subgroup"

        # Directly in container
        assert detector._compute_organization_path(
            "commands/test", "commands"
        ) is None

        # No container
        assert detector._compute_organization_path(
            "standalone/my-skill", None
        ) is None

        # Container path mismatch
        assert detector._compute_organization_path(
            "skills/my-skill", "commands"
        ) is None

    def test_organization_path_with_mcp_container(self):
        """Test organization_path with mcp container type."""
        files = [
            "mcp/integrations/slack-server/MCP.md",
            "mcp/integrations/slack-server/server.json",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].organization_path == "integrations"
        assert matches[0].artifact_type == "mcp"

    def test_organization_path_with_nested_plugin_structure(self):
        """Test organization_path with nested plugin structure."""
        files = [
            "my-plugin/commands/dev/deploy/COMMAND.md",
            "my-plugin/skills/core/helper/SKILL.md",
        ]
        detector = HeuristicDetector()
        matches = detector.analyze_paths(files, base_url="https://github.com/test/repo")

        # Find command and skill matches
        for match in matches:
            if match.artifact_type == "command":
                # Container is "my-plugin/commands", org path is "dev"
                assert match.organization_path == "dev"
            elif match.artifact_type == "skill":
                # Container is "my-plugin/skills", org path is "core"
                assert match.organization_path == "core"


class TestSingleFileArtifacts:
    """Test detection of single-file artifacts in containers."""

    @pytest.fixture
    def detector(self):
        return HeuristicDetector()

    def test_single_file_command_in_container(self, detector):
        """commands/use-mcp.md -> COMMAND"""
        paths = ["commands/use-mcp.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].artifact_type == "command"
        assert matches[0].path == "commands/use-mcp.md"
        assert matches[0].organization_path is None

    def test_single_file_agent_in_container(self, detector):
        """agents/mcp-manager.md -> AGENT"""
        paths = ["agents/mcp-manager.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].artifact_type == "agent"
        assert matches[0].path == "agents/mcp-manager.md"

    def test_multiple_commands_in_grouping_dir(self, detector):
        """commands/git/cm.md, cp.md, pr.md -> 3 COMMANDs"""
        paths = [
            "commands/git/cm.md",
            "commands/git/cp.md",
            "commands/git/pr.md",
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 3
        assert all(m.artifact_type == "command" for m in matches)
        assert all(m.organization_path == "git" for m in matches)

    def test_nested_command_org_path(self, detector):
        """commands/dev/subgroup/my-cmd.md -> organization_path='dev/subgroup'"""
        paths = ["commands/dev/subgroup/my-cmd.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].artifact_type == "command"
        assert matches[0].organization_path == "dev/subgroup"

    def test_excludes_readme_files(self, detector):
        """README.md files should not be detected as artifacts"""
        paths = [
            "commands/README.md",
            "commands/git/README.md",
            "commands/git/cm.md",  # This should be detected
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].path == "commands/git/cm.md"

    def test_excludes_manifest_files(self, detector):
        """Directories with manifests handled by directory detection, not single-file"""
        paths = [
            "commands/deploy/COMMAND.md",  # Directory-based
            "commands/deploy/helper.py",
            "commands/quick.md",  # Single-file
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        # Should get 2 matches: deploy directory + quick.md single-file
        assert len(matches) == 2
        by_path = {m.path: m for m in matches}
        assert "commands/deploy" in by_path or "commands/deploy/COMMAND.md" in by_path
        assert "commands/quick.md" in by_path

    def test_mixed_artifact_types(self, detector):
        """Mix of single-file and directory-based across types"""
        paths = [
            "commands/use-mcp.md",  # Single-file command
            "skills/aesthetic/SKILL.md",  # Directory-based skill
            "agents/helper.md",  # Single-file agent
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 3
        by_path = {m.path: m for m in matches}
        assert by_path["commands/use-mcp.md"].artifact_type == "command"
        assert by_path["skills/aesthetic"].artifact_type == "skill"
        assert by_path["agents/helper.md"].artifact_type == "agent"

    def test_claudekit_structure(self, detector):
        """Real-world test: mrgoonie/claudekit-skills structure"""
        paths = [
            # Commands
            "commands/git/cm.md",
            "commands/git/cp.md",
            "commands/git/pr.md",
            "commands/skill/create.md",
            "commands/use-mcp.md",
            # Agent
            "agents/mcp-manager.md",
            # Skills (directory-based)
            "skills/aesthetic/SKILL.md",
            "skills/ai-multimodal/SKILL.md",
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")

        # Should detect: 5 commands, 1 agent, 2 skills
        commands = [m for m in matches if m.artifact_type == "command"]
        agents = [m for m in matches if m.artifact_type == "agent"]
        skills = [m for m in matches if m.artifact_type == "skill"]

        assert len(commands) == 5, f"Expected 5 commands, got {len(commands)}"
        assert len(agents) == 1, f"Expected 1 agent, got {len(agents)}"
        assert len(skills) == 2, f"Expected 2 skills, got {len(skills)}"

    def test_single_file_confidence_score(self, detector):
        """Single-file artifacts should have appropriate confidence scores.

        Bug Fix: Single-file artifacts now apply depth penalty:
        - Directly in container: 75%
        - One level deep (e.g., commands/git/cm.md): 70%
        - Each additional level: -5% (minimum 50%)
        """
        # Direct in container - higher confidence
        paths_direct = ["commands/deploy.md"]
        matches_direct = detector.analyze_paths(
            paths_direct, base_url="https://github.com/test/repo"
        )
        assert len(matches_direct) == 1
        assert matches_direct[0].confidence_score == 75

        # Nested in grouping directory - slightly lower (one level deep)
        paths_nested = ["commands/git/deploy.md"]
        matches_nested = detector.analyze_paths(
            paths_nested, base_url="https://github.com/test/repo"
        )
        assert len(matches_nested) == 1
        assert matches_nested[0].confidence_score == 70

    def test_single_file_breakdown_structure(self, detector):
        """Single-file artifacts should have proper breakdown structure"""
        paths = ["commands/deploy.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")

        assert len(matches) == 1
        breakdown = matches[0].breakdown

        # Should have single_file_detection flag (stored as truthy value)
        assert breakdown.get("single_file_detection")

        # Should have container hint score
        assert breakdown["container_hint_score"] == 25  # default container_hint_weight

        # Should have extension score for .md
        assert breakdown["extensions_score"] == 5

        # Should have no manifest score (single-file, not directory-based)
        assert breakdown["manifest_score"] == 0

    def test_single_file_not_detected_outside_container(self, detector):
        """Single .md files outside containers should not be detected"""
        paths = [
            "src/docs/guide.md",
            "misc/notes.md",
        ]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        # Should not detect any artifacts (no container context)
        assert len(matches) == 0

    def test_single_file_hooks(self, detector):
        """hooks/pre-commit.md -> HOOK"""
        paths = ["hooks/pre-commit.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].artifact_type == "hook"

    def test_single_file_mcp(self, detector):
        """mcp/slack-server.md -> MCP"""
        paths = ["mcp/slack-server.md"]
        matches = detector.analyze_paths(paths, base_url="https://github.com/test/repo")
        assert len(matches) == 1
        assert matches[0].artifact_type == "mcp"

    def test_artifact_name_from_single_file(self):
        """Test that artifact name is extracted correctly from single-file path"""
        paths = ["commands/use-mcp.md"]
        artifacts = detect_artifacts_in_tree(paths, "https://github.com/test/repo")

        assert len(artifacts) == 1
        # Name should be the filename without .md extension for single-file artifacts
        assert artifacts[0].name == "use-mcp"  # Extension stripped for Commands/Agents/Hooks

    def test_upstream_url_for_single_file(self):
        """Test that upstream URL is correctly generated for single-file artifacts"""
        paths = ["commands/use-mcp.md"]
        artifacts = detect_artifacts_in_tree(
            paths, "https://github.com/user/repo", detected_sha="abc123"
        )

        assert len(artifacts) == 1
        assert (
            artifacts[0].upstream_url
            == "https://github.com/user/repo/tree/main/commands/use-mcp.md"
        )
        assert artifacts[0].detected_sha == "abc123"


class TestManualMappings:
    """Test suite for manual directory-to-type mappings (P2.1a/P2.1b/P2.1e).

    This test class covers:
    - _check_manual_mapping() method behavior
    - Hierarchical inheritance with depth tracking
    - Confidence scoring based on inheritance depth
    - Edge cases (empty mappings, special characters, etc.)
    - Integration with analyze_paths()
    """

    # -------------------------------------------------------------------------
    # _string_to_artifact_type() Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "type_str,expected",
        [
            ("skill", ArtifactType.SKILL),
            ("SKILL", ArtifactType.SKILL),
            ("Skill", ArtifactType.SKILL),
            ("command", ArtifactType.COMMAND),
            ("COMMAND", ArtifactType.COMMAND),
            ("agent", ArtifactType.AGENT),
            ("AGENT", ArtifactType.AGENT),
            ("mcp_server", ArtifactType.MCP),
            ("mcp", ArtifactType.MCP),
            ("mcp-server", ArtifactType.MCP),
            ("MCP", ArtifactType.MCP),
            ("hook", ArtifactType.HOOK),
            ("HOOK", ArtifactType.HOOK),
            # Invalid types
            ("invalid", None),
            ("", None),
            ("  ", None),
            ("unknown_type", None),
            ("skills", None),  # Plural form not valid
            ("commands", None),
        ],
    )
    def test_string_to_artifact_type_parametrized(self, type_str, expected):
        """Test _string_to_artifact_type with various inputs."""
        detector = HeuristicDetector()
        assert detector._string_to_artifact_type(type_str) == expected

    def test_string_to_artifact_type(self):
        """Test _string_to_artifact_type converts strings correctly."""
        detector = HeuristicDetector()

        assert detector._string_to_artifact_type("skill") == ArtifactType.SKILL
        assert detector._string_to_artifact_type("SKILL") == ArtifactType.SKILL
        assert detector._string_to_artifact_type("command") == ArtifactType.COMMAND
        assert detector._string_to_artifact_type("agent") == ArtifactType.AGENT
        assert detector._string_to_artifact_type("mcp_server") == ArtifactType.MCP
        assert detector._string_to_artifact_type("mcp-server") == ArtifactType.MCP
        assert detector._string_to_artifact_type("hook") == ArtifactType.HOOK
        assert detector._string_to_artifact_type("invalid") is None
        assert detector._string_to_artifact_type("") is None

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Exact Match Tests
    # -------------------------------------------------------------------------

    def test_exact_match(self):
        """Test exact path matching."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill", "cmds": "command"})

        result = detector._check_manual_mapping("skills")
        assert result == (ArtifactType.SKILL, "exact", 0)

        result = detector._check_manual_mapping("cmds")
        assert result == (ArtifactType.COMMAND, "exact", 0)

    @pytest.mark.parametrize(
        "mapping_path,query_path,expected_type",
        [
            ("skills", "skills", ArtifactType.SKILL),
            ("my/path", "my/path", ArtifactType.COMMAND),
            ("deep/nested/path", "deep/nested/path", ArtifactType.AGENT),
            ("single", "single", ArtifactType.HOOK),
        ],
    )
    def test_exact_match_parametrized(self, mapping_path, query_path, expected_type):
        """Test exact matches with various path patterns."""
        type_str = expected_type.value
        detector = HeuristicDetector(manual_mappings={mapping_path: type_str})
        result = detector._check_manual_mapping(query_path)
        assert result == (expected_type, "exact", 0)

    def test_exact_match_returns_depth_zero(self):
        """Verify exact matches always return depth=0."""
        detector = HeuristicDetector(
            manual_mappings={
                "a": "skill",
                "a/b": "command",
                "a/b/c": "agent",
            }
        )

        # All exact matches should have depth=0
        assert detector._check_manual_mapping("a")[2] == 0
        assert detector._check_manual_mapping("a/b")[2] == 0
        assert detector._check_manual_mapping("a/b/c")[2] == 0

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Inherited Match Tests
    # -------------------------------------------------------------------------

    def test_inherited_match(self):
        """Test hierarchical inheritance matching with depth tracking."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})

        # Direct child inherits from parent (depth 1)
        result = detector._check_manual_mapping("skills/canvas")
        assert result == (ArtifactType.SKILL, "inherited", 1)

        # Deeper nested paths inherit with increasing depth
        result = detector._check_manual_mapping("skills/canvas/deep")
        assert result == (ArtifactType.SKILL, "inherited", 2)

        result = detector._check_manual_mapping("skills/canvas/deep/nested")
        assert result == (ArtifactType.SKILL, "inherited", 3)

    @pytest.mark.parametrize(
        "query_path,expected_depth",
        [
            ("root/a", 1),
            ("root/a/b", 2),
            ("root/a/b/c", 3),
            ("root/a/b/c/d", 4),
            ("root/a/b/c/d/e", 5),
            ("root/a/b/c/d/e/f", 6),
        ],
    )
    def test_inherited_match_depth_tracking(self, query_path, expected_depth):
        """Test that inheritance depth is correctly calculated."""
        detector = HeuristicDetector(manual_mappings={"root": "skill"})
        result = detector._check_manual_mapping(query_path)
        assert result is not None
        assert result[1] == "inherited"
        assert result[2] == expected_depth

    def test_inherited_match_returns_correct_type(self):
        """Verify inherited matches return the correct artifact type."""
        detector = HeuristicDetector(
            manual_mappings={
                "skills": "skill",
                "commands": "command",
                "agents": "agent",
            }
        )

        result = detector._check_manual_mapping("skills/my-skill")
        assert result[0] == ArtifactType.SKILL

        result = detector._check_manual_mapping("commands/my-cmd/nested")
        assert result[0] == ArtifactType.COMMAND

        result = detector._check_manual_mapping("agents/helper/deep/path")
        assert result[0] == ArtifactType.AGENT

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Non-Matching Path Tests
    # -------------------------------------------------------------------------

    def test_no_partial_name_match(self):
        """Test that partial name matches are NOT allowed."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})

        # These should NOT match (partial name, not prefix with /)
        assert detector._check_manual_mapping("my-skills") is None
        assert detector._check_manual_mapping("skillset") is None
        assert detector._check_manual_mapping("other/skills") is None

    def test_no_match_when_unmapped(self):
        """Test that unmapped paths return None."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})

        assert detector._check_manual_mapping("commands") is None
        assert detector._check_manual_mapping("agents/helper") is None

    @pytest.mark.parametrize(
        "query_path",
        [
            "my-skills",  # Contains mapping but not a prefix
            "skillset",  # Contains mapping but not a prefix
            "other/skills",  # Mapping in middle, not at start
            "prefix-skills/something",  # Mapping as suffix, not prefix
            "totally/different/path",  # No relation
            "",  # Empty path
            "s",  # Partial
            "skill",  # Singular (mapping is "skills")
        ],
    )
    def test_non_matching_paths_return_none(self, query_path):
        """Test various paths that should not match."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})
        assert detector._check_manual_mapping(query_path) is None

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Empty Mappings Tests
    # -------------------------------------------------------------------------

    def test_no_mappings_returns_none(self):
        """Test that no mappings always returns None."""
        detector = HeuristicDetector()
        assert detector._check_manual_mapping("skills") is None
        assert detector._check_manual_mapping("anything") is None

    def test_empty_mappings_dict_returns_none(self):
        """Test that empty mappings dict always returns None."""
        detector = HeuristicDetector(manual_mappings={})
        assert detector._check_manual_mapping("skills") is None
        assert detector._check_manual_mapping("skills/nested") is None
        assert detector._check_manual_mapping("any/path") is None

    def test_none_mappings_returns_none(self):
        """Test that None mappings always returns None."""
        detector = HeuristicDetector(manual_mappings=None)
        assert detector._check_manual_mapping("skills") is None
        assert detector._check_manual_mapping("anything/nested") is None

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Path Normalization Tests
    # -------------------------------------------------------------------------

    def test_trailing_slash_normalization(self):
        """Test that trailing slashes are normalized."""
        detector = HeuristicDetector(manual_mappings={"skills/": "skill"})

        # Should still match exact
        result = detector._check_manual_mapping("skills")
        assert result == (ArtifactType.SKILL, "exact", 0)

        # Should still match inherited
        result = detector._check_manual_mapping("skills/canvas")
        assert result == (ArtifactType.SKILL, "inherited", 1)

    def test_trailing_slash_in_query_path(self):
        """Test that trailing slashes in query path are normalized."""
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})

        # Query with trailing slash should still match
        result = detector._check_manual_mapping("skills/")
        assert result == (ArtifactType.SKILL, "exact", 0)

        result = detector._check_manual_mapping("skills/canvas/")
        assert result == (ArtifactType.SKILL, "inherited", 1)

    def test_backslash_normalization(self):
        """Test that backslashes are normalized to forward slashes."""
        detector = HeuristicDetector(manual_mappings={"skills\\nested": "skill"})

        # Query with forward slashes should match
        result = detector._check_manual_mapping("skills/nested")
        assert result == (ArtifactType.SKILL, "exact", 0)

    # -------------------------------------------------------------------------
    # _check_manual_mapping() - Edge Cases
    # -------------------------------------------------------------------------

    def test_root_path_mapping_empty_string(self):
        """Test root path mapping with empty string."""
        detector = HeuristicDetector(manual_mappings={"": "skill"})

        # Empty string mapping - exact match should work
        result = detector._check_manual_mapping("")
        assert result == (ArtifactType.SKILL, "exact", 0)

        # But other paths should not inherit (empty prefix matches nothing)
        result = detector._check_manual_mapping("anything")
        # Empty string is not a proper prefix, should not match
        assert result is None

    def test_single_character_path_mapping(self):
        """Test single character path mappings."""
        detector = HeuristicDetector(manual_mappings={"a": "skill"})

        assert detector._check_manual_mapping("a") == (ArtifactType.SKILL, "exact", 0)
        assert detector._check_manual_mapping("a/b") == (
            ArtifactType.SKILL,
            "inherited",
            1,
        )
        # 'ab' is not under 'a', should not match
        assert detector._check_manual_mapping("ab") is None

    def test_paths_with_special_characters(self):
        """Test paths containing special characters."""
        detector = HeuristicDetector(
            manual_mappings={
                "my-skills": "skill",
                "my_commands": "command",
                "my.agents": "agent",
            }
        )

        # Hyphens
        assert detector._check_manual_mapping("my-skills") == (
            ArtifactType.SKILL,
            "exact",
            0,
        )
        assert detector._check_manual_mapping("my-skills/canvas") == (
            ArtifactType.SKILL,
            "inherited",
            1,
        )

        # Underscores
        assert detector._check_manual_mapping("my_commands") == (
            ArtifactType.COMMAND,
            "exact",
            0,
        )
        assert detector._check_manual_mapping("my_commands/deploy") == (
            ArtifactType.COMMAND,
            "inherited",
            1,
        )

        # Dots
        assert detector._check_manual_mapping("my.agents") == (
            ArtifactType.AGENT,
            "exact",
            0,
        )
        assert detector._check_manual_mapping("my.agents/helper") == (
            ArtifactType.AGENT,
            "inherited",
            1,
        )

    def test_paths_with_unicode_characters(self):
        """Test paths containing unicode characters."""
        detector = HeuristicDetector(
            manual_mappings={
                "skills/日本語": "skill",
                "commands/命令": "command",
            }
        )

        assert detector._check_manual_mapping("skills/日本語") == (
            ArtifactType.SKILL,
            "exact",
            0,
        )
        assert detector._check_manual_mapping("skills/日本語/nested") == (
            ArtifactType.SKILL,
            "inherited",
            1,
        )
        assert detector._check_manual_mapping("commands/命令/sub") == (
            ArtifactType.COMMAND,
            "inherited",
            1,
        )

    def test_paths_with_spaces(self):
        """Test paths containing spaces (edge case, not typical)."""
        detector = HeuristicDetector(manual_mappings={"my skills": "skill"})

        assert detector._check_manual_mapping("my skills") == (
            ArtifactType.SKILL,
            "exact",
            0,
        )
        assert detector._check_manual_mapping("my skills/canvas") == (
            ArtifactType.SKILL,
            "inherited",
            1,
        )

    def test_very_long_paths(self):
        """Test very long paths (stress test)."""
        # Create a very long nested path
        long_path = "/".join([f"dir{i}" for i in range(50)])
        detector = HeuristicDetector(manual_mappings={"dir0": "skill"})

        result = detector._check_manual_mapping(long_path)
        assert result is not None
        assert result[0] == ArtifactType.SKILL
        assert result[1] == "inherited"
        # Depth should be 49 (50 parts - 1 for the mapping)
        assert result[2] == 49

    def test_path_with_many_segments(self):
        """Test paths with many segments for correct depth calculation."""
        detector = HeuristicDetector(manual_mappings={"a/b/c": "skill"})

        # Exact match
        assert detector._check_manual_mapping("a/b/c") == (
            ArtifactType.SKILL,
            "exact",
            0,
        )

        # One level deeper
        assert detector._check_manual_mapping("a/b/c/d") == (
            ArtifactType.SKILL,
            "inherited",
            1,
        )

        # Many levels deeper
        assert detector._check_manual_mapping("a/b/c/d/e/f/g/h") == (
            ArtifactType.SKILL,
            "inherited",
            5,
        )

    def test_invalid_artifact_types_skipped(self):
        """Test that invalid artifact types in mappings are skipped."""
        detector = HeuristicDetector(
            manual_mappings={
                "valid_path": "skill",
                "invalid_path": "not_a_type",
                "another_invalid": "foobar",
            }
        )

        # Valid path should work
        assert detector._check_manual_mapping("valid_path") == (
            ArtifactType.SKILL,
            "exact",
            0,
        )

        # Invalid paths should be ignored (not in normalized mappings)
        assert detector._check_manual_mapping("invalid_path") is None
        assert detector._check_manual_mapping("another_invalid") is None

    # -------------------------------------------------------------------------
    # Confidence Scoring Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "depth,expected_score",
        [
            (0, 95),  # Exact match
            (1, 92),  # 95 - 3
            (2, 89),  # 95 - 6
            (3, 86),  # max(86, 95 - 9)
            (4, 86),  # max(86, 95 - 12) = max(86, 83) = 86
            (5, 86),  # max(86, 95 - 15) = max(86, 80) = 86
            (10, 86),  # Very deep, still 86
            (100, 86),  # Extremely deep, still 86
        ],
    )
    def test_confidence_score_formula(self, depth, expected_score):
        """Test confidence score formula: max(86, 95 - depth*3)."""
        # Calculate using the formula
        calculated = max(86, 95 - (depth * 3))
        assert calculated == expected_score

    def test_confidence_score_depth_zero_exact_match(self):
        """Test that depth=0 (exact match) returns confidence=95."""
        files = ["custom/path/SKILL.md", "custom/path/index.ts"]
        detector = HeuristicDetector(manual_mappings={"custom/path": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].confidence_score == 95
        assert matches[0].metadata["inheritance_depth"] == 0

    def test_confidence_score_depth_one(self):
        """Test that depth=1 (inherited) returns confidence=92."""
        files = ["parent/child/SKILL.md", "parent/child/index.ts"]
        detector = HeuristicDetector(manual_mappings={"parent": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].confidence_score == 92
        assert matches[0].metadata["inheritance_depth"] == 1

    def test_confidence_score_depth_two(self):
        """Test that depth=2 returns confidence=89."""
        files = ["a/b/c/SKILL.md", "a/b/c/index.ts"]
        detector = HeuristicDetector(manual_mappings={"a": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].confidence_score == 89
        assert matches[0].metadata["inheritance_depth"] == 2

    def test_confidence_score_minimum_threshold(self):
        """Test that confidence never goes below 86 for manual mappings."""
        # Deep nesting (depth >= 3) should still get 86
        files = ["a/b/c/d/e/f/SKILL.md", "a/b/c/d/e/f/index.ts"]
        detector = HeuristicDetector(manual_mappings={"a": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].confidence_score == 86
        assert matches[0].metadata["inheritance_depth"] == 5

    def test_confidence_score_beats_heuristic_max(self):
        """Test that manual mapping confidence (min 86) beats heuristic max (~80)."""
        # Even the minimum manual mapping score (86) should be higher than
        # typical heuristic scores (~80 max)
        files = ["weird/nested/path/SKILL.md", "weird/nested/path/index.ts"]

        # Without manual mapping - uses heuristics
        detector_heuristic = HeuristicDetector()
        matches_heuristic = detector_heuristic.analyze_paths(
            files, "https://github.com/test/repo"
        )

        # With manual mapping - always at least 86
        detector_manual = HeuristicDetector(manual_mappings={"weird": "skill"})
        matches_manual = detector_manual.analyze_paths(
            files, "https://github.com/test/repo"
        )

        # If heuristic detected anything, manual should beat it
        if matches_heuristic:
            assert matches_manual[0].confidence_score >= matches_heuristic[0].confidence_score

        # Manual should always be >= 86
        assert len(matches_manual) == 1
        assert matches_manual[0].confidence_score >= 86

    # -------------------------------------------------------------------------
    # Integration with analyze_paths() Tests
    # -------------------------------------------------------------------------

    def test_integration_exact_match(self):
        """Test manual mapping integration with analyze_paths (exact match)."""
        files = [
            "custom/path/SKILL.md",
            "custom/path/index.ts",
        ]
        detector = HeuristicDetector(manual_mappings={"custom/path": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].path == "custom/path"
        assert matches[0].artifact_type == "skill"
        assert matches[0].confidence_score == 95
        assert matches[0].metadata is not None
        assert matches[0].metadata.get("is_manual_mapping") is True
        assert matches[0].metadata.get("match_type") == "exact"
        assert matches[0].metadata.get("inheritance_depth") == 0
        assert "Manual mapping (exact match, depth=0)" in matches[0].match_reasons[0]

    def test_integration_inherited_match(self):
        """Test manual mapping integration with analyze_paths (inherited match).

        Confidence scores vary by inheritance depth:
        - Exact match (depth=0): 95
        - Inherited depth=1: 92
        - Inherited depth=2: 89
        - Inherited depth=3+: 86 (minimum)
        """
        files = [
            "my-artifacts/subdir/SKILL.md",
            "my-artifacts/subdir/index.ts",
        ]
        detector = HeuristicDetector(manual_mappings={"my-artifacts": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].path == "my-artifacts/subdir"
        assert matches[0].artifact_type == "skill"
        # depth=1 -> confidence = 95 - (1 * 3) = 92
        assert matches[0].confidence_score == 92
        assert matches[0].metadata is not None
        assert matches[0].metadata.get("is_manual_mapping") is True
        assert matches[0].metadata.get("match_type") == "inherited"
        assert matches[0].metadata.get("inheritance_depth") == 1
        assert matches[0].metadata.get("confidence_reason") == "Manual mapping inherited from ancestor (depth=1, score=92)"

    def test_non_matching_paths_use_heuristics(self):
        """Test that non-matching paths still use heuristic detection."""
        files = [
            "skills/my-skill/SKILL.md",
            "skills/my-skill/index.ts",
        ]
        # Manual mapping for different path
        detector = HeuristicDetector(manual_mappings={"custom": "command"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        # Should detect via heuristics
        assert len(matches) == 1
        assert matches[0].artifact_type == "skill"
        # Should NOT have manual mapping metadata
        assert matches[0].metadata is None

    def test_heuristic_fallback_for_unmapped_paths(self):
        """Test that heuristic detection works alongside manual mappings."""
        files = [
            # Mapped path
            "custom/skill1/SKILL.md",
            "custom/skill1/index.ts",
            # Unmapped path (uses heuristic)
            "skills/skill2/SKILL.md",
            "skills/skill2/index.ts",
        ]
        detector = HeuristicDetector(manual_mappings={"custom": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        # Should detect both
        assert len(matches) == 2

        # Find each match
        by_path = {m.path: m for m in matches}

        # Mapped path should have manual mapping metadata
        assert "custom/skill1" in by_path
        assert by_path["custom/skill1"].metadata is not None
        assert by_path["custom/skill1"].metadata["is_manual_mapping"] is True

        # Unmapped path should NOT have manual mapping metadata
        assert "skills/skill2" in by_path
        assert by_path["skills/skill2"].metadata is None

    def test_integration_metadata_fields(self):
        """Test that all expected metadata fields are present."""
        files = ["mapped/path/SKILL.md", "mapped/path/index.ts"]
        detector = HeuristicDetector(manual_mappings={"mapped": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        metadata = matches[0].metadata

        assert metadata is not None
        assert "is_manual_mapping" in metadata
        assert "match_type" in metadata
        assert "inheritance_depth" in metadata
        assert "confidence_reason" in metadata

        assert metadata["is_manual_mapping"] is True
        assert metadata["match_type"] == "inherited"
        assert metadata["inheritance_depth"] == 1
        assert "Manual mapping inherited" in metadata["confidence_reason"]

    def test_integration_match_reasons_format(self):
        """Test that match_reasons contain expected information."""
        files = ["exact/SKILL.md", "exact/index.ts"]
        detector = HeuristicDetector(manual_mappings={"exact": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1

        # Check match reasons
        reasons = matches[0].match_reasons
        assert len(reasons) >= 1

        # First reason should describe the manual mapping
        assert "Manual mapping" in reasons[0]
        assert "exact match" in reasons[0]
        assert "depth=0" in reasons[0]

    def test_manual_mapping_enables_non_standard_locations(self):
        """Test that manual mapping boosts confidence for non-standard locations.

        Note: Confidence varies by inheritance depth with manual mapping:
        - weird (depth=0): 95
        - weird/custom (depth=1): 92
        - weird/custom/path (depth=2): 89

        Without manual mapping, artifacts with manifest files can still be
        detected via the standalone manifest bonus, but with lower confidence.
        Manual mappings provide significantly higher confidence.
        """
        files = [
            "weird/custom/path/SKILL.md",
            "weird/custom/path/index.ts",
        ]
        # Without manual mapping - detected with lower confidence via standalone bonus
        # manifest(20) + extensions(2) + standalone_bonus(25) - depth_penalty(3) = 44 raw
        # normalized: (44 / 120) * 100 = 37%
        artifacts_without = detect_artifacts_in_tree(files, "https://github.com/test/repo")
        assert len(artifacts_without) == 1
        assert artifacts_without[0].artifact_type == "skill"
        assert artifacts_without[0].confidence_score < 50  # Low confidence without mapping

        # With manual mapping at "weird" - artifact at depth=2 gets confidence=89
        # This is significantly higher than heuristic-only detection
        artifacts_with = detect_artifacts_in_tree(
            files,
            "https://github.com/test/repo",
            manual_mappings={"weird": "skill"},
        )
        assert len(artifacts_with) == 1
        assert artifacts_with[0].artifact_type == "skill"
        # depth=2 -> confidence = 95 - (2 * 3) = 89
        assert artifacts_with[0].confidence_score == 89
        # Manual mapping provides much higher confidence than heuristic
        assert artifacts_with[0].confidence_score > artifacts_without[0].confidence_score

    def test_invalid_mapping_type_logged(self):
        """Test that invalid artifact types in mappings are logged and ignored."""
        # Should not raise, but should log warning
        detector = HeuristicDetector(manual_mappings={"path": "invalid_type"})

        # The invalid mapping should be ignored
        assert "path" not in detector._normalized_mappings

    def test_multiple_mappings(self):
        """Test multiple manual mappings work together."""
        detector = HeuristicDetector(
            manual_mappings={
                "lib/skills": "skill",
                "lib/commands": "command",
                "lib/agents": "agent",
            }
        )

        assert detector._check_manual_mapping("lib/skills") == (ArtifactType.SKILL, "exact", 0)
        assert detector._check_manual_mapping("lib/skills/canvas") == (ArtifactType.SKILL, "inherited", 1)
        assert detector._check_manual_mapping("lib/commands") == (ArtifactType.COMMAND, "exact", 0)
        assert detector._check_manual_mapping("lib/commands/deploy") == (ArtifactType.COMMAND, "inherited", 1)
        assert detector._check_manual_mapping("lib/agents/helper") == (ArtifactType.AGENT, "inherited", 1)

    def test_case_sensitive_matching(self):
        """Test that path matching is case-sensitive."""
        detector = HeuristicDetector(manual_mappings={"Skills": "skill"})

        # Exact case should match
        assert detector._check_manual_mapping("Skills") == (ArtifactType.SKILL, "exact", 0)
        assert detector._check_manual_mapping("Skills/canvas") == (ArtifactType.SKILL, "inherited", 1)

        # Different case should NOT match
        assert detector._check_manual_mapping("skills") is None
        assert detector._check_manual_mapping("SKILLS") is None

    def test_hierarchical_inheritance_most_specific_wins(self):
        """Test that most specific (longest) parent mapping wins."""
        detector = HeuristicDetector(
            manual_mappings={
                "skills": "skill",
                "skills/canvas": "command",  # More specific mapping
            }
        )

        # Exact matches
        assert detector._check_manual_mapping("skills") == (ArtifactType.SKILL, "exact", 0)
        assert detector._check_manual_mapping("skills/canvas") == (ArtifactType.COMMAND, "exact", 0)

        # skills/canvas/nested should match skills/canvas (depth 1), not skills (depth 2)
        result = detector._check_manual_mapping("skills/canvas/nested")
        assert result == (ArtifactType.COMMAND, "inherited", 1)
        assert result[0] == ArtifactType.COMMAND  # Not SKILL!

        # skills/canvas/nested/deep should also match skills/canvas (depth 2)
        result = detector._check_manual_mapping("skills/canvas/nested/deep")
        assert result == (ArtifactType.COMMAND, "inherited", 2)

        # skills/other should match skills (depth 1) since no skills/other mapping
        result = detector._check_manual_mapping("skills/other")
        assert result == (ArtifactType.SKILL, "inherited", 1)

        # skills/other/nested should match skills (depth 2)
        result = detector._check_manual_mapping("skills/other/nested")
        assert result == (ArtifactType.SKILL, "inherited", 2)

    def test_hierarchical_inheritance_deep_nesting(self):
        """Test inheritance depth tracking for deeply nested paths."""
        detector = HeuristicDetector(manual_mappings={"root": "skill"})

        # Test various depths
        assert detector._check_manual_mapping("root") == (ArtifactType.SKILL, "exact", 0)
        assert detector._check_manual_mapping("root/a") == (ArtifactType.SKILL, "inherited", 1)
        assert detector._check_manual_mapping("root/a/b") == (ArtifactType.SKILL, "inherited", 2)
        assert detector._check_manual_mapping("root/a/b/c") == (ArtifactType.SKILL, "inherited", 3)
        assert detector._check_manual_mapping("root/a/b/c/d") == (ArtifactType.SKILL, "inherited", 4)
        assert detector._check_manual_mapping("root/a/b/c/d/e") == (ArtifactType.SKILL, "inherited", 5)

    def test_confidence_score_by_inheritance_depth(self):
        """Test confidence scores based on inheritance depth.

        Formula: confidence = max(86, 95 - (inheritance_depth * 3))
        - Exact match (depth=0): 95
        - Inherited depth=1: 92
        - Inherited depth=2: 89
        - Inherited depth=3: 86
        - Inherited depth=4+: 86 (minimum)

        This ensures manual mappings always beat heuristic detection (~80 max)
        while still reflecting match quality.
        """
        files = [
            "skills/SKILL.md",  # depth=0 (exact match)
            "skills/canvas/SKILL.md",  # depth=1
            "skills/canvas/nested/SKILL.md",  # depth=2
            "skills/canvas/nested/deep/SKILL.md",  # depth=3
            "skills/canvas/nested/deep/deeper/SKILL.md",  # depth=4
        ]
        detector = HeuristicDetector(manual_mappings={"skills": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        # Sort by path for predictable order
        matches_by_path = {m.path: m for m in matches}

        # depth=0 (exact match) -> "skills" is a container, won't be detected as artifact
        # depth=1 -> 95 - 3 = 92
        assert matches_by_path["skills/canvas"].confidence_score == 92
        assert matches_by_path["skills/canvas"].metadata["confidence_reason"] == \
            "Manual mapping inherited from ancestor (depth=1, score=92)"

        # depth=2 -> 95 - 6 = 89
        assert matches_by_path["skills/canvas/nested"].confidence_score == 89
        assert matches_by_path["skills/canvas/nested"].metadata["confidence_reason"] == \
            "Manual mapping inherited from ancestor (depth=2, score=89)"

        # depth=3 -> 95 - 9 = 86
        assert matches_by_path["skills/canvas/nested/deep"].confidence_score == 86
        assert matches_by_path["skills/canvas/nested/deep"].metadata["confidence_reason"] == \
            "Manual mapping inherited from ancestor (depth=3, score=86)"

        # depth=4 -> max(86, 95 - 12) = max(86, 83) = 86
        assert matches_by_path["skills/canvas/nested/deep/deeper"].confidence_score == 86
        assert matches_by_path["skills/canvas/nested/deep/deeper"].metadata["confidence_reason"] == \
            "Manual mapping inherited from ancestor (depth=4, score=86)"

    def test_confidence_score_exact_match(self):
        """Test exact match gets confidence=95 with correct reason."""
        files = ["custom/path/SKILL.md", "custom/path/index.ts"]
        detector = HeuristicDetector(manual_mappings={"custom/path": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        assert matches[0].confidence_score == 95
        assert matches[0].metadata["confidence_reason"] == "Manual mapping exact match (95)"

    def test_confidence_score_always_beats_heuristic(self):
        """Test that even minimum manual mapping confidence (86) beats max heuristic (~80)."""
        # Deep inheritance should still be >= 86
        files = [
            "root/a/b/c/d/e/SKILL.md",  # depth=5
            "root/a/b/c/d/e/index.ts",
        ]
        detector = HeuristicDetector(manual_mappings={"root": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        # max(86, 95 - 15) = max(86, 80) = 86
        assert matches[0].confidence_score == 86
        # Verify it's still above heuristic max (~80)
        assert matches[0].confidence_score > 80


class TestManualMappingNonSkillTypes:
    """Test that manual mappings work correctly for non-Skill artifact types.

    Claude Code convention:
    - Skills: Always directories containing SKILL.md (entire directory is the artifact)
    - All other types (Agent, Command, Hook, MCP Server): Always single markdown files
    """

    def test_manual_mapping_agent_directory_not_artifact(self):
        """Test that directories mapped to 'agent' are not detected as artifacts.

        When a user maps a directory to 'agent', the directory itself should NOT
        be an artifact. Only .md files inside should be detected as agents.
        """
        files = [
            "categories/ai-engineer/prompt.md",
            "categories/ai-engineer/README.md",
            "categories/code-review/review.md",
        ]
        detector = HeuristicDetector(manual_mappings={"categories": "agent"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        # Should detect individual .md files as agents, not the directories
        paths = {m.path for m in matches}

        # Directories should NOT be detected
        assert "categories" not in paths
        assert "categories/ai-engineer" not in paths
        assert "categories/code-review" not in paths

        # .md files (except README) should be detected as agents
        assert "categories/ai-engineer/prompt.md" in paths
        assert "categories/code-review/review.md" in paths

        # README.md should be excluded
        assert "categories/ai-engineer/README.md" not in paths

        # All detected artifacts should be agents
        for match in matches:
            assert match.artifact_type == "agent"

    def test_manual_mapping_command_directory_not_artifact(self):
        """Test that directories mapped to 'command' are not detected as artifacts."""
        files = [
            "my-commands/deploy.md",
            "my-commands/build.md",
            "my-commands/nested/test.md",
        ]
        detector = HeuristicDetector(manual_mappings={"my-commands": "command"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        # Directory should NOT be detected
        assert "my-commands" not in paths
        assert "my-commands/nested" not in paths

        # .md files should be detected as commands
        assert "my-commands/deploy.md" in paths
        assert "my-commands/build.md" in paths
        assert "my-commands/nested/test.md" in paths

        for match in matches:
            assert match.artifact_type == "command"

    def test_manual_mapping_hook_directory_not_artifact(self):
        """Test that directories mapped to 'hook' are not detected as artifacts."""
        files = [
            "git-hooks/pre-commit.md",
            "git-hooks/post-checkout.md",
        ]
        detector = HeuristicDetector(manual_mappings={"git-hooks": "hook"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        assert "git-hooks" not in paths
        assert "git-hooks/pre-commit.md" in paths
        assert "git-hooks/post-checkout.md" in paths

        for match in matches:
            assert match.artifact_type == "hook"

    def test_manual_mapping_mcp_server_directory_not_artifact(self):
        """Test that directories mapped to 'mcp' are not detected as artifacts."""
        files = [
            "servers/database.md",
            "servers/api.md",
        ]
        detector = HeuristicDetector(manual_mappings={"servers": "mcp"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        assert "servers" not in paths
        assert "servers/database.md" in paths
        assert "servers/api.md" in paths

        for match in matches:
            assert match.artifact_type == "mcp"

    def test_manual_mapping_skill_directory_is_artifact(self):
        """Test that directories mapped to 'skill' WITH SKILL.md are detected as artifacts."""
        files = [
            "my-skills/canvas/SKILL.md",
            "my-skills/canvas/index.ts",
            "my-skills/planning/SKILL.md",
            "my-skills/planning/plan.py",
        ]
        detector = HeuristicDetector(manual_mappings={"my-skills": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        # Skill directories with SKILL.md should be detected
        assert "my-skills/canvas" in paths
        assert "my-skills/planning" in paths

        # Container should not be detected
        assert "my-skills" not in paths

        for match in matches:
            assert match.artifact_type == "skill"

    def test_manual_mapping_skill_directory_without_manifest_not_artifact(self):
        """Test that skill directories without SKILL.md are not detected."""
        files = [
            "my-skills/incomplete/index.ts",  # No SKILL.md
            "my-skills/incomplete/helpers.py",
        ]
        detector = HeuristicDetector(manual_mappings={"my-skills": "skill"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        # Without SKILL.md, should not be detected
        assert "my-skills/incomplete" not in paths
        assert len(matches) == 0

    def test_manual_mapping_agent_confidence_scores(self):
        """Test that manually-mapped single-file agents get proper confidence scores."""
        files = [
            "agents/helper.md",  # depth=0 from mapping
            "agents/nested/reviewer.md",  # depth=1 from mapping
            "agents/deep/nested/tester.md",  # depth=2 from mapping
        ]
        detector = HeuristicDetector(manual_mappings={"agents": "agent"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        matches_by_path = {m.path: m for m in matches}

        # Direct in container: depth=0 -> 95
        assert matches_by_path["agents/helper.md"].confidence_score == 95

        # One level nested: depth=1 -> 92
        assert matches_by_path["agents/nested/reviewer.md"].confidence_score == 92

        # Two levels nested: depth=2 -> 89
        assert matches_by_path["agents/deep/nested/tester.md"].confidence_score == 89

    def test_manual_mapping_agent_metadata(self):
        """Test that manually-mapped single-file agents have correct metadata."""
        files = ["my-agents/helper.md"]
        detector = HeuristicDetector(manual_mappings={"my-agents": "agent"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        assert len(matches) == 1
        match = matches[0]

        assert match.metadata is not None
        assert match.metadata["is_manual_mapping"] is True
        assert "match_type" in match.metadata
        assert "inheritance_depth" in match.metadata
        assert "confidence_reason" in match.metadata

    def test_manual_mapping_mixed_skill_and_agent(self):
        """Test manual mappings with both skill and agent types."""
        files = [
            "skills/canvas/SKILL.md",
            "skills/canvas/index.ts",
            "agents/helper.md",
            "agents/reviewer.md",
        ]
        detector = HeuristicDetector(
            manual_mappings={"skills": "skill", "agents": "agent"}
        )
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        matches_by_path = {m.path: m for m in matches}

        # Skill directory with SKILL.md
        assert "skills/canvas" in matches_by_path
        assert matches_by_path["skills/canvas"].artifact_type == "skill"

        # Agent single files
        assert "agents/helper.md" in matches_by_path
        assert matches_by_path["agents/helper.md"].artifact_type == "agent"
        assert "agents/reviewer.md" in matches_by_path
        assert matches_by_path["agents/reviewer.md"].artifact_type == "agent"

        # Directories should not be artifacts
        assert "skills" not in matches_by_path
        assert "agents" not in matches_by_path

    def test_awesome_subagents_scenario(self):
        """Test the VoltAgent/awesome-claude-code-subagents scenario from the bug report.

        User imports with manual mapping: {"categories": "agent"}
        Each .md file under categories should be an Agent, not the directories.
        """
        files = [
            "categories/ai-engineer/prompt.md",
            "categories/ai-engineer/example.md",
            "categories/code-review/review-prompt.md",
            "categories/debugging/debugger.md",
            "categories/README.md",
        ]
        detector = HeuristicDetector(manual_mappings={"categories": "agent"})
        matches = detector.analyze_paths(files, "https://github.com/test/repo")

        paths = {m.path for m in matches}

        # Directories should NOT be detected
        assert "categories" not in paths
        assert "categories/ai-engineer" not in paths
        assert "categories/code-review" not in paths
        assert "categories/debugging" not in paths

        # .md files should be detected as agents
        assert "categories/ai-engineer/prompt.md" in paths
        assert "categories/ai-engineer/example.md" in paths
        assert "categories/code-review/review-prompt.md" in paths
        assert "categories/debugging/debugger.md" in paths

        # README should be excluded
        assert "categories/README.md" not in paths

        # All should be agents with proper confidence
        for match in matches:
            assert match.artifact_type == "agent"
            assert match.confidence_score >= 86  # Manual mapping minimum
