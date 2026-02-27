"""Transaction helpers for cross-repository atomic workflow operations.

This module provides :class:`WorkflowTransactionManager`, a helper that
coordinates atomic operations spanning multiple session-injected repositories
(:class:`~skillmeat.cache.workflow_execution_repository.WorkflowExecutionRepository`
and :class:`~skillmeat.cache.execution_step_repository.ExecutionStepRepository`).

Design contract
---------------
- The caller (service layer) owns the ``Session`` and decides when to commit.
- All helpers here operate within an existing session — they flush but never
  commit, so the caller retains full transaction control.
- :meth:`WorkflowTransactionManager.begin_transaction` is a context manager
  that catches any exception, issues a rollback, and re-raises.  Use it to
  wrap multi-step operations where a partial failure must be fully unwound.
- The two ``atomic_*`` methods compose repository operations in a single
  logical unit.  They call :meth:`begin_transaction` internally, so callers
  do not need to wrap them again.

Usage::

    from skillmeat.cache.models import get_session
    from skillmeat.cache.workflow_execution_repository import (
        WorkflowExecutionRepository,
    )
    from skillmeat.cache.execution_step_repository import ExecutionStepRepository
    from skillmeat.cache.workflow_transaction import WorkflowTransactionManager

    session = get_session()
    try:
        execution_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        tx = WorkflowTransactionManager(session)

        # Atomically transition execution + steps
        updated = tx.atomic_execution_state_change(
            execution_repo=execution_repo,
            step_repo=step_repo,
            execution_id="exec-abc",
            new_execution_status="completed",
            completed_at=datetime.utcnow(),
            step_id_to_status={"step-1": "completed", "step-2": "completed"},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import ExecutionStep, WorkflowExecution

if TYPE_CHECKING:
    from skillmeat.cache.execution_step_repository import ExecutionStepRepository
    from skillmeat.cache.workflow_execution_repository import (
        WorkflowExecutionRepository,
    )

logger = logging.getLogger(__name__)


class WorkflowTransactionManager:
    """Cross-repository transaction helper for workflow execution state.

    Provides atomic operations that span
    :class:`~skillmeat.cache.workflow_execution_repository.WorkflowExecutionRepository`
    and
    :class:`~skillmeat.cache.execution_step_repository.ExecutionStepRepository`.

    The manager holds a reference to the injected ``Session`` and uses it for
    rollback on failure.  All operations flush but do **not** commit — the
    caller decides the transaction boundary.

    Args:
        session: An active SQLAlchemy session shared with the repositories
            that will be used in the atomic operations.

    Example::

        tx = WorkflowTransactionManager(session)

        # Guard a multi-step block
        with tx.begin_transaction():
            execution_repo.create(execution)
            step_repo.create_bulk(steps)

        # Or use the higher-level helpers directly
        tx.atomic_execution_state_change(
            execution_repo, step_repo,
            execution_id="abc",
            new_execution_status="failed",
            error_message="Timeout",
        )
    """

    def __init__(self, session: Session) -> None:
        """Initialise with an injected session.

        Args:
            session: Active SQLAlchemy session.  Must be the same session
                used by the repositories passed to the atomic methods.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    @contextmanager
    def begin_transaction(self) -> Generator[None, None, None]:
        """Context manager that rolls back on any exception and re-raises.

        Wraps a block of repository operations so that any failure triggers
        an immediate ``session.rollback()`` before propagating the exception.
        The caller is still responsible for calling ``session.commit()`` on
        success (after the ``with`` block exits normally).

        Yields:
            Nothing — the body of the ``with`` block runs within the guard.

        Raises:
            Exception: Any exception raised inside the block is re-raised
                after the rollback.

        Example::

            with tx.begin_transaction():
                execution_repo.create(execution)
                step_repo.create_bulk(steps)
            session.commit()  # caller commits
        """
        try:
            yield
        except Exception:
            logger.debug(
                "WorkflowTransactionManager: exception caught, rolling back session"
            )
            self.session.rollback()
            raise

    # ------------------------------------------------------------------
    # Atomic helpers
    # ------------------------------------------------------------------

    def atomic_execution_state_change(
        self,
        execution_repo: WorkflowExecutionRepository,
        step_repo: ExecutionStepRepository,
        execution_id: str,
        new_execution_status: str,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        step_id_to_status: Optional[Dict[str, str]] = None,
    ) -> WorkflowExecution:
        """Atomically update an execution's status and its associated steps.

        Updates the :class:`~skillmeat.cache.models.WorkflowExecution` row
        and — when *step_id_to_status* is provided — each referenced
        :class:`~skillmeat.cache.models.ExecutionStep` row in a single
        logical unit.  If any part fails the entire operation is rolled back.

        The method flushes but does **not** commit.  The caller must call
        ``session.commit()`` after a successful return.

        Args:
            execution_repo: Repository used to update the execution row.
            step_repo: Repository used to update the step rows.
            execution_id: Primary key of the
                :class:`~skillmeat.cache.models.WorkflowExecution` to update.
            new_execution_status: Status string to set on the execution
                (e.g. ``"completed"``, ``"failed"``).
            completed_at: Optional UTC datetime to set ``completed_at`` on
                the execution.
            error_message: Optional error detail to attach to the execution.
            step_id_to_status: Optional mapping of
                ``{step_id: new_status}`` pairs.  Each step is updated
                individually via
                :meth:`~skillmeat.cache.execution_step_repository.ExecutionStepRepository.update_status`.
                Steps that are not found are logged as a warning and skipped.

        Returns:
            The updated :class:`~skillmeat.cache.models.WorkflowExecution`
            instance (flushed but not yet committed).

        Raises:
            ValueError: If *execution_id* does not match any execution row.
            Exception: Any database error causes a full rollback before the
                exception is re-raised.

        Example::

            updated = tx.atomic_execution_state_change(
                execution_repo=execution_repo,
                step_repo=step_repo,
                execution_id="exec-abc",
                new_execution_status="completed",
                completed_at=datetime.utcnow(),
                step_id_to_status={"step-1": "completed", "step-2": "skipped"},
            )
            session.commit()
        """
        with self.begin_transaction():
            # 1. Update execution status
            execution = execution_repo.update_status(
                execution_id=execution_id,
                status=new_execution_status,
                completed_at=completed_at,
                error_message=error_message,
            )
            if execution is None:
                raise ValueError(
                    f"WorkflowExecution id={execution_id!r} not found; "
                    "cannot apply atomic state change"
                )

            # 2. Update each step status
            if step_id_to_status:
                for step_id, new_status in step_id_to_status.items():
                    updated_step = step_repo.update_status(
                        step_id=step_id,
                        status=new_status,
                    )
                    if updated_step is None:
                        logger.warning(
                            "atomic_execution_state_change: ExecutionStep id=%r "
                            "not found; skipping status update to %r",
                            step_id,
                            new_status,
                        )

            logger.debug(
                "atomic_execution_state_change: execution id=%r → status=%r "
                "step_count=%d",
                execution_id,
                new_execution_status,
                len(step_id_to_status) if step_id_to_status else 0,
            )
            return execution

    def atomic_create_execution(
        self,
        execution_repo: WorkflowExecutionRepository,
        step_repo: ExecutionStepRepository,
        execution: WorkflowExecution,
        steps: List[ExecutionStep],
    ) -> WorkflowExecution:
        """Atomically create an execution and all of its initial steps.

        Persists the :class:`~skillmeat.cache.models.WorkflowExecution` row
        first, then bulk-creates all associated
        :class:`~skillmeat.cache.models.ExecutionStep` rows in the same
        logical unit.  If any part fails the entire operation is rolled back.

        The method flushes but does **not** commit.  The caller must call
        ``session.commit()`` after a successful return.

        Args:
            execution_repo: Repository used to persist the execution row.
            step_repo: Repository used to bulk-persist the step rows.
            execution: Unsaved :class:`~skillmeat.cache.models.WorkflowExecution`
                instance.  The ``execution_id`` on each step must match
                ``execution.id`` (set it before calling, or let the flush
                populate it automatically via the ORM relationship).
            steps: List of unsaved :class:`~skillmeat.cache.models.ExecutionStep`
                instances to create alongside the execution.  May be empty.

        Returns:
            The persisted :class:`~skillmeat.cache.models.WorkflowExecution`
            instance (flushed but not yet committed).

        Raises:
            Exception: Any database error causes a full rollback before the
                exception is re-raised.

        Example::

            execution = WorkflowExecution(workflow_id="wf-1", status="pending")
            steps = [
                ExecutionStep(stage_name="Fetch", status="pending"),
                ExecutionStep(stage_name="Transform", status="pending"),
            ]
            created = tx.atomic_create_execution(
                execution_repo, step_repo, execution, steps
            )
            session.commit()
        """
        with self.begin_transaction():
            # 1. Persist the execution (flush → id is populated)
            created_execution = execution_repo.create(execution)

            # 2. Bulk-create all steps
            if steps:
                step_repo.create_bulk(steps)

            logger.debug(
                "atomic_create_execution: created execution id=%r with %d step(s)",
                created_execution.id,
                len(steps),
            )
            return created_execution
