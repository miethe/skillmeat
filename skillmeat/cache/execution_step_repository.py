"""Repository CRUD and status-update operations for ExecutionStep.

This module provides ``ExecutionStepRepository``, the data-access layer for
``execution_steps`` rows.  It is session-injected (the caller provides a
live ``Session``), which makes it easy to compose with other repositories
inside a single transaction.

Design notes
------------
- The constructor accepts an ``sqlalchemy.orm.Session`` directly — the caller
  manages session lifecycle.  This mirrors the pattern used by the FastAPI
  dependency-injection layer (``get_session()``).
- All public methods raise ``NotFoundError`` (from ``repositories.py``) when a
  requested row is absent and a concrete object is required.
- ``append_log`` reads the current ``logs_json`` column, parses it as a JSON
  array, appends the new entry, and writes back.  SQLite does not support
  native JSON-array append so this round-trip is intentional.
- ``count_by_status`` returns a complete dict even for statuses with zero
  rows so callers can always do ``counts["completed"]`` without a KeyError.

Usage
-----
>>> from sqlalchemy.orm import Session
>>> from skillmeat.cache.execution_step_repository import ExecutionStepRepository
>>> from skillmeat.cache.models import ExecutionStep
>>>
>>> # Inside a FastAPI route / service that already has a session
>>> def do_something(session: Session) -> None:
...     repo = ExecutionStepRepository(session)
...     step = repo.get("some-step-id")
...     repo.update_status(step.id, "running", started_at=datetime.utcnow())
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from skillmeat.cache.models import ExecutionStep
from skillmeat.cache.repositories import ConstraintError, NotFoundError

logger = logging.getLogger(__name__)


class ExecutionStepRepository:
    """Data-access layer for :class:`~skillmeat.cache.models.ExecutionStep` rows.

    All mutating operations raise :class:`~skillmeat.cache.repositories.ConstraintError`
    when an ``IntegrityError`` is detected and
    :class:`~skillmeat.cache.repositories.NotFoundError` when a lookup by ID
    fails and a result is required.

    Attributes:
        session: The active SQLAlchemy session provided by the caller.

    Example:
        >>> repo = ExecutionStepRepository(session)
        >>> step = ExecutionStep(execution_id="exec-1", stage_id_ref="stage-a",
        ...                      stage_name="Fetch", status="pending")
        >>> created = repo.create(step)
        >>> repo.update_status(created.id, "running", started_at=datetime.utcnow())
    """

    def __init__(self, session: Session) -> None:
        """Initialise the repository with an injected session.

        Args:
            session: An active SQLAlchemy session.  Lifecycle (commit/rollback/
                close) is managed by the caller.
        """
        self.session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, step: ExecutionStep) -> ExecutionStep:
        """Persist a new execution step and return the flushed instance.

        Args:
            step: An unsaved :class:`ExecutionStep` ORM instance.

        Returns:
            The same instance after ``session.flush()`` (ID is populated).

        Raises:
            ConstraintError: If a database constraint is violated (e.g.
                duplicate primary key or missing foreign key).
        """
        try:
            self.session.add(step)
            self.session.flush()
            logger.debug("Created ExecutionStep id=%s for execution=%s", step.id, step.execution_id)
            return step
        except IntegrityError as exc:
            self.session.rollback()
            logger.warning("Constraint violation creating ExecutionStep: %s", exc)
            raise ConstraintError(f"Database constraint violation: {exc}") from exc

    def create_bulk(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """Persist multiple execution steps in a single flush.

        This is the preferred way to initialise all steps for a new execution
        at once because it avoids per-row round-trips.

        Args:
            steps: A list of unsaved :class:`ExecutionStep` ORM instances.

        Returns:
            The same list after ``session.flush()`` (IDs are populated).

        Raises:
            ConstraintError: If any constraint is violated during the bulk
                insert.
        """
        if not steps:
            return []
        try:
            for step in steps:
                self.session.add(step)
            self.session.flush()
            logger.debug(
                "Bulk-created %d ExecutionStep(s) for execution=%s",
                len(steps),
                steps[0].execution_id if steps else "unknown",
            )
            return steps
        except IntegrityError as exc:
            self.session.rollback()
            logger.warning("Constraint violation bulk-creating ExecutionSteps: %s", exc)
            raise ConstraintError(f"Database constraint violation: {exc}") from exc

    def get(self, step_id: str) -> Optional[ExecutionStep]:
        """Fetch an execution step by primary key.

        Args:
            step_id: The UUID hex string of the step.

        Returns:
            The :class:`ExecutionStep` instance, or ``None`` if not found.
        """
        return self.session.get(ExecutionStep, step_id)

    def update(self, step: ExecutionStep) -> ExecutionStep:
        """Merge updated step state and flush.

        The caller modifies the ORM instance's attributes before calling this
        method.  ``updated_at`` is handled by the model's ``onupdate`` hook.

        Args:
            step: A tracked (or detached) :class:`ExecutionStep` instance.

        Returns:
            The merged instance.

        Raises:
            ConstraintError: If a constraint is violated.
        """
        try:
            merged = self.session.merge(step)
            self.session.flush()
            logger.debug("Updated ExecutionStep id=%s", merged.id)
            return merged
        except IntegrityError as exc:
            self.session.rollback()
            logger.warning("Constraint violation updating ExecutionStep id=%s: %s", step.id, exc)
            raise ConstraintError(f"Database constraint violation: {exc}") from exc

    def delete(self, step_id: str) -> bool:
        """Delete an execution step by primary key.

        Args:
            step_id: The UUID hex string of the step.

        Returns:
            ``True`` if a row was deleted, ``False`` if the ID was not found.
        """
        step = self.session.get(ExecutionStep, step_id)
        if step is None:
            logger.debug("ExecutionStep id=%s not found for deletion", step_id)
            return False
        self.session.delete(step)
        self.session.flush()
        logger.debug("Deleted ExecutionStep id=%s", step_id)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_by_execution(self, execution_id: str) -> List[ExecutionStep]:
        """Return all steps for an execution ordered by creation time.

        The result is bounded by the number of workflow stages (typically
        single digits to low dozens), so no pagination is needed.

        Args:
            execution_id: The parent ``WorkflowExecution.id``.

        Returns:
            List of :class:`ExecutionStep` instances ordered by
            ``created_at`` ascending.
        """
        return (
            self.session.query(ExecutionStep)
            .filter(ExecutionStep.execution_id == execution_id)
            .order_by(ExecutionStep.created_at.asc())
            .all()
        )

    def get_by_stage_ref(
        self,
        execution_id: str,
        stage_id_ref: str,
    ) -> Optional[ExecutionStep]:
        """Find the step for a specific stage within an execution.

        Args:
            execution_id: The parent ``WorkflowExecution.id``.
            stage_id_ref: The ``stage_id_ref`` snapshot field identifying
                which workflow stage this step belongs to.

        Returns:
            The matching :class:`ExecutionStep`, or ``None`` if not found.
        """
        return (
            self.session.query(ExecutionStep)
            .filter(
                ExecutionStep.execution_id == execution_id,
                ExecutionStep.stage_id_ref == stage_id_ref,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Status updates (for execution engine)
    # ------------------------------------------------------------------

    def update_status(
        self,
        step_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[ExecutionStep]:
        """Update the execution status and optional timing/error fields.

        Only non-``None`` keyword arguments are applied so callers can
        supply a minimal subset of fields.

        Args:
            step_id: The UUID hex string of the step to update.
            status: New status string (e.g. ``"running"``, ``"completed"``).
            started_at: UTC datetime when the step started executing.
            completed_at: UTC datetime when the step finished.
            duration_seconds: Wall-clock duration in seconds.
            error_message: Human-readable error detail when status is
                ``"failed"``.

        Returns:
            The updated :class:`ExecutionStep`, or ``None`` if not found.
        """
        step = self.session.get(ExecutionStep, step_id)
        if step is None:
            logger.debug("update_status: ExecutionStep id=%s not found", step_id)
            return None

        step.status = status
        if started_at is not None:
            step.started_at = started_at
        if completed_at is not None:
            step.completed_at = completed_at
        if duration_seconds is not None:
            step.duration_seconds = duration_seconds
        if error_message is not None:
            step.error_message = error_message

        self.session.flush()
        logger.debug("Updated status of ExecutionStep id=%s to %s", step_id, status)
        return step

    def update_outputs(
        self,
        step_id: str,
        outputs_json: str,
        logs_json: Optional[str] = None,
    ) -> Optional[ExecutionStep]:
        """Store serialised output (and optionally log) payloads on a step.

        Args:
            step_id: The UUID hex string of the step.
            outputs_json: JSON-serialised outputs string to store in
                ``outputs_json``.
            logs_json: Optional JSON-serialised log array.  When provided,
                **replaces** the existing ``logs_json`` value entirely.
                Use :meth:`append_log` for incremental log appending.

        Returns:
            The updated :class:`ExecutionStep`, or ``None`` if not found.
        """
        step = self.session.get(ExecutionStep, step_id)
        if step is None:
            logger.debug("update_outputs: ExecutionStep id=%s not found", step_id)
            return None

        step.outputs_json = outputs_json
        if logs_json is not None:
            step.logs_json = logs_json

        self.session.flush()
        logger.debug("Updated outputs for ExecutionStep id=%s", step_id)
        return step

    def append_log(self, step_id: str, log_entry: str) -> Optional[ExecutionStep]:
        """Append a single log string to the step's ``logs_json`` array.

        ``logs_json`` stores a JSON-serialised list of strings.  Because
        SQLite does not support native JSON array append, this method reads
        the current value, parses it, appends the new entry, and writes back.

        Args:
            step_id: The UUID hex string of the step.
            log_entry: Plain-text log string to append.

        Returns:
            The updated :class:`ExecutionStep`, or ``None`` if not found.
        """
        step = self.session.get(ExecutionStep, step_id)
        if step is None:
            logger.debug("append_log: ExecutionStep id=%s not found", step_id)
            return None

        current: List[str] = json.loads(step.logs_json or "[]")
        current.append(log_entry)
        step.logs_json = json.dumps(current)

        self.session.flush()
        logger.debug(
            "Appended log entry to ExecutionStep id=%s (total=%d)", step_id, len(current)
        )
        return step

    def bulk_update_status(
        self,
        step_ids: List[str],
        status: str,
    ) -> int:
        """Set the same status on multiple steps in a single UPDATE statement.

        Args:
            step_ids: List of UUID hex strings of the steps to update.
            status: Target status string.

        Returns:
            The number of rows actually updated.
        """
        if not step_ids:
            return 0

        updated = (
            self.session.query(ExecutionStep)
            .filter(ExecutionStep.id.in_(step_ids))
            .update(
                {"status": status, "updated_at": datetime.utcnow()},
                synchronize_session="fetch",
            )
        )
        self.session.flush()
        logger.debug(
            "bulk_update_status: set %d step(s) to %s", updated, status
        )
        return updated

    def count_by_status(self, execution_id: str) -> Dict[str, int]:
        """Return a status-keyed count dict for all steps in an execution.

        All known status values are always present in the result so callers
        can do ``counts["completed"]`` without a ``KeyError``.

        Known statuses: ``pending``, ``running``, ``completed``, ``failed``,
        ``skipped``, ``cancelled``.

        Args:
            execution_id: The parent ``WorkflowExecution.id``.

        Returns:
            Dict mapping status string to row count, e.g.
            ``{"pending": 3, "running": 1, "completed": 5, ...}``.
        """
        known_statuses = ["pending", "running", "completed", "failed", "skipped", "cancelled"]
        # Initialise all buckets to 0
        counts: Dict[str, int] = {s: 0 for s in known_statuses}

        rows = (
            self.session.query(ExecutionStep.status, func.count(ExecutionStep.id))
            .filter(ExecutionStep.execution_id == execution_id)
            .group_by(ExecutionStep.status)
            .all()
        )
        for row_status, row_count in rows:
            counts[row_status] = row_count

        return counts
