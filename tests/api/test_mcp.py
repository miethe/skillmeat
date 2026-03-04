"""Tests for MCP server management API endpoints.

Covers all routes in skillmeat/api/routers/mcp.py:
- GET  /api/v1/mcp/servers
- GET  /api/v1/mcp/servers/{name}
- POST /api/v1/mcp/servers
- PUT  /api/v1/mcp/servers/{name}
- DELETE /api/v1/mcp/servers/{name}
- POST /api/v1/mcp/servers/{name}/deploy
- POST /api/v1/mcp/servers/{name}/undeploy
- GET  /api/v1/mcp/servers/{name}/status
- GET  /api/v1/mcp/servers/{name}/health
- GET  /api/v1/mcp/health
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.mcp.health import HealthStatus
from skillmeat.core.mcp.metadata import MCPServerStatus


@pytest.fixture
def test_settings():
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    from skillmeat.api.config import get_settings

    _app = create_app(test_settings)
    _app.dependency_overrides[get_settings] = lambda: test_settings
    return _app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _make_server_metadata(name="test-server"):
    """Return a realistic MCPServerMetadata mock."""
    server = MagicMock()
    server.name = name
    server.repo = "anthropics/mcp-test"
    server.version = "latest"
    server.description = "Test MCP server"
    server.env_vars = {}
    server.status = MCPServerStatus.NOT_INSTALLED
    server.installed_at = None
    server.resolved_sha = None
    server.resolved_version = None
    server.last_updated = None
    return server


def _make_collection_mock(servers=None):
    """Return a collection mock pre-loaded with given server list."""
    coll = MagicMock()
    coll.list_mcp_servers.return_value = servers or []
    return coll


# ---------------------------------------------------------------------------
# GET /api/v1/mcp/servers
# ---------------------------------------------------------------------------


class TestListMCPServers:
    def test_list_mcp_servers_success(self, client):
        """Listing servers returns 200 with a server list."""
        server = _make_server_metadata()
        coll = _make_collection_mock(servers=[server])
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "servers" in data
        assert "total" in data

    def test_list_mcp_servers_empty_collections_returns_empty(self, client):
        """No collections in manager → empty server list, not an error."""
        mgr = MagicMock()
        mgr.list_collections.return_value = []

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["servers"] == []

    def test_list_mcp_servers_with_collection_query_param(self, client):
        """?collection=mycoll is forwarded to the manager."""
        server = _make_server_metadata()
        coll = _make_collection_mock(servers=[server])
        mgr = MagicMock()
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers?collection=mycoll")

        assert response.status_code == status.HTTP_200_OK
        mgr.load_collection.assert_called_with("mycoll")

    def test_list_mcp_servers_error_returns_500(self, client):
        """Unexpected exception from the manager → 500."""
        mgr = MagicMock()
        mgr.list_collections.side_effect = RuntimeError("disk read failed")

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# GET /api/v1/mcp/servers/{name}
# ---------------------------------------------------------------------------


class TestGetMCPServer:
    def test_get_mcp_server_success(self, client):
        """Known server is returned with 200."""
        server = _make_server_metadata()
        coll = MagicMock()
        coll.find_mcp_server.return_value = server
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers/test-server")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "test-server"

    def test_get_mcp_server_not_found(self, client):
        """Server not in collection → 404."""
        coll = MagicMock()
        coll.find_mcp_server.return_value = None
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers/no-such-server")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_mcp_server_no_collections_returns_404(self, client):
        """No collections available → 404."""
        mgr = MagicMock()
        mgr.list_collections.return_value = []

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.get("/api/v1/mcp/servers/test-server")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/v1/mcp/servers
# ---------------------------------------------------------------------------


class TestCreateMCPServer:
    def test_create_mcp_server_success(self, client):
        """Valid payload creates server and returns 201."""
        server = _make_server_metadata("new-server")
        coll = MagicMock()
        coll.find_mcp_server.return_value = server
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPServerMetadata"
        ) as mock_meta:
            mock_meta.return_value = server
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.post(
                "/api/v1/mcp/servers",
                json={
                    "name": "new-server",
                    "repo": "anthropics/mcp-test",
                    "version": "latest",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_mcp_server_conflict_returns_409(self, client):
        """Duplicate server name → 409 Conflict."""
        coll = MagicMock()
        coll.add_mcp_server.side_effect = ValueError("server already exists")
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPServerMetadata"
        ) as mock_meta:
            mock_meta.return_value = MagicMock()
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.post(
                "/api/v1/mcp/servers",
                json={
                    "name": "dup-server",
                    "repo": "anthropics/mcp-test",
                    "version": "latest",
                },
            )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_mcp_server_invalid_metadata_returns_400(self, client):
        """MCPServerMetadata validation failure → 400 Bad Request."""
        coll = MagicMock()
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPServerMetadata"
        ) as mock_meta:
            mock_meta.side_effect = ValueError("bad repo url")
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.post(
                "/api/v1/mcp/servers",
                json={
                    "name": "bad-server",
                    "repo": "not-a-repo",
                    "version": "latest",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# PUT /api/v1/mcp/servers/{name}
# ---------------------------------------------------------------------------


class TestUpdateMCPServer:
    def test_update_mcp_server_success(self, client):
        """Existing server is updated and returned with 200."""
        server = _make_server_metadata()
        server._validate_repo_url = MagicMock()
        coll = MagicMock()
        coll.find_mcp_server.return_value = server
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.put(
                "/api/v1/mcp/servers/test-server",
                json={"description": "Updated description"},
            )

        assert response.status_code == status.HTTP_200_OK

    def test_update_mcp_server_not_found_returns_404(self, client):
        """Updating non-existent server → 404."""
        coll = MagicMock()
        coll.find_mcp_server.return_value = None
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.put(
                "/api/v1/mcp/servers/ghost",
                json={"version": "v2.0.0"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /api/v1/mcp/servers/{name}
# ---------------------------------------------------------------------------


class TestDeleteMCPServer:
    def test_delete_mcp_server_success(self, client):
        """Existing server is removed and 204 is returned."""
        coll = MagicMock()
        coll.remove_mcp_server.return_value = True
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.delete("/api/v1/mcp/servers/test-server")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_mcp_server_not_found_returns_404(self, client):
        """Server not found → remove returns False → 404."""
        coll = MagicMock()
        coll.remove_mcp_server.return_value = False
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = MagicMock()
            response = client.delete("/api/v1/mcp/servers/no-such-server")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/v1/mcp/servers/{name}/deploy
# ---------------------------------------------------------------------------


class TestDeployMCPServer:
    def test_deploy_mcp_server_success(self, client):
        """Successful deployment returns 200 with success=True."""
        server = _make_server_metadata()
        coll = MagicMock()
        coll.find_mcp_server.return_value = server
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        deploy_result = MagicMock()
        deploy_result.success = True
        deploy_result.settings_path = None
        deploy_result.backup_path = None
        deploy_result.env_file_path = None
        deploy_result.command = "npx"
        deploy_result.args = []
        deploy_result.error_message = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.collection_manager = mgr
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.deploy_server.return_value = deploy_result
            response = client.post(
                "/api/v1/mcp/servers/test-server/deploy",
                json={"dry_run": False, "backup": False},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_deploy_mcp_server_not_found_returns_404(self, client):
        """Deploying a server not in collection → 404."""
        coll = MagicMock()
        coll.find_mcp_server.return_value = None
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.collection_manager = mgr
            mock_state.config_manager = cfg_mgr
            response = client.post(
                "/api/v1/mcp/servers/ghost/deploy",
                json={"dry_run": False, "backup": False},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deploy_mcp_server_dry_run(self, client):
        """dry_run=True returns success with [DRY RUN] in message."""
        server = _make_server_metadata()
        coll = MagicMock()
        coll.find_mcp_server.return_value = server
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = coll
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        deploy_result = MagicMock()
        deploy_result.success = True
        deploy_result.settings_path = None
        deploy_result.backup_path = None
        deploy_result.env_file_path = None
        deploy_result.command = None
        deploy_result.args = None
        deploy_result.error_message = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.collection_manager = mgr
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.deploy_server.return_value = deploy_result
            response = client.post(
                "/api/v1/mcp/servers/test-server/deploy",
                json={"dry_run": True, "backup": False},
            )

        assert response.status_code == status.HTTP_200_OK
        assert "DRY RUN" in response.json()["message"]


# ---------------------------------------------------------------------------
# POST /api/v1/mcp/servers/{name}/undeploy
# ---------------------------------------------------------------------------


class TestUndeployMCPServer:
    def test_undeploy_mcp_server_success(self, client):
        """Successful undeploy returns 200 with success=True."""
        mgr = MagicMock()
        mgr.list_collections.return_value = ["default"]
        mgr.load_collection.return_value = MagicMock()
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.collection_manager = mgr
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.get_settings_path.return_value = (
                "/path/to/settings.json"
            )
            mock_deploy_cls.return_value.undeploy_server.return_value = True
            response = client.post("/api/v1/mcp/servers/test-server/undeploy")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_undeploy_mcp_server_not_deployed(self, client):
        """Server not deployed → undeploy returns False → success=False."""
        mgr = MagicMock()
        mgr.list_collections.return_value = []
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.collection_manager = mgr
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.get_settings_path.return_value = (
                "/path/to/settings.json"
            )
            mock_deploy_cls.return_value.undeploy_server.return_value = False
            response = client.post("/api/v1/mcp/servers/ghost/undeploy")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/mcp/servers/{name}/status
# ---------------------------------------------------------------------------


class TestGetDeploymentStatus:
    def test_get_deployment_status_deployed(self, client):
        """Deployed server shows deployed=True and settings_path."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.get_settings_path.return_value = (
                "/path/settings.json"
            )
            mock_deploy_cls.return_value.is_server_deployed.return_value = True
            mock_deploy_cls.return_value.read_settings.return_value = {
                "mcpServers": {"test-server": {"command": "npx", "args": []}}
            }
            response = client.get("/api/v1/mcp/servers/test-server/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deployed"] is True
        assert "settings_path" in data

    def test_get_deployment_status_not_deployed(self, client):
        """Server not deployed → deployed=False."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ) as mock_deploy_cls:
            mock_state.config_manager = cfg_mgr
            mock_deploy_cls.return_value.get_settings_path.return_value = (
                "/path/settings.json"
            )
            mock_deploy_cls.return_value.is_server_deployed.return_value = False
            response = client.get("/api/v1/mcp/servers/ghost/status")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deployed"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/mcp/servers/{name}/health
# ---------------------------------------------------------------------------


class TestGetServerHealth:
    def test_get_server_health_success(self, client):
        """Health check returns 200 with status and counts."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        health_result = MagicMock()
        health_result.server_name = "test-server"
        health_result.status = HealthStatus.HEALTHY
        health_result.deployed = True
        health_result.last_seen = None
        health_result.error_count = 0
        health_result.warning_count = 0
        health_result.recent_errors = []
        health_result.recent_warnings = []
        health_result.checked_at = datetime.now(timezone.utc)

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ), patch(
            "skillmeat.api.routers.mcp.MCPHealthChecker"
        ) as mock_health_cls:
            mock_state.config_manager = cfg_mgr
            mock_health_cls.return_value.check_server_health.return_value = (
                health_result
            )
            response = client.get("/api/v1/mcp/servers/test-server/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["server_name"] == "test-server"
        assert "status" in data
        assert "error_count" in data

    def test_get_server_health_error_returns_500(self, client):
        """Health check exception → 500."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ), patch(
            "skillmeat.api.routers.mcp.MCPHealthChecker"
        ) as mock_health_cls:
            mock_state.config_manager = cfg_mgr
            mock_health_cls.return_value.check_server_health.side_effect = (
                RuntimeError("log read error")
            )
            response = client.get("/api/v1/mcp/servers/test-server/health")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# GET /api/v1/mcp/health
# ---------------------------------------------------------------------------


class TestGetAllServersHealth:
    def test_get_all_servers_health_empty(self, client):
        """No deployed servers → empty result with zero counts."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ), patch(
            "skillmeat.api.routers.mcp.MCPHealthChecker"
        ) as mock_health_cls:
            mock_state.config_manager = cfg_mgr
            mock_health_cls.return_value.check_all_servers.return_value = {}
            response = client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["healthy"] == 0

    def test_get_all_servers_health_with_servers(self, client):
        """Multiple servers → counts aggregated correctly."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        now = datetime.now(timezone.utc)

        def _make_result(name, health_status):
            r = MagicMock()
            r.server_name = name
            r.status = health_status
            r.deployed = True
            r.last_seen = None
            r.error_count = 0
            r.warning_count = 0
            r.recent_errors = []
            r.recent_warnings = []
            r.checked_at = now
            return r

        all_results = {
            "server-a": _make_result("server-a", HealthStatus.HEALTHY),
            "server-b": _make_result("server-b", HealthStatus.UNHEALTHY),
        }

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ), patch(
            "skillmeat.api.routers.mcp.MCPHealthChecker"
        ) as mock_health_cls:
            mock_state.config_manager = cfg_mgr
            mock_health_cls.return_value.check_all_servers.return_value = all_results
            response = client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["healthy"] == 1
        assert data["unhealthy"] == 1

    def test_get_all_servers_health_error_returns_500(self, client):
        """Exception in health checker → 500."""
        cfg_mgr = MagicMock()
        cfg_mgr.get.return_value = None

        with patch("skillmeat.api.dependencies.app_state") as mock_state, patch(
            "skillmeat.api.routers.mcp.MCPDeploymentManager"
        ), patch(
            "skillmeat.api.routers.mcp.MCPHealthChecker"
        ) as mock_health_cls:
            mock_state.config_manager = cfg_mgr
            mock_health_cls.return_value.check_all_servers.side_effect = RuntimeError(
                "boom"
            )
            response = client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
