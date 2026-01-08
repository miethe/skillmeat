"""Tests for artifact validation."""

import tempfile
from pathlib import Path

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.utils.validator import (
    ArtifactValidator,
    ValidationResult,
    normalize_artifact_type,
    validate_artifact_type,
)


class TestSkillValidation:
    """Test skill artifact validation."""

    def test_validate_skill_valid(self, tmp_path):
        """Test validating a valid skill."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# My Skill\n\nThis is a test skill.")

        result = ArtifactValidator.validate_skill(skill_dir)
        assert result.is_valid is True
        assert result.error_message is None
        assert result.artifact_type == ArtifactType.SKILL

    def test_validate_skill_missing_skill_md(self, tmp_path):
        """Test validating skill without SKILL.md."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        result = ArtifactValidator.validate_skill(skill_dir)
        assert result.is_valid is False
        assert "SKILL.md" in result.error_message

    def test_validate_skill_empty_skill_md(self, tmp_path):
        """Test validating skill with empty SKILL.md."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("")

        result = ArtifactValidator.validate_skill(skill_dir)
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    def test_validate_skill_not_directory(self, tmp_path):
        """Test validating skill that is a file, not directory."""
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Skill")

        result = ArtifactValidator.validate_skill(skill_file)
        assert result.is_valid is False
        assert "directory" in result.error_message.lower()

    def test_validate_skill_nonexistent(self, tmp_path):
        """Test validating nonexistent skill."""
        skill_dir = tmp_path / "nonexistent"

        result = ArtifactValidator.validate_skill(skill_dir)
        assert result.is_valid is False
        assert "does not exist" in result.error_message.lower()


class TestCommandValidation:
    """Test command artifact validation."""

    def test_validate_command_file(self, tmp_path):
        """Test validating command as a .md file."""
        command_file = tmp_path / "review.md"
        command_file.write_text("# Review Command\n\nReview code changes.")

        result = ArtifactValidator.validate_command(command_file)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.COMMAND
        assert result.deprecation_warning is None  # File-based is not deprecated

    def test_validate_command_directory(self, tmp_path):
        """Test validating command as a directory with command.md."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        command_md = command_dir / "command.md"
        command_md.write_text("# Review Command")

        result = ArtifactValidator.validate_command(command_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.COMMAND
        assert result.deprecation_warning is not None  # Directory-based is deprecated
        assert "deprecated" in result.deprecation_warning.lower()
        assert "single .md file" in result.deprecation_warning.lower()

    def test_validate_command_directory_any_md(self, tmp_path):
        """Test validating command directory with any .md file."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        md_file = command_dir / "README.md"
        md_file.write_text("# Review Command")

        result = ArtifactValidator.validate_command(command_dir)
        assert result.is_valid is True
        assert result.deprecation_warning is not None  # Directory-based is deprecated

    def test_validate_command_empty_file(self, tmp_path):
        """Test validating command with empty .md file."""
        command_file = tmp_path / "review.md"
        command_file.write_text("")

        result = ArtifactValidator.validate_command(command_file)
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    def test_validate_command_wrong_extension(self, tmp_path):
        """Test validating command with wrong file extension."""
        command_file = tmp_path / "review.txt"
        command_file.write_text("# Review Command")

        result = ArtifactValidator.validate_command(command_file)
        assert result.is_valid is False
        assert ".md" in result.error_message

    def test_validate_command_directory_no_md(self, tmp_path):
        """Test validating command directory without any .md file."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()

        result = ArtifactValidator.validate_command(command_dir)
        assert result.is_valid is False
        assert ".md" in result.error_message

    def test_validate_command_nonexistent(self, tmp_path):
        """Test validating nonexistent command."""
        command_file = tmp_path / "nonexistent.md"

        result = ArtifactValidator.validate_command(command_file)
        assert result.is_valid is False
        assert "does not exist" in result.error_message.lower()


class TestAgentValidation:
    """Test agent artifact validation."""

    def test_validate_agent_file(self, tmp_path):
        """Test validating agent as a .md file."""
        agent_file = tmp_path / "coder.md"
        agent_file.write_text("# Coding Agent\n\nAn AI coding assistant.")

        result = ArtifactValidator.validate_agent(agent_file)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.AGENT
        assert result.deprecation_warning is None  # File-based is not deprecated

    def test_validate_agent_directory_upper(self, tmp_path):
        """Test validating agent directory with AGENT.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        agent_md = agent_dir / "AGENT.md"
        agent_md.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.AGENT
        assert result.deprecation_warning is not None  # Directory-based is deprecated
        assert "deprecated" in result.deprecation_warning.lower()
        assert "single .md file" in result.deprecation_warning.lower()

    def test_validate_agent_directory_lower(self, tmp_path):
        """Test validating agent directory with agent.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        agent_md = agent_dir / "agent.md"
        agent_md.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.AGENT
        assert result.deprecation_warning is not None  # Directory-based is deprecated

    def test_validate_agent_directory_any_md(self, tmp_path):
        """Test validating agent directory with any .md file."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        md_file = agent_dir / "README.md"
        md_file.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True
        assert result.deprecation_warning is not None  # Directory-based is deprecated

    def test_validate_agent_empty_file(self, tmp_path):
        """Test validating agent with empty .md file."""
        agent_file = tmp_path / "coder.md"
        agent_file.write_text("")

        result = ArtifactValidator.validate_agent(agent_file)
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    def test_validate_agent_wrong_extension(self, tmp_path):
        """Test validating agent with wrong file extension."""
        agent_file = tmp_path / "coder.txt"
        agent_file.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_file)
        assert result.is_valid is False
        assert ".md" in result.error_message

    def test_validate_agent_directory_no_md(self, tmp_path):
        """Test validating agent directory without any .md file."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is False
        assert ".md" in result.error_message

    def test_validate_agent_nonexistent(self, tmp_path):
        """Test validating nonexistent agent."""
        agent_file = tmp_path / "nonexistent.md"

        result = ArtifactValidator.validate_agent(agent_file)
        assert result.is_valid is False
        assert "does not exist" in result.error_message.lower()


class TestGenericValidation:
    """Test generic validate() method."""

    def test_validate_skill(self, tmp_path):
        """Test validate with SKILL type."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# My Skill")

        result = ArtifactValidator.validate(skill_dir, ArtifactType.SKILL)
        assert result.is_valid is True

    def test_validate_command(self, tmp_path):
        """Test validate with COMMAND type."""
        command_file = tmp_path / "review.md"
        command_file.write_text("# Review")

        result = ArtifactValidator.validate(command_file, ArtifactType.COMMAND)
        assert result.is_valid is True

    def test_validate_agent(self, tmp_path):
        """Test validate with AGENT type."""
        agent_file = tmp_path / "coder.md"
        agent_file.write_text("# Coder")

        result = ArtifactValidator.validate(agent_file, ArtifactType.AGENT)
        assert result.is_valid is True


class TestDetectArtifactType:
    """Test artifact type detection."""

    def test_detect_skill(self, tmp_path):
        """Test detecting skill type."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        detected = ArtifactValidator.detect_artifact_type(skill_dir)
        assert detected == ArtifactType.SKILL

    def test_detect_agent_upper(self, tmp_path):
        """Test detecting agent type with AGENT.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text("# Agent")

        detected = ArtifactValidator.detect_artifact_type(agent_dir)
        assert detected == ArtifactType.AGENT

    def test_detect_agent_lower(self, tmp_path):
        """Test detecting agent type with agent.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        (agent_dir / "agent.md").write_text("# Agent")

        detected = ArtifactValidator.detect_artifact_type(agent_dir)
        assert detected == ArtifactType.AGENT

    def test_detect_command_file(self, tmp_path):
        """Test detecting command type from .md file."""
        command_file = tmp_path / "review.md"
        command_file.write_text("# Command")

        detected = ArtifactValidator.detect_artifact_type(command_file)
        assert detected == ArtifactType.COMMAND

    def test_detect_command_directory(self, tmp_path):
        """Test detecting command type from directory with .md file."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        (command_dir / "README.md").write_text("# Command")

        detected = ArtifactValidator.detect_artifact_type(command_dir)
        assert detected == ArtifactType.COMMAND

    def test_detect_nonexistent(self, tmp_path):
        """Test detecting type of nonexistent path."""
        detected = ArtifactValidator.detect_artifact_type(tmp_path / "nonexistent")
        assert detected is None

    def test_detect_directory_no_markers(self, tmp_path):
        """Test detecting type of directory with no markers."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        detected = ArtifactValidator.detect_artifact_type(empty_dir)
        assert detected is None

    def test_detect_skill_priority_over_agent(self, tmp_path):
        """Test that SKILL.md takes priority over AGENT.md."""
        dir_path = tmp_path / "artifact"
        dir_path.mkdir()
        (dir_path / "SKILL.md").write_text("# Skill")
        (dir_path / "AGENT.md").write_text("# Agent")

        detected = ArtifactValidator.detect_artifact_type(dir_path)
        assert detected == ArtifactType.SKILL


class TestNormalizeArtifactType:
    """Test artifact type normalization function."""

    def test_normalize_string_lowercase(self):
        """Test normalizing lowercase string artifact types."""
        assert normalize_artifact_type("skill") == ArtifactType.SKILL
        assert normalize_artifact_type("command") == ArtifactType.COMMAND
        assert normalize_artifact_type("agent") == ArtifactType.AGENT
        assert normalize_artifact_type("hook") == ArtifactType.HOOK
        assert normalize_artifact_type("mcp") == ArtifactType.MCP

    def test_normalize_string_uppercase(self):
        """Test normalizing uppercase string artifact types."""
        assert normalize_artifact_type("SKILL") == ArtifactType.SKILL
        assert normalize_artifact_type("COMMAND") == ArtifactType.COMMAND
        assert normalize_artifact_type("AGENT") == ArtifactType.AGENT
        assert normalize_artifact_type("HOOK") == ArtifactType.HOOK
        assert normalize_artifact_type("MCP") == ArtifactType.MCP

    def test_normalize_string_mixed_case(self):
        """Test normalizing mixed case string artifact types."""
        assert normalize_artifact_type("Skill") == ArtifactType.SKILL
        assert normalize_artifact_type("CoMmAnD") == ArtifactType.COMMAND

    def test_normalize_string_with_whitespace(self):
        """Test normalizing strings with leading/trailing whitespace."""
        assert normalize_artifact_type("  skill  ") == ArtifactType.SKILL
        assert normalize_artifact_type("\tcommand\n") == ArtifactType.COMMAND

    def test_normalize_enum_passthrough(self):
        """Test that ArtifactType enums pass through unchanged."""
        assert normalize_artifact_type(ArtifactType.SKILL) == ArtifactType.SKILL
        assert normalize_artifact_type(ArtifactType.COMMAND) == ArtifactType.COMMAND
        assert normalize_artifact_type(ArtifactType.AGENT) == ArtifactType.AGENT
        assert normalize_artifact_type(ArtifactType.HOOK) == ArtifactType.HOOK
        assert normalize_artifact_type(ArtifactType.MCP) == ArtifactType.MCP

    def test_normalize_mcp_aliases(self):
        """Test historical MCP type aliases (backwards compatibility)."""
        # Snake_case variant
        assert normalize_artifact_type("mcp_server") == ArtifactType.MCP
        # Kebab-case variant
        assert normalize_artifact_type("mcp-server") == ArtifactType.MCP
        # No separator variant
        assert normalize_artifact_type("mcpserver") == ArtifactType.MCP
        # Uppercase variants
        assert normalize_artifact_type("MCP_SERVER") == ArtifactType.MCP
        assert normalize_artifact_type("MCP-SERVER") == ArtifactType.MCP

    def test_normalize_context_types(self):
        """Test normalizing context entity types."""
        assert normalize_artifact_type("project_config") == ArtifactType.PROJECT_CONFIG
        assert normalize_artifact_type("spec_file") == ArtifactType.SPEC_FILE
        assert normalize_artifact_type("rule_file") == ArtifactType.RULE_FILE
        assert normalize_artifact_type("context_file") == ArtifactType.CONTEXT_FILE
        assert (
            normalize_artifact_type("progress_template") == ArtifactType.PROGRESS_TEMPLATE
        )

    def test_normalize_invalid_string(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid artifact type"):
            normalize_artifact_type("invalid")

        with pytest.raises(ValueError, match="Invalid artifact type"):
            normalize_artifact_type("unknown_type")

        with pytest.raises(ValueError, match="Invalid artifact type"):
            normalize_artifact_type("")

    def test_normalize_invalid_type(self):
        """Test that non-string, non-enum values raise ValueError."""
        with pytest.raises(ValueError, match="must be a string or ArtifactType enum"):
            normalize_artifact_type(123)

        with pytest.raises(ValueError, match="must be a string or ArtifactType enum"):
            normalize_artifact_type(None)

        with pytest.raises(ValueError, match="must be a string or ArtifactType enum"):
            normalize_artifact_type(["skill"])

        with pytest.raises(ValueError, match="must be a string or ArtifactType enum"):
            normalize_artifact_type({"type": "skill"})

    def test_normalize_error_message_includes_valid_types(self):
        """Test that error message lists all valid types."""
        with pytest.raises(ValueError) as exc_info:
            normalize_artifact_type("bad_type")

        error_message = str(exc_info.value)
        # Should include all primary types
        assert "skill" in error_message
        assert "command" in error_message
        assert "agent" in error_message
        assert "hook" in error_message
        assert "mcp" in error_message


class TestValidateArtifactType:
    """Test artifact type validation function (non-throwing)."""

    def test_validate_valid_strings(self):
        """Test that valid string types return True."""
        assert validate_artifact_type("skill") is True
        assert validate_artifact_type("command") is True
        assert validate_artifact_type("agent") is True
        assert validate_artifact_type("hook") is True
        assert validate_artifact_type("mcp") is True

    def test_validate_valid_uppercase_strings(self):
        """Test that uppercase valid strings return True."""
        assert validate_artifact_type("SKILL") is True
        assert validate_artifact_type("COMMAND") is True

    def test_validate_valid_enums(self):
        """Test that ArtifactType enums return True."""
        assert validate_artifact_type(ArtifactType.SKILL) is True
        assert validate_artifact_type(ArtifactType.COMMAND) is True
        assert validate_artifact_type(ArtifactType.AGENT) is True
        assert validate_artifact_type(ArtifactType.HOOK) is True
        assert validate_artifact_type(ArtifactType.MCP) is True

    def test_validate_mcp_aliases(self):
        """Test that MCP aliases return True."""
        assert validate_artifact_type("mcp_server") is True
        assert validate_artifact_type("mcp-server") is True
        assert validate_artifact_type("mcpserver") is True
        assert validate_artifact_type("MCP_SERVER") is True

    def test_validate_context_types(self):
        """Test that context entity types return True."""
        assert validate_artifact_type("project_config") is True
        assert validate_artifact_type("spec_file") is True
        assert validate_artifact_type("rule_file") is True
        assert validate_artifact_type("context_file") is True
        assert validate_artifact_type("progress_template") is True

    def test_validate_invalid_strings(self):
        """Test that invalid strings return False (no exception)."""
        assert validate_artifact_type("invalid") is False
        assert validate_artifact_type("unknown") is False
        assert validate_artifact_type("") is False
        assert validate_artifact_type("   ") is False

    def test_validate_invalid_types(self):
        """Test that invalid types return False (no exception)."""
        assert validate_artifact_type(123) is False
        assert validate_artifact_type(None) is False
        assert validate_artifact_type([]) is False
        assert validate_artifact_type({}) is False
        assert validate_artifact_type(True) is False

    def test_validate_does_not_raise(self):
        """Test that validate never raises exceptions."""
        # Should not raise, just return False
        try:
            result = validate_artifact_type("totally_invalid_type")
            assert result is False
        except Exception as e:
            pytest.fail(f"validate_artifact_type should not raise, but raised {e}")

        try:
            result = validate_artifact_type(99999)
            assert result is False
        except Exception as e:
            pytest.fail(f"validate_artifact_type should not raise, but raised {e}")

