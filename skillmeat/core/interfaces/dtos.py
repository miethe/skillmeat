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
    # Groups
    "GroupDTO",
    "GroupArtifactDTO",
    # Context entities
    "ContextEntityDTO",
    # Marketplace
    "MarketplaceSourceDTO",
    "CatalogItemDTO",
    # Project templates
    "ProjectTemplateDTO",
    "TemplateEntityDTO",
    # User collections (DB-backed)
    "UserCollectionDTO",
    "CollectionArtifactDTO",
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
        sort_order: Display ordering (ascending).
        path_prefix: Default filesystem path prefix for this type.
        required_frontmatter_keys: Frontmatter keys that must be present.
        optional_frontmatter_keys: Frontmatter keys that may be present.
        validation_rules: Additional validation configuration dict.
        example_path: Example path illustrating this entity type.
        content_template: Default Markdown template for new entities.
        applicable_platforms: Platform slugs this type applies to; ``None``
            means all platforms.
        frontmatter_schema: JSON Schema subset for frontmatter validation.
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
    sort_order: int = 0
    path_prefix: str | None = None
    required_frontmatter_keys: List[str] | None = None
    optional_frontmatter_keys: List[str] | None = None
    validation_rules: Dict[str, Any] | None = None
    example_path: str | None = None
    content_template: str | None = None
    applicable_platforms: List[str] | None = None
    frontmatter_schema: Dict[str, Any] | None = None
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
            sort_order=int(data.get("sort_order") or 0),
            path_prefix=data.get("path_prefix"),
            required_frontmatter_keys=data.get("required_frontmatter_keys"),
            optional_frontmatter_keys=data.get("optional_frontmatter_keys"),
            validation_rules=data.get("validation_rules"),
            example_path=data.get("example_path"),
            content_template=data.get("content_template"),
            applicable_platforms=data.get("applicable_platforms"),
            frontmatter_schema=data.get("frontmatter_schema"),
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
        slug: URL-safe machine identifier.
        entity_type: The entity type this category applies to, or ``None``
            for cross-type categories.
        description: Optional description of what this category represents.
        color: Optional hex color code for UI display (e.g. ``"#00FF00"``).
        platform: Optional platform scope filter.
        sort_order: Ascending display order in the UI.
        is_builtin: True when this category is system-seeded.
        artifact_count: Number of artifacts assigned to this category.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    slug: str = ""
    entity_type: str | None = None
    description: str | None = None
    color: str | None = None
    platform: str | None = None
    sort_order: int = 0
    is_builtin: bool = False
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
            slug=data.get("slug", ""),
            entity_type=data.get("entity_type"),
            description=data.get("description"),
            color=data.get("color"),
            platform=data.get("platform"),
            sort_order=int(data.get("sort_order") or 0),
            is_builtin=bool(data.get("is_builtin", False)),
            artifact_count=int(data.get("artifact_count") or 0),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# GroupDTO
# =============================================================================


@dataclass(frozen=True)
class GroupDTO:
    """Lightweight representation of an artifact group within a collection.

    Groups let users organise collection artifacts into named, position-ordered
    buckets.  Each group belongs to exactly one collection.

    Attributes:
        id: Integer primary key (stored as ``str`` for DTO uniformity).
        name: Human-readable group name.
        collection_id: Identifier of the owning collection.
        description: Optional group description.
        position: Zero-based display order within the collection.
        artifact_count: Number of artifacts currently in this group.
        tags: List of tag strings attached to the group.
        color: Display colour slug (e.g. ``"slate"``).  Defaults to ``"slate"``.
        icon: Display icon slug (e.g. ``"layers"``).  Defaults to ``"layers"``.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    collection_id: str
    description: str | None = None
    position: int = 0
    artifact_count: int = 0
    tags: List[str] = field(default_factory=list)
    color: str = "slate"
    icon: str = "layers"
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a GroupDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``name``,
                and ``collection_id``.

        Returns:
            A fully populated :class:`GroupDTO`.
        """
        return cls(
            id=str(data["id"]),
            name=data["name"],
            collection_id=str(data["collection_id"]),
            description=data.get("description"),
            position=int(data.get("position") or 0),
            artifact_count=int(data.get("artifact_count") or 0),
            tags=list(data.get("tags") or []),
            color=data.get("color") or "slate",
            icon=data.get("icon") or "layers",
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# GroupArtifactDTO
# =============================================================================


@dataclass(frozen=True)
class GroupArtifactDTO:
    """Records that an artifact is a member of a group.

    Carries the position-based ordering of artifacts within a group.

    Attributes:
        group_id: Integer primary key of the owning group (as ``str``).
        artifact_uuid: Stable ADR-007 UUID of the artifact.
        position: Zero-based display order within the group.
        added_at: ISO-8601 timestamp when the artifact was added to the group.
    """

    group_id: str
    artifact_uuid: str
    position: int = 0
    added_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a GroupArtifactDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``group_id`` and
                ``artifact_uuid``.

        Returns:
            A fully populated :class:`GroupArtifactDTO`.
        """
        return cls(
            group_id=str(data["group_id"]),
            artifact_uuid=data["artifact_uuid"],
            position=int(data.get("position") or 0),
            added_at=_to_iso(data.get("added_at")),
        )


# =============================================================================
# ContextEntityDTO
# =============================================================================


@dataclass(frozen=True)
class ContextEntityDTO:
    """Lightweight representation of a context entity artifact.

    Context entities are special artifacts (CLAUDE.md, spec files, rule files,
    context files, progress templates) that define project structure, rules, and
    context for Claude Code projects.

    Attributes:
        id: Artifact primary key (e.g. ``"ctx_abc123"``).
        name: Human-readable entity name.
        entity_type: Entity type key (``"project_config"``, ``"spec_file"``,
            ``"rule_file"``, ``"context_file"``, ``"progress_template"``).
        content: Assembled markdown content.
        path_pattern: Target path pattern for deployment (e.g. ``".claude/CLAUDE.md"``).
        description: Optional description.
        category: Optional category for progressive disclosure (e.g. ``"api"``).
        auto_load: Whether the entity should be auto-loaded by the platform.
        version: Optional version string.
        target_platforms: Optional list of target platform identifiers.
        content_hash: SHA-256 hex hash of the current content for change detection.
        category_ids: Ordered list of category IDs associated with this entity.
        core_content: Platform-agnostic source content (modular content architecture).
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    entity_type: str
    content: str = ""
    path_pattern: str = ""
    description: str | None = None
    category: str | None = None
    auto_load: bool = False
    version: str | None = None
    target_platforms: List[str] = field(default_factory=list)
    content_hash: str | None = None
    category_ids: List[int] = field(default_factory=list)
    core_content: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a ContextEntityDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id``, ``name``,
                and ``entity_type`` (or ``type`` as an alias).

        Returns:
            A fully populated :class:`ContextEntityDTO`.
        """
        raw_platforms = data.get("target_platforms") or []
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=data.get("entity_type") or data.get("type") or "",
            content=data.get("content") or "",
            path_pattern=data.get("path_pattern") or "",
            description=data.get("description"),
            category=data.get("category"),
            auto_load=bool(data.get("auto_load", False)),
            version=data.get("version") or data.get("deployed_version"),
            target_platforms=list(raw_platforms),
            content_hash=data.get("content_hash"),
            category_ids=list(data.get("category_ids") or []),
            core_content=data.get("core_content"),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# MarketplaceSourceDTO
# =============================================================================


@dataclass(frozen=True)
class MarketplaceSourceDTO:
    """Lightweight representation of a marketplace broker/source.

    A marketplace source is a configured endpoint (broker) that provides
    listings of artifacts available for installation.

    Attributes:
        id: Source unique identifier (usually the broker name).
        name: Human-readable source name.
        enabled: Whether this source is currently active.
        endpoint: Base URL for the broker API.
        description: Optional description of this source.
        supports_publish: Whether this source allows publishing new listings.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    enabled: bool = False
    endpoint: str = ""
    description: str | None = None
    supports_publish: bool = False
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a MarketplaceSourceDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id`` and ``name``.

        Returns:
            A fully populated :class:`MarketplaceSourceDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            enabled=bool(data.get("enabled", False)),
            endpoint=data.get("endpoint") or "",
            description=data.get("description"),
            supports_publish=bool(data.get("supports_publish", False)),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# CatalogItemDTO
# =============================================================================


@dataclass(frozen=True)
class CatalogItemDTO:
    """Lightweight representation of a single marketplace catalog listing.

    Each catalog item represents one publishable artifact bundle available
    from a marketplace source/broker.

    Attributes:
        listing_id: Unique identifier for this listing within its source.
        name: Human-readable listing name.
        source_id: Identifier of the broker/source that provides this listing.
        publisher: Publisher or author name.
        description: Optional listing description.
        license: SPDX license identifier (e.g. ``"MIT"``).
        version: Version string.
        artifact_count: Number of artifacts bundled in this listing.
        tags: Tag strings categorising this listing.
        source_url: URL to the upstream source repository or page.
        bundle_url: URL to the downloadable bundle archive.
        signature: Bundle signature for integrity verification.
        downloads: Total download count.
        rating: Average rating (0-5 scale).
        price: Price string (``None`` or ``"0"`` for free listings).
        created_at: ISO-8601 creation timestamp.
    """

    listing_id: str
    name: str
    source_id: str | None = None
    publisher: str | None = None
    description: str | None = None
    license: str | None = None
    version: str | None = None
    artifact_count: int = 0
    tags: List[str] = field(default_factory=list)
    source_url: str | None = None
    bundle_url: str | None = None
    signature: str | None = None
    downloads: int = 0
    rating: float | None = None
    price: str | None = None
    created_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a CatalogItemDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``listing_id`` and ``name``.

        Returns:
            A fully populated :class:`CatalogItemDTO`.
        """
        return cls(
            listing_id=data["listing_id"],
            name=data["name"],
            source_id=data.get("source_id"),
            publisher=data.get("publisher"),
            description=data.get("description"),
            license=data.get("license"),
            version=data.get("version"),
            artifact_count=int(data.get("artifact_count") or 0),
            tags=list(data.get("tags") or []),
            source_url=data.get("source_url"),
            bundle_url=data.get("bundle_url"),
            signature=data.get("signature"),
            downloads=int(data.get("downloads") or 0),
            rating=float(data["rating"]) if data.get("rating") is not None else None,
            price=data.get("price"),
            created_at=_to_iso(data.get("created_at")),
        )


# =============================================================================
# ProjectTemplateDTO
# =============================================================================


@dataclass(frozen=True)
class TemplateEntityDTO:
    """A single entity entry within a project template.

    Captures the relationship between a :class:`ProjectTemplateDTO` and one
    of its constituent context-entity artifacts.

    Attributes:
        artifact_id: Artifact primary key (``"type:name"``).
        name: Artifact display name.
        artifact_type: Artifact type string (e.g. ``"spec_file"``).
        deploy_order: Zero-based position controlling deployment sequence.
        required: Whether this entity is mandatory for template deployment.
        path_pattern: Target path pattern from the artifact.
    """

    artifact_id: str
    name: str
    artifact_type: str = ""
    deploy_order: int = 0
    required: bool = True
    path_pattern: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a TemplateEntityDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``artifact_id`` and ``name``.

        Returns:
            A fully populated :class:`TemplateEntityDTO`.
        """
        return cls(
            artifact_id=data["artifact_id"],
            name=data["name"],
            artifact_type=data.get("artifact_type") or data.get("type") or "",
            deploy_order=int(data.get("deploy_order") or 0),
            required=bool(data.get("required", True)),
            path_pattern=data.get("path_pattern"),
        )


@dataclass(frozen=True)
class ProjectTemplateDTO:
    """Lightweight representation of a project template.

    Project templates are reusable collections of context entities that can
    be deployed together to initialise Claude Code project structures.
    Templates support variable substitution for customisation.

    Attributes:
        id: Template unique identifier (hex UUID).
        name: Human-readable template name.
        description: Optional template description.
        collection_id: Identifier of the owning collection.
        default_project_config_id: Artifact ID of the default CLAUDE.md to use.
        entities: Ordered list of template entity records.
        entity_count: Total number of entities in this template.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str
    name: str
    description: str | None = None
    collection_id: str | None = None
    default_project_config_id: str | None = None
    entities: List[TemplateEntityDTO] = field(default_factory=list)
    entity_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a ProjectTemplateDTO from a plain dictionary.

        Args:
            data: Mapping that contains at minimum ``id`` and ``name``.

        Returns:
            A fully populated :class:`ProjectTemplateDTO`.
        """
        raw_entities = data.get("entities") or []
        entities = [
            TemplateEntityDTO.from_dict(e) if isinstance(e, dict) else e
            for e in raw_entities
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            collection_id=data.get("collection_id"),
            default_project_config_id=data.get("default_project_config_id"),
            entities=entities,
            entity_count=int(data.get("entity_count") or len(entities)),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
        )


# =============================================================================
# UserCollectionDTO
# =============================================================================


@dataclass(frozen=True)
class UserCollectionDTO:
    """Lightweight representation of a DB-backed user collection.

    Maps from the ``Collection`` ORM model in ``skillmeat.cache.models``.
    Unlike the filesystem-oriented :class:`CollectionDTO`, this DTO is keyed
    by the database UUID primary key and carries the full set of metadata
    columns used by the web API.

    Attributes:
        id: UUID hex primary key (e.g. ``"a1b2c3d4..."``).
        name: Human-readable collection name (1-255 characters).
        description: Optional detailed description.
        created_by: User identifier for future multi-user support.
        collection_type: Optional collection type (e.g. ``"context"``
            or ``"artifacts"``).
        context_category: Optional sub-category for context collections
            (e.g. ``"rules"`` or ``"specs"``).
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        artifact_count: Number of artifacts currently in the collection
            (derived, not a stored column).
    """

    id: str
    name: str
    description: str | None = None
    created_by: str | None = None
    collection_type: str | None = None
    context_category: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    artifact_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a UserCollectionDTO from a plain dictionary.

        Unknown keys are silently ignored so callers can pass raw ORM
        ``to_dict()`` output or query-result rows without pre-filtering.

        Args:
            data: Mapping that contains at minimum ``id`` and ``name``.

        Returns:
            A fully populated :class:`UserCollectionDTO`.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            created_by=data.get("created_by"),
            collection_type=data.get("collection_type"),
            context_category=data.get("context_category"),
            created_at=_to_iso(data.get("created_at")),
            updated_at=_to_iso(data.get("updated_at")),
            artifact_count=int(data.get("artifact_count") or 0),
        )


# =============================================================================
# CollectionArtifactDTO
# =============================================================================


@dataclass(frozen=True)
class CollectionArtifactDTO:
    """Lightweight representation of a collection–artifact association row.

    Maps from the ``CollectionArtifact`` ORM model (the rich join table in
    ``skillmeat.cache.models``).  Carries both the join keys and the cached
    metadata columns that allow the web API to serve collection pages without
    re-reading every artifact from the filesystem.

    Attributes:
        collection_id: UUID hex FK to ``collections.id``.
        artifact_uuid: Stable ADR-007 UUID FK to ``artifacts.uuid``.
        added_at: ISO-8601 timestamp when the artifact was added to the
            collection.
        description: Cached artifact description.
        author: Cached artifact author string.
        license: Cached SPDX license identifier (e.g. ``"MIT"``).
        tags: Cached tag name strings (deserialised from ``tags_json``).
        tools: Cached tool name strings (deserialised from ``tools_json``).
        deployments: Cached deployment path strings (from ``deployments_json``).
        artifact_content_hash: SHA-256 hash of artifact file contents.
        artifact_structure_hash: Hash of the artifact directory structure.
        artifact_file_count: Number of files in the artifact.
        artifact_total_size: Total byte size of all artifact files.
        source: Upstream source spec string.
        origin: Origin URL or identifier.
        resolved_sha: Resolved VCS commit SHA.
        resolved_version: Resolved version string.
        synced_at: ISO-8601 timestamp of the most-recent metadata sync.
    """

    collection_id: str
    artifact_uuid: str
    added_at: str | None = None
    description: str | None = None
    author: str | None = None
    license: str | None = None
    tags: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    deployments: List[str] = field(default_factory=list)
    artifact_content_hash: str | None = None
    artifact_structure_hash: str | None = None
    artifact_file_count: int | None = None
    artifact_total_size: int | None = None
    source: str | None = None
    origin: str | None = None
    resolved_sha: str | None = None
    resolved_version: str | None = None
    synced_at: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Construct a CollectionArtifactDTO from a plain dictionary.

        Handles JSON-serialised list columns (``tags_json``, ``tools_json``,
        ``deployments_json``) transparently — pass the raw ORM ``__dict__``
        or a pre-deserialised mapping; both are accepted.

        Args:
            data: Mapping that contains at minimum ``collection_id`` and
                ``artifact_uuid``.

        Returns:
            A fully populated :class:`CollectionArtifactDTO`.
        """
        import json as _json

        def _parse_json_list(raw: Any) -> List[str]:
            """Return a list from a JSON string, a list, or None/empty."""
            if raw is None:
                return []
            if isinstance(raw, list):
                return list(raw)
            if isinstance(raw, str):
                try:
                    parsed = _json.loads(raw)
                    return list(parsed) if isinstance(parsed, list) else []
                except (_json.JSONDecodeError, TypeError):
                    return []
            return []

        file_count = data.get("artifact_file_count")
        total_size = data.get("artifact_total_size")

        return cls(
            collection_id=data["collection_id"],
            artifact_uuid=data["artifact_uuid"],
            added_at=_to_iso(data.get("added_at")),
            description=data.get("description"),
            author=data.get("author"),
            license=data.get("license"),
            tags=_parse_json_list(data.get("tags") or data.get("tags_json")),
            tools=_parse_json_list(data.get("tools") or data.get("tools_json")),
            deployments=_parse_json_list(
                data.get("deployments") or data.get("deployments_json")
            ),
            artifact_content_hash=data.get("artifact_content_hash"),
            artifact_structure_hash=data.get("artifact_structure_hash"),
            artifact_file_count=int(file_count) if file_count is not None else None,
            artifact_total_size=int(total_size) if total_size is not None else None,
            source=data.get("source"),
            origin=data.get("origin"),
            resolved_sha=data.get("resolved_sha"),
            resolved_version=data.get("resolved_version"),
            synced_at=_to_iso(data.get("synced_at")),
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
