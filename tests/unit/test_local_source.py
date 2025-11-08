"""Tests for local source."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.sources.local import LocalSource


class TestLocalSource:
    """Test LocalSource functionality."""

    def test_fetch_skill_valid(self, tmp_path):
        """Test fetching a valid skill from local filesystem."""
        # Create valid skill structure
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\ntitle: My Skill\n---\n\nThis is my skill.")

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        assert result.artifact_path == skill_dir
        assert result.metadata.title == "My Skill"
        assert result.resolved_sha is None
        assert result.resolved_version is None
        assert result.upstream_url is None

    def test_fetch_command_file(self, tmp_path):
        """Test fetching a command file from local filesystem."""
        command_file = tmp_path / "review.md"
        command_file.write_text("# Review Command\n\nReview code.")

        source = LocalSource()
        result = source.fetch(str(command_file), ArtifactType.COMMAND)

        assert result.artifact_path == command_file
        assert result.resolved_sha is None
        assert result.upstream_url is None

    def test_fetch_agent_file(self, tmp_path):
        """Test fetching an agent file from local filesystem."""
        agent_file = tmp_path / "coder.md"
        agent_file.write_text("---\ntitle: Coder Agent\n---\n\nCoding assistant.")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        assert result.artifact_path == agent_file
        assert result.metadata.title == "Coder Agent"

    def test_fetch_nonexistent_path(self, tmp_path):
        """Test fetching from nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        source = LocalSource()
        with pytest.raises(ValueError, match="does not exist"):
            source.fetch(str(nonexistent), ArtifactType.SKILL)

    def test_fetch_invalid_skill(self, tmp_path):
        """Test fetching invalid skill (missing SKILL.md)."""
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        # Don't create SKILL.md

        source = LocalSource()
        with pytest.raises(ValueError, match="Invalid artifact"):
            source.fetch(str(skill_dir), ArtifactType.SKILL)

    def test_fetch_empty_skill_md(self, tmp_path):
        """Test fetching skill with empty SKILL.md."""
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("")

        source = LocalSource()
        with pytest.raises(ValueError, match="Invalid artifact"):
            source.fetch(str(skill_dir), ArtifactType.SKILL)

    @patch("skillmeat.sources.local.extract_artifact_metadata")
    def test_fetch_metadata_extraction_fails(self, mock_extract, tmp_path):
        """Test fetching when metadata extraction fails."""
        mock_extract.side_effect = Exception("Metadata error")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        # Should return empty metadata on extraction failure
        assert result.metadata is not None
        assert result.artifact_path == skill_dir

    def test_check_updates_returns_none(self, tmp_path):
        """Test that check_updates always returns None for local sources."""
        artifact = Artifact(
            name="test",
            type=ArtifactType.SKILL,
            path="skills/test",
            origin="local",
            metadata=ArtifactMetadata(),
            added="2024-01-01T00:00:00",
        )

        source = LocalSource()
        update_info = source.check_updates(artifact)

        assert update_info is None

    def test_validate_valid_skill(self, tmp_path):
        """Test validating a valid skill."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        source = LocalSource()
        result = source.validate(skill_dir, ArtifactType.SKILL)

        assert result is True

    def test_validate_invalid_skill(self, tmp_path):
        """Test validating an invalid skill."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        # Missing SKILL.md

        source = LocalSource()
        result = source.validate(skill_dir, ArtifactType.SKILL)

        assert result is False

    def test_validate_valid_command(self, tmp_path):
        """Test validating a valid command."""
        command_file = tmp_path / "review.md"
        command_file.write_text("# Review")

        source = LocalSource()
        result = source.validate(command_file, ArtifactType.COMMAND)

        assert result is True

    def test_validate_invalid_command(self, tmp_path):
        """Test validating an invalid command."""
        command_file = tmp_path / "review.txt"
        command_file.write_text("# Review")

        source = LocalSource()
        result = source.validate(command_file, ArtifactType.COMMAND)

        assert result is False

    def test_fetch_with_relative_path(self, tmp_path, monkeypatch):
        """Test fetching with relative path (should be resolved to absolute)."""
        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        source = LocalSource()
        result = source.fetch("skill", ArtifactType.SKILL)

        # Should resolve to absolute path
        assert result.artifact_path.is_absolute()
        assert result.artifact_path == skill_dir

    def test_fetch_skill_with_metadata(self, tmp_path):
        """Test fetching skill with YAML frontmatter metadata."""
        skill_dir = tmp_path / "python-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
title: Python Skill
description: Python development assistance
author: Test Author
version: 1.0.0
tags:
  - python
  - development
---

# Python Skill

This skill helps with Python development.
"""
        )

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        assert result.metadata.title == "Python Skill"
        assert result.metadata.description == "Python development assistance"
        assert result.metadata.author == "Test Author"
        assert result.metadata.version == "1.0.0"
        assert "python" in result.metadata.tags
        assert "development" in result.metadata.tags

    def test_fetch_command_directory(self, tmp_path):
        """Test fetching command as a directory."""
        command_dir = tmp_path / "review"
        command_dir.mkdir()
        command_md = command_dir / "command.md"
        command_md.write_text("# Review Command")

        source = LocalSource()
        result = source.fetch(str(command_dir), ArtifactType.COMMAND)

        assert result.artifact_path == command_dir

    def test_fetch_agent_directory(self, tmp_path):
        """Test fetching agent as a directory."""
        agent_dir = tmp_path / "coder"
        agent_dir.mkdir()
        agent_md = agent_dir / "AGENT.md"
        agent_md.write_text("# Coder Agent")

        source = LocalSource()
        result = source.fetch(str(agent_dir), ArtifactType.AGENT)

        assert result.artifact_path == agent_dir
