"""Tests for artifact validation."""

import tempfile
from pathlib import Path

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.utils.validator import ArtifactValidator, ValidationResult


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

    def test_validate_command_directory(self, tmp_path):
        """Test validating command as a directory with command.md."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        command_md = command_dir / "command.md"
        command_md.write_text("# Review Command")

        result = ArtifactValidator.validate_command(command_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.COMMAND

    def test_validate_command_directory_any_md(self, tmp_path):
        """Test validating command directory with any .md file."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        md_file = command_dir / "README.md"
        md_file.write_text("# Review Command")

        result = ArtifactValidator.validate_command(command_dir)
        assert result.is_valid is True

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

    def test_validate_agent_directory_upper(self, tmp_path):
        """Test validating agent directory with AGENT.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        agent_md = agent_dir / "AGENT.md"
        agent_md.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.AGENT

    def test_validate_agent_directory_lower(self, tmp_path):
        """Test validating agent directory with agent.md."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        agent_md = agent_dir / "agent.md"
        agent_md.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True
        assert result.artifact_type == ArtifactType.AGENT

    def test_validate_agent_directory_any_md(self, tmp_path):
        """Test validating agent directory with any .md file."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        md_file = agent_dir / "README.md"
        md_file.write_text("# Coding Agent")

        result = ArtifactValidator.validate_agent(agent_dir)
        assert result.is_valid is True

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
