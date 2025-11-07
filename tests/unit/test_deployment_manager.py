"""Unit tests for DeploymentManager."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.deployment import Deployment, DeploymentManager


@pytest.fixture
def mock_collection_mgr():
    """Create a mock CollectionManager."""
    mgr = Mock()
    mgr.config = Mock()
    return mgr


@pytest.fixture
def sample_collection():
    """Create a sample collection with artifacts."""
    return Collection(
        name="default",
        version="1.0.0",
        artifacts=[
            Artifact(
                name="test-skill",
                type=ArtifactType.SKILL,
                path="skills/test-skill",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
            Artifact(
                name="review-cmd",
                type=ArtifactType.COMMAND,
                path="commands/review.md",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
            Artifact(
                name="assistant",
                type=ArtifactType.AGENT,
                path="agents/assistant.md",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
        ],
        created=datetime.now(),
        updated=datetime.now(),
    )


class TestDeploymentManager:
    """Test DeploymentManager functionality."""

    def test_init_default_collection_mgr(self):
        """Test initialization with default CollectionManager."""
        with patch("skillmeat.core.collection.CollectionManager"):
            manager = DeploymentManager()
            assert manager.collection_mgr is not None
            assert manager.filesystem_mgr is not None

    def test_init_custom_collection_mgr(self, mock_collection_mgr):
        """Test initialization with custom CollectionManager."""
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        assert manager.collection_mgr == mock_collection_mgr

    def test_deploy_artifacts_single_skill(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch
    ):
        """Test deploying a single skill artifact."""
        # Setup paths
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        # Create source skill
        skill_dir = collection_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        # Mock Confirm.ask to always return True
        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Create manager and deploy
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Verify deployment
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "test-skill"
        assert deployments[0].artifact_type == "skill"

        # Verify file was copied
        deployed_path = project_path / ".claude" / "skills" / "test-skill"
        assert deployed_path.exists()
        assert (deployed_path / "SKILL.md").exists()

    def test_deploy_artifacts_single_command(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch
    ):
        """Test deploying a single command artifact."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        # Create source command
        cmd_dir = collection_path / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "review.md").write_text("# Review Command")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Create manager and deploy
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.deploy_artifacts(
            ["review-cmd"],
            project_path=project_path,
            artifact_type=ArtifactType.COMMAND,
        )

        # Verify deployment
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "review-cmd"
        assert deployments[0].artifact_type == "command"

        # Verify file was copied
        deployed_path = project_path / ".claude" / "commands" / "review-cmd.md"
        assert deployed_path.exists()

    def test_deploy_artifacts_not_found(
        self, tmp_path, mock_collection_mgr, sample_collection, capsys
    ):
        """Test deploying non-existent artifact."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.deploy_artifacts(
            ["nonexistent"], project_path=project_path
        )

        # Should return empty list
        assert len(deployments) == 0

        # Should print warning
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_deploy_artifacts_overwrite_decline(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch, capsys
    ):
        """Test declining to overwrite existing artifact."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        # Create source skill
        skill_dir = collection_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Create existing deployment
        existing_dir = project_path / ".claude" / "skills" / "test-skill"
        existing_dir.mkdir(parents=True)
        (existing_dir / "SKILL.md").write_text("# Existing")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        # Mock Confirm.ask to return False (decline overwrite)
        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: False)

        # Create manager and deploy
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Should return empty list (deployment declined)
        assert len(deployments) == 0

        # Should print skipped message
        captured = capsys.readouterr()
        assert "Skipped" in captured.out

    def test_deploy_all(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch
    ):
        """Test deploying all artifacts from collection."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        # Create all source artifacts
        skill_dir = collection_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        cmd_dir = collection_path / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "review.md").write_text("# Review")

        agent_dir = collection_path / "agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "assistant.md").write_text("# Assistant")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Create manager and deploy all
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.deploy_all(project_path=project_path)

        # Should deploy all 3 artifacts
        assert len(deployments) == 3

        # Verify all deployed
        assert (project_path / ".claude" / "skills" / "test-skill").exists()
        assert (project_path / ".claude" / "commands" / "review-cmd.md").exists()
        assert (project_path / ".claude" / "agents" / "assistant.md").exists()

    def test_undeploy(self, tmp_path, mock_collection_mgr):
        """Test undeploying an artifact."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create deployed skill
        skill_dir = project_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Record deployment
        from skillmeat.storage.deployment import DeploymentTracker

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        DeploymentTracker.record_deployment(
            project_path, artifact, "default", "testsha"
        )

        # Undeploy
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        manager.undeploy("test-skill", ArtifactType.SKILL, project_path=project_path)

        # Verify file removed
        assert not skill_dir.exists()

        # Verify deployment record removed
        deployment = DeploymentTracker.get_deployment(
            project_path, "test-skill", "skill"
        )
        assert deployment is None

    def test_undeploy_not_deployed(self, tmp_path, mock_collection_mgr):
        """Test undeploying an artifact that isn't deployed."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = DeploymentManager(collection_mgr=mock_collection_mgr)

        with pytest.raises(ValueError, match="not deployed"):
            manager.undeploy(
                "nonexistent", ArtifactType.SKILL, project_path=project_path
            )

    def test_list_deployments_empty(self, tmp_path, mock_collection_mgr):
        """Test listing deployments when none exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.list_deployments(project_path=project_path)

        assert deployments == []

    def test_list_deployments(self, tmp_path, mock_collection_mgr):
        """Test listing deployments."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Record some deployments
        from skillmeat.storage.deployment import DeploymentTracker

        artifact1 = Artifact(
            name="skill1",
            type=ArtifactType.SKILL,
            path="skills/skill1",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        artifact2 = Artifact(
            name="cmd1",
            type=ArtifactType.COMMAND,
            path="commands/cmd1.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(project_path, artifact1, "default", "sha1")
        DeploymentTracker.record_deployment(project_path, artifact2, "default", "sha2")

        # List deployments
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        deployments = manager.list_deployments(project_path=project_path)

        assert len(deployments) == 2
        assert deployments[0].artifact_name == "skill1"
        assert deployments[1].artifact_name == "cmd1"

    def test_check_deployment_status_synced(self, tmp_path, mock_collection_mgr):
        """Test checking deployment status when synced."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create deployed skill
        skill_dir = project_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Record deployment with correct hash
        from skillmeat.storage.deployment import DeploymentTracker
        from skillmeat.utils.filesystem import compute_content_hash

        skill_hash = compute_content_hash(skill_dir)
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        DeploymentTracker.record_deployment(
            project_path, artifact, "default", skill_hash
        )

        # Check status
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        status = manager.check_deployment_status(project_path=project_path)

        assert "test-skill::skill" in status
        assert status["test-skill::skill"] == "synced"

    def test_check_deployment_status_modified(self, tmp_path, mock_collection_mgr):
        """Test checking deployment status when modified."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create deployed skill
        skill_dir = project_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Original")

        # Record deployment with original hash
        from skillmeat.storage.deployment import DeploymentTracker

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        DeploymentTracker.record_deployment(
            project_path, artifact, "default", "original_hash"
        )

        # Modify the file
        skill_file.write_text("# Modified")

        # Check status
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        status = manager.check_deployment_status(project_path=project_path)

        assert "test-skill::skill" in status
        assert status["test-skill::skill"] == "modified"

    def test_deploy_artifacts_uses_cwd_by_default(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch
    ):
        """Test that deploy_artifacts uses CWD when project_path is None."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir(parents=True)

        # Create source skill
        skill_dir = collection_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Change to temp directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create manager and deploy (no project_path specified)
            manager = DeploymentManager(collection_mgr=mock_collection_mgr)
            deployments = manager.deploy_artifacts(["test-skill"])

            # Verify deployment in CWD
            assert len(deployments) == 1
            deployed_path = tmp_path / ".claude" / "skills" / "test-skill"
            assert deployed_path.exists()
        finally:
            os.chdir(original_cwd)

    def test_deploy_artifacts_error_handling(
        self, tmp_path, mock_collection_mgr, sample_collection, monkeypatch, capsys
    ):
        """Test error handling during deployment."""
        collection_path = tmp_path / "collection"
        project_path = tmp_path / "project"
        collection_path.mkdir(parents=True)
        project_path.mkdir(parents=True)

        # Create source skill
        skill_dir = collection_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Setup mocks
        mock_collection_mgr.load_collection.return_value = sample_collection
        mock_collection_mgr.config.get_collection_path.return_value = collection_path

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Mock copy_artifact to raise an exception
        manager = DeploymentManager(collection_mgr=mock_collection_mgr)
        manager.filesystem_mgr.copy_artifact = Mock(
            side_effect=Exception("Copy failed")
        )

        # Deploy should handle error gracefully
        deployments = manager.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Should return empty list
        assert len(deployments) == 0

        # Should print error
        captured = capsys.readouterr()
        assert "Error deploying" in captured.out
