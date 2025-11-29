"""Artifact API schemas for request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .common import PaginatedResponse


class ArtifactSourceType(str, Enum):
    """Source type for artifact creation."""

    GITHUB = "github"
    LOCAL = "local"


class ArtifactCreateRequest(BaseModel):
    """Request schema for creating an artifact."""

    source_type: ArtifactSourceType = Field(description="Source type: github or local")
    source: str = Field(description="GitHub URL/spec or local path")
    artifact_type: str = Field(
        description="Type of artifact (skill, command, agent, mcp, hook)"
    )
    name: Optional[str] = Field(default=None, description="Override artifact name")
    collection: Optional[str] = Field(
        default=None, description="Target collection (uses default if not specified)"
    )
    tags: Optional[List[str]] = Field(default=None, description="Tags to apply")
    description: Optional[str] = Field(default=None, description="Override description")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "source_type": "github",
                "source": "anthropics/skills/canvas-design",
                "artifact_type": "skill",
                "name": "canvas",
                "collection": "default",
                "tags": ["design", "canvas"],
                "description": "Canvas design skill",
            }
        }


class ArtifactCreateResponse(BaseModel):
    """Response for artifact creation."""

    success: bool = Field(description="Whether creation succeeded")
    artifact_id: str = Field(description="Artifact ID (format: type:name)")
    artifact_name: str = Field(description="Name of created artifact")
    artifact_type: str = Field(description="Type of artifact")
    collection: str = Field(description="Collection name")
    source: str = Field(description="Source specification or path")
    source_type: str = Field(description="Source type (github or local)")
    path: str = Field(description="Path to artifact in collection")
    message: str = Field(description="Human-readable result message")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "artifact_id": "skill:canvas",
                "artifact_name": "canvas",
                "artifact_type": "skill",
                "collection": "default",
                "source": "anthropics/skills/canvas-design",
                "source_type": "github",
                "path": "skills/canvas",
                "message": "Artifact 'canvas' created successfully",
            }
        }


class ArtifactMetadataResponse(BaseModel):
    """Artifact metadata from SKILL.md / COMMAND.md / AGENT.md."""

    title: Optional[str] = Field(
        default=None,
        description="Artifact title",
        examples=["PDF Processing Skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Artifact description",
        examples=["Extract and analyze PDF documents"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Artifact author",
        examples=["Anthropic"],
    )
    license: Optional[str] = Field(
        default=None,
        description="Artifact license",
        examples=["MIT"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Artifact version from metadata",
        examples=["1.2.3"],
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required dependencies",
        examples=[["python-magic", "PyPDF2"]],
    )


class ArtifactUpstreamInfo(BaseModel):
    """Upstream tracking information for an artifact."""

    tracking_enabled: bool = Field(
        description="Whether upstream tracking is enabled",
        examples=[True],
    )
    current_sha: Optional[str] = Field(
        default=None,
        description="Current installed version SHA",
        examples=["abc123def456"],
    )
    upstream_sha: Optional[str] = Field(
        default=None,
        description="Latest upstream version SHA",
        examples=["def789ghi012"],
    )
    update_available: bool = Field(
        description="Whether an update is available",
        examples=[True],
    )
    has_local_modifications: bool = Field(
        description="Whether local modifications exist",
        examples=[False],
    )
    drift_status: Optional[str] = Field(
        default=None,
        description="Drift status: none (no changes), modified (local changes only), outdated (upstream changes only), conflict (both changed), added (new in collection), removed (deleted from collection)",
        examples=["conflict"],
    )


class ArtifactResponse(BaseModel):
    """Response schema for a single artifact.

    Provides complete artifact information including metadata,
    deployment status, and upstream tracking.
    """

    id: str = Field(
        description="Artifact composite key (type:name)",
        examples=["skill:pdf"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["pdf"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    source: str = Field(
        description="Source specification",
        examples=["anthropics/skills/pdf"],
    )
    version: str = Field(
        description="Version specification",
        examples=["latest"],
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Artifact aliases",
        examples=[["pdf-processor", "doc-reader"]],
    )
    metadata: Optional[ArtifactMetadataResponse] = Field(
        default=None,
        description="Artifact metadata",
    )
    upstream: Optional[ArtifactUpstreamInfo] = Field(
        default=None,
        description="Upstream tracking information",
    )
    deployment_stats: Optional["DeploymentStatistics"] = Field(
        default=None,
        description="Deployment statistics (included when include_deployments=true)",
    )
    added: datetime = Field(
        description="Timestamp when artifact was added to collection",
    )
    updated: datetime = Field(
        description="Timestamp of last update",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "skill:pdf",
                "name": "pdf",
                "type": "skill",
                "source": "anthropics/skills/pdf",
                "version": "latest",
                "aliases": ["pdf-processor"],
                "metadata": {
                    "title": "PDF Processing Skill",
                    "description": "Extract and analyze PDF documents",
                    "author": "Anthropic",
                    "license": "MIT",
                    "tags": ["document", "pdf"],
                },
                "upstream": {
                    "tracking_enabled": True,
                    "current_sha": "abc123",
                    "upstream_sha": "def456",
                    "update_available": True,
                    "has_local_modifications": False,
                },
                "added": "2024-11-16T12:00:00Z",
                "updated": "2024-11-16T15:30:00Z",
            }
        }


class ArtifactListResponse(PaginatedResponse[ArtifactResponse]):
    """Paginated response for artifact listings."""

    pass


class ArtifactUpstreamResponse(BaseModel):
    """Response for upstream status check.

    Provides detailed information about available updates and
    local modifications.
    """

    artifact_id: str = Field(
        description="Artifact composite key",
        examples=["skill:pdf"],
    )
    tracking_enabled: bool = Field(
        description="Whether upstream tracking is enabled",
        examples=[True],
    )
    current_version: str = Field(
        description="Current installed version",
        examples=["1.2.3"],
    )
    current_sha: str = Field(
        description="Current version SHA",
        examples=["abc123def456"],
    )
    upstream_version: Optional[str] = Field(
        default=None,
        description="Latest upstream version",
        examples=["1.3.0"],
    )
    upstream_sha: Optional[str] = Field(
        default=None,
        description="Latest upstream SHA",
        examples=["def789ghi012"],
    )
    update_available: bool = Field(
        description="Whether an update is available",
        examples=[True],
    )
    has_local_modifications: bool = Field(
        description="Whether local modifications exist",
        examples=[False],
    )
    last_checked: datetime = Field(
        description="Timestamp of last upstream check",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf",
                "tracking_enabled": True,
                "current_version": "1.2.3",
                "current_sha": "abc123def456",
                "upstream_version": "1.3.0",
                "upstream_sha": "def789ghi012",
                "update_available": True,
                "has_local_modifications": False,
                "last_checked": "2024-11-16T15:30:00Z",
            }
        }


class ArtifactUpdateMetadataRequest(BaseModel):
    """Request schema for updating artifact metadata fields."""

    title: Optional[str] = Field(
        default=None,
        description="Artifact title",
        examples=["PDF Processing Skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Artifact description",
        examples=["Extract and analyze PDF documents"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Artifact author",
        examples=["Anthropic"],
    )
    license: Optional[str] = Field(
        default=None,
        description="Artifact license",
        examples=["MIT"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )


class ArtifactUpdateRequest(BaseModel):
    """Request schema for updating an artifact.

    Allows updating metadata and tags. Note: aliases are not yet
    implemented in the backend but are included for future compatibility.
    """

    aliases: Optional[List[str]] = Field(
        default=None,
        description="Artifact aliases (not yet implemented)",
        examples=[["pdf-processor", "doc-reader"]],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )
    metadata: Optional[ArtifactUpdateMetadataRequest] = Field(
        default=None,
        description="Artifact metadata to update",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "tags": ["document", "pdf", "productivity"],
                "metadata": {
                    "title": "Enhanced PDF Processor",
                    "description": "Advanced PDF extraction and analysis",
                    "tags": ["document", "pdf"],
                },
            }
        }


class ArtifactDeployRequest(BaseModel):
    """Request schema for deploying an artifact."""

    project_path: str = Field(
        description="Path to target project directory",
        examples=["/Users/me/my-project"],
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing artifact if already deployed",
    )


class ArtifactDeployResponse(BaseModel):
    """Response schema for artifact deployment."""

    success: bool = Field(description="Whether deployment succeeded")
    message: str = Field(description="Human-readable result message")
    artifact_name: str = Field(description="Name of deployed artifact")
    artifact_type: str = Field(description="Type of artifact (skill/command/agent)")
    deployed_path: Optional[str] = Field(
        default=None,
        description="Path where artifact was deployed",
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
                "message": "Artifact 'pdf' deployed successfully",
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "deployed_path": "/Users/me/my-project/.claude/skills/pdf",
                "error_message": None,
            }
        }


class ArtifactSyncRequest(BaseModel):
    """Request schema for syncing an artifact.

    If project_path is provided: Syncs FROM project TO collection (reverse sync).
    If project_path is omitted: Syncs FROM upstream source TO collection (update).
    """

    project_path: Optional[str] = Field(
        default=None,
        description="Path to project directory containing deployed artifact. If omitted, syncs from upstream source.",
        examples=["/Users/me/my-project"],
    )
    force: bool = Field(
        default=False,
        description="Force sync even if conflicts are detected",
    )
    strategy: str = Field(
        default="theirs",
        description="Conflict resolution strategy: 'theirs' (take upstream), 'ours' (keep local), 'manual' (preserve conflicts)",
        pattern="^(theirs|ours|manual)$",
    )


class ConflictInfo(BaseModel):
    """Information about a sync conflict."""

    file_path: str = Field(
        description="Path to conflicted file relative to artifact root"
    )
    conflict_type: str = Field(
        description="Type of conflict",
        examples=["modified", "added", "removed"],
    )


class ArtifactSyncResponse(BaseModel):
    """Response schema for artifact sync operation."""

    success: bool = Field(description="Whether sync operation succeeded")
    message: str = Field(description="Human-readable result message")
    artifact_name: str = Field(description="Name of synced artifact")
    artifact_type: str = Field(description="Type of artifact (skill/command/agent)")
    conflicts: Optional[List[ConflictInfo]] = Field(
        default=None,
        description="List of conflicts detected during sync (if any)",
    )
    updated_version: Optional[str] = Field(
        default=None,
        description="New version after sync (if applicable)",
    )
    synced_files_count: Optional[int] = Field(
        default=None,
        description="Number of files synced",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Artifact 'pdf' synced successfully",
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "conflicts": None,
                "updated_version": "1.2.0",
                "synced_files_count": 5,
            }
        }


# ===========================
# Version Tracking Schemas
# ===========================


class ArtifactVersionInfo(BaseModel):
    """Version information for a single artifact instance.

    Represents a specific version of an artifact at a point in time,
    tracking content hash and parent lineage.
    """

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type (skill/command/agent)")
    location: str = Field(
        description="Location (collection name or absolute project path)"
    )
    location_type: Literal["collection", "project"] = Field(
        description="Type of location"
    )
    content_sha: str = Field(
        description="SHA-256 content hash of artifact",
        examples=["abc123def456789abcdef123456789abcdef123456789abcdef123456789ab"],
    )
    parent_sha: Optional[str] = Field(
        default=None,
        description="Parent version SHA (for tracking lineage)",
        examples=["def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh"],
    )
    is_modified: bool = Field(description="Whether content differs from parent version")
    created_at: datetime = Field(description="Version creation timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional version metadata",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "location": "default",
                "location_type": "collection",
                "content_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
                "parent_sha": None,
                "is_modified": False,
                "created_at": "2025-11-15T10:00:00Z",
                "metadata": {"collection_name": "default"},
            }
        }


class VersionGraphNodeResponse(BaseModel):
    """Node in version graph visualization.

    Recursive structure representing the version tree,
    where each node can have multiple children representing
    deployments or forks.
    """

    id: str = Field(
        description="Unique node identifier (e.g., 'collection:default:abc123' or 'project:/path/to/project')",
        examples=["collection:default:abc123", "project:/Users/me/project1"],
    )
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    version_info: ArtifactVersionInfo = Field(
        description="Version information for this node"
    )
    children: List["VersionGraphNodeResponse"] = Field(
        default_factory=list,
        description="Child nodes (deployments/forks from this version)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node metadata",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "collection:default:abc123",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "version_info": {
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "location": "default",
                    "location_type": "collection",
                    "content_sha": "abc123",
                    "parent_sha": None,
                    "is_modified": False,
                    "created_at": "2025-11-15T10:00:00Z",
                    "metadata": {},
                },
                "children": [],
                "metadata": {},
            }
        }


class VersionGraphResponse(BaseModel):
    """Complete version graph for an artifact.

    Provides hierarchical view of artifact versions across
    collection and all project deployments, with aggregated
    statistics.
    """

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    root: Optional[VersionGraphNodeResponse] = Field(
        default=None,
        description="Root node (typically the collection version)",
    )
    statistics: Dict[str, Any] = Field(
        description="Aggregated statistics about version graph",
        examples=[
            {
                "total_deployments": 5,
                "modified_count": 2,
                "unmodified_count": 3,
                "orphaned_count": 0,
            }
        ],
    )
    last_updated: datetime = Field(description="Timestamp when graph was last computed")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "root": {
                    "id": "collection:default:abc123",
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "version_info": {},
                    "children": [],
                    "metadata": {},
                },
                "statistics": {
                    "total_deployments": 2,
                    "modified_count": 1,
                    "unmodified_count": 1,
                    "orphaned_count": 0,
                },
                "last_updated": "2025-11-20T16:00:00Z",
            }
        }


class DeploymentModificationStatus(BaseModel):
    """Modification status for a single deployment.

    Tracks whether a deployed artifact has been modified
    since deployment by comparing content hashes.
    """

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    deployed_sha: str = Field(
        description="SHA-256 hash at deployment time",
        examples=["abc123def456789abcdef123456789abcdef123456789abcdef123456789ab"],
    )
    current_sha: str = Field(
        description="Current SHA-256 hash",
        examples=["def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh"],
    )
    is_modified: bool = Field(
        description="Whether artifact has been modified since deployment"
    )
    modification_detected_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when modification was first detected",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "deployed_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
                "current_sha": "def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh",
                "is_modified": True,
                "modification_detected_at": "2025-11-20T15:45:00Z",
            }
        }


class ModificationCheckResponse(BaseModel):
    """Response from modification check operation.

    Provides comprehensive status of all deployments in a project,
    identifying which artifacts have been modified.
    """

    project_id: str = Field(
        description="Base64-encoded project path",
        examples=["L1VzZXJzL21lL3Byb2plY3Qx"],
    )
    checked_at: datetime = Field(description="Timestamp when check was performed")
    modifications_detected: int = Field(
        description="Number of modified artifacts detected",
        ge=0,
    )
    deployments: List[DeploymentModificationStatus] = Field(
        description="Status of each deployment in the project"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
                "checked_at": "2025-11-20T16:00:00Z",
                "modifications_detected": 2,
                "deployments": [
                    {
                        "artifact_name": "pdf-processor",
                        "artifact_type": "skill",
                        "deployed_sha": "abc123",
                        "current_sha": "def456",
                        "is_modified": True,
                        "modification_detected_at": "2025-11-20T15:45:00Z",
                    }
                ],
            }
        }


class ProjectDeploymentInfo(BaseModel):
    """Deployment information for a single project.

    Provides per-project deployment details including
    modification status and deployment timestamp.
    """

    project_name: str = Field(description="Project name (derived from path)")
    project_path: str = Field(description="Absolute project path")
    is_modified: bool = Field(
        description="Whether this deployment has local modifications"
    )
    deployed_at: datetime = Field(description="Deployment timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "project_name": "my-project",
                "project_path": "/Users/me/my-project",
                "is_modified": True,
                "deployed_at": "2025-11-20T10:30:00Z",
            }
        }


class DeploymentStatistics(BaseModel):
    """Deployment statistics for an artifact.

    Aggregates deployment information across all projects
    where this artifact is deployed.
    """

    total_deployments: int = Field(
        description="Total number of deployments across all projects",
        ge=0,
    )
    modified_deployments: int = Field(
        description="Number of deployments with local modifications",
        ge=0,
    )
    projects: List[ProjectDeploymentInfo] = Field(
        description="Per-project deployment information"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "total_deployments": 5,
                "modified_deployments": 2,
                "projects": [
                    {
                        "project_name": "project1",
                        "project_path": "/Users/me/project1",
                        "is_modified": True,
                        "deployed_at": "2025-11-20T10:30:00Z",
                    },
                    {
                        "project_name": "project2",
                        "project_path": "/Users/me/project2",
                        "is_modified": False,
                        "deployed_at": "2025-11-19T14:20:00Z",
                    },
                ],
            }
        }


# ===========================
# Diff Schemas
# ===========================


class FileDiff(BaseModel):
    """Diff information for a single file."""

    file_path: str = Field(description="Relative path to file within artifact")
    status: Literal["added", "modified", "deleted", "unchanged"] = Field(
        description="Change status of file"
    )
    collection_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash in collection"
    )
    project_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash in project"
    )
    unified_diff: Optional[str] = Field(
        default=None, description="Unified diff content (for modified files)"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "file_path": "SKILL.md",
                "status": "modified",
                "collection_hash": "abc123def456",
                "project_hash": "def789ghi012",
                "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1,3 +1,3 @@\n-Old line\n+New line\n",
            }
        }


class ArtifactDiffResponse(BaseModel):
    """Response for artifact diff."""

    artifact_id: str = Field(description="Artifact identifier")
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    collection_name: str = Field(description="Collection name")
    project_path: str = Field(description="Project path")
    has_changes: bool = Field(description="Whether any changes detected")
    files: List[FileDiff] = Field(description="List of file diffs")
    summary: Dict[str, int] = Field(
        description="Summary counts: added, modified, deleted, unchanged"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "collection_name": "default",
                "project_path": "/Users/me/my-project",
                "has_changes": True,
                "files": [
                    {
                        "file_path": "SKILL.md",
                        "status": "modified",
                        "collection_hash": "abc123",
                        "project_hash": "def456",
                        "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n...",
                    }
                ],
                "summary": {
                    "added": 0,
                    "modified": 1,
                    "deleted": 0,
                    "unchanged": 3,
                },
            }
        }


class ArtifactUpstreamDiffResponse(BaseModel):
    """Response for upstream diff comparing collection with GitHub source."""

    artifact_id: str = Field(description="Artifact identifier")
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    collection_name: str = Field(description="Collection name")
    upstream_source: str = Field(description="GitHub upstream source specification")
    upstream_version: str = Field(description="Upstream version (SHA or tag)")
    has_changes: bool = Field(description="Whether any changes detected")
    files: List[FileDiff] = Field(description="List of file diffs")
    summary: Dict[str, int] = Field(
        description="Summary counts: added, modified, deleted, unchanged"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "collection_name": "default",
                "upstream_source": "anthropics/skills/pdf",
                "upstream_version": "abc123def456",
                "has_changes": True,
                "files": [
                    {
                        "file_path": "SKILL.md",
                        "status": "modified",
                        "collection_hash": "abc123",
                        "project_hash": "def456",
                        "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n...",
                    }
                ],
                "summary": {
                    "added": 0,
                    "modified": 1,
                    "deleted": 0,
                    "unchanged": 3,
                },
            }
        }


# ===========================
# File Content Schemas
# ===========================


class FileNode(BaseModel):
    """File or directory node in artifact file tree."""

    name: str = Field(description="File or directory name")
    path: str = Field(description="Relative path from artifact root")
    type: Literal["file", "directory"] = Field(description="Node type")
    size: Optional[int] = Field(
        default=None,
        description="File size in bytes (only for files)",
    )
    children: Optional[List["FileNode"]] = Field(
        default=None,
        description="Child nodes (only for directories)",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "src",
                "path": "src",
                "type": "directory",
                "size": None,
                "children": [
                    {
                        "name": "main.py",
                        "path": "src/main.py",
                        "type": "file",
                        "size": 1234,
                        "children": None,
                    }
                ],
            }
        }


class FileListResponse(BaseModel):
    """Response for artifact file listing."""

    artifact_id: str = Field(description="Artifact identifier")
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    collection_name: str = Field(description="Collection name")
    files: List[FileNode] = Field(description="File tree structure")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "collection_name": "default",
                "files": [
                    {
                        "name": "SKILL.md",
                        "path": "SKILL.md",
                        "type": "file",
                        "size": 2048,
                        "children": None,
                    },
                    {
                        "name": "src",
                        "path": "src",
                        "type": "directory",
                        "size": None,
                        "children": [],
                    },
                ],
            }
        }


class FileContentResponse(BaseModel):
    """Response for artifact file content."""

    artifact_id: str = Field(description="Artifact identifier")
    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    collection_name: str = Field(description="Collection name")
    path: str = Field(description="Relative file path within artifact")
    content: str = Field(description="File content (UTF-8 encoded)")
    size: int = Field(description="File size in bytes")
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME type of the file",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "collection_name": "default",
                "path": "SKILL.md",
                "content": "# PDF Processor Skill\n\nThis skill processes PDF files...",
                "size": 2048,
                "mime_type": "text/markdown",
            }
        }


class FileUpdateRequest(BaseModel):
    """Request body for updating file content."""

    content: str = Field(..., description="New file content")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "content": "# Updated PDF Processor Skill\n\nThis skill processes PDF files with enhanced features...",
            }
        }
