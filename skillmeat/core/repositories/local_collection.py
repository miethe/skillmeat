"""Filesystem-backed implementation of ICollectionRepository.

This module provides ``LocalCollectionRepository``, which satisfies the
``ICollectionRepository`` contract by delegating all operations to the
existing ``CollectionManager`` (filesystem source of truth) and
``ProjectPathResolver`` for path construction.

Design notes:
- Reads/writes always go to the filesystem first; DB cache synchronisation
  is left to the caller (or a write-through helper) per the data-flow
  invariants in ``.claude/context/key-context/data-flow-patterns.md``.
- The ``Collection`` domain objects returned by ``CollectionManager`` are
  converted to frozen ``CollectionDTO`` / ``ArtifactDTO`` values before
  leaving this layer, so no ORM or filesystem types leak upward.
- Python 3.9+ compatible: no ``X | Y`` union syntax in annotations.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from skillmeat.core.collection import CollectionManager
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ArtifactDTO, CollectionDTO
from skillmeat.core.interfaces.repositories import ICollectionRepository
from skillmeat.core.path_resolver import ProjectPathResolver

logger = logging.getLogger(__name__)

__all__ = ["LocalCollectionRepository"]


class LocalCollectionRepository(ICollectionRepository):
    """Filesystem-backed collection repository.

    Delegates to :class:`~skillmeat.core.collection.CollectionManager` for
    all I/O and converts the resulting domain objects into
    :class:`~skillmeat.core.interfaces.dtos.CollectionDTO` /
    :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` values.

    Parameters
    ----------
    collection_manager:
        The ``CollectionManager`` instance used for filesystem operations.
    path_resolver:
        The ``ProjectPathResolver`` instance used for path construction.
        Used primarily for collection root resolution and size calculations.
    """

    def __init__(
        self,
        collection_manager: CollectionManager,
        path_resolver: ProjectPathResolver,
    ) -> None:
        self._manager = collection_manager
        self._resolver = path_resolver

    # ------------------------------------------------------------------
    # ICollectionRepository — single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[CollectionDTO]:
        """Return the active collection's metadata.

        Args:
            ctx: Optional per-request metadata (unused at present).

        Returns:
            A :class:`CollectionDTO` when an active collection exists,
            ``None`` if the collection has not been initialised.
        """
        try:
            active_name = self._manager.get_active_collection_name()
            return self.get_by_id(active_name, ctx=ctx)
        except Exception as exc:
            logger.debug("get(): failed to load active collection: %s", exc)
            return None

    def get_by_id(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[CollectionDTO]:
        """Return the collection identified by *id* (collection name).

        Args:
            id: Collection name (the filesystem directory name).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`CollectionDTO` when the collection exists on disk,
            ``None`` otherwise.
        """
        try:
            collection = self._manager.load_collection(id)
        except ValueError as exc:
            logger.debug("get_by_id(%r): collection not found: %s", id, exc)
            return None

        return self._collection_to_dto(collection, id)

    # ------------------------------------------------------------------
    # ICollectionRepository — collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> List[CollectionDTO]:
        """Return all collections known to the manager.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`CollectionDTO` objects, one per collection
            directory found on disk.
        """
        names = self._manager.list_collections()
        result: List[CollectionDTO] = []
        for name in names:
            dto = self.get_by_id(name, ctx=ctx)
            if dto is not None:
                result.append(dto)
        return result

    def get_stats(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Return aggregate statistics for the active collection.

        Computes artifact counts, total on-disk size, and the last-synced
        timestamp from the active collection's manifest.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            Dictionary containing at minimum:

            * ``artifact_count`` — total number of artifacts in the
              active collection.
            * ``total_size_bytes`` — approximate combined size of all
              artifact directories/files under the collection root.
            * ``last_synced`` — ISO-8601 string of the collection's
              ``updated`` timestamp, or ``None`` when not available.
            * ``collection_root`` — absolute path to the collection
              root directory.

            Returns an empty dict when no active collection exists.
        """
        try:
            active_name = self._manager.get_active_collection_name()
            collection = self._manager.load_collection(active_name)
        except Exception as exc:
            logger.debug("get_stats(): failed to load active collection: %s", exc)
            return {}

        artifact_count = len(collection.artifacts)
        last_synced = collection.updated.isoformat() if collection.updated else None
        collection_root = self._resolver.collection_root()

        # Walk the artifacts directory to compute total on-disk size.
        artifacts_dir = self._resolver.artifacts_dir()
        total_size_bytes = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(artifacts_dir):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        total_size_bytes += os.path.getsize(fpath)
                    except OSError:
                        pass
        except OSError as exc:
            logger.debug("get_stats(): could not walk artifacts dir: %s", exc)

        return {
            "artifact_count": artifact_count,
            "total_size_bytes": total_size_bytes,
            "last_synced": last_synced,
            "collection_root": str(collection_root),
        }

    def refresh(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> CollectionDTO:
        """Invalidate the in-memory manifest cache and reload from disk.

        Forces a fresh read of the collection manifest from the filesystem.
        Callers that need a full DB-cache rebuild should call the appropriate
        ``CacheManager`` or ``RefreshJob`` method in addition.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            The refreshed :class:`CollectionDTO`.

        Raises:
            ValueError: If no active collection exists or the manifest
                cannot be loaded.
        """
        active_name = self._manager.get_active_collection_name()

        # Invalidate the in-memory manifest cache so the next load reads from disk.
        self._manager.invalidate_collection_cache(active_name)

        collection = self._manager.load_collection(active_name)
        return self._collection_to_dto(collection, active_name)

    def get_artifacts(
        self,
        collection_id: str,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 50,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """Return artifacts in *collection_id* with optional filtering and pagination.

        Args:
            collection_id: Collection name (filesystem directory name).
            filters: Optional dict of filter constraints.  Supported keys:

                * ``artifact_type`` / ``type`` — filter by artifact type
                  string (e.g. ``"skill"``).
                * ``name`` — case-insensitive substring filter on artifact
                  name.
                * ``source`` — filter by upstream source spec substring.

            offset: Zero-based pagination offset.
            limit: Maximum number of records to return (capped at 250).
            ctx: Optional per-request metadata.

        Returns:
            Filtered, paginated list of :class:`ArtifactDTO` objects.
        """
        try:
            collection = self._manager.load_collection(collection_id)
        except ValueError as exc:
            logger.debug(
                "get_artifacts(%r): collection not found: %s", collection_id, exc
            )
            return []

        artifacts = collection.artifacts
        filters = filters or {}

        # -- type filter --
        type_filter = filters.get("artifact_type") or filters.get("type")
        if type_filter:
            type_filter_lower = str(type_filter).lower()
            artifacts = [
                a for a in artifacts if a.type.value.lower() == type_filter_lower
            ]

        # -- name filter (case-insensitive substring) --
        name_filter = filters.get("name")
        if name_filter:
            name_filter_lower = str(name_filter).lower()
            artifacts = [a for a in artifacts if name_filter_lower in a.name.lower()]

        # -- source filter (substring match) --
        source_filter = filters.get("source")
        if source_filter:
            source_filter_lower = str(source_filter).lower()
            artifacts = [
                a
                for a in artifacts
                if a.upstream and source_filter_lower in a.upstream.lower()
            ]

        # -- pagination --
        limit = min(limit, 250)
        page = artifacts[offset : offset + limit]

        return [self._artifact_to_dto(a, collection_id) for a in page]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collection_to_dto(
        self,
        collection: Any,
        collection_id: str,
    ) -> CollectionDTO:
        """Convert a filesystem ``Collection`` domain object to a DTO.

        Args:
            collection: ``skillmeat.core.collection.Collection`` instance.
            collection_id: The collection name (used as the DTO ``id``).

        Returns:
            A frozen :class:`CollectionDTO`.
        """
        collection_path = self._manager.config.get_collection_path(collection_id)
        return CollectionDTO(
            id=collection_id,
            name=collection.name,
            path=str(collection_path),
            version=collection.version,
            artifact_count=len(collection.artifacts),
            created_at=collection.created.isoformat() if collection.created else None,
            updated_at=collection.updated.isoformat() if collection.updated else None,
        )

    def _artifact_to_dto(
        self,
        artifact: Any,
        collection_id: str,
    ) -> ArtifactDTO:
        """Convert a filesystem ``Artifact`` domain object to a DTO.

        Constructs the ``"type:name"`` primary key expected by
        :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO` and extracts
        metadata fields from the artifact's metadata dataclass.

        Args:
            artifact: ``skillmeat.core.artifact.Artifact`` domain instance.
            collection_id: The owning collection identifier.

        Returns:
            A frozen :class:`ArtifactDTO`.
        """
        artifact_type = artifact.type.value if artifact.type else ""
        artifact_id = f"{artifact_type}:{artifact.name}"

        # Extract description from metadata if available.
        description: Optional[str] = None
        metadata_dict: Dict[str, Any] = {}
        if artifact.metadata is not None:
            description = getattr(artifact.metadata, "description", None)
            # Convert metadata dataclass to plain dict for the DTO.
            metadata_dict = {
                k: v
                for k, v in {
                    "title": getattr(artifact.metadata, "title", None),
                    "author": getattr(artifact.metadata, "author", None),
                    "license": getattr(artifact.metadata, "license", None),
                    "version": getattr(artifact.metadata, "version", None),
                    "dependencies": getattr(artifact.metadata, "dependencies", None),
                    "extra": getattr(artifact.metadata, "extra", None),
                }.items()
                if v
            }

        # Extract tag names from metadata.
        tags: List[str] = []
        if artifact.metadata is not None:
            raw_tags = getattr(artifact.metadata, "tags", None)
            if raw_tags:
                tags = list(raw_tags)

        # Resolve the filesystem path for this artifact.
        content_path: Optional[str] = None
        try:
            resolved = self._resolver.artifact_path(artifact.name, artifact_type)
            content_path = str(resolved)
        except (ValueError, Exception) as exc:
            logger.debug(
                "_artifact_to_dto: could not resolve path for %s: %s",
                artifact_id,
                exc,
            )

        return ArtifactDTO(
            id=artifact_id,
            name=artifact.name,
            artifact_type=artifact_type,
            uuid=getattr(artifact, "uuid", None),
            source=getattr(artifact, "upstream", None),
            version=getattr(artifact, "version", None),
            scope=getattr(artifact, "scope", None),
            description=description,
            content_path=content_path,
            metadata=metadata_dict,
            tags=tags,
            is_outdated=False,
            local_modified=False,
            project_id=collection_id,
        )
