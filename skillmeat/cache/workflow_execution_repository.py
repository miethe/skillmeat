"""Repository for WorkflowExecution and ExecutionStep persistence.

Provides CRUD operations, cursor-based pagination, and convenience query
methods for workflow execution records.  The repository is designed for
session-injection use — callers supply an active SQLAlchemy ``Session``
(e.g. via FastAPI dependency injection) rather than having the repository
manage its own connection.

Usage::

    from skillmeat.cache.models import get_session
    from skillmeat.cache.workflow_execution_repository import (
        WorkflowExecutionRepository,
    )

    session = get_session()
    try:
        repo = WorkflowExecutionRepository(session)
        execution = repo.get_with_steps("abc123")
    finally:
        session.close()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from skillmeat.cache.models import WorkflowExecution
from skillmeat.cache.repositories import ConstraintError, RepositoryError

logger = logging.getLogger(__name__)

# Statuses that represent an in-flight execution.
_ACTIVE_STATUSES: Tuple[str, ...] = ("pending", "running", "paused")


class WorkflowExecutionRepository:
    """Data-access layer for :class:`~skillmeat.cache.models.WorkflowExecution`.

    All methods operate on the injected ``session``; the caller is responsible
    for committing or rolling back transactions and for closing the session.

    Args:
        session: Active SQLAlchemy ORM session.

    Example::

        repo = WorkflowExecutionRepository(session)

        # Create
        execution = WorkflowExecution(workflow_id="wf1", ...)
        saved = repo.create(execution)

        # Paginate
        items, next_cursor = repo.list(workflow_id="wf1", limit=20)
        if next_cursor:
            page2, _ = repo.list(workflow_id="wf1", cursor=next_cursor, limit=20)
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Persist a new ``WorkflowExecution`` row.

        Args:
            execution: Unsaved ``WorkflowExecution`` instance to insert.

        Returns:
            The same instance, now attached to the session (primary key
            populated after flush).

        Raises:
            ConstraintError: If a unique/foreign-key constraint is violated.
            RepositoryError: On any other database error.
        """
        try:
            self.session.add(execution)
            self.session.flush()
            logger.debug(
                "Created WorkflowExecution id=%r workflow_id=%r status=%r",
                execution.id,
                execution.workflow_id,
                execution.status,
            )
            return execution
        except IntegrityError as exc:
            self.session.rollback()
            raise ConstraintError(
                f"Failed to create WorkflowExecution (constraint violation): {exc}"
            ) from exc
        except Exception as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Failed to create WorkflowExecution: {exc}"
            ) from exc

    def get(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Return a ``WorkflowExecution`` by primary key, or ``None``.

        Steps are *not* eagerly loaded.  Use :meth:`get_with_steps` when
        step data is required.

        Args:
            execution_id: Primary key of the execution row.

        Returns:
            ``WorkflowExecution`` instance or ``None`` if not found.
        """
        return (
            self.session.query(WorkflowExecution)
            .filter(WorkflowExecution.id == execution_id)
            .first()
        )

    def get_with_steps(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Return a ``WorkflowExecution`` with its ``steps`` eagerly loaded.

        This issues a single JOIN query rather than a lazy-load N+1.

        Args:
            execution_id: Primary key of the execution row.

        Returns:
            ``WorkflowExecution`` instance (with ``steps`` populated) or
            ``None`` if not found.
        """
        return (
            self.session.query(WorkflowExecution)
            .options(joinedload(WorkflowExecution.steps))
            .filter(WorkflowExecution.id == execution_id)
            .first()
        )

    def update(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Flush pending changes on a managed ``WorkflowExecution`` instance.

        The instance must already be attached to this session (i.e. retrieved
        via this repository or explicitly added).  Calling this method flushes
        dirty state to the DB within the current transaction.

        Args:
            execution: Modified ``WorkflowExecution`` instance.

        Returns:
            The same instance after flushing.

        Raises:
            ConstraintError: If a constraint is violated during the flush.
            RepositoryError: On any other database error.
        """
        try:
            self.session.flush()
            logger.debug(
                "Updated WorkflowExecution id=%r status=%r",
                execution.id,
                execution.status,
            )
            return execution
        except IntegrityError as exc:
            self.session.rollback()
            raise ConstraintError(
                f"Failed to update WorkflowExecution (constraint violation): {exc}"
            ) from exc
        except Exception as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Failed to update WorkflowExecution: {exc}"
            ) from exc

    def delete(self, execution_id: str) -> bool:
        """Delete a ``WorkflowExecution`` row by primary key.

        Associated ``ExecutionStep`` rows are removed via the
        ``cascade="all, delete-orphan"`` relationship defined on the model.

        Args:
            execution_id: Primary key of the execution to remove.

        Returns:
            ``True`` if a row was deleted, ``False`` if not found.

        Raises:
            RepositoryError: On any database error during the delete flush.
        """
        execution = self.get(execution_id)
        if execution is None:
            logger.debug(
                "delete: WorkflowExecution id=%r not found", execution_id
            )
            return False

        try:
            self.session.delete(execution)
            self.session.flush()
            logger.debug("Deleted WorkflowExecution id=%r", execution_id)
            return True
        except Exception as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Failed to delete WorkflowExecution {execution_id!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        started_after: Optional[datetime] = None,
        started_before: Optional[datetime] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[WorkflowExecution], Optional[str]]:
        """Return a page of ``WorkflowExecution`` records.

        Results are ordered ``started_at DESC, id ASC`` (most-recent first;
        ``id`` breaks ties for rows with the same ``started_at``).

        Cursor-based pagination is keyed on ``id``.  Pass the cursor returned
        from a previous call as *cursor* to retrieve the next page.

        Args:
            workflow_id: If given, restrict results to this workflow.
            status: If given, restrict results to this status value.
            started_after: If given, include only executions whose
                ``started_at`` is strictly after this timestamp.
            started_before: If given, include only executions whose
                ``started_at`` is strictly before this timestamp.
            cursor: Opaque cursor from a previous :meth:`list` call.
                ``None`` fetches the first page.
            limit: Maximum number of items to return (default ``50``).

        Returns:
            A 2-tuple of ``(items, next_cursor)`` where *next_cursor* is
            ``None`` when there are no further pages.

        Example::

            items, cursor = repo.list(workflow_id="wf1", limit=20)
            while cursor:
                items, cursor = repo.list(
                    workflow_id="wf1", cursor=cursor, limit=20
                )
        """
        query = self.session.query(WorkflowExecution)

        # --- filter ---
        if workflow_id is not None:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        if status is not None:
            query = query.filter(WorkflowExecution.status == status)
        if started_after is not None:
            query = query.filter(WorkflowExecution.started_at > started_after)
        if started_before is not None:
            query = query.filter(WorkflowExecution.started_at < started_before)

        # --- cursor ---
        # The cursor encodes the `id` of the last item on the previous page.
        # Because we order DESC by started_at, ASC by id, keying purely on id
        # is sufficient for stable pagination (ids are UUIDs, not timestamps).
        if cursor is not None:
            query = query.filter(WorkflowExecution.id > cursor)

        # --- order ---
        query = query.order_by(
            WorkflowExecution.started_at.desc(),
            WorkflowExecution.id.asc(),
        )

        # Fetch limit + 1 to detect whether a next page exists.
        rows = query.limit(limit + 1).all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        next_cursor: Optional[str] = rows[-1].id if rows and has_more else None

        logger.debug(
            "list WorkflowExecutions workflow_id=%r status=%r "
            "cursor=%r limit=%d → count=%d has_more=%s",
            workflow_id,
            status,
            cursor,
            limit,
            len(rows),
            has_more,
        )
        return rows, next_cursor

    def list_active(self) -> List[WorkflowExecution]:
        """Return all executions currently in an active state.

        Active statuses are ``'pending'``, ``'running'``, and ``'paused'``.

        Returns:
            List of ``WorkflowExecution`` instances in active states, ordered
            ``started_at ASC`` (oldest first, useful for scheduling purposes).
        """
        rows = (
            self.session.query(WorkflowExecution)
            .filter(WorkflowExecution.status.in_(_ACTIVE_STATUSES))
            .order_by(WorkflowExecution.started_at.asc())
            .all()
        )
        logger.debug("list_active returned %d executions", len(rows))
        return rows

    def get_latest_for_workflow(
        self, workflow_id: str
    ) -> Optional[WorkflowExecution]:
        """Return the most-recent execution for a workflow.

        "Most recent" is determined by ``started_at DESC``.  Executions with
        a ``NULL`` ``started_at`` (i.e. still in ``'pending'`` state and not
        yet started) sort after all timestamped rows.

        Args:
            workflow_id: Workflow to query.

        Returns:
            The latest ``WorkflowExecution`` or ``None`` if the workflow has
            no execution history.
        """
        return (
            self.session.query(WorkflowExecution)
            .filter(WorkflowExecution.workflow_id == workflow_id)
            .order_by(WorkflowExecution.started_at.desc())
            .first()
        )

    def count(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Return the total number of executions matching the given filters.

        Args:
            workflow_id: If given, count only executions for this workflow.
            status: If given, count only executions with this status.

        Returns:
            Integer count of matching rows.
        """
        query = self.session.query(WorkflowExecution)
        if workflow_id is not None:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        if status is not None:
            query = query.filter(WorkflowExecution.status == status)
        total: int = query.count()
        return total

    def update_status(
        self,
        execution_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> Optional[WorkflowExecution]:
        """Convenience method for status-transition updates.

        Fetches the execution, applies the provided fields, and flushes.
        Returns ``None`` if the execution does not exist.

        Args:
            execution_id: Primary key of the execution to update.
            status: New status value (e.g. ``'running'``, ``'completed'``,
                ``'failed'``).
            started_at: If provided, set ``started_at`` on the execution.
            completed_at: If provided, set ``completed_at`` on the execution.
            error_message: If provided, set ``error_message`` on the
                execution.  Pass an empty string to clear a previous error.

        Returns:
            Updated ``WorkflowExecution`` instance, or ``None`` if not found.
        """
        execution = self.get(execution_id)
        if execution is None:
            logger.warning(
                "update_status: WorkflowExecution id=%r not found",
                execution_id,
            )
            return None

        execution.status = status
        if started_at is not None:
            execution.started_at = started_at
        if completed_at is not None:
            execution.completed_at = completed_at
        if error_message is not None:
            execution.error_message = error_message

        self.session.flush()
        logger.debug(
            "update_status WorkflowExecution id=%r → status=%r",
            execution_id,
            status,
        )
        return execution

    def save(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Flush pending changes for this object without committing.

        Intended for use when the caller controls the transaction boundary
        (e.g. inside a
        :class:`~skillmeat.cache.workflow_transaction.WorkflowTransactionManager`
        context or a FastAPI dependency-injected session).

        Flushes only the provided instance so that any auto-generated values
        are reflected before the caller continues.

        Args:
            execution: A tracked :class:`WorkflowExecution` instance with
                unsaved mutations.

        Returns:
            The same instance after the flush and refresh.

        Raises:
            ConstraintError: If a constraint is violated during the flush.
            RepositoryError: On any other database error.

        Example::

            exec = repo.get("exec-abc")
            exec.status = "running"
            repo.save(exec)
            # ... more repository work in the same transaction ...
            session.commit()
        """
        try:
            self.session.flush([execution])
            self.session.refresh(execution)
            return execution
        except IntegrityError as exc:
            self.session.rollback()
            raise ConstraintError(
                f"Failed to save WorkflowExecution (constraint violation): {exc}"
            ) from exc
        except Exception as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Failed to save WorkflowExecution: {exc}"
            ) from exc
