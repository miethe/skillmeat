"""Pydantic schemas for platform defaults API endpoints.

Provides models for platform-specific default configurations
including root directories, artifact path mappings, config filenames,
supported artifact types, and context prefixes.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlatformDefaultsEntry(BaseModel):
    """Platform-specific default configuration entry.

    Represents the default settings for a single platform including
    directory structure, artifact mappings, and supported features.
    """

    root_dir: str = Field(
        description="Root directory for the platform (e.g., '.claude', '.continue')",
        examples=[".claude"],
    )
    artifact_path_map: Dict[str, str] = Field(
        description="Mapping of artifact types to their relative paths within root_dir",
        examples=[{"skill": "skills", "command": "commands"}],
    )
    config_filenames: List[str] = Field(
        description="List of configuration filenames recognized by the platform",
        examples=[["claude_config.toml", "config.toml"]],
    )
    supported_artifact_types: List[str] = Field(
        description="List of artifact types supported by this platform",
        examples=[["skill", "command", "agent", "mcp", "hook"]],
    )
    context_prefixes: List[str] = Field(
        description="List of directory prefixes for context files/documentation",
        examples=[["context", "docs", "specs"]],
    )


class PlatformDefaultsResponse(BaseModel):
    """Response schema for GET /platform-defaults/{platform}.

    Returns the complete default configuration for a specific platform.
    """

    platform: str = Field(
        description="Platform identifier (e.g., 'claude', 'continue')",
        examples=["claude"],
    )
    root_dir: str = Field(
        description="Root directory for the platform",
        examples=[".claude"],
    )
    artifact_path_map: Dict[str, str] = Field(
        description="Mapping of artifact types to their relative paths",
        examples=[{"skill": "skills", "command": "commands"}],
    )
    config_filenames: List[str] = Field(
        description="Configuration filenames recognized by the platform",
        examples=[["claude_config.toml", "config.toml"]],
    )
    supported_artifact_types: List[str] = Field(
        description="Artifact types supported by this platform",
        examples=[["skill", "command", "agent", "mcp", "hook"]],
    )
    context_prefixes: List[str] = Field(
        description="Directory prefixes for context files",
        examples=[["context", "docs", "specs"]],
    )


class AllPlatformDefaultsResponse(BaseModel):
    """Response schema for GET /platform-defaults.

    Returns default configurations for all supported platforms.
    """

    defaults: Dict[str, PlatformDefaultsEntry] = Field(
        description="Dictionary of platform defaults keyed by platform name",
        examples=[
            {
                "claude": {
                    "root_dir": ".claude",
                    "artifact_path_map": {"skill": "skills", "command": "commands"},
                    "config_filenames": ["claude_config.toml"],
                    "supported_artifact_types": ["skill", "command", "agent"],
                    "context_prefixes": ["context", "docs"],
                }
            }
        ],
    )


class PlatformDefaultsUpdateRequest(BaseModel):
    """Request schema for PUT /platform-defaults/{platform}.

    All fields are optional to allow partial updates of platform defaults.
    """

    root_dir: Optional[str] = Field(
        default=None,
        description="Root directory for the platform",
        examples=[".claude"],
    )
    artifact_path_map: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping of artifact types to their relative paths",
        examples=[{"skill": "skills", "command": "commands"}],
    )
    config_filenames: Optional[List[str]] = Field(
        default=None,
        description="Configuration filenames recognized by the platform",
        examples=[["claude_config.toml", "config.toml"]],
    )
    supported_artifact_types: Optional[List[str]] = Field(
        default=None,
        description="Artifact types supported by this platform",
        examples=[["skill", "command", "agent", "mcp", "hook"]],
    )
    context_prefixes: Optional[List[str]] = Field(
        default=None,
        description="Directory prefixes for context files",
        examples=[["context", "docs", "specs"]],
    )


class CustomContextConfig(BaseModel):
    """Custom context prefix configuration.

    Allows users to configure custom context directory prefixes
    that supplement or override platform defaults.
    """

    enabled: bool = Field(
        default=False,
        description="Whether custom context configuration is enabled",
        examples=[True],
    )
    prefixes: List[str] = Field(
        default_factory=list,
        description="List of custom context directory prefixes to use",
        examples=[["custom-context", "my-docs"]],
    )
    mode: str = Field(
        default="addendum",
        description="How custom prefixes are applied: 'override' replaces platform defaults, 'addendum' adds to them",
        examples=["addendum"],
    )
    platforms: List[str] = Field(
        default_factory=list,
        description="List of platform names this custom configuration applies to. Empty means all platforms.",
        examples=[["claude", "continue"]],
    )


class CustomContextConfigResponse(BaseModel):
    """Response schema for GET /custom-context.

    Returns the current custom context configuration.
    """

    enabled: bool = Field(
        description="Whether custom context configuration is enabled",
        examples=[True],
    )
    prefixes: List[str] = Field(
        description="Custom context directory prefixes",
        examples=[["custom-context", "my-docs"]],
    )
    mode: str = Field(
        description="Application mode: 'override' or 'addendum'",
        examples=["addendum"],
    )
    platforms: List[str] = Field(
        description="Platforms this configuration applies to",
        examples=[["claude", "continue"]],
    )


class CustomContextConfigUpdateRequest(BaseModel):
    """Request schema for PUT /custom-context.

    All fields are optional to allow partial updates of custom context configuration.
    """

    enabled: Optional[bool] = Field(
        default=None,
        description="Enable or disable custom context configuration",
        examples=[True],
    )
    prefixes: Optional[List[str]] = Field(
        default=None,
        description="Custom context directory prefixes",
        examples=[["custom-context", "my-docs"]],
    )
    mode: Optional[str] = Field(
        default=None,
        description="Application mode: 'override' or 'addendum'",
        examples=["addendum"],
    )
    platforms: Optional[List[str]] = Field(
        default=None,
        description="Platforms this configuration applies to",
        examples=[["claude", "continue"]],
    )
