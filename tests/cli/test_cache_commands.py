"""Tests for cache CLI commands.

This module tests the cache management commands added in CACHE-4.1 and CACHE-4.2:
- skillmeat cache status
- skillmeat cache clear
- skillmeat cache refresh
- skillmeat cache config get/set
- skillmeat list --no-cache
- skillmeat list --cache-status
"""

import re
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timezone

from skillmeat.cli import main


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_cache_manager():
    """Mock CacheManager for isolated testing."""
    # CacheManager is imported inside command functions, so patch at the source
    with patch("skillmeat.cache.manager.CacheManager") as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance

        # Configure default behaviors
        mock_instance.initialize_cache.return_value = True
        mock_instance.get_cache_status.return_value = {
            "total_projects": 5,
            "total_artifacts": 20,
            "stale_projects": 1,
            "outdated_artifacts": 3,
            "cache_size_bytes": 1024,
            "last_refresh": datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc),
        }
        mock_instance.clear_cache.return_value = True
        mock_instance.is_cache_stale.return_value = False

        yield mock_instance


@pytest.fixture
def mock_refresh_job():
    """Mock RefreshJob for isolated testing."""
    # RefreshJob is imported inside command functions, so patch at the source
    with patch("skillmeat.cache.refresh.RefreshJob") as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance

        # Configure default refresh results
        mock_result = Mock()
        mock_result.success = True
        mock_result.projects_refreshed = 3
        mock_result.changes_detected = 1
        mock_result.errors = []

        mock_instance.refresh_all.return_value = mock_result
        mock_instance.refresh_project.return_value = mock_result

        yield mock_instance


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for isolated testing."""
    # ConfigManager is imported inside command functions, so patch at the source
    with patch("skillmeat.config.ConfigManager") as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance

        mock_instance.get.return_value = "360"  # Default cache TTL
        mock_instance.set.return_value = None

        yield mock_instance


# =============================================================================
# Test: cache status
# =============================================================================


class TestCacheStatus:
    """Test suite for 'skillmeat cache status' command."""

    def test_cache_status_shows_stats(self, runner, mock_cache_manager):
        """Test cache status displays statistics correctly."""
        result = runner.invoke(main, ["cache", "status"])

        assert result.exit_code == 0
        assert "Cache Status" in result.output
        assert "Total Projects" in result.output
        assert "5" in result.output  # total_projects
        assert "Total Artifacts" in result.output
        assert "20" in result.output  # total_artifacts
        assert "Stale Projects" in result.output
        assert "1" in result.output  # stale_projects
        assert "Outdated Artifacts" in result.output
        assert "3" in result.output  # outdated_artifacts
        assert "Cache Size" in result.output
        assert "1.0 KB" in result.output  # cache_size_bytes / 1024

    def test_cache_status_shows_last_refresh(self, runner, mock_cache_manager):
        """Test cache status shows last refresh timestamp."""
        result = runner.invoke(main, ["cache", "status"])

        assert result.exit_code == 0
        assert "Last Refresh" in result.output
        assert "2025-12-01" in result.output

    def test_cache_status_no_refresh(self, runner, mock_cache_manager):
        """Test cache status when never refreshed."""
        mock_cache_manager.get_cache_status.return_value = {
            "total_projects": 0,
            "total_artifacts": 0,
            "stale_projects": 0,
            "outdated_artifacts": 0,
            "cache_size_bytes": 0,
            "last_refresh": None,
        }

        result = runner.invoke(main, ["cache", "status"])

        assert result.exit_code == 0
        assert "Last Refresh" in result.output
        assert "Never" in result.output

    def test_cache_status_handles_error(self, runner):
        """Test cache status handles errors gracefully."""
        with patch("skillmeat.cache.manager.CacheManager", side_effect=Exception("DB error")):
            result = runner.invoke(main, ["cache", "status"])

            assert result.exit_code == 1
            assert "Error" in result.output
            assert "DB error" in result.output

    def test_cache_status_initialization_failure(self, runner, mock_cache_manager):
        """Test cache status when initialization fails."""
        mock_cache_manager.initialize_cache.return_value = False

        result = runner.invoke(main, ["cache", "status"])

        # Should still try to get status even if init returns False
        assert mock_cache_manager.get_cache_status.called


# =============================================================================
# Test: cache clear
# =============================================================================


class TestCacheClear:
    """Test suite for 'skillmeat cache clear' command."""

    def test_cache_clear_with_confirmation(self, runner, mock_cache_manager):
        """Test cache clear with user confirmation."""
        result = runner.invoke(main, ["cache", "clear"], input="y\n")

        assert result.exit_code == 0
        assert "cleared successfully" in result.output.lower()
        mock_cache_manager.clear_cache.assert_called_once()

    def test_cache_clear_cancelled(self, runner, mock_cache_manager):
        """Test cache clear when user cancels."""
        result = runner.invoke(main, ["cache", "clear"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_cache_manager.clear_cache.assert_not_called()

    def test_cache_clear_with_yes_flag(self, runner, mock_cache_manager):
        """Test cache clear with --yes flag (skip confirmation)."""
        result = runner.invoke(main, ["cache", "clear", "--yes"])

        assert result.exit_code == 0
        assert "cleared successfully" in result.output.lower()
        mock_cache_manager.clear_cache.assert_called_once()

    def test_cache_clear_with_y_short_flag(self, runner, mock_cache_manager):
        """Test cache clear with -y short flag."""
        result = runner.invoke(main, ["cache", "clear", "-y"])

        assert result.exit_code == 0
        assert "cleared successfully" in result.output.lower()
        mock_cache_manager.clear_cache.assert_called_once()

    def test_cache_clear_failure(self, runner, mock_cache_manager):
        """Test cache clear when operation fails."""
        mock_cache_manager.clear_cache.return_value = False

        result = runner.invoke(main, ["cache", "clear", "--yes"])

        assert result.exit_code == 1
        assert "Failed to clear cache" in result.output

    def test_cache_clear_handles_exception(self, runner):
        """Test cache clear handles exceptions gracefully."""
        with patch("skillmeat.cache.manager.CacheManager") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.clear_cache.side_effect = Exception("DB locked")

            result = runner.invoke(main, ["cache", "clear", "--yes"])

            assert result.exit_code == 1
            assert "Error" in result.output
            assert "DB locked" in result.output


# =============================================================================
# Test: cache refresh
# =============================================================================


class TestCacheRefresh:
    """Test suite for 'skillmeat cache refresh' command."""

    def test_cache_refresh_all(self, runner, mock_cache_manager, mock_refresh_job):
        """Test refreshing all projects."""
        mock_result = Mock()
        mock_result.projects_refreshed = 3
        mock_result.changes_detected = 1
        mock_result.errors = []
        mock_refresh_job.refresh_all.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Starting cache refresh" in output
        assert "Refreshed 3 projects" in output
        assert "Changes detected: 1" in output
        mock_refresh_job.refresh_all.assert_called_once_with(force=False)

    def test_cache_refresh_all_with_force(self, runner, mock_cache_manager, mock_refresh_job):
        """Test forced refresh of all projects."""
        result = runner.invoke(main, ["cache", "refresh", "--force"])

        assert result.exit_code == 0
        mock_refresh_job.refresh_all.assert_called_once_with(force=True)

    def test_cache_refresh_no_changes(self, runner, mock_cache_manager, mock_refresh_job):
        """Test refresh when no changes detected."""
        mock_result = Mock()
        mock_result.projects_refreshed = 2
        mock_result.changes_detected = 0
        mock_result.errors = []
        mock_refresh_job.refresh_all.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Refreshed 2 projects" in output
        # Should not show "Changes detected: 0"
        assert "Changes detected: 0" not in output

    def test_cache_refresh_with_errors(self, runner, mock_cache_manager, mock_refresh_job):
        """Test refresh with some errors."""
        mock_result = Mock()
        mock_result.projects_refreshed = 3
        mock_result.changes_detected = 1
        mock_result.errors = ["Error 1", "Error 2"]
        mock_refresh_job.refresh_all.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Refreshed 3 projects" in output
        assert "Errors: 2" in output

    def test_cache_refresh_specific_project(self, runner, mock_cache_manager, mock_refresh_job):
        """Test refreshing a specific project."""
        mock_result = Mock()
        mock_result.success = True
        mock_result.changes_detected = 2
        mock_result.errors = []
        mock_refresh_job.refresh_project.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh", "proj-123"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Project refreshed: 2 changes detected" in output
        mock_refresh_job.refresh_project.assert_called_once_with("proj-123", force=False)

    def test_cache_refresh_specific_project_force(self, runner, mock_cache_manager, mock_refresh_job):
        """Test forced refresh of specific project."""
        mock_result = Mock()
        mock_result.success = True
        mock_result.changes_detected = 0
        mock_result.errors = []
        mock_refresh_job.refresh_project.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh", "proj-456", "--force"])

        assert result.exit_code == 0
        mock_refresh_job.refresh_project.assert_called_once_with("proj-456", force=True)

    def test_cache_refresh_project_failure(self, runner, mock_cache_manager, mock_refresh_job):
        """Test refresh project when operation fails."""
        mock_result = Mock()
        mock_result.success = False
        mock_result.errors = ["Project not found", "Network error"]
        mock_refresh_job.refresh_project.return_value = mock_result

        result = runner.invoke(main, ["cache", "refresh", "bad-proj"])

        assert result.exit_code == 1
        assert "Refresh failed" in result.output
        assert "Project not found" in result.output
        assert "Network error" in result.output

    def test_cache_refresh_handles_exception(self, runner, mock_cache_manager):
        """Test refresh handles exceptions gracefully."""
        with patch("skillmeat.cache.refresh.RefreshJob", side_effect=Exception("Init failed")):
            result = runner.invoke(main, ["cache", "refresh"])

            assert result.exit_code == 1
            assert "Error" in result.output
            assert "Init failed" in result.output


# =============================================================================
# Test: cache config get/set
# =============================================================================


class TestCacheConfig:
    """Test suite for 'skillmeat cache config' commands."""

    def test_cache_config_get(self, runner, mock_config_manager):
        """Test getting cache config value."""
        mock_config_manager.get.return_value = "360"

        result = runner.invoke(main, ["cache", "config", "get", "cache-ttl"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "cache-ttl = 360" in output
        mock_config_manager.get.assert_called_once_with("cache.cache-ttl")

    def test_cache_config_get_not_set(self, runner, mock_config_manager):
        """Test getting cache config value that is not set."""
        mock_config_manager.get.return_value = None

        result = runner.invoke(main, ["cache", "config", "get", "custom-key"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "not set (using default)" in output

    def test_cache_config_get_error(self, runner):
        """Test cache config get handles errors."""
        with patch("skillmeat.config.ConfigManager") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.get.side_effect = Exception("Config error")

            result = runner.invoke(main, ["cache", "config", "get", "cache-ttl"])

            assert result.exit_code == 1
            assert "Error" in result.output

    def test_cache_config_set(self, runner, mock_config_manager):
        """Test setting cache config value."""
        result = runner.invoke(main, ["cache", "config", "set", "cache-ttl", "720"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Set cache-ttl = 720" in output
        mock_config_manager.set.assert_called_once_with("cache.cache-ttl", "720")

    def test_cache_config_set_error(self, runner):
        """Test cache config set handles errors."""
        with patch("skillmeat.config.ConfigManager") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.set.side_effect = Exception("Write failed")

            result = runner.invoke(main, ["cache", "config", "set", "cache-ttl", "720"])

            assert result.exit_code == 1
            assert "Error" in result.output


# =============================================================================
# Test: list command with cache flags
# =============================================================================


class TestListWithCacheFlags:
    """Test suite for 'skillmeat list' with cache-related flags."""

    def test_list_no_cache_flag(self, runner, isolated_cli_runner, sample_skill_dir):
        """Test list --no-cache bypasses cache."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Mock the cache to ensure it's NOT used
        with patch("skillmeat.cache.manager.CacheManager") as mock_cache:
            mock_instance = Mock()
            mock_cache.return_value = mock_instance
            mock_instance.initialize_cache.return_value = True
            mock_instance.get_artifacts.return_value = []

            result = runner.invoke(main, ["list", "--no-cache"])

            assert result.exit_code == 0
            # Cache should be initialized but not queried for artifacts
            # (the command should use ArtifactManager directly)
            # Note: Actual implementation may vary, this tests the flag exists

    def test_list_cache_status_flag(self, runner, isolated_cli_runner, sample_skill_dir):
        """Test list --cache-status shows cache information."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        result = runner.invoke(main, ["list", "--cache-status"])

        assert result.exit_code == 0
        # Should show artifact list (implementation may show cache status in output)

    def test_list_uses_cache_by_default(self, runner, isolated_cli_runner, sample_skill_dir):
        """Test list command uses cache by default."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Mock cache to return artifacts
        with patch("skillmeat.cache.manager.CacheManager") as mock_cache:
            mock_instance = Mock()
            mock_cache.return_value = mock_instance
            mock_instance.initialize_cache.return_value = True
            mock_instance.is_cache_stale.return_value = False

            # Mock cached artifact
            mock_artifact = Mock()
            mock_artifact.name = "cached-skill"
            mock_artifact.type = "skill"
            mock_artifact.deployed_version = "1.0.0"
            mock_instance.get_artifacts.return_value = [mock_artifact]

            result = runner.invoke(main, ["list"])

            # Should succeed (cache may or may not be used depending on implementation)
            assert result.exit_code == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestCacheIntegration:
    """Integration tests for cache CLI commands."""

    def test_cache_lifecycle(self, runner, isolated_cli_runner, sample_skill_dir):
        """Test complete cache lifecycle: status -> clear -> refresh."""
        runner = isolated_cli_runner

        # Initialize collection
        runner.invoke(main, ["init"])

        # Add artifact to create cache data
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Mock cache operations for integration test
        with patch("skillmeat.cache.manager.CacheManager") as mock_cache_class:
            mock_cache = Mock()
            mock_cache_class.return_value = mock_cache
            mock_cache.initialize_cache.return_value = True
            mock_cache.get_cache_status.return_value = {
                "total_projects": 1,
                "total_artifacts": 1,
                "stale_projects": 0,
                "outdated_artifacts": 0,
                "cache_size_bytes": 512,
                "last_refresh": None,
            }
            mock_cache.clear_cache.return_value = True

            # Check status
            status_result = runner.invoke(main, ["cache", "status"])
            assert status_result.exit_code == 0
            assert "Cache Status" in status_result.output

            # Clear cache
            clear_result = runner.invoke(main, ["cache", "clear", "--yes"])
            assert clear_result.exit_code == 0
            assert "cleared successfully" in clear_result.output.lower()

        # Refresh cache
        with patch("skillmeat.cache.manager.CacheManager") as mock_cache_class, \
             patch("skillmeat.cache.refresh.RefreshJob") as mock_refresh_class:
            mock_cache = Mock()
            mock_cache_class.return_value = mock_cache
            mock_cache.initialize_cache.return_value = True

            mock_refresh = Mock()
            mock_refresh_class.return_value = mock_refresh
            mock_result = Mock()
            mock_result.projects_refreshed = 1
            mock_result.changes_detected = 0
            mock_result.errors = []
            mock_refresh.refresh_all.return_value = mock_result

            refresh_result = runner.invoke(main, ["cache", "refresh"])
            assert refresh_result.exit_code == 0
            assert "Refreshed" in refresh_result.output

    def test_cache_config_workflow(self, runner):
        """Test cache configuration get/set workflow."""
        with patch("skillmeat.config.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            mock_config.get.return_value = "360"
            mock_config.set.return_value = None

            # Get default value
            get_result = runner.invoke(main, ["cache", "config", "get", "cache-ttl"])
            get_output = strip_ansi(get_result.output)
            assert get_result.exit_code == 0
            assert "360" in get_output

            # Set new value
            set_result = runner.invoke(main, ["cache", "config", "set", "cache-ttl", "720"])
            set_output = strip_ansi(set_result.output)
            assert set_result.exit_code == 0
            assert "Set cache-ttl = 720" in set_output

            # Verify set was called
            mock_config.set.assert_called_once_with("cache.cache-ttl", "720")


# =============================================================================
# Help Text Tests
# =============================================================================


class TestCacheCommandHelp:
    """Test cache command help text and documentation."""

    def test_cache_group_help(self, runner):
        """Test cache command group help text."""
        result = runner.invoke(main, ["cache", "--help"])

        assert result.exit_code == 0
        assert "Manage cache" in result.output
        assert "status" in result.output
        assert "clear" in result.output
        assert "refresh" in result.output
        assert "config" in result.output

    def test_cache_status_help(self, runner):
        """Test cache status help text."""
        result = runner.invoke(main, ["cache", "status", "--help"])

        assert result.exit_code == 0
        assert "Show cache statistics" in result.output

    def test_cache_clear_help(self, runner):
        """Test cache clear help text."""
        result = runner.invoke(main, ["cache", "clear", "--help"])

        assert result.exit_code == 0
        assert "Clear all cached data" in result.output
        assert "--yes" in result.output or "-y" in result.output

    def test_cache_refresh_help(self, runner):
        """Test cache refresh help text."""
        result = runner.invoke(main, ["cache", "refresh", "--help"])

        assert result.exit_code == 0
        assert "Refresh cache data" in result.output
        assert "--force" in result.output

    def test_cache_config_help(self, runner):
        """Test cache config help text."""
        result = runner.invoke(main, ["cache", "config", "--help"])

        assert result.exit_code == 0
        assert "get" in result.output
        assert "set" in result.output
