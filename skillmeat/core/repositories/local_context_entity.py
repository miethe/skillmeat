"""Local DB-backed implementation of IContextEntityRepository.

Stores context entities as ``Artifact`` rows in the SQLite cache database,
using the ``context_entity_types`` set to distinguish them from regular
artifacts.  Category associations are managed through the
``ArtifactCategoryAssociation`` join table.

Design notes
------------
* Context entities have no filesystem representation — they live exclusively
  in the DB cache (the Artifact table).  There is no write-through to the
  filesystem for CRUD operations; ``deploy()`` is the one operation that
  writes a file to disk.
* The ``Artifact.id`` column serves as the external entity ID and uses the
  ``"ctx_<hex>"`` scheme established by the existing router.
* ``Artifact.uuid`` is the internal stable identifier used for join table
  relationships (``ArtifactCategoryAssociation.artifact_uuid``).
* Sessions are obtained via ``get_session()`` from the cache models module.
  Each public method opens its own short-lived session and closes it in a
  ``finally`` block to match the existing router pattern.
* Business-logic (validation, content assembly) stays in the router / caller
  layer.  This repository is pure data access.

Python 3.9+ compatible.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ContextEntityDTO
from skillmeat.core.interfaces.repositories import IContextEntityRepository

logger = logging.getLogger(__name__)

__all__ = ["LocalContextEntityRepository"]

# ---------------------------------------------------------------------------
# Optional DB imports — graceful degradation when cache module absent.
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import (
        Artifact as _DBArtifact,
        ArtifactCategoryAssociation as _DBAssoc,
        Project as _DBProject,
        get_session as _get_session,
    )

    _db_available = True
except ImportError:  # pragma: no cover
    _DBArtifact = None  # type: ignore[assignment]
    _DBAssoc = None  # type: ignore[assignment]
    _DBProject = None  # type: ignore[assignment]
    _get_session = None  # type: ignore[assignment]
    _db_available = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Context entity type discriminators (mirrors CONTEXT_ENTITY_TYPES in router)
_CONTEXT_ENTITY_TYPES = frozenset(
    {
        "project_config",
        "spec_file",
        "rule_file",
        "context_file",
        "progress_template",
    }
)

# Sentinel project ID for context entities (must match router constant)
_CONTEXT_ENTITIES_PROJECT_ID = "ctx_project_global"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_project(session: Any) -> None:
    """Ensure the sentinel project row exists in the DB.

    Context entities are stored as ``Artifact`` rows but are not tied to any
    real project.  A sentinel project satisfies the foreign key constraint.

    Args:
        session: Active SQLAlchemy session.
    """
    project = (
        session.query(_DBProject).filter_by(id=_CONTEXT_ENTITIES_PROJECT_ID).first()
    )
    if not project:
        project = _DBProject(
            id=_CONTEXT_ENTITIES_PROJECT_ID,
            name="Context Entities",
            path="~/.skillmeat/context-entities",
            description="Virtual project for context entity storage",
            status="active",
        )
        session.add(project)
        session.commit()
        logger.info(
            "Created sentinel project for context entities: %s",
            _CONTEXT_ENTITIES_PROJECT_ID,
        )


def _get_category_ids(session: Any, artifact_uuid: str) -> List[int]:
    """Return sorted list of category IDs associated with an artifact.

    Args:
        session: Active SQLAlchemy session.
        artifact_uuid: The ``Artifact.uuid`` hex field.

    Returns:
        Sorted list of ``ContextEntityCategory.id`` values.
    """
    rows = (
        session.query(_DBAssoc)
        .filter(_DBAssoc.artifact_uuid == artifact_uuid)
        .all()
    )
    return sorted(row.category_id for row in rows)


def _sync_category_associations(
    session: Any,
    artifact_uuid: str,
    category_ids: List[int],
) -> None:
    """Replace all category associations for an artifact.

    Deletes existing ``ArtifactCategoryAssociation`` rows then inserts new
    rows for each ID in *category_ids*.

    Args:
        session: Active SQLAlchemy session.
        artifact_uuid: The ``Artifact.uuid`` hex field.
        category_ids: Ordered list of category IDs to associate.
    """
    session.query(_DBAssoc).filter(
        _DBAssoc.artifact_uuid == artifact_uuid
    ).delete(synchronize_session=False)

    for cat_id in category_ids:
        session.add(_DBAssoc(artifact_uuid=artifact_uuid, category_id=cat_id))


def _encode_cursor(value: str) -> str:
    """Base64-encode a cursor value.

    Args:
        value: Raw cursor string (typically an artifact ID).

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(value.encode()).decode()


def _decode_cursor(cursor: str) -> Optional[str]:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64-encoded cursor string.

    Returns:
        Decoded string, or ``None`` if the cursor is malformed.
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception:
        return None


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hex digest of *content*.

    Args:
        content: UTF-8 text to hash.

    Returns:
        64-character hex string.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _orm_to_dto(artifact: Any, category_ids: Optional[List[int]] = None) -> ContextEntityDTO:
    """Convert an ``Artifact`` ORM row to a :class:`ContextEntityDTO`.

    Args:
        artifact: SQLAlchemy ``Artifact`` model instance.
        category_ids: Pre-fetched category ID list.  When ``None`` the caller
            is responsible for populating via a separate query.

    Returns:
        An immutable :class:`ContextEntityDTO` populated from the ORM row.
    """
    created_str: Optional[str] = None
    updated_str: Optional[str] = None
    if getattr(artifact, "created_at", None) is not None:
        created_str = (
            artifact.created_at.isoformat()
            if hasattr(artifact.created_at, "isoformat")
            else str(artifact.created_at)
        )
    if getattr(artifact, "updated_at", None) is not None:
        updated_str = (
            artifact.updated_at.isoformat()
            if hasattr(artifact.updated_at, "isoformat")
            else str(artifact.updated_at)
        )

    raw_platforms = artifact.target_platforms or []
    platforms: List[str] = [str(p) for p in raw_platforms]

    return ContextEntityDTO(
        id=artifact.id,
        name=artifact.name,
        entity_type=artifact.type,
        content=artifact.content or "",
        path_pattern=artifact.path_pattern or "",
        description=artifact.description,
        category=artifact.category,
        auto_load=bool(artifact.auto_load),
        version=artifact.deployed_version,
        target_platforms=platforms,
        content_hash=artifact.content_hash,
        category_ids=list(category_ids or []),
        core_content=artifact.core_content,
        created_at=created_str,
        updated_at=updated_str,
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalContextEntityRepository(IContextEntityRepository):
    """DB-backed :class:`IContextEntityRepository` implementation.

    All operations use the SQLite cache database via ``get_session()``.
    Context entities are stored as ``Artifact`` rows distinguished by their
    ``type`` being one of the five context entity type discriminators.

    Args:
        db_path: Optional explicit path to the SQLite database file.  When
            ``None``, ``get_session()`` resolves the default location.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Internal session helper
    # ------------------------------------------------------------------

    def _session(self) -> Any:
        """Open and return a SQLAlchemy session.

        Raises:
            RuntimeError: When the cache module is unavailable.
        """
        if not _db_available or _get_session is None:
            raise RuntimeError(
                "LocalContextEntityRepository requires the skillmeat.cache "
                "module but it is not available in this environment."
            )
        return _get_session(self._db_path) if self._db_path else _get_session()

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        after: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[ContextEntityDTO]:
        """Return a page of context entities matching optional filter criteria.

        Supported filter keys: ``entity_type``, ``category``, ``auto_load``,
        ``search`` (full-text across name, description, path_pattern).

        Args:
            filters: Optional key/value filter map.
            limit: Maximum number of records (1-100).
            after: Opaque base64 cursor for the next page.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO`.
        """
        session = self._session()
        try:
            query = session.query(_DBArtifact).filter(
                _DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES)
            )

            if filters:
                entity_type = filters.get("entity_type")
                if entity_type:
                    query = query.filter(_DBArtifact.type == entity_type)

                category = filters.get("category")
                if category:
                    query = query.filter(_DBArtifact.category == category)

                auto_load = filters.get("auto_load")
                if auto_load is not None:
                    query = query.filter(_DBArtifact.auto_load == bool(auto_load))

                search = filters.get("search")
                if search:
                    pattern = f"%{search}%"
                    query = query.filter(
                        _DBArtifact.name.ilike(pattern)
                        | _DBArtifact.description.ilike(pattern)
                        | _DBArtifact.path_pattern.ilike(pattern)
                    )

            if after:
                cursor_id = _decode_cursor(after)
                if cursor_id:
                    query = query.filter(_DBArtifact.id > cursor_id)
                else:
                    logger.warning("Invalid cursor value ignored: %r", after)

            query = query.order_by(_DBArtifact.id)
            artifacts = query.limit(limit).all()

            return [
                _orm_to_dto(
                    artifact,
                    category_ids=_get_category_ids(session, artifact.uuid),
                )
                for artifact in artifacts
            ]
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        entity_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ContextEntityDTO]:
        """Return a context entity by its identifier.

        Args:
            entity_id: Artifact primary key (e.g. ``"ctx_abc123"``).
            ctx: Optional per-request metadata.

        Returns:
            :class:`ContextEntityDTO` when found, ``None`` otherwise.
        """
        session = self._session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == entity_id)
                .filter(_DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES))
                .first()
            )
            if not artifact:
                return None
            return _orm_to_dto(
                artifact,
                category_ids=_get_category_ids(session, artifact.uuid),
            )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        entity_type: str,
        content: str,
        path_pattern: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        auto_load: bool = False,
        version: Optional[str] = None,
        target_platforms: Optional[List[str]] = None,
        category_ids: Optional[List[int]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> ContextEntityDTO:
        """Persist a new context entity and return the stored representation.

        Args:
            name: Human-readable entity name.
            entity_type: Entity type discriminator key.
            content: Assembled markdown content.
            path_pattern: Target deployment path.
            description: Optional description.
            category: Optional category label.
            auto_load: Whether to auto-load on startup.
            version: Optional version string.
            target_platforms: Optional target platform identifiers.
            category_ids: Ordered category IDs to associate.
            ctx: Optional per-request metadata.

        Returns:
            The persisted :class:`ContextEntityDTO`.

        Raises:
            ValueError: If *entity_type* is not a recognised context entity type.
        """
        if entity_type not in _CONTEXT_ENTITY_TYPES:
            raise ValueError(
                f"Unrecognised entity_type {entity_type!r}. "
                f"Valid values: {sorted(_CONTEXT_ENTITY_TYPES)}"
            )

        content_hash = _compute_content_hash(content)
        artifact_id = f"ctx_{uuid.uuid4().hex[:12]}"

        session = self._session()
        try:
            _ensure_project(session)

            artifact = _DBArtifact(
                id=artifact_id,
                project_id=_CONTEXT_ENTITIES_PROJECT_ID,
                name=name,
                type=entity_type,
                content=content,
                path_pattern=path_pattern,
                description=description,
                category=category,
                auto_load=auto_load,
                deployed_version=version,
                target_platforms=target_platforms,
                content_hash=content_hash,
            )
            session.add(artifact)
            session.flush()  # Populate artifact.uuid before associations

            if category_ids is not None:
                _sync_category_associations(session, artifact.uuid, category_ids)

            session.commit()
            session.refresh(artifact)

            fetched_category_ids = _get_category_ids(session, artifact.uuid)
            logger.info(
                "Created context entity %s ('%s') type=%s",
                artifact.id,
                artifact.name,
                artifact.type,
            )
            return _orm_to_dto(artifact, category_ids=fetched_category_ids)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(
        self,
        entity_id: str,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> ContextEntityDTO:
        """Apply a partial update to an existing context entity.

        Supported update keys: ``name``, ``entity_type``, ``content``,
        ``path_pattern``, ``description``, ``category``, ``auto_load``,
        ``version``, ``target_platforms``, ``category_ids``.

        If ``content`` is updated, ``content_hash`` is recomputed automatically.

        Args:
            entity_id: Artifact primary key.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`ContextEntityDTO`.

        Raises:
            KeyError: If no entity with *entity_id* exists.
        """
        session = self._session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == entity_id)
                .filter(_DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES))
                .first()
            )
            if not artifact:
                raise KeyError(f"Context entity '{entity_id}' not found")

            content_changed = False

            if "name" in updates and updates["name"] is not None:
                artifact.name = updates["name"]
            if "entity_type" in updates and updates["entity_type"] is not None:
                new_type = updates["entity_type"]
                if new_type not in _CONTEXT_ENTITY_TYPES:
                    raise ValueError(
                        f"Unrecognised entity_type {new_type!r}. "
                        f"Valid values: {sorted(_CONTEXT_ENTITY_TYPES)}"
                    )
                artifact.type = new_type
            if "content" in updates and updates["content"] is not None:
                artifact.content = updates["content"]
                content_changed = True
            if "core_content" in updates and updates["core_content"] is not None:
                artifact.core_content = updates["core_content"]
            if "path_pattern" in updates and updates["path_pattern"] is not None:
                artifact.path_pattern = updates["path_pattern"]
            if "description" in updates:
                artifact.description = updates["description"]
            if "category" in updates:
                artifact.category = updates["category"]
            if "auto_load" in updates and updates["auto_load"] is not None:
                artifact.auto_load = bool(updates["auto_load"])
            if "version" in updates:
                artifact.deployed_version = updates["version"]
            if "target_platforms" in updates:
                artifact.target_platforms = updates["target_platforms"]
            if "category_ids" in updates and updates["category_ids"] is not None:
                _sync_category_associations(
                    session, artifact.uuid, updates["category_ids"]
                )

            if content_changed:
                artifact.content_hash = _compute_content_hash(artifact.content or "")

            session.commit()
            session.refresh(artifact)

            fetched_category_ids = _get_category_ids(session, artifact.uuid)
            logger.info("Updated context entity %s", entity_id)
            return _orm_to_dto(artifact, category_ids=fetched_category_ids)
        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(
        self,
        entity_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> None:
        """Delete a context entity permanently.

        Args:
            entity_id: Artifact primary key.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no entity with *entity_id* exists.
        """
        session = self._session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == entity_id)
                .filter(_DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES))
                .first()
            )
            if not artifact:
                raise KeyError(f"Context entity '{entity_id}' not found")

            session.delete(artifact)
            session.commit()
            logger.info("Deleted context entity %s", entity_id)
        except KeyError:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(
        self,
        entity_id: str,
        project_path: str,
        options: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> None:
        """Deploy a context entity's content to a filesystem project path.

        Writes the assembled content to the location specified by the entity's
        ``path_pattern``, resolved against *project_path*.

        Args:
            entity_id: Artifact primary key.
            project_path: Absolute filesystem path to the target project.
            options: Optional deployment options.  Supported keys:
                ``overwrite`` (bool, default ``False``) — whether to overwrite
                an existing file.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If *entity_id* does not exist.
            FileExistsError: If the target file already exists and
                ``options["overwrite"]`` is ``False``.
            ValueError: If *project_path* does not exist or the entity has no
                ``path_pattern``.
        """
        opts = options or {}
        overwrite = bool(opts.get("overwrite", False))

        resolved_project = Path(project_path).expanduser().resolve()
        if not resolved_project.exists():
            raise ValueError(
                f"Project path does not exist: {resolved_project}"
            )

        session = self._session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == entity_id)
                .filter(_DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES))
                .first()
            )
            if not artifact:
                raise KeyError(f"Context entity '{entity_id}' not found")

            if not artifact.path_pattern:
                raise ValueError(
                    f"Context entity '{entity_id}' has no path_pattern"
                )

            target_path = resolved_project / artifact.path_pattern
            content = artifact.content or ""

            if target_path.exists() and not overwrite:
                raise FileExistsError(
                    f"File already exists: {target_path}. "
                    "Pass options={'overwrite': True} to overwrite."
                )

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            logger.info(
                "Deployed context entity %s to %s",
                entity_id,
                target_path,
            )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Content access
    # ------------------------------------------------------------------

    def get_content(
        self,
        entity_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[str]:
        """Return the raw markdown content of a context entity.

        Args:
            entity_id: Artifact primary key.
            ctx: Optional per-request metadata.

        Returns:
            Raw content string when found, ``None`` otherwise.
        """
        session = self._session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == entity_id)
                .filter(_DBArtifact.type.in_(_CONTEXT_ENTITY_TYPES))
                .first()
            )
            if not artifact:
                return None
            return artifact.content or ""
        finally:
            session.close()
