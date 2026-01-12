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
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA256 content hash of the artifact for deduplication",
        examples=["abc123def456789..."],
    )
    collection_match: Optional["CollectionMatch"] = Field(
        default=None,
        description=(
            "Hash-based collection matching result. Populated when collection "
            "context is provided during discovery. Shows if artifact content "
            "matches an existing collection artifact."
        ),
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
                "content_hash": "a1b2c3d4e5f6...",
                "collection_match": {
                    "type": "exact",
                    "matched_artifact_id": "skill:canvas-design",
                    "matched_name": "canvas-design",
                    "confidence": 1.0,
                },
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
    skip_list: Optional[List[str]] = Field(
        default=None,
        description="List of artifact keys to mark as skipped (format: type:name)",
        examples=[["skill:canvas-design", "command:my-command"]],
    )
    apply_path_tags: bool = Field(
        default=True,
        description=(
            "Apply approved path-based tags to imported artifacts. "
            "If true, segments with status='approved' in entry.path_segments "
            "will be created/found and linked as tags to the imported artifact."
        ),
        examples=[True],
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
                "skip_list": ["skill:existing-skill"],
                "apply_path_tags": True,
            }
        }
    }


class ImportStatus(str, Enum):
    """Status of an artifact import operation."""

    SUCCESS = "success"  # Artifact was successfully imported
    SKIPPED = "skipped"  # Artifact already exists in Collection/Project
    FAILED = "failed"  # Import failed due to error


class ErrorReasonCode(str, Enum):
    """Reason codes for import failures and skips.

    These codes provide machine-readable reasons for why an artifact
    was skipped or failed during bulk import, enabling frontend
    error handling and reporting.
    """

    # Validation errors
    INVALID_STRUCTURE = "invalid_structure"  # Artifact directory structure invalid
    YAML_PARSE_ERROR = "yaml_parse_error"  # YAML frontmatter parsing failed
    MISSING_METADATA = "missing_metadata"  # Required metadata files missing
    INVALID_TYPE = "invalid_type"  # Invalid artifact type specified
    INVALID_SOURCE = "invalid_source"  # Invalid source format

    # Import errors
    IMPORT_ERROR = "import_error"  # Generic import failure
    NETWORK_ERROR = "network_error"  # Failed to fetch from GitHub
    PERMISSION_ERROR = "permission_error"  # Filesystem permission denied
    IO_ERROR = "io_error"  # File I/O operation failed

    # Skip reasons
    ALREADY_EXISTS = "already_exists"  # Artifact already exists in target
    IN_SKIP_LIST = "in_skip_list"  # Artifact is in user's skip list
    DUPLICATE = "duplicate"  # Duplicate in current batch


class ImportResult(BaseModel):
    """Result for a single imported artifact."""

    artifact_id: str = Field(
        ...,
        description="ID of the artifact (type:name)",
        examples=["skill:canvas-design"],
    )
    path: Optional[str] = Field(
        default=None,
        description="Path to the artifact (for local imports)",
        examples=["/Users/me/.claude/skills/canvas-design"],
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
    reason_code: Optional[ErrorReasonCode] = Field(
        default=None,
        description=(
            "Machine-readable reason code for failures/skips. "
            "Use this for programmatic error handling."
        ),
        examples=[ErrorReasonCode.YAML_PARSE_ERROR],
    )
    skip_reason: Optional[str] = Field(
        default=None,
        description="Reason artifact was skipped (if status=skipped)",
        examples=["Artifact already exists in collection"],
    )
    details: Optional[str] = Field(
        default=None,
        description=(
            "Additional details about the error, such as line numbers "
            "for YAML parse errors or specific validation failures."
        ),
        examples=["Line 5: expected ':' but found '-'"],
    )
    tags_applied: int = Field(
        default=0,
        description=(
            "Number of path-based tags applied to this artifact during import. "
            "Only non-zero when apply_path_tags=True and approved segments exist."
        ),
        ge=0,
        examples=[3],
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "artifact_id": "skill:canvas-design",
                "path": "/Users/me/.claude/skills/canvas-design",
                "status": "success",
                "message": "Artifact 'canvas-design' imported successfully",
                "error": None,
                "reason_code": None,
                "skip_reason": None,
                "details": None,
                "tags_applied": 3,
            }
        },
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
    total_tags_applied: int = Field(
        default=0,
        description=(
            "Total number of path-based tags applied across all artifacts. "
            "Sum of tags_applied from all ImportResult entries."
        ),
        ge=0,
        examples=[15],
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
                "total_tags_applied": 15,
                "results": [
                    {
                        "artifact_id": "skill:canvas-design",
                        "status": "success",
                        "message": "Artifact 'canvas-design' imported successfully",
                        "error": None,
                        "skip_reason": None,
                        "tags_applied": 3,
                    },
                    {
                        "artifact_id": "skill:existing-skill",
                        "status": "skipped",
                        "message": "Artifact already exists",
                        "error": None,
                        "skip_reason": "Artifact already exists in collection",
                        "tags_applied": 0,
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


# ===========================
# Skip Preference Schemas
# ===========================


class SkipPreferenceResponse(BaseModel):
    """Response containing a skip preference."""

    artifact_key: str = Field(
        ...,
        description="Artifact identifier in format 'type:name'",
        examples=["skill:canvas-design"],
    )
    skip_reason: str = Field(
        ...,
        description="Human-readable reason for skipping this artifact",
        examples=["Already in collection"],
    )
    added_date: datetime = Field(
        ...,
        description="When this skip preference was added (ISO 8601 format)",
        examples=["2025-12-04T10:00:00Z"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifact_key": "skill:canvas-design",
                "skip_reason": "Already in collection",
                "added_date": "2025-12-04T10:00:00Z",
            }
        }
    }


class SkipPreferenceListResponse(BaseModel):
    """Response containing list of skip preferences."""

    skips: List[SkipPreferenceResponse] = Field(
        default_factory=list,
        description="List of skip preferences for this project",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "skips": [
                    {
                        "artifact_key": "skill:canvas-design",
                        "skip_reason": "Already in collection",
                        "added_date": "2025-12-04T10:00:00Z",
                    },
                    {
                        "artifact_key": "command:my-command",
                        "skip_reason": "Not needed for this project",
                        "added_date": "2025-12-04T11:00:00Z",
                    },
                ]
            }
        }
    }


class SkipClearResponse(BaseModel):
    """Response from clearing skip preferences."""

    success: bool = Field(
        ...,
        description="Whether clear operation succeeded",
        examples=[True],
    )
    cleared_count: int = Field(
        ...,
        description="Number of skip preferences that were cleared",
        ge=0,
        examples=[5],
    )
    message: str = Field(
        ...,
        description="Human-readable result message",
        examples=["Cleared 5 skip preferences"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "cleared_count": 5,
                "message": "Cleared 5 skip preferences",
            }
        }
    }


class SkipPreferenceAddRequest(BaseModel):
    """Request to add a skip preference."""

    artifact_key: str = Field(
        ...,
        description="Artifact identifier in format 'type:name'",
        examples=["skill:canvas-design"],
        min_length=3,
    )
    skip_reason: str = Field(
        ...,
        description="Human-readable reason for skipping this artifact",
        examples=["Already have it"],
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifact_key": "skill:canvas-design",
                "skip_reason": "Already in collection",
            }
        }
    }


# ===========================
# Collection Membership Schemas
# ===========================


class MatchType(str, Enum):
    """Type of match when checking collection membership."""

    EXACT = "exact"  # Exact source_link match
    HASH = "hash"  # Content hash match
    NAME_TYPE = "name_type"  # Name + type match
    NONE = "none"  # No match found


class CollectionStatus(BaseModel):
    """Collection membership status for a discovered artifact.

    Provides detailed information about whether an artifact exists
    in the collection and how it was matched.
    """

    in_collection: bool = Field(
        ...,
        description="Whether the artifact exists in the collection",
        examples=[True],
    )
    match_type: MatchType = Field(
        ...,
        description=(
            "How the artifact was matched: "
            "'exact' (source_link match), "
            "'hash' (content hash match), "
            "'name_type' (name + type match), "
            "'none' (no match)"
        ),
        examples=[MatchType.EXACT],
    )
    matched_artifact_id: Optional[str] = Field(
        default=None,
        description="ID of the matched artifact in collection (format: type:name)",
        examples=["skill:canvas-design"],
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "in_collection": True,
                "match_type": "exact",
                "matched_artifact_id": "skill:canvas-design",
            }
        },
    )


class CollectionMatch(BaseModel):
    """Hash-based collection matching result for a discovered artifact.

    Provides detailed information about how an artifact matches against
    the collection using content hash and name+type matching.

    Attributes:
        type: Type of match found:
            - "exact": Content hash exact match (confidence: 1.0)
            - "hash": Legacy alias for exact hash match (confidence: 1.0)
            - "name_type": Name and type match but different content (confidence: 0.85)
            - "none": No match found (confidence: 0.0)
        matched_artifact_id: ID of matched artifact if found (format: type:name)
        matched_name: Name of the matched artifact
        confidence: Confidence score (0.0-1.0) indicating match quality
    """

    type: str = Field(
        ...,
        description=(
            "Match type: 'exact' (hash match, 1.0 confidence), "
            "'hash' (alias for exact), 'name_type' (0.85 confidence), "
            "'none' (no match, 0.0 confidence)"
        ),
        examples=["exact"],
    )
    matched_artifact_id: Optional[str] = Field(
        default=None,
        description="ID of matched artifact in collection (format: type:name)",
        examples=["skill:canvas-design"],
    )
    matched_name: Optional[str] = Field(
        default=None,
        description="Name of the matched artifact",
        examples=["canvas-design"],
    )
    confidence: float = Field(
        ...,
        description="Confidence score from 0.0 (no match) to 1.0 (exact hash match)",
        ge=0.0,
        le=1.0,
        examples=[1.0],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "exact",
                "matched_artifact_id": "skill:canvas-design",
                "matched_name": "canvas-design",
                "confidence": 1.0,
            }
        },
    )


# ===========================
# Duplicate Confirmation Schemas
# ===========================


class DuplicateDecisionAction(str, Enum):
    """Action to take for a duplicate match."""

    LINK = "link"  # Link discovered artifact to existing collection artifact
    SKIP = "skip"  # Skip this artifact (do nothing)


class DuplicateMatch(BaseModel):
    """A single duplicate match decision from the user.

    Represents the user's decision to link a discovered artifact
    to an existing artifact in their collection.
    """

    discovered_path: str = Field(
        ...,
        description="Full filesystem path to the discovered artifact",
        examples=["/Users/me/.claude/skills/my-canvas"],
    )
    collection_artifact_id: str = Field(
        ...,
        description="ID of the matching collection artifact (format: type:name)",
        examples=["skill:canvas-design"],
    )
    action: DuplicateDecisionAction = Field(
        default=DuplicateDecisionAction.LINK,
        description="Action to take: 'link' to create association, 'skip' to ignore",
        examples=[DuplicateDecisionAction.LINK],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "discovered_path": "/Users/me/.claude/skills/my-canvas",
                "collection_artifact_id": "skill:canvas-design",
                "action": "link",
            }
        }
    }


class ConfirmDuplicatesRequest(BaseModel):
    """Request to process duplicate review decisions.

    Handles three types of decisions:
    1. matches: Duplicates to link to existing collection artifacts
    2. new_artifacts: Paths to import as new artifacts
    3. skipped: Paths the user chose to skip
    """

    project_path: str = Field(
        ...,
        description="Base64-encoded or absolute path to the project being scanned",
        examples=["/Users/me/myproject"],
    )
    matches: List[DuplicateMatch] = Field(
        default_factory=list,
        description="Duplicate artifacts to link to collection entries",
    )
    new_artifacts: List[str] = Field(
        default_factory=list,
        description="Filesystem paths of artifacts to import as new",
        examples=[["/Users/me/.claude/skills/new-skill"]],
    )
    skipped: List[str] = Field(
        default_factory=list,
        description="Filesystem paths of artifacts the user chose to skip",
        examples=[["/Users/me/.claude/skills/unwanted-skill"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_path": "/Users/me/myproject",
                "matches": [
                    {
                        "discovered_path": "/Users/me/.claude/skills/my-canvas",
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "link",
                    }
                ],
                "new_artifacts": ["/Users/me/.claude/skills/new-skill"],
                "skipped": ["/Users/me/.claude/skills/unwanted-skill"],
            }
        }
    }


class ConfirmDuplicatesStatus(str, Enum):
    """Status of duplicate confirmation operation."""

    SUCCESS = "success"  # All operations completed successfully
    PARTIAL = "partial"  # Some operations succeeded, some failed
    FAILED = "failed"  # All operations failed


class ConfirmDuplicatesResponse(BaseModel):
    """Response from processing duplicate review decisions.

    Provides summary counts and status of all operations performed.
    """

    status: ConfirmDuplicatesStatus = Field(
        ...,
        description="Overall status: 'success', 'partial', or 'failed'",
        examples=[ConfirmDuplicatesStatus.SUCCESS],
    )
    linked_count: int = Field(
        ...,
        description="Number of artifacts successfully linked to collection entries",
        ge=0,
        examples=[3],
    )
    imported_count: int = Field(
        ...,
        description="Number of new artifacts successfully imported",
        ge=0,
        examples=[2],
    )
    skipped_count: int = Field(
        ...,
        description="Number of artifacts marked as skipped",
        ge=0,
        examples=[1],
    )
    message: str = Field(
        ...,
        description="Human-readable summary message",
        examples=["Processed 6 artifacts: 3 linked, 2 imported, 1 skipped"],
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of when the operation completed",
        examples=["2025-01-09T10:30:00Z"],
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages for failed operations",
        examples=[["Failed to import /path/to/artifact: permission denied"]],
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "linked_count": 3,
                "imported_count": 2,
                "skipped_count": 1,
                "message": "Processed 6 artifacts: 3 linked, 2 imported, 1 skipped",
                "timestamp": "2025-01-09T10:30:00Z",
                "errors": [],
            }
        },
    )


# =============================================================================
# Forward Reference Resolution
# =============================================================================
# Rebuild models that have forward references to classes defined later in the file
# This must be done after all referenced classes are defined

DiscoveredArtifact.model_rebuild()  # References CollectionMatch
