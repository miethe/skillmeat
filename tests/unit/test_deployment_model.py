"""Unit tests for Deployment dataclass."""

from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.deployment import Deployment


class TestDeployment:
    """Test Deployment dataclass."""

    def test_deployment_creation(self):
        """Test creating a Deployment instance."""
        now = datetime.now()
        deployment = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection="default",
            deployed_at=now,
            artifact_path=Path("skills/test-skill"),
            collection_sha="abc123",
            local_modifications=False,
        )

        assert deployment.artifact_name == "test-skill"
        assert deployment.artifact_type == "skill"
        assert deployment.from_collection == "default"
        assert deployment.deployed_at == now
        assert deployment.artifact_path == Path("skills/test-skill")
        assert deployment.collection_sha == "abc123"
        assert deployment.local_modifications is False

    def test_deployment_to_dict(self):
        """Test converting Deployment to dictionary."""
        now = datetime.now()
        deployment = Deployment(
            artifact_name="test-command",
            artifact_type="command",
            from_collection="myproject",
            deployed_at=now,
            artifact_path=Path("commands/review.md"),
            collection_sha="def456",
            local_modifications=True,
        )

        result = deployment.to_dict()

        assert result["artifact_name"] == "test-command"
        assert result["artifact_type"] == "command"
        assert result["from_collection"] == "myproject"
        assert result["deployed_at"] == now.isoformat()
        assert result["artifact_path"] == "commands/review.md"
        assert result["collection_sha"] == "def456"
        assert result["local_modifications"] is True

    def test_deployment_from_dict(self):
        """Test creating Deployment from dictionary."""
        now = datetime.now()
        data = {
            "artifact_name": "test-agent",
            "artifact_type": "agent",
            "from_collection": "shared",
            "deployed_at": now.isoformat(),
            "artifact_path": "agents/assistant.md",
            "collection_sha": "ghi789",
            "local_modifications": False,
        }

        deployment = Deployment.from_dict(data)

        assert deployment.artifact_name == "test-agent"
        assert deployment.artifact_type == "agent"
        assert deployment.from_collection == "shared"
        assert deployment.deployed_at == now
        assert deployment.artifact_path == Path("agents/assistant.md")
        assert deployment.collection_sha == "ghi789"
        assert deployment.local_modifications is False

    def test_deployment_roundtrip(self):
        """Test to_dict/from_dict roundtrip."""
        now = datetime.now()
        original = Deployment(
            artifact_name="roundtrip-test",
            artifact_type="skill",
            from_collection="default",
            deployed_at=now,
            artifact_path=Path("skills/roundtrip-test"),
            collection_sha="roundtrip123",
            local_modifications=True,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = Deployment.from_dict(data)

        assert restored.artifact_name == original.artifact_name
        assert restored.artifact_type == original.artifact_type
        assert restored.from_collection == original.from_collection
        assert restored.deployed_at == original.deployed_at
        assert restored.artifact_path == original.artifact_path
        assert restored.collection_sha == original.collection_sha
        assert restored.local_modifications == original.local_modifications

    def test_deployment_datetime_handling(self):
        """Test that datetime serialization works correctly."""
        # Test with a specific datetime
        dt = datetime(2025, 1, 15, 10, 30, 45)
        deployment = Deployment(
            artifact_name="datetime-test",
            artifact_type="command",
            from_collection="default",
            deployed_at=dt,
            artifact_path=Path("commands/test.md"),
            collection_sha="dt123",
        )

        data = deployment.to_dict()
        assert data["deployed_at"] == "2025-01-15T10:30:45"

        restored = Deployment.from_dict(data)
        assert restored.deployed_at == dt

    def test_deployment_default_local_modifications(self):
        """Test that local_modifications defaults to False."""
        data = {
            "artifact_name": "default-test",
            "artifact_type": "skill",
            "from_collection": "default",
            "deployed_at": datetime.now().isoformat(),
            "artifact_path": "skills/default-test",
            "collection_sha": "default123",
            # Note: local_modifications not in data
        }

        deployment = Deployment.from_dict(data)
        assert deployment.local_modifications is False

    def test_deployment_path_types(self):
        """Test that artifact_path handles both string and Path types."""
        now = datetime.now()

        # Create with Path
        deployment1 = Deployment(
            artifact_name="path-test",
            artifact_type="skill",
            from_collection="default",
            deployed_at=now,
            artifact_path=Path("skills/path-test"),
            collection_sha="path123",
        )
        assert isinstance(deployment1.artifact_path, Path)

        # Serialize and deserialize
        data = deployment1.to_dict()
        assert isinstance(data["artifact_path"], str)

        deployment2 = Deployment.from_dict(data)
        assert isinstance(deployment2.artifact_path, Path)
        assert deployment2.artifact_path == Path("skills/path-test")
