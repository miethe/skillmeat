"""Unit tests for ManifestManager."""

import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.storage.manifest import ManifestManager


@pytest.fixture
def temp_collection_path(tmp_path):
    """Provide temporary collection directory."""
    return tmp_path / "test-collection"


@pytest.fixture
def manifest_manager():
    """Provide ManifestManager instance."""
    return ManifestManager()


class TestManifestManager:
    """Test ManifestManager class."""

    def test_create_empty_collection(self, temp_collection_path, manifest_manager):
        """Test creating an empty collection."""
        collection = manifest_manager.create_empty(temp_collection_path, "test")

        assert collection.name == "test"
        assert collection.version == "1.0.0"
        assert collection.artifacts == []
        assert (temp_collection_path / "collection.toml").exists()

        # Check type directories were created
        assert (temp_collection_path / "skills").is_dir()
        assert (temp_collection_path / "commands").is_dir()
        assert (temp_collection_path / "agents").is_dir()

    def test_create_empty_raises_if_exists(
        self, temp_collection_path, manifest_manager
    ):
        """Test that creating collection raises error if already exists."""
        manifest_manager.create_empty(temp_collection_path, "test")

        with pytest.raises(FileExistsError, match="already exists"):
            manifest_manager.create_empty(temp_collection_path, "test")

    def test_exists_true(self, temp_collection_path, manifest_manager):
        """Test exists returns True when manifest exists."""
        manifest_manager.create_empty(temp_collection_path, "test")
        assert manifest_manager.exists(temp_collection_path) is True

    def test_exists_false(self, temp_collection_path, manifest_manager):
        """Test exists returns False when manifest doesn't exist."""
        assert manifest_manager.exists(temp_collection_path) is False

    def test_write_and_read_empty_collection(
        self, temp_collection_path, manifest_manager
    ):
        """Test writing and reading empty collection."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        temp_collection_path.mkdir(parents=True)
        manifest_manager.write(temp_collection_path, collection)

        # Read back
        loaded = manifest_manager.read(temp_collection_path)
        assert loaded.name == "test"
        assert loaded.version == "1.0.0"
        assert loaded.artifacts == []
        assert loaded.created == now

    def test_write_and_read_collection_with_artifacts(
        self, temp_collection_path, manifest_manager
    ):
        """Test writing and reading collection with artifacts."""
        now = datetime(2025, 11, 7, 12, 0, 0)

        # Create collection with artifacts
        skill = Artifact(
            name="python-skill",
            type=ArtifactType.SKILL,
            path="skills/python-skill/",
            origin="github",
            metadata=ArtifactMetadata(title="Python Skill", description="Coding help"),
            added=now,
            upstream="https://github.com/user/repo",
            version_spec="latest",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            tags=["python", "coding"],
        )
        command = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )

        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[skill, command],
            created=now,
            updated=now,
        )

        temp_collection_path.mkdir(parents=True)
        manifest_manager.write(temp_collection_path, collection)

        # Read back
        loaded = manifest_manager.read(temp_collection_path)
        assert loaded.name == "test"
        assert len(loaded.artifacts) == 2

        # Check skill
        loaded_skill = loaded.artifacts[0]
        assert loaded_skill.name == "python-skill"
        assert loaded_skill.type == ArtifactType.SKILL
        assert loaded_skill.origin == "github"
        assert loaded_skill.upstream == "https://github.com/user/repo"
        assert loaded_skill.tags == ["python", "coding"]
        assert loaded_skill.metadata.title == "Python Skill"

        # Check command
        loaded_command = loaded.artifacts[1]
        assert loaded_command.name == "review"
        assert loaded_command.type == ArtifactType.COMMAND
        assert loaded_command.origin == "local"

    def test_read_nonexistent_raises_error(
        self, temp_collection_path, manifest_manager
    ):
        """Test reading non-existent manifest raises error."""
        with pytest.raises(FileNotFoundError, match="not found"):
            manifest_manager.read(temp_collection_path)

    def test_read_corrupted_toml_raises_error(
        self, temp_collection_path, manifest_manager
    ):
        """Test reading corrupted TOML raises error."""
        temp_collection_path.mkdir(parents=True)
        manifest_file = temp_collection_path / "collection.toml"

        # Write invalid TOML
        manifest_file.write_text("invalid toml content [[[")

        with pytest.raises(ValueError, match="Failed to parse"):
            manifest_manager.read(temp_collection_path)

    def test_write_updates_timestamp(self, temp_collection_path, manifest_manager):
        """Test that write updates the updated timestamp."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        temp_collection_path.mkdir(parents=True)
        manifest_manager.write(temp_collection_path, collection)

        # Read back and check updated timestamp changed
        loaded = manifest_manager.read(temp_collection_path)
        assert loaded.updated > now

    def test_roundtrip_preserves_data(self, temp_collection_path, manifest_manager):
        """Test that roundtrip write/read preserves all data."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        updated = datetime(2025, 11, 7, 14, 0, 0)

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="github",
            metadata=ArtifactMetadata(
                title="Test",
                description="A test skill",
                author="Test Author",
                license="MIT",
                version="1.0.0",
                tags=["test"],
                dependencies=["dep1"],
            ),
            added=now,
            upstream="https://github.com/user/repo",
            version_spec="v1.0.0",
            resolved_sha="abc123def",
            resolved_version="v1.0.0",
            last_updated=updated,
            tags=["coding"],
        )

        collection = Collection(
            name="my-collection",
            version="1.0.0",
            artifacts=[artifact],
            created=now,
            updated=now,
        )

        temp_collection_path.mkdir(parents=True)
        manifest_manager.write(temp_collection_path, collection)

        # Read back
        loaded = manifest_manager.read(temp_collection_path)

        # Verify all fields
        assert loaded.name == collection.name
        assert len(loaded.artifacts) == 1

        loaded_artifact = loaded.artifacts[0]
        assert loaded_artifact.name == artifact.name
        assert loaded_artifact.type == artifact.type
        assert loaded_artifact.path == artifact.path
        assert loaded_artifact.origin == artifact.origin
        assert loaded_artifact.upstream == artifact.upstream
        assert loaded_artifact.version_spec == artifact.version_spec
        assert loaded_artifact.resolved_sha == artifact.resolved_sha
        assert loaded_artifact.resolved_version == artifact.resolved_version
        assert loaded_artifact.last_updated == artifact.last_updated
        assert loaded_artifact.tags == artifact.tags
        assert loaded_artifact.metadata.title == artifact.metadata.title
        assert loaded_artifact.metadata.description == artifact.metadata.description
        assert loaded_artifact.metadata.author == artifact.metadata.author
        assert loaded_artifact.metadata.license == artifact.metadata.license
