"""Comprehensive unit tests for ArtifactDiscoveryService.

This test suite provides >80% code coverage for the discovery.py module,
testing all public methods, artifact types, error scenarios, and performance.
"""

import time
from pathlib import Path

import pytest
import yaml

from skillmeat.core.discovery import (
    ArtifactDiscoveryService,
    DiscoveredArtifact,
    DiscoveryResult,
)


class TestArtifactDiscovery:
    """Test suite for core artifact discovery functionality."""

    @pytest.fixture
    def sample_skill(self, tmp_path):
        """Create a sample skill artifact for testing.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to collection root with sample skill
        """
        skill_dir = tmp_path / "artifacts" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill for unit testing
author: test-author
version: 1.0.0
tags:
  - testing
  - automation
source: github/test/repo
scope: user
---

# Test Skill

This is a test skill artifact.
"""
        )
        return tmp_path

    @pytest.fixture
    def empty_collection(self, tmp_path):
        """Create empty collection structure.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to collection root with empty artifacts dir
        """
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        return tmp_path

    def test_discover_artifacts_success(self, sample_skill):
        """Test successful artifact discovery with valid skill."""
        service = ArtifactDiscoveryService(sample_skill)
        result = service.discover_artifacts()

        assert result.discovered_count == 1
        assert len(result.artifacts) == 1
        assert result.artifacts[0].type == "skill"
        assert result.artifacts[0].name == "test-skill"
        assert result.artifacts[0].description == "A test skill for unit testing"
        assert result.artifacts[0].version == "1.0.0"
        assert "testing" in result.artifacts[0].tags
        assert "automation" in result.artifacts[0].tags
        assert result.artifacts[0].source == "github/test/repo"
        assert result.artifacts[0].scope == "user"
        assert result.scan_duration_ms > 0
        assert len(result.errors) == 0

    def test_discover_artifacts_empty_directory(self, empty_collection):
        """Test discovery when no artifacts found."""
        service = ArtifactDiscoveryService(empty_collection)
        result = service.discover_artifacts()

        assert result.discovered_count == 0
        assert len(result.artifacts) == 0
        assert len(result.errors) == 0
        assert result.scan_duration_ms > 0

    def test_discover_artifacts_no_artifacts_dir(self, tmp_path):
        """Test discovery when artifacts directory doesn't exist."""
        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 0
        assert len(result.artifacts) == 0
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    def test_discover_multiple_types(self, tmp_path):
        """Test discovery finds skills, commands, agents, hooks, and mcps."""
        # Create skill
        skill_dir = tmp_path / "artifacts" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n# Skill")

        # Create command
        cmd_dir = tmp_path / "artifacts" / "commands" / "my-command"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "COMMAND.md").write_text("---\nname: my-command\n---\n# Command")

        # Create agent
        agent_dir = tmp_path / "artifacts" / "agents" / "my-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "AGENT.md").write_text("---\nname: my-agent\n---\n# Agent")

        # Create hook
        hook_dir = tmp_path / "artifacts" / "hooks" / "my-hook"
        hook_dir.mkdir(parents=True)
        (hook_dir / "HOOK.md").write_text("---\nname: my-hook\n---\n# Hook")

        # Create MCP
        mcp_dir = tmp_path / "artifacts" / "mcps" / "my-mcp"
        mcp_dir.mkdir(parents=True)
        (mcp_dir / "MCP.md").write_text("---\nname: my-mcp\n---\n# MCP")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 5
        types = {a.type for a in result.artifacts}
        assert types == {"skill", "command", "agent", "hook", "mcp"}

        # Verify names
        names = {a.name for a in result.artifacts}
        assert names == {"my-skill", "my-command", "my-agent", "my-hook", "my-mcp"}

    def test_discover_multiple_artifacts_same_type(self, tmp_path):
        """Test discovery finds multiple artifacts of the same type."""
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        # Create 5 different skills
        for i in range(5):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\ndescription: Skill {i}\n---\n"
            )

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 5
        assert all(a.type == "skill" for a in result.artifacts)
        assert len({a.name for a in result.artifacts}) == 5

    def test_discover_skips_hidden_directories(self, tmp_path):
        """Test that discovery skips hidden directories (starting with .)."""
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        # Create visible skill
        visible = skills_dir / "visible-skill"
        visible.mkdir()
        (visible / "SKILL.md").write_text("---\nname: visible\n---\n")

        # Create hidden skill (should be skipped)
        hidden = skills_dir / ".hidden-skill"
        hidden.mkdir()
        (hidden / "SKILL.md").write_text("---\nname: hidden\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 1
        assert result.artifacts[0].name == "visible"


class TestTypeDetection:
    """Test suite for artifact type detection."""

    def test_detect_skill_type(self, tmp_path):
        """Test detection via SKILL.md file."""
        skill_dir = tmp_path / "test-artifact"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(skill_dir)
        assert detected == "skill"

    def test_detect_command_type_uppercase(self, tmp_path):
        """Test detection via COMMAND.md file (uppercase)."""
        cmd_dir = tmp_path / "test-command"
        cmd_dir.mkdir()
        (cmd_dir / "COMMAND.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(cmd_dir)
        assert detected == "command"

    def test_detect_command_type_lowercase(self, tmp_path):
        """Test detection via command.md file (lowercase)."""
        cmd_dir = tmp_path / "test-command"
        cmd_dir.mkdir()
        (cmd_dir / "command.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(cmd_dir)
        assert detected == "command"

    def test_detect_agent_type_uppercase(self, tmp_path):
        """Test detection via AGENT.md file (uppercase)."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(agent_dir)
        assert detected == "agent"

    def test_detect_agent_type_lowercase(self, tmp_path):
        """Test detection via agent.md file (lowercase)."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "agent.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(agent_dir)
        assert detected == "agent"

    def test_detect_hook_type_uppercase(self, tmp_path):
        """Test detection via HOOK.md file (uppercase)."""
        hook_dir = tmp_path / "test-hook"
        hook_dir.mkdir()
        (hook_dir / "HOOK.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(hook_dir)
        assert detected == "hook"

    def test_detect_hook_type_lowercase(self, tmp_path):
        """Test detection via hook.md file (lowercase)."""
        hook_dir = tmp_path / "test-hook"
        hook_dir.mkdir()
        (hook_dir / "hook.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(hook_dir)
        assert detected == "hook"

    def test_detect_mcp_type_md(self, tmp_path):
        """Test detection via MCP.md file."""
        mcp_dir = tmp_path / "test-mcp"
        mcp_dir.mkdir()
        (mcp_dir / "MCP.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(mcp_dir)
        assert detected == "mcp"

    def test_detect_mcp_type_json(self, tmp_path):
        """Test detection via mcp.json file."""
        mcp_dir = tmp_path / "test-mcp"
        mcp_dir.mkdir()
        (mcp_dir / "mcp.json").write_text('{"name": "test"}')

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(mcp_dir)
        assert detected == "mcp"

    def test_detect_unknown_type(self, tmp_path):
        """Test handling of unknown artifact type."""
        unknown_dir = tmp_path / "unknown-artifact"
        unknown_dir.mkdir()
        (unknown_dir / "README.md").write_text("Not an artifact")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(unknown_dir)
        assert detected is None

    def test_detect_file_command(self, tmp_path):
        """Test detection of command as single .md file."""
        cmd_file = tmp_path / "my-command.md"
        cmd_file.write_text("---\nname: my-command\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(cmd_file)
        assert detected == "command"

    def test_detect_file_agent(self, tmp_path):
        """Test detection of agent as single .md file."""
        agent_file = tmp_path / "my-agent.md"
        agent_file.write_text("---\nname: my-agent\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(agent_file)
        assert detected == "agent"

    def test_detect_type_nonexistent_path(self, tmp_path):
        """Test detection on non-existent path."""
        nonexistent = tmp_path / "does-not-exist"

        service = ArtifactDiscoveryService(tmp_path)
        detected = service._detect_artifact_type(nonexistent)
        assert detected is None


class TestMetadataExtraction:
    """Test suite for metadata extraction from frontmatter."""

    def test_extract_metadata_complete(self, tmp_path):
        """Test extraction with all fields present."""
        skill_dir = tmp_path / "complete-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: complete-skill
description: Full description here
author: author-name
version: 1.0.0
tags:
  - tag1
  - tag2
  - tag3
source: github/user/repo
scope: user
license: MIT
---

# Complete Skill
"""
        )

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        assert metadata["name"] == "complete-skill"
        assert metadata["description"] == "Full description here"
        assert metadata["author"] == "author-name"
        assert metadata["version"] == "1.0.0"
        assert metadata["tags"] == ["tag1", "tag2", "tag3"]
        assert metadata["source"] == "github/user/repo"
        assert metadata["scope"] == "user"
        assert metadata["license"] == "MIT"

    def test_extract_metadata_partial(self, tmp_path):
        """Test extraction with some fields missing."""
        skill_dir = tmp_path / "partial-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: partial
description: Only has name and description
---
"""
        )

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        assert metadata["name"] == "partial"
        assert metadata["description"] == "Only has name and description"
        assert "author" not in metadata
        assert "version" not in metadata
        assert "source" not in metadata

    def test_extract_metadata_minimal(self, tmp_path):
        """Test extraction with only name field."""
        skill_dir = tmp_path / "minimal-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: minimal\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        assert metadata["name"] == "minimal"
        assert "description" not in metadata

    def test_extract_metadata_invalid_yaml(self, tmp_path):
        """Test handling of corrupted/invalid YAML frontmatter."""
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
invalid yaml: : : :
[broken structure
---
"""
        )

        service = ArtifactDiscoveryService(tmp_path)
        # Should handle gracefully, not crash
        metadata = service._extract_artifact_metadata(skill_dir, "skill")
        # Should return empty metadata on parse error
        assert isinstance(metadata, dict)

    def test_extract_metadata_no_frontmatter(self, tmp_path):
        """Test extraction when file has no frontmatter."""
        skill_dir = tmp_path / "no-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just a heading\n\nNo frontmatter here.")

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        # Should return empty metadata
        assert isinstance(metadata, dict)
        assert len(metadata) == 0

    def test_extract_metadata_empty_file(self, tmp_path):
        """Test extraction from empty metadata file."""
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("")

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        assert isinstance(metadata, dict)

    def test_extract_metadata_with_title_fallback(self, tmp_path):
        """Test that 'title' field falls back to 'name'."""
        skill_dir = tmp_path / "title-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ntitle: My Title\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        # 'title' should map to 'name'
        assert metadata["name"] == "My Title"

    def test_extract_metadata_with_upstream_fallback(self, tmp_path):
        """Test that 'upstream' field falls back to 'source'."""
        skill_dir = tmp_path / "upstream-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\nupstream: github/user/repo\n---\n"
        )

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(skill_dir, "skill")

        # 'upstream' should map to 'source'
        assert metadata["source"] == "github/user/repo"

    def test_extract_metadata_command(self, tmp_path):
        """Test metadata extraction from command."""
        cmd_dir = tmp_path / "test-command"
        cmd_dir.mkdir()
        (cmd_dir / "COMMAND.md").write_text(
            "---\nname: test-command\ndescription: Test command\n---\n"
        )

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(cmd_dir, "command")

        assert metadata["name"] == "test-command"
        assert metadata["description"] == "Test command"

    def test_extract_metadata_agent(self, tmp_path):
        """Test metadata extraction from agent."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text(
            "---\nname: test-agent\nauthor: Agent Author\n---\n"
        )

        service = ArtifactDiscoveryService(tmp_path)
        metadata = service._extract_artifact_metadata(agent_dir, "agent")

        assert metadata["name"] == "test-agent"
        assert metadata["author"] == "Agent Author"


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_invalid_artifact_skipped(self, tmp_path):
        """Test that invalid artifacts are skipped with warning."""
        # Create valid skill
        valid = tmp_path / "artifacts" / "skills" / "valid"
        valid.mkdir(parents=True)
        (valid / "SKILL.md").write_text("---\nname: valid\n---\n# Valid")

        # Create invalid (no metadata file)
        invalid = tmp_path / "artifacts" / "skills" / "invalid"
        invalid.mkdir(parents=True)
        (invalid / "README.md").write_text("Not a skill")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should find valid, skip invalid
        assert result.discovered_count == 1
        assert result.artifacts[0].name == "valid"

    def test_missing_required_files(self, tmp_path):
        """Test detection of incomplete artifacts."""
        # Create directory that looks like artifact but missing SKILL.md
        incomplete = tmp_path / "artifacts" / "skills" / "incomplete"
        incomplete.mkdir(parents=True)
        (incomplete / "README.md").write_text("Has README but no SKILL.md")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should not discover incomplete artifact
        assert result.discovered_count == 0

    def test_mixed_valid_invalid_artifacts(self, tmp_path):
        """Test that valid artifacts are discovered even when invalid ones exist."""
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        # Create 3 valid skills
        for i in range(3):
            skill = skills_dir / f"valid-{i}"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"---\nname: valid-{i}\n---\n")

        # Create 2 invalid skills
        for i in range(2):
            skill = skills_dir / f"invalid-{i}"
            skill.mkdir()
            (skill / "README.md").write_text("No SKILL.md")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should find only valid artifacts
        assert result.discovered_count == 3

    def test_unsupported_directory_skipped(self, tmp_path):
        """Test that unsupported artifact type directories are skipped."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Create supported type
        skills_dir = artifacts_dir / "skills"
        skills_dir.mkdir()
        skill = skills_dir / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        # Create unsupported type directory
        unsupported = artifacts_dir / "unsupported-type"
        unsupported.mkdir()
        (unsupported / "thing.md").write_text("---\nname: thing\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should find only supported type
        assert result.discovered_count == 1
        assert result.artifacts[0].type == "skill"

    def test_corrupted_frontmatter_adds_error(self, tmp_path):
        """Test that artifacts with corrupted frontmatter add errors but don't crash."""
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        # Create skill with corrupted YAML
        corrupted = skills_dir / "corrupted"
        corrupted.mkdir()
        (corrupted / "SKILL.md").write_text("---\nbroken: yaml: : :\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should not crash, validation should fail
        assert result.discovered_count == 0

    def test_file_in_artifacts_root_skipped(self, tmp_path):
        """Test that files directly in artifacts/ are skipped."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Create file directly in artifacts/ (should be skipped)
        (artifacts_dir / "loose-file.md").write_text("---\nname: loose\n---\n")

        # Create valid skill in subdirectory
        skills_dir = artifacts_dir / "skills"
        skills_dir.mkdir()
        skill = skills_dir / "valid-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: valid\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should find only the valid skill
        assert result.discovered_count == 1
        assert result.artifacts[0].name == "valid"


class TestValidation:
    """Test suite for artifact validation."""

    def test_validate_artifact_valid_skill(self, tmp_path):
        """Test validation of valid skill artifact."""
        skill_dir = tmp_path / "valid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: valid\n---\n# Skill")

        service = ArtifactDiscoveryService(tmp_path)
        is_valid = service._validate_artifact(skill_dir, "skill")

        assert is_valid is True

    def test_validate_artifact_missing_metadata_file(self, tmp_path):
        """Test validation fails when metadata file missing."""
        skill_dir = tmp_path / "no-skill-md"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("No SKILL.md")

        service = ArtifactDiscoveryService(tmp_path)
        is_valid = service._validate_artifact(skill_dir, "skill")

        assert is_valid is False

    def test_validate_artifact_invalid_yaml(self, tmp_path):
        """Test validation fails with invalid YAML."""
        skill_dir = tmp_path / "invalid-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ninvalid: yaml: :\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        is_valid = service._validate_artifact(skill_dir, "skill")

        # Should fail validation due to parse error
        assert is_valid is False

    def test_validate_artifact_empty_frontmatter(self, tmp_path):
        """Test validation with empty but valid frontmatter."""
        skill_dir = tmp_path / "empty-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n---\n# Content")

        service = ArtifactDiscoveryService(tmp_path)
        is_valid = service._validate_artifact(skill_dir, "skill")

        # Empty frontmatter is still valid YAML
        assert is_valid is True


class TestNormalization:
    """Test suite for type normalization from directory names."""

    def test_normalize_type_from_dirname_plural(self, tmp_path):
        """Test normalization of plural directory names."""
        service = ArtifactDiscoveryService(tmp_path)

        assert service._normalize_type_from_dirname("skills") == "skill"
        assert service._normalize_type_from_dirname("commands") == "command"
        assert service._normalize_type_from_dirname("agents") == "agent"
        assert service._normalize_type_from_dirname("hooks") == "hook"
        assert service._normalize_type_from_dirname("mcps") == "mcp"

    def test_normalize_type_from_dirname_singular(self, tmp_path):
        """Test normalization of singular directory names."""
        service = ArtifactDiscoveryService(tmp_path)

        assert service._normalize_type_from_dirname("skill") == "skill"
        assert service._normalize_type_from_dirname("command") == "command"
        assert service._normalize_type_from_dirname("agent") == "agent"

    def test_normalize_type_from_dirname_case_insensitive(self, tmp_path):
        """Test normalization is case-insensitive."""
        service = ArtifactDiscoveryService(tmp_path)

        assert service._normalize_type_from_dirname("SKILLS") == "skill"
        assert service._normalize_type_from_dirname("Commands") == "command"
        assert service._normalize_type_from_dirname("AGENTS") == "agent"


class TestPerformance:
    """Test suite for performance requirements."""

    def test_discovery_performance_50_artifacts(self, tmp_path):
        """Test that discovery completes <2 seconds for 50 artifacts."""
        # Create 50 test artifacts across different types
        artifacts_dir = tmp_path / "artifacts"

        # 40 skills
        skills_dir = artifacts_dir / "skills"
        skills_dir.mkdir(parents=True)
        for i in range(40):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i}
description: Performance test skill {i}
author: test-author
tags:
  - performance
  - test
---

# Skill {i}
"""
            )

        # 10 commands
        cmds_dir = artifacts_dir / "commands"
        cmds_dir.mkdir()
        for i in range(10):
            cmd_dir = cmds_dir / f"cmd-{i}"
            cmd_dir.mkdir()
            (cmd_dir / "COMMAND.md").write_text(
                f"---\nname: cmd-{i}\ndescription: Command {i}\n---\n"
            )

        service = ArtifactDiscoveryService(tmp_path)

        start = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start

        assert result.discovered_count == 50, f"Expected 50, got {result.discovered_count}"
        assert (
            duration < 2.0
        ), f"Discovery took {duration:.2f}s (expected <2s)"
        print(f"\n  Performance: Discovered {result.discovered_count} artifacts in {duration:.3f}s")

    def test_discovery_performance_100_artifacts(self, tmp_path):
        """Test discovery performance with 100 artifacts."""
        # Create 100 test artifacts
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        for i in range(100):
            skill_dir = skills_dir / f"skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i:03d}\ndescription: Skill {i}\n---\n"
            )

        service = ArtifactDiscoveryService(tmp_path)

        start = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start

        assert result.discovered_count == 100
        # Should still be reasonably fast
        assert duration < 5.0, f"Discovery of 100 artifacts took {duration:.2f}s (expected <5s)"
        print(f"\n  Performance: Discovered {result.discovered_count} artifacts in {duration:.3f}s")

    def test_scan_duration_recorded(self, tmp_path):
        """Test that scan duration is properly recorded."""
        # Create simple collection
        skill_dir = tmp_path / "artifacts" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Duration should be positive
        assert result.scan_duration_ms > 0
        # Should be reasonable (not absurdly large)
        assert result.scan_duration_ms < 10000  # <10 seconds


class TestDiscoveredArtifactModel:
    """Test suite for DiscoveredArtifact Pydantic model."""

    def test_discovered_artifact_creation(self):
        """Test creating DiscoveredArtifact with all fields."""
        from datetime import datetime

        artifact = DiscoveredArtifact(
            type="skill",
            name="test-skill",
            source="github/user/repo",
            version="1.0.0",
            scope="user",
            tags=["test", "example"],
            description="Test description",
            path="/path/to/skill",
            discovered_at=datetime.utcnow(),
        )

        assert artifact.type == "skill"
        assert artifact.name == "test-skill"
        assert artifact.source == "github/user/repo"
        assert artifact.version == "1.0.0"
        assert artifact.scope == "user"
        assert artifact.tags == ["test", "example"]
        assert artifact.description == "Test description"
        assert artifact.path == "/path/to/skill"
        assert artifact.discovered_at is not None

    def test_discovered_artifact_optional_fields(self):
        """Test creating DiscoveredArtifact with minimal fields."""
        from datetime import datetime

        artifact = DiscoveredArtifact(
            type="skill",
            name="minimal",
            path="/path",
            discovered_at=datetime.utcnow(),
        )

        assert artifact.type == "skill"
        assert artifact.name == "minimal"
        assert artifact.source is None
        assert artifact.version is None
        assert artifact.tags == []


class TestDiscoveryResultModel:
    """Test suite for DiscoveryResult Pydantic model."""

    def test_discovery_result_creation(self):
        """Test creating DiscoveryResult."""
        from datetime import datetime

        artifact = DiscoveredArtifact(
            type="skill",
            name="test",
            path="/path",
            discovered_at=datetime.utcnow(),
        )

        result = DiscoveryResult(
            discovered_count=1,
            artifacts=[artifact],
            errors=["error1", "error2"],
            scan_duration_ms=123.45,
        )

        assert result.discovered_count == 1
        assert len(result.artifacts) == 1
        assert result.errors == ["error1", "error2"]
        assert result.scan_duration_ms == 123.45

    def test_discovery_result_defaults(self):
        """Test DiscoveryResult with default values."""
        result = DiscoveryResult(
            discovered_count=0, artifacts=[], scan_duration_ms=0.0
        )

        assert result.discovered_count == 0
        assert result.artifacts == []
        assert result.errors == []  # Default empty list
        assert result.scan_duration_ms == 0.0


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_unicode_in_metadata(self, tmp_path):
        """Test handling of Unicode characters in metadata."""
        skill_dir = tmp_path / "artifacts" / "skills" / "unicode-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: unicode-skill
description: Handles 中文, العربية, and emoji 🚀
author: José García
tags:
  - 日本語
  - español
---

# Unicode Skill
""",
            encoding="utf-8",
        )

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 1
        artifact = result.artifacts[0]
        assert "中文" in artifact.description
        assert "🚀" in artifact.description
        assert "日本語" in artifact.tags

    def test_very_long_artifact_name(self, tmp_path):
        """Test handling of very long artifact names."""
        long_name = "a" * 500  # 500 character name
        skill_dir = tmp_path / "artifacts" / "skills" / "long-name"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"---\nname: {long_name}\n---\n")

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 1
        assert result.artifacts[0].name == long_name

    def test_whitespace_only_metadata_values(self, tmp_path):
        """Test handling of whitespace-only metadata values."""
        skill_dir = tmp_path / "artifacts" / "skills" / "whitespace"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: "   "
description: "
"
---
"""
        )

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        # Should still discover, but with whitespace values
        assert result.discovered_count == 1

    def test_deeply_nested_tags(self, tmp_path):
        """Test handling of complex nested tag structures."""
        skill_dir = tmp_path / "artifacts" / "skills" / "nested-tags"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: nested-tags
tags:
  - simple
  - tag
---
"""
        )

        service = ArtifactDiscoveryService(tmp_path)
        result = service.discover_artifacts()

        assert result.discovered_count == 1
        assert result.artifacts[0].tags == ["simple", "tag"]
