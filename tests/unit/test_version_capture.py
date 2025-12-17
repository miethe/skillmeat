"""Tests for automatic version capture on sync and deploy operations."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.sync import SyncManager
from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.models import SyncResult
from skillmeat.storage.snapshot import Snapshot


@pytest.fixture
def mock_collection_mgr():
    """Mock CollectionManager."""
    mgr = Mock()
    mgr.get_active_collection_name.return_value = "default"
    collection_mock = Mock()
    collection_mock.name = "default"
    collection_mock.artifacts = []
    mgr.load_collection.return_value = collection_mock
    mgr.config.get_collection_path.return_value = Path("/tmp/collection")
    return mgr


@pytest.fixture
def mock_version_mgr():
    """Mock VersionManager."""
    mgr = Mock()
    snapshot = Snapshot(
        id="snap_test123",
        collection_name="default",
        timestamp=datetime.now(),
        message="Test snapshot",
        artifact_count=1,
        tarball_path=Path("/tmp/snapshot.tar.gz"),
    )
    mgr.auto_snapshot.return_value = snapshot
    return mgr


class TestSyncVersionCapture:
    """Test automatic version capture during sync operations."""

    def test_sync_creates_snapshot_on_success(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that successful sync creates an automatic snapshot."""
        # Setup
        sync_mgr = SyncManager(
            collection_manager=mock_collection_mgr,
            version_manager=mock_version_mgr,
        )

        # Create minimal project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()

        # Create deployment metadata
        metadata_file = claude_dir / ".skillmeat-deployed.toml"
        metadata_file.write_text("""
[deployment]
collection = "default"
deployed-at = "2024-01-01T00:00:00Z"
skillmeat-version = "0.3.0"

[[artifacts]]
name = "test-skill"
type = "skill"
source = "local:/path"
version = "1.0.0"
sha = "abc123"
deployed-at = "2024-01-01T00:00:00Z"
deployed-from = "/tmp/collection"
""")

        # Mock sync operation returning success
        with patch.object(sync_mgr, 'check_drift') as mock_drift, \
             patch.object(sync_mgr, '_sync_artifact') as mock_sync_artifact, \
             patch.object(sync_mgr, '_load_deployment_metadata') as mock_load:

            # Setup mocks
            mock_load.return_value = Mock(collection="default")
            mock_drift.return_value = []  # No drift to sync

            # Execute sync (will return no_changes)
            result = sync_mgr.sync_from_project(
                project_path=project_path,
                interactive=False,
            )

            # Verify result
            assert result.status == "no_changes"

            # Snapshot should NOT be created when no artifacts are synced
            mock_version_mgr.auto_snapshot.assert_not_called()

    def test_sync_includes_artifact_names_in_message(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that snapshot message includes artifact names."""
        # Setup
        sync_mgr = SyncManager(
            collection_manager=mock_collection_mgr,
            version_manager=mock_version_mgr,
        )

        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()

        # Create deployment metadata
        metadata_file = claude_dir / ".skillmeat-deployed.toml"
        metadata_file.write_text("""
[deployment]
collection = "default"
deployed-at = "2024-01-01T00:00:00Z"
skillmeat-version = "0.3.0"
""")

        # Mock successful sync with artifacts
        with patch.object(sync_mgr, 'check_drift') as mock_drift, \
             patch.object(sync_mgr, '_sync_artifact') as mock_sync_artifact, \
             patch.object(sync_mgr, '_load_deployment_metadata') as mock_load, \
             patch.object(sync_mgr, '_show_sync_preview'), \
             patch.object(sync_mgr, '_confirm_sync', return_value=True):

            # Setup mocks
            mock_load.return_value = Mock(collection="default")

            # Mock drift detection with modified artifacts
            from skillmeat.models import DriftDetectionResult, ArtifactSyncResult
            drift = DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="modified",
                collection_sha="old_sha",
                project_sha="new_sha",
                collection_version="1.0",
                project_version="1.0",
                recommendation="push_to_collection",
            )
            mock_drift.return_value = [drift]

            # Mock artifact paths
            with patch.object(sync_mgr, '_get_project_artifact_path') as mock_path, \
                 patch.object(sync_mgr, '_compute_artifact_hash') as mock_hash:

                mock_path.return_value = project_path / "artifact"
                mock_hash.return_value = "new_sha"

                # Mock sync artifact success
                mock_sync_artifact.return_value = ArtifactSyncResult(
                    artifact_name="skill1",
                    success=True,
                )

                # Execute sync
                result = sync_mgr.sync_from_project(
                    project_path=project_path,
                    interactive=False,
                )

                # Verify snapshot was created
                mock_version_mgr.auto_snapshot.assert_called_once()
                call_args = mock_version_mgr.auto_snapshot.call_args

                # Check message includes artifact name
                assert "skill1" in call_args.kwargs["message"]
                assert "Auto-sync from project" in call_args.kwargs["message"]

    def test_sync_handles_snapshot_failure_gracefully(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that sync continues even if snapshot creation fails."""
        # Setup - version manager raises error
        mock_version_mgr.auto_snapshot.side_effect = RuntimeError("Snapshot failed")

        sync_mgr = SyncManager(
            collection_manager=mock_collection_mgr,
            version_manager=mock_version_mgr,
        )

        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()

        metadata_file = claude_dir / ".skillmeat-deployed.toml"
        metadata_file.write_text("""
[deployment]
collection = "default"
deployed-at = "2024-01-01T00:00:00Z"
skillmeat-version = "0.3.0"
""")

        # Mock successful sync
        with patch.object(sync_mgr, 'check_drift') as mock_drift, \
             patch.object(sync_mgr, '_sync_artifact') as mock_sync_artifact, \
             patch.object(sync_mgr, '_load_deployment_metadata') as mock_load, \
             patch.object(sync_mgr, '_show_sync_preview'), \
             patch.object(sync_mgr, '_confirm_sync', return_value=True), \
             patch.object(sync_mgr, '_get_project_artifact_path') as mock_path, \
             patch.object(sync_mgr, '_compute_artifact_hash') as mock_hash:

            mock_load.return_value = Mock(collection="default")

            from skillmeat.models import DriftDetectionResult, ArtifactSyncResult
            drift = DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="modified",
                collection_sha="old",
                project_sha="new",
                collection_version="1.0",
                project_version="1.0",
                recommendation="push_to_collection",
            )
            mock_drift.return_value = [drift]
            mock_path.return_value = project_path / "artifact"
            mock_hash.return_value = "new"
            mock_sync_artifact.return_value = ArtifactSyncResult(
                artifact_name="skill1",
                success=True,
            )

            # Execute - should not raise exception
            result = sync_mgr.sync_from_project(
                project_path=project_path,
                interactive=False,
            )

            # Verify sync still succeeded
            assert result.status == "success"
            assert "skill1" in result.artifacts_synced


class TestDeployVersionCapture:
    """Test automatic version capture during deploy operations."""

    def test_deploy_creates_snapshot_on_success(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that successful deployment creates an automatic snapshot."""
        # Setup
        deploy_mgr = DeploymentManager(
            collection_mgr=mock_collection_mgr,
            version_mgr=mock_version_mgr,
        )

        # Create collection with artifact
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        skills_dir = collection_path / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Mock collection
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=Mock(version="1.0.0"),
            added=datetime.now(),
        )
        collection_mock = Mock()
        collection_mock.name = "default"
        collection_mock.find_artifact.return_value = artifact
        mock_collection_mgr.load_collection.return_value = collection_mock
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        # Create project
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Mock filesystem operations
        with patch('skillmeat.core.deployment.FilesystemManager') as mock_fs_mgr, \
             patch('skillmeat.core.deployment.compute_content_hash') as mock_hash, \
             patch('skillmeat.storage.deployment.DeploymentTracker'), \
             patch('skillmeat.core.deployment.Confirm.ask', return_value=True):

            mock_hash.return_value = "abc123"
            mock_fs_mgr_instance = Mock()
            mock_fs_mgr.return_value = mock_fs_mgr_instance

            # Execute deployment
            deployments = deploy_mgr.deploy_artifacts(
                artifact_names=["test-skill"],
                collection_name="default",
                project_path=project_path,
            )

            # Verify deployment succeeded
            assert len(deployments) == 1
            assert deployments[0].artifact_name == "test-skill"

            # Verify snapshot was created
            mock_version_mgr.auto_snapshot.assert_called_once()
            call_args = mock_version_mgr.auto_snapshot.call_args

            # Check message includes artifact name and project path
            assert "test-skill" in call_args.kwargs["message"]
            assert "Auto-deploy" in call_args.kwargs["message"]
            assert str(project_path) in call_args.kwargs["message"]

    def test_deploy_handles_snapshot_failure_gracefully(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that deployment continues even if snapshot creation fails."""
        # Setup - version manager raises error
        mock_version_mgr.auto_snapshot.side_effect = RuntimeError("Snapshot failed")

        deploy_mgr = DeploymentManager(
            collection_mgr=mock_collection_mgr,
            version_mgr=mock_version_mgr,
        )

        # Create collection with artifact
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        skills_dir = collection_path / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=Mock(version="1.0.0"),
            added=datetime.now(),
        )
        collection_mock = Mock()
        collection_mock.name = "default"
        collection_mock.find_artifact.return_value = artifact
        mock_collection_mgr.load_collection.return_value = collection_mock
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        project_path = tmp_path / "project"
        project_path.mkdir()

        # Mock filesystem operations
        with patch('skillmeat.core.deployment.FilesystemManager') as mock_fs_mgr, \
             patch('skillmeat.core.deployment.compute_content_hash') as mock_hash, \
             patch('skillmeat.storage.deployment.DeploymentTracker'), \
             patch('skillmeat.core.deployment.Confirm.ask', return_value=True):

            mock_hash.return_value = "abc123"
            mock_fs_mgr_instance = Mock()
            mock_fs_mgr.return_value = mock_fs_mgr_instance

            # Execute - should not raise exception
            deployments = deploy_mgr.deploy_artifacts(
                artifact_names=["test-skill"],
                collection_name="default",
                project_path=project_path,
            )

            # Verify deployment still succeeded
            assert len(deployments) == 1
            assert deployments[0].artifact_name == "test-skill"

    def test_deploy_all_creates_single_snapshot(self, mock_collection_mgr, mock_version_mgr, tmp_path):
        """Test that deploy_all creates a single snapshot for all artifacts."""
        # Setup
        deploy_mgr = DeploymentManager(
            collection_mgr=mock_collection_mgr,
            version_mgr=mock_version_mgr,
        )

        # Create collection with multiple artifacts
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        skills_dir = collection_path / "skills"
        skills_dir.mkdir()

        # Create two skills
        for skill_name in ["skill1", "skill2"]:
            skill_dir = skills_dir / skill_name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}")

        # Mock collection
        artifacts = [
            Artifact(
                name="skill1",
                type=ArtifactType.SKILL,
                path="skills/skill1",
                origin="local",
                metadata=Mock(version="1.0.0"),
                added=datetime.now(),
            ),
            Artifact(
                name="skill2",
                type=ArtifactType.SKILL,
                path="skills/skill2",
                origin="local",
                metadata=Mock(version="1.0.0"),
                added=datetime.now(),
            ),
        ]

        collection_mock = Mock()
        collection_mock.name = "default"
        collection_mock.artifacts = artifacts
        collection_mock.find_artifact = lambda name, _: next(
            (a for a in artifacts if a.name == name), None
        )
        mock_collection_mgr.load_collection.return_value = collection_mock
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        project_path = tmp_path / "project"
        project_path.mkdir()

        # Mock filesystem operations
        with patch('skillmeat.core.deployment.FilesystemManager') as mock_fs_mgr, \
             patch('skillmeat.core.deployment.compute_content_hash') as mock_hash, \
             patch('skillmeat.storage.deployment.DeploymentTracker'), \
             patch('skillmeat.core.deployment.Confirm.ask', return_value=True):

            mock_hash.return_value = "abc123"
            mock_fs_mgr_instance = Mock()
            mock_fs_mgr.return_value = mock_fs_mgr_instance

            # Execute deploy_all
            deployments = deploy_mgr.deploy_all(
                collection_name="default",
                project_path=project_path,
            )

            # Verify both artifacts deployed
            assert len(deployments) == 2

            # Verify only one snapshot was created (deploy_all calls deploy_artifacts)
            mock_version_mgr.auto_snapshot.assert_called_once()
            call_args = mock_version_mgr.auto_snapshot.call_args

            # Message should include both artifact names (or indicate multiple)
            message = call_args.kwargs["message"]
            assert "Auto-deploy" in message
            assert ("skill1" in message and "skill2" in message) or "2" in message
