"""Tests for SyncManager.

Tests sync metadata tracking, drift detection, and deployment tracking.
"""

import pytest
from datetime import datetime
from pathlib import Path
from skillmeat.core.sync import SyncManager
from skillmeat.models import (
    DeploymentRecord,
    DeploymentMetadata,
    DriftDetectionResult,
)


class TestComputeArtifactHash:
    """Tests for _compute_artifact_hash method."""

    def test_hash_single_file(self, tmp_path):
        """Test hashing artifact with single file."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")

        sync_mgr = SyncManager()
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)

        assert hash1
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_hash_multiple_files(self, tmp_path):
        """Test hashing artifact with multiple files."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")
        (artifact_path / "code.py").write_text("print('hello')\n")
        (artifact_path / "data.txt").write_text("data\n")

        sync_mgr = SyncManager()
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)

        assert hash1
        assert len(hash1) == 64

    def test_hash_consistency(self, tmp_path):
        """Test hash is consistent for same content."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")

        sync_mgr = SyncManager()
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)
        hash2 = sync_mgr._compute_artifact_hash(artifact_path)

        assert hash1 == hash2

    def test_hash_changes_with_content(self, tmp_path):
        """Test hash changes when content changes."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")

        sync_mgr = SyncManager()
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)

        # Modify content
        (artifact_path / "SKILL.md").write_text("# Modified Skill\n")
        hash2 = sync_mgr._compute_artifact_hash(artifact_path)

        assert hash1 != hash2

    def test_hash_changes_with_new_file(self, tmp_path):
        """Test hash changes when new file added."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")

        sync_mgr = SyncManager()
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)

        # Add new file
        (artifact_path / "new.txt").write_text("new content\n")
        hash2 = sync_mgr._compute_artifact_hash(artifact_path)

        assert hash1 != hash2

    def test_hash_nonexistent_path(self, tmp_path):
        """Test hash raises error for nonexistent path."""
        sync_mgr = SyncManager()
        with pytest.raises(ValueError, match="does not exist"):
            sync_mgr._compute_artifact_hash(tmp_path / "nonexistent")

    def test_hash_ignores_unreadable_files(self, tmp_path):
        """Test hash continues when file is unreadable."""
        artifact_path = tmp_path / "test-artifact"
        artifact_path.mkdir()
        (artifact_path / "SKILL.md").write_text("# Test Skill\n")

        sync_mgr = SyncManager()
        # Should succeed even with potential permission issues
        hash1 = sync_mgr._compute_artifact_hash(artifact_path)
        assert hash1


class TestLoadDeploymentMetadata:
    """Tests for _load_deployment_metadata method."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent metadata returns None."""
        sync_mgr = SyncManager()
        metadata = sync_mgr._load_deployment_metadata(tmp_path)
        assert metadata is None

    def test_load_valid_metadata(self, tmp_path):
        """Test loading valid deployment metadata."""
        # Create metadata file
        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"

        toml_content = """
[deployment]
collection = "my-collection"
deployed-at = "2025-11-15T10:30:00Z"
skillmeat-version = "0.2.0-alpha"

[[artifacts]]
name = "test-skill"
type = "skill"
source = "github:user/repo/test-skill"
version = "1.0.0"
sha = "abc123def456"
deployed-at = "2025-11-15T10:30:00Z"
deployed-from = "/path/to/collection"
"""
        metadata_file.write_text(toml_content)

        sync_mgr = SyncManager()
        metadata = sync_mgr._load_deployment_metadata(tmp_path)

        assert metadata is not None
        assert metadata.collection == "my-collection"
        assert metadata.deployed_at == "2025-11-15T10:30:00Z"
        assert metadata.skillmeat_version == "0.2.0-alpha"
        assert len(metadata.artifacts) == 1
        assert metadata.artifacts[0].name == "test-skill"
        assert metadata.artifacts[0].sha == "abc123def456"

    def test_load_multiple_artifacts(self, tmp_path):
        """Test loading metadata with multiple artifacts."""
        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"

        toml_content = """
[deployment]
collection = "default"
deployed-at = "2025-11-15T10:30:00Z"
skillmeat-version = "0.2.0-alpha"

[[artifacts]]
name = "skill1"
type = "skill"
source = "local:/path/skill1"
version = "1.0.0"
sha = "abc123"
deployed-at = "2025-11-15T10:30:00Z"
deployed-from = "/path/to/collection"

[[artifacts]]
name = "skill2"
type = "skill"
source = "local:/path/skill2"
version = "2.0.0"
sha = "def456"
deployed-at = "2025-11-15T10:35:00Z"
deployed-from = "/path/to/collection"
"""
        metadata_file.write_text(toml_content)

        sync_mgr = SyncManager()
        metadata = sync_mgr._load_deployment_metadata(tmp_path)

        assert metadata is not None
        assert len(metadata.artifacts) == 2
        assert metadata.artifacts[0].name == "skill1"
        assert metadata.artifacts[1].name == "skill2"

    def test_load_corrupted_metadata(self, tmp_path):
        """Test loading corrupted metadata returns None."""
        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"
        metadata_file.write_text("invalid toml content {{{")

        sync_mgr = SyncManager()
        metadata = sync_mgr._load_deployment_metadata(tmp_path)
        assert metadata is None


class TestSaveDeploymentMetadata:
    """Tests for _save_deployment_metadata method."""

    def test_save_creates_directory(self, tmp_path):
        """Test save creates .claude directory if needed."""
        metadata_file = tmp_path / ".claude" / ".skillmeat-deployed.toml"

        metadata = DeploymentMetadata(
            collection="test",
            deployed_at="2025-11-15T10:30:00Z",
            skillmeat_version="0.2.0-alpha",
            artifacts=[],
        )

        sync_mgr = SyncManager()
        sync_mgr._save_deployment_metadata(metadata_file, metadata)

        assert metadata_file.exists()
        assert metadata_file.parent.exists()

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip preserves data."""
        metadata_file = tmp_path / ".claude" / ".skillmeat-deployed.toml"

        metadata = DeploymentMetadata(
            collection="my-collection",
            deployed_at="2025-11-15T10:30:00Z",
            skillmeat_version="0.2.0-alpha",
            artifacts=[
                DeploymentRecord(
                    name="test-skill",
                    artifact_type="skill",
                    source="github:user/repo",
                    version="1.0.0",
                    sha="abc123",
                    deployed_at="2025-11-15T10:30:00Z",
                    deployed_from="/path/to/collection",
                )
            ],
        )

        sync_mgr = SyncManager()
        sync_mgr._save_deployment_metadata(metadata_file, metadata)

        # Load back
        loaded = sync_mgr._load_deployment_metadata(tmp_path)

        assert loaded is not None
        assert loaded.collection == metadata.collection
        assert loaded.deployed_at == metadata.deployed_at
        assert len(loaded.artifacts) == len(metadata.artifacts)
        assert loaded.artifacts[0].name == metadata.artifacts[0].name
        assert loaded.artifacts[0].sha == metadata.artifacts[0].sha


class TestUpdateDeploymentMetadata:
    """Tests for update_deployment_metadata method."""

    def test_update_creates_new_metadata(self, tmp_path):
        """Test update creates new metadata if none exists."""
        # Create artifact
        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"

        sync_mgr = SyncManager()
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
            collection_name="default",
        )

        # Check metadata was created
        metadata_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert metadata_file.exists()

        # Load and verify
        metadata = sync_mgr._load_deployment_metadata(project_path)
        assert metadata is not None
        assert metadata.collection == "default"
        assert len(metadata.artifacts) == 1
        assert metadata.artifacts[0].name == "test-skill"

    def test_update_replaces_existing_artifact(self, tmp_path):
        """Test update replaces existing artifact record."""
        # Create artifact
        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"

        sync_mgr = SyncManager()

        # First deployment
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Modify artifact
        (artifact_path / "SKILL.md").write_text("# Modified\n")

        # Second deployment
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Should only have one artifact record
        metadata = sync_mgr._load_deployment_metadata(project_path)
        assert len(metadata.artifacts) == 1

    def test_update_adds_multiple_artifacts(self, tmp_path):
        """Test update can track multiple artifacts."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"

        # Create two artifacts
        skill1_path = collection_path / "skills" / "skill1"
        skill1_path.mkdir(parents=True)
        (skill1_path / "SKILL.md").write_text("# Skill 1\n")

        skill2_path = collection_path / "skills" / "skill2"
        skill2_path.mkdir(parents=True)
        (skill2_path / "SKILL.md").write_text("# Skill 2\n")

        sync_mgr = SyncManager()

        # Deploy both
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="skill1",
            artifact_type="skill",
            collection_path=collection_path,
        )

        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="skill2",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Check both recorded
        metadata = sync_mgr._load_deployment_metadata(project_path)
        assert len(metadata.artifacts) == 2
        names = {a.name for a in metadata.artifacts}
        assert names == {"skill1", "skill2"}


class TestCheckDrift:
    """Tests for check_drift method."""

    def test_no_drift_when_no_metadata(self, tmp_path):
        """Test no drift when no deployment metadata exists."""
        sync_mgr = SyncManager()
        drift_results = sync_mgr.check_drift(tmp_path)
        assert drift_results == []

    def test_no_drift_when_unchanged(self, tmp_path):
        """Test no drift when artifacts unchanged."""

        # Setup collection mock
        class MockCollectionManager:
            def load_collection(self, name):
                class Collection:
                    path = tmp_path / "collection"

                return Collection()

        # Create collection artifact
        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        # Create deployment metadata
        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager())
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Check drift - should be none
        drift_results = sync_mgr.check_drift(project_path)
        assert drift_results == []

    def test_detects_modified_artifact(self, tmp_path):
        """Test detects when artifact modified in collection."""

        class MockCollectionManager:
            def load_collection(self, name):
                class Collection:
                    path = tmp_path / "collection"

                return Collection()

        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager())

        # Deploy
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Modify artifact
        (artifact_path / "SKILL.md").write_text("# Modified\n")

        # Check drift
        drift_results = sync_mgr.check_drift(project_path)

        assert len(drift_results) == 1
        assert drift_results[0].artifact_name == "test-skill"
        assert drift_results[0].drift_type == "modified"
        assert drift_results[0].collection_sha is not None
        assert drift_results[0].project_sha is not None
        assert drift_results[0].collection_sha != drift_results[0].project_sha

    def test_detects_added_artifact(self, tmp_path):
        """Test detects when artifact added to collection."""

        class MockCollectionManager:
            def load_collection(self, name):
                class Collection:
                    path = tmp_path / "collection"

                return Collection()

        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"

        # Create initial artifact and deploy
        artifact1_path = collection_path / "skills" / "skill1"
        artifact1_path.mkdir(parents=True)
        (artifact1_path / "SKILL.md").write_text("# Skill 1\n")

        sync_mgr = SyncManager(collection_manager=MockCollectionManager())
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="skill1",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Add new artifact to collection
        artifact2_path = collection_path / "skills" / "skill2"
        artifact2_path.mkdir()
        (artifact2_path / "SKILL.md").write_text("# Skill 2\n")

        # Check drift
        drift_results = sync_mgr.check_drift(project_path)

        # Should detect skill2 as added
        added = [d for d in drift_results if d.drift_type == "added"]
        assert len(added) == 1
        assert added[0].artifact_name == "skill2"
        assert added[0].collection_sha is not None
        assert added[0].project_sha is None

    def test_detects_removed_artifact(self, tmp_path):
        """Test detects when artifact removed from collection."""

        class MockCollectionManager:
            def load_collection(self, name):
                class Collection:
                    path = tmp_path / "collection"

                return Collection()

        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"

        # Create and deploy artifact
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        sync_mgr = SyncManager(collection_manager=MockCollectionManager())
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Remove artifact from collection (simulate removal)
        import shutil

        shutil.rmtree(artifact_path)

        # Check drift
        drift_results = sync_mgr.check_drift(project_path)

        assert len(drift_results) == 1
        assert drift_results[0].artifact_name == "test-skill"
        assert drift_results[0].drift_type == "removed"
        assert drift_results[0].collection_sha is None
        assert drift_results[0].project_sha is not None

    def test_drift_with_custom_collection(self, tmp_path):
        """Test drift detection with custom collection name."""

        class MockCollectionManager:
            def load_collection(self, name):
                class Collection:
                    path = tmp_path / "my-collection"

                return Collection()

        collection_path = tmp_path / "my-collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager())

        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
            collection_name="my-collection",
        )

        # Check drift with custom collection
        drift_results = sync_mgr.check_drift(
            project_path, collection_name="my-collection"
        )
        assert drift_results == []


class TestDataModels:
    """Tests for data models."""

    def test_deployment_record_creation(self):
        """Test creating DeploymentRecord."""
        record = DeploymentRecord(
            name="test-skill",
            artifact_type="skill",
            source="github:user/repo",
            version="1.0.0",
            sha="abc123",
            deployed_at="2025-11-15T10:30:00Z",
            deployed_from="/path/to/collection",
        )

        assert record.name == "test-skill"
        assert record.artifact_type == "skill"
        assert record.sha == "abc123"

    def test_deployment_metadata_creation(self):
        """Test creating DeploymentMetadata."""
        metadata = DeploymentMetadata(
            collection="default",
            deployed_at="2025-11-15T10:30:00Z",
            skillmeat_version="0.2.0-alpha",
            artifacts=[],
        )

        assert metadata.collection == "default"
        assert len(metadata.artifacts) == 0

    def test_drift_detection_result_creation(self):
        """Test creating DriftDetectionResult."""
        result = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",
            recommendation="push_from_collection",
        )

        assert result.artifact_name == "test-skill"
        assert result.drift_type == "modified"

    def test_drift_detection_result_validation(self):
        """Test DriftDetectionResult validates drift_type."""
        with pytest.raises(ValueError, match="Invalid drift_type"):
            DriftDetectionResult(
                artifact_name="test",
                artifact_type="skill",
                drift_type="invalid",
            )
