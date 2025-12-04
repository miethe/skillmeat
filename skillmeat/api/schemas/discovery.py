"""Discovery and import schemas for Smart Import & Discovery feature.

Provides Pydantic models for:
- Artifact discovery and scanning
- GitHub metadata fetching
- Bulk import operations
- Artifact parameter updates
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


# ===========================
# Discovery Schemas
# ===========================


class DiscoveryRequest(BaseModel):
    """Request to scan for artifacts."""

    scan_path: Optional[str] = Field(
        default=None,
        description="Custom path to scan. Defaults to collection artifacts directory.",
        examples=["/Users/me/.claude/skills"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scan_path": "/Users/me/.claude/skills",
            }
        }
    }


class DiscoveredArtifact(BaseModel):
    """An artifact discovered during scanning."""

    type: str = Field(
        ...,
        description="Artifact type: skill, command, agent, hook, mcp",
        examples=["skill"],
    )
    name: str = Field(
        ...,
        description="Artifact name",
        examples=["canvas-design"],
    )
    source: Optional[str] = Field(
        default=None,
        description="GitHub source if known",
        examples=["anthropics/skills/canvas-design"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Version if known",
        examples=["latest"],
    )
    scope: Optional[str] = Field(
        default=None,
        description="Scope: user or local",
        examples=["user"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags",
        examples=[["design", "canvas", "art"]],
    )
    description: Optional[str] = Field(
        default=None,
        description="Description",
        examples=["Create beautiful visual art in .png and .pdf documents"],
    )
    path: str = Field(
        ...,
        description="Full path to artifact directory",
        examples=["/Users/me/.claude/skills/canvas-design"],
    )
    discovered_at: datetime = Field(
        ...,
        description="When artifact was discovered",
    )

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: Optional[str]) -> Optional[str]:
        """Validate scope is either 'user' or 'local'."""
        if v is not None and v not in ["user", "local"]:
            raise ValueError("scope must be 'user' or 'local'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "skill",
                "name": "canvas-design",
                "source": "anthropics/skills/canvas-design",
                "version": "latest",
                "scope": "user",
                "tags": ["design", "canvas", "art"],
                "description": "Create beautiful visual art in .png and .pdf documents",
                "path": "/Users/me/.claude/skills/canvas-design",
                "discovered_at": "2025-11-30T10:30:00Z",
            }
        }
    }


class DiscoveryResult(BaseModel):
    """Result of artifact discovery scan."""

    discovered_count: int = Field(
        ...,
        description="Total number of artifacts discovered",
        ge=0,
        examples=[15],
    )
    importable_count: int = Field(
        ...,
        description="Number of artifacts not yet imported (filtered by manifest)",
        ge=0,
        examples=[8],
    )
    artifacts: List[DiscoveredArtifact] = Field(
        default_factory=list,
        description="List of discovered artifacts (filtered if manifest provided)",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Per-artifact errors encountered during scan",
        examples=[
            [
                "Failed to parse SKILL.md in /path/to/skill: invalid YAML frontmatter",
                "Permission denied accessing /path/to/protected/skill",
            ]
        ],
    )
    scan_duration_ms: float = Field(
        ...,
        description="Scan duration in milliseconds",
        ge=0.0,
        examples=[245.67],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "discovered_count": 15,
                "importable_count": 8,
                "artifacts": [
                    {
                        "type": "skill",
                        "name": "canvas-design",
                        "source": "anthropics/skills/canvas-design",
                        "version": "latest",
                        "scope": "user",
                        "tags": ["design", "canvas"],
                        "description": "Create beautiful visual art",
                        "path": "/Users/me/.claude/skills/canvas-design",
                        "discovered_at": "2025-11-30T10:30:00Z",
                    }
                ],
                "errors": [],
                "scan_duration_ms": 245.67,
            }
        }
    }


# ===========================
# GitHub Metadata Schemas
# ===========================


class GitHubSourceSpec(BaseModel):
    """Parsed GitHub source specification."""

    owner: str = Field(
        ...,
        description="GitHub repository owner",
        examples=["anthropics"],
    )
    repo: str = Field(
        ...,
        description="GitHub repository name",
        examples=["skills"],
    )
    path: str = Field(
        ...,
        description="Path within repository",
        examples=["canvas-design"],
    )
    version: Optional[str] = Field(
        default="latest",
        description="Version specification (latest, tag, or SHA)",
        examples=["latest"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "owner": "anthropics",
                "repo": "skills",
                "path": "canvas-design",
                "version": "latest",
            }
        }
    }


class GitHubMetadata(BaseModel):
    """Metadata fetched from GitHub."""

    title: Optional[str] = Field(
        default=None,
        description="Repository or artifact title",
        examples=["Canvas Design Skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Repository or artifact description",
        examples=["Create beautiful visual art in .png and .pdf documents"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Repository owner or artifact author",
        examples=["Anthropic"],
    )
    license: Optional[str] = Field(
        default=None,
        description="Repository license",
        examples=["MIT"],
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Repository topics (tags)",
        examples=[["design", "canvas", "art", "generative"]],
    )
    url: str = Field(
        ...,
        description="GitHub URL",
        examples=["https://github.com/anthropics/skills/tree/main/canvas-design"],
    )
    fetched_at: datetime = Field(
        ...,
        description="Timestamp when metadata was fetched",
    )
    source: str = Field(
        default="auto-populated",
        description="Source of metadata",
        examples=["auto-populated"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Canvas Design Skill",
                "description": "Create beautiful visual art in .png and .pdf documents",
                "author": "Anthropic",
                "license": "MIT",
                "topics": ["design", "canvas", "art"],
                "url": "https://github.com/anthropics/skills/tree/main/canvas-design",
                "fetched_at": "2025-11-30T10:30:00Z",
                "source": "auto-populated",
            }
        }
    }


class MetadataFetchRequest(BaseModel):
    """Request to fetch GitHub metadata."""

    source: str = Field(
        ...,
        description="GitHub source: user/repo/path[@version]",
        examples=["anthropics/skills/canvas-design@latest"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "anthropics/skills/canvas-design@latest",
            }
        }
    }


class MetadataFetchResponse(BaseModel):
    """Response from GitHub metadata fetch."""

    success: bool = Field(
        ...,
        description="Whether metadata fetch succeeded",
        examples=[True],
    )
    metadata: Optional[GitHubMetadata] = Field(
        default=None,
        description="Fetched metadata (if successful)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)",
        examples=["Repository not found"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "metadata": {
                    "title": "Canvas Design Skill",
                    "description": "Create beautiful visual art",
                    "author": "Anthropic",
                    "license": "MIT",
                    "topics": ["design", "canvas"],
                    "url": "https://github.com/anthropics/skills/tree/main/canvas-design",
                    "fetched_at": "2025-11-30T10:30:00Z",
                    "source": "auto-populated",
                },
                "error": None,
            }
        }
    }


# ===========================
# Bulk Import Schemas
# ===========================


class BulkImportArtifact(BaseModel):
    """Single artifact to import in bulk operation."""

    source: str = Field(
        ...,
        description="GitHub source or local path",
        examples=["anthropics/skills/canvas-design@latest"],
    )
    path: Optional[str] = Field(
        default=None,
        description="Filesystem path for local artifacts (required when source starts with 'local/')",
        examples=["/Users/user/.claude/skills/my-skill"],
    )
    artifact_type: str = Field(
        ...,
        description="Type: skill, command, agent, hook, mcp",
        examples=["skill"],
    )
    name: Optional[str] = Field(
        default=None,
        description="Name (auto-derived from source if None)",
        examples=["canvas-design"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Description override",
        examples=["Create beautiful visual art"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Author override",
        examples=["Anthropic"],
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to apply",
        examples=[["design", "canvas", "art"]],
    )
    scope: str = Field(
        default="user",
        description="Scope: user or local",
        examples=["user"],
    )

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """Validate scope is either 'user' or 'local'."""
        if v not in ["user", "local"]:
            raise ValueError("scope must be 'user' or 'local'")
        return v

    @field_validator("artifact_type")
    @classmethod
    def validate_artifact_type(cls, v: str) -> str:
        """Validate artifact type."""
        allowed_types = ["skill", "command", "agent", "hook", "mcp"]
        if v not in allowed_types:
            raise ValueError(f"artifact_type must be one of {allowed_types}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "anthropics/skills/canvas-design@latest",
                "artifact_type": "skill",
                "name": "canvas-design",
                "description": "Create beautiful visual art",
                "author": "Anthropic",
                "tags": ["design", "canvas", "art"],
                "scope": "user",
            }
        }
    }


class BulkImportRequest(BaseModel):
    """Request to import multiple artifacts."""

    artifacts: List[BulkImportArtifact] = Field(
        ...,
        description="List of artifacts to import",
        min_length=1,
    )
    auto_resolve_conflicts: bool = Field(
        default=False,
        description="Automatically resolve conflicts (overwrite existing artifacts)",
        examples=[False],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifacts": [
                    {
                        "source": "anthropics/skills/canvas-design@latest",
                        "artifact_type": "skill",
                        "name": "canvas-design",
                        "tags": ["design", "canvas"],
                        "scope": "user",
                    },
                    {
                        "source": "anthropics/skills/pdf@latest",
                        "artifact_type": "skill",
                        "name": "pdf",
                        "tags": ["document", "pdf"],
                        "scope": "user",
                    },
                ],
                "auto_resolve_conflicts": False,
            }
        }
    }


class ImportStatus(str, Enum):
    """Status of an artifact import operation."""
    SUCCESS = "success"  # Artifact was successfully imported
    SKIPPED = "skipped"  # Artifact already exists in Collection/Project
    FAILED = "failed"    # Import failed due to error


class ImportResult(BaseModel):
    """Result for a single imported artifact."""

    artifact_id: str = Field(
        ...,
        description="ID of the artifact (type:name)",
        examples=["skill:canvas-design"],
    )
    status: ImportStatus = Field(
        ...,
        description="Import status: success, skipped, or failed",
        examples=[ImportStatus.SUCCESS],
    )
    message: str = Field(
        ...,
        description="Human-readable result message",
        examples=["Artifact 'canvas-design' imported successfully"],
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if status=failed)",
        examples=["Artifact already exists and auto_resolve_conflicts is False"],
    )
    skip_reason: Optional[str] = Field(
        default=None,
        description="Reason artifact was skipped (if status=skipped)",
        examples=["Artifact already exists in collection"],
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "artifact_id": "skill:canvas-design",
                "status": "success",
                "message": "Artifact 'canvas-design' imported successfully",
                "error": None,
                "skip_reason": None,
            }
        }
    )

    @computed_field
    @property
    def success(self) -> bool:
        """Backward compatibility: returns True if status is SUCCESS."""
        return self.status == ImportStatus.SUCCESS


class BulkImportResult(BaseModel):
    """Result of bulk import operation."""

    total_requested: int = Field(
        ...,
        description="Total number of artifacts requested for import",
        ge=0,
        examples=[10],
    )
    total_imported: int = Field(
        ...,
        description="Number of artifacts successfully imported",
        ge=0,
        examples=[7],
    )
    total_skipped: int = Field(
        default=0,
        description="Number of artifacts skipped (already exist)",
        ge=0,
        examples=[2],
    )
    total_failed: int = Field(
        ...,
        description="Number of artifacts that failed to import",
        ge=0,
        examples=[1],
    )

    # Per-location breakdown
    imported_to_collection: int = Field(
        default=0,
        description="Number of artifacts added to Collection",
        ge=0,
        examples=[5],
    )
    added_to_project: int = Field(
        default=0,
        description="Number of artifacts deployed to Project",
        ge=0,
        examples=[7],
    )

    results: List[ImportResult] = Field(
        default_factory=list,
        description="Per-artifact import results",
    )
    duration_ms: float = Field(
        ...,
        description="Total import duration in milliseconds",
        ge=0.0,
        examples=[1250.5],
    )

    @computed_field
    @property
    def summary(self) -> str:
        """Human-readable summary of import results."""
        parts = []
        if self.total_imported > 0:
            parts.append(f"{self.total_imported} imported")
        if self.total_skipped > 0:
            parts.append(f"{self.total_skipped} skipped")
        if self.total_failed > 0:
            parts.append(f"{self.total_failed} failed")
        return ", ".join(parts) if parts else "No artifacts processed"

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_requested": 10,
                "total_imported": 7,
                "total_skipped": 2,
                "total_failed": 1,
                "imported_to_collection": 5,
                "added_to_project": 7,
                "results": [
                    {
                        "artifact_id": "skill:canvas-design",
                        "status": "success",
                        "message": "Artifact 'canvas-design' imported successfully",
                        "error": None,
                        "skip_reason": None,
                    },
                    {
                        "artifact_id": "skill:existing-skill",
                        "status": "skipped",
                        "message": "Artifact already exists",
                        "error": None,
                        "skip_reason": "Artifact already exists in collection",
                    },
                ],
                "duration_ms": 1250.5,
                "summary": "7 imported, 2 skipped, 1 failed",
            }
        }
    }


# ===========================
# Parameter Update Schemas
# ===========================


class ArtifactParameters(BaseModel):
    """Updatable artifact parameters."""

    source: Optional[str] = Field(
        default=None,
        description="GitHub source or local path",
        examples=["anthropics/skills/canvas-design@v2.0.0"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Version specification",
        examples=["v2.0.0"],
    )
    scope: Optional[str] = Field(
        default=None,
        description="Scope: user or local",
        examples=["user"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags to apply (replaces existing tags)",
        examples=[["design", "canvas", "art", "generative"]],
    )
    aliases: Optional[List[str]] = Field(
        default=None,
        description="Aliases to apply (replaces existing aliases)",
        examples=[["canvas", "design-tool"]],
    )

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: Optional[str]) -> Optional[str]:
        """Validate scope is either 'user' or 'local'."""
        if v is not None and v not in ["user", "local"]:
            raise ValueError("scope must be 'user' or 'local'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "anthropics/skills/canvas-design@v2.0.0",
                "version": "v2.0.0",
                "scope": "user",
                "tags": ["design", "canvas", "art"],
                "aliases": ["canvas", "design-tool"],
            }
        }
    }


class ParameterUpdateRequest(BaseModel):
    """Request to update artifact parameters."""

    parameters: ArtifactParameters = Field(
        ...,
        description="Parameters to update",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "parameters": {
                    "source": "anthropics/skills/canvas-design@v2.0.0",
                    "version": "v2.0.0",
                    "tags": ["design", "canvas", "art"],
                    "aliases": ["canvas"],
                }
            }
        }
    }


class ParameterUpdateResponse(BaseModel):
    """Response from parameter update."""

    success: bool = Field(
        ...,
        description="Whether update succeeded",
        examples=[True],
    )
    artifact_id: str = Field(
        ...,
        description="ID of the updated artifact (type:name)",
        examples=["skill:canvas-design"],
    )
    updated_fields: List[str] = Field(
        default_factory=list,
        description="List of fields that were updated",
        examples=[["source", "version", "tags"]],
    )
    message: str = Field(
        ...,
        description="Human-readable result message",
        examples=["Artifact 'canvas-design' parameters updated successfully"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "artifact_id": "skill:canvas-design",
                "updated_fields": ["source", "version", "tags"],
                "message": "Artifact 'canvas-design' parameters updated successfully",
            }
        }
    }
