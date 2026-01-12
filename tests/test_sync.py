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
        """Test loading nonexistent metadata returns empty list."""
        sync_mgr = SyncManager()
        deployments = sync_mgr._load_deployment_metadata(tmp_path)
        assert deployments == []

    def test_load_valid_metadata(self, tmp_path):
        """Test loading valid deployment metadata."""
        # Create metadata file in new format
        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"

        toml_content = """
[[deployed]]
artifact_name = "test-skill"
artifact_type = "skill"
from_collection = "my-collection"
deployed_at = "2025-11-15T10:30:00Z"
artifact_path = "skills/test-skill"
content_hash = "abc123def456"
local_modifications = false
collection_sha = "abc123def456"
"""
        metadata_file.write_text(toml_content)

        sync_mgr = SyncManager()
        deployments = sync_mgr._load_deployment_metadata(tmp_path)

        assert len(deployments) == 1
        assert deployments[0].artifact_name == "test-skill"
        assert deployments[0].artifact_type == "skill"
        assert deployments[0].from_collection == "my-collection"
        assert deployments[0].content_hash == "abc123def456"

    def test_load_multiple_artifacts(self, tmp_path):
        """Test loading metadata with multiple artifacts."""
        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"

        toml_content = """
[[deployed]]
artifact_name = "skill1"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-11-15T10:30:00Z"
artifact_path = "skills/skill1"
content_hash = "abc123"
local_modifications = false

[[deployed]]
artifact_name = "skill2"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-11-15T10:35:00Z"
artifact_path = "skills/skill2"
content_hash = "def456"
local_modifications = false
"""
        metadata_file.write_text(toml_content)

        sync_mgr = SyncManager()
        deployments = sync_mgr._load_deployment_metadata(tmp_path)

        assert len(deployments) == 2
        assert deployments[0].artifact_name == "skill1"
        assert deployments[1].artifact_name == "skill2"

    def test_load_corrupted_metadata(self, tmp_path):
        """Test loading corrupted metadata raises exception."""
        import tomllib

        metadata_dir = tmp_path / ".claude"
        metadata_dir.mkdir()
        metadata_file = metadata_dir / ".skillmeat-deployed.toml"
        metadata_file.write_text("invalid toml content {{{")

        sync_mgr = SyncManager()
        # DeploymentTracker.read_deployments raises exception on corrupted TOML
        with pytest.raises(tomllib.TOMLDecodeError):
            sync_mgr._load_deployment_metadata(tmp_path)


class TestSaveDeploymentMetadata:
    """Tests for _save_deployment_metadata method."""

    def test_save_creates_directory(self, tmp_path):
        """Test save creates .claude directory if needed."""
        from skillmeat.core.deployment import Deployment

        deployments = []

        sync_mgr = SyncManager()
        sync_mgr._save_deployment_metadata(tmp_path, deployments)

        metadata_file = tmp_path / ".claude" / ".skillmeat-deployed.toml"
        assert metadata_file.exists()
        assert metadata_file.parent.exists()

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip preserves data."""
        from skillmeat.core.deployment import Deployment

        deployment = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection="my-collection",
            deployed_at=datetime.fromisoformat("2025-11-15T10:30:00"),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123",
            local_modifications=False,
        )

        sync_mgr = SyncManager()
        sync_mgr._save_deployment_metadata(tmp_path, [deployment])

        # Load back
        loaded = sync_mgr._load_deployment_metadata(tmp_path)

        assert len(loaded) == 1
        assert loaded[0].artifact_name == deployment.artifact_name
        assert loaded[0].from_collection == deployment.from_collection
        assert loaded[0].content_hash == deployment.content_hash


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

        # Load and verify - returns List[Deployment] now
        deployments = sync_mgr._load_deployment_metadata(project_path)
        assert deployments is not None
        assert len(deployments) == 1
        assert deployments[0].from_collection == "default"
        assert deployments[0].artifact_name == "test-skill"

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

        # Should only have one deployment record
        deployments = sync_mgr._load_deployment_metadata(project_path)
        assert len(deployments) == 1

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
        deployments = sync_mgr._load_deployment_metadata(project_path)
        assert len(deployments) == 2
        names = {d.artifact_name for d in deployments}
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
        class MockConfig:
            def __init__(self, collection_path):
                self._collection_path = collection_path

            def get_collection_path(self, name):
                return self._collection_path

        class MockCollectionManager:
            def __init__(self, collection_path):
                self.collection_path = collection_path
                self.config = MockConfig(collection_path)

            def load_collection(self, name):
                class Collection:
                    pass
                return Collection()

        # Create collection artifact
        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        # Create deployment metadata
        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager(collection_path))
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Copy artifact to project to simulate deployed state
        project_artifact_path = project_path / ".claude" / "skills" / "test-skill"
        project_artifact_path.mkdir(parents=True, exist_ok=True)
        (project_artifact_path / "SKILL.md").write_text("# Test\n")

        # Check drift - should be none
        drift_results = sync_mgr.check_drift(project_path)
        assert drift_results == []

    def test_detects_modified_artifact(self, tmp_path):
        """Test detects when artifact modified in collection."""

        class MockCollectionManager:
            def __init__(self, collection_path):
                self.collection_path = collection_path

            def load_collection(self, name):
                class Collection:
                    pass
                return Collection()

            @property
            def config(self):
                class Config:
                    def __init__(self, collection_path):
                        self.collection_path = collection_path
                    def get_collection_path(self, name):
                        return self.collection_path
                return Config(self.collection_path)

        collection_path = tmp_path / "collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager(collection_path))

        # Deploy
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Copy artifact to project to simulate deployed state
        project_artifact_path = project_path / ".claude" / "skills" / "test-skill"
        project_artifact_path.mkdir(parents=True, exist_ok=True)
        (project_artifact_path / "SKILL.md").write_text("# Test\n")

        # Modify artifact in collection
        (artifact_path / "SKILL.md").write_text("# Modified\n")

        # Check drift
        drift_results = sync_mgr.check_drift(project_path)

        assert len(drift_results) == 1
        assert drift_results[0].artifact_name == "test-skill"
        assert drift_results[0].drift_type == "outdated"  # Collection changed, project unchanged
        assert drift_results[0].collection_sha is not None
        assert drift_results[0].project_sha is not None
        assert drift_results[0].collection_sha != drift_results[0].project_sha

    def test_detects_added_artifact(self, tmp_path):
        """Test detects when artifact added to collection."""

        class MockCollectionManager:
            def __init__(self, collection_path):
                self.collection_path = collection_path

            def load_collection(self, name):
                class Collection:
                    pass
                return Collection()

            @property
            def config(self):
                class Config:
                    def __init__(self, collection_path):
                        self.collection_path = collection_path
                    def get_collection_path(self, name):
                        return self.collection_path
                return Config(self.collection_path)

        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"

        # Create initial artifact and deploy
        artifact1_path = collection_path / "skills" / "skill1"
        artifact1_path.mkdir(parents=True)
        (artifact1_path / "SKILL.md").write_text("# Skill 1\n")

        sync_mgr = SyncManager(collection_manager=MockCollectionManager(collection_path))
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="skill1",
            artifact_type="skill",
            collection_path=collection_path,
        )

        # Copy artifact to project to simulate deployed state
        project_artifact1_path = project_path / ".claude" / "skills" / "skill1"
        project_artifact1_path.mkdir(parents=True, exist_ok=True)
        (project_artifact1_path / "SKILL.md").write_text("# Skill 1\n")

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
            def __init__(self, collection_path):
                self.collection_path = collection_path

            def load_collection(self, name):
                class Collection:
                    pass
                return Collection()

            @property
            def config(self):
                class Config:
                    def __init__(self, collection_path):
                        self.collection_path = collection_path
                    def get_collection_path(self, name):
                        return self.collection_path
                return Config(self.collection_path)

        collection_path = tmp_path / "my-collection"
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Test\n")

        project_path = tmp_path / "project"
        sync_mgr = SyncManager(collection_manager=MockCollectionManager(collection_path))

        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="test-skill",
            artifact_type="skill",
            collection_path=collection_path,
            collection_name="my-collection",
        )

        # Copy artifact to project to simulate deployed state
        project_artifact_path = project_path / ".claude" / "skills" / "test-skill"
        project_artifact_path.mkdir(parents=True, exist_ok=True)
        (project_artifact_path / "SKILL.md").write_text("# Test\n")

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
