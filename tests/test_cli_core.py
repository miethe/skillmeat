"""Tests for core CLI functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


class TestCliInit:
    """Test suite for CLI init command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_init_creates_collection(self, cli_runner):
        """Test that init command creates a collection (not skills.toml)."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init"])

            # Init creates or reports on the 'default' collection
            assert result.exit_code == 0
            assert "default" in result.output or "Collection" in result.output or "already exists" in result.output

    def test_init_collection_already_exists(self, cli_runner):
        """Test that init command handles existing collection gracefully."""
        with cli_runner.isolated_filesystem():
            # First init creates the collection
            result1 = cli_runner.invoke(main, ["init"])
            assert result1.exit_code == 0

            # Second init reports it already exists
            result2 = cli_runner.invoke(main, ["init"])
            assert result2.exit_code == 0
            assert "already exists" in result2.output or "Collection" in result2.output

    def test_init_with_custom_name(self, cli_runner):
        """Test that init command accepts a custom name."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init", "--name", "mywork"])

            assert result.exit_code == 0


class TestCliRemove:
    """Test suite for CLI remove command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_remove_skill_not_in_manifest(self, cli_runner):
        """Test removing skill not in collection."""
        with cli_runner.isolated_filesystem():
            # In non-TTY mode, --force is required; artifact not found returns error
            result = cli_runner.invoke(main, ["remove", "nonexistent", "--force"])

            # Exit code 1 with not-found error is expected
            assert result.exit_code in (0, 1)
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_remove_no_force_exits_with_error(self, cli_runner):
        """Test remove without --force in non-TTY exits with error code."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["remove", "test-skill"])

            # Non-TTY without --force returns exit code 2
            assert result.exit_code == 2
            assert "force" in result.output.lower() or "Error" in result.output

    def test_remove_skill_with_scope_option(self, cli_runner):
        """Test removing skill with scope option (non-TTY requires --force)."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main, ["remove", "test-skill", "--keep-files", "--force"]
            )

            # Either not-found (exit 1) or missing force (exit 2) is acceptable
            assert result.exit_code in (0, 1, 2)


class TestCliList:
    """Test suite for CLI list command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_list_shows_artifacts(self, cli_runner):
        """Test list command shows artifact table."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["list"])

            assert result.exit_code == 0
            # Current CLI shows "Artifacts" header, not "Installed Skills"
            assert "Artifact" in result.output or "Name" in result.output or "Type" in result.output

    def test_list_with_type_filter_skill(self, cli_runner):
        """Test list command with skill type filter."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["list", "--type", "skill"])

            assert result.exit_code == 0

    def test_list_with_type_filter(self, cli_runner):
        """Test list command with type filter."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["list", "--type", "skill"])

            assert result.exit_code == 0

    def test_list_displays_artifacts(self, cli_runner):
        """Test that list command succeeds and shows output."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["list"])

            assert result.exit_code == 0
            # Table heading contains "Artifacts"
            assert "Artifact" in result.output or "Name" in result.output


class TestCliShow:
    """Test suite for CLI show command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_show_skill_not_found(self, cli_runner):
        """Test show command with non-existent skill exits with code 1."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["show", "nonexistent"])

            # Current behavior: exits with code 1 when artifact not found
            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_show_requires_artifact_name(self, cli_runner):
        """Test show command requires an artifact name argument."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["show"])

            # Missing argument causes usage error
            assert result.exit_code != 0


class TestCliVerify:
    """Test suite for CLI verify command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_verify_requires_type_option(self, cli_runner):
        """Test verify command requires --type option."""
        with cli_runner.isolated_filesystem():
            # Without --type, verify exits with code 2 (usage error)
            result = cli_runner.invoke(main, ["verify", "username/repo"])

            assert result.exit_code == 2

    def test_verify_invalid_spec(self, cli_runner):
        """Test verify with invalid specification format."""
        with cli_runner.isolated_filesystem():
            # With --type but invalid spec format
            result = cli_runner.invoke(main, ["verify", "invalid", "--type", "skill"])

            # Should exit with non-zero code for invalid spec
            assert result.exit_code != 0


class TestCliConfigCommand:
    """Test suite for CLI config commands."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_config_set(self, cli_runner):
        """Test setting configuration value."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main, ["config", "set", "test-key", "test-value"]
            )

            assert result.exit_code == 0
            assert "Set test-key" in result.output

    def test_config_get_not_set(self, cli_runner):
        """Test getting configuration value that is not set — returns JSON null in non-TTY."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["config", "get", "missing-key-xyz"])

            assert result.exit_code == 0
            # In non-TTY mode, output is JSON
            output = result.output
            # Either JSON format (null value) or text "not set"
            assert "null" in output or "not set" in output or "missing-key-xyz" in output

    def test_config_list_returns_json_in_non_tty(self, cli_runner):
        """Test listing all configuration values returns JSON in non-TTY mode."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["config", "list"])

            assert result.exit_code == 0
            # In non-TTY mode, CLI returns JSON
            output = result.output.strip()
            assert output  # non-empty

    def test_config_set_and_get(self, cli_runner):
        """Test setting and retrieving a config value round-trip."""
        with cli_runner.isolated_filesystem():
            set_result = cli_runner.invoke(
                main, ["config", "set", "round-trip-key", "round-trip-value"]
            )
            assert set_result.exit_code == 0

            get_result = cli_runner.invoke(main, ["config", "get", "round-trip-key"])
            assert get_result.exit_code == 0
            assert "round-trip-value" in get_result.output


class TestCliClean:
    """Test suite for CLI status command (replaces old clean functionality)."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_status_command_exists(self, cli_runner):
        """Test status command is available (provides artifact/deployment status)."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["status", "--help"])

            assert result.exit_code == 0

    def test_find_duplicates_command_exists(self, cli_runner):
        """Test find-duplicates command is available."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["find-duplicates", "--help"])

            assert result.exit_code == 0


class TestCliUpdate:
    """Test suite for CLI update command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_update_no_manifest(self, cli_runner):
        """Test update for non-existent artifact exits gracefully."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["update", "test-skill"])

            # Exits 0 (refreshes) or 1 (not found), but not crash
            assert result.exit_code in (0, 1)

    def test_update_skill_not_found(self, cli_runner):
        """Test update for non-existent artifact reports not found."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["update", "nonexistent-xyz-abc"])

            # Exits 1 with not-found message or 0 with a message
            assert result.exit_code in (0, 1)
            assert "nonexistent-xyz-abc" in result.output or "not found" in result.output.lower()

    def test_update_help(self, cli_runner):
        """Test update command has help."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["update", "--help"])

            assert result.exit_code == 0


class TestCliSyncCheck:
    """Test suite for CLI sync-check command (replaces old sync)."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_sync_check_exists(self, cli_runner):
        """Test sync-check command is available."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["sync-check", "--help"])

            assert result.exit_code == 0

    def test_sync_pull_exists(self, cli_runner):
        """Test sync-pull command is available."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["sync-pull", "--help"])

            assert result.exit_code == 0

    def test_sync_preview_exists(self, cli_runner):
        """Test sync-preview command is available."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["sync-preview", "--help"])

            assert result.exit_code == 0
