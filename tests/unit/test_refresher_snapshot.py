"""Unit tests for snapshot creation during refresh operations.

Tests for BE-408: Implement refresh snapshot creation for rollback support.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.refresher import CollectionRefresher, RefreshMode, RefreshResult
from skillmeat.storage.snapshot import Snapshot, SnapshotManager


class TestRefreshResultSnapshotField:
    """Test RefreshResult dataclass with snapshot_id field."""

    def test_refresh_result_has_snapshot_id_field(self):
        """RefreshResult should have optional snapshot_id field."""
        result = RefreshResult(
            refreshed_count=5,
            unchanged_count=10,
            skipped_count=2,
            error_count=1,
            snapshot_id="20250122-103045-123456",
        )

        assert result.snapshot_id == "20250122-103045-123456"

    def test_refresh_result_snapshot_id_defaults_to_none(self):
        """snapshot_id should default to None if not provided."""
        result = RefreshResult()
        assert result.snapshot_id is None

    def test_refresh_result_to_dict_includes_snapshot_id(self):
        """to_dict() should include snapshot_id field."""
        result = RefreshResult(snapshot_id="test-snapshot-123")
        result_dict = result.to_dict()

        assert "snapshot_id" in result_dict
        assert result_dict["snapshot_id"] == "test-snapshot-123"

    def test_refresh_result_from_dict_loads_snapshot_id(self):
        """from_dict() should correctly load snapshot_id."""
        data = {
            "refreshed_count": 3,
            "unchanged_count": 2,
            "snapshot_id": "restored-snapshot-id",
        }

        result = RefreshResult.from_dict(data)
        assert result.snapshot_id == "restored-snapshot-id"
        assert result.refreshed_count == 3

    def test_refresh_result_from_dict_handles_missing_snapshot_id(self):
        """from_dict() should handle missing snapshot_id gracefully."""
        data = {"refreshed_count": 1}
        result = RefreshResult.from_dict(data)

        assert result.snapshot_id is None


class TestSnapshotCreationDuringRefresh:
    """Test snapshot creation before refresh operations."""

    @pytest.fixture
    def mock_managers(self):
        """Create mock managers for testing."""
        collection_manager = MagicMock(spec=CollectionManager)
        snapshot_manager = MagicMock(spec=SnapshotManager)
        return collection_manager, snapshot_manager

    @pytest.fixture
    def mock_collection(self):
        """Create a mock collection with one artifact."""
        # Create artifact with required fields
        artifact = Mock(spec=Artifact)
        artifact.name = "test-skill"
        artifact.type = ArtifactType.SKILL
        artifact.origin = "local"  # No GitHub source, will be skipped
        artifact.upstream = None

        collection = Mock(spec=Collection)
        collection.name = "test"
        collection.artifacts = [artifact]

        return collection

    def test_snapshot_created_before_refresh(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Snapshot should be created before applying refresh changes."""
        collection_manager, snapshot_manager = mock_managers

        # Setup mocks
        collection_path = tmp_path / "test_collection"
        collection_path.mkdir()

        mock_config = Mock()
        mock_config.get_collection_path.return_value = collection_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        mock_snapshot = Mock(spec=Snapshot)
        mock_snapshot.id = "20250122-103045-123456"
        mock_snapshot.artifact_count = 1

        snapshot_manager.create_snapshot.return_value = mock_snapshot

        # Create refresher with snapshot manager
        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh with snapshot enabled
        result = refresher.refresh_collection(
            collection_name="test",
            mode=RefreshMode.METADATA_ONLY,
            create_snapshot_before_refresh=True,
        )

        # Verify snapshot was created
        snapshot_manager.create_snapshot.assert_called_once()
        call_kwargs = snapshot_manager.create_snapshot.call_args.kwargs

        assert call_kwargs["collection_path"] == collection_path
        assert call_kwargs["collection_name"] == "test"
        assert "pre-refresh" in call_kwargs["message"]

        # Verify snapshot ID in result
        assert result.snapshot_id == "20250122-103045-123456"

    def test_snapshot_not_created_when_disabled(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Snapshot should not be created when create_snapshot_before_refresh=False."""
        collection_manager, snapshot_manager = mock_managers

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh with snapshot disabled
        result = refresher.refresh_collection(
            collection_name="test",
            create_snapshot_before_refresh=False,
        )

        # Verify snapshot was NOT created
        snapshot_manager.create_snapshot.assert_not_called()
        assert result.snapshot_id is None

    def test_snapshot_not_created_in_dry_run_mode(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Snapshot should not be created in dry-run mode."""
        collection_manager, snapshot_manager = mock_managers

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh in dry-run mode
        result = refresher.refresh_collection(
            collection_name="test",
            dry_run=True,
            create_snapshot_before_refresh=True,
        )

        # Verify snapshot was NOT created (dry-run should not create snapshots)
        snapshot_manager.create_snapshot.assert_not_called()
        assert result.snapshot_id is None

    def test_snapshot_not_created_in_check_only_mode(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Snapshot should not be created in CHECK_ONLY mode."""
        collection_manager, snapshot_manager = mock_managers

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh in CHECK_ONLY mode
        result = refresher.refresh_collection(
            collection_name="test",
            mode=RefreshMode.CHECK_ONLY,
            create_snapshot_before_refresh=True,
        )

        # Verify snapshot was NOT created
        snapshot_manager.create_snapshot.assert_not_called()
        assert result.snapshot_id is None

    def test_snapshot_not_created_when_no_snapshot_manager(
        self, mock_collection, tmp_path
    ):
        """Snapshot should not be created if snapshot_manager is None."""
        collection_manager = MagicMock(spec=CollectionManager)

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        # Create refresher WITHOUT snapshot manager
        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=None,
        )

        # Run refresh
        result = refresher.refresh_collection(
            collection_name="test",
            create_snapshot_before_refresh=True,
        )

        # Verify no snapshot created (manager is None)
        assert result.snapshot_id is None

    def test_snapshot_failure_does_not_block_refresh(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Refresh should continue even if snapshot creation fails."""
        collection_manager, snapshot_manager = mock_managers

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        # Make snapshot creation fail
        snapshot_manager.create_snapshot.side_effect = IOError("Disk full")

        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh - should not raise exception
        result = refresher.refresh_collection(
            collection_name="test",
            create_snapshot_before_refresh=True,
        )

        # Verify refresh continued without snapshot
        assert result.snapshot_id is None
        assert result.skipped_count == 1  # The local artifact was skipped

    def test_snapshot_message_contains_timestamp(
        self, mock_managers, mock_collection, tmp_path
    ):
        """Snapshot message should contain pre-refresh and timestamp."""
        collection_manager, snapshot_manager = mock_managers

        mock_config = Mock()
        mock_config.get_collection_path.return_value = tmp_path

        collection_manager.load_collection.return_value = mock_collection
        collection_manager.config = mock_config

        mock_snapshot = Mock(spec=Snapshot)
        mock_snapshot.id = "20250122-103045-123456"
        mock_snapshot.artifact_count = 1

        snapshot_manager.create_snapshot.return_value = mock_snapshot

        refresher = CollectionRefresher(
            collection_manager=collection_manager,
            snapshot_manager=snapshot_manager,
        )

        # Run refresh
        refresher.refresh_collection(
            collection_name="test",
            create_snapshot_before_refresh=True,
        )

        # Verify snapshot message format
        call_kwargs = snapshot_manager.create_snapshot.call_args.kwargs
        message = call_kwargs["message"]

        assert message.startswith("pre-refresh-")
        # Message should contain timestamp in format YYYYMMDD-HHMMSS
        timestamp_part = message.replace("pre-refresh-", "")
        assert len(timestamp_part) == 15  # YYYYMMDD-HHMMSS
