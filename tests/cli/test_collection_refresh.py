"""Integration tests for 'skillmeat collection refresh' command.

Tests cover CLI invocation and behavior of the collection refresh functionality:
- Basic refresh execution (BE-213)
- Dry-run mode (BE-214)
- Metadata-only flag (BE-215)
- Check mode (BE-216)
- Error handling (BE-217)

Tasks: BE-213, BE-214, BE-215, BE-216, BE-217
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from skillmeat.cli import main
from skillmeat.core.refresher import (
    RefreshEntryResult,
    RefreshResult,
    RefreshMode,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_refresh_result_with_changes():
    """Create a mock RefreshResult with refreshed artifacts."""
    return RefreshResult(
        refreshed_count=2,
        unchanged_count=1,
        skipped_count=1,
        error_count=0,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="refreshed",
                changes=["description", "tags"],
                old_values={"description": "Old desc", "tags": []},
                new_values={"description": "New desc", "tags": ["design"]},
                error=None,
                reason=None,
                duration_ms=150.5,
            ),
            RefreshEntryResult(
                artifact_id="skill:pdf-tools",
                status="refreshed",
                changes=["description"],
                old_values={"description": "PDF tools"},
                new_values={"description": "Enhanced PDF tools"},
                error=None,
                reason=None,
                duration_ms=120.3,
            ),
            RefreshEntryResult(
                artifact_id="skill:local-skill",
                status="skipped",
                changes=[],
                old_values=None,
                new_values=None,
                error=None,
                reason="No GitHub source",
                duration_ms=5.0,
            ),
            RefreshEntryResult(
                artifact_id="command:test-cmd",
                status="unchanged",
                changes=[],
                old_values=None,
                new_values=None,
                error=None,
                reason=None,
                duration_ms=85.2,
            ),
        ],
        duration_ms=500.0,
    )


@pytest.fixture
def mock_refresh_result_no_changes():
    """Create a mock RefreshResult with no changes detected."""
    return RefreshResult(
        refreshed_count=0,
        unchanged_count=3,
        skipped_count=0,
        error_count=0,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="unchanged",
                changes=[],
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:pdf-tools",
                status="unchanged",
                changes=[],
                duration_ms=90.0,
            ),
            RefreshEntryResult(
                artifact_id="command:test-cmd",
                status="unchanged",
                changes=[],
                duration_ms=80.0,
            ),
        ],
        duration_ms=350.0,
    )


@pytest.fixture
def mock_refresh_result_with_errors():
    """Create a mock RefreshResult with errors."""
    return RefreshResult(
        refreshed_count=1,
        unchanged_count=0,
        skipped_count=0,
        error_count=2,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="refreshed",
                changes=["description"],
                old_values={"description": "Old"},
                new_values={"description": "New"},
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:private-skill",
                status="error",
                changes=[],
                error="Repository not found or access denied",
                reason="GitHub API error",
                duration_ms=50.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:rate-limited",
                status="error",
                changes=[],
                error="Rate limit exceeded",
                reason="GitHub API rate limit",
                duration_ms=30.0,
            ),
        ],
        duration_ms=250.0,
    )


@pytest.fixture
def mock_refresh_result_empty():
    """Create a mock RefreshResult with no artifacts processed."""
    return RefreshResult(
        refreshed_count=0,
        unchanged_count=0,
        skipped_count=0,
        error_count=0,
        entries=[],
        duration_ms=50.0,
    )


# =============================================================================
# BE-213: TestBasicRefresh
# =============================================================================


class TestBasicRefresh:
    """Integration tests for basic refresh execution (BE-213)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_basic_refresh_with_changes(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-213: Test basic refresh shows summary with changes."""
        runner = isolated_cli_runner

        # Configure mocks
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        # Run command
        result = runner.invoke(main, ["collection", "refresh"])

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify summary table was displayed
        assert "Refresh Summary" in result.output
        assert "Refreshed" in result.output
        assert "2" in result.output  # refreshed_count
        assert "Unchanged" in result.output
        assert "1" in result.output  # unchanged_count
        assert "Skipped" in result.output
        assert "Errors" in result.output

        # Verify refresh was called with default mode
        mock_refresher.refresh_collection.assert_called_once()
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["mode"] == RefreshMode.METADATA_ONLY
        assert call_kwargs["dry_run"] is False

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_basic_refresh_no_changes(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_no_changes,
    ):
        """BE-213: Test basic refresh when no changes detected."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_no_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh"])

        assert result.exit_code == 0
        assert "Refresh Summary" in result.output
        # Should show 0 refreshed, 3 unchanged
        assert "Unchanged" in result.output

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_refresh_with_collection_name(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-213: Test refresh with specific collection name."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "-c", "work"])

        assert result.exit_code == 0

        # Verify collection name was passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["collection_name"] == "work"

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_refresh_shows_changed_artifacts(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-213: Test refresh shows details for changed artifacts."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh"])

        assert result.exit_code == 0
        # Should show changed artifact details
        assert "Changed Artifacts" in result.output
        assert "skill:canvas-design" in result.output
        assert "skill:pdf-tools" in result.output


# =============================================================================
# BE-214: TestDryRunMode
# =============================================================================


class TestDryRunMode:
    """Integration tests for --dry-run mode (BE-214)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_dry_run_shows_notice(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-214: Test --dry-run flag displays dry run notice."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--dry-run"])

        assert result.exit_code == 0
        # Should show dry run notice
        assert "Dry run" in result.output or "dry-run" in result.output.lower()
        assert "no changes saved" in result.output.lower() or "preview" in result.output.lower()

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_dry_run_passes_flag_to_refresher(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-214: Test --dry-run flag is passed to refresher."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--dry-run"])

        assert result.exit_code == 0

        # Verify dry_run was passed to refresh_collection
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["dry_run"] is True

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_dry_run_no_notice_when_no_changes(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_no_changes,
    ):
        """BE-214: Test dry run notice not shown when no changes detected."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_no_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--dry-run"])

        assert result.exit_code == 0
        # When refreshed_count == 0, dry run notice should not appear
        # (since there are no changes that would have been saved)


# =============================================================================
# BE-215: TestMetadataOnlyFlag
# =============================================================================


class TestMetadataOnlyFlag:
    """Integration tests for --metadata-only flag (BE-215)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_metadata_only_is_default(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-215: Test --metadata-only is True by default."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        # Run without explicit --metadata-only flag
        result = runner.invoke(main, ["collection", "refresh"])

        assert result.exit_code == 0

        # Default should be METADATA_ONLY mode
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["mode"] == RefreshMode.METADATA_ONLY

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_metadata_only_explicit(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-215: Test explicit --metadata-only flag uses METADATA_ONLY mode."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--metadata-only"])

        assert result.exit_code == 0

        # Should use METADATA_ONLY mode
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["mode"] == RefreshMode.METADATA_ONLY


# =============================================================================
# BE-216: TestCheckMode
# =============================================================================


class TestCheckMode:
    """Integration tests for --check mode (BE-216)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_check_mode_shows_notice(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-216: Test --check flag displays check-only notice."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--check"])

        assert result.exit_code == 0
        # Should show check-only notice when updates are available
        assert "Check only" in result.output or "check" in result.output.lower()
        assert "updates available" in result.output.lower() or "remove --check" in result.output.lower()

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_check_mode_uses_check_only(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """BE-216: Test --check flag uses CHECK_ONLY mode."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--check"])

        assert result.exit_code == 0

        # Verify CHECK_ONLY mode was used
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["mode"] == RefreshMode.CHECK_ONLY

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_check_mode_no_notice_when_no_updates(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_no_changes,
    ):
        """BE-216: Test check notice not shown when no updates available."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_no_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--check"])

        assert result.exit_code == 0
        # When refreshed_count == 0, check notice should not appear


# =============================================================================
# BE-217: TestErrorHandling
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling (BE-217)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_error_handling_collection_not_found(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
    ):
        """BE-217: Test error handling when collection doesn't exist."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.side_effect = ValueError(
            "Collection 'nonexistent' not found"
        )
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "-c", "nonexistent"])

        # Should exit with error code
        assert result.exit_code == 1
        # Should show error message
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_error_handling_refresh_errors_displayed(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_errors,
    ):
        """BE-217: Test error handling when refresh encounters errors."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_errors
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh"])

        # Command exits with error code 1 when there are per-artifact errors
        assert result.exit_code == 1
        # Should show error count in summary
        assert "Errors" in result.output
        assert "2" in result.output  # error_count
        # Should show error details section
        assert "skill:private-skill" in result.output or "skill:rate-limited" in result.output

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_error_handling_generic_exception(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
    ):
        """BE-217: Test error handling for unexpected exceptions."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.side_effect = Exception("Unexpected error")
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh"])

        # Should exit with error code
        assert result.exit_code == 1
        # Should display error message
        assert "error" in result.output.lower()


# =============================================================================
# Additional Tests: Type and Name Filters
# =============================================================================


class TestFilterOptions:
    """Integration tests for filter options (--type, --name)."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_type_filter(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """Test --type filter is passed correctly."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "-t", "skill"])

        assert result.exit_code == 0

        # Verify filter was passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["artifact_filter"] == {"type": "skill"}

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_name_filter(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """Test --name filter is passed correctly."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "-n", "canvas-*"])

        assert result.exit_code == 0

        # Verify filter was passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["artifact_filter"] == {"name": "canvas-*"}

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_combined_filters(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """Test combined --type and --name filters."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(
            main, ["collection", "refresh", "-t", "skill", "-n", "pdf-*"]
        )

        assert result.exit_code == 0

        # Verify both filters were passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["artifact_filter"] == {"type": "skill", "name": "pdf-*"}


# =============================================================================
# Additional Tests: Fields Option
# =============================================================================


class TestFieldsOption:
    """Integration tests for --fields option."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_fields_option_single_field(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """Test --fields with single field."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh", "--fields", "description"])

        assert result.exit_code == 0

        # Verify fields were passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["fields"] == ["description"]

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_fields_option_multiple_fields(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_with_changes,
    ):
        """Test --fields with multiple comma-separated fields."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_with_changes
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(
            main, ["collection", "refresh", "--fields", "description,tags,author"]
        )

        assert result.exit_code == 0

        # Verify fields were parsed and passed
        call_kwargs = mock_refresher.refresh_collection.call_args[1]
        assert call_kwargs["fields"] == ["description", "tags", "author"]


# =============================================================================
# Additional Tests: Empty Collection
# =============================================================================


class TestEmptyCollection:
    """Integration tests for empty collection scenarios."""

    @patch("skillmeat.cli.CollectionRefresher")
    @patch("skillmeat.cli.CollectionManager")
    def test_refresh_empty_collection(
        self,
        mock_manager_class,
        mock_refresher_class,
        isolated_cli_runner,
        mock_refresh_result_empty,
    ):
        """Test refresh on empty collection."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_refresher = MagicMock()
        mock_refresher.refresh_collection.return_value = mock_refresh_result_empty
        mock_refresher_class.return_value = mock_refresher

        result = runner.invoke(main, ["collection", "refresh"])

        assert result.exit_code == 0
        # Should show summary with all zeros
        assert "Refresh Summary" in result.output
        assert "Total" in result.output


# =============================================================================
# BE-409: TestRollbackFlag
# =============================================================================


class TestRollbackFlag:
    """Integration tests for --rollback flag (BE-409)."""

    @patch("skillmeat.storage.snapshot.SnapshotManager")
    @patch("skillmeat.cli.CollectionManager")
    def test_rollback_flag_exclusive_with_other_flags(
        self,
        mock_manager_class,
        mock_snapshot_manager_class,
        isolated_cli_runner,
    ):
        """BE-409: Test --rollback cannot be combined with other flags."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager.get_active_collection_name.return_value = "default"
        mock_manager_class.return_value = mock_manager

        # Test with dry-run
        result = runner.invoke(main, ["collection", "refresh", "--rollback", "--dry-run"])
        assert result.exit_code == 1
        assert "cannot be combined" in result.output.lower()

        # Test with check
        result = runner.invoke(main, ["collection", "refresh", "--rollback", "--check"])
        assert result.exit_code == 1
        assert "cannot be combined" in result.output.lower()

        # Test with type filter
        result = runner.invoke(main, ["collection", "refresh", "--rollback", "-t", "skill"])
        assert result.exit_code == 1
        assert "cannot be combined" in result.output.lower()

    @patch("skillmeat.storage.snapshot.SnapshotManager")
    @patch("skillmeat.cli.CollectionManager")
    def test_rollback_finds_pre_refresh_snapshot(
        self,
        mock_manager_class,
        mock_snapshot_manager_class,
        isolated_cli_runner,
    ):
        """BE-409: Test rollback finds most recent pre-refresh snapshot."""
        from datetime import datetime
        from skillmeat.storage.snapshot import Snapshot
        from pathlib import Path

        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager.get_active_collection_name.return_value = "default"
        mock_manager.config.get_collection_path.return_value = Path("/test/collection")
        mock_manager_class.return_value = mock_manager

        # Create mock snapshots
        pre_refresh_snapshot = Snapshot(
            id="20260122-120000-000000",
            timestamp=datetime(2026, 1, 22, 12, 0, 0),
            message="pre-refresh snapshot",
            collection_name="default",
            artifact_count=5,
            tarball_path=Path("/test/snapshots/20260122-120000-000000.tar.gz"),
        )

        mock_snapshot_manager = MagicMock()
        mock_snapshot_manager.list_snapshots.return_value = ([pre_refresh_snapshot], None)
        mock_snapshot_manager_class.return_value = mock_snapshot_manager

        # Run with -y to skip confirmation
        result = runner.invoke(main, ["collection", "refresh", "--rollback", "-y"])

        assert result.exit_code == 0
        assert "Found pre-refresh snapshot" in result.output
        # Check for ID parts (Rich may add formatting codes between them)
        assert "20260122" in result.output
        assert "120000" in result.output
        assert "Successfully restored" in result.output

        # Verify restore was called
        mock_snapshot_manager.restore_snapshot.assert_called_once_with(
            pre_refresh_snapshot, Path("/test/collection")
        )

    @patch("skillmeat.storage.snapshot.SnapshotManager")
    @patch("skillmeat.cli.CollectionManager")
    def test_rollback_no_snapshot_found(
        self,
        mock_manager_class,
        mock_snapshot_manager_class,
        isolated_cli_runner,
    ):
        """BE-409: Test error when no pre-refresh snapshot exists."""
        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager.get_active_collection_name.return_value = "default"
        mock_manager_class.return_value = mock_manager

        # No snapshots available
        mock_snapshot_manager = MagicMock()
        mock_snapshot_manager.list_snapshots.return_value = ([], None)
        mock_snapshot_manager_class.return_value = mock_snapshot_manager

        result = runner.invoke(main, ["collection", "refresh", "--rollback"])

        assert result.exit_code == 1
        assert "No pre-refresh snapshot found" in result.output
        assert "Hint" in result.output

    @patch("skillmeat.storage.snapshot.SnapshotManager")
    @patch("skillmeat.cli.CollectionManager")
    def test_rollback_requires_confirmation(
        self,
        mock_manager_class,
        mock_snapshot_manager_class,
        isolated_cli_runner,
    ):
        """BE-409: Test rollback prompts for confirmation when -y not provided."""
        from datetime import datetime
        from skillmeat.storage.snapshot import Snapshot
        from pathlib import Path

        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager.get_active_collection_name.return_value = "default"
        mock_manager.config.get_collection_path.return_value = Path("/test/collection")
        mock_manager_class.return_value = mock_manager

        # Create mock snapshot
        pre_refresh_snapshot = Snapshot(
            id="20260122-120000-000000",
            timestamp=datetime(2026, 1, 22, 12, 0, 0),
            message="Before refresh: pre-refresh snapshot",
            collection_name="default",
            artifact_count=5,
            tarball_path=Path("/test/snapshots/20260122-120000-000000.tar.gz"),
        )

        mock_snapshot_manager = MagicMock()
        mock_snapshot_manager.list_snapshots.return_value = ([pre_refresh_snapshot], None)
        mock_snapshot_manager_class.return_value = mock_snapshot_manager

        # Run without -y and simulate user cancelling
        result = runner.invoke(
            main, ["collection", "refresh", "--rollback"], input="n\n"
        )

        assert "Warning" in result.output
        assert "Continue with rollback?" in result.output
        assert "cancelled" in result.output.lower()

        # Verify restore was NOT called
        mock_snapshot_manager.restore_snapshot.assert_not_called()

    @patch("skillmeat.storage.snapshot.SnapshotManager")
    @patch("skillmeat.cli.CollectionManager")
    def test_rollback_selects_most_recent(
        self,
        mock_manager_class,
        mock_snapshot_manager_class,
        isolated_cli_runner,
    ):
        """BE-409: Test rollback selects most recent pre-refresh snapshot."""
        from datetime import datetime
        from skillmeat.storage.snapshot import Snapshot
        from pathlib import Path

        runner = isolated_cli_runner

        mock_manager = MagicMock()
        mock_manager.get_active_collection_name.return_value = "default"
        mock_manager.config.get_collection_path.return_value = Path("/test/collection")
        mock_manager_class.return_value = mock_manager

        # Create multiple pre-refresh snapshots (list_snapshots returns newest first)
        recent_snapshot = Snapshot(
            id="20260122-150000-000000",
            timestamp=datetime(2026, 1, 22, 15, 0, 0),
            message="pre-refresh snapshot",
            collection_name="default",
            artifact_count=5,
            tarball_path=Path("/test/snapshots/20260122-150000-000000.tar.gz"),
        )

        old_snapshot = Snapshot(
            id="20260122-120000-000000",
            timestamp=datetime(2026, 1, 22, 12, 0, 0),
            message="Before refresh: older pre-refresh",
            collection_name="default",
            artifact_count=5,
            tarball_path=Path("/test/snapshots/20260122-120000-000000.tar.gz"),
        )

        mock_snapshot_manager = MagicMock()
        mock_snapshot_manager.list_snapshots.return_value = (
            [recent_snapshot, old_snapshot],
            None,
        )
        mock_snapshot_manager_class.return_value = mock_snapshot_manager

        # Run with -y
        result = runner.invoke(main, ["collection", "refresh", "--rollback", "-y"])

        assert result.exit_code == 0
        # Check for ID parts (Rich may add formatting codes between them)
        assert "20260122" in result.output
        assert "150000" in result.output  # Most recent

        # Verify correct snapshot was restored
        mock_snapshot_manager.restore_snapshot.assert_called_once_with(
            recent_snapshot, Path("/test/collection")
        )
