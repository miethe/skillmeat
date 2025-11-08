"""Tests for 'skillmeat add' commands (skill, command, agent)."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock

from skillmeat.cli import main
from tests.conftest import create_minimal_skill, create_minimal_command, create_minimal_agent


class TestAddSkillCommand:
    """Test suite for 'skillmeat add skill' command."""

    def test_add_skill_from_local_path(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill from local path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add skill with permission skip
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added skill: test-skill" in result.output

        # Verify it appears in list
        list_result = runner.invoke(main, ['list'])
        assert "test-skill" in list_result.output

    def test_add_skill_with_custom_name(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill with custom name override."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--name', 'custom-skill', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added skill: custom-skill" in result.output

        # Verify custom name in list
        list_result = runner.invoke(main, ['list'])
        assert "custom-skill" in list_result.output

    def test_add_skill_with_short_flags(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill with short flags -n and -f."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add with short flags
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '-n', 'short-name', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added skill: short-name" in result.output

    def test_add_skill_force_overwrite(self, isolated_cli_runner, sample_skill_dir):
        """Test force overwriting existing skill."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add skill first time
        result1 = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions']
        )
        assert result1.exit_code == 0

        # Try to add again without force (should fail)
        result2 = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions']
        )
        assert result2.exit_code == 1

        # Add with force flag
        result3 = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '-f', '--dangerously-skip-permissions']
        )
        assert result3.exit_code == 0

    def test_add_skill_security_warning(self, isolated_cli_runner, sample_skill_dir):
        """Test that security warning is shown without skip flag."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add without skip flag, answer 'n' to confirmation
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir)],
            input='n\n'
        )

        assert "Security warning" in result.output
        assert "execute code" in result.output
        assert "Cancelled" in result.output

    def test_add_skill_security_warning_accepted(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill after accepting security warning."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add without skip flag, answer 'y' to confirmation
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir)],
            input='y\n'
        )

        assert "Security warning" in result.output
        assert result.exit_code == 0
        assert "Added skill" in result.output

    def test_add_skill_invalid_path(self, isolated_cli_runner):
        """Test adding skill from non-existent path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'skill', '/nonexistent/path', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_add_skill_no_verify(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill with validation skipped."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--no-verify', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0

    @patch('skillmeat.sources.github.GitHubSource.fetch')
    def test_add_skill_from_github(self, mock_fetch, isolated_cli_runner, sample_skill_dir, tmp_path):
        """Test adding skill from GitHub spec."""
        runner = isolated_cli_runner

        # Mock GitHub fetch to return local fixture
        from skillmeat.models.metadata import ArtifactMetadata

        def mock_fetch_impl(spec, artifact_type, dest_dir):
            # Copy skill to dest_dir
            import shutil
            dest_path = dest_dir / "test-skill"
            shutil.copytree(sample_skill_dir, dest_path)

            return dest_path, ArtifactMetadata(
                title="Test Skill",
                description="A test skill",
                version="1.0.0",
            )

        mock_fetch.side_effect = mock_fetch_impl

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'skill', 'user/repo/test-skill', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Fetching from GitHub" in result.output
        assert "Added skill" in result.output

    def test_add_skill_to_custom_collection(self, isolated_cli_runner, sample_skill_dir):
        """Test adding skill to non-default collection."""
        runner = isolated_cli_runner

        # Create custom collection
        runner.invoke(main, ['init', '--name', 'work'])

        # Add skill to specific collection
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--collection', 'work', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0

        # Verify in correct collection
        list_result = runner.invoke(main, ['list', '--collection', 'work'])
        assert "test-skill" in list_result.output


class TestAddCommandCommand:
    """Test suite for 'skillmeat add command' command."""

    def test_add_command_from_local_path(self, isolated_cli_runner, sample_command_file):
        """Test adding command from local path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'command', str(sample_command_file), '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added command" in result.output

    def test_add_command_with_custom_name(self, isolated_cli_runner, sample_command_file):
        """Test adding command with custom name."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'command', str(sample_command_file), '--name', 'my-command', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added command: my-command" in result.output

    def test_add_command_invalid_path(self, isolated_cli_runner):
        """Test adding command from non-existent path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'command', '/nonexistent/command.md', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch('skillmeat.sources.github.GitHubSource.fetch')
    def test_add_command_from_github(self, mock_fetch, isolated_cli_runner, sample_command_file, tmp_path):
        """Test adding command from GitHub spec."""
        runner = isolated_cli_runner

        from skillmeat.models.metadata import ArtifactMetadata
        import shutil

        def mock_fetch_impl(spec, artifact_type, dest_dir):
            dest_path = dest_dir / "test-command.md"
            shutil.copy2(sample_command_file, dest_path)

            return dest_path, ArtifactMetadata(
                title="Test Command",
                description="A test command",
                version="1.0.0",
            )

        mock_fetch.side_effect = mock_fetch_impl

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'command', 'user/repo/test-command.md', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Fetching from GitHub" in result.output


class TestAddAgentCommand:
    """Test suite for 'skillmeat add agent' command."""

    def test_add_agent_from_local_path(self, isolated_cli_runner, sample_agent_file):
        """Test adding agent from local path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'agent', str(sample_agent_file), '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added agent" in result.output

    def test_add_agent_with_custom_name(self, isolated_cli_runner, sample_agent_file):
        """Test adding agent with custom name."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'agent', str(sample_agent_file), '--name', 'my-agent', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Added agent: my-agent" in result.output

    def test_add_agent_invalid_path(self, isolated_cli_runner):
        """Test adding agent from non-existent path."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'agent', '/nonexistent/agent.md', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch('skillmeat.sources.github.GitHubSource.fetch')
    def test_add_agent_from_github(self, mock_fetch, isolated_cli_runner, sample_agent_file, tmp_path):
        """Test adding agent from GitHub spec."""
        runner = isolated_cli_runner

        from skillmeat.models.metadata import ArtifactMetadata
        import shutil

        def mock_fetch_impl(spec, artifact_type, dest_dir):
            dest_path = dest_dir / "test-agent.md"
            shutil.copy2(sample_agent_file, dest_path)

            return dest_path, ArtifactMetadata(
                title="Test Agent",
                description="A test agent",
                version="1.0.0",
            )

        mock_fetch.side_effect = mock_fetch_impl

        runner.invoke(main, ['init'])

        result = runner.invoke(
            main,
            ['add', 'agent', 'user/repo/test-agent.md', '--dangerously-skip-permissions']
        )

        assert result.exit_code == 0
        assert "Fetching from GitHub" in result.output


class TestAddCommandEdgeCases:
    """Test edge cases for add commands."""

    def test_add_without_init(self, isolated_cli_runner, sample_skill_dir):
        """Test adding artifact without initializing collection first."""
        runner = isolated_cli_runner

        # Try to add without init - should auto-init or fail gracefully
        result = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions']
        )

        # Should either auto-initialize or show helpful error
        # Current implementation might create default collection automatically
        assert result.exit_code in [0, 1]

    def test_add_multiple_artifacts_same_session(self, isolated_cli_runner, sample_skill_dir, sample_command_file):
        """Test adding multiple artifacts in the same session."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add skill
        result1 = runner.invoke(
            main,
            ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions']
        )
        assert result1.exit_code == 0

        # Add command
        result2 = runner.invoke(
            main,
            ['add', 'command', str(sample_command_file), '--dangerously-skip-permissions']
        )
        assert result2.exit_code == 0

        # Verify both in list
        list_result = runner.invoke(main, ['list'])
        assert "test-skill" in list_result.output
        assert "test-command" in list_result.output

    def test_add_all_artifact_types(self, isolated_cli_runner, sample_skill_dir, sample_command_file, sample_agent_file):
        """Test adding all three artifact types."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        # Add all three types
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])
        runner.invoke(main, ['add', 'command', str(sample_command_file), '--dangerously-skip-permissions'])
        runner.invoke(main, ['add', 'agent', str(sample_agent_file), '--dangerously-skip-permissions'])

        # Verify all in list
        list_result = runner.invoke(main, ['list'])
        assert "test-skill" in list_result.output
        assert "test-command" in list_result.output
        assert "test-agent" in list_result.output
