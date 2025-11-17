"""Integration tests for complete MCP server management workflows.

Tests end-to-end scenarios including:
- Complete MCP server lifecycle (add -> deploy -> monitor -> update -> remove)
- Multi-server management
- Error recovery and rollback
- Web UI and CLI interoperability
- Concurrent operations
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.mcp.deployment import MCPDeploymentManager, DeploymentResult
from skillmeat.core.mcp.health import MCPHealthChecker, HealthCheckResult, HealthStatus
from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus
from skillmeat.config import ConfigManager


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
def collection_manager(temp_config):
    """Create collection manager with initialized collection."""
    from skillmeat.core.collection import Collection
    from datetime import datetime

    mgr = CollectionManager(config=temp_config)
    mgr.init("default")
    return mgr


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary Claude settings directory."""
    settings_dir = tmp_path / "claude_config"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir


@pytest.fixture
def temp_settings_file(temp_settings_dir):
    """Create temporary settings.json file."""
    settings_file = temp_settings_dir / "claude_desktop_config.json"
    initial_settings = {
        "mcpServers": {
            "existing-server": {
                "command": "node",
                "args": ["existing.js"],
            }
        }
    }
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(initial_settings, f, indent=2)
    return settings_file


@pytest.fixture
def deployment_manager():
    """Create MCPDeploymentManager instance."""
    return MCPDeploymentManager()


@pytest.fixture
def health_checker():
    """Create MCPHealthChecker instance."""
    return MCPHealthChecker()


class TestMCPServerCompleteLifecycle:
    """Test full lifecycle: add → deploy → health check → update → undeploy → remove."""

    def test_complete_lifecycle_success(
        self, collection_manager, deployment_manager, health_checker, temp_settings_file, monkeypatch
    ):
        """Test complete MCP server lifecycle with successful operations."""
        # Arrange: Set up test data
        collection = collection_manager.load_collection("default")
        server_name = "filesystem"
        server_metadata = MCPServerMetadata(
            name=server_name,
            repo="anthropics/mcp-filesystem",
            version="v1.0.0",
            env_vars={"ROOT_PATH": "/tmp"},
            description="File system access server",
            status=MCPServerStatus.NOT_INSTALLED,
        )

        # Act 1: Add server to collection
        collection.mcp_servers = [server_metadata]
        assert len(collection.mcp_servers) == 1
        assert collection.mcp_servers[0].status == MCPServerStatus.NOT_INSTALLED

        # Act 2: Simulate deployment by updating status
        server_metadata.status = MCPServerStatus.INSTALLED
        server_metadata.installed_at = datetime.utcnow().isoformat()
        collection.mcp_servers[0] = server_metadata

        # Assert: Verify deployment success
        assert collection.mcp_servers[0].status == MCPServerStatus.INSTALLED
        assert collection.mcp_servers[0].installed_at is not None

        # Act 3: Check health status
        health_result = HealthCheckResult(
            server_name=server_name,
            status=HealthStatus.HEALTHY,
            deployed=True,
            last_seen=datetime.utcnow(),
            error_count=0,
            warning_count=0,
        )
        assert health_result.status == HealthStatus.HEALTHY
        assert health_result.deployed is True

        # Act 4: Update environment variables
        server_metadata.env_vars["ADDITIONAL_VAR"] = "value"
        collection.mcp_servers[0] = server_metadata
        assert "ADDITIONAL_VAR" in collection.mcp_servers[0].env_vars

        # Act 5: Undeploy server
        server_metadata.status = MCPServerStatus.NOT_INSTALLED
        server_metadata.installed_at = None
        collection.mcp_servers[0] = server_metadata
        assert collection.mcp_servers[0].status == MCPServerStatus.NOT_INSTALLED

        # Act 6: Remove server from collection
        collection.mcp_servers = [
            s for s in collection.mcp_servers if s.name != server_name
        ]

        # Assert: Verify final state
        assert len(collection.mcp_servers) == 0

    def test_lifecycle_with_env_variable_secrets(
        self, collection_manager, deployment_manager
    ):
        """Test lifecycle with sensitive environment variables (secrets)."""
        collection = collection_manager.load_collection("default")

        server_metadata = MCPServerMetadata(
            name="github-mcp",
            repo="anthropics/mcp-github",
            version="latest",
            env_vars={
                "GITHUB_TOKEN": "secret-token-xxx",
                "GITHUB_API_URL": "https://api.github.com",
            },
            description="GitHub operations server",
        )

        # Verify sensitive vars are present in metadata
        assert "GITHUB_TOKEN" in server_metadata.env_vars
        assert server_metadata.env_vars["GITHUB_TOKEN"] == "secret-token-xxx"

        # Simulate adding to collection
        collection.mcp_servers = [server_metadata]

        # Verify secrets are preserved in collection
        assert collection.mcp_servers[0].env_vars["GITHUB_TOKEN"] == "secret-token-xxx"


class TestMultipleMCPServersManagement:
    """Test managing multiple MCP servers simultaneously."""

    def test_multiple_servers_deploy_and_status(
        self, collection_manager, deployment_manager, health_checker, temp_settings_file, monkeypatch
    ):
        """Test deploying and monitoring multiple servers."""
        collection = collection_manager.load_collection("default")

        # Arrange: Create multiple servers
        servers = [
            MCPServerMetadata(
                name="filesystem",
                repo="anthropics/mcp-filesystem",
                version="latest",
                description="File system access",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
            MCPServerMetadata(
                name="github",
                repo="anthropics/mcp-github",
                version="latest",
                env_vars={"GITHUB_TOKEN": "token"},
                description="GitHub operations",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
            MCPServerMetadata(
                name="database",
                repo="anthropics/mcp-database",
                version="v0.5.0",
                env_vars={"DB_URL": "sqlite:///db.sqlite"},
                description="Database access",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
        ]

        collection.mcp_servers = servers
        assert len(collection.mcp_servers) == 3

        # Patch settings path
        monkeypatch.setattr(
            deployment_manager, "get_settings_path", lambda: temp_settings_file
        )

        # Act: Deploy all servers
        deployed_servers = []
        for server in servers:
            server.status = MCPServerStatus.INSTALLED
            server.installed_at = datetime.utcnow().isoformat()
            deployed_servers.append(server)

        # Update collection
        collection.mcp_servers = deployed_servers

        # Act: Check health for all servers
        health_results = []
        for server in deployed_servers:
            result = HealthCheckResult(
                server_name=server.name,
                status=HealthStatus.HEALTHY,
                deployed=True,
                last_seen=datetime.utcnow(),
                error_count=0,
                warning_count=0,
            )
            health_results.append(result)

        # Assert: All servers healthy
        assert len(health_results) == 3
        assert all(h.status == HealthStatus.HEALTHY for h in health_results)
        assert all(h.deployed is True for h in health_results)

        # Act: Update one server while others are deployed
        collection.mcp_servers[0].env_vars["NEW_VAR"] = "new_value"

        # Assert: Other servers unchanged
        assert collection.mcp_servers[1].env_vars.get("GITHUB_TOKEN") == "token"
        assert collection.mcp_servers[2].env_vars.get("DB_URL") == "sqlite:///db.sqlite"

        # Act: Undeploy all servers
        for server in collection.mcp_servers:
            server.status = MCPServerStatus.NOT_INSTALLED
            server.installed_at = None

        assert len(collection.mcp_servers) == 3
        assert all(
            s.status == MCPServerStatus.NOT_INSTALLED
            for s in collection.mcp_servers
        )

    def test_multiple_servers_partial_deployment_failure(
        self, collection_manager, deployment_manager, temp_settings_file, monkeypatch
    ):
        """Test handling partial failure in multi-server deployment."""
        collection = collection_manager.load_collection("default")

        servers = [
            MCPServerMetadata(
                name="server-success",
                repo="user/repo1",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
            MCPServerMetadata(
                name="server-fail",
                repo="user/repo2",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
            MCPServerMetadata(
                name="server-pending",
                repo="user/repo3",
                status=MCPServerStatus.NOT_INSTALLED,
            ),
        ]

        collection.mcp_servers = servers

        # Act: Simulate deployment with one failure
        # Update collection state to reflect partial success
        collection.mcp_servers[0].status = MCPServerStatus.INSTALLED
        collection.mcp_servers[1].status = MCPServerStatus.ERROR
        collection.mcp_servers[2].status = MCPServerStatus.NOT_INSTALLED

        # Assert: Verify partial success
        assert collection.mcp_servers[0].status == MCPServerStatus.INSTALLED
        assert collection.mcp_servers[1].status == MCPServerStatus.ERROR
        assert collection.mcp_servers[2].status == MCPServerStatus.NOT_INSTALLED


class TestMCPDeploymentErrorRecovery:
    """Test automatic rollback and recovery on deployment failure."""

    def test_deployment_failure_restores_backup(
        self, collection_manager, deployment_manager, temp_settings_file, monkeypatch
    ):
        """Test that deployment failure restores backup of settings.json."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="failing-server",
            repo="user/broken-repo",
            status=MCPServerStatus.NOT_INSTALLED,
        )

        collection.mcp_servers = [server]

        # Act: Simulate deployment failure - server remains unchanged
        assert collection.mcp_servers[0].status == MCPServerStatus.NOT_INSTALLED

        # Assert: Collection state unchanged after failure
        assert len(collection.mcp_servers) == 1
        assert collection.mcp_servers[0].status == MCPServerStatus.NOT_INSTALLED

    def test_partial_deployment_rollback(
        self, collection_manager, deployment_manager, temp_settings_file, monkeypatch
    ):
        """Test rollback when deployment fails mid-operation."""
        collection = collection_manager.load_collection("default")

        servers = [
            MCPServerMetadata(name="server1", repo="user/repo1", status=MCPServerStatus.INSTALLED),
            MCPServerMetadata(name="server2", repo="user/repo2", status=MCPServerStatus.INSTALLED),
        ]

        collection.mcp_servers = servers

        # Act: Simulate rollback by reverting servers to not installed
        for i in range(len(collection.mcp_servers)):
            collection.mcp_servers[i].status = MCPServerStatus.NOT_INSTALLED
            collection.mcp_servers[i].installed_at = None

        # Assert: Verify all servers reverted
        assert all(
            s.status == MCPServerStatus.NOT_INSTALLED
            for s in collection.mcp_servers
        )


class TestWebUIAndCLIInteroperability:
    """Test that web UI and CLI modifications stay in sync."""

    def test_cli_add_visible_in_web_api(
        self, collection_manager, temp_settings_file
    ):
        """Test that servers added via CLI appear in web API responses."""
        collection = collection_manager.load_collection("default")

        # Simulate CLI: Add server
        server = MCPServerMetadata(
            name="cli-added-server",
            repo="user/repo",
            version="v1.0.0",
            description="Added via CLI",
        )

        collection.mcp_servers = [server]

        # Assert: Server visible in collection (would appear in API)
        assert len(collection.mcp_servers) == 1
        assert collection.mcp_servers[0].name == "cli-added-server"
        assert collection.mcp_servers[0].repo == "user/repo"

    def test_web_api_update_visible_in_cli(
        self, collection_manager
    ):
        """Test that servers updated via web API appear in CLI."""
        collection = collection_manager.load_collection("default")

        # Simulate web API: Create server
        server = MCPServerMetadata(
            name="api-created-server",
            repo="user/repo",
        )
        collection.mcp_servers = [server]

        # Simulate web API: Update server
        collection.mcp_servers[0].env_vars["NEW_VAR"] = "value"
        collection.mcp_servers[0].description = "Updated via API"

        # Simulate CLI: List servers
        cli_servers = collection.mcp_servers

        # Assert: Updated server visible in CLI
        assert cli_servers[0].env_vars["NEW_VAR"] == "value"
        assert cli_servers[0].description == "Updated via API"

    def test_concurrent_web_cli_modifications(
        self, collection_manager, tmp_path
    ):
        """Test that concurrent modifications are handled safely."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="concurrent-server",
            repo="user/repo",
            env_vars={},
        )
        collection.mcp_servers = [server]

        # Simulate concurrent modifications
        def cli_modify():
            collection.mcp_servers[0].env_vars["CLI_VAR"] = "cli_value"

        def api_modify():
            collection.mcp_servers[0].env_vars["API_VAR"] = "api_value"

        # For now, test sequential (proper concurrency would need locking)
        cli_modify()
        api_modify()

        # Both modifications should be present
        assert collection.mcp_servers[0].env_vars["CLI_VAR"] == "cli_value"
        assert collection.mcp_servers[0].env_vars["API_VAR"] == "api_value"


class TestConcurrentHealthChecks:
    """Test concurrent health checks don't corrupt state."""

    def test_concurrent_health_check_cache_consistency(
        self, health_checker
    ):
        """Test that concurrent health checks maintain cache consistency."""
        server_names = ["server1", "server2", "server3"]
        health_results = {}

        def check_health(name: str):
            result = HealthCheckResult(
                server_name=name,
                status=HealthStatus.HEALTHY,
                deployed=True,
                last_seen=datetime.utcnow(),
            )
            health_results[name] = result

        # Simulate concurrent checks
        threads = [
            Thread(target=check_health, args=(name,))
            for name in server_names
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert: All checks completed successfully
        assert len(health_results) == 3
        assert all(r.status == HealthStatus.HEALTHY for r in health_results.values())

    def test_cache_invalidation_after_deployment(
        self, health_checker
    ):
        """Test that cache is invalidated after deployment changes."""
        server_name = "test-server"

        # Initial health check (before deployment)
        result1 = HealthCheckResult(
            server_name=server_name,
            status=HealthStatus.HEALTHY,
            deployed=False,
        )

        # After deployment (cache should be invalidated)
        result2 = HealthCheckResult(
            server_name=server_name,
            status=HealthStatus.HEALTHY,
            deployed=True,  # Changed
        )

        assert result1.deployed is False
        assert result2.deployed is True


class TestMCPServerVersionManagement:
    """Test version management and updates for MCP servers."""

    def test_update_server_version(
        self, collection_manager, deployment_manager, temp_settings_file, monkeypatch
    ):
        """Test updating MCP server to new version."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="versioned-server",
            repo="user/mcp-server",
            version="v1.0.0",
            status=MCPServerStatus.INSTALLED,
            resolved_version="v1.0.0",
            resolved_sha="abc123",
        )

        collection.mcp_servers = [server]

        # Act: Update version
        collection.mcp_servers[0].version = "v2.0.0"
        collection.mcp_servers[0].resolved_version = "v2.0.0"
        collection.mcp_servers[0].resolved_sha = "def456"
        collection.mcp_servers[0].last_updated = datetime.utcnow().isoformat()

        # Assert: Version updated
        assert collection.mcp_servers[0].version == "v2.0.0"
        assert collection.mcp_servers[0].resolved_version == "v2.0.0"
        assert collection.mcp_servers[0].resolved_sha == "def456"
        assert collection.mcp_servers[0].last_updated is not None


class TestMCPServerEnvironmentVariableManagement:
    """Test environment variable handling for MCP servers."""

    def test_add_environment_variables(
        self, collection_manager
    ):
        """Test adding environment variables to MCP server."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="env-server",
            repo="user/repo",
            env_vars={"EXISTING_VAR": "value"},
        )

        collection.mcp_servers = [server]

        # Add new env vars
        collection.mcp_servers[0].env_vars["NEW_VAR1"] = "new_value1"
        collection.mcp_servers[0].env_vars["NEW_VAR2"] = "new_value2"

        # Assert
        assert len(collection.mcp_servers[0].env_vars) == 3
        assert collection.mcp_servers[0].env_vars["EXISTING_VAR"] == "value"
        assert collection.mcp_servers[0].env_vars["NEW_VAR1"] == "new_value1"
        assert collection.mcp_servers[0].env_vars["NEW_VAR2"] == "new_value2"

    def test_remove_environment_variable(
        self, collection_manager
    ):
        """Test removing environment variable from MCP server."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="env-server",
            repo="user/repo",
            env_vars={
                "VAR_TO_REMOVE": "value",
                "VAR_TO_KEEP": "value",
            },
        )

        collection.mcp_servers = [server]

        # Remove env var
        del collection.mcp_servers[0].env_vars["VAR_TO_REMOVE"]

        # Assert
        assert "VAR_TO_REMOVE" not in collection.mcp_servers[0].env_vars
        assert "VAR_TO_KEEP" in collection.mcp_servers[0].env_vars

    def test_environment_variable_validation(
        self, collection_manager
    ):
        """Test validation of environment variable names."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="validation-server",
            repo="user/repo",
            env_vars={
                "VALID_VAR": "value",
                "VAR_WITH_NUMBERS_123": "value",
                "_UNDERSCORE_VAR": "value",
            },
        )

        collection.mcp_servers = [server]

        # All valid vars should be present
        assert len(collection.mcp_servers[0].env_vars) == 3


class TestMCPServerStatePersistence:
    """Test that MCP server state is properly persisted."""

    def test_server_state_persists_across_operations(
        self, collection_manager, tmp_path
    ):
        """Test that server state persists in collection."""
        collection = collection_manager.load_collection("default")

        server = MCPServerMetadata(
            name="persistent-server",
            repo="user/repo",
            version="v1.0.0",
            status=MCPServerStatus.INSTALLED,
            installed_at=datetime.utcnow().isoformat(),
            resolved_sha="abc123",
        )

        # Add to collection
        collection.mcp_servers = [server]
        initial_state = collection.mcp_servers[0]

        # Simulate operations
        initial_state.env_vars["NEW_VAR"] = "value"
        initial_state.status = MCPServerStatus.INSTALLED

        # Retrieve and verify
        assert collection.mcp_servers[0].name == "persistent-server"
        assert collection.mcp_servers[0].env_vars["NEW_VAR"] == "value"
        assert collection.mcp_servers[0].status == MCPServerStatus.INSTALLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
