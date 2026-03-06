"""Filesystem-backed implementation of IArtifactRepository.

Delegates to :class:`~skillmeat.core.artifact.ArtifactManager` for all
filesystem operations and optionally syncs the DB cache via
``refresh_single_artifact_cache()`` after mutations.

Design notes
------------
* The ``ArtifactManager`` works with ``Artifact`` dataclass instances whose
  primary key is the ``(type, name)`` composite.  The interface contract uses
  a ``"type:name"`` string, so we split / join as needed at the boundary.
* The ``ArtifactManager`` does not support search natively; we implement a
  simple in-memory filter over ``list_artifacts()`` for ``search()``.
* For ``get_by_uuid`` we scan the full artifact list; this is acceptable for
  a collection of typical size (< 10,000 items).  A future phase can push
  UUID lookups into the DB-backed repository.
* The DB cache write-through is best-effort: if the import is unavailable or
  the refresh call fails, the FS mutation still succeeds and ``True`` / the
  DTO is returned.  Failures are logged as warnings.
* Tags on the filesystem live inside the ``Artifact.tags`` list.  The
  ``get_tags`` / ``set_tags`` methods read and mutate that field, then
  persist via :meth:`ArtifactManager.save_artifact_tags` (if available) or
  by reconstructing the collection entry.  Since the manager has no
  dedicated tag-save API, we update the collection manifest directly via the
  ``CollectionManager`` that the manager owns.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from skillmeat.core.artifact import ArtifactManager, ArtifactType
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ArtifactDTO, CollectionMembershipDTO, TagDTO
from skillmeat.core.interfaces.repositories import IArtifactRepository
from skillmeat.core.path_resolver import ProjectPathResolver

# ---------------------------------------------------------------------------
# Optional DB UUID lookup — graceful degradation when cache module is absent.
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import get_session as _get_db_session
    from skillmeat.cache.models import Artifact as _DBArtifact
    from skillmeat.cache.models import Collection as _DBCollection
    from skillmeat.cache.models import CollectionArtifact as _DBCollectionArtifact
    from skillmeat.cache.models import DuplicatePair as _DBDuplicatePair
    _db_available = True
except ImportError:  # pragma: no cover
    _get_db_session = None  # type: ignore[assignment]
    _DBArtifact = None  # type: ignore[assignment]
    _DBCollection = None  # type: ignore[assignment]
    _DBCollectionArtifact = None  # type: ignore[assignment]
    _DBDuplicatePair = None  # type: ignore[assignment]
    _db_available = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional write-through import — graceful degradation when cache module is
# absent (e.g. during unit tests that don't set up a DB).
# ---------------------------------------------------------------------------
try:
    from skillmeat.api.services.artifact_cache_service import (
        refresh_single_artifact_cache as _refresh_fn,
    )
except ImportError:  # pragma: no cover
    _refresh_fn = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_id(id: str) -> tuple[str, str]:
    """Split a ``"type:name"`` primary key into ``(artifact_type, name)``.

    Args:
        id: Artifact primary key string.

    Returns:
        ``(artifact_type_str, artifact_name)`` tuple.

    Raises:
        ValueError: If *id* does not contain a colon.
    """
    if ":" not in id:
        raise ValueError(
            f"Invalid artifact id '{id}': expected 'type:name' format"
        )
    artifact_type_str, name = id.split(":", 1)
    return artifact_type_str, name


def _artifact_to_dto(
    artifact: Any,
    collection_id: Optional[str] = None,
    db_uuid: Optional[str] = None,
) -> ArtifactDTO:
    """Convert an :class:`~skillmeat.core.artifact.Artifact` to :class:`ArtifactDTO`.

    Args:
        artifact: A ``skillmeat.core.artifact.Artifact`` instance.
        collection_id: Optional collection identifier to set as ``project_id``.
        db_uuid: Optional UUID sourced from the DB cache.  When provided this
            takes precedence over any ``uuid`` attribute on the filesystem
            artifact (per ADR-007, UUIDs live in the DB, not on the FS).

    Returns:
        An :class:`ArtifactDTO` populated from the artifact's fields.
    """
    artifact_type_str = (
        artifact.type.value
        if hasattr(artifact.type, "value")
        else str(artifact.type)
    )
    artifact_id = f"{artifact_type_str}:{artifact.name}"

    metadata_dict: dict[str, Any] = {}
    if artifact.metadata is not None:
        raw = artifact.metadata.to_dict() if hasattr(artifact.metadata, "to_dict") else {}
        metadata_dict = dict(raw)

    description = (
        artifact.metadata.description
        if artifact.metadata and artifact.metadata.description
        else metadata_dict.get("description")
    )

    version = getattr(artifact, "resolved_version", None) or getattr(
        artifact, "version_spec", None
    )

    # Prefer DB UUID (authoritative per ADR-007) over any FS-level attribute.
    uuid = db_uuid or getattr(artifact, "uuid", None)

    return ArtifactDTO(
        id=artifact_id,
        name=artifact.name,
        artifact_type=artifact_type_str,
        uuid=uuid,
        source=getattr(artifact, "upstream", None),
        version=version,
        scope=None,  # scope lives at the deployment level, not collection
        description=description,
        content_path=getattr(artifact, "path", None),
        metadata=metadata_dict,
        tags=list(getattr(artifact, "tags", []) or []),
        is_outdated=False,
        local_modified=False,
        project_id=collection_id,
        created_at=(
            artifact.added.isoformat()
            if getattr(artifact, "added", None) is not None
            else None
        ),
        updated_at=(
            artifact.last_updated.isoformat()
            if getattr(artifact, "last_updated", None) is not None
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalArtifactRepository(IArtifactRepository):
    """Filesystem-backed :class:`IArtifactRepository` implementation.

    All read operations delegate to ``ArtifactManager.list_artifacts()``
    and ``ArtifactManager.show()``.  Write operations delegate to the
    appropriate manager methods and then trigger a DB cache refresh when a
    session / refresh callable is available.

    Args:
        artifact_manager: Fully initialised :class:`ArtifactManager` instance.
        path_resolver: A :class:`ProjectPathResolver` for collection path
            resolution (used for file content access).
        db_session: Optional SQLAlchemy ``Session``; when provided together
            with a callable for ``refresh_fn``, mutations trigger a
            write-through cache sync.
        refresh_fn: Optional callable with the same signature as
            ``refresh_single_artifact_cache``.  When ``None``, the module-
            level import is used (if available).
        collection_name: Name of the target collection (``None`` means the
            active/default collection).
    """

    def __init__(
        self,
        artifact_manager: ArtifactManager,
        path_resolver: ProjectPathResolver,
        db_session: Optional[Any] = None,
        refresh_fn: Optional[Callable[..., bool]] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self._mgr = artifact_manager
        self._path_resolver = path_resolver
        self._db_session = db_session
        self._refresh_fn: Optional[Callable[..., bool]] = refresh_fn or _refresh_fn
        self._collection_name = collection_name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_cache_refresh(self, artifact_id: str) -> None:
        """Best-effort write-through cache sync after a mutation.

        Args:
            artifact_id: Artifact primary key (``"type:name"``).
        """
        if self._db_session is None or self._refresh_fn is None:
            return
        try:
            self._refresh_fn(
                session=self._db_session,
                artifact_mgr=self._mgr,
                artifact_id=artifact_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Cache refresh failed for artifact '%s': %s",
                artifact_id,
                exc,
                exc_info=True,
            )

    def _get_db_uuid(self, artifact_id: str) -> Optional[str]:
        """Look up the stable UUID for an artifact from the DB cache.

        Filesystem ``Artifact`` instances do not carry UUIDs (per ADR-007,
        UUIDs live exclusively in the DB cache).  This method opens a
        short-lived DB session, queries ``artifacts.uuid`` by the
        ``type:name`` primary key, and returns the result.

        Args:
            artifact_id: Artifact primary key string (``"type:name"``).

        Returns:
            32-char hex UUID string when found in DB, ``None`` otherwise.
        """
        if not _db_available or _get_db_session is None or _DBArtifact is None:
            return None
        # Local refs for Pyright type narrowing
        get_session = _get_db_session
        DBArtifact = _DBArtifact
        try:
            session = get_session()
            try:
                row = session.query(DBArtifact.uuid).filter(
                    DBArtifact.id == artifact_id
                ).first()
                return row[0] if row else None
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "DB UUID lookup failed for artifact '%s': %s",
                artifact_id,
                exc,
            )
            return None

    def _get_db_uuid_batch(self, artifact_ids: List[str]) -> dict[str, str]:
        """Batch look up stable UUIDs for multiple artifacts from the DB cache.

        Opens a single session, queries all requested IDs in one round-trip,
        and returns a mapping of ``artifact_id → uuid``.  Artifacts not found
        in the DB are absent from the returned dict.

        Args:
            artifact_ids: List of ``"type:name"`` primary key strings.

        Returns:
            Dict mapping artifact ID to 32-char hex UUID.  Missing entries
            indicate the artifact has not yet been indexed in the DB cache.
        """
        if not _db_available or not artifact_ids or _get_db_session is None or _DBArtifact is None:
            return {}
        # Local refs for Pyright type narrowing
        get_session = _get_db_session
        DBArtifact = _DBArtifact
        try:
            session = get_session()
            try:
                rows = (
                    session.query(DBArtifact.id, DBArtifact.uuid)
                    .filter(DBArtifact.id.in_(artifact_ids))
                    .all()
                )
                return {row[0]: row[1] for row in rows if row[1] is not None}
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "DB UUID batch lookup failed (%d ids): %s",
                len(artifact_ids),
                exc,
            )
            return {}

    def _resolve_artifact_path(self, artifact: Any) -> Optional[str]:
        """Resolve the absolute filesystem path for an artifact's content.

        Args:
            artifact: An ``Artifact`` instance.

        Returns:
            Absolute path string or ``None`` when the path cannot be resolved.
        """
        if self._collection_name is None:
            return None
        try:
            collection_path = self._mgr.collection_mgr.config.get_collection_path(
                self._collection_name
            )
            return str(collection_path / artifact.path)
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ArtifactDTO]:
        """Return the artifact with the given ``"type:name"`` primary key.

        Args:
            id: Artifact primary key.
            ctx: Optional per-request metadata (unused in this implementation).

        Returns:
            :class:`ArtifactDTO` when found, ``None`` otherwise.
        """
        try:
            artifact_type_str, name = _parse_id(id)
        except ValueError:
            logger.warning("get() called with invalid id '%s'", id)
            return None

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            logger.warning("get() called with unknown artifact type '%s'", artifact_type_str)
            return None

        try:
            artifact = self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError:
            # show() raises ValueError when not found
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("get() failed for artifact '%s': %s", id, exc)
            return None

        db_uuid = self._get_db_uuid(id)
        return _artifact_to_dto(artifact, db_uuid=db_uuid)

    def get_by_uuid(
        self,
        uuid: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ArtifactDTO]:
        """Return the artifact identified by its stable UUID.

        This performs a linear scan over all artifacts because the filesystem
        manifest does not index by UUID.  For large collections the DB-backed
        repository should be preferred.

        Args:
            uuid: 32-char hex UUID string.
            ctx: Optional per-request metadata (unused).

        Returns:
            :class:`ArtifactDTO` when found, ``None`` otherwise.
        """
        # First try DB — UUIDs are authoritative there (ADR-007).
        if _db_available and _get_db_session is not None and _DBArtifact is not None:
            # Local refs for Pyright type narrowing
            get_session = _get_db_session
            DBArtifact = _DBArtifact
            try:
                session = get_session()
                try:
                    row = session.query(DBArtifact.id, DBArtifact.uuid).filter(
                        DBArtifact.uuid == uuid
                    ).first()
                finally:
                    session.close()
                if row:
                    artifact_id = row[0]
                    return self.get(artifact_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("get_by_uuid() DB lookup failed: %s", exc)

        # Fallback: linear scan over filesystem artifacts.
        try:
            all_artifacts = self._mgr.list_artifacts(
                collection_name=self._collection_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_by_uuid() list failed: %s", exc)
            return None

        for artifact in all_artifacts:
            if getattr(artifact, "uuid", None) == uuid:
                return _artifact_to_dto(artifact, db_uuid=uuid)

        return None

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 50,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """Return a page of artifacts matching optional filter criteria.

        Recognised filter keys: ``artifact_type``, ``tags`` (list of str,
        any-match), ``scope`` (not stored on filesystem — filtered only when
        provided and non-empty).

        Args:
            filters: Optional key/value filter map.
            offset: Zero-based pagination offset.
            limit: Maximum records to return.
            ctx: Optional per-request metadata (unused).

        Returns:
            List of matching :class:`ArtifactDTO` objects.
        """
        filters = filters or {}

        # Resolve artifact_type filter
        artifact_type_filter: Optional[ArtifactType] = None
        if filters.get("artifact_type"):
            try:
                artifact_type_filter = ArtifactType(str(filters["artifact_type"]))
            except ValueError:
                pass  # unknown type — return empty rather than crash

        tags_filter: Optional[List[str]] = filters.get("tags")

        try:
            artifacts = self._mgr.list_artifacts(
                collection_name=self._collection_name,
                artifact_type=artifact_type_filter,
                tags=tags_filter,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("list() failed: %s", exc)
            return []

        # Apply pagination
        page = artifacts[offset : offset + limit]

        # Batch-fetch UUIDs from DB cache in a single round-trip.
        page_ids = [
            f"{a.type.value if hasattr(a.type, 'value') else str(a.type)}:{a.name}"
            for a in page
        ]
        uuid_map = self._get_db_uuid_batch(page_ids)

        return [
            _artifact_to_dto(
                a,
                db_uuid=uuid_map.get(
                    f"{a.type.value if hasattr(a.type, 'value') else str(a.type)}:{a.name}"
                ),
            )
            for a in page
        ]

    def count(
        self,
        filters: Optional[dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> int:
        """Return the total number of artifacts matching optional filters.

        Args:
            filters: Same filter map accepted by :meth:`list`.
            ctx: Optional per-request metadata (unused).

        Returns:
            Non-negative integer count.
        """
        filters = filters or {}

        artifact_type_filter: Optional[ArtifactType] = None
        if filters.get("artifact_type"):
            try:
                artifact_type_filter = ArtifactType(str(filters["artifact_type"]))
            except ValueError:
                return 0

        tags_filter: Optional[List[str]] = filters.get("tags")

        try:
            artifacts = self._mgr.list_artifacts(
                collection_name=self._collection_name,
                artifact_type=artifact_type_filter,
                tags=tags_filter,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("count() failed: %s", exc)
            return 0

        return len(artifacts)

    def search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """In-memory fuzzy search over artifact names and descriptions.

        Checks whether *query* appears (case-insensitively) in the artifact
        name, description, or tags.  Additional filter constraints from
        *filters* are applied on top.

        Args:
            query: Free-form search string.
            filters: Optional additional filter constraints.
            ctx: Optional per-request metadata (unused).

        Returns:
            Matching :class:`ArtifactDTO` objects (no relevance ranking).
        """
        filters = filters or {}
        q = query.lower().strip()

        artifact_type_filter: Optional[ArtifactType] = None
        if filters.get("artifact_type"):
            try:
                artifact_type_filter = ArtifactType(str(filters["artifact_type"]))
            except ValueError:
                return []

        try:
            candidates = self._mgr.list_artifacts(
                collection_name=self._collection_name,
                artifact_type=artifact_type_filter,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("search() list failed: %s", exc)
            return []

        matched = []
        for artifact in candidates:
            name_match = q in artifact.name.lower()
            desc = (
                artifact.metadata.description
                if artifact.metadata and artifact.metadata.description
                else ""
            )
            desc_match = q in desc.lower()
            tag_match = any(q in t.lower() for t in (artifact.tags or []))

            if name_match or desc_match or tag_match:
                matched.append(artifact)

        # Batch-fetch UUIDs from DB cache in a single round-trip.
        matched_ids = [
            f"{a.type.value if hasattr(a.type, 'value') else str(a.type)}:{a.name}"
            for a in matched
        ]
        uuid_map = self._get_db_uuid_batch(matched_ids)

        return [
            _artifact_to_dto(
                a,
                db_uuid=uuid_map.get(
                    f"{a.type.value if hasattr(a.type, 'value') else str(a.type)}:{a.name}"
                ),
            )
            for a in matched
        ]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        dto: ArtifactDTO,
        ctx: Optional[RequestContext] = None,
    ) -> ArtifactDTO:
        """Persist a new artifact record from a local path.

        Uses :meth:`ArtifactManager.add_from_local` when the content path
        points to a local directory, otherwise falls back to constructing a
        minimal ``Artifact`` entry and saving it to the collection.

        Args:
            dto: Fully populated artifact data.  ``content_path`` must point
                to an existing filesystem path.
            ctx: Optional per-request metadata (unused).

        Returns:
            The persisted :class:`ArtifactDTO`.

        Raises:
            ValueError: If ``content_path`` is absent or the artifact already
                exists (and the manager enforces uniqueness).
        """
        if not dto.content_path:
            raise ValueError("content_path is required to create a local artifact")

        try:
            artifact_type = ArtifactType(dto.artifact_type)
        except ValueError as exc:
            raise ValueError(
                f"Unknown artifact type '{dto.artifact_type}'"
            ) from exc

        artifact = self._mgr.add_from_local(
            path=dto.content_path,
            artifact_type=artifact_type,
            collection_name=self._collection_name,
            custom_name=dto.name or None,
            tags=list(dto.tags) if dto.tags else None,
        )

        artifact_id = f"{artifact.type.value}:{artifact.name}"
        self._try_cache_refresh(artifact_id)
        return _artifact_to_dto(artifact)

    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> ArtifactDTO:
        """Apply a partial update to an existing artifact.

        Currently supports updating ``tags``.  Other fields require direct
        filesystem edits; the method refreshes the cache after any tag
        mutations.

        Args:
            id: Artifact primary key (``"type:name"``).
            updates: Map of field names to new values.
            ctx: Optional per-request metadata (unused).

        Returns:
            The updated :class:`ArtifactDTO`.

        Raises:
            KeyError: If no artifact with *id* exists.
        """
        artifact_type_str, name = _parse_id(id)

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError as exc:
            raise KeyError(id) from exc

        try:
            artifact = self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError as exc:
            raise KeyError(id) from exc

        mutated = False

        # Handle tag updates
        if "tags" in updates:
            new_tags: List[str] = list(updates["tags"] or [])
            artifact.tags = new_tags
            if artifact.metadata:
                artifact.metadata.tags = []  # keep tags on top-level only
            mutated = True

        if mutated:
            try:
                collection = self._mgr.collection_mgr.load_collection(
                    self._collection_name
                )
                # Replace the artifact entry in the collection
                collection.remove_artifact(name, artifact_type)
                collection.add_artifact(artifact)
                self._mgr.collection_mgr.save_collection(collection)
            except Exception as exc:  # noqa: BLE001
                logger.warning("update() save failed for '%s': %s", id, exc)

        self._try_cache_refresh(id)

        # Re-load to return the persisted state
        refreshed = self.get(id, ctx=ctx)
        if refreshed is None:
            raise KeyError(id)
        return refreshed

    def delete(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Delete an artifact from the collection.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata (unused).

        Returns:
            ``True`` when the artifact was found and deleted, ``False`` when
            no matching record existed.
        """
        try:
            artifact_type_str, name = _parse_id(id)
        except ValueError:
            return False

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            return False

        # Verify it exists first
        try:
            self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError:
            return False

        try:
            self._mgr.remove(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("delete() failed for '%s': %s", id, exc)
            return False

        return True

    # ------------------------------------------------------------------
    # File-content access
    # ------------------------------------------------------------------

    def get_content(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> str:
        """Return the raw text content of an artifact's primary file.

        For directory-based artifacts (skills, MCPs) this reads the first
        Markdown file found (``SKILL.md``, ``COMMAND.md``, etc.).  For
        single-file artifacts the file itself is read.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata (unused).

        Returns:
            File content as a UTF-8 string.

        Raises:
            KeyError: If no artifact with *id* exists.
            FileNotFoundError: If the content file cannot be located.
        """
        artifact_type_str, name = _parse_id(id)

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError as exc:
            raise KeyError(id) from exc

        try:
            artifact = self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError as exc:
            raise KeyError(id) from exc

        abs_path = self._resolve_artifact_path(artifact)
        if abs_path is None:
            raise FileNotFoundError(
                f"Cannot resolve filesystem path for artifact '{id}'"
            )

        import os
        from pathlib import Path

        artifact_fs_path = Path(abs_path)

        if artifact_fs_path.is_file():
            return artifact_fs_path.read_text(encoding="utf-8")

        if artifact_fs_path.is_dir():
            # Look for the canonical descriptor file
            descriptor_names = [
                f"{artifact_type_str.upper()}.md",
                "SKILL.md",
                "COMMAND.md",
                "AGENT.md",
                "HOOK.md",
                "MCP.md",
                "README.md",
            ]
            for descriptor in descriptor_names:
                candidate = artifact_fs_path / descriptor
                if candidate.exists():
                    return candidate.read_text(encoding="utf-8")

            # Fall back to first .md file
            md_files = sorted(artifact_fs_path.glob("*.md"))
            if md_files:
                return md_files[0].read_text(encoding="utf-8")

            raise FileNotFoundError(
                f"No content file found in artifact directory '{artifact_fs_path}'"
            )

        raise FileNotFoundError(
            f"Artifact path does not exist on disk: '{artifact_fs_path}'"
        )

    def update_content(
        self,
        id: str,
        content: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Overwrite the primary file content of an artifact.

        Args:
            id: Artifact primary key (``"type:name"``).
            content: New file content (UTF-8 string).
            ctx: Optional per-request metadata (unused).

        Returns:
            ``True`` on success.

        Raises:
            KeyError: If no artifact with *id* exists.
            FileNotFoundError: If the content file cannot be located.
        """
        artifact_type_str, name = _parse_id(id)

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError as exc:
            raise KeyError(id) from exc

        try:
            artifact = self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError as exc:
            raise KeyError(id) from exc

        abs_path = self._resolve_artifact_path(artifact)
        if abs_path is None:
            raise FileNotFoundError(
                f"Cannot resolve filesystem path for artifact '{id}'"
            )

        from pathlib import Path

        artifact_fs_path = Path(abs_path)

        if artifact_fs_path.is_file():
            target_file = artifact_fs_path
        elif artifact_fs_path.is_dir():
            descriptor_names = [
                f"{artifact_type_str.upper()}.md",
                "SKILL.md",
                "COMMAND.md",
                "AGENT.md",
                "HOOK.md",
                "MCP.md",
                "README.md",
            ]
            target_file = None
            for descriptor in descriptor_names:
                candidate = artifact_fs_path / descriptor
                if candidate.exists():
                    target_file = candidate
                    break

            if target_file is None:
                md_files = sorted(artifact_fs_path.glob("*.md"))
                if md_files:
                    target_file = md_files[0]

            if target_file is None:
                raise FileNotFoundError(
                    f"No content file found in artifact directory '{artifact_fs_path}'"
                )
        else:
            raise FileNotFoundError(
                f"Artifact path does not exist on disk: '{artifact_fs_path}'"
            )

        target_file.write_text(content, encoding="utf-8")
        self._try_cache_refresh(id)
        return True

    # ------------------------------------------------------------------
    # Tag associations
    # ------------------------------------------------------------------

    def get_tags(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[TagDTO]:
        """Return all tags currently assigned to an artifact.

        Tags are read from the ``Artifact.tags`` list in the collection
        manifest.

        Args:
            id: Artifact primary key (``"type:name"``).
            ctx: Optional per-request metadata (unused).

        Returns:
            List of :class:`TagDTO` objects.  The DTOs carry only ``name``
            and a derived ``slug``; ``id`` and ``color`` are not stored on
            the filesystem so they default to the slug and ``None``.
        """
        artifact_type_str, name = _parse_id(id)

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            return []

        try:
            artifact = self._mgr.show(
                artifact_name=name,
                artifact_type=artifact_type,
                collection_name=self._collection_name,
            )
        except ValueError:
            return []

        tags = list(getattr(artifact, "tags", []) or [])
        return [_tag_name_to_dto(t) for t in tags]

    def set_tags(
        self,
        id: str,
        tag_ids: List[str],
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Replace the complete tag set for an artifact.

        Tags are stored as plain strings in the collection manifest.  The
        ``tag_ids`` parameter is treated as a list of tag name strings (the
        only stable identifier available on the filesystem).

        Args:
            id: Artifact primary key (``"type:name"``).
            tag_ids: New complete list of tag name strings.
            ctx: Optional per-request metadata (unused).

        Returns:
            ``True`` on success.
        """
        try:
            self.update(id=id, updates={"tags": tag_ids}, ctx=ctx)
        except KeyError:
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("set_tags() failed for '%s': %s", id, exc)
            return False

        return True

    # ------------------------------------------------------------------
    # UUID resolution
    # ------------------------------------------------------------------

    def get_ids_by_uuids(
        self,
        uuids: List[str],
        ctx: Optional[RequestContext] = None,
    ) -> dict[str, str]:
        """Batch-map artifact UUIDs to their ``type:name`` ID strings.

        Opens a single DB session and queries ``(uuid, id)`` pairs for all
        requested UUIDs in one round-trip.  UUIDs with no matching row are
        absent from the returned dict.

        Args:
            uuids: List of 32-char hex UUID strings to look up.
            ctx: Optional per-request metadata (unused).

        Returns:
            Dict mapping each UUID to its ``"type:name"`` artifact ID string.
        """
        if not _db_available or not uuids or _get_db_session is None or _DBArtifact is None:
            return {}
        # Local refs for Pyright type narrowing
        get_session = _get_db_session
        DBArtifact = _DBArtifact
        try:
            session = get_session()
            try:
                rows = (
                    session.query(DBArtifact.uuid, DBArtifact.id)
                    .filter(DBArtifact.uuid.in_(uuids))
                    .all()
                )
                return {row[0]: row[1] for row in rows if row[1] is not None}
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "DB UUID→ID batch lookup failed (%d uuids): %s",
                len(uuids),
                exc,
            )
            return {}

    def resolve_uuid_by_type_name(
        self,
        artifact_type: str,
        name: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[str]:
        """Resolve the stable UUID for an artifact identified by type and name.

        Delegates to :meth:`_get_db_uuid` using the ``"type:name"`` format.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``).
            name: Artifact name string.
            ctx: Optional per-request metadata (unused).

        Returns:
            32-char hex UUID string when found in DB, ``None`` otherwise.
        """
        artifact_id = f"{artifact_type}:{name}"
        return self._get_db_uuid(artifact_id)

    def batch_resolve_uuids(
        self,
        artifacts: List[tuple],
        ctx: Optional[RequestContext] = None,
    ) -> dict:
        """Batch-resolve UUIDs for multiple ``(artifact_type, name)`` pairs.

        Converts each pair to the ``"type:name"`` format and calls
        :meth:`_get_db_uuid_batch` in a single round-trip.

        Args:
            artifacts: List of ``(artifact_type, name)`` tuples.
            ctx: Optional per-request metadata (unused).

        Returns:
            Dict mapping each ``(artifact_type, name)`` tuple to its 32-char
            hex UUID.  Unresolvable pairs are omitted.
        """
        id_to_pair = {f"{atype}:{name}": (atype, name) for atype, name in artifacts}
        uuid_map = self._get_db_uuid_batch(list(id_to_pair.keys()))
        return {
            id_to_pair[artifact_id]: uuid_val
            for artifact_id, uuid_val in uuid_map.items()
        }

    # ------------------------------------------------------------------
    # Collection-context queries
    # ------------------------------------------------------------------

    def get_with_collection_context(
        self,
        uuid: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ArtifactDTO]:
        """Return an artifact with enriched collection-membership context.

        Fetches the artifact via :meth:`get_by_uuid` and enriches it with
        the collection-level description from the ``CollectionArtifact``
        association row when available.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata (unused).

        Returns:
            An :class:`ArtifactDTO` with collection context populated where
            available, ``None`` when the artifact does not exist.
        """
        dto = self.get_by_uuid(uuid, ctx=ctx)
        if dto is None:
            return None

        # Enrich with collection-level description if available in DB.
        if (
            _db_available
            and _get_db_session is not None
            and _DBCollectionArtifact is not None
        ):
            get_session = _get_db_session
            DBCollectionArtifact = _DBCollectionArtifact
            try:
                session = get_session()
                try:
                    row = (
                        session.query(DBCollectionArtifact.description)
                        .filter(DBCollectionArtifact.artifact_uuid == uuid)
                        .order_by(DBCollectionArtifact.added_at.desc())
                        .first()
                    )
                    if row and row[0]:
                        # Return a new DTO with the collection-level description
                        # overriding the intrinsic description.
                        return ArtifactDTO(
                            id=dto.id,
                            name=dto.name,
                            artifact_type=dto.artifact_type,
                            uuid=dto.uuid,
                            source=dto.source,
                            version=dto.version,
                            scope=dto.scope,
                            description=row[0],
                            content_path=dto.content_path,
                            metadata=dto.metadata,
                            tags=dto.tags,
                            is_outdated=dto.is_outdated,
                            local_modified=dto.local_modified,
                            project_id=dto.project_id,
                            created_at=dto.created_at,
                            updated_at=dto.updated_at,
                        )
                finally:
                    session.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "get_with_collection_context() DB enrichment failed for uuid '%s': %s",
                    uuid,
                    exc,
                )

        return dto

    def get_collection_memberships(
        self,
        uuid: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[CollectionMembershipDTO]:
        """Return all collections that contain the artifact identified by *uuid*.

        Queries the ``collection_artifacts`` join table and resolves collection
        names from the ``collections`` table.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata (unused).

        Returns:
            List of :class:`CollectionMembershipDTO` objects, one per
            collection membership.  Empty list when artifact is not found
            or has no memberships.
        """
        if (
            not _db_available
            or _get_db_session is None
            or _DBCollectionArtifact is None
            or _DBCollection is None
        ):
            return []

        get_session = _get_db_session
        DBCollectionArtifact = _DBCollectionArtifact
        DBCollection = _DBCollection
        try:
            session = get_session()
            try:
                rows = (
                    session.query(
                        DBCollectionArtifact.collection_id,
                        DBCollectionArtifact.artifact_uuid,
                        DBCollectionArtifact.added_at,
                        DBCollection.name,
                    )
                    .join(
                        DBCollection,
                        DBCollection.id == DBCollectionArtifact.collection_id,
                    )
                    .filter(DBCollectionArtifact.artifact_uuid == uuid)
                    .all()
                )
                memberships = []
                for row in rows:
                    collection_id, artifact_uuid, added_at, collection_name = row
                    memberships.append(
                        CollectionMembershipDTO(
                            collection_id=collection_id,
                            collection_name=collection_name or collection_id,
                            artifact_uuid=artifact_uuid,
                            artifact_id=None,
                            added_at=(
                                added_at.isoformat() if added_at is not None else None
                            ),
                        )
                    )
                return memberships
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "get_collection_memberships() failed for uuid '%s': %s",
                uuid,
                exc,
            )
            return []

    def get_collection_description(
        self,
        uuid: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[str]:
        """Return the collection-level description for an artifact.

        Reads the ``description`` column from the most recent
        ``CollectionArtifact`` association row for this UUID.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata (unused).

        Returns:
            Collection-level description string, or ``None`` when not set
            or the artifact does not exist.
        """
        if (
            not _db_available
            or _get_db_session is None
            or _DBCollectionArtifact is None
        ):
            return None

        get_session = _get_db_session
        DBCollectionArtifact = _DBCollectionArtifact
        try:
            session = get_session()
            try:
                row = (
                    session.query(DBCollectionArtifact.description)
                    .filter(DBCollectionArtifact.artifact_uuid == uuid)
                    .order_by(DBCollectionArtifact.added_at.desc())
                    .first()
                )
                return row[0] if row and row[0] else None
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "get_collection_description() failed for uuid '%s': %s",
                uuid,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Deduplication cluster queries
    # ------------------------------------------------------------------

    def get_duplicate_cluster_members(
        self,
        cluster_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """Return all artifacts that belong to the given deduplication cluster.

        In this implementation *cluster_id* is treated as an artifact UUID.
        The method fetches all ``DuplicatePair`` rows where either
        ``artifact1_uuid`` or ``artifact2_uuid`` matches *cluster_id*, then
        loads the full artifact for each unique UUID in the cluster.

        Args:
            cluster_id: Artifact UUID that anchors the cluster.
            ctx: Optional per-request metadata (unused).

        Returns:
            List of :class:`ArtifactDTO` objects representing cluster members,
            including the anchor artifact.  Returns an empty list when the DB
            is unavailable or no pairs are found.
        """
        if (
            not _db_available
            or _get_db_session is None
            or _DBDuplicatePair is None
            or _DBArtifact is None
        ):
            return []

        get_session = _get_db_session
        DBDuplicatePair = _DBDuplicatePair
        DBArtifact = _DBArtifact
        try:
            session = get_session()
            try:
                rows = (
                    session.query(
                        DBDuplicatePair.artifact1_uuid,
                        DBDuplicatePair.artifact2_uuid,
                    )
                    .filter(
                        (DBDuplicatePair.artifact1_uuid == cluster_id)
                        | (DBDuplicatePair.artifact2_uuid == cluster_id),
                        DBDuplicatePair.ignored.is_(False),
                    )
                    .all()
                )
                # Collect all unique UUIDs in the cluster (including the anchor).
                cluster_uuids: set[str] = {cluster_id}
                for r1, r2 in rows:
                    cluster_uuids.add(r1)
                    cluster_uuids.add(r2)

                # Resolve each UUID to an artifact ID, then fetch the DTO.
                id_rows = (
                    session.query(DBArtifact.id, DBArtifact.uuid)
                    .filter(DBArtifact.uuid.in_(list(cluster_uuids)))
                    .all()
                )
            finally:
                session.close()

            results: List[ArtifactDTO] = []
            for artifact_id, db_uuid in id_rows:
                dto = self.get(artifact_id, ctx=ctx)
                if dto is not None:
                    # Override uuid with the confirmed DB value.
                    results.append(
                        ArtifactDTO(
                            id=dto.id,
                            name=dto.name,
                            artifact_type=dto.artifact_type,
                            uuid=db_uuid,
                            source=dto.source,
                            version=dto.version,
                            scope=dto.scope,
                            description=dto.description,
                            content_path=dto.content_path,
                            metadata=dto.metadata,
                            tags=dto.tags,
                            is_outdated=dto.is_outdated,
                            local_modified=dto.local_modified,
                            project_id=dto.project_id,
                            created_at=dto.created_at,
                            updated_at=dto.updated_at,
                        )
                    )
            return results
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "get_duplicate_cluster_members() failed for cluster_id '%s': %s",
                cluster_id,
                exc,
            )
            return []

    # ------------------------------------------------------------------
    # Existence and type queries
    # ------------------------------------------------------------------

    def validate_exists(
        self,
        uuid: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Check whether an artifact with the given UUID exists.

        Attempts a lightweight DB lookup first.  Falls back to a full
        filesystem scan when the DB is unavailable.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            ctx: Optional per-request metadata (unused).

        Returns:
            ``True`` when an artifact with *uuid* exists, ``False`` otherwise.
        """
        if (
            _db_available
            and _get_db_session is not None
            and _DBArtifact is not None
        ):
            get_session = _get_db_session
            DBArtifact = _DBArtifact
            try:
                session = get_session()
                try:
                    count = (
                        session.query(DBArtifact.uuid)
                        .filter(DBArtifact.uuid == uuid)
                        .count()
                    )
                    return count > 0
                finally:
                    session.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "validate_exists() DB check failed for uuid '%s': %s",
                    uuid,
                    exc,
                )

        # Filesystem fallback — linear scan.
        return self.get_by_uuid(uuid, ctx=ctx) is not None

    def get_by_type(
        self,
        artifact_type: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """Return all artifacts of the specified type.

        Convenience wrapper around :meth:`list` with an ``artifact_type``
        filter and no pagination cap (returns all matching artifacts).

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``, ``"command"``).
            ctx: Optional per-request metadata (unused).

        Returns:
            List of :class:`ArtifactDTO` objects matching *artifact_type*.
        """
        return self.list(
            filters={"artifact_type": artifact_type},
            offset=0,
            limit=10_000,
            ctx=ctx,
        )

    # ------------------------------------------------------------------
    # Collection-level mutations
    # ------------------------------------------------------------------

    def update_collection_tags(
        self,
        uuid: str,
        tags: List[str],
        ctx: Optional[RequestContext] = None,
    ) -> None:
        """Replace the collection-level tags for an artifact.

        Updates the ``tags_json`` column on all ``CollectionArtifact`` rows
        for this UUID so that the collection-level tag set is authoritative.
        When the DB is unavailable, falls back to updating the intrinsic
        artifact tags via the filesystem.

        Args:
            uuid: Stable artifact UUID (32-char hex).
            tags: New complete list of tag name strings.
            ctx: Optional per-request metadata (unused).

        Raises:
            KeyError: If no artifact with *uuid* exists.
        """
        import json as _json

        if (
            _db_available
            and _get_db_session is not None
            and _DBCollectionArtifact is not None
            and _DBArtifact is not None
        ):
            get_session = _get_db_session
            DBCollectionArtifact = _DBCollectionArtifact
            DBArtifact = _DBArtifact
            try:
                session = get_session()
                try:
                    # Verify the artifact exists.
                    exists = (
                        session.query(DBArtifact.uuid)
                        .filter(DBArtifact.uuid == uuid)
                        .count()
                        > 0
                    )
                    if not exists:
                        raise KeyError(uuid)

                    tags_json = _json.dumps(tags)
                    (
                        session.query(DBCollectionArtifact)
                        .filter(DBCollectionArtifact.artifact_uuid == uuid)
                        .update({"tags_json": tags_json})
                    )
                    session.commit()
                    return
                except KeyError:
                    session.rollback()
                    raise
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()
            except KeyError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "update_collection_tags() DB update failed for uuid '%s': %s",
                    uuid,
                    exc,
                )
                # Fall through to filesystem fallback.

        # Filesystem fallback: locate the artifact by UUID and update its tags.
        dto = self.get_by_uuid(uuid, ctx=ctx)
        if dto is None:
            raise KeyError(uuid)
        self.set_tags(id=dto.id, tag_ids=tags, ctx=ctx)


# ---------------------------------------------------------------------------
# Tag helper
# ---------------------------------------------------------------------------


def _tag_name_to_dto(tag_name: str) -> TagDTO:
    """Build a minimal :class:`TagDTO` from a plain tag name string.

    The filesystem does not store tag metadata beyond the name, so ``id`` is
    set to the slug and ``color`` is ``None``.

    Args:
        tag_name: Raw tag name string.

    Returns:
        Minimal :class:`TagDTO`.
    """
    slug = tag_name.lower().replace(" ", "-")
    return TagDTO(
        id=slug,
        name=tag_name,
        slug=slug,
        color=None,
        artifact_count=0,
        deployment_set_count=0,
        created_at=None,
        updated_at=None,
    )
