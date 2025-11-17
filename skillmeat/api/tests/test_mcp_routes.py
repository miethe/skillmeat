"""Tests for MCP server management API endpoints.

Tests the REST API for managing MCP servers including CRUD operations,
deployment, and status checks.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from skillmeat.api.server import create_app
from skillmeat.api.config import APISettings
from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus
from skillmeat.core.mcp.deployment import DeploymentResult


@pytest.fixture
def api_settings():
    """Create test API settings."""
    return APISettings(
        env="test",
        api_key_enabled=False,  # Disable auth for testing
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """Create test client."""
    app = create_app(api_settings)
    return TestClient(app)


@pytest.fixture
def mock_collection(tmp_path):
    """Create mock collection with MCP servers."""
    from skillmeat.core.collection import Collection
    from datetime import datetime

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[],
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        mcp_servers=[
            MCPServerMetadata(
                name="filesystem",
                repo="anthropics/mcp-filesystem",
                version="latest",
                description="File system access server",
                env_vars={"ROOT_PATH": "/home/user"},
                status=MCPServerStatus.INSTALLED,
            ),
            MCPServerMetadata(
                name="git",
                repo="anthropics/mcp-git",
                version="v1.0.0",
                description="Git operations server",
                env_vars={},
                status=MCPServerStatus.NOT_INSTALLED,
            ),
        ],
    )
    return collection


class TestMCPServerList:
    """Test listing MCP servers."""

    def test_list_servers_empty(self, client, monkeypatch):
        """Test listing servers when collection is empty."""
        from skillmeat.core.collection import Collection
        from datetime import datetime

        empty_collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
            mcp_servers=[],
        )

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = empty_collection

            response = client.get("/api/v1/mcp/servers")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 0
            assert data["servers"] == []

    def test_list_servers_with_data(self, client, mock_collection):
        """Test listing servers with data."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            response = client.get("/api/v1/mcp/servers")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 2
            assert len(data["servers"]) == 2
            assert data["servers"][0]["name"] == "filesystem"
            assert data["servers"][1]["name"] == "git"


class TestMCPServerGet:
    """Test getting a specific MCP server."""

    def test_get_server_success(self, client, mock_collection):
        """Test getting server details."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            response = client.get("/api/v1/mcp/servers/filesystem")
            assert response.status_code == 200

            data = response.json()
            assert data["name"] == "filesystem"
            assert data["repo"] == "anthropics/mcp-filesystem"
            assert data["status"] == "installed"

    def test_get_server_not_found(self, client, mock_collection):
        """Test getting non-existent server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            response = client.get("/api/v1/mcp/servers/nonexistent")
            assert response.status_code == 404


class TestMCPServerCreate:
    """Test creating MCP servers."""

    def test_create_server_success(self, client, mock_collection):
        """Test creating a new server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection
            mock_mgr.save_collection.return_value = None

            request_data = {
                "name": "newserver",
                "repo": "user/repo",
                "version": "latest",
                "description": "Test server",
                "env_vars": {"KEY": "value"},
            }

            response = client.post("/api/v1/mcp/servers", json=request_data)
            assert response.status_code == 201

            data = response.json()
            assert data["name"] == "newserver"
            assert data["repo"] == "user/repo"
            assert data["status"] == "not_installed"

    def test_create_server_invalid_name(self, client, mock_collection):
        """Test creating server with invalid name."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            request_data = {
                "name": "invalid name!",  # Spaces and special chars not allowed
                "repo": "user/repo",
                "version": "latest",
            }

            response = client.post("/api/v1/mcp/servers", json=request_data)
            assert response.status_code == 400

    def test_create_server_duplicate(self, client, mock_collection):
        """Test creating server with duplicate name."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            request_data = {
                "name": "filesystem",  # Already exists
                "repo": "user/repo",
                "version": "latest",
            }

            response = client.post("/api/v1/mcp/servers", json=request_data)
            assert response.status_code == 409


class TestMCPServerUpdate:
    """Test updating MCP servers."""

    def test_update_server_success(self, client, mock_collection):
        """Test updating server configuration."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection
            mock_mgr.save_collection.return_value = None

            request_data = {
                "description": "Updated description",
                "env_vars": {"NEW_KEY": "new_value"},
            }

            response = client.put("/api/v1/mcp/servers/filesystem", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data["description"] == "Updated description"
            assert "NEW_KEY" in data["env_vars"]

    def test_update_server_not_found(self, client, mock_collection):
        """Test updating non-existent server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            request_data = {"description": "Updated"}

            response = client.put("/api/v1/mcp/servers/nonexistent", json=request_data)
            assert response.status_code == 404


class TestMCPServerDelete:
    """Test deleting MCP servers."""

    def test_delete_server_success(self, client, mock_collection):
        """Test deleting a server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection
            mock_mgr.save_collection.return_value = None

            response = client.delete("/api/v1/mcp/servers/git")
            assert response.status_code == 204

    def test_delete_server_not_found(self, client, mock_collection):
        """Test deleting non-existent server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            mock_mgr.list_collections.return_value = ["test"]
            mock_mgr.load_collection.return_value = mock_collection

            response = client.delete("/api/v1/mcp/servers/nonexistent")
            assert response.status_code == 404


class TestMCPServerDeployment:
    """Test deploying MCP servers."""

    def test_deploy_server_success(self, client, mock_collection, tmp_path):
        """Test deploying a server."""
        deployment_result = DeploymentResult(
            server_name="filesystem",
            success=True,
            settings_path=tmp_path / "settings.json",
            backup_path=tmp_path / "backup.json",
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
        )

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            with patch("skillmeat.core.mcp.deployment.MCPDeploymentManager") as mock_deploy:
                mock_mgr.list_collections.return_value = ["test"]
                mock_mgr.load_collection.return_value = mock_collection
                mock_mgr.save_collection.return_value = None

                mock_deploy_instance = Mock()
                mock_deploy_instance.deploy_server.return_value = deployment_result
                mock_deploy.return_value = mock_deploy_instance

                response = client.post(
                    "/api/v1/mcp/servers/filesystem/deploy",
                    json={"dry_run": False, "backup": True},
                )
                assert response.status_code == 200

                data = response.json()
                assert data["success"] is True
                assert "filesystem" in data["message"]
                assert data["command"] == "npx"

    def test_deploy_server_dry_run(self, client, mock_collection, tmp_path):
        """Test deploying with dry run."""
        deployment_result = DeploymentResult(
            server_name="filesystem",
            success=True,
            settings_path=tmp_path / "settings.json",
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
        )

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            with patch("skillmeat.core.mcp.deployment.MCPDeploymentManager") as mock_deploy:
                mock_mgr.list_collections.return_value = ["test"]
                mock_mgr.load_collection.return_value = mock_collection

                mock_deploy_instance = Mock()
                mock_deploy_instance.deploy_server.return_value = deployment_result
                mock_deploy.return_value = mock_deploy_instance

                response = client.post(
                    "/api/v1/mcp/servers/filesystem/deploy",
                    json={"dry_run": True},
                )
                assert response.status_code == 200

                data = response.json()
                assert data["success"] is True
                assert "DRY RUN" in data["message"]

    def test_undeploy_server_success(self, client, mock_collection):
        """Test undeploying a server."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_mgr:
            with patch("skillmeat.core.mcp.deployment.MCPDeploymentManager") as mock_deploy:
                mock_mgr.list_collections.return_value = ["test"]
                mock_mgr.load_collection.return_value = mock_collection

                mock_deploy_instance = Mock()
                mock_deploy_instance.get_settings_path.return_value = "/path/to/settings.json"
                mock_deploy_instance.undeploy_server.return_value = True
                mock_deploy.return_value = mock_deploy_instance

                response = client.post("/api/v1/mcp/servers/filesystem/undeploy")
                assert response.status_code == 200

                data = response.json()
                assert data["success"] is True
                assert "filesystem" in data["message"]


class TestMCPServerStatus:
    """Test getting deployment status."""

    def test_get_deployment_status(self, client, tmp_path):
        """Test getting deployment status for a server."""
        with patch("skillmeat.core.mcp.deployment.MCPDeploymentManager") as mock_deploy:
            mock_deploy_instance = Mock()
            mock_deploy_instance.get_settings_path.return_value = tmp_path / "settings.json"
            mock_deploy_instance.is_server_deployed.return_value = True
            mock_deploy_instance.read_settings.return_value = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@anthropic/mcp-filesystem"],
                    }
                }
            }
            mock_deploy.return_value = mock_deploy_instance

            response = client.get("/api/v1/mcp/servers/filesystem/status")
            assert response.status_code == 200

            data = response.json()
            assert data["deployed"] is True
            assert data["command"] == "npx"
            assert data["args"] == ["-y", "@anthropic/mcp-filesystem"]
