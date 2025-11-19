"""Pydantic schemas for bundle import/export API endpoints.

Defines request and response models for bundle operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ====================
# Request Schemas
# ====================


class BundleImportRequest(BaseModel):
    """Request to import a bundle."""

    strategy: str = Field(
        default="interactive",
        description="Conflict resolution strategy (merge, fork, skip, interactive)",
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Target collection (uses active if None)",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview import without making changes",
    )
    force: bool = Field(
        default=False,
        description="Force import even with validation warnings",
    )
    expected_hash: Optional[str] = Field(
        default=None,
        description="Expected SHA-256 hash for verification",
    )

    @field_validator("strategy", mode="after")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate strategy is one of allowed values."""
        allowed = {"merge", "fork", "skip", "interactive"}
        if v not in allowed:
            raise ValueError(f"Strategy must be one of: {', '.join(allowed)}")
        return v


# ====================
# Response Schemas
# ====================


class ImportedArtifactResponse(BaseModel):
    """Single imported artifact in import result."""

    name: str = Field(description="Artifact name")
    type: str = Field(description="Artifact type (skill, command, agent)")
    resolution: str = Field(
        description="How conflict was resolved (imported, forked, skipped, merged)"
    )
    new_name: Optional[str] = Field(
        default=None,
        description="New name if forked",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for resolution decision",
    )


class BundleImportResponse(BaseModel):
    """Response from bundle import operation."""

    success: bool = Field(description="Whether import succeeded")
    imported_count: int = Field(
        default=0,
        description="Number of new artifacts imported",
    )
    skipped_count: int = Field(
        default=0,
        description="Number of artifacts skipped",
    )
    forked_count: int = Field(
        default=0,
        description="Number of artifacts forked",
    )
    merged_count: int = Field(
        default=0,
        description="Number of artifacts merged (overwritten)",
    )
    artifacts: List[ImportedArtifactResponse] = Field(
        default_factory=list,
        description="Details of imported artifacts",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages if import failed",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warning messages",
    )
    bundle_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of imported bundle",
    )
    import_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of import operation",
    )
    summary: str = Field(
        default="",
        description="Human-readable summary",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "imported_count": 3,
                "skipped_count": 1,
                "forked_count": 1,
                "merged_count": 0,
                "artifacts": [
                    {
                        "name": "python-skill",
                        "type": "skill",
                        "resolution": "imported",
                        "new_name": None,
                        "reason": None,
                    },
                    {
                        "name": "existing-skill",
                        "type": "skill",
                        "resolution": "forked",
                        "new_name": "existing-skill-imported",
                        "reason": "user chose: fork",
                    },
                ],
                "errors": [],
                "warnings": ["Hidden file detected in bundle"],
                "bundle_hash": "abc123def456...",
                "import_time": "2025-11-16T12:00:00Z",
                "summary": "Import successful: 4 artifacts imported, 1 skipped",
            }
        }


class ValidationIssueResponse(BaseModel):
    """Single validation issue."""

    severity: str = Field(description="Issue severity (error, warning, info)")
    category: str = Field(
        description="Issue category (security, schema, integrity, size)"
    )
    message: str = Field(description="Issue message")
    file_path: Optional[str] = Field(
        default=None,
        description="File path if issue relates to specific file",
    )


class BundleValidationResponse(BaseModel):
    """Response from bundle validation."""

    is_valid: bool = Field(description="Whether bundle is valid")
    issues: List[ValidationIssueResponse] = Field(
        default_factory=list,
        description="Validation issues found",
    )
    bundle_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of bundle",
    )
    artifact_count: int = Field(
        default=0,
        description="Number of artifacts in bundle",
    )
    total_size_bytes: int = Field(
        default=0,
        description="Total bundle size in bytes",
    )
    summary: str = Field(
        default="",
        description="Human-readable summary",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "is_valid": True,
                "issues": [
                    {
                        "severity": "warning",
                        "category": "security",
                        "message": "Hidden file detected",
                        "file_path": ".hidden/file.txt",
                    }
                ],
                "bundle_hash": "abc123def456...",
                "artifact_count": 5,
                "total_size_bytes": 1048576,
                "summary": "Bundle valid: 5 artifacts, 1.00 MB",
            }
        }


# ====================
# Bundle CRUD Schemas
# ====================


class BundleArtifactSummary(BaseModel):
    """Summary of an artifact within a bundle."""

    name: str = Field(description="Artifact name")
    type: str = Field(description="Artifact type (skill, command, agent)")
    version: str = Field(description="Artifact version")
    scope: str = Field(description="Artifact scope (user, local)")


class BundleMetadataResponse(BaseModel):
    """Bundle metadata response."""

    name: str = Field(description="Bundle name (identifier)")
    description: str = Field(description="Human-readable description")
    author: str = Field(description="Author name or email")
    created_at: str = Field(description="ISO 8601 timestamp of bundle creation")
    version: str = Field(default="1.0.0", description="Bundle version")
    license: str = Field(default="MIT", description="License identifier")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    homepage: Optional[str] = Field(default=None, description="Project homepage URL")
    repository: Optional[str] = Field(default=None, description="Source repository URL")


class BundleListItem(BaseModel):
    """Single bundle in list response."""

    bundle_id: str = Field(description="Bundle unique identifier (hash)")
    name: str = Field(description="Bundle name")
    description: str = Field(description="Bundle description")
    author: str = Field(description="Author name or email")
    created_at: str = Field(description="ISO 8601 timestamp of bundle creation")
    artifact_count: int = Field(description="Number of artifacts in bundle")
    total_size_bytes: int = Field(description="Total bundle size in bytes")
    source: str = Field(description="Bundle source (created, imported, or marketplace)")
    imported_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when bundle was imported (if applicable)",
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "bundle_id": "sha256:abc123def456...",
                "name": "python-essentials",
                "description": "Essential Python development skills",
                "author": "john.doe@example.com",
                "created_at": "2025-11-16T12:00:00Z",
                "artifact_count": 5,
                "total_size_bytes": 1048576,
                "source": "imported",
                "imported_at": "2025-11-18T10:30:00Z",
                "tags": ["python", "development"],
            }
        }


class BundleListResponse(BaseModel):
    """Response for listing bundles."""

    bundles: List[BundleListItem] = Field(
        default_factory=list,
        description="List of bundles",
    )
    total: int = Field(description="Total number of bundles")
    filtered_by: Optional[str] = Field(
        default=None,
        description="Filter applied (created, imported, or None for all)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "bundles": [
                    {
                        "bundle_id": "sha256:abc123...",
                        "name": "python-essentials",
                        "description": "Essential Python development skills",
                        "author": "john.doe@example.com",
                        "created_at": "2025-11-16T12:00:00Z",
                        "artifact_count": 5,
                        "total_size_bytes": 1048576,
                        "source": "imported",
                        "imported_at": "2025-11-18T10:30:00Z",
                        "tags": ["python", "development"],
                    }
                ],
                "total": 1,
                "filtered_by": "imported",
            }
        }


class BundleDetailResponse(BaseModel):
    """Detailed bundle information response."""

    bundle_id: str = Field(description="Bundle unique identifier (hash)")
    metadata: BundleMetadataResponse = Field(description="Bundle metadata")
    artifacts: List[BundleArtifactSummary] = Field(
        description="List of artifacts in bundle"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of bundle dependencies",
    )
    bundle_hash: str = Field(description="SHA-256 hash of bundle")
    total_size_bytes: int = Field(description="Total bundle size in bytes")
    total_files: int = Field(description="Total number of files in bundle")
    source: str = Field(description="Bundle source (created, imported, or marketplace)")
    imported_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when bundle was imported",
    )
    bundle_path: Optional[str] = Field(
        default=None,
        description="Local path to bundle file if available",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "bundle_id": "sha256:abc123def456...",
                "metadata": {
                    "name": "python-essentials",
                    "description": "Essential Python development skills",
                    "author": "john.doe@example.com",
                    "created_at": "2025-11-16T12:00:00Z",
                    "version": "1.0.0",
                    "license": "MIT",
                    "tags": ["python", "development"],
                    "homepage": "https://example.com",
                    "repository": "https://github.com/user/repo",
                },
                "artifacts": [
                    {
                        "name": "python-skill",
                        "type": "skill",
                        "version": "1.0.0",
                        "scope": "user",
                    }
                ],
                "dependencies": [],
                "bundle_hash": "sha256:abc123def456...",
                "total_size_bytes": 1048576,
                "total_files": 25,
                "source": "imported",
                "imported_at": "2025-11-18T10:30:00Z",
                "bundle_path": "/home/user/.skillmeat/bundles/abc123.zip",
            }
        }


class ArtifactPopularity(BaseModel):
    """Popular artifact statistics."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    deploy_count: int = Field(description="Number of times deployed")
    last_deployed: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last deployment",
    )


class BundleAnalyticsResponse(BaseModel):
    """Bundle analytics response."""

    bundle_id: str = Field(description="Bundle unique identifier")
    bundle_name: str = Field(description="Bundle name")
    total_downloads: int = Field(
        default=0,
        description="Total number of times bundle was downloaded/imported",
    )
    total_deploys: int = Field(
        default=0,
        description="Total deployments of artifacts from this bundle",
    )
    popular_artifacts: List[ArtifactPopularity] = Field(
        default_factory=list,
        description="Most deployed artifacts from this bundle (top 10)",
    )
    first_imported: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of first import",
    )
    last_used: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last artifact deployment",
    )
    active_projects: int = Field(
        default=0,
        description="Number of projects using artifacts from this bundle",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "bundle_id": "sha256:abc123def456...",
                "bundle_name": "python-essentials",
                "total_downloads": 15,
                "total_deploys": 42,
                "popular_artifacts": [
                    {
                        "artifact_name": "python-skill",
                        "artifact_type": "skill",
                        "deploy_count": 25,
                        "last_deployed": "2025-11-18T10:00:00Z",
                    }
                ],
                "first_imported": "2025-11-01T08:00:00Z",
                "last_used": "2025-11-18T10:00:00Z",
                "active_projects": 3,
            }
        }


class BundleDeleteResponse(BaseModel):
    """Response from bundle deletion."""

    success: bool = Field(description="Whether deletion succeeded")
    bundle_id: str = Field(description="Deleted bundle identifier")
    message: str = Field(description="Status message")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "bundle_id": "sha256:abc123def456...",
                "message": "Bundle deleted successfully",
            }
        }


# ====================
# Bundle Preview Schemas
# ====================


class PreviewArtifact(BaseModel):
    """Artifact information in preview."""

    name: str = Field(description="Artifact name")
    type: str = Field(description="Artifact type (skill, command, agent)")
    version: Optional[str] = Field(default=None, description="Artifact version")
    path: str = Field(description="Relative path in bundle")
    has_conflict: bool = Field(
        default=False,
        description="Whether this artifact conflicts with existing one",
    )
    existing_version: Optional[str] = Field(
        default=None,
        description="Version of existing artifact if conflict exists",
    )


class BundlePreviewCategorization(BaseModel):
    """Categorization of artifacts in bundle."""

    new_artifacts: int = Field(
        default=0,
        description="Number of artifacts that don't exist in collection",
    )
    existing_artifacts: int = Field(
        default=0,
        description="Number of artifacts that conflict with existing ones",
    )
    will_import: int = Field(
        default=0,
        description="Number of artifacts that will be imported (new)",
    )
    will_require_resolution: int = Field(
        default=0,
        description="Number of artifacts that will require conflict resolution",
    )


class BundlePreviewResponse(BaseModel):
    """Response from bundle preview operation."""

    is_valid: bool = Field(description="Whether bundle is valid")
    bundle_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of bundle",
    )
    metadata: Optional[BundleMetadataResponse] = Field(
        default=None,
        description="Bundle metadata from manifest",
    )
    artifacts: List[PreviewArtifact] = Field(
        default_factory=list,
        description="List of artifacts in bundle with conflict information",
    )
    categorization: BundlePreviewCategorization = Field(
        description="Categorization summary of artifacts"
    )
    validation_issues: List[ValidationIssueResponse] = Field(
        default_factory=list,
        description="Validation issues (errors and warnings)",
    )
    total_size_bytes: int = Field(
        default=0,
        description="Total bundle size in bytes",
    )
    collection_name: str = Field(
        description="Name of collection that would receive imports"
    )
    summary: str = Field(
        default="",
        description="Human-readable summary",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "is_valid": True,
                "bundle_hash": "sha256:abc123def456...",
                "metadata": {
                    "name": "python-essentials",
                    "description": "Essential Python development skills",
                    "author": "john.doe@example.com",
                    "created_at": "2025-11-16T12:00:00Z",
                    "version": "1.0.0",
                    "license": "MIT",
                    "tags": ["python", "development"],
                    "homepage": None,
                    "repository": None,
                },
                "artifacts": [
                    {
                        "name": "python-skill",
                        "type": "skill",
                        "version": "1.0.0",
                        "path": "skills/python-skill",
                        "has_conflict": False,
                        "existing_version": None,
                    },
                    {
                        "name": "existing-skill",
                        "type": "skill",
                        "version": "2.0.0",
                        "path": "skills/existing-skill",
                        "has_conflict": True,
                        "existing_version": "1.5.0",
                    },
                ],
                "categorization": {
                    "new_artifacts": 1,
                    "existing_artifacts": 1,
                    "will_import": 1,
                    "will_require_resolution": 1,
                },
                "validation_issues": [],
                "total_size_bytes": 1048576,
                "collection_name": "default",
                "summary": "Bundle contains 2 artifacts (1 new, 1 conflict)",
            }
        }


# ====================
# Bundle Export Schemas
# ====================


class BundleExportMetadata(BaseModel):
    """Metadata for bundle export."""

    name: str = Field(
        description="Bundle name (identifier, alphanumeric + dash/underscore)"
    )
    description: str = Field(description="Human-readable description")
    author: str = Field(description="Author name or email")
    version: str = Field(
        default="1.0.0", description="Bundle version (semver recommended)"
    )
    license: str = Field(default="MIT", description="License identifier")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    homepage: Optional[str] = Field(default=None, description="Project homepage URL")
    repository: Optional[str] = Field(default=None, description="Source repository URL")

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate bundle name format."""
        if not v or not isinstance(v, str):
            raise ValueError("Bundle name must be a non-empty string")
        if not all(c.isalnum() or c in ("-", "_") for c in v):
            raise ValueError(
                "Bundle name can only contain alphanumeric characters, dashes, and underscores"
            )
        return v


class BundleExportOptions(BaseModel):
    """Options for bundle export."""

    format: str = Field(
        default="zip",
        description="Bundle format (zip or tar.gz)",
    )
    generate_share_link: bool = Field(
        default=False,
        description="Generate shareable link for bundle",
    )
    permission_level: str = Field(
        default="view",
        description="Permission level for share link (view, download)",
    )
    link_expiration_hours: Optional[int] = Field(
        default=None,
        description="Hours until share link expires (None for no expiration)",
    )
    vault_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional vault storage configuration",
    )
    sign_bundle: bool = Field(
        default=False,
        description="Sign bundle with Ed25519 signature",
    )
    signing_key_id: Optional[str] = Field(
        default=None,
        description="Signing key ID (uses default if None and sign_bundle=True)",
    )

    @field_validator("format", mode="after")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate bundle format."""
        allowed = {"zip", "tar.gz"}
        if v not in allowed:
            raise ValueError(f"Format must be one of: {', '.join(allowed)}")
        return v

    @field_validator("permission_level", mode="after")
    @classmethod
    def validate_permission_level(cls, v: str) -> str:
        """Validate permission level."""
        allowed = {"view", "download"}
        if v not in allowed:
            raise ValueError(f"Permission level must be one of: {', '.join(allowed)}")
        return v


class BundleExportRequest(BaseModel):
    """Request to export artifacts as a bundle."""

    artifact_ids: List[str] = Field(
        description="List of artifact IDs to include (format: 'type::name')",
        min_length=1,
    )
    metadata: BundleExportMetadata = Field(description="Bundle metadata")
    options: BundleExportOptions = Field(
        default_factory=BundleExportOptions,
        description="Export options",
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Source collection (uses active if None)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_ids": [
                    "skill::python-debugger",
                    "command::pytest-helper",
                    "skill::code-formatter",
                ],
                "metadata": {
                    "name": "python-essentials",
                    "description": "Essential Python development tools",
                    "author": "john.doe@example.com",
                    "version": "1.0.0",
                    "license": "MIT",
                    "tags": ["python", "development", "productivity"],
                    "homepage": "https://github.com/johndoe/python-essentials",
                    "repository": "https://github.com/johndoe/python-essentials",
                },
                "options": {
                    "format": "zip",
                    "generate_share_link": True,
                    "permission_level": "download",
                    "link_expiration_hours": 24,
                    "sign_bundle": False,
                },
                "collection_name": None,
            }
        }


class BundleExportResponse(BaseModel):
    """Response from bundle export operation."""

    success: bool = Field(description="Whether export succeeded")
    bundle_id: str = Field(description="Bundle unique identifier (SHA-256 hash)")
    bundle_path: str = Field(description="Path to exported bundle file")
    download_url: str = Field(description="URL to download the bundle")
    share_link: Optional[str] = Field(
        default=None,
        description="Shareable link if generate_share_link was True",
    )
    stream_url: Optional[str] = Field(
        default=None,
        description="SSE stream URL for progress updates",
    )
    metadata: BundleMetadataResponse = Field(description="Bundle metadata")
    artifact_count: int = Field(description="Number of artifacts in bundle")
    total_size_bytes: int = Field(description="Total bundle size in bytes")
    warnings: List[str] = Field(
        default_factory=list,
        description="Warning messages",
    )
    export_time: datetime = Field(description="Timestamp of export operation")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "bundle_id": "sha256:abc123def456789012345678901234567890123456789012345678901234",
                "bundle_path": "/home/user/.skillmeat/bundles/python-essentials.skillmeat-pack",
                "download_url": "/api/bundles/sha256:abc123.../download",
                "share_link": "https://skillmeat.app/share/abc123xyz",
                "stream_url": None,
                "metadata": {
                    "name": "python-essentials",
                    "description": "Essential Python development tools",
                    "author": "john.doe@example.com",
                    "created_at": "2025-11-18T12:00:00Z",
                    "version": "1.0.0",
                    "license": "MIT",
                    "tags": ["python", "development", "productivity"],
                    "homepage": "https://github.com/johndoe/python-essentials",
                    "repository": "https://github.com/johndoe/python-essentials",
                },
                "artifact_count": 3,
                "total_size_bytes": 1048576,
                "warnings": [],
                "export_time": "2025-11-18T12:00:00Z",
            }
        }


# ====================
# Share Link Schemas
# ====================


class ShareLinkUpdateRequest(BaseModel):
    """Request to create or update a bundle share link."""

    permission_level: str = Field(
        default="viewer",
        description="Permission level for share link (viewer, importer, editor)",
    )
    expiration_hours: Optional[int] = Field(
        default=None,
        description="Hours until share link expires (None for no expiration)",
    )
    max_downloads: Optional[int] = Field(
        default=None,
        description="Maximum number of downloads allowed (None for unlimited)",
    )

    @field_validator("permission_level", mode="after")
    @classmethod
    def validate_permission_level(cls, v: str) -> str:
        """Validate permission level."""
        allowed = {"viewer", "importer", "editor"}
        if v not in allowed:
            raise ValueError(f"Permission level must be one of: {', '.join(allowed)}")
        return v

    @field_validator("expiration_hours", mode="after")
    @classmethod
    def validate_expiration_hours(cls, v: Optional[int]) -> Optional[int]:
        """Validate expiration hours is positive."""
        if v is not None and v <= 0:
            raise ValueError("Expiration hours must be positive")
        return v

    @field_validator("max_downloads", mode="after")
    @classmethod
    def validate_max_downloads(cls, v: Optional[int]) -> Optional[int]:
        """Validate max downloads is positive."""
        if v is not None and v <= 0:
            raise ValueError("Max downloads must be positive")
        return v

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "permission_level": "importer",
                "expiration_hours": 24,
                "max_downloads": 10,
            }
        }


class ShareLinkResponse(BaseModel):
    """Response for share link creation/update."""

    success: bool = Field(description="Whether operation succeeded")
    bundle_id: str = Field(description="Bundle unique identifier")
    url: str = Field(description="Full shareable URL")
    short_url: str = Field(description="Short URL for easier sharing")
    qr_code: Optional[str] = Field(
        default=None,
        description="QR code as data URL (optional)",
    )
    permission_level: str = Field(description="Permission level for this link")
    expires_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when link expires (None if no expiration)",
    )
    max_downloads: Optional[int] = Field(
        default=None,
        description="Maximum downloads allowed (None if unlimited)",
    )
    download_count: int = Field(
        default=0,
        description="Current number of downloads",
    )
    created_at: str = Field(description="ISO 8601 timestamp when link was created")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "bundle_id": "sha256:abc123def456789012345678901234567890123456789012345678901234",
                "url": "https://skillmeat.app/share/abc123xyz",
                "short_url": "https://sm.app/abc123",
                "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA...",
                "permission_level": "importer",
                "expires_at": "2025-11-19T12:00:00Z",
                "max_downloads": 10,
                "download_count": 3,
                "created_at": "2025-11-18T12:00:00Z",
            }
        }


class ShareLinkDeleteResponse(BaseModel):
    """Response for share link deletion/revocation."""

    success: bool = Field(description="Whether deletion succeeded")
    bundle_id: str = Field(description="Bundle unique identifier")
    message: str = Field(description="Status message")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "bundle_id": "sha256:abc123def456789012345678901234567890123456789012345678901234",
                "message": "Share link revoked successfully",
            }
        }
