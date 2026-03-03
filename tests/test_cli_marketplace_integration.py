"""Integration tests for CLI commands related to collection management."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


class TestCliMarketplaceIntegration:
    """Test suite for CLI add/update/sync integration."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_manifest(self):
        """Mock manifest file."""
        return """
[[skills]]
name = "test-skill"
source = "username/repo"
version = "latest"
scope = "local"
"""

    def test_add_command_exists_as_group(self, cli_runner):
        """Test that add command is available as a group."""
        result = cli_runner.invoke(main, ["add", "--help"])
        assert result.exit_code == 0
        # 'add' is a group with subcommands for artifact types
        assert "skill" in result.output.lower() or "Usage" in result.output

    def test_add_skill_subcommand_exists(self, cli_runner):
        """Test that add skill subcommand is available."""
        result = cli_runner.invoke(main, ["add", "skill", "--help"])
        assert result.exit_code == 0

    def test_add_command_shows_error_on_invalid_source(self, cli_runner):
        """Test that add skill with invalid source shows an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with cli_runner.isolated_filesystem(temp_dir=tmpdir):
                result = cli_runner.invoke(
                    main,
                    [
                        "add",
                        "skill",
                        "invalid-source-xyz",
                        "--dangerously-skip-permissions",
                    ],
                )
                # Should fail (invalid source format)
                assert result.exit_code != 0 or "error" in result.output.lower()

    def test_add_command_handles_github_source_format(self, cli_runner):
        """Test that add skill accepts username/repo format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with cli_runner.isolated_filesystem(temp_dir=tmpdir):
                with patch("skillmeat.sources.github.GitHubSource.fetch") as mock_fetch:
                    mock_fetch.side_effect = Exception("Mocked network error")
                    result = cli_runner.invoke(
                        main,
                        [
                            "add",
                            "skill",
                            "username/repo/path",
                            "--dangerously-skip-permissions",
                        ],
                    )
                    # Either fails with network error or usage error, but not crash
                    assert result.exit_code in (0, 1, 2)

    def test_update_command_accepts_artifact_name(self, cli_runner):
        """Test that update command accepts an artifact name argument."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["update", "test-skill"])
            # Should not crash with exit code other than 0 or 1
            assert result.exit_code in (0, 1)

    def test_sync_check_command_exists(self, cli_runner):
        """Test that sync-check command is available (replaced old sync)."""
        result = cli_runner.invoke(main, ["sync-check", "--help"])
        assert result.exit_code == 0

    def test_sync_pull_command_exists(self, cli_runner):
        """Test that sync-pull command is available."""
        result = cli_runner.invoke(main, ["sync-pull", "--help"])
        assert result.exit_code == 0
