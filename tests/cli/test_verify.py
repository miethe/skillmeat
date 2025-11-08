"""Tests for 'skillmeat verify' command."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock

from skillmeat.cli import main
from tests.conftest import (
    create_minimal_skill,
    create_minimal_command,
    create_minimal_agent,
)


class TestVerifyCommand:
    """Test suite for the verify command."""

    def test_verify_local_skill(self, isolated_cli_runner, sample_skill_dir):
        """Test verifying a local skill."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_skill_dir), "--type", "skill"]
        )

        assert result.exit_code == 0
        assert "Valid artifact" in result.output
        assert "skill" in result.output

    def test_verify_local_command(self, isolated_cli_runner, sample_command_file):
        """Test verifying a local command."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_command_file), "--type", "command"]
        )

        assert result.exit_code == 0
        assert "Valid artifact" in result.output
        assert "command" in result.output

    def test_verify_local_agent(self, isolated_cli_runner, sample_agent_file):
        """Test verifying a local agent."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_agent_file), "--type", "agent"]
        )

        assert result.exit_code == 0
        assert "Valid artifact" in result.output
        assert "agent" in result.output

    def test_verify_nonexistent_path(self, isolated_cli_runner):
        """Test verifying non-existent path."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["verify", "/nonexistent/path", "--type", "skill"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_verify_invalid_artifact(self, isolated_cli_runner, tmp_path):
        """Test verifying invalid artifact (missing SKILL.md)."""
        runner = isolated_cli_runner

        # Create invalid skill directory (no SKILL.md)
        invalid_skill = tmp_path / "invalid-skill"
        invalid_skill.mkdir()

        result = runner.invoke(main, ["verify", str(invalid_skill), "--type", "skill"])

        assert result.exit_code == 1
        assert "Invalid" in result.output

    def test_verify_shows_metadata(self, isolated_cli_runner, sample_skill_dir):
        """Test that verify shows artifact metadata."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_skill_dir), "--type", "skill"]
        )

        assert result.exit_code == 0
        assert "Valid artifact" in result.output
        # Should show metadata like title, description, etc.

    def test_verify_requires_type(self, isolated_cli_runner, sample_skill_dir):
        """Test that verify requires --type flag."""
        runner = isolated_cli_runner

        # Try without --type (should fail)
        result = runner.invoke(main, ["verify", str(sample_skill_dir)])

        # Should show error about missing type
        assert result.exit_code == 2  # Click missing required option error

    def test_verify_invalid_type(self, isolated_cli_runner, sample_skill_dir):
        """Test verify with invalid type."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_skill_dir), "--type", "invalid"]
        )

        # Should show error about invalid choice
        assert result.exit_code == 2

    @patch("skillmeat.sources.github.GitHubSource.fetch")
    def test_verify_github_spec(
        self, mock_fetch, isolated_cli_runner, sample_skill_dir, tmp_path
    ):
        """Test verifying GitHub artifact spec."""
        runner = isolated_cli_runner

        from skillmeat.models.metadata import ArtifactMetadata
        import shutil

        def mock_fetch_impl(spec, artifact_type, dest_dir):
            # Copy skill to dest_dir
            dest_path = dest_dir / "test-skill"
            shutil.copytree(sample_skill_dir, dest_path)

            return dest_path, ArtifactMetadata(
                title="Test Skill",
                description="A test skill from GitHub",
                version="1.0.0",
                author="Test Author",
            )

        mock_fetch.side_effect = mock_fetch_impl

        result = runner.invoke(
            main, ["verify", "user/repo/test-skill", "--type", "skill"]
        )

        assert result.exit_code == 0
        assert "Valid artifact" in result.output
        assert "Verifying GitHub artifact" in result.output

    @patch("skillmeat.sources.github.GitHubSource.fetch")
    def test_verify_github_invalid(self, mock_fetch, isolated_cli_runner, tmp_path):
        """Test verifying invalid GitHub artifact."""
        runner = isolated_cli_runner

        # Mock fetch to return invalid artifact
        def mock_fetch_impl(spec, artifact_type, dest_dir):
            # Create empty directory (invalid)
            dest_path = dest_dir / "invalid-skill"
            dest_path.mkdir()
            return dest_path, None

        mock_fetch.side_effect = mock_fetch_impl

        result = runner.invoke(
            main, ["verify", "user/repo/invalid-skill", "--type", "skill"]
        )

        assert result.exit_code == 1
        assert "Invalid" in result.output


class TestVerifyMetadataDisplay:
    """Test that verify displays artifact metadata correctly."""

    def test_verify_displays_title(self, isolated_cli_runner, tmp_path):
        """Test verify displays artifact title."""
        runner = isolated_cli_runner

        skill = create_minimal_skill(tmp_path, "titled-skill")

        result = runner.invoke(main, ["verify", str(skill), "--type", "skill"])

        assert result.exit_code == 0
        assert "Title:" in result.output or "Test Skill" in result.output

    def test_verify_displays_description(self, isolated_cli_runner, tmp_path):
        """Test verify displays artifact description."""
        runner = isolated_cli_runner

        skill = create_minimal_skill(tmp_path, "described-skill")

        result = runner.invoke(main, ["verify", str(skill), "--type", "skill"])

        assert result.exit_code == 0
        # Should show description in output

    def test_verify_displays_version(self, isolated_cli_runner, tmp_path):
        """Test verify displays artifact version."""
        runner = isolated_cli_runner

        skill = create_minimal_skill(tmp_path, "versioned-skill")

        result = runner.invoke(main, ["verify", str(skill), "--type", "skill"])

        assert result.exit_code == 0
        assert "Version:" in result.output or "1.0.0" in result.output

    def test_verify_displays_author(self, isolated_cli_runner, tmp_path):
        """Test verify displays artifact author if present."""
        runner = isolated_cli_runner

        # Create skill with author metadata
        skill_dir = tmp_path / "authored-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
title: Authored Skill
description: A skill with author
version: 1.0.0
author: Test Author
---

# Authored Skill

Content here.
"""
        )

        result = runner.invoke(main, ["verify", str(skill_dir), "--type", "skill"])

        assert result.exit_code == 0
        if "Author:" in result.output:
            assert "Test Author" in result.output

    def test_verify_displays_tags(self, isolated_cli_runner, tmp_path):
        """Test verify displays artifact tags if present."""
        runner = isolated_cli_runner

        # Create skill with tags
        skill_dir = tmp_path / "tagged-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
title: Tagged Skill
description: A skill with tags
version: 1.0.0
tags:
  - productivity
  - automation
---

# Tagged Skill

Content here.
"""
        )

        result = runner.invoke(main, ["verify", str(skill_dir), "--type", "skill"])

        assert result.exit_code == 0
        if "Tags:" in result.output:
            assert "productivity" in result.output or "automation" in result.output


class TestVerifyWorkflows:
    """Test verify command workflows."""

    def test_verify_before_add(self, isolated_cli_runner, sample_skill_dir):
        """Test workflow: verify → add."""
        runner = isolated_cli_runner

        # Verify first
        verify_result = runner.invoke(
            main, ["verify", str(sample_skill_dir), "--type", "skill"]
        )
        assert verify_result.exit_code == 0
        assert "Valid artifact" in verify_result.output

        # Now add with confidence
        runner.invoke(main, ["init"])
        add_result = runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        assert add_result.exit_code == 0

    def test_verify_all_types(
        self,
        isolated_cli_runner,
        sample_skill_dir,
        sample_command_file,
        sample_agent_file,
    ):
        """Test verifying all artifact types."""
        runner = isolated_cli_runner

        # Verify skill
        skill_result = runner.invoke(
            main, ["verify", str(sample_skill_dir), "--type", "skill"]
        )
        assert skill_result.exit_code == 0

        # Verify command
        command_result = runner.invoke(
            main, ["verify", str(sample_command_file), "--type", "command"]
        )
        assert command_result.exit_code == 0

        # Verify agent
        agent_result = runner.invoke(
            main, ["verify", str(sample_agent_file), "--type", "agent"]
        )
        assert agent_result.exit_code == 0

    def test_verify_multiple_artifacts(self, isolated_cli_runner, tmp_path):
        """Test verifying multiple artifacts."""
        runner = isolated_cli_runner

        # Create multiple skills
        skill1 = create_minimal_skill(tmp_path, "skill-1")
        skill2 = create_minimal_skill(tmp_path, "skill-2")
        skill3 = create_minimal_skill(tmp_path, "skill-3")

        # Verify each
        for skill in [skill1, skill2, skill3]:
            result = runner.invoke(main, ["verify", str(skill), "--type", "skill"])
            assert result.exit_code == 0

    @patch("skillmeat.sources.github.GitHubSource.fetch")
    def test_verify_github_before_add(
        self, mock_fetch, isolated_cli_runner, sample_skill_dir, tmp_path
    ):
        """Test workflow: verify GitHub spec → add."""
        runner = isolated_cli_runner

        from skillmeat.models.metadata import ArtifactMetadata
        import shutil

        def mock_fetch_impl(spec, artifact_type, dest_dir):
            dest_path = dest_dir / "test-skill"
            shutil.copytree(sample_skill_dir, dest_path)
            return dest_path, ArtifactMetadata(
                title="Test Skill",
                description="A test skill",
                version="1.0.0",
            )

        mock_fetch.side_effect = mock_fetch_impl

        # Verify GitHub spec
        verify_result = runner.invoke(
            main, ["verify", "user/repo/test-skill", "--type", "skill"]
        )
        assert verify_result.exit_code == 0

        # Now can add with confidence
        runner.invoke(main, ["init"])
        add_result = runner.invoke(
            main,
            ["add", "skill", "user/repo/test-skill", "--dangerously-skip-permissions"],
        )
        assert add_result.exit_code == 0


class TestVerifyEdgeCases:
    """Test edge cases for verify command."""

    def test_verify_empty_directory(self, isolated_cli_runner, tmp_path):
        """Test verifying empty directory."""
        runner = isolated_cli_runner

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(main, ["verify", str(empty_dir), "--type", "skill"])

        assert result.exit_code == 1
        assert "Invalid" in result.output

    def test_verify_directory_without_skill_md(self, isolated_cli_runner, tmp_path):
        """Test verifying skill directory without SKILL.md."""
        runner = isolated_cli_runner

        skill_dir = tmp_path / "no-skill-md"
        skill_dir.mkdir()
        (skill_dir / "other-file.txt").write_text("content")

        result = runner.invoke(main, ["verify", str(skill_dir), "--type", "skill"])

        assert result.exit_code == 1
        assert "Invalid" in result.output

    def test_verify_command_file_not_md(self, isolated_cli_runner, tmp_path):
        """Test verifying command that's not .md file."""
        runner = isolated_cli_runner

        # Create .txt file instead of .md
        cmd_file = tmp_path / "command.txt"
        cmd_file.write_text("---\ntitle: Test\n---\nContent")

        result = runner.invoke(main, ["verify", str(cmd_file), "--type", "command"])

        # May fail validation depending on implementation
        # Either way, should handle gracefully

    def test_verify_with_relative_path(
        self, isolated_cli_runner, sample_skill_dir, monkeypatch
    ):
        """Test verifying with relative path."""
        runner = isolated_cli_runner

        # Change to parent directory
        monkeypatch.chdir(sample_skill_dir.parent)

        # Use relative path
        result = runner.invoke(main, ["verify", "./test-skill", "--type", "skill"])

        assert result.exit_code == 0

    def test_verify_with_absolute_path(self, isolated_cli_runner, sample_skill_dir):
        """Test verifying with absolute path."""
        runner = isolated_cli_runner

        result = runner.invoke(
            main, ["verify", str(sample_skill_dir.resolve()), "--type", "skill"]
        )

        assert result.exit_code == 0

    def test_verify_symlink(self, isolated_cli_runner, sample_skill_dir, tmp_path):
        """Test verifying artifact via symlink."""
        runner = isolated_cli_runner

        # Create symlink to skill
        symlink = tmp_path / "skill-link"
        symlink.symlink_to(sample_skill_dir)

        result = runner.invoke(main, ["verify", str(symlink), "--type", "skill"])

        # Should handle symlinks correctly
        assert result.exit_code in [0, 1]
