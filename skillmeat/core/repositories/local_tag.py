"""Local DB-backed implementation of the ITagRepository interface.

Tags are stored exclusively in the SQLite DB cache (there is no filesystem
representation for tags).  This repository delegates all operations to the
existing :class:`~skillmeat.cache.repositories.TagRepository` (cache layer)
and converts the ORM :class:`~skillmeat.cache.models.Tag` instances into the
:class:`~skillmeat.core.interfaces.dtos.TagDTO` contract required by the
hexagonal architecture.

The ``assign``/``unassign`` methods bridge between the interface's
``artifact_id`` (``"type:name"`` string) and the cache layer's
``artifact_uuid`` (ADR-007 stable hex identity) by performing a DB lookup via
the ``Artifact`` model.

Design notes:
- The ``session_factory`` argument is a zero-argument callable that returns a
  SQLAlchemy session.  Callers may omit it to use the module-level
  ``get_session()`` default; tests can inject a factory bound to an in-memory
  database.
- All DB access happens inside methods, not at construction time, so the
  repository can be constructed cheaply even when the DB is unavailable.
- Python 3.9+ compatible (no ``X | Y`` union syntax in runtime code).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import TagDTO
from skillmeat.core.interfaces.repositories import ITagRepository

logger = logging.getLogger(__name__)

__all__ = ["LocalTagRepository"]


def _slugify(name: str) -> str:
    """Derive a URL-friendly slug from a tag name.

    Converts to lowercase, replaces non-alphanumeric sequences with hyphens,
    and strips leading/trailing hyphens.

    Args:
        name: Human-readable tag name.

    Returns:
        Kebab-case slug string.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "tag"


def _tag_to_dto(tag: Any) -> TagDTO:
    """Convert a cache-layer :class:`Tag` ORM object to a :class:`TagDTO`.

    Args:
        tag: SQLAlchemy ``Tag`` model instance.

    Returns:
        Immutable :class:`TagDTO`.
    """
    artifact_count = 0
    deployment_set_count = 0
    try:
        artifact_count = len(tag.artifact_tags) if tag.artifact_tags else 0
    except Exception:
        pass
    try:
        deployment_set_count = (
            len(tag.deployment_set_tags) if tag.deployment_set_tags else 0
        )
    except Exception:
        pass

    created_at = None
    updated_at = None
    try:
        if tag.created_at is not None:
            created_at = (
                tag.created_at.isoformat()
                if hasattr(tag.created_at, "isoformat")
                else str(tag.created_at)
            )
    except Exception:
        pass
    try:
        if tag.updated_at is not None:
            updated_at = (
                tag.updated_at.isoformat()
                if hasattr(tag.updated_at, "isoformat")
                else str(tag.updated_at)
            )
    except Exception:
        pass

    return TagDTO(
        id=tag.id,
        name=tag.name,
        slug=tag.slug,
        color=getattr(tag, "color", None),
        artifact_count=artifact_count,
        deployment_set_count=deployment_set_count,
        created_at=created_at,
        updated_at=updated_at,
    )


class LocalTagRepository(ITagRepository):
    """``ITagRepository`` backed by the SkillMeat SQLite DB cache.

    Delegates to :class:`~skillmeat.cache.repositories.TagRepository` for
    CRUD operations and artifact-tag association management.

    Args:
        session_factory: Optional zero-argument callable returning a
            SQLAlchemy session.  When ``None``, the module-level
            ``skillmeat.cache.models.get_session`` is used.
        db_path: Optional path to the SQLite DB file.  Passed through to
            ``TagRepository`` when *session_factory* is ``None``.
    """

    def __init__(
        self,
        session_factory: Optional[Callable[[], Any]] = None,
        db_path: Optional[Any] = None,
    ) -> None:
        self._session_factory = session_factory
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tag_repo(self) -> Any:
        """Return a cache-layer ``TagRepository`` instance.

        Imports are deferred to avoid circular imports and to allow the
        repository to be constructed even when the DB is unavailable.

        Returns:
            A :class:`~skillmeat.cache.repositories.TagRepository` instance.
        """
        try:
            from skillmeat.cache.repositories import TagRepository

            return TagRepository(db_path=self._db_path)
        except Exception as exc:
            raise RuntimeError(
                f"LocalTagRepository: failed to create TagRepository: {exc}"
            ) from exc

    def _resolve_artifact_uuid(self, artifact_id: str) -> Optional[str]:
        """Resolve a ``"type:name"`` artifact ID to its UUID.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.

        Returns:
            The artifact's ``uuid`` hex string, or ``None`` if not found.
        """
        try:
            from skillmeat.cache.models import Artifact, get_session

            session = (
                self._session_factory()
                if self._session_factory
                else get_session()
            )
            try:
                artifact = (
                    session.query(Artifact)
                    .filter(Artifact.id == artifact_id)
                    .first()
                )
                return artifact.uuid if artifact else None
            finally:
                session.close()
        except Exception as exc:
            logger.debug(
                "_resolve_artifact_uuid: could not resolve '%s': %s",
                artifact_id,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # ITagRepository — single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[TagDTO]:
        """Return a tag by its unique identifier.

        Args:
            id: Tag unique identifier (hex string).
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.TagDTO` when found,
            ``None`` otherwise.
        """
        tag_repo = self._get_tag_repo()
        tag = tag_repo.get_by_id(id)
        return _tag_to_dto(tag) if tag else None

    def get_by_slug(
        self,
        slug: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[TagDTO]:
        """Return a tag by its URL-friendly slug.

        Args:
            slug: Kebab-case slug string.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.TagDTO` when found,
            ``None`` otherwise.
        """
        tag_repo = self._get_tag_repo()
        tag = tag_repo.get_by_slug(slug)
        return _tag_to_dto(tag) if tag else None

    # ------------------------------------------------------------------
    # ITagRepository — collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[TagDTO]:
        """Return all tags, optionally filtered by name prefix.

        Supported filter keys:
        - ``name``: substring/prefix match against the tag name.

        Args:
            filters: Optional filter map.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.TagDTO` objects.
        """
        filters = filters or {}
        tag_repo = self._get_tag_repo()

        name_filter: Optional[str] = filters.get("name")

        if name_filter:
            tags = tag_repo.search_by_name(name_filter, limit=1000)
        else:
            tags, _cursor, _has_more = tag_repo.list_all(limit=1000)

        return [_tag_to_dto(t) for t in tags]

    # ------------------------------------------------------------------
    # ITagRepository — mutations
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        color: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> TagDTO:
        """Create a new tag.

        The slug is derived automatically from *name* using :func:`_slugify`.

        Args:
            name: Human-readable tag name (must be unique).
            color: Optional hex color code (e.g. ``"#FF5733"``).
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.TagDTO`.

        Raises:
            ValueError: If a tag with the same name or slug already exists.
        """
        slug = _slugify(name)
        tag_repo = self._get_tag_repo()
        try:
            tag = tag_repo.create(name=name, slug=slug, color=color)
        except Exception as exc:
            # Cache TagRepository raises RepositoryError; surface as ValueError.
            raise ValueError(f"Failed to create tag '{name}': {exc}") from exc
        return _tag_to_dto(tag)

    def update(
        self,
        id: str,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> TagDTO:
        """Apply a partial update to an existing tag.

        Recognised update keys: ``name``, ``slug``, ``color``.

        Args:
            id: Tag unique identifier.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.TagDTO`.

        Raises:
            KeyError: If no tag with *id* exists.
        """
        tag_repo = self._get_tag_repo()
        tag = tag_repo.update(
            tag_id=id,
            name=updates.get("name"),
            slug=updates.get("slug"),
            color=updates.get("color"),
        )
        if tag is None:
            raise KeyError(f"No tag found with id '{id}'")
        return _tag_to_dto(tag)

    def delete(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Delete a tag and all its artifact associations.

        Args:
            id: Tag unique identifier.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the tag was found and deleted, ``False`` otherwise.
        """
        tag_repo = self._get_tag_repo()
        return tag_repo.delete(tag_id=id)

    # ------------------------------------------------------------------
    # ITagRepository — artifact associations
    # ------------------------------------------------------------------

    def assign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Associate a tag with an artifact.

        Idempotent: returns ``True`` if the association already exists.

        Args:
            tag_id: Tag unique identifier.
            artifact_id: Artifact primary key in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` on success.

        Raises:
            KeyError: If *tag_id* or *artifact_id* does not exist.
        """
        artifact_uuid = self._resolve_artifact_uuid(artifact_id)
        if artifact_uuid is None:
            raise KeyError(
                f"assign: artifact '{artifact_id}' not found in DB cache"
            )

        tag_repo = self._get_tag_repo()
        try:
            tag_repo.add_tag_to_artifact(
                artifact_uuid=artifact_uuid,
                tag_id=tag_id,
            )
            return True
        except Exception as exc:
            exc_str = str(exc).lower()
            # Treat "already exists" / "already has tag" as idempotent success.
            if "already" in exc_str or "exists" in exc_str:
                return True
            raise KeyError(
                f"assign: failed to associate tag '{tag_id}' with "
                f"artifact '{artifact_id}': {exc}"
            ) from exc

    def unassign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Remove the association between a tag and an artifact.

        Args:
            tag_id: Tag unique identifier.
            artifact_id: Artifact primary key in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when the association existed and was removed, ``False``
            if there was no such association.
        """
        artifact_uuid = self._resolve_artifact_uuid(artifact_id)
        if artifact_uuid is None:
            logger.debug(
                "unassign: artifact '%s' not found in DB cache — returning False",
                artifact_id,
            )
            return False

        tag_repo = self._get_tag_repo()
        return tag_repo.remove_tag_from_artifact(
            artifact_uuid=artifact_uuid,
            tag_id=tag_id,
        )
