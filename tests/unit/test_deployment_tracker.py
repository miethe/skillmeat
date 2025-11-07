"""Unit tests for DeploymentTracker."""

from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.deployment import Deployment
from skillmeat.storage.deployment import DeploymentTracker


class TestDeploymentTracker:
    """Test DeploymentTracker functionality."""

    def test_get_deployment_file_path(self, tmp_path):
        """Test getting deployment file path."""
        project_path = tmp_path / "project"
        expected_path = project_path / ".claude" / ".skillmeat-deployed.toml"

        result = DeploymentTracker.get_deployment_file_path(project_path)
        assert result == expected_path

    def test_read_deployments_no_file(self, tmp_path):
        """Test reading deployments when file doesn't exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        deployments = DeploymentTracker.read_deployments(project_path)
        assert deployments == []

    def test_write_and_read_deployments(self, tmp_path):
        """Test writing and reading deployments."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        now = datetime.now()
        deployments = [
            Deployment(
                artifact_name="test-skill",
                artifact_type="skill",
                from_collection="default",
                deployed_at=now,
                artifact_path=Path("skills/test-skill"),
                collection_sha="abc123",
                local_modifications=False,
            ),
            Deployment(
                artifact_name="test-command",
                artifact_type="command",
                from_collection="default",
                deployed_at=now,
                artifact_path=Path("commands/test.md"),
                collection_sha="def456",
                local_modifications=True,
            ),
        ]

        # Write
        DeploymentTracker.write_deployments(project_path, deployments)

        # Verify file was created
        deployment_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert deployment_file.exists()

        # Read back
        read_deployments = DeploymentTracker.read_deployments(project_path)
        assert len(read_deployments) == 2
        assert read_deployments[0].artifact_name == "test-skill"
        assert read_deployments[1].artifact_name == "test-command"

    def test_record_deployment_new(self, tmp_path):
        """Test recording a new deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        artifact = Artifact(
            name="my-skill",
            type=ArtifactType.SKILL,
            path="skills/my-skill",
            origin="github",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(project_path, artifact, "default", "sha123")

        # Verify deployment was recorded
        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "my-skill"
        assert deployments[0].artifact_type == "skill"
        assert deployments[0].from_collection == "default"
        assert deployments[0].collection_sha == "sha123"
        assert deployments[0].artifact_path == Path("skills/my-skill")

    def test_record_deployment_update(self, tmp_path):
        """Test updating an existing deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        artifact = Artifact(
            name="my-skill",
            type=ArtifactType.SKILL,
            path="skills/my-skill",
            origin="github",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        # Record initial deployment
        DeploymentTracker.record_deployment(project_path, artifact, "default", "sha123")

        # Record update with new SHA
        DeploymentTracker.record_deployment(project_path, artifact, "default", "sha456")

        # Verify only one deployment exists with updated SHA
        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 1
        assert deployments[0].collection_sha == "sha456"

    def test_record_deployment_command(self, tmp_path):
        """Test recording a command deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        artifact = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(project_path, artifact, "default", "cmdsha")

        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "review"
        assert deployments[0].artifact_type == "command"
        assert deployments[0].artifact_path == Path("commands/review.md")

    def test_record_deployment_agent(self, tmp_path):
        """Test recording an agent deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        artifact = Artifact(
            name="assistant",
            type=ArtifactType.AGENT,
            path="agents/assistant.md",
            origin="github",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(
            project_path, artifact, "default", "agentsha"
        )

        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "assistant"
        assert deployments[0].artifact_type == "agent"
        assert deployments[0].artifact_path == Path("agents/assistant.md")

    def test_get_deployment_exists(self, tmp_path):
        """Test getting a specific deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

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

        # Get deployment
        deployment = DeploymentTracker.get_deployment(
            project_path, "test-skill", "skill"
        )
        assert deployment is not None
        assert deployment.artifact_name == "test-skill"
        assert deployment.collection_sha == "testsha"

    def test_get_deployment_not_found(self, tmp_path):
        """Test getting a deployment that doesn't exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        deployment = DeploymentTracker.get_deployment(
            project_path, "nonexistent", "skill"
        )
        assert deployment is None

    def test_remove_deployment(self, tmp_path):
        """Test removing a deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Add two deployments
        artifact1 = Artifact(
            name="skill1",
            type=ArtifactType.SKILL,
            path="skills/skill1",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        artifact2 = Artifact(
            name="skill2",
            type=ArtifactType.SKILL,
            path="skills/skill2",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(project_path, artifact1, "default", "sha1")
        DeploymentTracker.record_deployment(project_path, artifact2, "default", "sha2")

        # Verify both exist
        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 2

        # Remove one
        DeploymentTracker.remove_deployment(project_path, "skill1", "skill")

        # Verify only one remains
        deployments = DeploymentTracker.read_deployments(project_path)
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "skill2"

    def test_detect_modifications_no_deployment(self, tmp_path):
        """Test detecting modifications when deployment doesn't exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        result = DeploymentTracker.detect_modifications(
            project_path, "nonexistent", "skill"
        )
        assert result is False

    def test_detect_modifications_file_missing(self, tmp_path):
        """Test detecting modifications when deployed file is missing."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        artifact = Artifact(
            name="missing-skill",
            type=ArtifactType.SKILL,
            path="skills/missing-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(
            project_path, artifact, "default", "missingsha"
        )

        result = DeploymentTracker.detect_modifications(
            project_path, "missing-skill", "skill"
        )
        assert result is False

    def test_detect_modifications_no_changes(self, tmp_path):
        """Test detecting modifications when file hasn't changed."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create skill directory and file
        skill_dir = project_path / ".claude" / "skills" / "unchanged-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Unchanged Skill\n\nThis skill hasn't changed.")

        # Compute hash
        from skillmeat.utils.filesystem import compute_content_hash

        skill_hash = compute_content_hash(skill_dir)

        # Record deployment with correct hash
        artifact = Artifact(
            name="unchanged-skill",
            type=ArtifactType.SKILL,
            path="skills/unchanged-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(
            project_path, artifact, "default", skill_hash
        )

        # Check for modifications
        result = DeploymentTracker.detect_modifications(
            project_path, "unchanged-skill", "skill"
        )
        assert result is False

    def test_detect_modifications_with_changes(self, tmp_path):
        """Test detecting modifications when file has changed."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create skill directory and file
        skill_dir = project_path / ".claude" / "skills" / "changed-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Original Content")

        # Record deployment with original hash
        artifact = Artifact(
            name="changed-skill",
            type=ArtifactType.SKILL,
            path="skills/changed-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(
            project_path, artifact, "default", "original_hash"
        )

        # Modify the file
        skill_file.write_text("# Modified Content")

        # Check for modifications
        result = DeploymentTracker.detect_modifications(
            project_path, "changed-skill", "skill"
        )
        assert result is True

    def test_detect_modifications_command(self, tmp_path):
        """Test detecting modifications for a command file."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create command file
        cmd_dir = project_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        cmd_file = cmd_dir / "review.md"
        cmd_file.write_text("# Review Command")

        from skillmeat.utils.filesystem import compute_content_hash

        cmd_hash = compute_content_hash(cmd_file)

        # Record deployment
        artifact = Artifact(
            name="review",
            type=ArtifactType.COMMAND,
            path="commands/review.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )

        DeploymentTracker.record_deployment(project_path, artifact, "default", cmd_hash)

        # No modifications yet
        result = DeploymentTracker.detect_modifications(
            project_path, "review", "command"
        )
        assert result is False

        # Modify the file
        cmd_file.write_text("# Modified Review Command")

        # Should detect modification
        result = DeploymentTracker.detect_modifications(
            project_path, "review", "command"
        )
        assert result is True
