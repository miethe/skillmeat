"""Tests for web process manager."""

import signal
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from skillmeat.web.manager import ServerConfig, WebManager


class TestServerConfig:
    """Tests for ServerConfig dataclass."""

    def test_basic_config(self):
        """Test basic server configuration."""
        config = ServerConfig(
            name="Test",
            command=["test", "command"],
            startup_message="Starting test...",
            ready_message="Test ready",
            log_prefix="[TEST]",
            log_color="blue",
        )

        assert config.name == "Test"
        assert config.command == ["test", "command"]
        assert config.cwd is None
        assert config.env is None
        assert config.health_url is None
        assert config.startup_message == "Starting test..."
        assert config.ready_message == "Test ready"
        assert config.log_prefix == "[TEST]"
        assert config.log_color == "blue"

    def test_config_with_optional_fields(self):
        """Test config with optional fields."""
        config = ServerConfig(
            name="Test",
            command=["test"],
            cwd=Path("/tmp"),
            env={"KEY": "value"},
            health_url="http://localhost:8000/health",
        )

        assert config.cwd == Path("/tmp")
        assert config.env == {"KEY": "value"}
        assert config.health_url == "http://localhost:8000/health"


class TestWebManager:
    """Tests for WebManager class."""

    def test_init_default(self):
        """Test WebManager initialization with defaults."""
        manager = WebManager()

        assert manager.api_only is False
        assert manager.web_only is False
        assert manager.api_port == 8000
        assert manager.web_port == 3000
        assert manager.api_host == "127.0.0.1"
        assert isinstance(manager.processes, dict)
        assert isinstance(manager.log_threads, dict)

    def test_init_custom_ports(self):
        """Test WebManager with custom ports."""
        manager = WebManager(api_port=8080, web_port=3001)

        assert manager.api_port == 8080
        assert manager.web_port == 3001

    def test_init_api_only(self):
        """Test WebManager in API-only mode."""
        manager = WebManager(api_only=True)

        assert manager.api_only is True
        assert manager.web_only is False

    def test_init_web_only(self):
        """Test WebManager in web-only mode."""
        manager = WebManager(web_only=True)

        assert manager.api_only is False
        assert manager.web_only is True

    def test_get_api_config(self):
        """Test API server configuration."""
        manager = WebManager(api_port=8080)
        config = manager._get_api_config(reload=True)

        assert config.name == "API"
        assert "uvicorn" in config.command
        assert "--port" in config.command
        assert "8080" in config.command
        assert "--reload" in config.command
        assert config.health_url == "http://127.0.0.1:8080/health"
        assert config.log_prefix == "[API]"
        assert config.log_color == "blue"

    def test_get_api_config_no_reload(self):
        """Test API config without reload."""
        manager = WebManager()
        config = manager._get_api_config(reload=False)

        assert "--reload" not in config.command

    def test_get_web_config_dev(self):
        """Test Next.js dev configuration."""
        manager = WebManager(web_port=3001)
        config = manager._get_web_config(production=False)

        assert config.name == "Web"
        assert config.command == ["pnpm", "dev"]
        assert config.env["PORT"] == "3001"
        assert config.health_url == "http://localhost:3001"
        assert config.log_prefix == "[Web]"
        assert config.log_color == "green"
        assert config.cwd == manager.web_dir

    def test_get_web_config_production(self):
        """Test Next.js production configuration."""
        manager = WebManager()
        config = manager._get_web_config(production=True)

        assert config.command == ["pnpm", "start"]
        assert "production" in config.startup_message

    @patch("subprocess.Popen")
    def test_start_process(self, mock_popen):
        """Test starting a process."""
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.stdout = MagicMock()
        mock_popen.return_value = mock_process

        manager = WebManager()
        config = ServerConfig(
            name="Test",
            command=["test", "command"],
            log_prefix="[TEST]",
            log_color="white",
        )

        with patch.object(manager, "_forward_logs"):
            process = manager._start_process(config)

        assert process == mock_process
        assert "Test" in manager.processes
        assert "Test" in manager.log_threads

        # Verify subprocess.Popen was called correctly
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs["stdout"] == subprocess.PIPE
        assert call_kwargs["stderr"] == subprocess.STDOUT
        assert call_kwargs["text"] is True

    @patch("subprocess.Popen")
    def test_start_process_failure(self, mock_popen):
        """Test process start failure."""
        mock_popen.side_effect = OSError("Failed to start")

        manager = WebManager()
        config = ServerConfig(
            name="Test",
            command=["test"],
            log_prefix="[TEST]",
            log_color="white",
        )

        with pytest.raises(RuntimeError, match="Failed to start Test server"):
            manager._start_process(config)

    @patch("requests.get")
    def test_wait_for_health_success(self, mock_get):
        """Test health check success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        manager = WebManager()
        config = ServerConfig(
            name="Test",
            command=["test"],
            health_url="http://localhost:8000/health",
        )

        result = manager._wait_for_health(config, timeout=5)

        assert result is True
        assert mock_get.called

    @patch("requests.get")
    def test_wait_for_health_timeout(self, mock_get):
        """Test health check timeout."""
        mock_get.side_effect = Exception("Connection refused")

        manager = WebManager()
        config = ServerConfig(
            name="Test",
            command=["test"],
            health_url="http://localhost:8000/health",
        )

        result = manager._wait_for_health(config, timeout=1)

        assert result is False

    def test_wait_for_health_no_url(self):
        """Test health check with no URL (should just wait)."""
        manager = WebManager()
        config = ServerConfig(
            name="Test",
            command=["test"],
        )

        # Should return True quickly
        start = time.time()
        result = manager._wait_for_health(config, timeout=10)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 5  # Should be ~2 seconds

    def test_stop_process(self):
        """Test stopping a process."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None

        manager = WebManager()
        manager.processes["Test"] = mock_process
        manager.log_threads["Test"] = Mock()

        manager._stop_process("Test", timeout=5)

        # Verify terminate was called
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()

        # Verify cleanup
        assert "Test" not in manager.processes
        assert "Test" not in manager.log_threads

    def test_stop_process_force_kill(self):
        """Test force killing a process."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=5),
            None,
        ]

        manager = WebManager()
        manager.processes["Test"] = mock_process

        manager._stop_process("Test", timeout=1)

        # Verify terminate then kill was called
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_stop_all(self):
        """Test stopping all processes."""
        manager = WebManager()
        manager.processes = {
            "API": Mock(),
            "Web": Mock(),
        }

        with patch.object(manager, "_stop_process") as mock_stop:
            manager.stop_all()

        # Verify all processes were stopped
        assert mock_stop.call_count == 2
        mock_stop.assert_any_call("API")
        mock_stop.assert_any_call("Web")

    @patch("skillmeat.web.manager.check_prerequisites")
    @patch.object(WebManager, "start_dev")
    def test_build_web(self, mock_start, mock_prereqs):
        """Test building Next.js."""
        manager = WebManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            exit_code = manager.build_web()

        assert exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["pnpm", "build"]
        assert call_args[1]["cwd"] == manager.web_dir

    def test_build_web_failure(self):
        """Test build failure."""
        manager = WebManager()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "pnpm build")

            exit_code = manager.build_web()

        assert exit_code == 1


class TestCheckPrerequisites:
    """Tests for check_prerequisites function."""

    @patch("skillmeat.web.manager.RequirementsChecker")
    def test_prerequisites_met(self, mock_checker_class):
        """Test when all prerequisites are met."""
        from rich.console import Console

        from skillmeat.web.manager import check_prerequisites

        mock_checker = Mock()
        mock_checker.check_all.return_value = (True, [])
        mock_checker_class.return_value = mock_checker

        console = Console()
        result = check_prerequisites(console)

        assert result is True

    @patch("skillmeat.web.manager.RequirementsChecker")
    def test_prerequisites_not_met(self, mock_checker_class):
        """Test when prerequisites are not met."""
        from rich.console import Console

        from skillmeat.web.manager import check_prerequisites

        mock_checker = Mock()
        mock_checker.check_all.return_value = (False, ["Error 1", "Error 2"])
        mock_checker_class.return_value = mock_checker

        console = Console()
        result = check_prerequisites(console)

        assert result is False
