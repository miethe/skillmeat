"""Integration tests for deployment workflow."""

from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.deployment import DeploymentManager
from skillmeat.storage.deployment import DeploymentTracker


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path / ".skillmeat"


@pytest.fixture
def temp_config(temp_config_dir):
    """Create temporary configuration."""
    config = ConfigManager(config_dir=temp_config_dir)
    config.set("settings.active-collection", "default")
    return config


@pytest.fixture
def temp_collection(temp_config):
    """Create a temporary collection with artifacts."""
    collection_mgr = CollectionManager(config=temp_config)
    collection = collection_mgr.init("default")

    # Create some test artifacts manually
    collection_path = temp_config.get_collection_path("default")

    # Create a skill
    skill_dir = collection_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill\n\nThis is a test skill.")

    # Create a command
    cmd_dir = collection_path / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    (cmd_dir / "review.md").write_text("# Review Command\n\nReview code changes.")

    # Create an agent
    agent_dir = collection_path / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "assistant.md").write_text("# Assistant Agent\n\nHelps with tasks.")

    return collection_mgr, collection


class TestDeploymentWorkflow:
    """Test full deployment workflow."""

    def test_full_workflow_skill(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test complete workflow: create collection -> add artifact -> deploy -> check status -> undeploy."""
        collection_mgr, collection = temp_collection
        artifact_mgr = ArtifactManager(collection_mgr=collection_mgr)
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add artifact to collection
        from skillmeat.core.artifact import Artifact

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(title="Test Skill"),
            added=datetime.now(),
        )
        collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        # Mock Confirm.ask to always return True
        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy artifact
        deployments = deployment_mgr.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Verify deployment
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "test-skill"

        # Verify files exist
        deployed_skill = project_path / ".claude" / "skills" / "test-skill"
        assert deployed_skill.exists()
        assert (deployed_skill / "SKILL.md").exists()

        # Check deployment status
        status = deployment_mgr.check_deployment_status(project_path=project_path)
        assert "test-skill::skill" in status
        assert status["test-skill::skill"] == "synced"

        # List deployments
        listed = deployment_mgr.list_deployments(project_path=project_path)
        assert len(listed) == 1
        assert listed[0].artifact_name == "test-skill"

        # Undeploy
        deployment_mgr.undeploy(
            "test-skill", ArtifactType.SKILL, project_path=project_path
        )

        # Verify undeployed
        assert not deployed_skill.exists()
        listed = deployment_mgr.list_deployments(project_path=project_path)
        assert len(listed) == 0

    def test_modification_detection(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test detecting local modifications to deployed artifacts."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add artifact to collection
        from skillmeat.core.artifact import Artifact

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy artifact
        deployment_mgr.deploy_artifacts(["test-skill"], project_path=project_path)

        # Check initial status (should be synced)
        status = deployment_mgr.check_deployment_status(project_path=project_path)
        assert status["test-skill::skill"] == "synced"

        # Modify deployed file
        deployed_skill = project_path / ".claude" / "skills" / "test-skill"
        skill_file = deployed_skill / "SKILL.md"
        skill_file.write_text("# Modified Skill\n\nThis has been changed.")

        # Check status again (should be modified)
        status = deployment_mgr.check_deployment_status(project_path=project_path)
        assert status["test-skill::skill"] == "modified"

        # Verify modification detection directly
        modified = DeploymentTracker.detect_modifications(
            project_path, "test-skill", "skill"
        )
        assert modified is True

    def test_deploy_multiple_artifacts(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test deploying multiple artifacts at once."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add multiple artifacts
        from skillmeat.core.artifact import Artifact

        artifacts = [
            Artifact(
                name="test-skill",
                type=ArtifactType.SKILL,
                path="skills/test-skill",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
            Artifact(
                name="review",
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
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
        ]

        for artifact in artifacts:
            collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy all artifacts
        deployments = deployment_mgr.deploy_artifacts(
            ["test-skill", "review", "assistant"], project_path=project_path
        )

        # Verify all deployed
        assert len(deployments) == 3

        # Verify files exist
        assert (project_path / ".claude" / "skills" / "test-skill").exists()
        assert (project_path / ".claude" / "commands" / "review.md").exists()
        assert (project_path / ".claude" / "agents" / "assistant.md").exists()

        # List deployments
        listed = deployment_mgr.list_deployments(project_path=project_path)
        assert len(listed) == 3

    def test_deploy_all(self, temp_config, temp_collection, tmp_path, monkeypatch):
        """Test deploying all artifacts from collection."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add multiple artifacts
        from skillmeat.core.artifact import Artifact

        artifacts = [
            Artifact(
                name="skill1",
                type=ArtifactType.SKILL,
                path="skills/skill1",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
            Artifact(
                name="skill2",
                type=ArtifactType.SKILL,
                path="skills/skill2",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            ),
        ]

        # Create directories for artifacts
        collection_path = temp_config.get_collection_path("default")
        for artifact in artifacts:
            artifact_dir = collection_path / artifact.path
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "SKILL.md").write_text(f"# {artifact.name}")
            collection.add_artifact(artifact)

        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy all
        deployments = deployment_mgr.deploy_all(project_path=project_path)

        # Should deploy all artifacts in collection
        assert len(deployments) == 2

    def test_overwrite_prompt(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test overwrite prompt when deploying to existing location."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add artifact
        from skillmeat.core.artifact import Artifact

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        # Create existing deployment
        existing_dir = project_path / ".claude" / "skills" / "test-skill"
        existing_dir.mkdir(parents=True)
        (existing_dir / "SKILL.md").write_text("# Existing")

        # Track confirmation calls
        confirm_calls = []

        def mock_confirm(prompt):
            confirm_calls.append(prompt)
            return False  # Decline overwrite

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", mock_confirm)

        # Attempt to deploy
        deployments = deployment_mgr.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Should be declined
        assert len(deployments) == 0

        # Verify confirmation was requested
        assert len(confirm_calls) == 1
        assert "Overwrite" in confirm_calls[0]

        # Verify original file unchanged
        content = (existing_dir / "SKILL.md").read_text()
        assert content == "# Existing"

    def test_redeploy_updates_tracking(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test that redeploying updates the tracking information."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add artifact
        from skillmeat.core.artifact import Artifact

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Initial deployment
        deployments1 = deployment_mgr.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )
        original_sha = deployments1[0].content_hash

        # Modify collection artifact
        collection_path = temp_config.get_collection_path("default")
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        skill_file.write_text("# Updated Test Skill")

        # Redeploy (accept overwrite)
        deployments2 = deployment_mgr.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )
        new_sha = deployments2[0].content_hash

        # SHA should be different
        assert new_sha != original_sha

        # Verify tracking record updated
        deployment = DeploymentTracker.get_deployment(
            project_path, "test-skill", "skill"
        )
        assert deployment.content_hash == new_sha

    def test_command_and_agent_deployment(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test deploying command and agent artifacts."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Add command and agent
        from skillmeat.core.artifact import Artifact

        cmd = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        agent = Artifact(
            name="assistant",
            type=ArtifactType.AGENT,
            path="agents/assistant.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        collection.add_artifact(cmd)
        collection.add_artifact(agent)
        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy both
        deployments = deployment_mgr.deploy_artifacts(
            ["review", "assistant"], project_path=project_path
        )

        # Verify both deployed
        assert len(deployments) == 2

        # Commands and agents are single files
        assert (project_path / ".claude" / "commands" / "review.md").exists()
        assert (project_path / ".claude" / "agents" / "assistant.md").exists()

        # Verify they're tracked
        cmd_deployment = DeploymentTracker.get_deployment(
            project_path, "review", "command"
        )
        agent_deployment = DeploymentTracker.get_deployment(
            project_path, "assistant", "agent"
        )

        assert cmd_deployment is not None
        assert agent_deployment is not None

    def test_empty_project_deployment(
        self, temp_config, temp_collection, tmp_path, monkeypatch
    ):
        """Test deploying to a project with no .claude directory."""
        collection_mgr, collection = temp_collection
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Create project directory (no .claude dir)
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # Verify .claude doesn't exist
        assert not (project_path / ".claude").exists()

        # Add artifact
        from skillmeat.core.artifact import Artifact

        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        collection.add_artifact(artifact)
        collection_mgr.save_collection(collection)

        monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda x: True)

        # Deploy (should create .claude directory)
        deployments = deployment_mgr.deploy_artifacts(
            ["test-skill"], project_path=project_path
        )

        # Verify .claude was created
        assert (project_path / ".claude").exists()
        assert (project_path / ".claude" / "skills" / "test-skill").exists()

        # Verify deployment tracking file created
        tracking_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert tracking_file.exists()
