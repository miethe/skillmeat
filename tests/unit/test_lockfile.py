"""Unit tests for LockManager."""

import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.artifact import ArtifactType
from skillmeat.storage.lockfile import LockEntry, LockManager


@pytest.fixture
def temp_collection_path(tmp_path):
    """Provide temporary collection directory."""
    collection_path = tmp_path / "test-collection"
    collection_path.mkdir(parents=True)
    return collection_path


@pytest.fixture
def lock_manager():
    """Provide LockManager instance."""
    return LockManager()


class TestLockEntry:
    """Test LockEntry dataclass."""

    def test_create_lock_entry(self):
        """Test creating a lock entry."""
        now = datetime.utcnow()
        entry = LockEntry(
            name="test-skill",
            type="skill",
            upstream="https://github.com/user/repo",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            content_hash="hash123",
            fetched=now,
        )
        assert entry.name == "test-skill"
        assert entry.type == "skill"
        assert entry.upstream == "https://github.com/user/repo"
        assert entry.resolved_sha == "abc123"
        assert entry.resolved_version == "v1.0.0"
        assert entry.content_hash == "hash123"
        assert entry.fetched == now


class TestLockManager:
    """Test LockManager class."""

    def test_read_nonexistent_returns_empty(self, temp_collection_path, lock_manager):
        """Test reading non-existent lock file returns empty dict."""
        entries = lock_manager.read(temp_collection_path)
        assert entries == {}

    def test_write_and_read_empty(self, temp_collection_path, lock_manager):
        """Test writing and reading empty lock file."""
        lock_manager.write(temp_collection_path, {})

        entries = lock_manager.read(temp_collection_path)
        assert entries == {}
        assert (temp_collection_path / "collection.lock").exists()

    def test_write_and_read_single_entry(self, temp_collection_path, lock_manager):
        """Test writing and reading single lock entry."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        entry = LockEntry(
            name="test-skill",
            type="skill",
            upstream="https://github.com/user/repo",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            content_hash="hash123",
            fetched=now,
        )
        entries = {("test-skill", "skill"): entry}

        lock_manager.write(temp_collection_path, entries)

        # Read back
        loaded = lock_manager.read(temp_collection_path)
        assert len(loaded) == 1
        assert ("test-skill", "skill") in loaded

        loaded_entry = loaded[("test-skill", "skill")]
        assert loaded_entry.name == "test-skill"
        assert loaded_entry.type == "skill"
        assert loaded_entry.upstream == "https://github.com/user/repo"
        assert loaded_entry.resolved_sha == "abc123"
        assert loaded_entry.resolved_version == "v1.0.0"
        assert loaded_entry.content_hash == "hash123"
        assert loaded_entry.fetched == now

    def test_write_and_read_multiple_entries(self, temp_collection_path, lock_manager):
        """Test writing and reading multiple lock entries."""
        now = datetime(2025, 11, 7, 12, 0, 0)

        entry1 = LockEntry(
            name="skill1",
            type="skill",
            upstream="https://github.com/user/repo1",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            content_hash="hash1",
            fetched=now,
        )
        entry2 = LockEntry(
            name="command1",
            type="command",
            upstream=None,  # Local artifact
            resolved_sha=None,
            resolved_version=None,
            content_hash="hash2",
            fetched=now,
        )
        entry3 = LockEntry(
            name="review",  # Same name as entry2 but different type
            type="skill",
            upstream="https://github.com/user/repo2",
            resolved_sha="def456",
            resolved_version="v2.0.0",
            content_hash="hash3",
            fetched=now,
        )

        entries = {
            ("skill1", "skill"): entry1,
            ("command1", "command"): entry2,
            ("review", "skill"): entry3,
        }

        lock_manager.write(temp_collection_path, entries)

        # Read back
        loaded = lock_manager.read(temp_collection_path)
        assert len(loaded) == 3
        assert loaded[("skill1", "skill")].name == "skill1"
        assert loaded[("command1", "command")].name == "command1"
        assert loaded[("review", "skill")].name == "review"

        # Check that local artifact has None values preserved
        local_entry = loaded[("command1", "command")]
        assert local_entry.upstream is None
        assert local_entry.resolved_sha is None
        assert local_entry.resolved_version is None

    def test_update_entry_new(self, temp_collection_path, lock_manager):
        """Test updating a new entry."""
        lock_manager.update_entry(
            temp_collection_path,
            "test-skill",
            ArtifactType.SKILL,
            "https://github.com/user/repo",
            "abc123",
            "v1.0.0",
            "hash123",
        )

        entries = lock_manager.read(temp_collection_path)
        assert len(entries) == 1
        entry = entries[("test-skill", "skill")]
        assert entry.name == "test-skill"
        assert entry.upstream == "https://github.com/user/repo"
        assert entry.resolved_sha == "abc123"

    def test_update_entry_existing(self, temp_collection_path, lock_manager):
        """Test updating an existing entry."""
        now = datetime(2025, 11, 7, 12, 0, 0)

        # Create initial entry
        entry = LockEntry(
            name="test-skill",
            type="skill",
            upstream="https://github.com/user/repo",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            content_hash="hash123",
            fetched=now,
        )
        lock_manager.write(temp_collection_path, {("test-skill", "skill"): entry})

        # Update entry
        lock_manager.update_entry(
            temp_collection_path,
            "test-skill",
            ArtifactType.SKILL,
            "https://github.com/user/repo",
            "def456",  # New SHA
            "v2.0.0",  # New version
            "hash456",  # New hash
        )

        # Read and verify
        entries = lock_manager.read(temp_collection_path)
        assert len(entries) == 1
        updated_entry = entries[("test-skill", "skill")]
        assert updated_entry.resolved_sha == "def456"
        assert updated_entry.resolved_version == "v2.0.0"
        assert updated_entry.content_hash == "hash456"
        assert updated_entry.fetched > now  # Should be updated

    def test_get_entry_exists(self, temp_collection_path, lock_manager):
        """Test getting an existing entry."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        entry = LockEntry(
            name="test-skill",
            type="skill",
            upstream="https://github.com/user/repo",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            content_hash="hash123",
            fetched=now,
        )
        lock_manager.write(temp_collection_path, {("test-skill", "skill"): entry})

        found = lock_manager.get_entry(
            temp_collection_path, "test-skill", ArtifactType.SKILL
        )
        assert found is not None
        assert found.name == "test-skill"
        assert found.resolved_sha == "abc123"

    def test_get_entry_not_exists(self, temp_collection_path, lock_manager):
        """Test getting non-existent entry returns None."""
        found = lock_manager.get_entry(
            temp_collection_path, "nonexistent", ArtifactType.SKILL
        )
        assert found is None

    def test_remove_entry(self, temp_collection_path, lock_manager):
        """Test removing an entry."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        entry1 = LockEntry(
            name="skill1",
            type="skill",
            upstream=None,
            resolved_sha=None,
            resolved_version=None,
            content_hash="hash1",
            fetched=now,
        )
        entry2 = LockEntry(
            name="skill2",
            type="skill",
            upstream=None,
            resolved_sha=None,
            resolved_version=None,
            content_hash="hash2",
            fetched=now,
        )

        entries = {
            ("skill1", "skill"): entry1,
            ("skill2", "skill"): entry2,
        }
        lock_manager.write(temp_collection_path, entries)

        # Remove one entry
        lock_manager.remove_entry(temp_collection_path, "skill1", ArtifactType.SKILL)

        # Verify only one entry remains
        loaded = lock_manager.read(temp_collection_path)
        assert len(loaded) == 1
        assert ("skill2", "skill") in loaded
        assert ("skill1", "skill") not in loaded

    def test_remove_nonexistent_entry(self, temp_collection_path, lock_manager):
        """Test removing non-existent entry doesn't raise error."""
        lock_manager.remove_entry(
            temp_collection_path, "nonexistent", ArtifactType.SKILL
        )
        # Should not raise error

    def test_read_corrupted_lock_raises_error(self, temp_collection_path, lock_manager):
        """Test reading corrupted lock file raises error."""
        lock_file = temp_collection_path / "collection.lock"
        lock_file.write_text("invalid toml content [[[")

        with pytest.raises(ValueError, match="Failed to parse"):
            lock_manager.read(temp_collection_path)

    def test_composite_key_in_toml(self, temp_collection_path, lock_manager):
        """Test that composite keys are properly formatted in TOML."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        entry = LockEntry(
            name="review",
            type="skill",
            upstream=None,
            resolved_sha=None,
            resolved_version=None,
            content_hash="hash123",
            fetched=now,
        )
        lock_manager.write(temp_collection_path, {("review", "skill"): entry})

        # Read TOML file directly
        lock_file = temp_collection_path / "collection.lock"
        content = lock_file.read_text()

        # Check that composite key is formatted as "name::type"
        assert "review::skill" in content
