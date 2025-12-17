"""Unit tests for VersionManager."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from skillmeat.core.version import VersionManager
from skillmeat.storage.snapshot import Snapshot


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide temporary config directory."""
    return tmp_path / "skillmeat"


@pytest.fixture
def temp_collection(tmp_path):
    """Create a temporary collection."""
    collection_path = tmp_path / "skillmeat" / "collections" / "test-collection"
    collection_path.mkdir(parents=True)

    # Create collection structure
    (collection_path / "skills").mkdir()
    (collection_path / "commands").mkdir()
    (collection_path / "agents").mkdir()

    # Create collection.toml
    collection_toml = """
[collection]
name = "test-collection"
version = "1.0.0"
created = "2025-01-01T00:00:00"
updated = "2025-01-01T00:00:00"

[[artifacts]]
name = "test-skill"
type = "skill"
path = "skills/test-skill"
origin = "local"
added = "2025-01-01T00:00:00"

[artifacts.metadata]
"""
    (collection_path / "collection.toml").write_text(collection_toml)

    # Create test skill
    skill_dir = collection_path / "skills" / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")

    return collection_path


@pytest.fixture
def mock_collection_mgr(temp_config_dir, temp_collection):
    """Provide mocked CollectionManager."""
    from skillmeat.config import ConfigManager
    from skillmeat.core.collection import CollectionManager

    config = ConfigManager(temp_config_dir)
    config.set_active_collection("test-collection")

    collection_mgr = CollectionManager(config)
    return collection_mgr


@pytest.fixture
def version_manager(mock_collection_mgr):
    """Provide VersionManager instance."""
    return VersionManager(mock_collection_mgr)


class TestVersionManagerInit:
    """Test VersionManager initialization."""

    def test_init_with_collection_mgr(self, mock_collection_mgr):
        """Test initialization with provided CollectionManager."""
        vm = VersionManager(mock_collection_mgr)
        assert vm.collection_mgr is mock_collection_mgr
        assert vm.snapshot_mgr is not None

    def test_init_without_collection_mgr(self):
        """Test initialization creates default CollectionManager."""
        vm = VersionManager()
        assert vm.collection_mgr is not None
        assert vm.snapshot_mgr is not None

    def test_init_with_custom_snapshot_mgr(self, mock_collection_mgr, tmp_path):
        """Test initialization with custom SnapshotManager."""
        from skillmeat.storage.snapshot import SnapshotManager

        custom_snapshot_mgr = SnapshotManager(tmp_path / "snapshots")
        vm = VersionManager(mock_collection_mgr, custom_snapshot_mgr)
        assert vm.snapshot_mgr is custom_snapshot_mgr


class TestCreateSnapshot:
    """Test create_snapshot method."""

    @patch("skillmeat.core.version.console")
    def test_create_snapshot_default_collection(
        self, mock_console, version_manager, temp_collection
    ):
        """Test creating snapshot with default collection."""
        snapshot = version_manager.create_snapshot(message="Test snapshot")

        assert snapshot is not None
        assert snapshot.collection_name == "test-collection"
        assert snapshot.message == "Test snapshot"
        assert snapshot.artifact_count >= 0
        assert snapshot.tarball_path.exists()

        # Verify console output
        assert mock_console.print.called

    @patch("skillmeat.core.version.console")
    def test_create_snapshot_explicit_collection(
        self, mock_console, version_manager, temp_collection
    ):
        """Test creating snapshot with explicit collection name."""
        snapshot = version_manager.create_snapshot(
            collection_name="test-collection", message="Explicit snapshot"
        )

        assert snapshot.collection_name == "test-collection"
        assert snapshot.message == "Explicit snapshot"

    def test_create_snapshot_nonexistent_collection_raises_error(self, version_manager):
        """Test creating snapshot of nonexistent collection raises error."""
        with pytest.raises(ValueError, match="not found"):
            version_manager.create_snapshot(
                collection_name="nonexistent", message="Test"
            )


class TestListSnapshots:
    """Test list_snapshots method."""

    @patch("skillmeat.core.version.console")
    def test_list_snapshots_empty(self, mock_console, version_manager):
        """Test listing snapshots when none exist."""
        snapshots, _ = version_manager.list_snapshots()
        assert snapshots == []

    @patch("skillmeat.core.version.console")
    def test_list_snapshots_single(
        self, mock_console, version_manager, temp_collection
    ):
        """Test listing single snapshot."""
        version_manager.create_snapshot(message="Snapshot 1")
        snapshots, _ = version_manager.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0].message == "Snapshot 1"

    @patch("skillmeat.core.version.console")
    def test_list_snapshots_multiple_sorted(
        self, mock_console, version_manager, temp_collection
    ):
        """Test listing multiple snapshots sorted newest first."""
        import time

        version_manager.create_snapshot(message="Snapshot 1")
        time.sleep(0.01)
        version_manager.create_snapshot(message="Snapshot 2")
        time.sleep(0.01)
        version_manager.create_snapshot(message="Snapshot 3")

        snapshots, _ = version_manager.list_snapshots()
        assert len(snapshots) == 3

        # Should be sorted newest first
        assert snapshots[0].message == "Snapshot 3"
        assert snapshots[1].message == "Snapshot 2"
        assert snapshots[2].message == "Snapshot 1"


class TestGetSnapshot:
    """Test get_snapshot method."""

    @patch("skillmeat.core.version.console")
    def test_get_snapshot_exists(self, mock_console, version_manager, temp_collection):
        """Test getting existing snapshot."""
        created = version_manager.create_snapshot(message="Test")

        snapshot = version_manager.get_snapshot(created.id)
        assert snapshot is not None
        assert snapshot.id == created.id
        assert snapshot.message == "Test"

    @patch("skillmeat.core.version.console")
    def test_get_snapshot_not_found(
        self, mock_console, version_manager, temp_collection
    ):
        """Test getting nonexistent snapshot returns None."""
        snapshot = version_manager.get_snapshot("nonexistent-id")
        assert snapshot is None


class TestRollback:
    """Test rollback method."""

    @patch("skillmeat.core.version.console")
    @patch("skillmeat.core.version.Confirm.ask")
    def test_rollback_with_confirmation(
        self, mock_confirm, mock_console, version_manager, temp_collection
    ):
        """Test rollback with user confirmation."""
        # Create initial snapshot
        snapshot = version_manager.create_snapshot(message="Before changes")

        # Modify collection
        (temp_collection / "skills" / "new-skill").mkdir()
        (temp_collection / "skills" / "new-skill" / "SKILL.md").write_text("# New")

        # Mock user confirmation
        mock_confirm.return_value = True

        # Rollback
        version_manager.rollback(snapshot.id, confirm=True)

        # Verify confirmation was asked
        assert mock_confirm.called

        # Verify collection was restored (new-skill should not exist)
        assert not (temp_collection / "skills" / "new-skill").exists()

    @patch("skillmeat.core.version.console")
    @patch("skillmeat.core.version.Confirm.ask")
    def test_rollback_cancelled_by_user(
        self, mock_confirm, mock_console, version_manager, temp_collection
    ):
        """Test rollback cancelled by user."""
        snapshot = version_manager.create_snapshot(message="Test")

        # Mock user declining
        mock_confirm.return_value = False

        # Should raise ValueError
        with pytest.raises(ValueError, match="cancelled"):
            version_manager.rollback(snapshot.id, confirm=True)

    @patch("skillmeat.core.version.console")
    def test_rollback_without_confirmation(
        self, mock_console, version_manager, temp_collection
    ):
        """Test rollback without confirmation prompt."""
        # Create initial snapshot
        snapshot = version_manager.create_snapshot(message="Before changes")

        # Modify collection
        (temp_collection / "skills" / "new-skill").mkdir()
        (temp_collection / "skills" / "new-skill" / "SKILL.md").write_text("# New")

        # Rollback without confirmation
        version_manager.rollback(snapshot.id, confirm=False)

        # Verify collection was restored
        assert not (temp_collection / "skills" / "new-skill").exists()

    @patch("skillmeat.core.version.console")
    def test_rollback_nonexistent_snapshot_raises_error(
        self, mock_console, version_manager
    ):
        """Test rollback to nonexistent snapshot raises error."""
        with pytest.raises(ValueError, match="not found"):
            version_manager.rollback("nonexistent-id", confirm=False)

    @patch("skillmeat.core.version.console")
    def test_rollback_creates_safety_snapshot(
        self, mock_console, version_manager, temp_collection
    ):
        """Test rollback creates safety snapshot before restoring."""
        # Create initial snapshot
        snapshot = version_manager.create_snapshot(message="Before changes")

        # Modify collection
        (temp_collection / "skills" / "new-skill").mkdir()

        initial_count = len(version_manager.list_snapshots()[0])

        # Rollback (creates auto-snapshot first)
        version_manager.rollback(snapshot.id, confirm=False)

        # Should have one more snapshot (the safety snapshot)
        final_count = len(version_manager.list_snapshots()[0])
        assert final_count == initial_count + 1

        # Find the safety snapshot
        snapshots, _ = version_manager.list_snapshots()
        safety_snapshot = next(
            s for s in snapshots if "[auto] Before rollback" in s.message
        )
        assert safety_snapshot is not None


class TestAutoSnapshot:
    """Test auto_snapshot method."""

    def test_auto_snapshot_creates_snapshot(self, version_manager, temp_collection):
        """Test auto-snapshot creates snapshot without console output."""
        snapshot = version_manager.auto_snapshot(message="Auto test")

        assert snapshot is not None
        assert snapshot.message == "[auto] Auto test"
        assert snapshot.tarball_path.exists()

    def test_auto_snapshot_nonexistent_collection_raises_error(self, version_manager):
        """Test auto-snapshot on nonexistent collection raises error."""
        with pytest.raises(ValueError, match="not found"):
            version_manager.auto_snapshot(collection_name="nonexistent", message="Test")


class TestCleanupSnapshots:
    """Test cleanup_snapshots method."""

    @patch("skillmeat.core.version.console")
    def test_cleanup_under_limit(self, mock_console, version_manager, temp_collection):
        """Test cleanup when under limit doesn't delete anything."""
        import time

        for i in range(3):
            version_manager.create_snapshot(message=f"Snapshot {i}")
            time.sleep(0.01)

        deleted = version_manager.cleanup_snapshots(keep_count=10)

        assert len(deleted) == 0
        snapshots, _ = version_manager.list_snapshots()
        assert len(snapshots) == 3

    @patch("skillmeat.core.version.console")
    def test_cleanup_over_limit(self, mock_console, version_manager, temp_collection):
        """Test cleanup deletes old snapshots over limit."""
        import time

        for i in range(5):
            version_manager.create_snapshot(message=f"Snapshot {i}")
            time.sleep(0.01)

        deleted = version_manager.cleanup_snapshots(keep_count=2)

        assert len(deleted) == 3
        snapshots, _ = version_manager.list_snapshots()
        assert len(snapshots) == 2

        # Newest snapshots should be kept
        assert snapshots[0].message == "Snapshot 4"
        assert snapshots[1].message == "Snapshot 3"


class TestDeleteSnapshot:
    """Test delete_snapshot method."""

    @patch("skillmeat.core.version.console")
    def test_delete_snapshot(self, mock_console, version_manager, temp_collection):
        """Test deleting a snapshot."""
        snapshot = version_manager.create_snapshot(message="To delete")

        tarball_path = snapshot.tarball_path
        assert tarball_path.exists()

        version_manager.delete_snapshot(snapshot.id)

        # Verify tarball deleted
        assert not tarball_path.exists()

        # Verify metadata updated
        snapshots, _ = version_manager.list_snapshots()
        assert len(snapshots) == 0

    @patch("skillmeat.core.version.console")
    def test_delete_nonexistent_snapshot_raises_error(
        self, mock_console, version_manager
    ):
        """Test deleting nonexistent snapshot raises error."""
        with pytest.raises(ValueError, match="not found"):
            version_manager.delete_snapshot("nonexistent-id")
