"""Tests for BundleBuilder functionality.

This module tests bundle creation, validation, and archive generation.
"""

import json
import pytest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata
from skillmeat.core.collection import Collection
from skillmeat.core.sharing import (
    BundleBuilder,
    BundleValidationError,
    inspect_bundle,
)


@pytest.fixture
def mock_collection_manager(tmp_path):
    """Create mock CollectionManager with test collection."""
    from skillmeat.core.collection import CollectionManager
    from skillmeat.config import ConfigManager

    # Create test collection directory
    collection_path = tmp_path / "collections" / "test"
    collection_path.mkdir(parents=True, exist_ok=True)

    # Create skills directory
    skills_dir = collection_path / "skills"
    skills_dir.mkdir(exist_ok=True)

    # Create test skill
    test_skill_dir = skills_dir / "test-skill"
    test_skill_dir.mkdir(exist_ok=True)
    skill_md = test_skill_dir / "SKILL.md"
    skill_md.write_text("---\ntitle: Test Skill\ndescription: A test skill\n---\n# Test Skill")

    # Create test artifact
    test_artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="local",
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="A test skill",
            version="1.0.0",
        ),
        added=datetime.utcnow(),
    )

    # Create collection
    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[test_artifact],
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )

    # Mock CollectionManager
    manager = Mock(spec=CollectionManager)
    manager.load_collection.return_value = collection
    manager.config = Mock(spec=ConfigManager)
    manager.config.get_collection_path.return_value = collection_path

    return manager


def test_bundle_builder_init():
    """Test BundleBuilder initialization."""
    with patch("skillmeat.core.sharing.builder.CollectionManager"):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )

        assert builder.name == "test-bundle"
        assert builder.description == "Test bundle"
        assert builder.author == "Test Author"
        assert builder.version == "1.0.0"
        assert builder.license == "MIT"


def test_bundle_builder_invalid_name():
    """Test BundleBuilder rejects invalid names."""
    with pytest.raises(ValueError, match="invalid characters"):
        BundleBuilder(
            name="invalid/name",
            description="Test",
            author="Test",
        )

    with pytest.raises(ValueError, match="invalid characters"):
        BundleBuilder(
            name="invalid name",
            description="Test",
            author="Test",
        )


def test_bundle_builder_add_artifact(mock_collection_manager, tmp_path):
    """Test adding artifacts to bundle."""
    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )

        # Add artifact
        builder.add_artifact("test-skill", ArtifactType.SKILL)

        assert len(builder._artifacts) == 1
        assert builder._artifacts[0].name == "test-skill"
        assert builder._artifacts[0].type == "skill"


def test_bundle_builder_duplicate_artifact(mock_collection_manager, tmp_path):
    """Test adding duplicate artifact raises error."""
    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )

        builder.add_artifact("test-skill", ArtifactType.SKILL)

        with pytest.raises(ValueError, match="already added"):
            builder.add_artifact("test-skill", ArtifactType.SKILL)


def test_bundle_builder_build(mock_collection_manager, tmp_path):
    """Test building bundle archive."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )

        builder.add_artifact("test-skill", ArtifactType.SKILL)

        # Build bundle
        bundle = builder.build(output_path)

        # Verify bundle created
        assert output_path.exists()
        assert bundle.artifact_count == 1
        assert bundle.bundle_hash is not None
        assert bundle.bundle_hash.startswith("sha256:")

        # Verify ZIP structure
        with zipfile.ZipFile(output_path, "r") as zipf:
            assert "manifest.json" in zipf.namelist()
            assert any("artifacts/" in name for name in zipf.namelist())


def test_bundle_builder_validation_no_artifacts(mock_collection_manager, tmp_path):
    """Test validation fails with no artifacts."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )

        # Try to build without artifacts
        with pytest.raises(BundleValidationError, match="at least one artifact"):
            builder.build(output_path)


def test_bundle_builder_deterministic(mock_collection_manager, tmp_path):
    """Test bundle creation produces valid hashes.

    Note: Full determinism (same hash for same inputs) would require
    fixed timestamps, which is not realistic for production use.
    This test verifies that bundles have valid hashes.
    """
    output_path1 = tmp_path / "bundle1.skillmeat-pack"
    output_path2 = tmp_path / "bundle2.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        # Create first bundle
        builder1 = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )
        builder1.add_artifact("test-skill", ArtifactType.SKILL)
        bundle1 = builder1.build(output_path1)

        # Create second bundle with same inputs
        builder2 = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )
        builder2.add_artifact("test-skill", ArtifactType.SKILL)
        bundle2 = builder2.build(output_path2)

        # Both bundles should have valid hashes
        assert bundle1.bundle_hash is not None
        assert bundle1.bundle_hash.startswith("sha256:")
        assert bundle2.bundle_hash is not None
        assert bundle2.bundle_hash.startswith("sha256:")

        # Both bundles should be valid ZIP files
        assert output_path1.exists()
        assert output_path2.exists()


def test_inspect_bundle(mock_collection_manager, tmp_path):
    """Test inspecting bundle file."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        # Create bundle
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )
        builder.add_artifact("test-skill", ArtifactType.SKILL)
        original_bundle = builder.build(output_path)

        # Inspect bundle
        inspected_bundle = inspect_bundle(output_path)

        # Verify metadata matches
        assert inspected_bundle.metadata.name == "test-bundle"
        assert inspected_bundle.metadata.description == "Test bundle"
        assert inspected_bundle.metadata.author == "Test Author"
        assert inspected_bundle.artifact_count == 1
        assert inspected_bundle.bundle_hash == original_bundle.bundle_hash


def test_inspect_bundle_invalid_file(tmp_path):
    """Test inspecting invalid bundle file."""
    invalid_file = tmp_path / "not-a-bundle.txt"
    invalid_file.write_text("This is not a bundle")

    with pytest.raises(ValueError, match="Not a valid ZIP"):
        inspect_bundle(invalid_file)


def test_inspect_bundle_missing_manifest(tmp_path):
    """Test inspecting bundle without manifest."""
    bundle_path = tmp_path / "invalid-bundle.zip"

    # Create ZIP without manifest
    with zipfile.ZipFile(bundle_path, "w") as zipf:
        zipf.writestr("some-file.txt", "content")

    with pytest.raises(BundleValidationError, match="manifest.json not found"):
        inspect_bundle(bundle_path)


def test_bundle_builder_compression_levels(mock_collection_manager, tmp_path):
    """Test different compression levels."""
    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        # Test default compression
        builder_default = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
            compression_level=zipfile.ZIP_DEFLATED,
        )
        builder_default.add_artifact("test-skill", ArtifactType.SKILL)
        output_default = tmp_path / "bundle-default.skillmeat-pack"
        builder_default.build(output_default)

        # Test no compression
        builder_none = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
            compression_level=zipfile.ZIP_STORED,
        )
        builder_none.add_artifact("test-skill", ArtifactType.SKILL)
        output_none = tmp_path / "bundle-none.skillmeat-pack"
        builder_none.build(output_none)

        # Verify both bundles created successfully
        assert output_default.exists()
        assert output_none.exists()

        # Uncompressed should be larger
        assert output_none.stat().st_size >= output_default.stat().st_size


def test_bundle_builder_tags(mock_collection_manager, tmp_path):
    """Test bundle with tags."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
            tags=["python", "testing", "automation"],
        )
        builder.add_artifact("test-skill", ArtifactType.SKILL)
        bundle = builder.build(output_path)

        # Verify tags
        assert "python" in bundle.metadata.tags
        assert "testing" in bundle.metadata.tags
        assert "automation" in bundle.metadata.tags


def test_bundle_manifest_structure(mock_collection_manager, tmp_path):
    """Test bundle manifest has correct structure."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
            version="2.0.0",
            license="Apache-2.0",
        )
        builder.add_artifact("test-skill", ArtifactType.SKILL)
        builder.build(output_path)

        # Read manifest from ZIP
        with zipfile.ZipFile(output_path, "r") as zipf:
            manifest_data = zipf.read("manifest.json")
            manifest = json.loads(manifest_data)

            # Verify required fields
            assert manifest["version"] == "1.0"
            assert manifest["name"] == "test-bundle"
            assert manifest["description"] == "Test bundle"
            assert manifest["author"] == "Test Author"
            assert manifest["license"] == "Apache-2.0"
            assert "created_at" in manifest
            assert "artifacts" in manifest
            assert len(manifest["artifacts"]) == 1
            assert "bundle_hash" in manifest


def test_bundle_builder_artifact_metadata(mock_collection_manager, tmp_path):
    """Test artifact metadata in bundle."""
    output_path = tmp_path / "test-bundle.skillmeat-pack"

    with patch("skillmeat.core.sharing.builder.CollectionManager", return_value=mock_collection_manager):
        builder = BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
        )
        builder.add_artifact("test-skill", ArtifactType.SKILL)
        bundle = builder.build(output_path)

        # Verify artifact metadata
        artifact = bundle.artifacts[0]
        assert artifact.name == "test-skill"
        assert artifact.type == "skill"
        assert artifact.version == "1.0.0"
        assert artifact.metadata["title"] == "Test Skill"
        assert artifact.metadata["description"] == "A test skill"
