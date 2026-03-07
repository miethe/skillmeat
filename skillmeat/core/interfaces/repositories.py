"""Abstract repository interfaces for SkillMeat's hexagonal architecture.

These ABCs define the data-access contracts that every storage backend must
satisfy.  Infrastructure implementations (e.g. the SQLAlchemy cache adapter)
live outside the core and fulfil these interfaces; the core never depends on
any concrete storage technology.

Design invariants:
- All classes inherit from ``abc.ABC``.
- All methods are decorated with ``@abc.abstractmethod`` and raise
  ``NotImplementedError`` to prevent accidental instantiation of partial
  implementations.
- ``ctx: RequestContext | None = None`` is the last parameter of every method
  so that callers that do not care about per-request metadata can omit it.
- Filter arguments use ``dict[str, Any] | None`` for now; typed filter objects
  can be introduced in a later phase without breaking the contract.
- No Pydantic, no SQLAlchemy — stdlib only (plus the sibling interfaces
  modules).

Usage::

    from skillmeat.core.interfaces.repositories import (
        IArtifactRepository,
        IProjectRepository,
        ICollectionRepository,
        IDeploymentRepository,
        ITagRepository,
        ISettingsRepository,
    )
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from skillmeat.core.interfaces.context import RequestContext

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext
from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    ArtifactVersionDTO,
    CacheArtifactSummaryDTO,
    CatalogItemDTO,
    CategoryDTO,
    CollectionArtifactDTO,
    CollectionDTO,
    CollectionMembershipDTO,
    ContextEntityDTO,
    DeploymentDTO,
    EntityTypeConfigDTO,
    GroupArtifactDTO,
    GroupDTO,
    MarketplaceSourceDTO,
    ProjectDTO,
    ProjectTemplateDTO,
    SettingsDTO,
    TagDTO,
    UserCollectionDTO,
)

__all__ = [
    "IArtifactRepository",
    "IProjectRepository",
    "ICollectionRepository",
    "IDbUserCollectionRepository",
    "IDeploymentRepository",
    "ITagRepository",
    "ISettingsRepository",
    "IGroupRepository",
    "IContextEntityRepository",
    "IMarketplaceSourceRepository",
    "IProjectTemplateRepository",
    "IDbCollectionArtifactRepository",
    "IDbArtifactHistoryRepository",
]


# =============================================================================
# IArtifactRepository
# =============================================================================


class IArtifactRepository(abc.ABC):
    """Contract for all artifact storage backends.

    Covers the full lifecycle of an artifact: creation, retrieval, update,
    deletion, search, and file-content access.  The operations reflect what
    the ``/api/v1/artifacts`` router exposes.
    """

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return the artifact with the given ``type:name`` primary key.

        Args:
            id: Artifact primary key in ``"type:name"`` format
                (e.g. ``"skill:frontend-design"``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when the
            artifact exists, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_uuid(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return the artifact identified by its stable UUID.

        The UUID is the ADR-007 identity and remains stable across renames.

        Args:
            uuid: 32-char hex UUID string.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return a page of artifacts matching optional filter criteria.

        Args:
            filters: Optional key/value filter map.  Recognised keys are
                implementation-defined but should include at minimum
                ``artifact_type``, ``project_id``, ``scope``, and
                ``is_outdated``.
            offset: Zero-based record offset for pagination.
            limit: Maximum number of records to return.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> int:
        """Return the total number of artifacts matching optional filter criteria.

        Intended to back ``page_info.total`` in paginated list responses.

        Args:
            filters: Same filter map accepted by :meth:`list`.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Non-negative integer count.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Full-text / fuzzy search across artifact names and metadata.

        Args:
            query: Free-form search string.
            filters: Optional additional filter constraints applied on top
                of the text match.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Ranked list of matching
            :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` objects.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        dto: ArtifactDTO,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO:
        """Persist a new artifact record and return the stored representation.

        Args:
            dto: Fully populated artifact data.  The implementation may
                ignore ``created_at`` / ``updated_at`` and set them itself.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            The persisted :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            (may differ from *dto* if the backend generates fields such as
            ``uuid`` or timestamps).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO:
        """Apply a partial update to an existing artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            updates: Map of field names to new values.  Only provided
                fields are changed; others remain untouched.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`.

        Raises:
            KeyError: If no artifact with *id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Delete an artifact and all its associated records.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            ``True`` when the artifact was found and deleted, ``False`` when
            no matching record existed.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # File-content access
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_content(
        self,
        id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> str:
        """Return the raw text content of an artifact's primary file.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            File content as a UTF-8 string.

        Raises:
            KeyError: If no artifact with *id* exists.
            FileNotFoundError: If the content file cannot be located.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_content(
        self,
        id: str,
        content: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Overwrite the primary file content of an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            content: New file content (UTF-8 string).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            ``True`` on success.

        Raises:
            KeyError: If no artifact with *id* exists.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Tag associations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_tags(
        self,
        id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[TagDTO]:
        """Return all tags currently assigned to an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.TagDTO` objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_tags(
        self,
        id: str,
        tag_ids: list[str],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Replace the complete tag set for an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            tag_ids: New complete list of tag IDs.  Any previous tags not
                present in this list are removed.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            ``True`` on success.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # UUID resolution
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def resolve_uuid_by_type_name(
        self,
        artifact_type: str,
        name: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> str | None:
        """Resolve the stable UUID for an artifact identified by type and name.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``).
            name: Artifact name string.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            32-char hex UUID string when found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_ids_by_uuids(
        self,
        uuids: list[str],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> dict[str, str]:
        """Batch-map artifact UUIDs to their ``type:name`` ID strings.

        Executes a single round-trip against the DB cache and returns a
        mapping of every UUID that has a matching artifact row.  UUIDs with
        no corresponding row are absent from the returned dict.

        Args:
            uuids: List of 32-char hex UUID strings to look up.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Dict mapping each UUID to its ``"type:name"`` artifact ID string.
            Unresolvable UUIDs are omitted.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def batch_resolve_uuids(
        self,
        artifacts: list[tuple[str, str]],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> dict[tuple[str, str], str]:
        """Batch-resolve UUIDs for multiple ``(artifact_type, name)`` pairs.

        Executes a single round-trip (when possible) rather than N individual
        lookups.  Pairs that cannot be resolved are absent from the returned
        dict.

        Args:
            artifacts: List of ``(artifact_type, name)`` tuples.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Dict mapping each ``(artifact_type, name)`` tuple to its 32-char
            hex UUID.  Unresolvable pairs are omitted.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Collection-context queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_with_collection_context(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return an artifact with enriched collection-membership context.

        The returned DTO may carry additional collection-level metadata
        (e.g. collection description, collection tags) compared to the
        plain :meth:`get_by_uuid` result.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when
            found (with collection context populated where available),
            ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_collection_memberships(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[CollectionMembershipDTO]:
        """Return all collections that contain the artifact identified by *uuid*.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionMembershipDTO`
            objects, one per collection membership.  Returns an empty list
            when the artifact is not found or has no collection memberships.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_collection_description(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> str | None:
        """Return the collection-level description for an artifact.

        The collection-level description may differ from the artifact's
        intrinsic description (e.g. it may be set by the collection owner
        rather than the artifact author).

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Collection-level description string, or ``None`` when not set
            or the artifact does not exist.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Deduplication cluster queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_duplicate_cluster_members(
        self,
        cluster_id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return all artifacts that belong to the given deduplication cluster.

        Deduplication clusters group semantically equivalent artifacts
        discovered during import or sync.

        Args:
            cluster_id: Opaque cluster identifier (implementation-defined).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects representing every cluster member.  Returns an empty
            list when the cluster does not exist or has no members.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Existence and type queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def validate_exists(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Check whether an artifact with the given UUID exists.

        Lighter-weight alternative to :meth:`get_by_uuid` when only
        existence is needed.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            ``True`` when an artifact with *uuid* exists, ``False`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_type(
        self,
        artifact_type: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return all artifacts of the specified type.

        Equivalent to calling :meth:`list` with ``filters={"artifact_type": artifact_type}``
        and no pagination, but expressed as a first-class method for clarity.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``, ``"command"``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects matching *artifact_type*.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Collection-level mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def update_collection_tags(
        self,
        uuid: str,
        tags: list[str],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Replace the collection-level tags for an artifact.

        Collection-level tags are distinct from intrinsic artifact tags:
        they are set by the collection owner and stored alongside the
        collection membership record rather than in the artifact manifest.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            tags: New complete list of tag name strings.  Replaces any
                previously set collection-level tags.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If no artifact with *uuid* exists.
        """
        raise NotImplementedError


# =============================================================================
# IProjectRepository
# =============================================================================


class IProjectRepository(abc.ABC):
    """Contract for project storage backends.

    A project represents a directory on disk that has one or more artifacts
    deployed into it.  Operations map to the ``/api/v1/projects`` router.
    """

    @abc.abstractmethod
    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO | None:
        """Return the project with the given identifier.

        Args:
            id: Base64-encoded project path (primary key).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.ProjectDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[ProjectDTO]:
        """Return all known projects.

        Args:
            filters: Optional filter map (e.g. ``{"status": "active"}``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ProjectDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(
        self,
        dto: ProjectDTO,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        """Register a new project.

        Args:
            dto: Project data including at minimum ``id``, ``name``, and
                ``path``.
            ctx: Optional per-request metadata.

        Returns:
            The persisted :class:`~skillmeat.core.interfaces.dtos.ProjectDTO`.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        """Apply a partial update to an existing project.

        Args:
            id: Project primary key (base64-encoded path).
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.ProjectDTO`.

        Raises:
            KeyError: If no project with *id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Remove a project record.

        Does not delete anything on disk — only removes the DB/registry entry.

        Args:
            id: Project primary key (base64-encoded path).
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the project was found and deleted, ``False``
            otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_artifacts(
        self,
        project_id: str,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return all artifacts deployed to a project.

        Args:
            project_id: Base64-encoded project path.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects representing each deployed artifact.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def refresh(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        """Trigger a cache refresh for a single project.

        Rescans the project's deployment tracking files and updates the
        cached artifact list.

        Args:
            id: Project primary key (base64-encoded path).
            ctx: Optional per-request metadata.

        Returns:
            The refreshed :class:`~skillmeat.core.interfaces.dtos.ProjectDTO`.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_path(
        self,
        path: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO | None:
        """Return the project whose filesystem path matches *path*.

        Args:
            path: Absolute filesystem path (resolved).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.ProjectDTO` when a
            project with the given path is found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_by_path(
        self,
        path: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        """Return the project for *path*, creating a DB record if absent.

        Resolves the absolute path, looks up an existing project by path,
        and creates a new one if none is found.  Used by endpoints that
        accept base64-encoded paths that may not yet have a DB entry.

        Args:
            path: Absolute filesystem path (will be resolved).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.ProjectDTO` (existing
            or newly created).
        """
        raise NotImplementedError


# =============================================================================
# ICollectionRepository
# =============================================================================


class ICollectionRepository(abc.ABC):
    """Contract for collection storage backends.

    A collection is the user's personal artifact library managed under
    ``~/.skillmeat/``.  There is typically one active collection per user.
    Operations map to the ``/api/v1/user-collections`` router.
    """

    @abc.abstractmethod
    def get(
        self,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO | None:
        """Return the active collection metadata.

        Args:
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` when a
            collection exists, ``None`` if none has been initialised.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_id(
        self,
        id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO | None:
        """Return a specific collection by its identifier.

        Args:
            id: Collection unique identifier (usually the collection name).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list(
        self,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[CollectionDTO]:
        """Return all known collections.

        Args:
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_stats(
        self,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> dict[str, Any]:
        """Return aggregate statistics for the active collection.

        The returned dictionary should contain at minimum:
        ``artifact_count``, ``total_size_bytes``, ``last_synced``.

        Args:
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            Plain dictionary of stat key/value pairs.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def refresh(
        self,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Re-scan the filesystem and rebuild the collection cache.

        Args:
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            The refreshed :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_artifacts(
        self,
        collection_id: str,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return the artifacts that belong to a collection.

        Args:
            collection_id: Collection unique identifier.
            filters: Optional filter constraints (e.g. ``artifact_type``).
            offset: Zero-based pagination offset.
            limit: Maximum number of records to return.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        name: str,
        description: str | None = None,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Create a new collection.

        Args:
            name: Human-readable name for the new collection.  Must be
                unique within the storage backend.
            description: Optional description text.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.

        Raises:
            ValueError: If a collection with the same *name* already exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        collection_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Apply a partial update to an existing collection.

        Args:
            collection_id: Collection unique identifier.
            updates: Map of field names to new values (e.g. ``{"name": "new-name"}``).
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.

        Raises:
            KeyError: If no collection with *collection_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Delete a collection and remove all its membership records.

        Does not delete artifact files from disk — only removes the
        collection registry entry and associated memberships.

        Args:
            collection_id: Collection unique identifier.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If no collection with *collection_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_artifacts(
        self,
        collection_id: str,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Add one or more artifacts to a collection by UUID.

        Idempotent: artifacts already in the collection are silently skipped.

        Args:
            collection_id: Collection unique identifier.
            artifact_uuids: List of stable artifact UUIDs (32-char hex
                strings) to add to the collection.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If any UUID in *artifact_uuids* does not correspond
                to a known artifact.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_artifact(
        self,
        collection_id: str,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Remove a single artifact from a collection.

        Args:
            collection_id: Collection unique identifier.
            artifact_uuid: Stable artifact UUID (32-char hex) to remove.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If *collection_id* does not exist or *artifact_uuid* is
                not a member of the collection.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Entity management within a collection
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_entities(
        self,
        collection_id: str,
        entity_type: str | None = None,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[Any]:
        """Return entities belonging to a collection, optionally filtered by type.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Optional entity type string to filter by
                (e.g. ``"workflow"``, ``"dataset"``).  When ``None``, all
                entity types are returned.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Returns:
            List of entity records.  The exact element type is
            implementation-defined; callers should treat them as plain
            dicts or typed DTOs depending on the backend.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Associate an entity with a collection.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Entity type string (e.g. ``"workflow"``).
            entity_id: Unique identifier of the entity to associate.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *entity_id* does not correspond to a known entity
                of the given *entity_type*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Remove an entity association from a collection.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Entity type string (e.g. ``"workflow"``).
            entity_id: Unique identifier of the entity to disassociate.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If *collection_id* does not exist or the entity is not
                associated with the collection.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def migrate_to_default(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Migrate a collection's artifacts and entities to the default collection.

        Intended for use when a non-default collection is being retired.
        All member artifacts and entity associations are moved to the active
        default collection; the source collection record is then removed.

        Args:
            collection_id: Collection unique identifier of the source collection
                to migrate away from.
            ctx: Optional per-request metadata.
            auth_context: Optional authentication and authorisation context.
                When ``None`` the operation is performed without tenant
                scoping (local zero-auth mode).

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *collection_id* refers to the current default
                collection (cannot migrate to itself).
        """
        raise NotImplementedError


# =============================================================================
# IDeploymentRepository
# =============================================================================


class IDeploymentRepository(abc.ABC):
    """Contract for deployment storage backends.

    A deployment represents an artifact that has been installed into a project
    directory.  Operations map to the ``/api/v1/deploy`` router.
    """

    @abc.abstractmethod
    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> DeploymentDTO | None:
        """Return a deployment record by its identifier.

        Args:
            id: Deployment record identifier (often ``"type:name"``).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[DeploymentDTO]:
        """Return deployment records matching optional filter criteria.

        Args:
            filters: Optional filter map.  Recognised keys typically include
                ``project_id``, ``artifact_id``, ``artifact_type``, and
                ``status``.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def deploy(
        self,
        artifact_id: str,
        project_id: str,
        options: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> DeploymentDTO:
        """Deploy an artifact from the collection to a project.

        Args:
            artifact_id: Artifact primary key (``"type:name"``).
            project_id: Target project identifier (base64-encoded path).
            options: Optional deployment options such as ``scope``,
                ``dest_path``, ``overwrite``, and ``profile_id``.
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`.

        Raises:
            KeyError: If *artifact_id* or *project_id* does not exist.
            ValueError: If the deployment would result in a conflict and
                *options* does not permit overwrite.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def undeploy(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Remove a deployed artifact from its project.

        Args:
            id: Deployment record identifier.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the deployment was found and removed, ``False``
            otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> str:
        """Return the current status string for a deployment.

        Args:
            id: Deployment record identifier.
            ctx: Optional per-request metadata.

        Returns:
            Status string (e.g. ``"deployed"``, ``"modified"``,
            ``"outdated"``).

        Raises:
            KeyError: If no deployment with *id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_artifact(
        self,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> list[DeploymentDTO]:
        """Return all active deployments for a given artifact.

        Args:
            artifact_id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`
            objects (may be empty if the artifact has never been deployed).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upsert_idp_deployment_set(
        self,
        *,
        remote_url: str,
        name: str,
        provisioned_by: str,
        description: str | None = None,
        ctx: RequestContext | None = None,
    ) -> tuple[str, bool]:
        """Idempotently create or update a DeploymentSet for an IDP registration.

        Looks up an existing ``DeploymentSet`` by the ``(remote_url, name)``
        pair.  If a match is found the record is updated with the supplied
        *provisioned_by* and *description*; otherwise a new record is created.

        Args:
            remote_url: Remote Git repository URL (e.g. the Backstage repo URL).
            name: Artifact target identifier (used as the set name).
            provisioned_by: Audit field identifying the provisioning agent
                (e.g. ``"idp"``).
            description: Optional JSON-serialised metadata string.
            ctx: Optional per-request metadata.

        Returns:
            A ``(deployment_set_id, created)`` tuple where *created* is
            ``True`` when a new record was inserted and ``False`` when an
            existing record was updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def sync_deployment_cache(
        self,
        artifact_id: str,
        project_path: str,
        project_name: str,
        deployed_at: Any,
        content_hash: str | None = None,
        deployment_profile_id: str | None = None,
        local_modifications: bool = False,
        platform: str | None = None,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Upsert a single deployment entry into the artifact cache.

        Performs a write-through update of the ``deployments_json`` column in
        ``collection_artifacts`` so the cache reflects the most-recent
        deployment state without a full cache refresh.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            project_path: Absolute filesystem path of the deployment target.
            project_name: Human-readable project directory name.
            deployed_at: Deployment timestamp (``datetime`` or ISO string).
            content_hash: Optional SHA of the deployed content snapshot.
            deployment_profile_id: Optional deployment profile identifier.
            local_modifications: Whether local modifications are present.
            platform: Optional platform identifier string.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the cache entry was updated, ``False`` when the
            artifact was not found in the cache (non-fatal).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_deployment_cache(
        self,
        artifact_id: str,
        project_path: str,
        profile_id: str | None = None,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Remove a deployment entry from the artifact cache.

        Performs a write-through removal of the matching entry from the
        ``deployments_json`` column in ``collection_artifacts`` so the cache
        reflects the current deployment state without a full cache refresh.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            project_path: Absolute filesystem path of the deployment target.
            profile_id: Optional profile ID to narrow the removal to a
                specific deployment profile entry.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the cache entry was updated, ``False`` when the
            artifact was not found in the cache (non-fatal).
        """
        raise NotImplementedError


# =============================================================================
# ITagRepository
# =============================================================================


class ITagRepository(abc.ABC):
    """Contract for tag storage backends.

    Tags are workspace-scoped labels that can be assigned to one or more
    artifacts.  Operations map to the ``/api/v1/tags`` router and the
    tag-association sub-resources on ``/api/v1/artifacts``.
    """

    @abc.abstractmethod
    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> TagDTO | None:
        """Return a tag by its identifier.

        Args:
            id: Tag unique identifier.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.TagDTO` when found,
            ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_slug(
        self,
        slug: str,
        ctx: RequestContext | None = None,
    ) -> TagDTO | None:
        """Return a tag by its URL-friendly slug.

        Args:
            slug: Kebab-case slug string.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.TagDTO` when found,
            ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[TagDTO]:
        """Return all tags.

        Args:
            filters: Optional filter map (e.g. ``{"name": "ai"}`` for
                prefix/search filtering).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.TagDTO` objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(
        self,
        name: str,
        color: str | None = None,
        ctx: RequestContext | None = None,
    ) -> TagDTO:
        """Create a new tag.

        The slug is automatically derived from *name* by the implementation.

        Args:
            name: Human-readable tag name (must be unique).
            color: Optional hex color code (e.g. ``"#FF5733"``).
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.TagDTO`.

        Raises:
            ValueError: If a tag with the same name (or derived slug) already
                exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> TagDTO:
        """Apply a partial update to an existing tag.

        Args:
            id: Tag unique identifier.
            updates: Map of field names to new values (e.g. ``{"color": "#00FF00"}``).
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.TagDTO`.

        Raises:
            KeyError: If no tag with *id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Delete a tag and remove all its artifact associations.

        Args:
            id: Tag unique identifier.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the tag was found and deleted, ``False`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def assign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Associate a tag with an artifact.

        Idempotent: calling this when the association already exists is
        a no-op and returns ``True``.

        Args:
            tag_id: Tag unique identifier.
            artifact_id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

        Returns:
            ``True`` on success.

        Raises:
            KeyError: If *tag_id* or *artifact_id* does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def unassign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Remove the association between a tag and an artifact.

        Args:
            tag_id: Tag unique identifier.
            artifact_id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the association existed and was removed, ``False``
            if there was no such association.
        """
        raise NotImplementedError


# =============================================================================
# ISettingsRepository
# =============================================================================


class ISettingsRepository(abc.ABC):
    """Contract for application settings storage backends.

    Settings are a single, user-scoped configuration record.  Operations map
    to the ``/api/v1/settings`` router.
    """

    @abc.abstractmethod
    def get(
        self,
        ctx: RequestContext | None = None,
    ) -> SettingsDTO:
        """Return the current application settings snapshot.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.SettingsDTO` populated
            with the current configuration values.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> SettingsDTO:
        """Apply a partial update to the application settings.

        Only provided keys are changed; unmentioned settings remain at their
        current values.

        Args:
            updates: Map of setting keys to new values.  Recognised keys
                mirror :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`
                fields: ``github_token``, ``collection_path``,
                ``default_scope``, ``edition``, ``indexing_mode``.
                Additional keys are stored in ``extra``.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def validate_github_token(
        self,
        token: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Validate a GitHub Personal Access Token against the API.

        Args:
            token: Raw GitHub PAT string.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` if the token is valid and authenticated, ``False``
            otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Entity type configuration
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_entity_type_configs(
        self,
        ctx: RequestContext | None = None,
    ) -> list[EntityTypeConfigDTO]:
        """Return all registered entity type configurations.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`
            objects, including both system-defined and user-created entries.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_entity_type_config(
        self,
        entity_type: str,
        display_name: str,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        ctx: RequestContext | None = None,
    ) -> EntityTypeConfigDTO:
        """Create a new user-defined entity type configuration.

        Args:
            entity_type: Machine-readable entity type key
                (e.g. ``"workflow"``).  Must be unique.
            display_name: Human-readable display name.
            description: Optional description of this entity type.
            icon: Optional icon identifier or URL.
            color: Optional hex color code (e.g. ``"#FF5733"``).
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`.

        Raises:
            ValueError: If an entity type config with the same *entity_type*
                already exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_entity_type_config(
        self,
        config_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> EntityTypeConfigDTO:
        """Apply a partial update to an existing entity type configuration.

        Args:
            config_id: Unique identifier of the entity type config record.
            updates: Map of field names to new values.  Recognised keys
                mirror :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`
                fields: ``display_name``, ``description``, ``icon``,
                ``color``.  The ``entity_type`` and ``is_system`` fields
                are immutable after creation.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`.

        Raises:
            KeyError: If no config with *config_id* exists.
            ValueError: If the update attempts to mutate an immutable field.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_entity_type_config(
        self,
        config_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a user-defined entity type configuration.

        System-defined entity type configs (``is_system=True``) cannot be
        deleted.

        Args:
            config_id: Unique identifier of the entity type config record.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no config with *config_id* exists.
            ValueError: If the config is system-defined.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Category management
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_categories(
        self,
        entity_type: str | None = None,
        platform: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[CategoryDTO]:
        """Return all categories, optionally filtered by entity type and platform.

        Args:
            entity_type: When provided, return only categories scoped to this
                entity type.  When omitted, all categories are returned.
            platform: When provided, return only categories scoped to this
                platform.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`
            objects ordered by sort_order.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_category(
        self,
        name: str,
        slug: str | None = None,
        entity_type: str | None = None,
        description: str | None = None,
        color: str | None = None,
        platform: str | None = None,
        sort_order: int | None = None,
        ctx: RequestContext | None = None,
    ) -> CategoryDTO:
        """Create a new category.

        Args:
            name: Human-readable category name.
            slug: Optional URL-safe slug; auto-generated from *name* when
                omitted.
            entity_type: Optional entity type this category applies to.
                Pass ``None`` for a cross-type (universal) category.
            description: Optional description text.
            color: Optional hex color code for UI display (e.g. ``"#00FF00"``).
            platform: Optional platform scope filter.
            sort_order: Optional explicit display order; auto-computed when
                omitted.
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`.

        Raises:
            ValueError: If a category with the same resolved slug already
                exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_category(
        self,
        category_id: int,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> CategoryDTO:
        """Apply a partial update to an existing category.

        Args:
            category_id: Integer primary key of the category to update.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`.

        Raises:
            KeyError: If no category with *category_id* exists.
            ValueError: If the requested new slug is already taken.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_category(
        self,
        category_id: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a category by integer primary key.

        Args:
            category_id: Integer primary key of the category to delete.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no category with *category_id* exists.
            ValueError: If the category has artifact associations.
        """
        raise NotImplementedError


# =============================================================================
# IGroupRepository
# =============================================================================


class IGroupRepository(abc.ABC):
    """Contract for group storage backends.

    Groups let users organise artifacts within a collection into named,
    position-ordered buckets.  Operations map to the ``/api/v1/groups``
    router.
    """

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_with_artifacts(
        self,
        group_id: int,
        ctx: RequestContext | None = None,
    ) -> GroupDTO | None:
        """Return a group by ID, including its artifact membership list.

        Args:
            group_id: Integer primary key of the group.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.GroupDTO` when the
            group exists (with ``artifact_count`` populated), ``None``
            otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list(
        self,
        collection_id: str,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[GroupDTO]:
        """Return all groups belonging to a collection.

        Args:
            collection_id: Collection unique identifier.
            filters: Optional additional filter map (e.g. ``{"name": "…"}``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.GroupDTO` objects
            ordered by ``position`` ascending.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations — groups
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        name: str,
        collection_id: str,
        description: str | None = None,
        position: int | None = None,
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Create a new group in the given collection.

        Args:
            name: Human-readable group name (must be unique within the
                collection).
            collection_id: Owning collection identifier.
            description: Optional group description.
            position: Explicit display position.  When ``None`` the
                implementation appends the group at the end.
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.GroupDTO`.

        Raises:
            ValueError: If a group with the same *name* already exists in
                *collection_id*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        group_id: int,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Apply a partial update to an existing group's metadata.

        Args:
            group_id: Integer primary key of the group.
            updates: Map of field names to new values (e.g. ``{"name": "…",
                "description": "…"}``).
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.GroupDTO`.

        Raises:
            KeyError: If no group with *group_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        group_id: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a group and all its artifact membership records.

        Args:
            group_id: Integer primary key of the group.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no group with *group_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def copy_to_collection(
        self,
        group_id: int,
        target_collection_id: str,
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Duplicate a group (and its artifact memberships) into another collection.

        Artifact UUIDs are preserved; positions are reset to match the source
        group.

        Args:
            group_id: Integer primary key of the source group.
            target_collection_id: Identifier of the destination collection.
            ctx: Optional per-request metadata.

        Returns:
            The newly created :class:`~skillmeat.core.interfaces.dtos.GroupDTO`
            in the target collection.

        Raises:
            KeyError: If *group_id* or *target_collection_id* does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def reorder_groups(
        self,
        collection_id: str,
        ordered_ids: list[int],
        ctx: RequestContext | None = None,
    ) -> None:
        """Bulk-update the display positions of all groups in a collection.

        The ``position`` of each group is set to its zero-based index in
        *ordered_ids*.

        Args:
            collection_id: Collection unique identifier.
            ordered_ids: Complete list of group primary keys in the desired
                display order.  Must include all groups in the collection.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *ordered_ids* does not contain every group in the
                collection.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations — artifact membership
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def add_artifacts(
        self,
        group_id: int,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        """Add one or more artifacts to a group.

        Artifacts already present in the group are silently skipped.  Newly
        added artifacts are appended after existing members.

        Args:
            group_id: Integer primary key of the target group.
            artifact_uuids: List of stable artifact UUIDs to add.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *group_id* does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_artifact(
        self,
        group_id: int,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Remove a single artifact from a group.

        Args:
            group_id: Integer primary key of the group.
            artifact_uuid: Stable artifact UUID to remove.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *group_id* does not exist or *artifact_uuid* is not
                a member of the group.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_artifact_position(
        self,
        group_id: int,
        artifact_uuid: str,
        position: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Update the display position of a single artifact within a group.

        Args:
            group_id: Integer primary key of the group.
            artifact_uuid: Stable artifact UUID whose position to update.
            position: New zero-based display position.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *group_id* does not exist or *artifact_uuid* is not
                a member of the group.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def reorder_artifacts(
        self,
        group_id: int,
        ordered_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        """Bulk-update the display positions of all artifacts in a group.

        The ``position`` of each membership record is set to the artifact's
        zero-based index in *ordered_uuids*.

        Args:
            group_id: Integer primary key of the group.
            ordered_uuids: Complete list of artifact UUIDs in the desired
                display order.  Must include all current members.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *group_id* does not exist.
            ValueError: If *ordered_uuids* does not cover all current members.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_group_artifacts(
        self,
        group_id: str,
        ctx: RequestContext | None = None,
    ) -> list[GroupArtifactDTO]:
        """Return the ordered list of artifact membership records for a group.

        Args:
            group_id: Group primary key string.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.GroupArtifactDTO`
            objects ordered by ``position`` ascending.  Returns an empty list
            when the group does not exist or has no members.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_artifacts_at_position(
        self,
        group_id: str,
        artifact_uuids: list[str],
        position: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Insert artifacts at a specific position within a group.

        Existing artifacts at or after *position* are shifted down to
        accommodate the new insertions.  Artifacts already in the group
        are silently skipped (deduplicated).

        Args:
            group_id: Group primary key string.
            artifact_uuids: Ordered list of artifact UUIDs to insert.
            position: Zero-based target position for the first inserted artifact.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *group_id* does not exist.
            RuntimeError: On unexpected database errors.
        """
        raise NotImplementedError


# =============================================================================
# IContextEntityRepository
# =============================================================================


class IContextEntityRepository(abc.ABC):
    """Contract for context entity storage backends.

    Context entities are special artifacts (CLAUDE.md, spec files, rule files,
    context files, and progress templates) that define project structure and
    context for Claude Code projects.  Operations map to the
    ``/api/v1/context-entities`` router.
    """

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        after: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[ContextEntityDTO]:
        """Return a page of context entities matching optional filter criteria.

        Filters may include ``entity_type``, ``category``, ``auto_load``, and
        ``search`` (full-text across name, description, path_pattern).

        Args:
            filters: Optional key/value filter map.
            limit: Maximum number of records to return (1-100).
            after: Opaque cursor value for the next page (base64-encoded ID).
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO` objects.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get(
        self,
        entity_id: str,
        ctx: RequestContext | None = None,
    ) -> ContextEntityDTO | None:
        """Return a context entity by its identifier.

        Args:
            entity_id: Artifact primary key (e.g. ``"ctx_abc123"``).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        name: str,
        entity_type: str,
        content: str,
        path_pattern: str,
        description: str | None = None,
        category: str | None = None,
        auto_load: bool = False,
        version: str | None = None,
        target_platforms: list[str] | None = None,
        category_ids: list[int] | None = None,
        ctx: RequestContext | None = None,
    ) -> ContextEntityDTO:
        """Persist a new context entity and return the stored representation.

        Args:
            name: Human-readable entity name.
            entity_type: Entity type key (``"project_config"``,
                ``"spec_file"``, ``"rule_file"``, ``"context_file"``,
                ``"progress_template"``).
            content: Assembled markdown content.
            path_pattern: Target deployment path (must start with
                ``".claude/"`` or a supported prefix).
            description: Optional description.
            category: Optional category label (e.g. ``"api"``).
            auto_load: Whether to auto-load the entity on platform startup.
            version: Optional version string.
            target_platforms: Optional list of platform identifiers to
                target on deploy.
            category_ids: Ordered list of category IDs to associate.
            ctx: Optional per-request metadata.

        Returns:
            The persisted
            :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO`.

        Raises:
            ValueError: If *path_pattern* is invalid or *entity_type* is
                unrecognised.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        entity_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ContextEntityDTO:
        """Apply a partial update to an existing context entity.

        Args:
            entity_id: Artifact primary key.
            updates: Map of field names to new values.  Supported keys mirror
                :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO`
                fields (``name``, ``entity_type``, ``content``,
                ``path_pattern``, ``description``, ``category``,
                ``auto_load``, ``version``, ``target_platforms``,
                ``category_ids``).
            ctx: Optional per-request metadata.

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO`.

        Raises:
            KeyError: If no entity with *entity_id* exists.
            ValueError: If *updates* contains invalid field values.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        entity_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a context entity permanently.

        Args:
            entity_id: Artifact primary key.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no entity with *entity_id* exists.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def deploy(
        self,
        entity_id: str,
        project_path: str,
        options: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> None:
        """Deploy a context entity's content to a filesystem project path.

        Writes the assembled content to the location specified by the entity's
        ``path_pattern``, resolved against *project_path*.

        Args:
            entity_id: Artifact primary key.
            project_path: Absolute filesystem path to the target project
                directory.
            options: Optional deployment options such as ``overwrite``,
                ``deployment_profile_id``, and ``all_profiles``.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *entity_id* does not exist.
            FileExistsError: If the target file already exists and
                ``options["overwrite"]`` is ``False``.
            ValueError: If *project_path* does not exist or *entity_id* has
                no ``path_pattern``.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Content access
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_content(
        self,
        entity_id: str,
        ctx: RequestContext | None = None,
    ) -> str | None:
        """Return the raw markdown content of a context entity.

        Args:
            entity_id: Artifact primary key.
            ctx: Optional per-request metadata.

        Returns:
            Raw content string when the entity exists, ``None`` otherwise.
        """
        raise NotImplementedError


# =============================================================================
# IMarketplaceSourceRepository
# =============================================================================


class IMarketplaceSourceRepository(abc.ABC):
    """Contract for marketplace broker/source configuration backends.

    A marketplace source is a configured endpoint (broker) that provides
    artifact listings for installation.  This interface covers both source
    configuration management and the catalog operations delegated to each
    broker.  Operations map to ``/api/v1/marketplace-sources`` and the
    primary ``/api/v1/marketplace`` router.
    """

    # ------------------------------------------------------------------
    # Source CRUD
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_sources(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[MarketplaceSourceDTO]:
        """Return all configured marketplace sources.

        Args:
            filters: Optional filter map (e.g. ``{"enabled": True}``).
            ctx: Optional per-request metadata.

        Returns:
            List of
            :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_source(
        self,
        source_id: str,
        ctx: RequestContext | None = None,
    ) -> MarketplaceSourceDTO | None:
        """Return a marketplace source by its identifier.

        Args:
            source_id: Source unique identifier (broker name).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
            when found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_source(
        self,
        name: str,
        endpoint: str,
        enabled: bool = True,
        description: str | None = None,
        supports_publish: bool = False,
        ctx: RequestContext | None = None,
    ) -> MarketplaceSourceDTO:
        """Register a new marketplace source.

        Args:
            name: Human-readable source name (must be unique).
            endpoint: Base URL for the broker API.
            enabled: Whether to activate the source immediately.
            description: Optional description of this source.
            supports_publish: Whether the source allows publishing.
            ctx: Optional per-request metadata.

        Returns:
            The created
            :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`.

        Raises:
            ValueError: If a source with the same *name* already exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_source(
        self,
        source_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> MarketplaceSourceDTO:
        """Apply a partial update to a marketplace source configuration.

        Args:
            source_id: Source unique identifier.
            updates: Map of field names to new values (``enabled``,
                ``endpoint``, ``description``, ``supports_publish``).
            ctx: Optional per-request metadata.

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`.

        Raises:
            KeyError: If no source with *source_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_source(
        self,
        source_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Remove a marketplace source configuration.

        Args:
            source_id: Source unique identifier.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no source with *source_id* exists.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Catalog operations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_catalog_items(
        self,
        source_id: str | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        limit: int = 50,
        ctx: RequestContext | None = None,
    ) -> list[CatalogItemDTO]:
        """Return paginated catalog listings from one or all sources.

        Filters may include ``query`` (search term), ``tags``
        (``list[str]``), ``license``, and ``publisher``.

        Args:
            source_id: When provided, restrict results to this broker.
                When ``None``, aggregate listings from all enabled sources.
            filters: Optional key/value filter map.
            page: One-based page number for pagination.
            limit: Maximum number of items per page (1-100).
            ctx: Optional per-request metadata.

        Returns:
            List of
            :class:`~skillmeat.core.interfaces.dtos.CatalogItemDTO` objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def import_item(
        self,
        listing_id: str,
        source_id: str | None = None,
        strategy: str = "keep",
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        """Download and import a marketplace listing into the local collection.

        Args:
            listing_id: Unique identifier of the listing within its broker.
            source_id: Optional broker identifier.  When ``None`` the
                implementation auto-detects the broker that owns this listing.
            strategy: Conflict resolution strategy (``"keep"``, ``"replace"``,
                or ``"fork"``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects representing all imported artifacts.

        Raises:
            KeyError: If *listing_id* is not found in any enabled source.
            ValueError: If *strategy* is not a recognised value.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_composite_members(
        self,
        composite_id: str,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return the child artifacts that make up a composite listing.

        Args:
            composite_id: Artifact primary key of the composite artifact
                (``"composite:<name>"``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects for each member artifact, ordered by ``position``.

        Raises:
            KeyError: If *composite_id* does not exist or is not a composite
                artifact.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Catalog entry mutations (encapsulate direct session access)
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_catalog_entry_raw(
        self,
        entry_id: str,
        source_id: str | None = None,
        ctx: RequestContext | None = None,
    ) -> Any | None:
        """Return the raw ORM catalog entry object for read-only operations.

        Intended for endpoints that must inspect ORM fields not yet covered
        by :class:`~skillmeat.core.interfaces.dtos.CatalogItemDTO`.

        Args:
            entry_id: Catalog entry primary key.
            source_id: When provided, verify that the entry belongs to this
                source; returns ``None`` otherwise.
            ctx: Optional per-request metadata.

        Returns:
            The ORM ``MarketplaceCatalogEntry`` object when found, ``None``
            otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_catalog_entry_exclusion(
        self,
        entry_id: str,
        source_id: str,
        excluded: bool,
        reason: str | None = None,
        ctx: RequestContext | None = None,
    ) -> Any:
        """Toggle the exclusion status of a catalog entry.

        When *excluded* is ``True`` the entry is stamped with ``excluded_at``
        and ``excluded_reason`` and its ``status`` is set to ``"excluded"``.
        When *excluded* is ``False`` the exclusion fields are cleared and
        ``status`` is restored to ``"new"`` or ``"imported"`` depending on
        whether the entry was previously imported.

        Args:
            entry_id: Catalog entry primary key.
            source_id: Source the entry must belong to.
            excluded: ``True`` to exclude, ``False`` to restore.
            reason: Optional reason for the exclusion (ignored when restoring).
            ctx: Optional per-request metadata.

        Returns:
            The updated ORM ``MarketplaceCatalogEntry`` object.

        Raises:
            KeyError: If *entry_id* is not found or does not belong to
                *source_id*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_catalog_entry_path_tags(
        self,
        entry_id: str,
        source_id: str,
        path_segments_json: str,
        ctx: RequestContext | None = None,
    ) -> Any:
        """Persist updated ``path_segments`` JSON for a catalog entry.

        Args:
            entry_id: Catalog entry primary key.
            source_id: Source the entry must belong to.
            path_segments_json: Serialised JSON string for the
                ``path_segments`` column.
            ctx: Optional per-request metadata.

        Returns:
            The updated ORM ``MarketplaceCatalogEntry`` object.

        Raises:
            KeyError: If *entry_id* is not found or does not belong to
                *source_id*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_artifact_row(
        self,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> Any | None:
        """Return the raw ORM ``Artifact`` row for the given ``type:name`` id.

        Used internally by composite-wiring logic that needs the ORM object
        (e.g. to call ``CompositeService``).

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            The ORM ``Artifact`` object when found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upsert_composite_memberships(
        self,
        composite_id: str,
        child_artifact_ids: list[str],
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> int:
        """Create or update ``CompositeMembership`` rows for a composite artifact.

        For each child artifact ID the method resolves the ``Artifact.uuid``
        and inserts a ``CompositeMembership`` row if one does not already exist.
        Existing rows are updated to reflect the current position.

        Args:
            composite_id: Primary key of the composite artifact
                (``"composite:<name>"``).
            child_artifact_ids: Ordered list of child ``type:name`` artifact
                primary keys.
            collection_id: Collection the composite belongs to.
            ctx: Optional per-request metadata.

        Returns:
            Number of new membership rows created.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def commit_source_session(
        self,
        ctx: RequestContext | None = None,
    ) -> None:
        """Flush pending changes on the source repository session.

        Convenience wrapper used when mutations have been applied directly to
        ORM objects retrieved via the source repository's own session and those
        changes must be persisted without opening a new transaction.

        Args:
            ctx: Optional per-request metadata.
        """
        raise NotImplementedError


# =============================================================================
# IProjectTemplateRepository
# =============================================================================


class IProjectTemplateRepository(abc.ABC):
    """Contract for project template storage backends.

    Project templates are reusable collections of context entities that can
    be deployed together to initialise Claude Code project structures.
    Templates support variable substitution for customisation.  Operations
    map to the ``/api/v1/project-templates`` router.
    """

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: RequestContext | None = None,
    ) -> list[ProjectTemplateDTO]:
        """Return a page of project templates.

        Args:
            filters: Optional key/value filter map (e.g.
                ``{"collection_id": "default"}``).
            limit: Maximum number of records to return (1-100).
            offset: Zero-based record offset for pagination.
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.ProjectTemplateDTO`
            objects ordered by ``created_at`` descending.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> int:
        """Return the total number of project templates matching optional filters.

        Args:
            filters: Optional key/value filter map (same keys as :meth:`list`).
            ctx: Optional per-request metadata.

        Returns:
            Integer count of matching project templates.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get(
        self,
        template_id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectTemplateDTO | None:
        """Return a project template by its identifier, including full entity details.

        Args:
            template_id: Template hex-UUID identifier.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.ProjectTemplateDTO`
            (with ``entities`` populated) when found, ``None`` otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        name: str,
        entity_ids: list[str],
        description: str | None = None,
        collection_id: str | None = None,
        default_project_config_id: str | None = None,
        ctx: RequestContext | None = None,
    ) -> ProjectTemplateDTO:
        """Create a new project template from an ordered list of entity IDs.

        Args:
            name: Human-readable template name (must be unique).
            entity_ids: Ordered list of artifact primary keys to include.
                The deploy order is derived from the list order.
            description: Optional template description.
            collection_id: Optional owning collection identifier.
            default_project_config_id: Optional artifact ID of the default
                CLAUDE.md config to include.
            ctx: Optional per-request metadata.

        Returns:
            The created
            :class:`~skillmeat.core.interfaces.dtos.ProjectTemplateDTO`
            with full entity details.

        Raises:
            ValueError: If any element of *entity_ids* does not correspond
                to a known artifact.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        template_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ProjectTemplateDTO:
        """Apply a partial update to an existing project template.

        Supported update keys: ``name``, ``description``, ``entity_ids``
        (full replacement of the entity list).

        Args:
            template_id: Template hex-UUID identifier.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.ProjectTemplateDTO`.

        Raises:
            KeyError: If no template with *template_id* exists.
            ValueError: If ``entity_ids`` contains unknown artifact IDs.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        template_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a project template and all its entity associations.

        Args:
            template_id: Template hex-UUID identifier.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no template with *template_id* exists.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def deploy(
        self,
        template_id: str,
        project_path: str,
        options: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> dict[str, Any]:
        """Deploy all template entities to a target project directory.

        Performs variable substitution (if ``options["variables"]`` is
        provided) and writes each entity's content to the path resolved
        from ``path_pattern`` relative to *project_path*.

        Args:
            template_id: Template hex-UUID identifier.
            project_path: Absolute filesystem path to the target project
                directory.
            options: Optional deployment options, including:
                - ``variables`` (``dict[str, str]``): substitution variables,
                - ``selected_entity_ids`` (``list[str]``): subset of entities
                  to deploy (default: all),
                - ``overwrite`` (``bool``): overwrite existing files
                  (default: ``False``),
                - ``deployment_profile_id`` (``str``): profile to use.
            ctx: Optional per-request metadata.

        Returns:
            Result mapping with at minimum ``success`` (bool),
            ``deployed_files`` (list[str]), ``skipped_files`` (list[str]),
            and ``message`` (str).

        Raises:
            KeyError: If *template_id* does not exist.
            ValueError: If *project_path* does not exist or is invalid.
        """
        raise NotImplementedError


# =============================================================================
# IDbCollectionArtifactRepository
# =============================================================================


class IDbCollectionArtifactRepository(abc.ABC):
    """Repository ABC for DB-backed collection artifact membership.

    Covers the :class:`~skillmeat.cache.models.CollectionArtifact` ORM join
    table that tracks which artifacts belong to which user collections.
    All operations are scoped to a *collection_id* and operate on
    ``artifact_uuid`` stable identifiers (ADR-007).

    Operations map to the artifact-membership sub-resources of the
    ``/api/v1/user-collections`` router.
    """

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_by_collection(
        self,
        collection_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        artifact_type: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[CollectionArtifactDTO]:
        """Return a paginated list of artifact memberships for a collection.

        Args:
            collection_id: Unique identifier of the owning user collection.
            limit: Maximum number of records to return (default 50).
            offset: Zero-based pagination offset (default 0).
            search: Optional free-text search applied to artifact name or
                description fields.
            artifact_type: Optional artifact type filter
                (e.g. ``"skill"``, ``"command"``).
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_pk(
        self,
        collection_id: str,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
    ) -> CollectionArtifactDTO | None:
        """Return a single membership record by composite primary key.

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_uuid: Stable 32-char hex UUID of the artifact.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            when the membership exists, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count_by_collection(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> int:
        """Return the total number of artifacts in a collection.

        Intended to back ``page_info.total`` in paginated list responses.

        Args:
            collection_id: Unique identifier of the user collection.
            ctx: Optional per-request metadata.

        Returns:
            Non-negative integer count of collection memberships.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_with_tags(
        self,
        collection_id: str,
        *,
        tag: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[CollectionArtifactDTO]:
        """Return collection artifact memberships, optionally filtered by tag.

        Args:
            collection_id: Unique identifier of the user collection.
            tag: Optional tag name to filter by.  When provided, only
                memberships whose artifact carries this tag are returned.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            objects (possibly empty).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_deployment_info(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> list[CollectionArtifactDTO]:
        """Return collection memberships enriched with deployment tracking data.

        The returned DTOs include ``source``, ``origin``, ``resolved_sha``,
        ``resolved_version``, and ``synced_at`` fields where available.

        Args:
            collection_id: Unique identifier of the user collection.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            objects with deployment fields populated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_source_deployments_batch(
        self,
        artifact_ids: list[str],
        ctx: RequestContext | None = None,
    ) -> list[dict]:
        """Return source and deployments_json for a batch of artifact IDs.

        Executes a single JOIN query against the ``artifacts`` and
        ``collection_artifacts`` tables to retrieve the ``source`` and
        ``deployments_json`` columns for the given ``type:name`` artifact
        identifiers.

        Args:
            artifact_ids: List of ``"type:name"`` artifact identifier strings.
            ctx: Optional per-request metadata.

        Returns:
            List of dicts, each containing keys ``id`` (the ``type:name``
            artifact ID string), ``source`` (upstream source spec or ``None``),
            and ``deployments_json`` (raw JSON string or ``None``).  Only
            artifacts that have a matching ``CollectionArtifact`` row are
            included in the result.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def add_artifacts(
        self,
        collection_id: str,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> list[CollectionArtifactDTO]:
        """Add one or more artifacts to a collection by UUID.

        Idempotent: artifacts already present in the collection are
        silently skipped rather than duplicated.

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_uuids: List of stable 32-char hex UUIDs to add.
            ctx: Optional per-request metadata.

        Returns:
            List of created (or pre-existing)
            :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            records for the given UUIDs.

        Raises:
            KeyError: If *collection_id* does not correspond to a known
                user collection.
            ValueError: If any UUID in *artifact_uuids* is unknown.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_artifact(
        self,
        collection_id: str,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Remove a single artifact from a collection.

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_uuid: Stable 32-char hex UUID of the artifact to remove.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the membership was found and removed,
            ``False`` when no matching membership existed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upsert_metadata(
        self,
        collection_id: str,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
        **metadata: Any,
    ) -> CollectionArtifactDTO:
        """Create or update arbitrary metadata fields on a membership record.

        If the membership does not yet exist it is created with the supplied
        metadata.  If it already exists, only the provided fields are updated
        (partial update semantics).

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_uuid: Stable 32-char hex UUID of the artifact.
            ctx: Optional per-request metadata.
            **metadata: Keyword arguments corresponding to writable fields
                on :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
                (e.g. ``description``, ``notes``, ``custom_tags``).

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`.

        Raises:
            ValueError: If any key in *metadata* is not a recognised field.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_source_tracking(
        self,
        collection_id: str,
        artifact_uuid: str,
        *,
        source: str | None = None,
        origin: str | None = None,
        resolved_sha: str | None = None,
        resolved_version: str | None = None,
        ctx: RequestContext | None = None,
    ) -> CollectionArtifactDTO:
        """Update upstream source-tracking fields on a membership record.

        Used by the sync subsystem to record the resolved upstream coordinates
        for an artifact after a fetch or sync operation.

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_uuid: Stable 32-char hex UUID of the artifact.
            source: Optional GitHub source spec
                (e.g. ``"owner/repo/path@version"``).
            origin: Optional human-readable origin label
                (e.g. ``"github"``).
            resolved_sha: Optional resolved commit SHA for the artifact.
            resolved_version: Optional resolved semantic version string.
            ctx: Optional per-request metadata.

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`.

        Raises:
            KeyError: If no membership for *(collection_id, artifact_uuid)*
                exists.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Bootstrap / migration helpers
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_existing_artifact_ids(self) -> set[str]:
        """Return the set of all ``type:name`` Artifact IDs currently in the DB.

        Used during bootstrap to avoid redundant INSERT attempts for artifact
        rows that already exist.

        Returns:
            Set of ``"type:name"`` strings (e.g. ``{"skill:canvas", ...}``).
            Returns an empty set when no artifact rows exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ensure_artifact_rows(
        self,
        artifacts: list,
        *,
        project_id: str,
    ) -> int:
        """Ensure every filesystem artifact has a corresponding Artifact ORM row.

        Idempotent: artifacts already present in the ``artifacts`` table are
        skipped.  Inserts are committed as a single transaction.

        Args:
            artifacts: List of filesystem :class:`~skillmeat.core.artifact.Artifact`
                objects whose ``type``, ``name``, ``upstream``, and ``metadata``
                attributes are used to build the Artifact ORM row.
            project_id: Sentinel project ID assigned as ``project_id`` FK on
                every inserted row.

        Returns:
            Number of new Artifact rows inserted.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_artifact_ids_in_collection(
        self,
        collection_id: str,
    ) -> set[str]:
        """Return the set of ``type:name`` Artifact IDs present in a collection.

        Resolves UUIDs back to ``type:name`` strings by joining through the
        ``artifacts`` table so that callers can use set arithmetic against
        filesystem artifact lists.

        Args:
            collection_id: Unique identifier of the user collection.

        Returns:
            Set of ``"type:name"`` strings for all artifacts in the collection.
            Returns an empty set when the collection has no members.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def resolve_uuid_by_id(
        self,
        artifact_id: str,
    ) -> str | None:
        """Resolve the stable UUID for an artifact by its ``type:name`` ID.

        Args:
            artifact_id: ``"type:name"`` artifact identifier string.

        Returns:
            32-char hex UUID string when found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_all_with_tags(self) -> list[CollectionArtifactDTO]:
        """Return all CollectionArtifact rows that carry at least one tag.

        Unlike :meth:`list_with_tags`, this method is not scoped to a single
        collection and is intended for global tag-sync bootstrap operations.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            objects with ``tags_json`` populated.  Returns an empty list when
            no tagged rows exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def resolve_uuid_to_id_batch(
        self,
        uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> dict[str, str]:
        """Batch-resolve artifact UUIDs to ``type:name`` ID strings.

        Executes a single query against the ``artifacts`` table and returns a
        mapping from 32-char hex UUID to the corresponding ``type:name`` ID
        string for every UUID in *uuids* that exists in the database.

        Args:
            uuids: List of 32-char hex UUID strings to resolve.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Dict mapping ``artifact_uuid`` → ``type:name`` ID.  UUIDs not
            found in the database are omitted from the result.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_all_ordered(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> list[CollectionArtifactDTO]:
        """Return all memberships for a collection ordered by artifact ``type:name`` ID.

        Joins through the ``artifacts`` table to order results by the stable
        ``Artifact.id`` string (``type:name``), enabling stable cursor-based
        pagination at the endpoint layer.

        Args:
            collection_id: Unique identifier of the user collection.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            All :class:`~skillmeat.core.interfaces.dtos.CollectionArtifactDTO`
            records for the collection, ordered by artifact ID.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_group_artifact_uuids(
        self,
        group_id: str,
        ctx: RequestContext | None = None,
    ) -> set[str]:
        """Return the set of artifact UUIDs belonging to a group.

        Args:
            group_id: Unique identifier of the group.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Set of 32-char hex UUID strings.  Empty set when the group has no
            members or does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_source_for_uuids(
        self,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> dict[str, str]:
        """Return a mapping from ``type:name`` ID to source value for a batch.

        Joins ``artifacts`` to ``collection_artifacts`` and returns the
        ``source`` column for each UUID in *artifact_uuids* that has a
        non-null source.

        Args:
            artifact_uuids: List of 32-char hex UUID strings to look up.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Dict mapping ``type:name`` artifact ID → source string.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_group_memberships_batch(
        self,
        artifact_uuids: list[str],
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> list[dict]:
        """Return group-membership rows for a batch of artifact UUIDs.

        Args:
            artifact_uuids: List of 32-char hex UUID strings.
            collection_id: Scope results to groups belonging to this
                collection.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            List of dicts, each with keys:
            - ``artifact_id``: ``"type:name"`` identifier of the artifact
            - ``group_id``: Unique identifier of the group
            - ``group_name``: Display name of the group
            - ``position``: Integer position of the artifact within the group
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_staleness_stats(
        self,
        collection_id: str,
        ttl_seconds: int,
        ctx: RequestContext | None = None,
    ) -> dict:
        """Return staleness statistics for a collection.

        Computes counts of fresh vs stale memberships based on
        ``CollectionArtifact.synced_at`` relative to *ttl_seconds*.

        Args:
            collection_id: Unique identifier of the collection to analyse.
            ttl_seconds: Age in seconds after which a membership is
                considered stale.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Dict with keys: ``total_artifacts``, ``stale_count``,
            ``fresh_count``, ``oldest_sync_age_seconds``,
            ``percentage_stale``, ``ttl_seconds``, ``collection_id``.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_deployments_by_name(
        self,
        collection_id: str,
        artifact_name: str,
        deployments_json: str,
        ctx: RequestContext | None = None,
    ) -> int:
        """Update ``deployments_json`` on all memberships matching *artifact_name*.

        Finds all ``Artifact`` rows whose ``name`` column equals *artifact_name*
        and updates the corresponding ``CollectionArtifact.deployments_json``
        column within the specified collection.

        Args:
            collection_id: Unique identifier of the user collection.
            artifact_name: Short artifact name (without the ``type:`` prefix).
            deployments_json: Serialised JSON string to store in
                ``deployments_json``.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Number of rows updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def bulk_update_metadata(
        self,
        updates: list[dict],
        ctx: RequestContext | None = None,
    ) -> int:
        """Apply metadata field updates to multiple membership rows.

        Each element of *updates* must contain an ``artifact_uuid`` key that
        identifies the row to update plus any combination of the recognised
        metadata fields (``description``, ``author``, ``license``, ``version``,
        ``tags_json``, ``tools_json``, ``source``, ``origin``,
        ``origin_source``, ``resolved_sha``, ``resolved_version``,
        ``synced_at``).  Unknown keys are silently ignored.

        Args:
            updates: List of dicts, each with ``artifact_uuid`` and the fields
                to write.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            Number of rows successfully updated.
        """
        raise NotImplementedError


# =============================================================================
# IDbUserCollectionRepository
# =============================================================================


class IDbUserCollectionRepository(abc.ABC):
    """Contract for DB-backed user collection storage backends.

    User collections are named, persisted groups of artifacts stored in the
    ``Collection`` ORM model.  Unlike the filesystem-oriented
    :class:`ICollectionRepository`, this interface operates entirely against
    the DB cache and supports multi-collection, filtered queries, and
    group associations.  Operations back the ``/api/v1/user-collections``
    router.
    """

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list(
        self,
        *,
        created_by: str | None = None,
        collection_type: str | None = None,
        context_category: str | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: RequestContext | None = None,
    ) -> list[UserCollectionDTO]:
        """Return a filtered, paginated list of user collections.

        Args:
            created_by: When provided, return only collections owned by this
                user/agent identifier.
            collection_type: When provided, restrict to collections of this
                type (e.g. ``"default"``, ``"user"``).
            context_category: When provided, restrict to collections tagged
                with this context category string.
            limit: Maximum number of records to return.
            offset: Zero-based record offset for pagination.
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` objects.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_by_id(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> UserCollectionDTO | None:
        """Return a user collection by its UUID.

        Args:
            collection_id: Collection hex-UUID primary key.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_name(
        self,
        name: str,
        ctx: RequestContext | None = None,
    ) -> UserCollectionDTO | None:
        """Return a user collection by its human-readable name.

        Args:
            name: Collection name string (case-sensitive).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def create(
        self,
        *,
        name: str,
        description: str | None = None,
        created_by: str | None = None,
        collection_type: str | None = None,
        context_category: str | None = None,
        ctx: RequestContext | None = None,
    ) -> UserCollectionDTO:
        """Persist a new user collection and return the stored representation.

        Args:
            name: Human-readable collection name.  Must be unique within the
                scope of *created_by*.
            description: Optional free-text description.
            created_by: Optional owner identifier (user ID or agent name).
            collection_type: Optional type discriminator (e.g. ``"default"``).
            context_category: Optional context category tag string.
            ctx: Optional per-request metadata.

        Returns:
            The persisted
            :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO`.

        Raises:
            ValueError: If a collection with the same *name* already exists
                for the given *created_by*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
        **kwargs: Any,
    ) -> UserCollectionDTO:
        """Apply a partial update to an existing user collection.

        Only provided keyword arguments are changed; unmentioned fields remain
        at their current values.  Recognised keys mirror
        :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` fields:
        ``name``, ``description``, ``collection_type``, ``context_category``.

        Args:
            collection_id: Collection hex-UUID primary key.
            ctx: Optional per-request metadata.
            **kwargs: Field names to new values for the partial update.

        Returns:
            The updated
            :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO`.

        Raises:
            KeyError: If no collection with *collection_id* exists.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Delete a user collection and all its membership records.

        Does not delete artifact files — only removes the DB collection record
        and associated ``CollectionArtifact`` rows.

        Args:
            collection_id: Collection hex-UUID primary key.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the collection was found and deleted, ``False``
            when no matching record existed.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Default collection management
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def ensure_default(
        self,
        *,
        created_by: str | None = None,
        ctx: RequestContext | None = None,
    ) -> UserCollectionDTO:
        """Return the default collection, creating it if it does not exist.

        The implementation must be idempotent: concurrent callers must not
        produce duplicate default collections.

        Args:
            created_by: Optional owner identifier.  When provided the default
                collection is scoped to this owner.
            ctx: Optional per-request metadata.

        Returns:
            The existing or newly created default
            :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO`.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Enriched queries
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_with_artifact_stats(
        self,
        *,
        created_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: RequestContext | None = None,
    ) -> list[UserCollectionDTO]:
        """Return collections with ``artifact_count`` and ``total_size_bytes`` populated.

        Performs an aggregation join so that the returned DTOs carry up-to-date
        counts without additional round-trips by the caller.

        Args:
            created_by: When provided, return only collections owned by this
                identifier.
            limit: Maximum number of records to return.
            offset: Zero-based record offset for pagination.
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` objects
            with ``artifact_count`` and ``total_size_bytes`` set.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Group associations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def add_group(
        self,
        collection_id: str,
        group_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Associate an existing group with a user collection.

        Idempotent: associating a group that is already linked is a no-op and
        returns ``True``.

        Args:
            collection_id: Collection hex-UUID primary key.
            group_id: Group identifier to associate.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` on success (including when the association already existed),
            ``False`` when *collection_id* or *group_id* does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_group(
        self,
        collection_id: str,
        group_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        """Disassociate a group from a user collection.

        Args:
            collection_id: Collection hex-UUID primary key.
            group_id: Group identifier to remove.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the association existed and was removed, ``False``
            if the association was not found.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_groups(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> list[str]:
        """Return the identifiers of all groups associated with a collection.

        Args:
            collection_id: Collection hex-UUID primary key.
            ctx: Optional per-request metadata.

        Returns:
            List of group identifier strings.  Returns an empty list when the
            collection does not exist or has no group associations.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Aggregate helpers
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_artifact_count(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> int:
        """Return the number of artifacts currently in a collection.

        Args:
            collection_id: Collection hex-UUID primary key.
            ctx: Optional per-request metadata.

        Returns:
            Non-negative integer artifact count.  Returns ``0`` when the
            collection does not exist.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Sentinel project bootstrap
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def ensure_sentinel_project(self) -> None:
        """Ensure the sentinel Project row used by collection artifacts exists.

        Artifact rows require a ``project_id`` foreign-key.  Collection-level
        (filesystem) artifacts are not tied to any deployed project, so a
        sentinel project row satisfies the constraint.  The sentinel ID is
        the module-level constant ``COLLECTION_ARTIFACTS_PROJECT_ID``.

        This method is idempotent: if the sentinel row already exists the
        call is a no-op.
        """
        raise NotImplementedError


# =============================================================================
# IDbArtifactHistoryRepository
# =============================================================================


class IDbArtifactHistoryRepository(abc.ABC):
    """Repository ABC for artifact history queries.

    Encapsulates the two cache-model lookups and the version-lineage query
    used by the ``/api/v1/artifacts/{id}/history`` endpoint so that the
    router holds no raw SQLAlchemy session references.

    All methods are read-only; the history endpoint does not mutate state.
    """

    # ------------------------------------------------------------------
    # Artifact lookups
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_cache_artifact_by_uuid(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> CacheArtifactSummaryDTO | None:
        """Return a summary of the ``artifacts`` row identified by UUID.

        Args:
            uuid: Stable 32-char hex UUID (ADR-007 identity).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CacheArtifactSummaryDTO`
            when the artifact exists, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_cache_artifacts_by_name_type(
        self,
        name: str,
        artifact_type: str,
        ctx: RequestContext | None = None,
    ) -> list[CacheArtifactSummaryDTO]:
        """Return all ``artifacts`` rows matching *name* and *artifact_type*.

        Multiple rows can exist for the same logical artifact because each
        deployed project has its own row.

        Args:
            name: Artifact name (normalised, without file extension).
            artifact_type: Artifact type string (e.g. ``"skill"``).
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.CacheArtifactSummaryDTO`.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Version lineage
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def list_versions_for_artifacts(
        self,
        artifact_ids: list[str],
        ctx: RequestContext | None = None,
    ) -> list[ArtifactVersionDTO]:
        """Return version lineage records for a set of artifact primary keys.

        Args:
            artifact_ids: List of ``artifacts.id`` values (``type:name``
                strings).  The query is skipped and an empty list returned
                when *artifact_ids* is empty.
            ctx: Optional per-request metadata.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.ArtifactVersionDTO`
            ordered by ``created_at`` descending.
        """
        raise NotImplementedError
