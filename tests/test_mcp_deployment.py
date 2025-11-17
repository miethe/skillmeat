"""Tests for MCP deployment manager."""

import json
import platform
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.mcp.deployment import MCPDeploymentManager, DeploymentResult
from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary settings directory."""
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
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(initial_settings, f, indent=2)
    return settings_file


@pytest.fixture
def deployment_manager():
    """Create MCPDeploymentManager instance."""
    return MCPDeploymentManager()


@pytest.fixture
def sample_server():
    """Create sample MCP server metadata."""
    return MCPServerMetadata(
        name="test-server",
        repo="anthropics/test-mcp",
        version="latest",
        env_vars={"ROOT_PATH": "/tmp"},
        description="Test MCP server",
    )


class TestMCPDeploymentManager:
    """Test MCPDeploymentManager class."""

    def test_get_settings_path(self, deployment_manager):
        """Test platform-specific settings path detection."""
        settings_path = deployment_manager.get_settings_path()

        system = platform.system()
        if system == "Darwin":
            assert "Library/Application Support/Claude" in str(settings_path)
        elif system == "Windows":
            assert "Claude" in str(settings_path)
        elif system == "Linux":
            assert ".config/Claude" in str(settings_path)

        assert settings_path.name == "claude_desktop_config.json"

    def test_read_settings_empty(self, deployment_manager, temp_settings_dir):
        """Test reading settings from non-existent file."""
        non_existent = temp_settings_dir / "nonexistent.json"
        settings = deployment_manager.read_settings(non_existent)
        assert settings == {}

    def test_read_settings_existing(self, deployment_manager, temp_settings_file):
        """Test reading existing settings file."""
        settings = deployment_manager.read_settings(temp_settings_file)
        assert "mcpServers" in settings
        assert "existing-server" in settings["mcpServers"]

    def test_read_settings_invalid_json(self, deployment_manager, temp_settings_dir):
        """Test reading invalid JSON raises ValueError."""
        invalid_file = temp_settings_dir / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            deployment_manager.read_settings(invalid_file)

    def test_write_settings(self, deployment_manager, temp_settings_dir):
        """Test writing settings atomically."""
        settings_file = temp_settings_dir / "test_settings.json"
        test_settings = {
            "mcpServers": {
                "test": {
                    "command": "node",
                    "args": ["test.js"],
                }
            }
        }

        deployment_manager.write_settings(test_settings, settings_file)

        # Verify written content
        assert settings_file.exists()
        with open(settings_file, 'r') as f:
            written = json.load(f)
        assert written == test_settings

    def test_backup_settings(self, deployment_manager, temp_settings_file):
        """Test creating backup of settings file."""
        backup_path = deployment_manager.backup_settings(temp_settings_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert "backup" in backup_path.name
        assert backup_path.suffix == ".json"

        # Verify backup content matches original
        with open(temp_settings_file, 'r') as f:
            original = json.load(f)
        with open(backup_path, 'r') as f:
            backup = json.load(f)
        assert original == backup

    def test_backup_settings_nonexistent(self, deployment_manager, temp_settings_dir):
        """Test backup of non-existent file returns None."""
        non_existent = temp_settings_dir / "nonexistent.json"
        backup_path = deployment_manager.backup_settings(non_existent)
        assert backup_path is None

    def test_restore_settings(self, deployment_manager, temp_settings_file):
        """Test restoring settings from backup."""
        # Create backup
        backup_path = deployment_manager.backup_settings(temp_settings_file)

        # Modify original
        modified_settings = {"mcpServers": {"modified": {"command": "test"}}}
        with open(temp_settings_file, 'w') as f:
            json.dump(modified_settings, f)

        # Restore
        success = deployment_manager.restore_settings(backup_path, temp_settings_file)
        assert success

        # Verify restored content
        with open(temp_settings_file, 'r') as f:
            restored = json.load(f)
        assert "existing-server" in restored["mcpServers"]

    def test_is_server_deployed(self, deployment_manager, temp_settings_file):
        """Test checking if server is deployed."""
        assert deployment_manager.is_server_deployed("existing-server", temp_settings_file)
        assert not deployment_manager.is_server_deployed("nonexistent", temp_settings_file)

    def test_get_deployed_servers(self, deployment_manager, temp_settings_file):
        """Test getting list of deployed servers."""
        servers = deployment_manager.get_deployed_servers(temp_settings_file)
        assert isinstance(servers, list)
        assert "existing-server" in servers

    def test_undeploy_server(self, deployment_manager, temp_settings_file):
        """Test removing server from settings."""
        # Verify server exists
        assert deployment_manager.is_server_deployed("existing-server", temp_settings_file)

        # Undeploy
        success = deployment_manager.undeploy_server("existing-server", temp_settings_file)
        assert success

        # Verify server removed
        assert not deployment_manager.is_server_deployed("existing-server", temp_settings_file)

    def test_undeploy_server_not_found(self, deployment_manager, temp_settings_file):
        """Test undeploying non-existent server returns False."""
        success = deployment_manager.undeploy_server("nonexistent", temp_settings_file)
        assert not success

    def test_parse_package_json(self, deployment_manager, tmp_path):
        """Test parsing package.json."""
        package_json = tmp_path / "package.json"
        package_data = {
            "name": "@test/mcp-server",
            "version": "1.0.0",
            "main": "dist/index.js",
        }
        with open(package_json, 'w') as f:
            json.dump(package_data, f)

        result = deployment_manager._parse_package_json(tmp_path)
        assert result["name"] == "@test/mcp-server"
        assert result["version"] == "1.0.0"

    def test_parse_package_json_not_found(self, deployment_manager, tmp_path):
        """Test parsing missing package.json raises ValueError."""
        with pytest.raises(ValueError, match="package.json not found"):
            deployment_manager._parse_package_json(tmp_path)

    def test_resolve_command_npm_package(self, deployment_manager):
        """Test resolving command for npm package."""
        package_data = {
            "name": "@modelcontextprotocol/server-filesystem",
            "version": "1.0.0",
        }

        command, args = deployment_manager._resolve_command_from_package(package_data)
        assert command == "npx"
        assert args == ["-y", "@modelcontextprotocol/server-filesystem"]

    def test_resolve_command_local_package(self, deployment_manager):
        """Test resolving command for local package."""
        package_data = {
            "name": "local-server",
            "version": "1.0.0",
            "main": "dist/index.js",
        }

        command, args = deployment_manager._resolve_command_from_package(package_data)
        assert command == "node"
        assert args == ["dist/index.js"]

    def test_resolve_command_no_name(self, deployment_manager):
        """Test resolving command without package name raises ValueError."""
        package_data = {"version": "1.0.0"}

        with pytest.raises(ValueError, match="must contain a 'name' field"):
            deployment_manager._resolve_command_from_package(package_data)

    @patch("skillmeat.core.mcp.deployment.GitHubClient")
    def test_deploy_server_dry_run(
        self, mock_github_client, deployment_manager, sample_server, temp_settings_file
    ):
        """Test dry run deployment."""
        # Mock GitHub client
        mock_client_instance = MagicMock()
        mock_client_instance.resolve_version.return_value = ("abc123", "v1.0.0")
        mock_client_instance.clone_repo.return_value = None
        mock_github_client.return_value = mock_client_instance
        deployment_manager.github_client = mock_client_instance

        # Create mock repo with package.json
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            package_json = temp_path / "package.json"
            package_data = {
                "name": "@test/mcp-server",
                "version": "1.0.0",
            }
            with open(package_json, 'w') as f:
                json.dump(package_data, f)

            # Mock tempfile.mkdtemp to return our temp dir
            with patch("tempfile.mkdtemp", return_value=str(temp_path)):
                result = deployment_manager.deploy_server(
                    server=sample_server,
                    dry_run=True,
                    backup=False,
                )

        assert result.success
        assert result.server_name == "test-server"
        assert result.command == "npx"
        assert result.args == ["-y", "@test/mcp-server"]

    def test_scaffold_env_vars(self, deployment_manager, sample_server, tmp_path):
        """Test environment variable scaffolding."""
        env_file = deployment_manager._scaffold_env_vars(sample_server, tmp_path)

        assert env_file is not None
        assert env_file.exists()
        assert env_file.name == ".env"

        # Read and verify content
        with open(env_file, 'r') as f:
            content = f.read()

        assert "MCP_TEST_SERVER_ROOT_PATH=/tmp" in content
        assert "Environment variables for SkillMeat MCP servers" in content

    def test_scaffold_env_vars_no_env(self, deployment_manager, tmp_path):
        """Test scaffolding with no environment variables."""
        server = MCPServerMetadata(
            name="test",
            repo="test/repo",
            version="latest",
        )

        env_file = deployment_manager._scaffold_env_vars(server, tmp_path)
        assert env_file is None

    def test_scaffold_env_vars_updates_existing(self, deployment_manager, sample_server, tmp_path):
        """Test updating existing .env file."""
        # Create existing .env
        env_file = tmp_path / ".env"
        with open(env_file, 'w') as f:
            f.write("EXISTING_VAR=value\n")

        # Scaffold new vars
        result = deployment_manager._scaffold_env_vars(sample_server, tmp_path)

        # Read and verify both old and new vars present
        with open(result, 'r') as f:
            content = f.read()

        assert "EXISTING_VAR=value" in content
        assert "MCP_TEST_SERVER_ROOT_PATH=/tmp" in content

    def test_idempotent_deployment(self, deployment_manager, temp_settings_file):
        """Test that deploying same server twice updates instead of duplicating."""
        # Add server to settings
        settings = deployment_manager.read_settings(temp_settings_file)
        settings["mcpServers"]["test-server"] = {
            "command": "old-command",
            "args": ["old-arg"],
        }
        deployment_manager.write_settings(settings, temp_settings_file)

        # Update server config
        settings = deployment_manager.read_settings(temp_settings_file)
        settings["mcpServers"]["test-server"] = {
            "command": "new-command",
            "args": ["new-arg"],
        }
        deployment_manager.write_settings(settings, temp_settings_file)

        # Verify only one entry and it's updated
        updated_settings = deployment_manager.read_settings(temp_settings_file)
        assert len(updated_settings["mcpServers"]) == 2  # existing + test
        assert updated_settings["mcpServers"]["test-server"]["command"] == "new-command"


class TestDeploymentResult:
    """Test DeploymentResult dataclass."""

    def test_deployment_result_success(self):
        """Test successful deployment result."""
        result = DeploymentResult(
            server_name="test",
            success=True,
            settings_path=Path("/test/settings.json"),
            command="npx",
            args=["-y", "@test/server"],
        )

        assert result.success
        assert result.server_name == "test"
        assert result.command == "npx"
        assert result.error_message is None

    def test_deployment_result_failure(self):
        """Test failed deployment result."""
        result = DeploymentResult(
            server_name="test",
            success=False,
            settings_path=Path("/test/settings.json"),
            error_message="Deployment failed",
        )

        assert not result.success
        assert result.error_message == "Deployment failed"
        assert result.command is None


class TestPlatformCompatibility:
    """Test platform-specific behavior."""

    @patch("platform.system", return_value="Darwin")
    def test_settings_path_macos(self, mock_system):
        """Test settings path on macOS."""
        manager = MCPDeploymentManager()
        path = manager.get_settings_path()
        assert "Library/Application Support/Claude" in str(path)

    @patch("platform.system", return_value="Linux")
    def test_settings_path_linux(self, mock_system):
        """Test settings path on Linux."""
        manager = MCPDeploymentManager()
        path = manager.get_settings_path()
        assert ".config/Claude" in str(path)

    @patch("platform.system", return_value="Windows")
    @patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"})
    def test_settings_path_windows(self, mock_system):
        """Test settings path on Windows."""
        manager = MCPDeploymentManager()
        path = manager.get_settings_path()
        assert "Claude" in str(path)

    @patch("platform.system", return_value="Unknown")
    def test_settings_path_unsupported(self, mock_system):
        """Test unsupported platform raises RuntimeError."""
        manager = MCPDeploymentManager()
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            manager.get_settings_path()
