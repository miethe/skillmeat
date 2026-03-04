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
from typing import Any

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    CollectionDTO,
    DeploymentDTO,
    ProjectDTO,
    SettingsDTO,
    TagDTO,
)

__all__ = [
    "IArtifactRepository",
    "IProjectRepository",
    "ICollectionRepository",
    "IDeploymentRepository",
    "ITagRepository",
    "ISettingsRepository",
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
    ) -> ArtifactDTO | None:
        """Return the artifact with the given ``type:name`` primary key.

        Args:
            id: Artifact primary key in ``"type:name"`` format
                (e.g. ``"skill:frontend-design"``).
            ctx: Optional per-request metadata.

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
    ) -> ArtifactDTO | None:
        """Return the artifact identified by its stable UUID.

        The UUID is the ADR-007 identity and remains stable across renames.

        Args:
            uuid: 32-char hex UUID string.
            ctx: Optional per-request metadata.

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
    ) -> int:
        """Return the total number of artifacts matching optional filter criteria.

        Intended to back ``page_info.total`` in paginated list responses.

        Args:
            filters: Same filter map accepted by :meth:`list`.
            ctx: Optional per-request metadata.

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
    ) -> list[ArtifactDTO]:
        """Full-text / fuzzy search across artifact names and metadata.

        Args:
            query: Free-form search string.
            filters: Optional additional filter constraints applied on top
                of the text match.
            ctx: Optional per-request metadata.

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
    ) -> ArtifactDTO:
        """Persist a new artifact record and return the stored representation.

        Args:
            dto: Fully populated artifact data.  The implementation may
                ignore ``created_at`` / ``updated_at`` and set them itself.
            ctx: Optional per-request metadata.

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
    ) -> ArtifactDTO:
        """Apply a partial update to an existing artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            updates: Map of field names to new values.  Only provided
                fields are changed; others remain untouched.
            ctx: Optional per-request metadata.

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
    ) -> bool:
        """Delete an artifact and all its associated records.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

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
    ) -> str:
        """Return the raw text content of an artifact's primary file.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

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
    ) -> bool:
        """Overwrite the primary file content of an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            content: New file content (UTF-8 string).
            ctx: Optional per-request metadata.

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
    ) -> list[TagDTO]:
        """Return all tags currently assigned to an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata.

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
    ) -> bool:
        """Replace the complete tag set for an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            tag_ids: New complete list of tag IDs.  Any previous tags not
                present in this list are removed.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` on success.
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
    ) -> CollectionDTO | None:
        """Return the active collection metadata.

        Args:
            ctx: Optional per-request metadata.

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
    ) -> CollectionDTO | None:
        """Return a specific collection by its identifier.

        Args:
            id: Collection unique identifier (usually the collection name).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` when
            found, ``None`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list(
        self,
        ctx: RequestContext | None = None,
    ) -> list[CollectionDTO]:
        """Return all known collections.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`
            objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_stats(
        self,
        ctx: RequestContext | None = None,
    ) -> dict[str, Any]:
        """Return aggregate statistics for the active collection.

        The returned dictionary should contain at minimum:
        ``artifact_count``, ``total_size_bytes``, ``last_synced``.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            Plain dictionary of stat key/value pairs.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def refresh(
        self,
        ctx: RequestContext | None = None,
    ) -> CollectionDTO:
        """Re-scan the filesystem and rebuild the collection cache.

        Args:
            ctx: Optional per-request metadata.

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
    ) -> list[ArtifactDTO]:
        """Return the artifacts that belong to a collection.

        Args:
            collection_id: Collection unique identifier.
            filters: Optional filter constraints (e.g. ``artifact_type``).
            offset: Zero-based pagination offset.
            limit: Maximum number of records to return.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects.
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
