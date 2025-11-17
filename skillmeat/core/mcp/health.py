"""MCP Server Health Checking for SkillMeat.

This module provides health monitoring for deployed MCP servers by analyzing
Claude Desktop logs and settings.json configuration.
"""

import json
import platform
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console

from skillmeat.core.mcp.deployment import MCPDeploymentManager

console = Console()


class HealthStatus(str, Enum):
    """Health status of an MCP server."""

    HEALTHY = "healthy"  # Server configured and running
    DEGRADED = "degraded"  # Server running but with warnings
    UNHEALTHY = "unhealthy"  # Server configured but failing
    UNKNOWN = "unknown"  # Cannot determine status
    NOT_DEPLOYED = "not_deployed"  # Not in settings.json


@dataclass
class HealthCheckResult:
    """Result of MCP server health check.

    Attributes:
        server_name: Name of the MCP server
        status: Current health status
        deployed: Whether server is in settings.json
        last_seen: Last time server was seen in logs
        error_count: Number of recent errors
        warning_count: Number of recent warnings
        recent_errors: List of recent error messages
        recent_warnings: List of recent warning messages
        checked_at: Timestamp of health check
    """

    server_name: str
    status: HealthStatus
    deployed: bool
    last_seen: Optional[datetime] = None
    error_count: int = 0
    warning_count: int = 0
    recent_errors: List[str] = field(default_factory=list)
    recent_warnings: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "server_name": self.server_name,
            "status": self.status.value,
            "deployed": self.deployed,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "recent_errors": self.recent_errors,
            "recent_warnings": self.recent_warnings,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class LogEntry:
    """Parsed log entry from Claude Desktop logs.

    Attributes:
        timestamp: Timestamp of log entry
        level: Log level (INFO, WARN, ERROR, etc.)
        server_name: Name of MCP server (if applicable)
        message: Log message content
        raw_line: Raw log line
    """

    timestamp: Optional[datetime]
    level: str
    server_name: Optional[str]
    message: str
    raw_line: str


class MCPHealthChecker:
    """Health checker for MCP servers.

    This class provides health monitoring by:
    1. Validating settings.json configuration
    2. Parsing Claude Desktop logs for server status
    3. Detecting error and warning patterns
    4. Caching results to minimize I/O

    Attributes:
        deployment_manager: MCPDeploymentManager instance
        cache_ttl: Cache time-to-live in seconds (default: 30)
        _cache: Internal cache for log parsing results
        _cache_timestamp: Timestamp of last cache update
    """

    # Log patterns for different event types
    SUCCESS_PATTERNS = [
        r"MCP server ['\"](.+?)['\"] initialized successfully",
        r"Connected to MCP server ['\"](.+?)['\"]",
        r"MCP server ['\"](.+?)['\"] started",
        r"Successfully connected to ['\"](.+?)['\"]",
    ]

    ERROR_PATTERNS = [
        r"Failed to start MCP server ['\"](.+?)['\"]",
        r"MCP server ['\"](.+?)['\"] crashed",
        r"Error in MCP server ['\"](.+?)['\"]",
        r"MCP server ['\"](.+?)['\"] not found",
        r"Failed to connect to ['\"](.+?)['\"]",
        r"MCP server ['\"](.+?)['\"] exited with code",
    ]

    WARNING_PATTERNS = [
        r"MCP server ['\"](.+?)['\"] slow to respond",
        r"Restarting MCP server ['\"](.+?)['\"]",
        r"MCP server ['\"](.+?)['\"] timeout",
        r"Retrying connection to ['\"](.+?)['\"]",
    ]

    def __init__(
        self,
        deployment_manager: Optional[MCPDeploymentManager] = None,
        cache_ttl: int = 30,
    ):
        """Initialize health checker.

        Args:
            deployment_manager: Optional MCPDeploymentManager instance
            cache_ttl: Cache time-to-live in seconds
        """
        self.deployment_manager = deployment_manager or MCPDeploymentManager()
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, HealthCheckResult] = {}
        self._cache_timestamp: float = 0

    def get_log_directory(self) -> Path:
        """Get platform-specific Claude Desktop log directory.

        Returns:
            Path to log directory

        Raises:
            RuntimeError: If platform is not supported
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Logs" / "Claude"
        elif system == "Windows":
            import os

            appdata = os.environ.get("APPDATA")
            if not appdata:
                raise RuntimeError("APPDATA environment variable not found")
            return Path(appdata) / "Claude" / "logs"
        elif system == "Linux":
            return Path.home() / ".config" / "Claude" / "logs"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    def find_log_files(self) -> List[Path]:
        """Find Claude Desktop log files.

        Looks for log files in order:
        - mcp.log (current log file)
        - mcp.log.1, mcp.log.2, etc. (rotated logs)

        Returns:
            List of log file paths (most recent first)
        """
        try:
            log_dir = self.get_log_directory()
            if not log_dir.exists():
                return []

            # Find all MCP-related log files
            log_files = []

            # Check for main log file
            main_log = log_dir / "mcp.log"
            if main_log.exists():
                log_files.append(main_log)

            # Check for rotated logs
            for i in range(1, 10):  # Check up to mcp.log.9
                rotated_log = log_dir / f"mcp.log.{i}"
                if rotated_log.exists():
                    log_files.append(rotated_log)
                else:
                    break

            return log_files

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to find log files: {e}[/yellow]")
            return []

    def parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line.

        Expected format examples:
        - [2025-01-15 10:30:45] INFO: MCP server 'filesystem' initialized successfully
        - [2025-01-15T10:30:45Z] ERROR: Failed to start MCP server 'database'

        Args:
            line: Raw log line

        Returns:
            LogEntry if successfully parsed, None otherwise
        """
        # Try to parse timestamp and level
        # Format: [YYYY-MM-DD HH:MM:SS] LEVEL: message
        # or: [YYYY-MM-DDTHH:MM:SSZ] LEVEL: message
        timestamp_pattern = (
            r"\[(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[Z]?)\]\s*([A-Z]+):\s*(.+)"
        )
        match = re.match(timestamp_pattern, line)

        if not match:
            # Try simpler format without level
            simple_pattern = r"\[(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[Z]?)\]\s*(.+)"
            match = re.match(simple_pattern, line)
            if match:
                timestamp_str, message = match.groups()
                level = "INFO"
            else:
                # Cannot parse, return None
                return None
        else:
            timestamp_str, level, message = match.groups()

        # Parse timestamp
        try:
            # Remove 'Z' suffix if present and replace T with space
            timestamp_str = timestamp_str.replace("Z", "").replace("T", " ")
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = None

        # Extract server name if present
        server_name = None
        for pattern in (
            self.SUCCESS_PATTERNS + self.ERROR_PATTERNS + self.WARNING_PATTERNS
        ):
            server_match = re.search(pattern, message)
            if server_match:
                server_name = server_match.group(1)
                break

        return LogEntry(
            timestamp=timestamp,
            level=level,
            server_name=server_name,
            message=message,
            raw_line=line,
        )

    def get_server_logs(self, server_name: str, lines: int = 50) -> List[str]:
        """Get recent log entries for a specific server.

        Args:
            server_name: Name of MCP server
            lines: Maximum number of log lines to retrieve

        Returns:
            List of log lines (most recent first)
        """
        log_files = self.find_log_files()
        if not log_files:
            return []

        server_logs = []

        # Read logs from most recent first
        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    file_lines = f.readlines()

                # Search in reverse order (most recent first)
                for line in reversed(file_lines):
                    entry = self.parse_log_line(line.strip())
                    if entry and entry.server_name == server_name:
                        server_logs.append(line.strip())

                        if len(server_logs) >= lines:
                            return server_logs

            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to read {log_file}: {e}[/yellow]"
                )
                continue

        return server_logs

    def parse_claude_logs(self) -> Dict[str, Dict]:
        """Parse Claude Desktop logs for all MCP server status.

        Returns:
            Dictionary mapping server names to status information:
            {
                "server_name": {
                    "last_seen": datetime,
                    "errors": [error_messages],
                    "warnings": [warning_messages],
                    "success_count": int,
                }
            }
        """
        log_files = self.find_log_files()
        if not log_files:
            return {}

        server_status = {}

        # Read logs (most recent first)
        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                # Process in reverse order (most recent first)
                for line in reversed(lines):
                    entry = self.parse_log_line(line.strip())
                    if not entry or not entry.server_name:
                        continue

                    server_name = entry.server_name

                    # Initialize server status if not present
                    if server_name not in server_status:
                        server_status[server_name] = {
                            "last_seen": entry.timestamp,
                            "errors": [],
                            "warnings": [],
                            "success_count": 0,
                        }

                    # Update last_seen to most recent timestamp
                    if entry.timestamp:
                        if not server_status[server_name]["last_seen"]:
                            server_status[server_name]["last_seen"] = entry.timestamp
                        else:
                            server_status[server_name]["last_seen"] = max(
                                server_status[server_name]["last_seen"],
                                entry.timestamp,
                            )

                    # Check for error patterns
                    is_error = False
                    for pattern in self.ERROR_PATTERNS:
                        if re.search(pattern, entry.message):
                            # Only store first 10 errors
                            if len(server_status[server_name]["errors"]) < 10:
                                server_status[server_name]["errors"].append(
                                    entry.message
                                )
                            is_error = True
                            break

                    # Check for warning patterns (if not error)
                    if not is_error:
                        for pattern in self.WARNING_PATTERNS:
                            if re.search(pattern, entry.message):
                                # Only store first 10 warnings
                                if len(server_status[server_name]["warnings"]) < 10:
                                    server_status[server_name]["warnings"].append(
                                        entry.message
                                    )
                                break

                    # Check for success patterns
                    for pattern in self.SUCCESS_PATTERNS:
                        if re.search(pattern, entry.message):
                            server_status[server_name]["success_count"] += 1
                            break

            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to parse {log_file}: {e}[/yellow]"
                )
                continue

        return server_status

    def check_server_health(
        self, server_name: str, use_cache: bool = True
    ) -> HealthCheckResult:
        """Check health of a single MCP server.

        Args:
            server_name: Name of MCP server to check
            use_cache: Whether to use cached results (default: True)

        Returns:
            HealthCheckResult with server health information
        """
        # Check cache if enabled
        if use_cache and self._is_cache_valid():
            if server_name in self._cache:
                return self._cache[server_name]

        # Check if server is deployed
        deployed = self.deployment_manager.is_server_deployed(server_name)

        if not deployed:
            result = HealthCheckResult(
                server_name=server_name,
                status=HealthStatus.NOT_DEPLOYED,
                deployed=False,
            )
            self._cache[server_name] = result
            self._cache_timestamp = time.time()
            return result

        # Parse logs to get server status
        log_status = self.parse_claude_logs()

        # Get status for this server
        server_log_info = log_status.get(server_name, {})

        # Build health check result
        last_seen = server_log_info.get("last_seen")
        errors = server_log_info.get("errors", [])
        warnings = server_log_info.get("warnings", [])
        success_count = server_log_info.get("success_count", 0)

        # Determine health status
        status = self._determine_health_status(
            deployed=True,
            error_count=len(errors),
            warning_count=len(warnings),
            success_count=success_count,
            last_seen=last_seen,
        )

        result = HealthCheckResult(
            server_name=server_name,
            status=status,
            deployed=True,
            last_seen=last_seen,
            error_count=len(errors),
            warning_count=len(warnings),
            recent_errors=errors[:5],  # Return only 5 most recent
            recent_warnings=warnings[:5],
        )

        # Update cache
        self._cache[server_name] = result
        self._cache_timestamp = time.time()

        return result

    def check_all_servers(self, use_cache: bool = True) -> Dict[str, HealthCheckResult]:
        """Check health of all deployed MCP servers.

        Args:
            use_cache: Whether to use cached results (default: True)

        Returns:
            Dictionary mapping server names to HealthCheckResult
        """
        # Get all deployed servers
        deployed_servers = self.deployment_manager.get_deployed_servers()

        results = {}

        for server_name in deployed_servers:
            results[server_name] = self.check_server_health(server_name, use_cache)

        return results

    def _determine_health_status(
        self,
        deployed: bool,
        error_count: int,
        warning_count: int,
        success_count: int,
        last_seen: Optional[datetime],
    ) -> HealthStatus:
        """Determine overall health status based on metrics.

        Args:
            deployed: Whether server is deployed
            error_count: Number of recent errors
            warning_count: Number of recent warnings
            success_count: Number of successful events
            last_seen: Last time server was seen in logs

        Returns:
            HealthStatus enum value
        """
        if not deployed:
            return HealthStatus.NOT_DEPLOYED

        # If we have no log information at all
        if last_seen is None and success_count == 0:
            return HealthStatus.UNKNOWN

        # If we have recent errors
        if error_count > 0:
            # If errors outnumber successes, unhealthy
            if error_count > success_count:
                return HealthStatus.UNHEALTHY
            # If we have both errors and successes, degraded
            else:
                return HealthStatus.DEGRADED

        # If we have warnings but no errors
        if warning_count > 0:
            return HealthStatus.DEGRADED

        # If we have successes and no errors/warnings
        if success_count > 0:
            return HealthStatus.HEALTHY

        # Default to unknown if we can't determine
        return HealthStatus.UNKNOWN

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL.

        Returns:
            True if cache is valid, False otherwise
        """
        current_time = time.time()
        return (current_time - self._cache_timestamp) < self.cache_ttl

    def invalidate_cache(self) -> None:
        """Invalidate the cache, forcing fresh reads on next check."""
        self._cache.clear()
        self._cache_timestamp = 0
