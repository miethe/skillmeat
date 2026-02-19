"""Pydantic DTOs for artifact association (composite membership) endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssociationItemDTO(BaseModel):
    """Single association edge between two artifacts.

    Represents one row from the ``composite_memberships`` table, enriched
    with basic metadata about the related artifact so callers don't need a
    second round-trip.

    Attributes:
        artifact_id: ``type:name`` identifier of the related artifact
            (the parent composite for items in ``parents``, or the child
            artifact for items in ``children``).
        artifact_name: Human-readable name component extracted from
            ``artifact_id`` (e.g. ``"my-plugin"`` from
            ``"composite:my-plugin"``).
        artifact_type: Type component extracted from ``artifact_id``
            (e.g. ``"composite"``, ``"skill"``).
        relationship_type: Semantic label for the membership edge
            (default ``"contains"``; reserved for future graph queries).
        pinned_version_hash: Optional content hash locking the child to a
            specific snapshot; ``None`` means track latest.
        created_at: UTC timestamp when this membership was created.
    """

    artifact_id: str = Field(description="type:name identifier of the related artifact")
    artifact_name: str = Field(description="Name component extracted from artifact_id")
    artifact_type: str = Field(description="Type component extracted from artifact_id")
    relationship_type: str = Field(
        description='Semantic edge label (e.g. "contains")',
    )
    pinned_version_hash: Optional[str] = Field(
        default=None,
        description="Content hash pinning the child to a specific snapshot",
    )
    created_at: datetime = Field(
        description="UTC timestamp when this membership was created"
    )

    model_config = ConfigDict(from_attributes=True)


class AssociationsDTO(BaseModel):
    """All parent and child associations for a single artifact.

    Attributes:
        artifact_id: The ``type:name`` identifier of the queried artifact.
        parents: Composite artifacts that contain this artifact as a child
            (reverse lookup).  Empty when the artifact belongs to no
            composite.
        children: Child artifacts that this composite contains.  Empty when
            ``artifact_id`` is not a composite or has no members.
    """

    artifact_id: str = Field(description="type:name identifier of the queried artifact")
    parents: List[AssociationItemDTO] = Field(
        description="Composites that contain this artifact as a child"
    )
    children: List[AssociationItemDTO] = Field(
        description="Child artifacts that this composite contains"
    )

    model_config = ConfigDict(from_attributes=True)
