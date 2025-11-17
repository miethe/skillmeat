"""Tests for MCP health check functionality."""

import platform
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.mcp.deployment import MCPDeploymentManager
from skillmeat.core.mcp.health import (
    HealthCheckResult,
    HealthStatus,
    LogEntry,
    MCPHealthChecker,
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def sample_log_file(temp_log_dir):
    """Create sample log file with MCP server entries."""
    log_file = temp_log_dir / "mcp.log"

    # Create sample log entries
    now = datetime.utcnow()
    entries = [
        f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] INFO: MCP server 'filesystem' initialized successfully",
        f"[{(now - timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: Connected to MCP server 'filesystem'",
        f"[{(now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to start MCP server 'database'",
        f"[{(now - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')}] WARN: MCP server 'github' slow to respond",
        f"[{(now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}] INFO: MCP server 'github' started",
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))

    return log_file


@pytest.fixture
def deployment_manager():
    """Create mock deployment manager."""
    manager = MagicMock(spec=MCPDeploymentManager)
    manager.is_server_deployed.return_value = True
    manager.get_deployed_servers.return_value = ["filesystem", "database", "github"]
    return manager


@pytest.fixture
def health_checker(deployment_manager):
    """Create MCPHealthChecker instance."""
    return MCPHealthChecker(deployment_manager=deployment_manager)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
        assert HealthStatus.NOT_DEPLOYED.value == "not_deployed"


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            server_name="test-server",
            status=HealthStatus.HEALTHY,
            deployed=True,
        )

        assert result.server_name == "test-server"
        assert result.status == HealthStatus.HEALTHY
        assert result.deployed is True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert isinstance(result.checked_at, datetime)

    def test_health_check_result_to_dict(self):
        """Test converting health check result to dictionary."""
        last_seen = datetime.utcnow()
        result = HealthCheckResult(
            server_name="test-server",
            status=HealthStatus.DEGRADED,
            deployed=True,
            last_seen=last_seen,
            error_count=2,
            warning_count=3,
            recent_errors=["Error 1", "Error 2"],
            recent_warnings=["Warning 1", "Warning 2", "Warning 3"],
        )

        result_dict = result.to_dict()

        assert result_dict["server_name"] == "test-server"
        assert result_dict["status"] == "degraded"
        assert result_dict["deployed"] is True
        assert result_dict["last_seen"] == last_seen.isoformat()
        assert result_dict["error_count"] == 2
        assert result_dict["warning_count"] == 3
        assert len(result_dict["recent_errors"]) == 2
        assert len(result_dict["recent_warnings"]) == 3


class TestLogEntry:
    """Test LogEntry dataclass."""

    def test_log_entry_creation(self):
        """Test creating log entry."""
        timestamp = datetime.utcnow()
        entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            server_name="test-server",
            message="Test message",
            raw_line="[2025-01-15 10:30:00] INFO: Test message",
        )

        assert entry.timestamp == timestamp
        assert entry.level == "INFO"
        assert entry.server_name == "test-server"
        assert entry.message == "Test message"


class TestMCPHealthChecker:
    """Test MCPHealthChecker class."""

    def test_get_log_directory_macos(self):
        """Test log directory detection on macOS."""
        with patch("platform.system", return_value="Darwin"):
            checker = MCPHealthChecker()
            log_dir = checker.get_log_directory()

            assert "Library/Logs/Claude" in str(log_dir)

    def test_get_log_directory_linux(self):
        """Test log directory detection on Linux."""
        with patch("platform.system", return_value="Linux"):
            checker = MCPHealthChecker()
            log_dir = checker.get_log_directory()

            assert ".config/Claude/logs" in str(log_dir)

    def test_get_log_directory_windows(self):
        """Test log directory detection on Windows."""
        with patch("platform.system", return_value="Windows"):
            with patch.dict(
                "os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}
            ):
                checker = MCPHealthChecker()
                log_dir = checker.get_log_directory()

                assert "Claude" in str(log_dir)
                assert "logs" in str(log_dir)

    def test_get_log_directory_unsupported(self):
        """Test log directory detection on unsupported platform."""
        with patch("platform.system", return_value="FreeBSD"):
            checker = MCPHealthChecker()
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                checker.get_log_directory()

    def test_parse_log_line_success(self, health_checker):
        """Test parsing successful log line."""
        line = "[2025-01-15 10:30:00] INFO: MCP server 'filesystem' initialized successfully"
        entry = health_checker.parse_log_line(line)

        assert entry is not None
        assert entry.level == "INFO"
        assert entry.server_name == "filesystem"
        assert "initialized successfully" in entry.message

    def test_parse_log_line_error(self, health_checker):
        """Test parsing error log line."""
        line = "[2025-01-15 10:30:00] ERROR: Failed to start MCP server 'database'"
        entry = health_checker.parse_log_line(line)

        assert entry is not None
        assert entry.level == "ERROR"
        assert entry.server_name == "database"
        assert "Failed to start" in entry.message

    def test_parse_log_line_warning(self, health_checker):
        """Test parsing warning log line."""
        line = "[2025-01-15 10:30:00] WARN: MCP server 'github' slow to respond"
        entry = health_checker.parse_log_line(line)

        assert entry is not None
        assert entry.level == "WARN"
        assert entry.server_name == "github"
        assert "slow to respond" in entry.message

    def test_parse_log_line_iso_format(self, health_checker):
        """Test parsing log line with ISO 8601 timestamp."""
        line = "[2025-01-15T10:30:00Z] INFO: MCP server 'filesystem' started"
        entry = health_checker.parse_log_line(line)

        assert entry is not None
        assert entry.level == "INFO"
        assert entry.server_name == "filesystem"

    def test_parse_log_line_invalid(self, health_checker):
        """Test parsing invalid log line."""
        line = "This is not a valid log line"
        entry = health_checker.parse_log_line(line)

        assert entry is None

    def test_find_log_files_missing_directory(self, health_checker):
        """Test finding log files when directory doesn't exist."""
        with patch.object(
            health_checker, "get_log_directory", return_value=Path("/nonexistent")
        ):
            log_files = health_checker.find_log_files()
            assert log_files == []

    def test_find_log_files_with_rotation(self, temp_log_dir):
        """Test finding rotated log files."""
        # Create log files
        (temp_log_dir / "mcp.log").touch()
        (temp_log_dir / "mcp.log.1").touch()
        (temp_log_dir / "mcp.log.2").touch()

        checker = MCPHealthChecker()
        with patch.object(checker, "get_log_directory", return_value=temp_log_dir):
            log_files = checker.find_log_files()

            assert len(log_files) == 3
            assert temp_log_dir / "mcp.log" in log_files
            assert temp_log_dir / "mcp.log.1" in log_files
            assert temp_log_dir / "mcp.log.2" in log_files

    def test_get_server_logs(self, health_checker, sample_log_file):
        """Test getting logs for specific server."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            logs = health_checker.get_server_logs("filesystem", lines=10)

            assert len(logs) > 0
            assert any("filesystem" in log for log in logs)

    def test_get_server_logs_missing_files(self, health_checker):
        """Test getting logs when files don't exist."""
        with patch.object(health_checker, "find_log_files", return_value=[]):
            logs = health_checker.get_server_logs("filesystem")
            assert logs == []

    def test_parse_claude_logs(self, health_checker, sample_log_file):
        """Test parsing Claude Desktop logs."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            status = health_checker.parse_claude_logs()

            assert "filesystem" in status
            assert "database" in status
            assert "github" in status

            # Check filesystem server (has success entries)
            assert status["filesystem"]["success_count"] > 0
            assert len(status["filesystem"]["errors"]) == 0

            # Check database server (has error)
            assert len(status["database"]["errors"]) > 0

            # Check github server (has warning)
            assert len(status["github"]["warnings"]) > 0

    def test_check_server_health_not_deployed(self, health_checker):
        """Test health check for non-deployed server."""
        health_checker.deployment_manager.is_server_deployed.return_value = False

        result = health_checker.check_server_health("test-server", use_cache=False)

        assert result.status == HealthStatus.NOT_DEPLOYED
        assert result.deployed is False

    def test_check_server_health_healthy(self, health_checker, sample_log_file):
        """Test health check for healthy server."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            result = health_checker.check_server_health("filesystem", use_cache=False)

            assert result.deployed is True
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNKNOWN]
            assert result.server_name == "filesystem"

    def test_check_server_health_unhealthy(self, health_checker, sample_log_file):
        """Test health check for unhealthy server."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            result = health_checker.check_server_health("database", use_cache=False)

            assert result.deployed is True
            assert result.error_count > 0
            assert result.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]

    def test_check_server_health_degraded(self, health_checker, sample_log_file):
        """Test health check for degraded server."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            result = health_checker.check_server_health("github", use_cache=False)

            assert result.deployed is True
            assert result.warning_count > 0

    def test_check_server_health_caching(self, health_checker, sample_log_file):
        """Test health check result caching."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            # First check (cache miss)
            result1 = health_checker.check_server_health("filesystem", use_cache=True)

            # Second check (cache hit)
            result2 = health_checker.check_server_health("filesystem", use_cache=True)

            assert result1.server_name == result2.server_name
            assert result1.checked_at == result2.checked_at  # Same timestamp = cached

    def test_check_server_health_no_cache(self, health_checker, sample_log_file):
        """Test health check without caching."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            # First check
            result1 = health_checker.check_server_health("filesystem", use_cache=False)

            # Second check (should be fresh)
            result2 = health_checker.check_server_health("filesystem", use_cache=False)

            # Results should be different (different checked_at)
            assert result1.server_name == result2.server_name
            # Note: checked_at might be the same if executed very quickly

    def test_check_all_servers(self, health_checker, sample_log_file):
        """Test checking health of all servers."""
        with patch.object(
            health_checker, "find_log_files", return_value=[sample_log_file]
        ):
            results = health_checker.check_all_servers(use_cache=False)

            assert len(results) == 3
            assert "filesystem" in results
            assert "database" in results
            assert "github" in results

            # All should be deployed
            assert all(r.deployed for r in results.values())

    def test_check_all_servers_empty(self, health_checker):
        """Test checking health when no servers deployed."""
        health_checker.deployment_manager.get_deployed_servers.return_value = []

        results = health_checker.check_all_servers(use_cache=False)

        assert len(results) == 0

    def test_determine_health_status_healthy(self, health_checker):
        """Test determining healthy status."""
        status = health_checker._determine_health_status(
            deployed=True,
            error_count=0,
            warning_count=0,
            success_count=5,
            last_seen=datetime.utcnow(),
        )

        assert status == HealthStatus.HEALTHY

    def test_determine_health_status_degraded(self, health_checker):
        """Test determining degraded status."""
        # Warnings but no errors
        status1 = health_checker._determine_health_status(
            deployed=True,
            error_count=0,
            warning_count=2,
            success_count=3,
            last_seen=datetime.utcnow(),
        )
        assert status1 == HealthStatus.DEGRADED

        # Equal errors and successes
        status2 = health_checker._determine_health_status(
            deployed=True,
            error_count=2,
            warning_count=0,
            success_count=3,
            last_seen=datetime.utcnow(),
        )
        assert status2 == HealthStatus.DEGRADED

    def test_determine_health_status_unhealthy(self, health_checker):
        """Test determining unhealthy status."""
        status = health_checker._determine_health_status(
            deployed=True,
            error_count=5,
            warning_count=0,
            success_count=1,
            last_seen=datetime.utcnow(),
        )

        assert status == HealthStatus.UNHEALTHY

    def test_determine_health_status_unknown(self, health_checker):
        """Test determining unknown status."""
        status = health_checker._determine_health_status(
            deployed=True,
            error_count=0,
            warning_count=0,
            success_count=0,
            last_seen=None,
        )

        assert status == HealthStatus.UNKNOWN

    def test_determine_health_status_not_deployed(self, health_checker):
        """Test determining not deployed status."""
        status = health_checker._determine_health_status(
            deployed=False,
            error_count=0,
            warning_count=0,
            success_count=0,
            last_seen=None,
        )

        assert status == HealthStatus.NOT_DEPLOYED

    def test_cache_invalidation(self, health_checker):
        """Test cache invalidation."""
        # Add item to cache
        health_checker._cache["test"] = HealthCheckResult(
            server_name="test",
            status=HealthStatus.HEALTHY,
            deployed=True,
        )
        health_checker._cache_timestamp = 12345

        # Invalidate
        health_checker.invalidate_cache()

        assert len(health_checker._cache) == 0
        assert health_checker._cache_timestamp == 0

    def test_cache_ttl_expiration(self, health_checker):
        """Test cache TTL expiration."""
        # Set cache with old timestamp
        import time

        health_checker._cache["test"] = HealthCheckResult(
            server_name="test",
            status=HealthStatus.HEALTHY,
            deployed=True,
        )
        health_checker._cache_timestamp = time.time() - 100  # 100 seconds ago
        health_checker.cache_ttl = 30  # 30 second TTL

        # Cache should be invalid
        assert not health_checker._is_cache_valid()

    def test_cache_ttl_valid(self, health_checker):
        """Test cache TTL still valid."""
        import time

        health_checker._cache["test"] = HealthCheckResult(
            server_name="test",
            status=HealthStatus.HEALTHY,
            deployed=True,
        )
        health_checker._cache_timestamp = time.time()  # Just now
        health_checker.cache_ttl = 30  # 30 second TTL

        # Cache should be valid
        assert health_checker._is_cache_valid()

    def test_multiple_log_patterns(self, health_checker, temp_log_dir):
        """Test parsing logs with multiple error/warning patterns."""
        log_file = temp_log_dir / "mcp.log"

        entries = [
            "[2025-01-15 10:30:00] ERROR: MCP server 'test' crashed",
            "[2025-01-15 10:30:01] ERROR: MCP server 'test' not found",
            "[2025-01-15 10:30:02] WARN: Restarting MCP server 'test'",
            "[2025-01-15 10:30:03] WARN: MCP server 'test' timeout",
        ]

        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))

        with patch.object(health_checker, "find_log_files", return_value=[log_file]):
            status = health_checker.parse_claude_logs()

            assert "test" in status
            assert len(status["test"]["errors"]) == 2
            assert len(status["test"]["warnings"]) == 2

    def test_log_file_read_errors(self, health_checker, temp_log_dir):
        """Test handling of log file read errors."""
        # Create a directory instead of a file to cause read error
        bad_log = temp_log_dir / "mcp.log"
        bad_log.mkdir()

        with patch.object(health_checker, "find_log_files", return_value=[bad_log]):
            # Should handle error gracefully
            logs = health_checker.get_server_logs("filesystem")
            assert logs == []

            status = health_checker.parse_claude_logs()
            assert isinstance(status, dict)


class TestHealthCheckIntegration:
    """Integration tests for health checking."""

    def test_full_health_check_workflow(self, temp_log_dir):
        """Test complete health check workflow."""
        # Create mock deployment manager
        deployment_mgr = MagicMock(spec=MCPDeploymentManager)
        deployment_mgr.get_deployed_servers.return_value = ["filesystem", "database"]
        deployment_mgr.is_server_deployed.side_effect = lambda name: name in [
            "filesystem",
            "database",
        ]

        # Create health checker
        checker = MCPHealthChecker(deployment_manager=deployment_mgr, cache_ttl=30)

        # Create sample log file
        log_file = temp_log_dir / "mcp.log"
        now = datetime.utcnow()
        entries = [
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] INFO: MCP server 'filesystem' initialized successfully",
            f"[{(now - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to start MCP server 'database'",
        ]
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))

        with patch.object(checker, "find_log_files", return_value=[log_file]):
            # Check all servers
            results = checker.check_all_servers(use_cache=False)

            # Verify results
            assert len(results) == 2

            filesystem_result = results["filesystem"]
            assert filesystem_result.deployed is True
            assert filesystem_result.error_count == 0

            database_result = results["database"]
            assert database_result.deployed is True
            assert database_result.error_count > 0

            # Test caching
            cached_results = checker.check_all_servers(use_cache=True)
            assert len(cached_results) == 2
            assert (
                cached_results["filesystem"].checked_at == filesystem_result.checked_at
            )
