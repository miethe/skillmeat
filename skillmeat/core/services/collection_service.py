"""Collection service layer for SkillMeat core.

Provides a thin orchestration layer between API routers and the
ICollectionRepository interface.  Every public method accepts an optional
``auth_context`` parameter; when omitted (or ``None``) the call falls back
to ``LOCAL_ADMIN_CONTEXT`` so that local zero-auth deployments continue to
work without change.

Note: This is the *core* collection service that wraps ICollectionRepository.
It is distinct from ``skillmeat.api.services.collection_service``, which
provides DB-layer collection membership batch queries over SQLAlchemy directly.

References:
    .claude/progress/aaa-rbac-foundation/  SVR-007
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from skillmeat.core.interfaces.repositories import ICollectionRepository
from skillmeat.core.interfaces.dtos import ArtifactDTO, CollectionDTO

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext

logger = logging.getLogger(__name__)


class CollectionService:
    """Orchestration service for collection operations.

    Wraps an :class:`~skillmeat.core.interfaces.repositories.ICollectionRepository`
    and threads :class:`~skillmeat.api.schemas.auth.AuthContext` through every
    repository call.  When ``auth_context`` is ``None`` the service substitutes
    ``LOCAL_ADMIN_CONTEXT`` so that local zero-auth deployments remain fully
    functional.

    Args:
        repo: Concrete collection repository implementation.

    Example::

        from skillmeat.core.services.collection_service import CollectionService

        service = CollectionService(repo=collection_repo)
        collection = service.get()
        collections = service.list()
    """

    def __init__(self, repo: ICollectionRepository) -> None:
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
    # Read operations
    # ------------------------------------------------------------------

    def get(
        self,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO | None:
        """Return the active collection metadata.

        Args:
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` when a
            collection exists, ``None`` if none has been initialised.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get(auth_context=ctx)

    def get_by_id(
        self,
        id: str,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO | None:
        """Return a specific collection by its identifier.

        Args:
            id: Collection unique identifier (usually the collection name).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` when
            found, ``None`` otherwise.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_by_id(id, auth_context=ctx)

    def list(
        self,
        auth_context: AuthContext | None = None,
    ) -> list[CollectionDTO]:
        """Return all known collections.

        Args:
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`
            objects.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.list(auth_context=ctx)

    def get_stats(
        self,
        auth_context: AuthContext | None = None,
    ) -> dict[str, Any]:
        """Return aggregate statistics for the active collection.

        Args:
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            Plain dictionary containing at minimum ``artifact_count``,
            ``total_size_bytes``, and ``last_synced``.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_stats(auth_context=ctx)

    def refresh(
        self,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Re-scan the filesystem and rebuild the collection cache.

        Args:
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            The refreshed :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.refresh(auth_context=ctx)

    def get_artifacts(
        self,
        collection_id: str,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        auth_context: AuthContext | None = None,
    ) -> list[ArtifactDTO]:
        """Return the artifacts that belong to a collection.

        Args:
            collection_id: Collection unique identifier.
            filters: Optional filter constraints (e.g. ``artifact_type``).
            offset: Zero-based pagination offset.
            limit: Maximum number of records to return.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.get_artifacts(
            collection_id,
            filters=filters,
            offset=offset,
            limit=limit,
            auth_context=ctx,
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        description: str | None = None,
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Create a new collection.

        Args:
            name: Human-readable name for the new collection.
            description: Optional description text.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.

        Raises:
            ValueError: If a collection with the same *name* already exists.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.create(name, description=description, auth_context=ctx)

    def update(
        self,
        collection_id: str,
        updates: dict[str, Any],
        auth_context: AuthContext | None = None,
    ) -> CollectionDTO:
        """Apply a partial update to an existing collection.

        Args:
            collection_id: Collection unique identifier.
            updates: Map of field names to new values.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.CollectionDTO`.

        Raises:
            KeyError: If no collection with *collection_id* exists.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.update(collection_id, updates, auth_context=ctx)

    def delete(
        self,
        collection_id: str,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Delete a collection and remove all its membership records.

        Does not delete artifact files from disk — only removes the
        collection registry entry and associated memberships.

        Args:
            collection_id: Collection unique identifier.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If no collection with *collection_id* exists.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.delete(collection_id, auth_context=ctx)

    def add_artifacts(
        self,
        collection_id: str,
        artifact_uuids: list[str],
        auth_context: AuthContext | None = None,
    ) -> None:
        """Add one or more artifacts to a collection by UUID.

        Idempotent: artifacts already in the collection are silently skipped.

        Args:
            collection_id: Collection unique identifier.
            artifact_uuids: List of stable artifact UUIDs (32-char hex strings).
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If any UUID in *artifact_uuids* does not correspond
                to a known artifact.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.add_artifacts(collection_id, artifact_uuids, auth_context=ctx)

    def remove_artifact(
        self,
        collection_id: str,
        artifact_uuid: str,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Remove a single artifact from a collection.

        Args:
            collection_id: Collection unique identifier.
            artifact_uuid: Stable artifact UUID (32-char hex) to remove.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If *collection_id* does not exist or *artifact_uuid* is
                not a member of the collection.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.remove_artifact(collection_id, artifact_uuid, auth_context=ctx)

    # ------------------------------------------------------------------
    # Entity management within a collection
    # ------------------------------------------------------------------

    def list_entities(
        self,
        collection_id: str,
        entity_type: str | None = None,
        auth_context: AuthContext | None = None,
    ) -> list[Any]:
        """Return entities belonging to a collection, optionally filtered by type.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Optional entity type string (e.g. ``"workflow"``).
                When ``None``, all entity types are returned.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Returns:
            List of entity records.
        """
        ctx = self._resolve_auth(auth_context)
        return self._repo.list_entities(collection_id, entity_type=entity_type, auth_context=ctx)

    def add_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Associate an entity with a collection.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Entity type string (e.g. ``"workflow"``).
            entity_id: Unique identifier of the entity to associate.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *entity_id* does not correspond to a known entity
                of the given *entity_type*.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.add_entity(collection_id, entity_type, entity_id, auth_context=ctx)

    def remove_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Remove an entity association from a collection.

        Args:
            collection_id: Collection unique identifier.
            entity_type: Entity type string (e.g. ``"workflow"``).
            entity_id: Unique identifier of the entity to disassociate.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If *collection_id* does not exist or the entity is not
                associated with the collection.
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.remove_entity(collection_id, entity_type, entity_id, auth_context=ctx)

    def migrate_to_default(
        self,
        collection_id: str,
        auth_context: AuthContext | None = None,
    ) -> None:
        """Migrate a collection's artifacts and entities to the default collection.

        All member artifacts and entity associations are moved to the active
        default collection; the source collection record is then removed.

        Args:
            collection_id: Collection unique identifier of the source collection
                to migrate away from.
            auth_context: Optional authentication and authorisation context.
                Defaults to ``LOCAL_ADMIN_CONTEXT`` when ``None``.

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *collection_id* refers to the current default
                collection (cannot migrate to itself).
        """
        ctx = self._resolve_auth(auth_context)
        self._repo.migrate_to_default(collection_id, auth_context=ctx)
