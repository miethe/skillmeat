"""MCP server API schemas.

Provides Pydantic models for MCP server management API endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.mcp.metadata import MCPServerStatus


class MCPServerBase(BaseModel):
    """Base MCP server schema with common fields."""

    name: str = Field(
        description="Unique server name (alphanumeric, dash, underscore)",
        examples=["filesystem"],
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    repo: str = Field(
        description="GitHub repository (user/repo or full URL)",
        examples=["anthropics/mcp-filesystem"],
    )
    version: str = Field(
        default="latest",
        description="Version spec (latest, tag, or SHA)",
        examples=["latest", "v1.0.0", "abc123"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description",
        examples=["File system access MCP server"],
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables as key-value pairs",
        examples=[{"ROOT_PATH": "/home/user/documents"}],
    )


class MCPServerCreateRequest(MCPServerBase):
    """Request schema for creating a new MCP server."""

    pass


class MCPServerUpdateRequest(BaseModel):
    """Request schema for updating an MCP server."""

    repo: Optional[str] = Field(
        default=None,
        description="GitHub repository",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version spec",
    )
    description: Optional[str] = Field(
        default=None,
        description="Server description",
    )
    env_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables (replaces existing)",
    )


class MCPServerResponse(MCPServerBase):
    """Response schema for MCP server details."""

    status: str = Field(
        description="Installation status",
        examples=["installed", "not_installed", "updating", "error"],
    )
    installed_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of installation",
    )
    resolved_sha: Optional[str] = Field(
        default=None,
        description="Resolved git SHA",
    )
    resolved_version: Optional[str] = Field(
        default=None,
        description="Resolved version tag",
    )
    last_updated: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last update",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "filesystem",
                "repo": "anthropics/mcp-filesystem",
                "version": "latest",
                "description": "File system access MCP server",
                "env_vars": {"ROOT_PATH": "/home/user/documents"},
                "status": "installed",
                "installed_at": "2025-01-15T10:30:00Z",
                "resolved_sha": "abc123def456",
                "resolved_version": "v1.0.0",
                "last_updated": "2025-01-15T10:30:00Z",
            }
        }


class MCPServerListResponse(BaseModel):
    """Response schema for listing MCP servers."""

    servers: List[MCPServerResponse] = Field(
        description="List of MCP servers",
    )
    total: int = Field(
        description="Total number of servers",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "servers": [
                    {
                        "name": "filesystem",
                        "repo": "anthropics/mcp-filesystem",
                        "version": "latest",
                        "description": "File system access",
                        "env_vars": {"ROOT_PATH": "/home/user"},
                        "status": "installed",
                        "installed_at": "2025-01-15T10:30:00Z",
                    }
                ],
                "total": 1,
            }
        }


class DeploymentStatusResponse(BaseModel):
    """Response schema for deployment status."""

    deployed: bool = Field(
        description="Whether server is deployed to Claude Desktop",
    )
    settings_path: Optional[str] = Field(
        default=None,
        description="Path to Claude Desktop settings.json",
    )
    last_deployed: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last deployment",
    )
    health_status: Optional[str] = Field(
        default=None,
        description="Health check status (healthy, unhealthy, unknown)",
    )
    command: Optional[str] = Field(
        default=None,
        description="Command used to run the server",
    )
    args: Optional[List[str]] = Field(
        default=None,
        description="Arguments passed to the command",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "deployed": True,
                "settings_path": "/Users/name/Library/Application Support/Claude/claude_desktop_config.json",
                "last_deployed": "2025-01-15T10:30:00Z",
                "health_status": "unknown",
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-filesystem"],
            }
        }


class DeploymentRequest(BaseModel):
    """Request schema for deploying an MCP server."""

    dry_run: bool = Field(
        default=False,
        description="Preview deployment without applying changes",
    )
    backup: bool = Field(
        default=True,
        description="Create backup of settings.json before deployment",
    )


class DeploymentResponse(BaseModel):
    """Response schema for deployment operation."""

    success: bool = Field(
        description="Whether deployment succeeded",
    )
    message: str = Field(
        description="Human-readable result message",
    )
    settings_path: Optional[str] = Field(
        default=None,
        description="Path to settings.json",
    )
    backup_path: Optional[str] = Field(
        default=None,
        description="Path to backup file",
    )
    env_file_path: Optional[str] = Field(
        default=None,
        description="Path to .env file with environment variables",
    )
    command: Optional[str] = Field(
        default=None,
        description="Command configured for the server",
    )
    args: Optional[List[str]] = Field(
        default=None,
        description="Arguments configured for the server",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if deployment failed",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Server 'filesystem' deployed successfully",
                "settings_path": "/Users/name/Library/Application Support/Claude/claude_desktop_config.json",
                "backup_path": "/Users/name/Library/Application Support/Claude/claude_desktop_config.backup.20250115_103000.json",
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-filesystem"],
            }
        }
