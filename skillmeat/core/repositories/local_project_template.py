"""Local DB-backed implementation of IProjectTemplateRepository.

Delegates to SQLAlchemy ORM models (``ProjectTemplate``, ``TemplateEntity``,
``Artifact``) for all storage operations.  The optional
``deploy_template_async`` service is called for the :meth:`deploy` method;
if the service module is unavailable (e.g. during unit tests without a DB
fixture) the call degrades gracefully and raises ``NotImplementedError``.

Design notes
------------
* Primary keys for ``ProjectTemplate`` rows are hex UUIDs generated at
  creation time.
* DTO conversion is done at the repository boundary; no ORM objects cross
  into the caller.
* Mutations that could violate constraints (unknown entity IDs, duplicate
  template names) raise ``ValueError`` rather than letting the DB surface raw
  integrity errors.
* The ``deploy`` method intentionally stays thin: it delegates to the
  existing ``deploy_template_async`` coroutine that already lives in
  ``skillmeat.core.services.template_service`` and is tested separately.
  Because that coroutine is async, :meth:`deploy` runs it via
  ``asyncio.run()`` when called from synchronous code; callers that are
  already in an async context should call the service directly.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ProjectTemplateDTO, TemplateEntityDTO
from skillmeat.core.interfaces.repositories import IProjectTemplateRepository

# ---------------------------------------------------------------------------
# Optional DB import — graceful degradation when cache module is absent.
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import (
        Artifact as _DBArtifact,
        ProjectTemplate as _DBProjectTemplate,
        TemplateEntity as _DBTemplateEntity,
        get_session as _get_db_session,
    )

    _db_available = True
except ImportError:  # pragma: no cover
    _get_db_session = None  # type: ignore[assignment]
    _DBArtifact = None  # type: ignore[assignment]
    _DBProjectTemplate = None  # type: ignore[assignment]
    _DBTemplateEntity = None  # type: ignore[assignment]
    _db_available = False

logger = logging.getLogger(__name__)

__all__ = ["LocalProjectTemplateRepository"]


# ---------------------------------------------------------------------------
# DTO conversion helpers
# ---------------------------------------------------------------------------


def _entity_to_dto(te: "_DBTemplateEntity") -> TemplateEntityDTO:
    """Convert a :class:`TemplateEntity` ORM row to a :class:`TemplateEntityDTO`.

    Args:
        te: ORM row with a populated ``artifact`` relationship.

    Returns:
        Immutable :class:`TemplateEntityDTO`.
    """
    artifact = te.artifact
    return TemplateEntityDTO(
        artifact_id=te.artifact_id,
        name=artifact.name if artifact else te.artifact_id,
        artifact_type=artifact.artifact_type if artifact else "",
        deploy_order=te.deploy_order,
        required=te.required,
        path_pattern=artifact.path_pattern if artifact else None,
    )


def _template_to_dto(
    template: "_DBProjectTemplate",
    *,
    include_entities: bool = True,
) -> ProjectTemplateDTO:
    """Convert a :class:`ProjectTemplate` ORM row to a :class:`ProjectTemplateDTO`.

    Args:
        template: ORM row.  When *include_entities* is ``True`` the
            ``entities`` relationship must already be loaded (the ORM model
            uses ``lazy="selectin"`` so this is normally automatic within an
            open session).
        include_entities: Whether to populate the ``entities`` list.  Pass
            ``False`` for list-view calls that skip entity details for
            performance.

    Returns:
        Immutable :class:`ProjectTemplateDTO`.
    """
    if include_entities:
        entities: List[TemplateEntityDTO] = [
            _entity_to_dto(te) for te in (template.entities or [])
        ]
    else:
        entities = []

    return ProjectTemplateDTO(
        id=template.id,
        name=template.name,
        description=template.description,
        collection_id=template.collection_id,
        default_project_config_id=template.default_project_config_id,
        entities=entities,
        entity_count=len(template.entities) if template.entities is not None else 0,
        created_at=template.created_at.isoformat() if template.created_at else None,
        updated_at=template.updated_at.isoformat() if template.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalProjectTemplateRepository(IProjectTemplateRepository):
    """SQLAlchemy-backed implementation of :class:`IProjectTemplateRepository`.

    All queries go through the singleton SQLite session returned by
    :func:`~skillmeat.cache.models.get_session`.  Mutations commit within
    their own transaction and roll back on error.

    Args:
        db_session_factory: Optional callable returning a SQLAlchemy
            :class:`~sqlalchemy.orm.Session`.  Defaults to the global
            :func:`~skillmeat.cache.models.get_session` from the cache
            module.  Pass an explicit factory in tests to avoid touching the
            production database.
    """

    def __init__(
        self,
        db_session_factory: Optional[Any] = None,
    ) -> None:
        if db_session_factory is not None:
            self._get_session = db_session_factory
        elif _db_available:
            self._get_session = _get_db_session
        else:  # pragma: no cover
            raise RuntimeError(
                "skillmeat.cache is not available; cannot create "
                "LocalProjectTemplateRepository without a session factory."
            )

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: RequestContext | None = None,
    ) -> list[ProjectTemplateDTO]:
        """Return a page of project templates ordered by ``created_at`` descending.

        Args:
            filters: Optional key/value filter map.  Supported keys:
                ``collection_id`` (exact match).
            limit: Maximum number of records to return (1–100).
            offset: Zero-based record offset.
            ctx: Unused; accepted for interface compatibility.

        Returns:
            List of :class:`ProjectTemplateDTO` objects (entities list is
            empty for performance; call :meth:`get` for full details).
        """
        session = self._get_session()
        try:
            query = session.query(_DBProjectTemplate).order_by(
                _DBProjectTemplate.created_at.desc()
            )

            if filters:
                collection_id = filters.get("collection_id")
                if collection_id is not None:
                    query = query.filter(
                        _DBProjectTemplate.collection_id == collection_id
                    )

            rows = query.limit(limit).offset(offset).all()
            return [_template_to_dto(row, include_entities=False) for row in rows]
        finally:
            session.close()

    def count(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> int:
        """Return the total number of project templates matching optional filters.

        Args:
            filters: Optional key/value filter map.  Supported keys:
                ``collection_id`` (exact match).
            ctx: Unused; accepted for interface compatibility.

        Returns:
            Integer count of matching project templates.
        """
        session = self._get_session()
        try:
            query = session.query(_DBProjectTemplate)
            if filters:
                collection_id = filters.get("collection_id")
                if collection_id is not None:
                    query = query.filter(
                        _DBProjectTemplate.collection_id == collection_id
                    )
            return query.count()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        template_id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectTemplateDTO | None:
        """Return a project template by identifier, including full entity details.

        Args:
            template_id: Template hex-UUID primary key.
            ctx: Unused; accepted for interface compatibility.

        Returns:
            :class:`ProjectTemplateDTO` with ``entities`` populated, or
            ``None`` if no matching template exists.
        """
        session = self._get_session()
        try:
            row = (
                session.query(_DBProjectTemplate)
                .filter(_DBProjectTemplate.id == template_id)
                .first()
            )
            if row is None:
                return None
            return _template_to_dto(row, include_entities=True)
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

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
            entity_ids: Ordered artifact primary keys.  Deploy order is
                derived from list position.
            description: Optional template description.
            collection_id: Optional owning collection identifier.
            default_project_config_id: Optional artifact ID for the default
                CLAUDE.md config.
            ctx: Unused; accepted for interface compatibility.

        Returns:
            The created :class:`ProjectTemplateDTO` with full entity details.

        Raises:
            ValueError: If any element of *entity_ids* does not correspond to
                a known artifact.
        """
        session = self._get_session()
        try:
            # Validate that all entity IDs exist.
            found_artifacts = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id.in_(entity_ids))
                .all()
            )
            found_ids = {a.id for a in found_artifacts}
            missing = set(entity_ids) - found_ids
            if missing:
                raise ValueError(
                    f"Unknown artifact IDs: {', '.join(sorted(missing))}"
                )

            if default_project_config_id is not None:
                config_artifact = (
                    session.query(_DBArtifact)
                    .filter(_DBArtifact.id == default_project_config_id)
                    .first()
                )
                if config_artifact is None:
                    raise ValueError(
                        f"Unknown default_project_config_id: {default_project_config_id}"
                    )

            now = datetime.utcnow()
            template = _DBProjectTemplate(
                id=uuid.uuid4().hex,
                name=name,
                description=description,
                collection_id=collection_id,
                default_project_config_id=default_project_config_id,
                created_at=now,
                updated_at=now,
            )
            session.add(template)

            for idx, entity_id in enumerate(entity_ids):
                session.add(
                    _DBTemplateEntity(
                        template_id=template.id,
                        artifact_id=entity_id,
                        deploy_order=idx,
                        required=True,
                    )
                )

            session.commit()
            session.refresh(template)

            logger.info(
                "Created project template %r with %d entities",
                template.name,
                len(entity_ids),
            )
            return _template_to_dto(template, include_entities=True)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(
        self,
        template_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ProjectTemplateDTO:
        """Apply a partial update to an existing project template.

        Supported keys in *updates*: ``name``, ``description``,
        ``entity_ids`` (full replacement of the entity list).

        Args:
            template_id: Template hex-UUID identifier.
            updates: Map of field names to new values.
            ctx: Unused; accepted for interface compatibility.

        Returns:
            The updated :class:`ProjectTemplateDTO`.

        Raises:
            KeyError: If no template with *template_id* exists.
            ValueError: If ``entity_ids`` contains unknown artifact IDs.
        """
        session = self._get_session()
        try:
            template = (
                session.query(_DBProjectTemplate)
                .filter(_DBProjectTemplate.id == template_id)
                .first()
            )
            if template is None:
                raise KeyError(f"No project template with id={template_id!r}")

            if "name" in updates and updates["name"] is not None:
                template.name = updates["name"]
            if "description" in updates:
                template.description = updates["description"]

            if "entity_ids" in updates and updates["entity_ids"] is not None:
                new_ids: list[str] = updates["entity_ids"]

                found_artifacts = (
                    session.query(_DBArtifact)
                    .filter(_DBArtifact.id.in_(new_ids))
                    .all()
                )
                found_ids = {a.id for a in found_artifacts}
                missing = set(new_ids) - found_ids
                if missing:
                    raise ValueError(
                        f"Unknown artifact IDs: {', '.join(sorted(missing))}"
                    )

                # Replace all entity associations.
                session.query(_DBTemplateEntity).filter(
                    _DBTemplateEntity.template_id == template_id
                ).delete(synchronize_session="fetch")

                for idx, entity_id in enumerate(new_ids):
                    session.add(
                        _DBTemplateEntity(
                            template_id=template_id,
                            artifact_id=entity_id,
                            deploy_order=idx,
                            required=True,
                        )
                    )

            template.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(template)

            logger.info("Updated project template %r", template.name)
            return _template_to_dto(template, include_entities=True)
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
        template_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a project template and all its entity associations.

        Entity associations are removed via the ``all, delete-orphan``
        cascade defined on the ORM relationship.

        Args:
            template_id: Template hex-UUID identifier.
            ctx: Unused; accepted for interface compatibility.

        Raises:
            KeyError: If no template with *template_id* exists.
        """
        session = self._get_session()
        try:
            template = (
                session.query(_DBProjectTemplate)
                .filter(_DBProjectTemplate.id == template_id)
                .first()
            )
            if template is None:
                raise KeyError(f"No project template with id={template_id!r}")

            session.delete(template)
            session.commit()
            logger.info("Deleted project template id=%r", template_id)
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
        template_id: str,
        project_path: str,
        options: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> dict[str, Any]:
        """Deploy all template entities to a target project directory.

        Delegates to :func:`~skillmeat.core.services.template_service.deploy_template_async`
        which performs variable substitution and writes each entity's content
        to the path resolved from ``path_pattern`` relative to *project_path*.

        Args:
            template_id: Template hex-UUID identifier.
            project_path: Absolute filesystem path to the target project
                directory.
            options: Optional deployment options mapping. Recognised keys:
                - ``variables`` (``dict[str, str]``): substitution variables.
                - ``selected_entity_ids`` (``list[str]``): subset of entities
                  to deploy (default: all).
                - ``overwrite`` (``bool``): overwrite existing files
                  (default ``False``).
                - ``deployment_profile_id`` (``str``): profile to use.
            ctx: Unused; accepted for interface compatibility.

        Returns:
            Result mapping with keys ``success`` (bool),
            ``deployed_files`` (list[str]), ``skipped_files`` (list[str]),
            ``message`` (str), and ``project_path`` (str).

        Raises:
            KeyError: If *template_id* does not exist.
            ValueError: If *project_path* does not exist or is invalid.
            NotImplementedError: If the template service module cannot be
                imported.
        """
        try:
            from skillmeat.core.services.template_service import (
                deploy_template_async,
            )
        except ImportError as exc:  # pragma: no cover
            raise NotImplementedError(
                "deploy() requires skillmeat.core.services.template_service"
            ) from exc

        opts = options or {}
        variables: dict[str, str] = opts.get("variables") or {}
        selected_entity_ids: list[str] | None = opts.get("selected_entity_ids")
        overwrite: bool = bool(opts.get("overwrite", False))
        deployment_profile_id: str | None = opts.get("deployment_profile_id")

        # Verify the template exists before delegating to the service.
        session = self._get_session()
        try:
            row = (
                session.query(_DBProjectTemplate)
                .filter(_DBProjectTemplate.id == template_id)
                .first()
            )
            if row is None:
                raise KeyError(f"No project template with id={template_id!r}")
        finally:
            session.close()

        # Run the async deployment coroutine.  When called from a sync
        # context (e.g. CLI tests) ``asyncio.run`` handles the event loop.
        # Callers already inside an async context should call the service
        # directly instead of going through this repository method.
        deploy_session = self._get_session()
        try:
            result = asyncio.run(
                deploy_template_async(
                    session=deploy_session,
                    template_id=template_id,
                    project_path=project_path,
                    variables=variables,
                    selected_entity_ids=selected_entity_ids,
                    overwrite=overwrite,
                    deployment_profile_id=deployment_profile_id,
                )
            )
        finally:
            deploy_session.close()

        return {
            "success": result.success,
            "project_path": result.project_path,
            "deployed_files": result.deployed_files,
            "skipped_files": result.skipped_files,
            "message": result.message,
        }
