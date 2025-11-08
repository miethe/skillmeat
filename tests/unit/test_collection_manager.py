"""Tests for CollectionManager."""

import pytest
from datetime import datetime
from pathlib import Path
from skillmeat.config import ConfigManager
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path / "config"


@pytest.fixture
def config_manager(temp_config_dir):
    """Create ConfigManager with temp directory."""
    return ConfigManager(config_dir=temp_config_dir)


@pytest.fixture
def collection_manager(config_manager):
    """Create CollectionManager with temp config."""
    return CollectionManager(config=config_manager)


def test_init_creates_default_collection(collection_manager, config_manager):
    """Test initializing new collection creates directories and files."""
    collection = collection_manager.init("test-collection")

    assert collection.name == "test-collection"
    assert collection.version == "1.0.0"
    assert len(collection.artifacts) == 0

    # Check directory structure
    collection_path = config_manager.get_collection_path("test-collection")
    assert collection_path.exists()
    assert (collection_path / "skills").exists()
    assert (collection_path / "commands").exists()
    assert (collection_path / "agents").exists()
    assert (collection_path / "collection.toml").exists()
    assert (collection_path / "collection.lock").exists()


def test_init_default_collection_sets_active(collection_manager, config_manager):
    """Test initializing 'default' collection sets it as active."""
    collection_manager.init("default")
    active = config_manager.get_active_collection()
    assert active == "default"


def test_init_duplicate_collection_raises_error(collection_manager):
    """Test initializing duplicate collection raises ValueError."""
    collection_manager.init("test-collection")

    with pytest.raises(ValueError, match="already exists"):
        collection_manager.init("test-collection")


def test_list_collections_empty(collection_manager):
    """Test listing collections when none exist."""
    collections = collection_manager.list_collections()
    assert collections == []


def test_list_collections_multiple(collection_manager):
    """Test listing multiple collections."""
    collection_manager.init("collection1")
    collection_manager.init("collection2")
    collection_manager.init("collection3")

    collections = collection_manager.list_collections()
    assert set(collections) == {"collection1", "collection2", "collection3"}


def test_get_active_collection_name(collection_manager, config_manager):
    """Test getting active collection name."""
    config_manager.set_active_collection("test-collection")
    active = collection_manager.get_active_collection_name()
    assert active == "test-collection"


def test_switch_collection(collection_manager, config_manager):
    """Test switching active collection."""
    collection_manager.init("collection1")
    collection_manager.init("collection2")

    collection_manager.switch_collection("collection2")
    active = config_manager.get_active_collection()
    assert active == "collection2"


def test_switch_to_nonexistent_collection_raises_error(collection_manager):
    """Test switching to nonexistent collection raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        collection_manager.switch_collection("nonexistent")


def test_load_collection_by_name(collection_manager):
    """Test loading collection by explicit name."""
    collection_manager.init("test-collection")
    loaded = collection_manager.load_collection("test-collection")

    assert loaded.name == "test-collection"
    assert loaded.version == "1.0.0"


def test_load_collection_uses_active_when_none_specified(
    collection_manager, config_manager
):
    """Test loading collection without name uses active collection."""
    collection_manager.init("collection1")
    collection_manager.init("collection2")
    config_manager.set_active_collection("collection2")

    loaded = collection_manager.load_collection()
    assert loaded.name == "collection2"


def test_load_nonexistent_collection_raises_error(collection_manager):
    """Test loading nonexistent collection raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        collection_manager.load_collection("nonexistent")


def test_save_collection_updates_timestamp(collection_manager, config_manager):
    """Test saving collection updates the updated timestamp."""
    collection = collection_manager.init("test-collection")
    original_updated = collection.updated

    # Wait a tiny bit to ensure timestamp changes
    import time

    time.sleep(0.01)

    # Modify and save
    collection.artifacts.append(
        Artifact(
            name="test-artifact",
            type=ArtifactType.SKILL,
            path="skills/test-artifact",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.utcnow(),
        )
    )
    collection_manager.save_collection(collection)

    # Load and verify
    loaded = collection_manager.load_collection("test-collection")
    assert loaded.updated > original_updated
    assert len(loaded.artifacts) == 1


def test_delete_collection(collection_manager, config_manager):
    """Test deleting collection removes directory."""
    collection_manager.init("collection1")
    collection_manager.init("collection2")
    config_manager.set_active_collection("collection2")

    collection_path = config_manager.get_collection_path("collection1")
    assert collection_path.exists()

    collection_manager.delete_collection("collection1", confirm=False)
    assert not collection_path.exists()


def test_delete_active_collection_raises_error(collection_manager, config_manager):
    """Test deleting active collection raises ValueError."""
    collection_manager.init("test-collection")
    config_manager.set_active_collection("test-collection")

    with pytest.raises(ValueError, match="Cannot delete active collection"):
        collection_manager.delete_collection("test-collection", confirm=False)


def test_delete_nonexistent_collection_raises_error(collection_manager):
    """Test deleting nonexistent collection raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        collection_manager.delete_collection("nonexistent", confirm=False)


def test_delete_collection_with_confirm_true_raises_error(collection_manager):
    """Test deleting with confirm=True raises safety error."""
    collection_manager.init("collection1")
    collection_manager.init("collection2")

    with pytest.raises(ValueError, match="Use confirm=False"):
        collection_manager.delete_collection("collection1", confirm=True)


def test_roundtrip_with_artifacts(collection_manager, config_manager):
    """Test saving and loading collection with artifacts."""
    collection = collection_manager.init("test-collection")

    # Add artifacts
    artifact1 = Artifact(
        name="skill1",
        type=ArtifactType.SKILL,
        path="skills/skill1",
        origin="github",
        metadata=ArtifactMetadata(title="Skill 1", description="Test skill"),
        added=datetime.utcnow(),
        upstream="https://github.com/user/repo",
        version_spec="latest",
        resolved_sha="abc123",
        tags=["test", "python"],
    )

    artifact2 = Artifact(
        name="command1",
        type=ArtifactType.COMMAND,
        path="commands/command1.md",
        origin="local",
        metadata=ArtifactMetadata(title="Command 1"),
        added=datetime.utcnow(),
    )

    collection.add_artifact(artifact1)
    collection.add_artifact(artifact2)
    collection_manager.save_collection(collection)

    # Load and verify
    loaded = collection_manager.load_collection("test-collection")
    assert len(loaded.artifacts) == 2

    skill = loaded.find_artifact("skill1", ArtifactType.SKILL)
    assert skill.name == "skill1"
    assert skill.upstream == "https://github.com/user/repo"
    assert skill.tags == ["test", "python"]

    command = loaded.find_artifact("command1", ArtifactType.COMMAND)
    assert command.name == "command1"
    assert command.origin == "local"
