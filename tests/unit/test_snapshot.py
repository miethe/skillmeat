"""Unit tests for SnapshotManager."""

import pytest
import tarfile
from datetime import datetime
from pathlib import Path

from skillmeat.storage.snapshot import Snapshot, SnapshotManager


@pytest.fixture
def temp_snapshots_dir(tmp_path):
    """Provide temporary snapshots directory."""
    return tmp_path / "snapshots"


@pytest.fixture
def temp_collection_path(tmp_path):
    """Provide temporary collection directory."""
    collection_path = tmp_path / "collections" / "test-collection"
    collection_path.mkdir(parents=True)

    # Create some test files
    (collection_path / "collection.toml").write_text("# Test manifest")
    skills_dir = collection_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "skill1").mkdir()
    (skills_dir / "skill1" / "SKILL.md").write_text("# Skill 1")
    (skills_dir / "skill2").mkdir()
    (skills_dir / "skill2" / "SKILL.md").write_text("# Skill 2")

    commands_dir = collection_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "command1.md").write_text("# Command 1")

    return collection_path


@pytest.fixture
def snapshot_manager(temp_snapshots_dir):
    """Provide SnapshotManager instance."""
    return SnapshotManager(temp_snapshots_dir)


class TestSnapshot:
    """Test Snapshot dataclass."""

    def test_create_snapshot(self):
        """Test creating a snapshot."""
        now = datetime.utcnow()
        snapshot = Snapshot(
            id="20251107-120000",
            timestamp=now,
            message="Test snapshot",
            collection_name="test",
            artifact_count=5,
            tarball_path=Path("/path/to/snapshot.tar.gz"),
        )
        assert snapshot.id == "20251107-120000"
        assert snapshot.timestamp == now
        assert snapshot.message == "Test snapshot"
        assert snapshot.collection_name == "test"
        assert snapshot.artifact_count == 5


class TestSnapshotManager:
    """Test SnapshotManager class."""

    def test_init_creates_directory(self, temp_snapshots_dir):
        """Test that initialization creates snapshots directory."""
        manager = SnapshotManager(temp_snapshots_dir)
        assert temp_snapshots_dir.exists()
        assert temp_snapshots_dir.is_dir()

    def test_create_snapshot(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test creating a snapshot."""
        snapshot = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Initial snapshot"
        )

        assert snapshot.id is not None
        assert snapshot.message == "Initial snapshot"
        assert snapshot.collection_name == "test-collection"
        assert snapshot.artifact_count == 3  # 2 skills + 1 command
        assert snapshot.tarball_path.exists()
        assert snapshot.tarball_path.suffix == ".gz"

        # Verify tarball contains collection
        with tarfile.open(snapshot.tarball_path, "r:gz") as tar:
            names = tar.getnames()
            assert any("collection.toml" in name for name in names)

    def test_create_snapshot_nonexistent_collection_raises_error(
        self, tmp_path, snapshot_manager
    ):
        """Test creating snapshot of non-existent collection raises error."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="not found"):
            snapshot_manager.create_snapshot(nonexistent, "test", "message")

    def test_list_snapshots_empty(self, snapshot_manager):
        """Test listing snapshots when none exist."""
        snapshots, next_cursor = snapshot_manager.list_snapshots("test-collection")
        assert snapshots == []
        assert next_cursor is None

    def test_list_snapshots_single(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test listing single snapshot."""
        snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Snapshot 1"
        )

        snapshots, next_cursor = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 1
        assert snapshots[0].message == "Snapshot 1"
        assert snapshots[0].collection_name == "test-collection"
        assert next_cursor is None

    def test_list_snapshots_multiple_sorted(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test listing multiple snapshots sorted by timestamp."""
        # Create snapshots (they should have different IDs due to timestamps)
        import time

        snapshot1 = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Snapshot 1"
        )
        time.sleep(0.01)  # Small delay to ensure different timestamps
        snapshot2 = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Snapshot 2"
        )
        time.sleep(0.01)
        snapshot3 = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Snapshot 3"
        )

        snapshots, next_cursor = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 3

        # Should be sorted newest first
        assert snapshots[0].message == "Snapshot 3"
        assert snapshots[1].message == "Snapshot 2"
        assert snapshots[2].message == "Snapshot 1"
        assert next_cursor is None

    def test_restore_snapshot(
        self, temp_collection_path, snapshot_manager, tmp_path, temp_snapshots_dir
    ):
        """Test restoring a snapshot."""
        # Create snapshot
        snapshot = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Before changes"
        )

        # Modify collection
        (temp_collection_path / "collection.toml").write_text("# Modified")
        (temp_collection_path / "skills" / "skill3").mkdir()

        # Restore snapshot to new location
        restore_path = tmp_path / "restored"
        snapshot_manager.restore_snapshot(snapshot, restore_path)

        # Verify restored collection
        assert restore_path.exists()
        assert (restore_path / "collection.toml").exists()
        assert (restore_path / "skills" / "skill1").exists()
        assert (restore_path / "skills" / "skill2").exists()
        assert not (restore_path / "skills" / "skill3").exists()  # Should not exist

        # Check content is original
        content = (restore_path / "collection.toml").read_text()
        assert content == "# Test manifest"

    def test_restore_snapshot_nonexistent_raises_error(
        self, snapshot_manager, tmp_path, temp_snapshots_dir
    ):
        """Test restoring non-existent snapshot raises error."""
        snapshot = Snapshot(
            id="20251107-120000",
            timestamp=datetime.utcnow(),
            message="Test",
            collection_name="test",
            artifact_count=0,
            tarball_path=tmp_path / "nonexistent.tar.gz",
        )

        with pytest.raises(FileNotFoundError, match="not found"):
            snapshot_manager.restore_snapshot(snapshot, tmp_path / "restore")

    def test_delete_snapshot(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test deleting a snapshot."""
        snapshot = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "To delete"
        )

        tarball_path = snapshot.tarball_path
        assert tarball_path.exists()

        snapshot_manager.delete_snapshot(snapshot)

        # Verify tarball deleted
        assert not tarball_path.exists()

        # Verify metadata updated
        snapshots, _ = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 0

    def test_delete_snapshot_missing_tarball(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test deleting snapshot when tarball is already missing."""
        snapshot = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Test"
        )

        # Manually delete tarball
        snapshot.tarball_path.unlink()

        # Should not raise error
        snapshot_manager.delete_snapshot(snapshot)

        snapshots, _ = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 0

    def test_cleanup_old_snapshots_under_limit(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test cleanup when under limit doesn't delete anything."""
        import time

        for i in range(3):
            snapshot_manager.create_snapshot(
                temp_collection_path, "test-collection", f"Snapshot {i}"
            )
            time.sleep(0.01)

        deleted = snapshot_manager.cleanup_old_snapshots(
            "test-collection", keep_count=10
        )

        assert len(deleted) == 0
        snapshots, _ = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 3

    def test_cleanup_old_snapshots_over_limit(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test cleanup deletes old snapshots over limit."""
        import time

        for i in range(5):
            snapshot_manager.create_snapshot(
                temp_collection_path, "test-collection", f"Snapshot {i}"
            )
            time.sleep(0.01)

        deleted = snapshot_manager.cleanup_old_snapshots(
            "test-collection", keep_count=2
        )

        assert len(deleted) == 3
        snapshots, _ = snapshot_manager.list_snapshots("test-collection")
        assert len(snapshots) == 2

        # Newest snapshots should be kept
        assert snapshots[0].message == "Snapshot 4"
        assert snapshots[1].message == "Snapshot 3"

    def test_cleanup_deletes_tarballs(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test that cleanup actually deletes tarball files."""
        import time

        tarballs = []
        for i in range(5):
            snapshot = snapshot_manager.create_snapshot(
                temp_collection_path, "test-collection", f"Snapshot {i}"
            )
            tarballs.append(snapshot.tarball_path)
            time.sleep(0.01)

        # All tarballs exist
        for tarball in tarballs:
            assert tarball.exists()

        deleted = snapshot_manager.cleanup_old_snapshots(
            "test-collection", keep_count=2
        )

        # Old tarballs should be deleted
        assert len(deleted) == 3
        for i in range(3):
            assert not tarballs[i].exists()  # Old ones deleted

        # New tarballs should still exist
        for i in range(3, 5):
            assert tarballs[i].exists()  # Kept

    def test_snapshot_id_format(
        self, temp_collection_path, snapshot_manager, temp_snapshots_dir
    ):
        """Test that snapshot ID has correct format."""
        snapshot = snapshot_manager.create_snapshot(
            temp_collection_path, "test-collection", "Test"
        )

        # ID should be timestamp-based: YYYYMMDD-HHMMSS-mmmmmm (with microseconds)
        assert len(snapshot.id) == 22  # YYYYMMDD-HHMMSS-mmmmmm
        assert snapshot.id[8] == "-"
        assert snapshot.id[15] == "-"
        assert snapshot.id[:8].isdigit()
        assert snapshot.id[9:15].isdigit()
        assert snapshot.id[16:].isdigit()
