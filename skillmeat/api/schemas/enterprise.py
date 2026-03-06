"""Pydantic schemas for enterprise API endpoints.

Defines request and response models for enterprise artifact download operations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ArtifactFileEntry(BaseModel):
    """A single file within an artifact payload bundle.

    Attributes
    ----------
    path:
        Relative POSIX path of the file within the artifact directory.
    content:
        File contents — UTF-8 text or base64-encoded bytes for binary files.
    size:
        File size in bytes.
    encoding:
        ``"utf-8"`` for text files, ``"base64"`` for binary files.
    """

    path: str = Field(description="Relative POSIX path within the artifact directory")
    content: str = Field(
        description="File contents (UTF-8 text or base64-encoded for binary files)"
    )
    size: int = Field(description="File size in bytes", ge=0)
    encoding: str = Field(
        description='Content encoding: "utf-8" for text files, "base64" for binary',
        examples=["utf-8", "base64"],
    )


class ArtifactMetadata(BaseModel):
    """Metadata describing an enterprise artifact.

    Attributes
    ----------
    name:
        Human-readable artifact name (e.g. ``"canvas-design"``).
    type:
        Artifact type string (e.g. ``"skill"``, ``"command"``).
    source:
        Optional upstream source URL or identifier.
    """

    name: str = Field(description="Human-readable artifact name")
    type: str = Field(
        description="Artifact type (e.g. skill, command, agent, composite)",
        examples=["skill", "command", "agent", "composite"],
    )
    source: Optional[str] = Field(
        default=None,
        description="Upstream source URL or identifier, if available",
    )


class ArtifactDownloadResponse(BaseModel):
    """Response payload for the enterprise artifact download endpoint.

    Returned by ``GET /api/v1/artifacts/{artifact_id}/download`` when
    ``compress=False`` (default).  When ``compress=True`` the endpoint
    returns raw ``application/gzip`` bytes instead.

    Attributes
    ----------
    artifact_id:
        UUID string identifying the artifact in the enterprise DB.
    version:
        Resolved version tag (e.g. ``"v1.2.0"``), or ``"unknown"`` when
        no version rows exist.
    content_hash:
        SHA-256 hex digest of the artifact files at the resolved version,
        or an empty string when unavailable.
    metadata:
        Structured artifact metadata (name, type, source).
    files:
        Ordered list of file entries comprising the artifact bundle.
    """

    artifact_id: str = Field(description="UUID identifying the artifact")
    version: Optional[str] = Field(
        default=None,
        description='Resolved version tag, or "unknown" when no versions exist',
        examples=["v1.2.0", "latest", "unknown"],
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hex digest of the artifact at the resolved version",
    )
    metadata: ArtifactMetadata = Field(description="Artifact metadata")
    files: List[ArtifactFileEntry] = Field(
        description="Ordered list of files comprising the artifact bundle"
    )
