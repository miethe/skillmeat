"""Pydantic schemas for bundle import/export API endpoints.

Defines request and response models for bundle operations.
"""

from datetime import datetime
from typing import List, Optional

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

    @field_validator("strategy")
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
    category: str = Field(description="Issue category (security, schema, integrity, size)")
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
