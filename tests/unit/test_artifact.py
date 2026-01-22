"""Unit tests for artifact data models."""

import pytest
from datetime import datetime

from skillmeat.core.artifact import (
    Artifact,
    ArtifactMetadata,
    ArtifactType,
    UpdateStrategy,
)


class TestArtifactType:
    """Test ArtifactType enum."""

    def test_artifact_types(self):
        """Test all artifact types are defined."""
        assert ArtifactType.SKILL == "skill"
        assert ArtifactType.COMMAND == "command"
        assert ArtifactType.AGENT == "agent"


class TestUpdateStrategy:
    """Test UpdateStrategy enum."""

    def test_update_strategies(self):
        """Test all update strategies are defined."""
        assert UpdateStrategy.PROMPT == "prompt"
        assert UpdateStrategy.TAKE_UPSTREAM == "upstream"
        assert UpdateStrategy.KEEP_LOCAL == "local"


class TestArtifactMetadata:
    """Test ArtifactMetadata dataclass."""

    def test_create_empty_metadata(self):
        """Test creating empty metadata."""
        metadata = ArtifactMetadata()
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.author is None
        assert metadata.license is None
        assert metadata.version is None
        assert metadata.tags == []
        assert metadata.dependencies == []
        assert metadata.extra == {}

    def test_create_metadata_with_values(self):
        """Test creating metadata with values."""
        metadata = ArtifactMetadata(
            title="Test Skill",
            description="A test skill",
            author="Test Author",
            license="MIT",
            version="1.0.0",
            tags=["test", "example"],
            dependencies=["dep1", "dep2"],
            extra={"key": "value"},
        )
        assert metadata.title == "Test Skill"
        assert metadata.description == "A test skill"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.version == "1.0.0"
        assert metadata.tags == ["test", "example"]
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.extra == {"key": "value"}

    def test_to_dict_empty(self):
        """Test serializing empty metadata to dict."""
        metadata = ArtifactMetadata()
        result = metadata.to_dict()
        assert result == {}

    def test_to_dict_with_values(self):
        """Test serializing metadata to dict."""
        metadata = ArtifactMetadata(
            title="Test Skill",
            description="A test skill",
            tags=["test"],
        )
        result = metadata.to_dict()
        assert result == {
            "title": "Test Skill",
            "description": "A test skill",
            "tags": ["test"],
        }

    def test_from_dict_empty(self):
        """Test deserializing empty dict."""
        metadata = ArtifactMetadata.from_dict({})
        assert metadata.title is None
        assert metadata.tags == []

    def test_from_dict_with_values(self):
        """Test deserializing dict to metadata."""
        data = {
            "title": "Test Skill",
            "description": "A test skill",
            "author": "Test Author",
            "license": "MIT",
            "version": "1.0.0",
            "tags": ["test", "example"],
            "dependencies": ["dep1"],
            "extra": {"key": "value"},
        }
        metadata = ArtifactMetadata.from_dict(data)
        assert metadata.title == "Test Skill"
        assert metadata.description == "A test skill"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.version == "1.0.0"
        assert metadata.tags == ["test", "example"]
        assert metadata.dependencies == ["dep1"]
        assert metadata.extra == {"key": "value"}


class TestArtifact:
    """Test Artifact dataclass."""

    def test_create_artifact(self):
        """Test creating an artifact."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata(title="Test")
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="github",
            metadata=metadata,
            added=now,
        )
        assert artifact.name == "test-skill"
        assert artifact.type == ArtifactType.SKILL
        assert artifact.path == "skills/test-skill/"
        assert artifact.origin == "github"
        assert artifact.metadata == metadata
        assert artifact.added == now

    def test_create_artifact_with_string_type(self):
        """Test creating artifact with string type (auto-converted)."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-command",
            type="command",  # String, not enum
            path="commands/test.md",
            origin="local",
            metadata=metadata,
            added=now,
        )
        assert artifact.type == ArtifactType.COMMAND

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        with pytest.raises(ValueError, match="cannot be empty"):
            Artifact(
                name="",
                type=ArtifactType.SKILL,
                path="skills/test/",
                origin="github",
                metadata=metadata,
                added=now,
            )

    def test_invalid_origin_raises_error(self):
        """Test that invalid origin raises ValueError."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        with pytest.raises(ValueError, match="Invalid origin"):
            Artifact(
                name="test",
                type=ArtifactType.SKILL,
                path="skills/test/",
                origin="invalid",
                metadata=metadata,
                added=now,
            )

    def test_marketplace_origin(self):
        """Test creating artifact with marketplace origin."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
            origin_source="github",
        )
        assert artifact.origin == "marketplace"
        assert artifact.origin_source == "github"

    def test_marketplace_origin_with_gitlab(self):
        """Test creating artifact with marketplace origin from gitlab."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
            origin_source="gitlab",
        )
        assert artifact.origin == "marketplace"
        assert artifact.origin_source == "gitlab"

    def test_marketplace_origin_with_bitbucket(self):
        """Test creating artifact with marketplace origin from bitbucket."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
            origin_source="bitbucket",
        )
        assert artifact.origin == "marketplace"
        assert artifact.origin_source == "bitbucket"

    def test_origin_source_requires_marketplace_origin(self):
        """Test that origin_source raises error when origin is not marketplace."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        with pytest.raises(ValueError, match="origin_source can only be set when origin is 'marketplace'"):
            Artifact(
                name="test",
                type=ArtifactType.SKILL,
                path="skills/test/",
                origin="github",
                metadata=metadata,
                added=now,
                origin_source="github",
            )

    def test_origin_source_invalid_value(self):
        """Test that invalid origin_source raises ValueError."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        with pytest.raises(ValueError, match="Invalid origin_source"):
            Artifact(
                name="test",
                type=ArtifactType.SKILL,
                path="skills/test/",
                origin="marketplace",
                metadata=metadata,
                added=now,
                origin_source="invalid",
            )

    def test_marketplace_without_origin_source(self):
        """Test that marketplace origin can be created without origin_source."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
        )
        assert artifact.origin == "marketplace"
        assert artifact.origin_source is None

    def test_composite_key(self):
        """Test composite key generation."""
        now = datetime.utcnow()
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="github",
            metadata=metadata,
            added=now,
        )
        assert artifact.composite_key() == ("test-skill", "skill")

    def test_to_dict_minimal(self):
        """Test serializing artifact with minimal fields."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        metadata = ArtifactMetadata()
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="local",
            metadata=metadata,
            added=now,
        )
        result = artifact.to_dict()
        assert result == {
            "name": "test-skill",
            "type": "skill",
            "path": "skills/test-skill/",
            "origin": "local",
            "added": "2025-11-07T12:00:00",
        }

    def test_to_dict_full(self):
        """Test serializing artifact with all fields."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        updated = datetime(2025, 11, 7, 14, 0, 0)
        metadata = ArtifactMetadata(title="Test", description="A test")
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="github",
            metadata=metadata,
            added=now,
            upstream="https://github.com/user/repo",
            version_spec="latest",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            last_updated=updated,
            tags=["python"],
        )
        result = artifact.to_dict()
        assert result["name"] == "test-skill"
        assert result["type"] == "skill"
        assert result["origin"] == "github"
        assert result["added"] == "2025-11-07T12:00:00"
        assert result["upstream"] == "https://github.com/user/repo"
        assert result["version_spec"] == "latest"
        assert result["resolved_sha"] == "abc123"
        assert result["resolved_version"] == "v1.0.0"
        assert result["last_updated"] == "2025-11-07T14:00:00"
        assert result["tags"] == ["python"]
        assert result["metadata"]["title"] == "Test"

    def test_from_dict_minimal(self):
        """Test deserializing artifact with minimal fields."""
        data = {
            "name": "test-skill",
            "type": "skill",
            "path": "skills/test-skill/",
            "origin": "local",
            "added": "2025-11-07T12:00:00",
        }
        artifact = Artifact.from_dict(data)
        assert artifact.name == "test-skill"
        assert artifact.type == ArtifactType.SKILL
        assert artifact.path == "skills/test-skill/"
        assert artifact.origin == "local"
        assert artifact.added == datetime(2025, 11, 7, 12, 0, 0)
        assert artifact.upstream is None
        assert artifact.tags == []

    def test_from_dict_full(self):
        """Test deserializing artifact with all fields."""
        data = {
            "name": "test-skill",
            "type": "skill",
            "path": "skills/test-skill/",
            "origin": "github",
            "added": "2025-11-07T12:00:00",
            "upstream": "https://github.com/user/repo",
            "version_spec": "latest",
            "resolved_sha": "abc123",
            "resolved_version": "v1.0.0",
            "last_updated": "2025-11-07T14:00:00",
            "tags": ["python"],
            "metadata": {
                "title": "Test",
                "description": "A test",
            },
        }
        artifact = Artifact.from_dict(data)
        assert artifact.name == "test-skill"
        assert artifact.type == ArtifactType.SKILL
        assert artifact.upstream == "https://github.com/user/repo"
        assert artifact.version_spec == "latest"
        assert artifact.resolved_sha == "abc123"
        assert artifact.resolved_version == "v1.0.0"
        assert artifact.last_updated == datetime(2025, 11, 7, 14, 0, 0)
        assert artifact.tags == ["python"]
        assert artifact.metadata.title == "Test"
        assert artifact.metadata.description == "A test"

    def test_roundtrip_serialization(self):
        """Test that artifact can be serialized and deserialized."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        metadata = ArtifactMetadata(title="Test", tags=["python"])
        original = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="github",
            metadata=metadata,
            added=now,
            upstream="https://github.com/user/repo",
            tags=["coding"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Artifact.from_dict(data)

        # Check all fields match
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.path == original.path
        assert restored.origin == original.origin
        assert restored.added == original.added
        assert restored.upstream == original.upstream
        assert restored.tags == original.tags
        assert restored.metadata.title == original.metadata.title
        assert restored.metadata.tags == original.metadata.tags

    def test_to_dict_marketplace_with_origin_source(self):
        """Test serializing artifact with marketplace origin and origin_source."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        metadata = ArtifactMetadata(title="Test")
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
            upstream="https://github.com/user/repo",
            origin_source="github",
        )
        result = artifact.to_dict()
        assert result["origin"] == "marketplace"
        assert result["origin_source"] == "github"

    def test_from_dict_marketplace_with_origin_source(self):
        """Test deserializing artifact with marketplace origin and origin_source."""
        data = {
            "name": "test-skill",
            "type": "skill",
            "path": "skills/test-skill/",
            "origin": "marketplace",
            "added": "2025-11-07T12:00:00",
            "upstream": "https://github.com/user/repo",
            "origin_source": "github",
        }
        artifact = Artifact.from_dict(data)
        assert artifact.origin == "marketplace"
        assert artifact.origin_source == "github"

    def test_roundtrip_marketplace_origin_source(self):
        """Test roundtrip serialization with marketplace origin and origin_source."""
        now = datetime(2025, 11, 7, 12, 0, 0)
        metadata = ArtifactMetadata(title="Test")
        original = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill/",
            origin="marketplace",
            metadata=metadata,
            added=now,
            upstream="https://github.com/user/repo",
            origin_source="gitlab",
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Artifact.from_dict(data)

        # Check origin fields match
        assert restored.origin == original.origin
        assert restored.origin_source == original.origin_source
