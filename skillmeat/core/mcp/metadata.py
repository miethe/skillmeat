"""MCP server metadata models for SkillMeat.

This module defines data models for managing Model Context Protocol (MCP) servers
within SkillMeat collections, including metadata, validation, and serialization.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class MCPServerStatus(str, Enum):
    """Status of an MCP server installation."""

    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"
    UPDATING = "updating"


@dataclass
class MCPServerMetadata:
    """Metadata for an MCP server in a SkillMeat collection.

    Represents MCP server configuration including repository source, version,
    environment variables, and installation status.

    Attributes:
        name: Unique identifier for the MCP server (must be valid identifier)
        repo: GitHub repository URL (e.g., "anthropics/mcp-filesystem")
        version: Version specification (e.g., "latest", "v1.0.0", "abc123")
        env_vars: Environment variables required by the server
        description: Human-readable description of the server
        installed_at: ISO 8601 timestamp of installation (None if not installed)
        status: Current installation status
        resolved_sha: Resolved git SHA for the version (None if not resolved)
        resolved_version: Resolved version tag (None if not resolved)
        last_updated: ISO 8601 timestamp of last update (None if never updated)

    Example:
        >>> metadata = MCPServerMetadata(
        ...     name="filesystem",
        ...     repo="anthropics/mcp-filesystem",
        ...     version="latest",
        ...     env_vars={"ROOT_PATH": "/home/user"},
        ...     description="File system access MCP server"
        ... )
    """

    name: str
    repo: str
    version: str = "latest"
    env_vars: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None
    installed_at: Optional[str] = None  # ISO 8601 timestamp
    status: MCPServerStatus = MCPServerStatus.NOT_INSTALLED
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None
    last_updated: Optional[str] = None  # ISO 8601 timestamp

    def __post_init__(self):
        """Validate MCP server metadata.

        Raises:
            ValueError: If name is invalid or repo URL is malformed
        """
        # Validate name is a valid identifier
        if not self.name:
            raise ValueError("MCP server name cannot be empty")

        # Security: Prevent path traversal and hidden names (check before regex)
        if "/" in self.name or "\\" in self.name:
            raise ValueError(
                f"Invalid MCP server name '{self.name}': "
                "name cannot contain path separators (/ or \\)"
            )

        if ".." in self.name:
            raise ValueError(
                f"Invalid MCP server name '{self.name}': "
                "name cannot contain parent directory references (..)"
            )

        if self.name.startswith("."):
            raise ValueError(
                f"Invalid MCP server name '{self.name}': "
                "name cannot start with '.'"
            )

        # Name must be a valid identifier (alphanumeric, dash, underscore)
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
            raise ValueError(
                f"Invalid MCP server name '{self.name}': "
                "name must contain only alphanumeric characters, dashes, and underscores"
            )

        # Validate repo is a valid GitHub URL or user/repo format
        self._validate_repo_url()

        # Ensure status is MCPServerStatus enum
        if isinstance(self.status, str):
            self.status = MCPServerStatus(self.status)

        # Validate env_vars is a dictionary
        if not isinstance(self.env_vars, dict):
            raise ValueError(
                f"env_vars must be a dictionary, got {type(self.env_vars).__name__}"
            )

        # Validate all env_var keys and values are strings
        for key, value in self.env_vars.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"Environment variable key must be string, got {type(key).__name__}"
                )
            if not isinstance(value, str):
                raise ValueError(
                    f"Environment variable value for '{key}' must be string, "
                    f"got {type(value).__name__}"
                )

    def _validate_repo_url(self):
        """Validate repository URL format.

        Accepts:
        - Full GitHub URL: https://github.com/user/repo
        - GitHub URL without scheme: github.com/user/repo
        - Short format: user/repo

        Raises:
            ValueError: If repo format is invalid
        """
        if not self.repo:
            raise ValueError("Repository URL cannot be empty")

        # Try to parse as URL
        if self.repo.startswith("http://") or self.repo.startswith("https://"):
            parsed = urlparse(self.repo)
            if not parsed.netloc or not parsed.path:
                raise ValueError(
                    f"Invalid repository URL '{self.repo}': malformed URL"
                )
            # Validate it's a GitHub URL
            if "github.com" not in parsed.netloc.lower():
                raise ValueError(
                    f"Invalid repository URL '{self.repo}': "
                    "only GitHub repositories are supported"
                )
        elif self.repo.startswith("github.com/"):
            # github.com/user/repo format
            parts = self.repo.split("/")
            if len(parts) < 3:
                raise ValueError(
                    f"Invalid repository URL '{self.repo}': "
                    "expected format 'github.com/user/repo'"
                )
        else:
            # Short format: user/repo or user/repo/subpath
            parts = self.repo.split("/")
            if len(parts) < 2:
                raise ValueError(
                    f"Invalid repository URL '{self.repo}': "
                    "expected format 'user/repo' or 'https://github.com/user/repo'"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization.

        Returns:
            Dictionary representation suitable for TOML serialization
        """
        result = {
            "name": self.name,
            "repo": self.repo,
            "version": self.version,
        }

        # Add env_vars if present
        if self.env_vars:
            result["env_vars"] = self.env_vars

        # Add optional fields
        if self.description is not None:
            result["description"] = self.description
        if self.installed_at is not None:
            result["installed_at"] = self.installed_at
        if self.status != MCPServerStatus.NOT_INSTALLED:
            result["status"] = self.status.value
        if self.resolved_sha is not None:
            result["resolved_sha"] = self.resolved_sha
        if self.resolved_version is not None:
            result["resolved_version"] = self.resolved_version
        if self.last_updated is not None:
            result["last_updated"] = self.last_updated

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerMetadata":
        """Create from dictionary (TOML deserialization).

        Args:
            data: Dictionary from TOML parsing

        Returns:
            MCPServerMetadata instance

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if "name" not in data:
            raise ValueError("Missing required field 'name' in MCP server metadata")
        if "repo" not in data:
            raise ValueError(
                f"Missing required field 'repo' in MCP server '{data.get('name')}'"
            )

        # Parse status if present
        status = MCPServerStatus.NOT_INSTALLED
        if "status" in data:
            status = MCPServerStatus(data["status"])

        return cls(
            name=data["name"],
            repo=data["repo"],
            version=data.get("version", "latest"),
            env_vars=data.get("env_vars", {}),
            description=data.get("description"),
            installed_at=data.get("installed_at"),
            status=status,
            resolved_sha=data.get("resolved_sha"),
            resolved_version=data.get("resolved_version"),
            last_updated=data.get("last_updated"),
        )

    def composite_key(self) -> str:
        """Return unique composite key for the MCP server.

        Returns:
            Composite key (name, since MCP servers have unique names)
        """
        return self.name

    def mark_installed(self) -> None:
        """Mark MCP server as installed with current timestamp."""
        self.status = MCPServerStatus.INSTALLED
        self.installed_at = datetime.utcnow().isoformat()

    def mark_error(self) -> None:
        """Mark MCP server installation as errored."""
        self.status = MCPServerStatus.ERROR

    def mark_updating(self) -> None:
        """Mark MCP server as currently updating."""
        self.status = MCPServerStatus.UPDATING

    def update_version(self, sha: str, version: Optional[str] = None) -> None:
        """Update resolved version information.

        Args:
            sha: Git SHA of the resolved version
            version: Version tag (optional)
        """
        self.resolved_sha = sha
        self.resolved_version = version
        self.last_updated = datetime.utcnow().isoformat()
