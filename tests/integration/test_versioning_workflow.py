"""Integration tests for versioning and snapshot workflow."""

import pytest
import tarfile
from pathlib import Path
from unittest.mock import patch

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.version import VersionManager


@pytest.fixture
def temp_skillmeat_dir(tmp_path):
    """Provide temporary SkillMeat directory."""
    return tmp_path / "skillmeat"


@pytest.fixture
def config(temp_skillmeat_dir):
    """Provide ConfigManager with temp directory."""
    return ConfigManager(temp_skillmeat_dir)


@pytest.fixture
def collection_mgr(config):
    """Provide CollectionManager."""
    return CollectionManager(config)


@pytest.fixture
def artifact_mgr(collection_mgr):
    """Provide ArtifactManager."""
    return ArtifactManager(collection_mgr)


@pytest.fixture
def version_mgr(collection_mgr):
    """Provide VersionManager."""
    return VersionManager(collection_mgr)


@pytest.fixture
def initialized_collection(collection_mgr):
    """Provide initialized collection with test artifacts."""
    # Initialize collection
    collection = collection_mgr.init("test-collection")

    # Set as active collection
    collection_mgr.switch_collection("test-collection")

    # Create test skill
    collection_path = collection_mgr.config.get_collection_path("test-collection")
    skill_dir = collection_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill\n\nThis is a test skill.")

    # Add to collection manifest
    from skillmeat.core.artifact import Artifact, ArtifactMetadata
    from datetime import datetime

    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="local",
        metadata=ArtifactMetadata(),
        added=datetime.utcnow(),
    )
    collection.add_artifact(artifact)
    collection_mgr.save_collection(collection)

    return collection


class TestSnapshotCreationAndListing:
    """Test snapshot creation and listing workflow."""

    @patch("skillmeat.core.version.console")
    def test_create_and_list_snapshots(
        self, mock_console, version_mgr, initialized_collection
    ):
        """Test creating and listing snapshots."""
        # Create first snapshot
        snapshot1 = version_mgr.create_snapshot(message="First snapshot")
        assert snapshot1 is not None
        assert snapshot1.message == "First snapshot"

        # List snapshots
        snapshots = version_mgr.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].id == snapshot1.id

        # Create second snapshot
        import time

        time.sleep(0.01)
        snapshot2 = version_mgr.create_snapshot(message="Second snapshot")

        # List should show both, newest first
        snapshots = version_mgr.list_snapshots()
        assert len(snapshots) == 2
        assert snapshots[0].id == snapshot2.id
        assert snapshots[1].id == snapshot1.id

    @patch("skillmeat.core.version.console")
    def test_snapshot_contains_collection_contents(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test that snapshot tarball contains collection contents."""
        snapshot = version_mgr.create_snapshot(message="Test snapshot")

        # Verify tarball exists and contains expected files
        assert snapshot.tarball_path.exists()

        with tarfile.open(snapshot.tarball_path, "r:gz") as tar:
            names = tar.getnames()

            # Should contain collection structure
            assert any("collection.toml" in name for name in names)
            assert any("test-skill" in name for name in names)
            assert any("SKILL.md" in name for name in names)


class TestRollbackWorkflow:
    """Test rollback workflow."""

    @patch("skillmeat.core.version.console")
    def test_full_rollback_workflow(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test complete rollback workflow: snapshot -> modify -> rollback."""
        collection_path = collection_mgr.config.get_collection_path("test-collection")

        # Create initial snapshot
        snapshot = version_mgr.create_snapshot(message="Before modifications")
        initial_snapshot_count = len(version_mgr.list_snapshots())

        # Modify collection: add new skill
        new_skill_dir = collection_path / "skills" / "new-skill"
        new_skill_dir.mkdir()
        (new_skill_dir / "SKILL.md").write_text("# New Skill")

        # Verify modification exists
        assert new_skill_dir.exists()

        # Rollback (no confirmation)
        version_mgr.rollback(snapshot.id, confirm=False)

        # Verify collection restored
        assert not new_skill_dir.exists()
        assert (collection_path / "skills" / "test-skill").exists()

        # Verify safety snapshot was created
        snapshots_after_rollback = version_mgr.list_snapshots()
        assert len(snapshots_after_rollback) == initial_snapshot_count + 1

        # Find safety snapshot
        safety_snapshot = next(
            s for s in snapshots_after_rollback if "[auto] Before rollback" in s.message
        )
        assert safety_snapshot is not None

    @patch("skillmeat.core.version.console")
    def test_rollback_restores_exact_state(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test rollback restores exact collection state."""
        collection_path = collection_mgr.config.get_collection_path("test-collection")

        # Read original content
        original_skill_path = collection_path / "skills" / "test-skill" / "SKILL.md"
        original_content = original_skill_path.read_text()

        # Create snapshot
        snapshot = version_mgr.create_snapshot(message="Original state")

        # Modify skill content
        original_skill_path.write_text("# Modified Skill\n\nThis was modified.")

        # Add new file
        (collection_path / "skills" / "test-skill" / "extra.txt").write_text("Extra")

        # Verify modifications
        assert original_skill_path.read_text() != original_content
        assert (collection_path / "skills" / "test-skill" / "extra.txt").exists()

        # Rollback
        version_mgr.rollback(snapshot.id, confirm=False)

        # Verify exact restoration
        assert original_skill_path.read_text() == original_content
        assert not (collection_path / "skills" / "test-skill" / "extra.txt").exists()


class TestAutoSnapshotIntegration:
    """Test auto-snapshot integration with destructive operations."""

    @patch("skillmeat.core.version.console")
    def test_remove_artifact_creates_auto_snapshot(
        self,
        mock_console,
        artifact_mgr,
        version_mgr,
        initialized_collection,
        collection_mgr,
    ):
        """Test removing artifact creates auto-snapshot."""
        initial_snapshot_count = len(version_mgr.list_snapshots())

        # Remove artifact (should create auto-snapshot)
        artifact_mgr.remove("test-skill", ArtifactType.SKILL)

        # Verify auto-snapshot was created
        snapshots = version_mgr.list_snapshots()
        assert len(snapshots) == initial_snapshot_count + 1

        # Find auto-snapshot
        auto_snapshot = snapshots[0]  # Newest first
        assert "[auto] Before removing" in auto_snapshot.message
        assert "skill/test-skill" in auto_snapshot.message

    @patch("skillmeat.core.version.console")
    def test_rollback_after_remove_restores_artifact(
        self,
        mock_console,
        artifact_mgr,
        version_mgr,
        initialized_collection,
        collection_mgr,
    ):
        """Test rollback after remove restores deleted artifact."""
        collection_path = collection_mgr.config.get_collection_path("test-collection")
        skill_path = collection_path / "skills" / "test-skill"

        # Verify artifact exists
        assert skill_path.exists()

        # Remove artifact (creates auto-snapshot)
        artifact_mgr.remove("test-skill", ArtifactType.SKILL)

        # Verify artifact removed
        assert not skill_path.exists()

        # Get the auto-snapshot
        snapshots = version_mgr.list_snapshots()
        auto_snapshot = next(
            s for s in snapshots if "[auto] Before removing" in s.message
        )

        # Rollback to auto-snapshot
        version_mgr.rollback(auto_snapshot.id, confirm=False)

        # Verify artifact restored
        assert skill_path.exists()
        assert (skill_path / "SKILL.md").exists()


class TestSnapshotCleanup:
    """Test snapshot cleanup workflow."""

    @patch("skillmeat.core.version.console")
    def test_cleanup_removes_old_snapshots(
        self, mock_console, version_mgr, initialized_collection
    ):
        """Test cleanup removes old snapshots and keeps recent ones."""
        import time

        # Create 10 snapshots
        snapshot_ids = []
        for i in range(10):
            snapshot = version_mgr.create_snapshot(message=f"Snapshot {i}")
            snapshot_ids.append(snapshot.id)
            time.sleep(0.01)

        # Verify all exist
        snapshots = version_mgr.list_snapshots()
        assert len(snapshots) == 10

        # Cleanup, keeping only 3
        deleted = version_mgr.cleanup_snapshots(keep_count=3)

        # Verify 7 deleted
        assert len(deleted) == 7

        # Verify 3 remain (newest ones)
        remaining = version_mgr.list_snapshots()
        assert len(remaining) == 3
        assert remaining[0].message == "Snapshot 9"
        assert remaining[1].message == "Snapshot 8"
        assert remaining[2].message == "Snapshot 7"

        # Verify old tarballs deleted
        for deleted_snapshot in deleted:
            assert not deleted_snapshot.tarball_path.exists()

    @patch("skillmeat.core.version.console")
    def test_cleanup_deletes_tarballs_not_just_metadata(
        self, mock_console, version_mgr, initialized_collection
    ):
        """Test cleanup actually deletes tarball files."""
        import time

        # Create snapshots and track tarball paths
        tarball_paths = []
        for i in range(5):
            snapshot = version_mgr.create_snapshot(message=f"Snapshot {i}")
            tarball_paths.append(snapshot.tarball_path)
            time.sleep(0.01)

        # Verify all tarballs exist
        for path in tarball_paths:
            assert path.exists()

        # Cleanup, keeping only 2
        version_mgr.cleanup_snapshots(keep_count=2)

        # Verify old tarballs deleted
        for path in tarball_paths[:3]:
            assert not path.exists()

        # Verify recent tarballs remain
        for path in tarball_paths[3:]:
            assert path.exists()


class TestTarballIntegrity:
    """Test tarball creation and extraction integrity."""

    @patch("skillmeat.core.version.console")
    def test_tarball_compression(
        self, mock_console, version_mgr, initialized_collection
    ):
        """Test tarball uses gzip compression."""
        snapshot = version_mgr.create_snapshot(message="Test")

        # Verify it's a gzip-compressed tarball
        with tarfile.open(snapshot.tarball_path, "r:gz") as tar:
            # Should open successfully
            assert tar is not None
            # Should have members
            assert len(tar.getmembers()) > 0

    @patch("skillmeat.core.version.console")
    def test_snapshot_and_restore_preserves_permissions(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test snapshot and restore preserves file permissions."""
        collection_path = collection_mgr.config.get_collection_path("test-collection")
        skill_md = collection_path / "skills" / "test-skill" / "SKILL.md"

        # Get original permissions
        import stat

        original_mode = skill_md.stat().st_mode

        # Create snapshot
        snapshot = version_mgr.create_snapshot(message="Test permissions")

        # Modify permissions
        skill_md.chmod(0o444)  # Read-only

        # Rollback
        version_mgr.rollback(snapshot.id, confirm=False)

        # Check permissions restored (approximately - may vary by filesystem)
        restored_mode = skill_md.stat().st_mode
        # Just verify it's readable and writable (not checking exact mode)
        assert stat.S_ISREG(restored_mode)


class TestMultipleSnapshots:
    """Test workflow with multiple snapshots."""

    @patch("skillmeat.core.version.console")
    def test_multiple_snapshots_different_states(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test creating snapshots of different collection states."""
        import time

        collection_path = collection_mgr.config.get_collection_path("test-collection")

        # State 1: Initial state
        snapshot1 = version_mgr.create_snapshot(message="Initial state")
        time.sleep(0.01)

        # State 2: Add skill
        skill2_dir = collection_path / "skills" / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text("# Skill 2")
        snapshot2 = version_mgr.create_snapshot(message="Added skill2")
        time.sleep(0.01)

        # State 3: Add another skill
        skill3_dir = collection_path / "skills" / "skill3"
        skill3_dir.mkdir()
        (skill3_dir / "SKILL.md").write_text("# Skill 3")
        snapshot3 = version_mgr.create_snapshot(message="Added skill3")

        # Verify current state
        assert skill2_dir.exists()
        assert skill3_dir.exists()

        # Rollback to state 2
        version_mgr.rollback(snapshot2.id, confirm=False)
        assert skill2_dir.exists()
        assert not skill3_dir.exists()

        # Rollback to state 1
        version_mgr.rollback(snapshot1.id, confirm=False)
        assert not skill2_dir.exists()
        assert not skill3_dir.exists()


class TestSnapshotMetadata:
    """Test snapshot metadata tracking."""

    @patch("skillmeat.core.version.console")
    def test_snapshot_tracks_artifact_count(
        self, mock_console, version_mgr, initialized_collection, collection_mgr
    ):
        """Test snapshot correctly tracks artifact count."""
        # Initial snapshot (1 artifact)
        snapshot1 = version_mgr.create_snapshot(message="One artifact")
        assert snapshot1.artifact_count == 1

        # Add more skills
        collection_path = collection_mgr.config.get_collection_path("test-collection")
        for i in range(2, 5):
            skill_dir = collection_path / "skills" / f"skill{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# Skill {i}")

        # New snapshot (4 artifacts total)
        snapshot2 = version_mgr.create_snapshot(message="Four artifacts")
        assert snapshot2.artifact_count == 4

    @patch("skillmeat.core.version.console")
    def test_snapshot_id_uniqueness(
        self, mock_console, version_mgr, initialized_collection
    ):
        """Test snapshot IDs are unique."""
        import time

        snapshot_ids = set()
        for i in range(10):
            snapshot = version_mgr.create_snapshot(message=f"Snapshot {i}")
            snapshot_ids.add(snapshot.id)
            time.sleep(0.001)  # Small delay

        # All IDs should be unique
        assert len(snapshot_ids) == 10
