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
            content_hash="abc123",
            local_modifications=False,
        )

        assert deployment.artifact_name == "test-skill"
        assert deployment.artifact_type == "skill"
        assert deployment.from_collection == "default"
        assert deployment.deployed_at == now
        assert deployment.artifact_path == Path("skills/test-skill")
        assert deployment.content_hash == "abc123"
        assert deployment.local_modifications is False

        # collection_sha is deprecated and only populated during serialization
        data = deployment.to_dict()
        assert data["collection_sha"] == "abc123"

    def test_deployment_to_dict(self):
        """Test converting Deployment to dictionary."""
        now = datetime.now()
        deployment = Deployment(
            artifact_name="test-command",
            artifact_type="command",
            from_collection="myproject",
            deployed_at=now,
            artifact_path=Path("commands/review.md"),
            content_hash="def456",
            local_modifications=True,
        )

        result = deployment.to_dict()

        assert result["artifact_name"] == "test-command"
        assert result["artifact_type"] == "command"
        assert result["from_collection"] == "myproject"
        assert result["deployed_at"] == now.isoformat()
        assert result["artifact_path"] == "commands/review.md"
        assert result["content_hash"] == "def456"
        assert result["local_modifications"] is True
        # collection_sha is deprecated but still included in serialization
        assert result["collection_sha"] == "def456"

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
            content_hash="roundtrip123",
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
        assert restored.content_hash == original.content_hash
        assert restored.local_modifications == original.local_modifications
        # collection_sha should be populated from deserialized data
        assert restored.collection_sha == "roundtrip123"

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
            content_hash="dt123",
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
            content_hash="path123",
        )
        assert isinstance(deployment1.artifact_path, Path)

        # Serialize and deserialize
        data = deployment1.to_dict()
        assert isinstance(data["artifact_path"], str)

        deployment2 = Deployment.from_dict(data)
        assert isinstance(deployment2.artifact_path, Path)
        assert deployment2.artifact_path == Path("skills/path-test")

    def test_deployment_merge_base_snapshot(self):
        """Test merge_base_snapshot field."""
        now = datetime.now()

        # Test with merge_base_snapshot
        deployment1 = Deployment(
            artifact_name="merge-test",
            artifact_type="skill",
            from_collection="default",
            deployed_at=now,
            artifact_path=Path("skills/merge-test"),
            content_hash="current123",
            merge_base_snapshot="base456",
        )
        assert deployment1.merge_base_snapshot == "base456"

        # Serialize and verify field is included
        data = deployment1.to_dict()
        assert "merge_base_snapshot" in data
        assert data["merge_base_snapshot"] == "base456"

        # Deserialize and verify field is restored
        restored = Deployment.from_dict(data)
        assert restored.merge_base_snapshot == "base456"

        # Test without merge_base_snapshot (should be None)
        deployment2 = Deployment(
            artifact_name="no-merge-test",
            artifact_type="skill",
            from_collection="default",
            deployed_at=now,
            artifact_path=Path("skills/no-merge-test"),
            content_hash="nomg123",
        )
        assert deployment2.merge_base_snapshot is None

        # Serialize without merge_base_snapshot (field should not be in dict)
        data2 = deployment2.to_dict()
        assert "merge_base_snapshot" not in data2

        # Deserialize old-style deployment without merge_base_snapshot
        old_data = {
            "artifact_name": "old-test",
            "artifact_type": "skill",
            "from_collection": "default",
            "deployed_at": now.isoformat(),
            "artifact_path": "skills/old-test",
            "collection_sha": "old123",
        }
        old_deployment = Deployment.from_dict(old_data)
        assert old_deployment.merge_base_snapshot is None
