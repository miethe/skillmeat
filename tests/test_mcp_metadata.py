"""Unit tests for MCP metadata models and Collection integration."""

import pytest
from datetime import datetime

from skillmeat.core.collection import Collection
from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType


class TestMCPServerMetadata:
    """Test MCPServerMetadata class."""

    def test_create_minimal_metadata(self):
        """Test creating MCP metadata with minimal required fields."""
        metadata = MCPServerMetadata(
            name="filesystem", repo="anthropics/mcp-filesystem"
        )

        assert metadata.name == "filesystem"
        assert metadata.repo == "anthropics/mcp-filesystem"
        assert metadata.version == "latest"
        assert metadata.env_vars == {}
        assert metadata.description is None
        assert metadata.status == MCPServerStatus.NOT_INSTALLED

    def test_create_full_metadata(self):
        """Test creating MCP metadata with all fields."""
        metadata = MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            version="v1.0.0",
            env_vars={"ROOT_PATH": "/home/user"},
            description="File system access MCP server",
            status=MCPServerStatus.INSTALLED,
        )

        assert metadata.name == "filesystem"
        assert metadata.repo == "anthropics/mcp-filesystem"
        assert metadata.version == "v1.0.0"
        assert metadata.env_vars == {"ROOT_PATH": "/home/user"}
        assert metadata.description == "File system access MCP server"
        assert metadata.status == MCPServerStatus.INSTALLED

    def test_validate_empty_name(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            MCPServerMetadata(name="", repo="user/repo")

    def test_validate_invalid_name_characters(self):
        """Test that invalid characters in name raise ValueError."""
        with pytest.raises(
            ValueError, match="must contain only alphanumeric characters"
        ):
            MCPServerMetadata(name="invalid name!", repo="user/repo")

    def test_validate_name_with_path_separator(self):
        """Test that name with path separator raises ValueError."""
        with pytest.raises(ValueError, match="cannot contain path separators"):
            MCPServerMetadata(name="path/traversal", repo="user/repo")

        with pytest.raises(ValueError, match="cannot contain path separators"):
            MCPServerMetadata(name="path\\traversal", repo="user/repo")

    def test_validate_name_with_parent_reference(self):
        """Test that name with parent directory reference raises ValueError."""
        with pytest.raises(
            ValueError, match="cannot contain parent directory references"
        ):
            MCPServerMetadata(name="..parent", repo="user/repo")

    def test_validate_name_starting_with_dot(self):
        """Test that name starting with dot raises ValueError."""
        with pytest.raises(ValueError, match="cannot start with"):
            MCPServerMetadata(name=".hidden", repo="user/repo")

    def test_validate_empty_repo(self):
        """Test that empty repo raises ValueError."""
        with pytest.raises(ValueError, match="Repository URL cannot be empty"):
            MCPServerMetadata(name="test", repo="")

    def test_validate_full_github_url(self):
        """Test that full GitHub URL is accepted."""
        metadata = MCPServerMetadata(
            name="test", repo="https://github.com/user/repo"
        )
        assert metadata.repo == "https://github.com/user/repo"

    def test_validate_github_url_without_scheme(self):
        """Test that GitHub URL without scheme is accepted."""
        metadata = MCPServerMetadata(name="test", repo="github.com/user/repo")
        assert metadata.repo == "github.com/user/repo"

    def test_validate_short_format_repo(self):
        """Test that short format user/repo is accepted."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        assert metadata.repo == "user/repo"

    def test_validate_short_format_with_subpath(self):
        """Test that short format with subpath is accepted."""
        metadata = MCPServerMetadata(name="test", repo="user/repo/subpath/to/server")
        assert metadata.repo == "user/repo/subpath/to/server"

    def test_validate_non_github_url_rejected(self):
        """Test that non-GitHub URLs are rejected."""
        with pytest.raises(ValueError, match="only GitHub repositories are supported"):
            MCPServerMetadata(name="test", repo="https://gitlab.com/user/repo")

    def test_validate_invalid_short_format(self):
        """Test that invalid short format raises ValueError."""
        with pytest.raises(ValueError, match="expected format 'user/repo'"):
            MCPServerMetadata(name="test", repo="onlyuser")

    def test_validate_env_vars_not_dict(self):
        """Test that non-dict env_vars raises ValueError."""
        with pytest.raises(ValueError, match="env_vars must be a dictionary"):
            MCPServerMetadata(name="test", repo="user/repo", env_vars="not a dict")

    def test_validate_env_vars_non_string_key(self):
        """Test that non-string env var key raises ValueError."""
        with pytest.raises(ValueError, match="Environment variable key must be string"):
            MCPServerMetadata(name="test", repo="user/repo", env_vars={123: "value"})

    def test_validate_env_vars_non_string_value(self):
        """Test that non-string env var value raises ValueError."""
        with pytest.raises(
            ValueError, match="Environment variable value .* must be string"
        ):
            MCPServerMetadata(name="test", repo="user/repo", env_vars={"KEY": 123})

    def test_composite_key(self):
        """Test composite_key returns the name."""
        metadata = MCPServerMetadata(name="filesystem", repo="user/repo")
        assert metadata.composite_key() == "filesystem"

    def test_mark_installed(self):
        """Test mark_installed updates status and timestamp."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        assert metadata.status == MCPServerStatus.NOT_INSTALLED
        assert metadata.installed_at is None

        metadata.mark_installed()

        assert metadata.status == MCPServerStatus.INSTALLED
        assert metadata.installed_at is not None
        # Verify it's a valid ISO 8601 timestamp
        datetime.fromisoformat(metadata.installed_at)

    def test_mark_error(self):
        """Test mark_error updates status."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        metadata.mark_error()
        assert metadata.status == MCPServerStatus.ERROR

    def test_mark_updating(self):
        """Test mark_updating updates status."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        metadata.mark_updating()
        assert metadata.status == MCPServerStatus.UPDATING

    def test_update_version(self):
        """Test update_version sets SHA and version."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        metadata.update_version("abc123def456", "v1.0.0")

        assert metadata.resolved_sha == "abc123def456"
        assert metadata.resolved_version == "v1.0.0"
        assert metadata.last_updated is not None
        # Verify it's a valid ISO 8601 timestamp
        datetime.fromisoformat(metadata.last_updated)

    def test_update_version_without_tag(self):
        """Test update_version with only SHA."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        metadata.update_version("abc123def456")

        assert metadata.resolved_sha == "abc123def456"
        assert metadata.resolved_version is None
        assert metadata.last_updated is not None

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        metadata = MCPServerMetadata(name="test", repo="user/repo")
        result = metadata.to_dict()

        assert result == {
            "name": "test",
            "repo": "user/repo",
            "version": "latest",
        }

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        metadata = MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            version="v1.0.0",
            env_vars={"ROOT_PATH": "/home/user", "DEBUG": "true"},
            description="File system access",
            status=MCPServerStatus.INSTALLED,
            installed_at="2025-11-17T10:00:00",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
            last_updated="2025-11-17T11:00:00",
        )
        result = metadata.to_dict()

        assert result == {
            "name": "filesystem",
            "repo": "anthropics/mcp-filesystem",
            "version": "v1.0.0",
            "env_vars": {"ROOT_PATH": "/home/user", "DEBUG": "true"},
            "description": "File system access",
            "status": "installed",
            "installed_at": "2025-11-17T10:00:00",
            "resolved_sha": "abc123",
            "resolved_version": "v1.0.0",
            "last_updated": "2025-11-17T11:00:00",
        }

    def test_from_dict_minimal(self):
        """Test from_dict with minimal fields."""
        data = {"name": "test", "repo": "user/repo"}
        metadata = MCPServerMetadata.from_dict(data)

        assert metadata.name == "test"
        assert metadata.repo == "user/repo"
        assert metadata.version == "latest"
        assert metadata.env_vars == {}
        assert metadata.status == MCPServerStatus.NOT_INSTALLED

    def test_from_dict_full(self):
        """Test from_dict with all fields."""
        data = {
            "name": "filesystem",
            "repo": "anthropics/mcp-filesystem",
            "version": "v1.0.0",
            "env_vars": {"ROOT_PATH": "/home/user"},
            "description": "File system access",
            "status": "installed",
            "installed_at": "2025-11-17T10:00:00",
            "resolved_sha": "abc123",
            "resolved_version": "v1.0.0",
            "last_updated": "2025-11-17T11:00:00",
        }
        metadata = MCPServerMetadata.from_dict(data)

        assert metadata.name == "filesystem"
        assert metadata.repo == "anthropics/mcp-filesystem"
        assert metadata.version == "v1.0.0"
        assert metadata.env_vars == {"ROOT_PATH": "/home/user"}
        assert metadata.description == "File system access"
        assert metadata.status == MCPServerStatus.INSTALLED
        assert metadata.installed_at == "2025-11-17T10:00:00"
        assert metadata.resolved_sha == "abc123"
        assert metadata.resolved_version == "v1.0.0"
        assert metadata.last_updated == "2025-11-17T11:00:00"

    def test_from_dict_missing_name(self):
        """Test from_dict raises error when name is missing."""
        data = {"repo": "user/repo"}
        with pytest.raises(ValueError, match="Missing required field 'name'"):
            MCPServerMetadata.from_dict(data)

    def test_from_dict_missing_repo(self):
        """Test from_dict raises error when repo is missing."""
        data = {"name": "test"}
        with pytest.raises(ValueError, match="Missing required field 'repo'"):
            MCPServerMetadata.from_dict(data)

    def test_roundtrip_serialization(self):
        """Test that to_dict/from_dict roundtrip preserves data."""
        original = MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            version="v1.0.0",
            env_vars={"ROOT_PATH": "/home/user"},
            description="File system access",
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = MCPServerMetadata.from_dict(data)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.repo == original.repo
        assert restored.version == original.version
        assert restored.env_vars == original.env_vars
        assert restored.description == original.description


class TestCollectionMCPIntegration:
    """Test Collection class integration with MCP servers."""

    @pytest.fixture
    def sample_collection(self):
        """Provide a sample collection."""
        now = datetime(2025, 11, 17, 12, 0, 0)
        return Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
            mcp_servers=[],
        )

    @pytest.fixture
    def sample_mcp_server(self):
        """Provide a sample MCP server."""
        return MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            version="latest",
            env_vars={"ROOT_PATH": "/home/user"},
            description="File system access",
        )

    def test_add_mcp_server(self, sample_collection, sample_mcp_server):
        """Test adding MCP server to collection."""
        sample_collection.add_mcp_server(sample_mcp_server)

        assert len(sample_collection.mcp_servers) == 1
        assert sample_collection.mcp_servers[0].name == "filesystem"

    def test_add_duplicate_mcp_server_raises_error(
        self, sample_collection, sample_mcp_server
    ):
        """Test that adding duplicate MCP server raises ValueError."""
        sample_collection.add_mcp_server(sample_mcp_server)

        with pytest.raises(ValueError, match="already exists in collection"):
            sample_collection.add_mcp_server(sample_mcp_server)

    def test_find_mcp_server(self, sample_collection, sample_mcp_server):
        """Test finding MCP server by name."""
        sample_collection.add_mcp_server(sample_mcp_server)

        found = sample_collection.find_mcp_server("filesystem")
        assert found is not None
        assert found.name == "filesystem"

    def test_find_mcp_server_not_found(self, sample_collection):
        """Test finding non-existent MCP server returns None."""
        found = sample_collection.find_mcp_server("nonexistent")
        assert found is None

    def test_get_mcp_server(self, sample_collection, sample_mcp_server):
        """Test get_mcp_server alias."""
        sample_collection.add_mcp_server(sample_mcp_server)

        found = sample_collection.get_mcp_server("filesystem")
        assert found is not None
        assert found.name == "filesystem"

    def test_remove_mcp_server(self, sample_collection, sample_mcp_server):
        """Test removing MCP server from collection."""
        sample_collection.add_mcp_server(sample_mcp_server)
        assert len(sample_collection.mcp_servers) == 1

        removed = sample_collection.remove_mcp_server("filesystem")
        assert removed is True
        assert len(sample_collection.mcp_servers) == 0

    def test_remove_nonexistent_mcp_server(self, sample_collection):
        """Test removing non-existent MCP server returns False."""
        removed = sample_collection.remove_mcp_server("nonexistent")
        assert removed is False

    def test_list_mcp_servers_empty(self, sample_collection):
        """Test listing MCP servers when collection is empty."""
        servers = sample_collection.list_mcp_servers()
        assert servers == []

    def test_list_mcp_servers(self, sample_collection):
        """Test listing MCP servers."""
        server1 = MCPServerMetadata(name="filesystem", repo="user/repo1")
        server2 = MCPServerMetadata(name="database", repo="user/repo2")

        sample_collection.add_mcp_server(server1)
        sample_collection.add_mcp_server(server2)

        servers = sample_collection.list_mcp_servers()
        assert len(servers) == 2
        assert servers[0].name == "filesystem"
        assert servers[1].name == "database"

    def test_list_mcp_servers_returns_copy(self, sample_collection, sample_mcp_server):
        """Test that list_mcp_servers returns a copy."""
        sample_collection.add_mcp_server(sample_mcp_server)

        servers = sample_collection.list_mcp_servers()
        servers.append(MCPServerMetadata(name="fake", repo="user/fake"))

        # Original collection should not be affected
        assert len(sample_collection.mcp_servers) == 1

    def test_collection_to_dict_with_mcp_servers(self, sample_collection):
        """Test Collection.to_dict includes MCP servers."""
        server = MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            env_vars={"ROOT_PATH": "/home/user"},
        )
        sample_collection.add_mcp_server(server)

        result = sample_collection.to_dict()

        assert "mcp_servers" in result
        assert len(result["mcp_servers"]) == 1
        assert result["mcp_servers"][0]["name"] == "filesystem"
        assert result["mcp_servers"][0]["repo"] == "anthropics/mcp-filesystem"

    def test_collection_to_dict_without_mcp_servers(self, sample_collection):
        """Test Collection.to_dict without MCP servers."""
        result = sample_collection.to_dict()

        # Should not include mcp_servers key when empty
        assert "mcp_servers" not in result

    def test_collection_from_dict_with_mcp_servers(self):
        """Test Collection.from_dict parses MCP servers."""
        data = {
            "collection": {
                "name": "test",
                "version": "1.0.0",
                "created": "2025-11-17T12:00:00",
                "updated": "2025-11-17T12:00:00",
            },
            "artifacts": [],
            "mcp_servers": [
                {
                    "name": "filesystem",
                    "repo": "anthropics/mcp-filesystem",
                    "version": "latest",
                    "env_vars": {"ROOT_PATH": "/home/user"},
                    "description": "File system access",
                }
            ],
        }

        collection = Collection.from_dict(data)

        assert len(collection.mcp_servers) == 1
        assert collection.mcp_servers[0].name == "filesystem"
        assert collection.mcp_servers[0].repo == "anthropics/mcp-filesystem"
        assert collection.mcp_servers[0].env_vars == {"ROOT_PATH": "/home/user"}

    def test_collection_from_dict_without_mcp_servers(self):
        """Test Collection.from_dict handles missing mcp_servers."""
        data = {
            "collection": {
                "name": "test",
                "version": "1.0.0",
                "created": "2025-11-17T12:00:00",
                "updated": "2025-11-17T12:00:00",
            },
            "artifacts": [],
        }

        collection = Collection.from_dict(data)

        assert collection.mcp_servers == []

    def test_collection_roundtrip_with_mcp_servers(self, sample_collection):
        """Test Collection serialization roundtrip with MCP servers."""
        server1 = MCPServerMetadata(
            name="filesystem",
            repo="anthropics/mcp-filesystem",
            env_vars={"ROOT_PATH": "/home/user"},
        )
        server2 = MCPServerMetadata(
            name="database", repo="user/mcp-database", version="v2.0.0"
        )

        sample_collection.add_mcp_server(server1)
        sample_collection.add_mcp_server(server2)

        # Serialize and deserialize
        data = sample_collection.to_dict()
        restored = Collection.from_dict(data)

        # Verify MCP servers are preserved
        assert len(restored.mcp_servers) == 2
        assert restored.mcp_servers[0].name == "filesystem"
        assert restored.mcp_servers[1].name == "database"
        assert restored.mcp_servers[0].env_vars == {"ROOT_PATH": "/home/user"}
        assert restored.mcp_servers[1].version == "v2.0.0"

    def test_collection_with_both_artifacts_and_mcp_servers(self):
        """Test Collection with both artifacts and MCP servers."""
        now = datetime(2025, 11, 17, 12, 0, 0)

        # Create artifact
        artifact = Artifact(
            name="python-skill",
            type=ArtifactType.SKILL,
            path="skills/python-skill/",
            origin="github",
            metadata=ArtifactMetadata(title="Python Skill"),
            added=now,
        )

        # Create MCP server
        mcp_server = MCPServerMetadata(name="filesystem", repo="user/repo")

        # Create collection
        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[artifact],
            created=now,
            updated=now,
            mcp_servers=[mcp_server],
        )

        # Verify both are present
        assert len(collection.artifacts) == 1
        assert len(collection.mcp_servers) == 1

        # Test serialization
        data = collection.to_dict()
        assert len(data["artifacts"]) == 1
        assert len(data["mcp_servers"]) == 1

        # Test deserialization
        restored = Collection.from_dict(data)
        assert len(restored.artifacts) == 1
        assert len(restored.mcp_servers) == 1
