"""Configuration API schemas.

Provides Pydantic models for configuration-related API endpoints,
including detection patterns for artifact type inference and feature flags.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class DetectionPatternsResponse(BaseModel):
    """Response model for artifact detection patterns.

    This schema exposes the detection patterns used by the Python backend
    for identifying artifact types from directory structures. Frontend
    applications can use this data to replicate the same detection logic.

    Attributes:
        container_aliases: Maps artifact type to list of valid container names.
            e.g., {"skill": ["skills", "skill", "claude-skills"]}
        leaf_containers: Flattened unique list of all valid container names.
            Useful for quick membership checks when traversing directories.
        canonical_containers: Maps artifact type to its preferred container name.
            e.g., {"skill": "skills"}
    """

    container_aliases: Dict[str, List[str]] = Field(
        description="Maps artifact type to list of valid container directory names",
        examples=[
            {
                "skill": ["skills", "skill", "claude-skills"],
                "command": ["commands", "command", "claude-commands"],
            }
        ],
    )
    leaf_containers: List[str] = Field(
        description="Flattened unique list of all valid container names across all types",
        examples=[
            [
                "skills",
                "skill",
                "claude-skills",
                "commands",
                "command",
                "claude-commands",
            ]
        ],
    )
    canonical_containers: Dict[str, str] = Field(
        description="Maps artifact type to its canonical (preferred) container name",
        examples=[{"skill": "skills", "command": "commands", "agent": "agents"}],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "container_aliases": {
                    "skill": ["skills", "skill", "claude-skills"],
                    "command": ["commands", "command", "claude-commands"],
                    "agent": ["agents", "agent", "subagents", "claude-agents"],
                    "hook": ["hooks", "hook", "claude-hooks"],
                    "mcp": [
                        "mcp",
                        "mcp-servers",
                        "servers",
                        "mcp_servers",
                        "claude-mcp",
                    ],
                },
                "leaf_containers": [
                    "skills",
                    "skill",
                    "claude-skills",
                    "commands",
                    "command",
                    "claude-commands",
                    "agents",
                    "agent",
                    "subagents",
                    "claude-agents",
                    "hooks",
                    "hook",
                    "claude-hooks",
                    "mcp",
                    "mcp-servers",
                    "servers",
                    "mcp_servers",
                    "claude-mcp",
                ],
                "canonical_containers": {
                    "skill": "skills",
                    "command": "commands",
                    "agent": "agents",
                    "hook": "hooks",
                    "mcp": "mcp",
                },
            }
        }


class FeatureFlagsResponse(BaseModel):
    """Response model for backend feature flags.

    Exposes feature flag state to the frontend so the UI can conditionally
    render features that depend on backend capabilities. Frontend components
    should gate visibility and routing on these flags.

    Attributes:
        composite_artifacts_enabled: Whether composite artifact detection is active.
        deployment_sets_enabled: Whether the deployment sets feature is active.
            When False, all /api/v1/deployment-sets endpoints return 404.
        memory_context_enabled: Whether the Memory & Context Intelligence System
            (memory items, context modules, context packing) is active.
    """

    composite_artifacts_enabled: bool = Field(
        description=(
            "Whether composite artifact detection is enabled. "
            "When False, discovery always performs flat detection."
        )
    )
    deployment_sets_enabled: bool = Field(
        description=(
            "Whether the deployment sets feature is enabled. "
            "When False, all /api/v1/deployment-sets endpoints return 404."
        )
    )
    memory_context_enabled: bool = Field(
        description=(
            "Whether the Memory & Context Intelligence System is enabled. "
            "Covers memory items, context modules, and context packing."
        )
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "composite_artifacts_enabled": True,
                "deployment_sets_enabled": True,
                "memory_context_enabled": True,
            }
        }
