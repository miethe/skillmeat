"""Domain Data Transfer Objects for SkillMeat's hexagonal architecture.

Pure Python dataclasses that carry data across layer boundaries without leaking
ORM models (SQLAlchemy) or API framework types (Pydantic) into the core.

Design invariants:
- No Pydantic, no SQLAlchemy — stdlib only.
- Only allowed skillmeat import: ``skillmeat.core.enums``.
- All optional fields default to ``None``; list fields default to ``[]``.
- Dates are stored as ISO-8601 strings so the core stays timezone-naive.
- DTOs are frozen to enforce immutability at the layer boundary.
- Each DTO exposes a ``from_dict`` classmethod for convenient construction
  from plain dicts (e.g. repository query results, JSON payloads).

Usage::

    from skillmeat.core.interfaces import ArtifactDTO, ProjectDTO

    artifact = ArtifactDTO.from_dict(row)
    project  = ProjectDTO(id="abc", name="my-project", path="/home/user/proj")
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Self compat shim: typing.Self was added in Python 3.11; use the backport
# from typing_extensions on older interpreters.
# ---------------------------------------------------------------------------
if sys.version_info >= (3, 11):
    from typing import Self
else:
    try:
        from typing_extensions import Self
    except ImportError:  # typing_extensions not installed — define a fallback
        from typing import TypeVar as _TypeVar

        Self = _TypeVar("Self")  # type: ignore[assignment,misc]


__all__ = [
    "ArtifactDTO",
    "ProjectDTO",
    "CollectionDTO",
    "DeploymentDTO",
    "TagDTO",
    "SettingsDTO",
    "CollectionMembershipDTO",
    "EntityTypeConfigDTO",
    "CategoryDTO",
]


# =============================================================================
# ArtifactDTO
# =============================================================================


@dataclass(frozen=True)
class ArtifactDTO:
    """Lightweight representation of a cached artifact.

    Maps from the ``Artifact`` ORM model.  All mutable collections are
    represented as tuples to preserve the frozen contract.

    Attributes:
        id: Primary-key string in ``"type:name"`` format.
        uuid: Stable cross-context UUID (hex, 32 chars).
        name: Human-readable artifact name.
        artifact_type: Artifact category (skill, command, agent, …).
        source: Upstream source spec (e.g. ``"github:owner/repo/path"``).
        version: Resolved version string at the time of caching.
        scope: Deployment scope (user / local).
        description: Short human-readable description.
        content_path: Filesystem path to the artifact content.
        metadata: Arbitrary key/value metadata from YAML frontmatter.
        tags: Tag name strings associated with this artifact.
        is_outdated: True when an upstream update is available.
        local_modified: True when local edits have been detected.
        project_id: ID of the project that owns this artifact entry.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    artifact_type: str
    uuid: str | None = None
    source: str | None = None
    version: str | None = None
    scope: str | None = None
    description: str | None = None
    content_path: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    is_outdated: bool = False
    local_modified: bool = False
    project_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct an ArtifactDTO from a plain dictionary.

        Unknown keys are silently ignored so callers can pass raw ORM
        ``to_dict()`` output without pre-filtering.

        Args:
            data: Mapping that contains at minimum ``id``, ``name``, and
                ``artifact_type`` (or ``type`` as an alias).

        Returns:
            A fully populated :class:`ArtifactDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            # Accept both "artifact_type" (DTO convention) and "type" (ORM column)
            artifact_type=data.get("artifact_type") or data.get("type") or "",
            uuid=data.get("uuid"),
            source=data.get("source"),
            version=data.get("deployed_version") or data.get("version"),
            scope=data.get("scope"),
            description=data.get("description"),
            content_path=data.get("content_path"),
            metadata=dict(data.get("metadata") or {}),
            tags=list(data.get("tags") or []),
            is_outdated=bool(data.get("is_outdated", False)),
            local_modified=bool(data.get("local_modified", False)),
            project_id=data.get("project_id"),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# ProjectDTO
# =============================================================================


@dataclass(frozen=True)
class ProjectDTO:
    """Lightweight representation of a cached project.

    Maps from the ``Project`` ORM model.

    Attributes:
        id: Base64-encoded project path (primary key).
        name: Project directory name.
        path: Absolute filesystem path.
        description: Optional project description.
        status: Project cache status (active / stale / error).
        artifact_count: Number of artifacts deployed to this project.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        last_fetched: ISO-8601 timestamp of most-recent cache refresh.
    """

    id: str
    name: str
    path: str
    description: str | None = None
    status: str = "active"
    artifact_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    last_fetched: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a ProjectDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``name``,
                and ``path``.

        Returns:
            A fully populated :class:`ProjectDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            description=data.get("description"),
            status=data.get("status", "active"),
            artifact_count=int(data.get("artifact_count", 0)),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
            last_fetched=_to_iso(data.get("last_fetched")),
        )


# =============================================================================
# CollectionDTO
# =============================================================================


@dataclass(frozen=True)
class CollectionDTO:
    """Lightweight representation of an artifact collection.

    A collection is a named set of artifacts managed by the user.

    Attributes:
        id: Collection unique identifier (usually the collection name).
        name: Human-readable collection name.
        path: Absolute filesystem path to the collection directory.
        version: Collection format version string.
        artifact_count: Number of artifacts in this collection.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    path: str | None = None
    version: str = "1.0.0"
    artifact_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a CollectionDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id`` and ``name``.

        Returns:
            A fully populated :class:`CollectionDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            path=data.get("path"),
            version=data.get("version", "1.0.0"),
            artifact_count=int(data.get("artifact_count", 0)),
            created_at=_to_iso(data.get("created_at") or data.get("created")),
            updated_at=_to_iso(data.get("updated_at") or data.get("updated")),
        )


# =============================================================================
# DeploymentDTO
# =============================================================================


@dataclass(frozen=True)
class DeploymentDTO:
    """Lightweight representation of a single artifact deployment.

    Captures the result of deploying an artifact from a collection to a
    project directory.

    Attributes:
        id: Deployment record identifier (often ``"type:name"``).
        artifact_id: Identifier of the deployed artifact.
        artifact_name: Human-readable artifact name.
        artifact_type: Artifact category (skill, command, …).
        project_id: Identifier of the target project.
        project_path: Absolute filesystem path to the target project.
        project_name: Display name of the target project.
        from_collection: Source collection name.
        scope: Deployment scope (user / local).
        status: Current deployment status string.
        deployed_at: ISO-8601 timestamp when the deployment occurred.
        source_path: Filesystem path of the artifact in the collection.
        target_path: Filesystem path where the artifact was deployed.
        collection_sha: Content hash at deployment time.
        local_modifications: True when post-deploy edits have been detected.
        deployment_profile_id: Profile identifier used for this deployment.
        platform: Target platform string.
    """

    id: str
    artifact_id: str
    artifact_name: str
    artifact_type: str
    project_id: str | None = None
    project_path: str | None = None
    project_name: str | None = None
    from_collection: str | None = None
    scope: str | None = None
    status: str = "deployed"
    deployed_at: str | None = None
    source_path: str | None = None
    target_path: str | None = None
    collection_sha: str | None = None
    local_modifications: bool = False
    deployment_profile_id: str | None = None
    platform: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a DeploymentDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``artifact_id``,
                ``artifact_name``, and ``artifact_type``.

        Returns:
            A fully populated :class:`DeploymentDTO`.
        """
        return cls(
            id=data["id"],
            artifact_id=data["artifact_id"],
            artifact_name=data.get("artifact_name", ""),
            artifact_type=data.get("artifact_type", ""),
            project_id=data.get("project_id"),
            project_path=data.get("project_path"),
            project_name=data.get("project_name"),
            from_collection=data.get("from_collection"),
            scope=data.get("scope"),
            status=data.get("status", "deployed"),
            deployed_at=_to_iso(data.get("deployed_at")),
            source_path=data.get("source_path"),
            target_path=data.get("target_path") or data.get("deployed_path"),
            collection_sha=data.get("collection_sha") or data.get("content_hash"),
            local_modifications=bool(data.get("local_modifications", False)),
            deployment_profile_id=data.get("deployment_profile_id"),
            platform=data.get("platform"),
        )


# =============================================================================
# TagDTO
# =============================================================================


@dataclass(frozen=True)
class TagDTO:
    """Lightweight representation of an artifact tag.

    Attributes:
        id: Tag unique identifier.
        name: Human-readable tag name.
        slug: URL-friendly kebab-case slug.
        color: Optional hex color code (e.g. ``"#FF5733"``).
        artifact_count: Number of artifacts carrying this tag.
        deployment_set_count: Number of deployment sets carrying this tag.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    slug: str
    color: str | None = None
    artifact_count: int = 0
    deployment_set_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a TagDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``name``,
                and ``slug``.

        Returns:
            A fully populated :class:`TagDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            slug=data["slug"],
            color=data.get("color"),
            artifact_count=int(data.get("artifact_count") or 0),
            deployment_set_count=int(data.get("deployment_set_count") or 0),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# SettingsDTO
# =============================================================================


@dataclass(frozen=True)
class SettingsDTO:
    """Application-level settings snapshot.

    Carries the current user configuration for consumption by routers and
    services without exposing the underlying config manager or Pydantic models.

    Attributes:
        github_token: Configured GitHub Personal Access Token (masked or raw).
        collection_path: Absolute path to the user's artifact collection.
        default_scope: Default deployment scope (``"user"`` or ``"local"``).
        edition: Application edition identifier (e.g. ``"community"``).
        indexing_mode: Global artifact search indexing mode
            (``"off"`` | ``"on"`` | ``"opt_in"``).
        extra: Any additional key/value settings not covered above.
    """

    github_token: str | None = None
    collection_path: str | None = None
    default_scope: str = "user"
    edition: str = "community"
    indexing_mode: str = "opt_in"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a SettingsDTO from a plain dictionary.

        All keys in *data* that do not map to known fields are collected into
        ``extra`` so no information is silently discarded.

        Args:
            data: Flat configuration mapping (e.g. from ConfigManager).

        Returns:
            A fully populated :class:`SettingsDTO`.
        """
        known = {
            "github_token",
            "collection_path",
            "default_scope",
            "edition",
            "indexing_mode",
        }
        return cls(
            github_token=data.get("github_token"),
            collection_path=data.get("collection_path"),
            default_scope=data.get("default_scope", "user"),
            edition=data.get("edition", "community"),
            indexing_mode=data.get("indexing_mode", "opt_in"),
            extra={k: v for k, v in data.items() if k not in known},
        )


# =============================================================================
# CollectionMembershipDTO
# =============================================================================


@dataclass(frozen=True)
class CollectionMembershipDTO:
    """Records that an artifact belongs to a named collection.

    Attributes:
        collection_id: Unique identifier of the collection (collection name).
        collection_name: Human-readable collection name.
        artifact_uuid: Stable UUID of the artifact (per ADR-007).
        artifact_id: Artifact primary key in ``"type:name"`` format.
        added_at: ISO-8601 timestamp when the artifact was added to the
            collection, or ``None`` when not tracked.
    """

    collection_id: str
    collection_name: str
    artifact_uuid: str | None = None
    artifact_id: str | None = None
    added_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a CollectionMembershipDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``collection_id``
                and ``collection_name``.

        Returns:
            A fully populated :class:`CollectionMembershipDTO`.
        """
        return cls(
            collection_id=data["collection_id"],
            collection_name=data["collection_name"],
            artifact_uuid=data.get("artifact_uuid"),
            artifact_id=data.get("artifact_id"),
            added_at=_to_iso(data.get("added_at")),
        )


# =============================================================================
# EntityTypeConfigDTO
# =============================================================================


@dataclass(frozen=True)
class EntityTypeConfigDTO:
    """Configuration record for a custom entity type.

    Entity types extend the artifact model with user-defined groupings
    (e.g. ``"workflow"``, ``"dataset"``).

    Attributes:
        id: Unique identifier for the entity type config record.
        entity_type: Machine-readable entity type key (e.g. ``"workflow"``).
        display_name: Human-readable display name.
        description: Optional description of this entity type.
        icon: Optional icon identifier or URL.
        color: Optional hex color code for UI display (e.g. ``"#FF5733"``).
        is_system: True when this config is built-in (not user-created).
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    entity_type: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_system: bool = False
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct an EntityTypeConfigDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``entity_type``,
                and ``display_name``.

        Returns:
            A fully populated :class:`EntityTypeConfigDTO`.
        """
        return cls(
            id=data["id"],
            entity_type=data["entity_type"],
            display_name=data["display_name"],
            description=data.get("description"),
            icon=data.get("icon"),
            color=data.get("color"),
            is_system=bool(data.get("is_system", False)),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# CategoryDTO
# =============================================================================


@dataclass(frozen=True)
class CategoryDTO:
    """A user-defined category that can be applied to entities.

    Categories provide a secondary classification axis beyond artifact type,
    allowing users to group entities by purpose, domain, or any other
    meaningful attribute.

    Attributes:
        id: Unique identifier for the category record.
        name: Human-readable category name (must be unique within
            ``entity_type``).
        entity_type: The entity type this category applies to, or ``None``
            for cross-type categories.
        description: Optional description of what this category represents.
        color: Optional hex color code for UI display (e.g. ``"#00FF00"``).
        artifact_count: Number of artifacts assigned to this category.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    entity_type: str | None = None
    description: str | None = None
    color: str | None = None
    artifact_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a CategoryDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id`` and ``name``.

        Returns:
            A fully populated :class:`CategoryDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=data.get("entity_type"),
            description=data.get("description"),
            color=data.get("color"),
            artifact_count=int(data.get("artifact_count") or 0),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# Internal helpers
# =============================================================================


def _to_iso(value: Any) -> str | None:
    """Coerce *value* to an ISO-8601 string or ``None``.

    Accepts ``datetime`` objects (calls ``.isoformat()``), existing strings
    (returned as-is), and ``None`` (returned as ``None``).

    Args:
        value: A ``datetime``, ISO string, or ``None``.

    Returns:
        ISO-8601 string or ``None``.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # datetime / date objects
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
