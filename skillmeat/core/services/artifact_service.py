"""Artifact service layer for SkillMeat core.

Provides a thin orchestration layer between API routers and the
IArtifactRepository interface.  Every public method accepts an optional
``auth_context`` parameter; when omitted (or ``None``) the call falls back
to ``LOCAL_ADMIN_CONTEXT`` so that local zero-auth deployments continue to
work without change.

References:
    .claude/progress/aaa-rbac-foundation/  SVR-007
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from skillmeat.core.interfaces.repositories import IArtifactRepository
from skillmeat.core.interfaces.dtos import ArtifactDTO, TagDTO

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext

logger = logging.getLogger(__name__)


class ArtifactService:
    """Orchestration service for artifact operations.

    Wraps an :class:`~skillmeat.core.interfaces.repositories.IArtifactRepository`
    and threads :class:`~skillmeat.api.schemas.auth.AuthContext` through every
    repository call.  When ``auth_context`` is ``None`` the service substitutes
    ``LOCAL_ADMIN_CONTEXT`` so that local zero-auth deployments remain fully
    functional.

    Args:
        repo: Concrete artifact repository implementation.

    Example::

        from skillmeat.core.services.artifact_service import ArtifactService

        service = ArtifactService(repo=artifact_repo)
        artifact = service.get("skill:canvas")
        artifacts = service.list(filters={"artifact_type": "skill"})
    """

    def __init__(self, repo: IArtifactRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_auth(auth_context: AuthContext | None) -> AuthContext:
        """Return *auth_context* or ``LOCAL_ADMIN_CONTEXT`` as the fallback.

        The import is deferred to avoid potential circular imports at module
        load time.  ``LOCAL_ADMIN_CONTEXT`` is a plain constant so there is
        no runtime cost beyond the first import.
        """
        if auth_context is None:
            from skillmeat.api.schemas.auth import LOCAL_ADMIN_CONTEXT

            return LOCAL_ADMIN_CONTEXT
        return auth_context

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return the artifact identified by ``type:name`` primary key.

        Args:
            id: Artifact primary key in ``"type:name"`` format.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when
            found, ``None`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get(id, auth_context=ctx)

    def get_by_uuid(
        self,
        uuid: str,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return the artifact identified by its stable UUID.

        Args:
            uuid: 32-char hex UUID string.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when
            found, ``None`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_by_uuid(uuid, auth_context=ctx)

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return a page of artifacts matching optional filter criteria.

        Args:
            filters: Optional key/value filter map.
            offset: Zero-based record offset for pagination.
            limit: Maximum number of records to return.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` objects.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.list(filters=filters, offset=offset, limit=limit, auth_context=ctx)

    def count(
        self,
        filters: dict[str, Any] | None = None,
        auth_context: AuthContext | None = None,
    ) -> int:
        """Return the total number of artifacts matching optional filter criteria.

        Args:
            filters: Same filter map accepted by :meth:`list`.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Non-negative integer count.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.count(filters=filters, auth_context=ctx)

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Full-text / fuzzy search across artifact names and metadata.

        Args:
            query: Free-form search string.
            filters: Optional additional filter constraints.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Ranked list of matching
            :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` objects.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.search(query, filters=filters, auth_context=ctx)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        dto: ArtifactDTO,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO:
        """Persist a new artifact record and return the stored representation.

        Args:
            dto: Fully populated artifact data.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            The persisted :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.create(dto, auth_context=ctx)

    def update(
        self,
        id: str,
        updates: dict[str, Any],
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO:
        """Apply a partial update to an existing artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            updates: Map of field names to new values.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`.

        Raises:
            KeyError: If no artifact with *id* exists.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.update(id, updates, auth_context=ctx)

    def delete(
        self,
        id: str,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Delete an artifact and all its associated records.

        Args:
            id: Artifact primary key (``"type:name"``).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            ``True`` when the artifact was found and deleted, ``False`` when
            no matching record existed.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.delete(id, auth_context=ctx)

    # ------------------------------------------------------------------
    # File-content access
    # ------------------------------------------------------------------

    def get_content(
        self,
        id: str,
        auth_context: AuthContext | None = None,
    ) -> str:
        """Return the raw text content of an artifact's primary file.

        Args:
            id: Artifact primary key (``"type:name"``).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            File content as a UTF-8 string.

        Raises:
            KeyError: If no artifact with *id* exists.
            FileNotFoundError: If the content file cannot be located.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_content(id, auth_context=ctx)

    def update_content(
        self,
        id: str,
        content: str,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Overwrite the primary file content of an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            content: New file content (UTF-8 string).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            ``True`` on success.

        Raises:
            KeyError: If no artifact with *id* exists.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.update_content(id, content, auth_context=ctx)

    # ------------------------------------------------------------------
    # Tag associations
    # ------------------------------------------------------------------

    def get_tags(
        self,
        id: str,
        auth_context: AuthContext | None = None,
    ) -> list[TagDTO]:
        """Return all tags currently assigned to an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.TagDTO` objects.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_tags(id, auth_context=ctx)

    def set_tags(
        self,
        id: str,
        tag_ids: list[str],
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Replace the complete tag set for an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            tag_ids: New complete list of tag IDs.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            ``True`` on success.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.set_tags(id, tag_ids, auth_context=ctx)

    # ------------------------------------------------------------------
    # UUID resolution
    # ------------------------------------------------------------------

    def resolve_uuid_by_type_name(
        self,
        artifact_type: str,
        name: str,
        auth_context: AuthContext | None = None,
    ) -> str | None:
        """Resolve the stable UUID for an artifact identified by type and name.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``).
            name: Artifact name string.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            32-char hex UUID string when found, ``None`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.resolve_uuid_by_type_name(artifact_type, name, auth_context=ctx)

    def get_ids_by_uuids(
        self,
        uuids: list[str],
        auth_context: AuthContext | None = None,
    ) -> dict[str, str]:
        """Batch-map artifact UUIDs to their ``type:name`` ID strings.

        Args:
            uuids: List of 32-char hex UUID strings to look up.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Dict mapping each UUID to its ``"type:name"`` artifact ID string.
            Unresolvable UUIDs are omitted.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_ids_by_uuids(uuids, auth_context=ctx)

    def batch_resolve_uuids(
        self,
        artifacts: list[tuple[str, str]],
        auth_context: AuthContext | None = None,
    ) -> dict[tuple[str, str], str]:
        """Batch-resolve UUIDs for multiple ``(artifact_type, name)`` pairs.

        Args:
            artifacts: List of ``(artifact_type, name)`` tuples.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Dict mapping each ``(artifact_type, name)`` tuple to its 32-char
            hex UUID.  Unresolvable pairs are omitted.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.batch_resolve_uuids(artifacts, auth_context=ctx)

    # ------------------------------------------------------------------
    # Collection-context queries
    # ------------------------------------------------------------------

    def get_with_collection_context(
        self,
        uuid: str,
        auth_context: AuthContext | None = None,
    ) -> ArtifactDTO | None:
        """Return an artifact with enriched collection-membership context.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            An :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` when
            found (with collection context populated where available),
            ``None`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_with_collection_context(uuid, auth_context=ctx)

    def get_collection_memberships(
        self,
        uuid: str,
        auth_context: AuthContext | None = None,
    ) -> list:
        """Return all collections that contain the artifact identified by *uuid*.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of
            :class:`~skillmeat.core.interfaces.dtos.CollectionMembershipDTO`
            objects, one per collection membership.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_collection_memberships(uuid, auth_context=ctx)

    def get_collection_description(
        self,
        uuid: str,
        auth_context: AuthContext | None = None,
    ) -> str | None:
        """Return the collection-level description for an artifact.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Collection-level description string, or ``None`` when not set.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_collection_description(uuid, auth_context=ctx)

    # ------------------------------------------------------------------
    # Deduplication cluster queries
    # ------------------------------------------------------------------

    def get_duplicate_cluster_members(
        self,
        cluster_id: str,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return all artifacts that belong to the given deduplication cluster.

        Args:
            cluster_id: Opaque cluster identifier (implementation-defined).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects representing every cluster member.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_duplicate_cluster_members(cluster_id, auth_context=ctx)

    # ------------------------------------------------------------------
    # Existence and type queries
    # ------------------------------------------------------------------

    def validate_exists(
        self,
        uuid: str,
        auth_context: AuthContext | None = None,
    ) -> bool:
        """Check whether an artifact with the given UUID exists.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            ``True`` when an artifact with *uuid* exists, ``False`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.validate_exists(uuid, auth_context=ctx)

    def get_by_type(
        self,
        artifact_type: str,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return all artifacts of the specified type.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``, ``"command"``).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects matching *artifact_type*.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_by_type(artifact_type, auth_context=ctx)

    # ------------------------------------------------------------------
    # Collection-level mutations
    # ------------------------------------------------------------------

    def update_collection_tags(
        self,
        uuid: str,
        tags: list[str],
        auth_context: AuthContext | None = None,
    ) -> None:
        """Replace the collection-level tags for an artifact.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            tags: New complete list of tag name strings.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If no artifact with *uuid* exists.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.update_collection_tags(uuid, tags, auth_context=ctx)
