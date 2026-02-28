"""Repository for Workflow, WorkflowStage, and WorkflowExecution entities.

Follows the BaseRepository pattern established in repositories.py:
- Session-per-operation (create new session, close in finally)
- IntegrityError → ConstraintError, generic exceptions → RepositoryError
- Cursor pagination: order by created_at DESC, id ASC; next_cursor = last id
- JSON tag filtering via SQLite LIKE '%"tag"%' pattern
- Text search via LIKE '%query%' on name OR description (case-insensitive)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from skillmeat.cache.models import (
    Workflow,
    WorkflowStage,
    create_db_engine,
    create_tables,
)
from skillmeat.cache.repositories import (
    BaseRepository,
    ConstraintError,
    RepositoryError,
)

logger = logging.getLogger(__name__)


class WorkflowRepository(BaseRepository[Workflow]):
    """Repository for Workflow CRUD and list operations.

    Provides data-access operations for ``Workflow`` and its related
    ``WorkflowStage`` records.  All mutating operations open a fresh session,
    commit on success, and close the session in a ``finally`` block — matching
    the session-per-operation convention used throughout repositories.py.

    Cursor pagination is based on ``(created_at DESC, id ASC)``.  The cursor
    token is the opaque ``id`` of the last item in the previous page.

    Tag filtering uses SQLite ``LIKE '%"tag"%'`` against ``tags_json`` (a JSON
    text column storing a JSON array).  This avoids a JSON function dependency
    and is consistent with other JSON tag columns in the codebase.

    Usage:
        >>> repo = WorkflowRepository()
        >>> wf = Workflow(name="My Workflow", definition_yaml="...", status="draft")
        >>> created = repo.create(wf)
        >>> fetched = repo.get(created.id)
        >>> results, next_cursor = repo.list(status="draft", limit=10)
        >>> repo.delete(created.id)
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialise repository.

        Args:
            db_path: Optional path to SQLite database file. Uses the default
                ``~/.skillmeat/cache/cache.db`` when ``None``.
        """
        super().__init__(db_path, Workflow)

    # =========================================================================
    # CRUD
    # =========================================================================

    def create(self, workflow: Workflow) -> Workflow:
        """Persist a new Workflow record.

        The caller is responsible for setting all required fields on the
        ``Workflow`` instance before passing it in.  If the instance has no
        ``id``, one is generated automatically.

        Args:
            workflow: Unsaved ``Workflow`` ORM instance.

        Returns:
            The same instance after the database insert and refresh.

        Raises:
            ConstraintError: If a unique constraint is violated (e.g. duplicate
                primary key).
            RepositoryError: On any other database error.

        Example:
            >>> wf = Workflow(name="Deploy Pipeline", definition_yaml="...", status="draft")
            >>> created = repo.create(wf)
            >>> print(created.id)
        """
        if not workflow.id:
            workflow.id = uuid.uuid4().hex

        now = datetime.utcnow()
        if workflow.created_at is None:
            workflow.created_at = now
        if workflow.updated_at is None:
            workflow.updated_at = now

        session = self._get_session()
        try:
            session.add(workflow)
            session.commit()
            session.refresh(workflow)
            logger.info(
                "Created workflow id=%s name=%r status=%s",
                workflow.id,
                workflow.name,
                workflow.status,
            )
            return workflow
        except IntegrityError as exc:
            session.rollback()
            raise ConstraintError(
                f"Failed to create workflow (constraint violation): {exc}"
            ) from exc
        except Exception as exc:
            session.rollback()
            raise RepositoryError(f"Failed to create workflow: {exc}") from exc
        finally:
            session.close()

    def get(self, workflow_id: str) -> Optional[Workflow]:
        """Retrieve a Workflow by primary key.

        Stages are loaded lazily (``selectin`` on the relationship) unless the
        caller uses :meth:`get_with_stages`.

        Args:
            workflow_id: Primary key of the workflow.

        Returns:
            ``Workflow`` instance or ``None`` if not found.
        """
        session = self._get_session()
        try:
            return (
                session.query(Workflow)
                .filter(Workflow.id == workflow_id)
                .first()
            )
        finally:
            session.close()

    def get_with_stages(self, workflow_id: str) -> Optional[Workflow]:
        """Retrieve a Workflow with its stages eagerly loaded.

        Uses ``joinedload`` to ensure stage records are included in a single
        SQL query, avoiding the ``selectin`` lazy-load behaviour.

        Args:
            workflow_id: Primary key of the workflow.

        Returns:
            ``Workflow`` instance (with populated ``stages`` list) or ``None``.
        """
        session = self._get_session()
        try:
            return (
                session.query(Workflow)
                .options(joinedload(Workflow.stages))
                .filter(Workflow.id == workflow_id)
                .first()
            )
        finally:
            session.close()

    def update(self, workflow: Workflow) -> Workflow:
        """Merge an updated Workflow back to the database.

        The caller should mutate the fields they want to change directly on the
        ``Workflow`` instance, then pass it to this method.  ``updated_at`` is
        refreshed automatically.

        Args:
            workflow: ``Workflow`` instance with updated field values.

        Returns:
            The refreshed instance after the merge and commit.

        Raises:
            RepositoryError: If the merge or commit fails.

        Example:
            >>> wf = repo.get("abc123")
            >>> wf.status = "active"
            >>> updated = repo.update(wf)
        """
        workflow.updated_at = datetime.utcnow()

        session = self._get_session()
        try:
            merged = session.merge(workflow)
            session.commit()
            session.refresh(merged)
            logger.info(
                "Updated workflow id=%s name=%r status=%s",
                merged.id,
                merged.name,
                merged.status,
            )
            return merged
        except IntegrityError as exc:
            session.rollback()
            raise ConstraintError(
                f"Failed to update workflow (constraint violation): {exc}"
            ) from exc
        except Exception as exc:
            session.rollback()
            raise RepositoryError(f"Failed to update workflow: {exc}") from exc
        finally:
            session.close()

    def delete(self, workflow_id: str) -> bool:
        """Delete a Workflow by primary key.

        The ``workflows`` → ``workflow_stages`` relationship is defined with
        ``cascade="all, delete-orphan"``, so associated ``WorkflowStage`` rows
        are removed automatically.

        Args:
            workflow_id: Primary key of the workflow to delete.

        Returns:
            ``True`` if a row was deleted, ``False`` if no matching row existed.

        Raises:
            RepositoryError: On database error.

        Example:
            >>> deleted = repo.delete("abc123")
            >>> print("Gone" if deleted else "Not found")
        """
        session = self._get_session()
        try:
            workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow is None:
                logger.debug("delete: workflow id=%s not found", workflow_id)
                return False
            session.delete(workflow)
            session.commit()
            logger.info("Deleted workflow id=%s", workflow_id)
            return True
        except Exception as exc:
            session.rollback()
            raise RepositoryError(f"Failed to delete workflow {workflow_id}: {exc}") from exc
        finally:
            session.close()

    # =========================================================================
    # Query helpers
    # =========================================================================

    def find_by_name(self, name: str) -> Optional[Workflow]:
        """Find a workflow by exact name match.

        Names are not enforced as unique at the DB level, so this returns the
        first match ordered by ``created_at DESC``.

        Args:
            name: Exact workflow name to search for.

        Returns:
            First matching ``Workflow`` or ``None``.
        """
        session = self._get_session()
        try:
            return (
                session.query(Workflow)
                .filter(Workflow.name == name)
                .order_by(Workflow.created_at.desc())
                .first()
            )
        finally:
            session.close()

    def list(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Workflow], Optional[str]]:
        """Return a filtered, cursor-paginated list of workflows.

        Ordering: ``created_at DESC, id ASC`` (stable for cursor pagination).
        The cursor token is the ``id`` of the last item in the previous page.

        Tag filtering applies AND semantics — a workflow must contain every tag
        in the provided list.  Each tag is matched via SQLite
        ``LIKE '%"tag"%'`` against ``tags_json``.

        Text search matches workflows where ``name`` or ``description``
        contains the search string (case-insensitive ``LIKE``).

        Args:
            status: Optional status value to filter by (exact match).
            tags: Optional list of tag strings.  All must match (AND).
            search: Optional substring to search in ``name`` and ``description``.
            cursor: Opaque cursor token (``id`` of the last seen workflow).
                When provided, returns only workflows that come *after* the
                cursor in the stable ordering.
            limit: Maximum number of results to return (default 50).

        Returns:
            A tuple ``(results, next_cursor)`` where ``next_cursor`` is a
            string token to pass in the next request, or ``None`` when the
            current page is the last one.

        Example:
            >>> results, next_cur = repo.list(status="active", limit=10)
            >>> if next_cur:
            ...     page2, _ = repo.list(status="active", cursor=next_cur, limit=10)
        """
        session = self._get_session()
        try:
            q = session.query(Workflow)

            # Status filter
            if status is not None:
                q = q.filter(Workflow.status == status)

            # Tag filters — AND semantics, one LIKE per tag
            if tags:
                for tag in tags:
                    # Escape any % or _ in the tag to avoid wildcard collisions
                    escaped = tag.replace("%", r"\%").replace("_", r"\_")
                    # Match the exact JSON string value: "tag"
                    q = q.filter(
                        Workflow.tags_json.like(f'%"{escaped}"%')
                    )

            # Text search — OR across name and description
            if search is not None:
                pattern = f"%{search}%"
                q = q.filter(
                    or_(
                        Workflow.name.ilike(pattern),
                        Workflow.description.ilike(pattern),
                    )
                )

            # Cursor pagination: resolve the anchor row's (created_at, id) pair
            if cursor is not None:
                anchor = (
                    session.query(Workflow.created_at, Workflow.id)
                    .filter(Workflow.id == cursor)
                    .first()
                )
                if anchor is not None:
                    anchor_created_at, anchor_id = anchor
                    # Items strictly after cursor in (created_at DESC, id ASC) order:
                    # Either created_at < anchor, or same created_at with id > anchor
                    q = q.filter(
                        or_(
                            Workflow.created_at < anchor_created_at,
                            and_(
                                Workflow.created_at == anchor_created_at,
                                Workflow.id > anchor_id,
                            ),
                        )
                    )

            results: List[Workflow] = (
                q.order_by(Workflow.created_at.desc(), Workflow.id.asc())
                .limit(limit)
                .all()
            )

            next_cursor: Optional[str] = (
                results[-1].id if len(results) == limit else None
            )

            return results, next_cursor

        finally:
            session.close()

    def count(self, status: Optional[str] = None) -> int:
        """Count workflows, optionally filtered by status.

        Args:
            status: Optional status value to filter by (exact match).

        Returns:
            Integer count of matching workflows.

        Example:
            >>> total = repo.count()
            >>> active = repo.count(status="active")
        """
        session = self._get_session()
        try:
            q = session.query(func.count(Workflow.id))
            if status is not None:
                q = q.filter(Workflow.status == status)
            return q.scalar() or 0
        finally:
            session.close()

    def exists(self, workflow_id: str) -> bool:
        """Check whether a Workflow with the given ID exists.

        Uses a lightweight ``COUNT`` query rather than loading the full row.

        Args:
            workflow_id: Primary key to check.

        Returns:
            ``True`` if a matching row exists, ``False`` otherwise.
        """
        session = self._get_session()
        try:
            count = (
                session.query(func.count(Workflow.id))
                .filter(Workflow.id == workflow_id)
                .scalar()
                or 0
            )
            return count > 0
        finally:
            session.close()

    def save(self, workflow: Workflow) -> Workflow:
        """Persist an updated Workflow, committing the change immediately.

        ``WorkflowRepository`` uses the session-per-operation convention (each
        mutating method opens, commits, and closes its own session), so this
        method is a semantic alias for :meth:`update` rather than a bare flush.
        The commit is performed internally — the caller does **not** need to
        commit separately.

        This matches the interface of the ``save()`` methods on the
        session-injected sibling repositories
        (:class:`~skillmeat.cache.workflow_execution_repository.WorkflowExecutionRepository`
        and
        :class:`~skillmeat.cache.execution_step_repository.ExecutionStepRepository`),
        providing a uniform surface for service-layer code that works across
        repository types.

        Args:
            workflow: A :class:`Workflow` instance with updated field values.

        Returns:
            The refreshed instance after the merge and commit.

        Raises:
            ConstraintError: If a unique constraint is violated.
            RepositoryError: On any other database error.

        Example::

            wf = repo.get("abc123")
            wf.status = "active"
            updated = repo.save(wf)
        """
        return self.update(workflow)
