"""Pydantic schemas for SkillBOM API endpoints and serialisation.

Defines request/response models for BOM generation, attestation records,
and artifact history events.  All schemas include ORM-mode support via
``model_config = ConfigDict(from_attributes=True)``.

Schema Groups:
    - BOM: ArtifactEntrySchema, BomMetadataSchema, BomSchema
    - Attestation: AttestationSchema
    - History: HistoryEventSchema
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# BOM Schemas
# =============================================================================


class ArtifactEntrySchema(BaseModel):
    """Single artifact entry within a BOM.

    Represents one artifact included in the Bill of Materials.  All 13+
    artifact types are covered through the flexible ``metadata`` dict.
    Composite and deployment-set types include an optional ``members`` list.
    """

    name: str = Field(description="Artifact name (unique within type)")
    type: str = Field(description="Artifact type string (e.g. 'skill', 'command')")
    source: Optional[str] = Field(
        default=None,
        description="Source identifier (GitHub path or local path)",
    )
    version: Optional[str] = Field(
        default=None,
        description="Deployed or upstream version string",
    )
    content_hash: str = Field(
        description="SHA-256 hex digest of artifact content, or '' if unavailable",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Per-type metadata dict (author, description, tags, mime_type, etc.)",
    )
    members: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Child member list for composite/deployment_set types",
    )

    model_config = ConfigDict(from_attributes=True)


class BomMetadataSchema(BaseModel):
    """Metadata block included in every BOM response.

    Captures provenance information about the BOM generation run: version
    strings, timestamps, counts, and performance metrics.
    """

    schema_version: str = Field(
        description="BOM schema version (semver, e.g. '1.0.0')",
    )
    generator: str = Field(
        default="skillmeat-bom",
        description="Generator identifier",
    )
    generated_at: str = Field(
        description="ISO-8601 UTC timestamp when the BOM was generated",
    )
    artifact_count: int = Field(
        ge=0,
        description="Total number of artifact entries in this BOM",
    )
    elapsed_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock time in milliseconds for BOM generation",
    )
    project_path: Optional[str] = Field(
        default=None,
        description="Resolved project root path, if provided at generation time",
    )

    model_config = ConfigDict(from_attributes=True)


class BomSchema(BaseModel):
    """Full Bill of Materials document.

    Top-level response schema returned by BOM generation endpoints.
    Contains the metadata block and the full list of artifact entries.
    """

    schema_version: str = Field(
        description="BOM schema version (semver, e.g. '1.0.0')",
    )
    generated_at: str = Field(
        description="ISO-8601 UTC timestamp when the BOM was generated",
    )
    project_path: Optional[str] = Field(
        default=None,
        description="Resolved project root path, if provided at generation time",
    )
    artifact_count: int = Field(
        ge=0,
        description="Total number of artifact entries",
    )
    artifacts: List[ArtifactEntrySchema] = Field(
        default_factory=list,
        description="Artifact entries sorted by (type, name)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generator metadata (generator name, elapsed_ms, etc.)",
    )

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Attestation Schema
# =============================================================================


class AttestationSchema(BaseModel):
    """Attestation record linking an artifact to an owner with RBAC metadata.

    Maps to the ``attestation_records`` table.  Captures who attested an
    artifact and under what roles/scopes/visibility policy.
    """

    id: str = Field(description="Attestation record UUID hex")
    artifact_id: str = Field(
        description="Artifact identifier in 'type:name' format",
    )
    owner_type: str = Field(
        description="Owner entity type (e.g. 'user', 'team', 'org')",
    )
    owner_id: str = Field(
        description="Owner entity identifier",
    )
    roles: List[str] = Field(
        default_factory=list,
        description="RBAC roles granted to this attestation",
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="Permission scopes covered by this attestation",
    )
    visibility: str = Field(
        default="private",
        description="Visibility policy: 'private', 'org', or 'public'",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when attestation was created",
    )

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# History Event Schema
# =============================================================================


# =============================================================================
# IDP BOM Card Schema
# =============================================================================


class BomCardArtifactEntry(BaseModel):
    """Lightweight artifact summary for Backstage BOM card consumption.

    Omits heavy metadata fields to keep the IDP payload compact and fast
    to parse in Backstage backend/scaffolder actions.
    """

    name: str = Field(description="Artifact name (unique within type)")
    type: str = Field(description="Artifact type string (e.g. 'skill', 'command')")
    version: Optional[str] = Field(
        default=None,
        description="Deployed or upstream version string",
    )
    content_hash: str = Field(
        description="SHA-256 hex digest of artifact content, or '' if unavailable",
    )

    model_config = ConfigDict(from_attributes=True)


class BomCardResponse(BaseModel):
    """Backstage-renderable BOM payload for IDP catalog/backend consumers.

    A lightweight summary of the latest BOM snapshot for a project.
    Intended for use by Backstage software-catalog plugins and scaffolder
    actions that need artifact inventory metadata without the full BOM JSON.
    """

    project_id: str = Field(description="Project identifier")
    snapshot_id: int = Field(description="Primary key of the BOM snapshot row")
    generated_at: str = Field(
        description="ISO-8601 UTC timestamp when the snapshot was captured",
    )
    artifact_count: int = Field(
        ge=0,
        description="Total number of artifacts in this snapshot",
    )
    artifacts: List[BomCardArtifactEntry] = Field(
        default_factory=list,
        description="Lightweight artifact summaries from the snapshot",
    )
    signature_status: str = Field(
        description="'signed' if the snapshot carries a cryptographic signature, 'unsigned' otherwise",
    )
    attestation_count: int = Field(
        ge=0,
        description="Number of AttestationRecord rows linked to artifacts in this snapshot",
    )

    model_config = ConfigDict(from_attributes=True)


class HistoryEventSchema(BaseModel):
    """Artifact history/activity event record.

    Maps to the ``artifact_history_events`` table.  Each row captures a
    single change event for an artifact, including a JSON diff and the
    content hash after the change.
    """

    id: str = Field(description="History event UUID hex")
    artifact_id: str = Field(
        description="Artifact identifier in 'type:name' format",
    )
    event_type: str = Field(
        description="Event type string (e.g. 'created', 'updated', 'deployed', 'deleted')",
    )
    actor_id: Optional[str] = Field(
        default=None,
        description="Identifier of the actor who triggered the event",
    )
    owner_type: Optional[str] = Field(
        default=None,
        description="Owner entity type context for this event",
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp of the event",
    )
    diff_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON representation of changes made in this event",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 content hash of the artifact after this event",
    )

    model_config = ConfigDict(from_attributes=True)
