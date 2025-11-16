"""Tests for sync rollback functionality.

Tests the rollback support added in P3-004:
- sync_from_project_with_rollback() method
- Automatic rollback on sync failure
- User-initiated rollback on partial success
- Snapshot creation and restoration
- Error handling for rollback failures
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from skillmeat.core.sync import SyncManager
from skillmeat.models import (
    SyncResult,
    DriftDetectionResult,
    DeploymentMetadata,
    DeploymentRecord,
)
from skillmeat.storage.snapshot import Snapshot


class TestSyncFromProjectWithRollback:
    """Tests for sync_from_project_with_rollback() method."""

    def test_rollback_with_no_snapshot_manager(self, tmp_path):
        """Test rollback falls back to regular sync when no snapshot manager."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        # Create SyncManager without snapshot manager
        sync_mgr = SyncManager(
            collection_manager=None,
            snapshot_manager=None,  # No snapshot manager
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 1 artifact",
                artifacts_synced=["skill1"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
            )

            # Should fall back to regular sync
            assert mock_sync.called
            assert result.status == "success"

    def test_rollback_with_dry_run(self, tmp_path):
        """Test rollback falls back to regular sync in dry-run mode."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()

        snapshot_mgr = Mock()
        sync_mgr = SyncManager(
            collection_manager=None,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="dry_run",
                message="Would sync 2 artifacts",
                artifacts_synced=["skill1", "skill2"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
                dry_run=True,
            )

            # Should fall back to regular sync without creating snapshot
            assert mock_sync.called
            assert not snapshot_mgr.create_snapshot.called
            assert result.status == "dry_run"

    def test_rollback_with_no_metadata(self, tmp_path):
        """Test rollback proceeds without snapshot when no metadata."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        # No metadata file

        snapshot_mgr = Mock()
        sync_mgr = SyncManager(
            collection_manager=None,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 1 artifact",
                artifacts_synced=["skill1"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
            )

            # Should proceed without snapshot
            assert mock_sync.called
            assert not snapshot_mgr.create_snapshot.called
            assert result.status == "success"

    def test_rollback_with_no_collection_manager(self, tmp_path):
        """Test rollback proceeds without snapshot when no collection manager."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        snapshot_mgr = Mock()
        sync_mgr = SyncManager(
            collection_manager=None,  # No collection manager
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 1 artifact",
                artifacts_synced=["skill1"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
            )

            # Should proceed without snapshot
            assert mock_sync.called
            assert not snapshot_mgr.create_snapshot.called
            assert result.status == "success"

    def test_rollback_successful_snapshot_creation(self, tmp_path):
        """Test rollback creates snapshot before sync."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 1 artifact",
                artifacts_synced=["skill1"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
            )

            # Should create snapshot before sync
            snapshot_mgr.create_snapshot.assert_called_once_with(
                collection_path=collection_path,
                collection_name="test-collection",
                message="Pre-sync snapshot (automatic)",
            )
            assert mock_sync.called
            assert result.status == "success"

    def test_rollback_snapshot_creation_failure_interactive(self, tmp_path):
        """Test rollback handles snapshot creation failure in interactive mode."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        # Snapshot creation fails
        snapshot_mgr.create_snapshot.side_effect = Exception("Disk full")

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 1 artifact",
                artifacts_synced=["skill1"],
            )

            # User confirms to proceed without snapshot
            with patch('rich.prompt.Confirm.ask', return_value=True):
                result = sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                    interactive=True,
                )

                # Should proceed with sync despite snapshot failure
                assert mock_sync.called
                assert result.status == "success"

    def test_rollback_snapshot_creation_failure_user_cancels(self, tmp_path):
        """Test rollback cancels when user declines to proceed without snapshot."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        # Snapshot creation fails
        snapshot_mgr.create_snapshot.side_effect = Exception("Disk full")

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # User declines to proceed
            with patch('rich.prompt.Confirm.ask', return_value=False):
                result = sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                    interactive=True,
                )

                # Should cancel sync
                assert not mock_sync.called
                assert result.status == "cancelled"
                assert "snapshot creation failed" in result.message.lower()

    def test_rollback_on_sync_failure(self, tmp_path):
        """Test automatic rollback when sync fails."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # Sync fails
            mock_sync.side_effect = Exception("Permission denied")

            with pytest.raises(ValueError, match="Sync failed and was rolled back"):
                sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                )

            # Should automatically restore snapshot
            snapshot_mgr.restore_snapshot.assert_called_once_with(
                snapshot, collection_path
            )

    def test_rollback_on_partial_success_user_accepts(self, tmp_path):
        """Test user-initiated rollback on partial success."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # Partial success with conflicts
            mock_sync.return_value = SyncResult(
                status="partial",
                message="Synced 1 of 2 artifacts",
                artifacts_synced=["skill1"],
                conflicts=["skill2"],
            )

            # User chooses to rollback
            with patch('rich.prompt.Confirm.ask', return_value=True):
                result = sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                    interactive=True,
                )

                # Should rollback
                snapshot_mgr.restore_snapshot.assert_called_once_with(
                    snapshot, collection_path
                )
                assert result.status == "cancelled"
                assert "conflicts" in result.message.lower()

    def test_rollback_on_partial_success_user_declines(self, tmp_path):
        """Test user declines rollback on partial success."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # Partial success with conflicts
            mock_sync.return_value = SyncResult(
                status="partial",
                message="Synced 1 of 2 artifacts",
                artifacts_synced=["skill1"],
                conflicts=["skill2"],
            )

            # User declines rollback
            with patch('rich.prompt.Confirm.ask', return_value=False):
                result = sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                    interactive=True,
                )

                # Should not rollback
                assert not snapshot_mgr.restore_snapshot.called
                assert result.status == "partial"

    def test_rollback_failure_raises_error(self, tmp_path):
        """Test rollback failure raises error with both sync and rollback errors."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        # Rollback also fails
        snapshot_mgr.restore_snapshot.side_effect = Exception("Rollback failed")

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # Sync fails
            mock_sync.side_effect = Exception("Permission denied")

            with pytest.raises(ValueError) as exc_info:
                sync_mgr.sync_from_project_with_rollback(
                    project_path=project_path,
                    strategy="overwrite",
                )

            # Should mention both errors
            error_msg = str(exc_info.value)
            assert "sync failed" in error_msg.lower()
            assert "rollback" in error_msg.lower()

    def test_rollback_non_interactive_mode(self, tmp_path):
        """Test rollback in non-interactive mode (no user prompts)."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            # Partial success
            mock_sync.return_value = SyncResult(
                status="partial",
                message="Synced 1 of 2 artifacts",
                artifacts_synced=["skill1"],
                conflicts=["skill2"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
                interactive=False,  # Non-interactive
            )

            # Should not prompt for rollback, just return partial result
            assert result.status == "partial"
            assert not snapshot_mgr.restore_snapshot.called

    def test_rollback_success_no_rollback_needed(self, tmp_path):
        """Test successful sync with no rollback needed."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        metadata_path = project_path / ".claude" / ".skillmeat-deployed.toml"
        metadata_path.write_text(
            "[deployment]\n"
            'collection = "test-collection"\n'
            'deployed-at = "2024-01-01T00:00:00"\n'
            'skillmeat-version = "0.1.0"\n'
        )

        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        snapshot_mgr = Mock()
        collection_mgr = Mock()
        collection = Mock()
        collection.path = collection_path
        collection_mgr.get_collection.return_value = collection

        snapshot = Mock()
        snapshot.id = "snap123"
        snapshot.collection_name = "test-collection"
        snapshot_mgr.create_snapshot.return_value = snapshot

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr,
        )

        with patch.object(sync_mgr, 'sync_from_project') as mock_sync:
            mock_sync.return_value = SyncResult(
                status="success",
                message="Synced 3 artifacts",
                artifacts_synced=["skill1", "skill2", "skill3"],
            )

            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                strategy="overwrite",
            )

            # Should not rollback on success
            assert not snapshot_mgr.restore_snapshot.called
            assert result.status == "success"
