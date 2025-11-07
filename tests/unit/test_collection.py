"""Unit tests for collection data model."""

import pytest
from datetime import datetime

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection


class TestCollection:
    """Test Collection dataclass."""

    def test_create_empty_collection(self):
        """Test creating empty collection."""
        now = datetime.utcnow()
        collection = Collection(
            name="test-collection",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )
        assert collection.name == "test-collection"
        assert collection.version == "1.0.0"
        assert collection.artifacts == []
        assert collection.created == now
        assert collection.updated == now

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="cannot be empty"):
            Collection(
                name="",
                version="1.0.0",
                artifacts=[],
                created=now,
                updated=now,
            )

    def test_add_artifact(self):
        """Test adding artifact to collection."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )

        collection.add_artifact(artifact)
        assert len(collection.artifacts) == 1
        assert collection.artifacts[0] == artifact

    def test_add_duplicate_artifact_raises_error(self):
        """Test that adding duplicate artifact raises ValueError."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        artifact1 = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        artifact2 = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,  # Same name and type
            path="skills/test-skill-2/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )

        collection.add_artifact(artifact1)
        with pytest.raises(ValueError, match="already exists"):
            collection.add_artifact(artifact2)

    def test_add_same_name_different_type_allowed(self):
        """Test that same name with different type is allowed."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        skill = Artifact(
            name="review",
            type=ArtifactType.SKILL,
            path="skills/review/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        command = Artifact(
            name="review",
            type=ArtifactType.COMMAND,  # Same name, different type
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )

        collection.add_artifact(skill)
        collection.add_artifact(command)
        assert len(collection.artifacts) == 2

    def test_find_artifact_by_name_unique(self):
        """Test finding artifact by name when unique."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        collection.add_artifact(artifact)

        found = collection.find_artifact("test-skill")
        assert found == artifact

    def test_find_artifact_by_name_with_type(self):
        """Test finding artifact by name and type."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        skill = Artifact(
            name="review",
            type=ArtifactType.SKILL,
            path="skills/review/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        command = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        collection.add_artifact(skill)
        collection.add_artifact(command)

        found_skill = collection.find_artifact("review", ArtifactType.SKILL)
        found_command = collection.find_artifact("review", ArtifactType.COMMAND)

        assert found_skill == skill
        assert found_command == command

    def test_find_artifact_ambiguous_raises_error(self):
        """Test that finding ambiguous artifact raises ValueError."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        skill = Artifact(
            name="review",
            type=ArtifactType.SKILL,
            path="skills/review/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        command = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        collection.add_artifact(skill)
        collection.add_artifact(command)

        # Without type filter, should raise error
        with pytest.raises(ValueError, match="Ambiguous"):
            collection.find_artifact("review")

    def test_find_artifact_not_found(self):
        """Test finding non-existent artifact returns None."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        found = collection.find_artifact("nonexistent")
        assert found is None

    def test_remove_artifact(self):
        """Test removing artifact from collection."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=now,
        )
        collection.add_artifact(artifact)

        result = collection.remove_artifact("test-skill", ArtifactType.SKILL)
        assert result is True
        assert len(collection.artifacts) == 0

    def test_remove_nonexistent_artifact(self):
        """Test removing non-existent artifact returns False."""
        now = datetime.utcnow()
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        result = collection.remove_artifact("nonexistent", ArtifactType.SKILL)
        assert result is False

    def test_to_dict(self):
        """Test serializing collection to dict."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(title="Test"),
            added=now,
        )
        collection = Collection(
            name="test-collection",
            version="1.0.0",
            artifacts=[artifact],
            created=now,
            updated=now,
        )

        result = collection.to_dict()
        assert result["collection"]["name"] == "test-collection"
        assert result["collection"]["version"] == "1.0.0"
        assert result["collection"]["created"] == "2025-11-07T12:00:00"
        assert result["collection"]["updated"] == "2025-11-07T12:00:00"
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["name"] == "test-skill"

    def test_from_dict(self):
        """Test deserializing collection from dict."""
        data = {
            "collection": {
                "name": "test-collection",
                "version": "1.0.0",
                "created": "2025-11-07T12:00:00",
                "updated": "2025-11-07T12:00:00",
            },
            "artifacts": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "path": "skills/test-skill/",
                    "origin": "local",
                    "added": "2025-11-07T12:00:00",
                }
            ],
        }

        collection = Collection.from_dict(data)
        assert collection.name == "test-collection"
        assert collection.version == "1.0.0"
        assert collection.created == datetime(2025, 11, 7, 12, 0, 0)
        assert collection.updated == datetime(2025, 11, 7, 12, 0, 0)
        assert len(collection.artifacts) == 1
        assert collection.artifacts[0].name == "test-skill"

    def test_roundtrip_serialization(self):
        """Test that collection can be serialized and deserialized."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        artifact1 = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=ArtifactMetadata(title="Test"),
            added=now,
        )
        artifact2 = Artifact(
            name="test-command",
            type=ArtifactType.COMMAND,
            path="commands/test.md",
            origin="github",
            metadata=ArtifactMetadata(),
            added=now,
        )
        original = Collection(
            name="test-collection",
            version="1.0.0",
            artifacts=[artifact1, artifact2],
            created=now,
            updated=now,
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Collection.from_dict(data)

        # Check all fields match
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.created == original.created
        assert restored.updated == original.updated
        assert len(restored.artifacts) == len(original.artifacts)
        assert restored.artifacts[0].name == original.artifacts[0].name
        assert restored.artifacts[1].name == original.artifacts[1].name
