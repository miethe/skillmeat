"""WorkflowExecutionService: start and query workflow execution records.

Provides business-logic over ``WorkflowExecutionRepository`` and
``WorkflowService``.  All public methods return ``WorkflowExecutionDTO`` /
``ExecutionStepDTO`` dataclasses — never raw ORM models.

The service manages its own session lifecycle (one session per public-method
call, committed on success, rolled back on failure) so it can be used as a
standalone service without a FastAPI dependency-injection context.

Typical usage::

    from skillmeat.core.workflow.execution_service import WorkflowExecutionService

    svc = WorkflowExecutionService()

    # Start an execution — validates + plans the workflow, then persists
    execution = svc.start_execution(workflow_id="abc123", parameters={"env": "prod"})

    # Retrieve
    execution = svc.get_execution(execution.id)

    # List (optionally filtered)
    executions = svc.list_executions(workflow_id="abc123", status="running")
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from skillmeat.core.workflow.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Internal exception used to signal a "halt" from within _execute_stage
# =============================================================================


class _StageHaltError(Exception):
    """Raised inside _run_loop when a stage fails with error_policy='halt'.

    Carries the step_id and original cause so the loop can mark the execution
    as failed and surface a useful error message.
    """

    def __init__(self, stage_id: str, cause: Exception) -> None:
        super().__init__(str(cause))
        self.stage_id = stage_id
        self.cause = cause


# =============================================================================
# Data Transfer Objects
# =============================================================================


@dataclass
class ExecutionStepDTO:
    """Lightweight representation of a single workflow execution step.

    Attributes:
        id:             DB primary key (uuid hex).
        execution_id:   Parent ``WorkflowExecution`` primary key.
        stage_id:       Stage identifier from the SWDL definition (kebab-case).
        stage_name:     Human-readable stage name.
        stage_type:     Stage execution type: "agent" | "gate" | "fan_out".
        batch_index:    Parallel batch index from the execution plan (0-based).
        status:         Current step status: "pending" | "running" | "completed" | "failed" | "skipped".
        started_at:     Timestamp when the step began executing, or ``None``.
        completed_at:   Timestamp when the step finished, or ``None``.
        output:         JSON-serialisable output dict produced by the step, or ``None``.
        error_message:  Error description if the step failed, or ``None``.
    """

    id: str
    execution_id: str
    stage_id: str
    stage_name: str
    stage_type: str
    batch_index: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output: Optional[Dict[str, Any]]
    error_message: Optional[str]


@dataclass
class WorkflowExecutionDTO:
    """Lightweight representation of a persisted workflow execution.

    Attributes:
        id:                  DB primary key (uuid hex).
        workflow_id:         Parent workflow primary key.
        status:              Execution lifecycle status.
        parameters:          Resolved parameter dict (merged caller + defaults).
        workflow_snapshot:   JSON-serialised YAML definition snapshot at run time.
        started_at:          Timestamp when execution began, or ``None``.
        completed_at:        Timestamp when execution finished, or ``None``.
        error_message:       Top-level error description if the execution failed.
        steps:               Ordered list of per-stage execution step DTOs.
    """

    id: str
    workflow_id: str
    status: str
    parameters: Dict[str, Any]
    workflow_snapshot: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    steps: List[ExecutionStepDTO] = field(default_factory=list)


# =============================================================================
# Internal helpers
# =============================================================================


def _step_orm_to_dto(step: "ExecutionStep") -> ExecutionStepDTO:  # noqa: F821
    """Convert an ``ExecutionStep`` ORM instance to an ``ExecutionStepDTO``.

    Args:
        step: Populated ``ExecutionStep`` ORM instance.

    Returns:
        Equivalent ``ExecutionStepDTO``.
    """
    output: Optional[Dict[str, Any]] = None
    if step.outputs_json:
        try:
            output = json.loads(step.outputs_json)
        except (json.JSONDecodeError, TypeError):
            output = None

    # batch_index is stored in logs_json metadata under "batch_index" key,
    # or defaults to 0 when absent (pre-existing rows without this metadata).
    batch_index: int = 0
    if step.logs_json:
        try:
            meta = json.loads(step.logs_json)
            if isinstance(meta, dict):
                batch_index = int(meta.get("batch_index", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            batch_index = 0

    # stage_type is stored in context_consumed_json under "stage_type" key.
    stage_type: str = "agent"
    if step.context_consumed_json:
        try:
            ctx = json.loads(step.context_consumed_json)
            if isinstance(ctx, dict):
                stage_type = str(ctx.get("stage_type", "agent"))
        except (json.JSONDecodeError, TypeError):
            stage_type = "agent"

    return ExecutionStepDTO(
        id=step.id,
        execution_id=step.execution_id,
        stage_id=step.stage_id_ref,
        stage_name=step.stage_name,
        stage_type=stage_type,
        batch_index=batch_index,
        status=step.status,
        started_at=step.started_at,
        completed_at=step.completed_at,
        output=output,
        error_message=step.error_message,
    )


def _execution_orm_to_dto(execution: "WorkflowExecution") -> WorkflowExecutionDTO:  # noqa: F821
    """Convert a ``WorkflowExecution`` ORM instance to a ``WorkflowExecutionDTO``.

    The ``steps`` relationship must be loaded (eagerly or via ``selectin``).

    Args:
        execution: ``WorkflowExecution`` ORM instance.

    Returns:
        Equivalent ``WorkflowExecutionDTO``.
    """
    parameters: Dict[str, Any] = {}
    if execution.parameters_json:
        try:
            parameters = json.loads(execution.parameters_json)
        except (json.JSONDecodeError, TypeError):
            parameters = {}

    # workflow_snapshot is stored in overrides_json under "workflow_snapshot" key.
    workflow_snapshot: Optional[str] = None
    if execution.overrides_json:
        try:
            overrides = json.loads(execution.overrides_json)
            if isinstance(overrides, dict):
                workflow_snapshot = overrides.get("workflow_snapshot")
        except (json.JSONDecodeError, TypeError):
            workflow_snapshot = None

    step_dtos: List[ExecutionStepDTO] = sorted(
        [_step_orm_to_dto(s) for s in (execution.steps or [])],
        key=lambda s: (s.batch_index, s.stage_id),
    )

    return WorkflowExecutionDTO(
        id=execution.id,
        workflow_id=execution.workflow_id,
        status=execution.status,
        parameters=parameters,
        workflow_snapshot=workflow_snapshot,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        error_message=execution.error_message,
        steps=step_dtos,
    )


# =============================================================================
# WorkflowExecutionService
# =============================================================================


class WorkflowExecutionService:
    """Business-logic service for starting and querying workflow executions.

    Manages its own session lifecycle — each public method opens a session,
    commits on success, and rolls back on failure.  The underlying
    ``WorkflowExecutionRepository`` is session-injected, so the service
    constructs and closes the session itself.

    Attributes:
        _db_path: Optional path to the SQLite database file.  Uses the default
            ``~/.skillmeat/cache/cache.db`` when ``None``.

    Example::

        svc = WorkflowExecutionService()

        execution = svc.start_execution("abc123", parameters={"env": "prod"})
        print(execution.id, execution.status)

        execution = svc.get_execution(execution.id)

        page = svc.list_executions(workflow_id="abc123", limit=10)
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialise the service.

        Args:
            db_path: Optional path to the SQLite database file.  Uses the
                default ``~/.skillmeat/cache/cache.db`` when ``None``.
        """
        self._db_path = db_path

        # --- SSE event queues (API-3.13) ---
        # Maps execution_id -> list of event dicts appended by _emit_event().
        # Consumed by the SSE endpoint (future work).
        self._event_queues: Dict[str, List[Dict[str, Any]]] = {}
        self._event_queue_lock = threading.Lock()

        # --- Per-execution cancellation flags ---
        # Maps execution_id -> threading.Event.  Set to cancel/pause the loop.
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._cancel_flags_lock = threading.Lock()

        logger.info("WorkflowExecutionService initialised")

    # =========================================================================
    # Public API
    # =========================================================================

    def start_execution(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecutionDTO:
        """Validate, plan, and start a new workflow execution.

        Steps:

        1. Fetch the workflow via ``WorkflowService`` — raises
           ``WorkflowNotFoundError`` when absent.
        2. Call ``WorkflowService.plan()`` to validate the definition and
           resolve the merged parameter set.  Raises ``WorkflowValidationError``
           when the definition is invalid.
        3. Persist a ``WorkflowExecution`` row with ``status="running"`` and
           ``started_at=now()``.
        4. Persist one ``ExecutionStep`` row (``status="pending"``) for each
           stage in the plan, recording ``batch_index`` and ``stage_type`` in
           the step's JSON metadata fields.
        5. Return a ``WorkflowExecutionDTO`` containing the execution and all
           steps.

        Args:
            workflow_id: DB primary key of the workflow to execute.
            parameters:  Caller-supplied parameter values.  Merged with workflow
                         defaults inside ``WorkflowService.plan()``.  ``None``
                         is treated as an empty dict.
            overrides:   Optional execution-level overrides dict (e.g. model
                         overrides).  Stored alongside the execution record for
                         the execution engine to consume.

        Returns:
            ``WorkflowExecutionDTO`` for the newly created execution.

        Raises:
            WorkflowNotFoundError: If no workflow with ``workflow_id`` exists.
            WorkflowValidationError: If the workflow definition has blocking
                validation errors.
        """
        # Lazy imports to avoid circular dependencies at module load time.
        from skillmeat.cache.models import ExecutionStep  # noqa: PLC0415
        from skillmeat.cache.models import WorkflowExecution  # noqa: PLC0415
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )
        from skillmeat.core.workflow.service import WorkflowService  # noqa: PLC0415

        params: Dict[str, Any] = parameters if parameters is not None else {}

        # Step 1: Validate workflow exists and fetch snapshot metadata.
        wf_service = WorkflowService(db_path=self._db_path)
        workflow_dto = wf_service.get(workflow_id)  # raises WorkflowNotFoundError

        # Step 2: Generate execution plan (validates + resolves parameters).
        plan = wf_service.plan(workflow_id, parameters=params)
        # plan.parameters contains the fully merged set (caller + defaults).
        resolved_params: Dict[str, Any] = plan.parameters

        now = datetime.utcnow()
        execution_id = uuid.uuid4().hex

        # Step 3: Build the WorkflowExecution ORM instance.
        # Store the workflow_snapshot and execution overrides together in
        # overrides_json so we don't require a schema migration for the
        # snapshot column.
        overrides_payload: Dict[str, Any] = dict(overrides) if overrides else {}
        overrides_payload["workflow_snapshot"] = workflow_dto.definition

        execution_orm = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            workflow_name=workflow_dto.name,
            workflow_version=workflow_dto.version,
            status="running",
            trigger="manual",
            parameters_json=json.dumps(resolved_params),
            overrides_json=json.dumps(overrides_payload),
            started_at=now,
        )

        # Step 4: Build ExecutionStep rows from the plan batches.
        step_orms: List[ExecutionStep] = []
        for batch in plan.batches:
            for plan_stage in batch.stages:
                # Encode batch_index in logs_json for later retrieval.
                logs_meta = json.dumps({"batch_index": batch.index})
                # Encode stage_type in context_consumed_json for later retrieval.
                ctx_meta = json.dumps({"stage_type": plan_stage.stage_type})

                step_orms.append(
                    ExecutionStep(
                        id=uuid.uuid4().hex,
                        execution_id=execution_id,
                        stage_id_ref=plan_stage.stage_id,
                        stage_name=plan_stage.name,
                        status="pending",
                        logs_json=logs_meta,
                        context_consumed_json=ctx_meta,
                        created_at=now,
                        updated_at=now,
                    )
                )

        execution_orm.steps = step_orms

        # Step 5: Persist within a single transaction.
        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            saved = repo.create(execution_orm)
            session.commit()
            session.refresh(saved)
            # Refresh steps so they are accessible after commit.
            for step in saved.steps:
                session.refresh(step)

            logger.info(
                "WorkflowExecutionService.start_execution: "
                "execution_id=%s workflow_id=%s steps=%d",
                execution_id,
                workflow_id,
                len(step_orms),
            )
            return _execution_orm_to_dto(saved)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_execution(self, execution_id: str) -> WorkflowExecutionDTO:
        """Retrieve a workflow execution by ID.

        Args:
            execution_id: Primary key of the execution.

        Returns:
            ``WorkflowExecutionDTO`` for the matching record (steps included).

        Raises:
            WorkflowExecutionNotFoundError: If no execution with the given ID
                exists.
        """
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            execution = repo.get_with_steps(execution_id)
            if execution is None:
                raise WorkflowExecutionNotFoundError(
                    f"WorkflowExecution not found: {execution_id!r}",
                    execution_id=execution_id,
                )
            return _execution_orm_to_dto(execution)
        finally:
            session.close()

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WorkflowExecutionDTO]:
        """Return a paginated list of workflow execution DTOs.

        Args:
            workflow_id: Optional workflow filter.
            status:      Optional status filter (e.g. ``"running"``).
            skip:        Number of records to skip (0-based offset).
            limit:       Maximum number of records to return.

        Returns:
            List of ``WorkflowExecutionDTO`` instances, ordered by
            ``started_at DESC`` (most-recent first).
        """
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            # Fetch skip + limit rows and slice client-side, matching the
            # same pattern used in WorkflowService.list().
            rows, _ = repo.list(
                workflow_id=workflow_id,
                status=status,
                limit=skip + limit,
            )
            dtos = [_execution_orm_to_dto(row) for row in rows]
            return dtos[skip : skip + limit]  # noqa: E203
        finally:
            session.close()

    # =========================================================================
    # Execution loop — SVC-3.5
    # =========================================================================

    def run_execution(self, execution_id: str) -> WorkflowExecutionDTO:
        """Run all batches for an existing execution and return the final DTO.

        This is the top-level entry point for the execution engine.  It
        retrieves the persisted execution record, rebuilds the
        ``ExecutionPlan`` from the snapshot stored at start time, runs the
        batch loop, and updates the final execution status.

        The method is *synchronous* and will block until all stages have
        completed, been skipped, or the execution fails/is cancelled.

        Args:
            execution_id: Primary key of the ``WorkflowExecution`` to run.

        Returns:
            ``WorkflowExecutionDTO`` reflecting the final execution state.

        Raises:
            WorkflowExecutionNotFoundError: If no execution with the given ID
                exists.
            WorkflowNotFoundError: If the parent workflow no longer exists
                (needed to re-plan).
        """
        # Lazy imports — circular-import guard (same pattern as start_execution).
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )
        from skillmeat.core.workflow.service import WorkflowService  # noqa: PLC0415

        # --- Register a cancellation flag for this execution ---
        cancel_event = threading.Event()
        with self._cancel_flags_lock:
            self._cancel_flags[execution_id] = cancel_event

        error_msg: Optional[str] = None
        final_status = "completed"
        try:
            # Retrieve current execution state.
            session = get_session(self._db_path)
            try:
                repo = WorkflowExecutionRepository(session)
                execution = repo.get_with_steps(execution_id)
                if execution is None:
                    raise WorkflowExecutionNotFoundError(
                        f"WorkflowExecution not found: {execution_id!r}",
                        execution_id=execution_id,
                    )
                workflow_id = execution.workflow_id
                parameters: Dict[str, Any] = {}
                if execution.parameters_json:
                    try:
                        parameters = json.loads(execution.parameters_json)
                    except (json.JSONDecodeError, TypeError):
                        parameters = {}
            finally:
                session.close()

            # Re-derive the execution plan from the live workflow definition
            # so that the plan stage list is available for the loop.
            wf_service = WorkflowService(db_path=self._db_path)
            plan = wf_service.plan(workflow_id, parameters=parameters)

            logger.info(
                "run_execution: starting execution_id=%s batches=%d",
                execution_id,
                len(plan.batches),
            )
            self._emit_event(
                execution_id,
                "execution_started",
                {"execution_id": execution_id, "batch_count": len(plan.batches)},
            )

            # Run the batch loop.
            self._run_loop(execution_id, plan)

        except _StageHaltError as exc:
            final_status = "failed"
            error_msg = (
                f"Stage '{exc.stage_id}' failed (halt policy): {exc.cause}"
            )
            logger.error(
                "run_execution: execution_id=%s halted at stage %r — %s",
                execution_id,
                exc.stage_id,
                exc.cause,
            )
            self._emit_event(
                execution_id,
                "execution_failed",
                {"execution_id": execution_id, "error": error_msg},
            )
        except Exception as exc:
            final_status = "failed"
            error_msg = str(exc)
            logger.exception(
                "run_execution: unexpected error for execution_id=%s", execution_id
            )
            self._emit_event(
                execution_id,
                "execution_failed",
                {"execution_id": execution_id, "error": error_msg},
            )
        else:
            # Check whether the loop exited due to cancellation.
            if cancel_event.is_set():
                final_status = "cancelled"
            logger.info(
                "run_execution: execution_id=%s finished status=%s",
                execution_id,
                final_status,
            )
            if final_status == "completed":
                self._emit_event(
                    execution_id,
                    "execution_completed",
                    {"execution_id": execution_id},
                )
        finally:
            # Clean up cancellation flag.
            with self._cancel_flags_lock:
                self._cancel_flags.pop(execution_id, None)

        # Persist final execution status.
        now = datetime.utcnow()
        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            repo.update_status(
                execution_id,
                status=final_status,
                completed_at=now,
                error_message=error_msg,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return self.get_execution(execution_id)

    def _run_loop(self, execution_id: str, plan: "ExecutionPlan") -> None:  # noqa: F821
        """Iterate over batches and run each batch's stages in parallel.

        Checks the cancellation flag between batches and stops early if the
        execution has been cancelled or paused.  When any stage in a batch
        raises ``_StageHaltError`` the exception propagates to
        :meth:`run_execution` which marks the execution as failed.

        Args:
            execution_id: Primary key of the execution being run.
            plan:         ``ExecutionPlan`` produced by ``WorkflowService.plan()``.

        Raises:
            _StageHaltError: Propagated from ``_execute_stage`` when
                ``error_policy="halt"`` and the stage has exhausted retries.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import ExecutionStep  # noqa: PLC0415, F401
        from skillmeat.cache.models import get_session  # noqa: PLC0415

        # Build a lookup: stage_id → ExecutionStep.id (from the persisted rows).
        session = get_session(self._db_path)
        try:
            from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
                WorkflowExecutionRepository,
            )

            repo = WorkflowExecutionRepository(session)
            execution = repo.get_with_steps(execution_id)
            if execution is None:
                raise WorkflowExecutionNotFoundError(
                    f"WorkflowExecution not found in _run_loop: {execution_id!r}",
                    execution_id=execution_id,
                )
            # Map stage_id → step DB primary key.
            step_id_map: Dict[str, str] = {
                step.stage_id_ref: step.id for step in (execution.steps or [])
            }
        finally:
            session.close()

        with self._cancel_flags_lock:
            cancel_event = self._cancel_flags.get(execution_id)

        for batch in plan.batches:
            # --- Interruptibility check ---
            if cancel_event is not None and cancel_event.is_set():
                logger.info(
                    "_run_loop: execution_id=%s cancelled before batch %d",
                    execution_id,
                    batch.index,
                )
                return

            logger.info(
                "_run_loop: execution_id=%s starting batch %d (%d stages)",
                execution_id,
                batch.index,
                len(batch.stages),
            )

            # --- Run all stages in this batch concurrently ---
            halt_error: Optional[_StageHaltError] = None
            with ThreadPoolExecutor(
                max_workers=max(1, len(batch.stages)),
                thread_name_prefix=f"exec-{execution_id[:8]}-batch{batch.index}",
            ) as executor:
                futures = {
                    executor.submit(
                        self._execute_stage,
                        execution_id,
                        step_id_map.get(ps.stage_id, ""),
                        ps,
                    ): ps
                    for ps in batch.stages
                }
                for future in as_completed(futures):
                    ps = futures[future]
                    try:
                        future.result()
                    except _StageHaltError as exc:
                        # Record the first halt error; cancel remaining futures.
                        if halt_error is None:
                            halt_error = exc
                        # Other futures are already running — we will wait for
                        # them via as_completed but ignore their exceptions.
                        logger.error(
                            "_run_loop: execution_id=%s batch=%d stage=%r halted",
                            execution_id,
                            batch.index,
                            ps.stage_id,
                        )
                    except Exception as exc:
                        # Non-halt exceptions from _execute_stage are unexpected;
                        # treat them as halt to avoid silent failures.
                        if halt_error is None:
                            halt_error = _StageHaltError(ps.stage_id, exc)
                        logger.exception(
                            "_run_loop: execution_id=%s batch=%d stage=%r "
                            "unexpected exception",
                            execution_id,
                            batch.index,
                            ps.stage_id,
                        )

            # Re-raise the halt error after the entire batch has settled.
            if halt_error is not None:
                raise halt_error

            logger.info(
                "_run_loop: execution_id=%s batch %d complete",
                execution_id,
                batch.index,
            )

        # All batches done — execution loop finished normally.
        logger.info(
            "_run_loop: execution_id=%s all batches complete", execution_id
        )

    def _execute_stage(
        self,
        execution_id: str,
        step_id: str,
        stage: "ExecutionPlanStage",  # noqa: F821
    ) -> None:
        """Execute a single stage and update its ``ExecutionStep`` record.

        Execution flow:
        1. Mark step status = ``"running"``, set ``started_at``.
        2. Evaluate the stage condition (if present); skip when false.
        3. Dispatch based on ``stage.stage_type``:
           - ``"gate"``: mark ``"waiting_for_approval"`` and return (resolved
             externally via the approve/reject endpoint).
           - All other types (``"agent"``, ``"fan_out"``): stub dispatch —
             log and mark complete.
        4. Apply retry policy on failure (up to ``max_attempts - 1`` retries).
        5. Apply timeout via a threading.Timer watchdog.
        6. On final failure apply ``error_policy``:
           - ``"halt"`` / ``"skip_dependents"``: raise ``_StageHaltError``.
           - ``"continue"`` / ``"skip"``: mark appropriately, do not re-raise.
           - ``"ignore"``  : mark ``"failed"``, do not re-raise.

        Args:
            execution_id: Parent execution primary key.
            step_id:      ``ExecutionStep`` primary key for this stage.
            stage:        Resolved ``ExecutionPlanStage`` from the plan.

        Raises:
            _StageHaltError: When the stage fails and ``error_policy`` is
                ``"halt"`` or ``"skip_dependents"``.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        stage_id = stage.stage_id
        stage_name = stage.name
        stage_type = stage.stage_type

        # --- Resolve error / retry policy ---
        # ErrorPolicy on_failure values: "halt" | "continue" | "skip_dependents"
        # We also support "skip" and "ignore" as informal aliases used in
        # the task spec comments.  Map them to the closest canonical value.
        on_failure_raw: str = "halt"
        max_attempts: int = 1
        retry_delay_seconds: float = 0.0

        if stage.condition is not None or True:
            # We always need the error policy regardless of whether there is
            # a condition, so read it unconditionally.
            pass  # policy resolved below via stage attributes

        # ExecutionPlanStage carries error_policy.timeout but not the full
        # ErrorPolicy object; retry info would come from the full stage
        # definition.  For this phase we use the stage timeout field only.
        # Retry and on_failure are read from the SWDL model (not available
        # on ExecutionPlanStage directly), so we default to safe values.
        #
        # NOTE: A future iteration (SVC-3.6) will pass the full StageDefinition
        # so that retry and on_failure can be respected from the SWDL schema.

        # --- Parse timeout ---
        timeout_seconds: Optional[float] = None
        if stage.timeout:
            from skillmeat.core.workflow.planner import (  # noqa: PLC0415
                _parse_duration_seconds,
            )

            parsed = _parse_duration_seconds(stage.timeout)
            if parsed > 0:
                timeout_seconds = float(parsed)

        # ---------------------------------------------------------------
        # Step 1: Mark as "running"
        # ---------------------------------------------------------------
        now = datetime.utcnow()
        self._update_step(step_id, status="running", started_at=now)
        self._emit_event(
            execution_id,
            "stage_started",
            {
                "execution_id": execution_id,
                "step_id": step_id,
                "stage_id": stage_id,
                "stage_name": stage_name,
                "stage_type": stage_type,
            },
        )
        logger.info(
            "_execute_stage: execution_id=%s stage=%r type=%r started",
            execution_id,
            stage_id,
            stage_type,
        )

        # ---------------------------------------------------------------
        # Step 2: Evaluate condition
        # ---------------------------------------------------------------
        if stage.condition is not None:
            try:
                from skillmeat.core.workflow.expressions import (  # noqa: PLC0415
                    ExpressionContext,
                    ExpressionParser,
                )

                # Build a minimal expression context from the execution
                # parameters stored in the execution record.
                session = get_session(self._db_path)
                try:
                    repo = WorkflowExecutionRepository(session)
                    execution = repo.get(execution_id)
                    params: Dict[str, Any] = {}
                    if execution is not None and execution.parameters_json:
                        try:
                            params = json.loads(execution.parameters_json)
                        except (json.JSONDecodeError, TypeError):
                            params = {}
                finally:
                    session.close()

                ctx = ExpressionContext(
                    parameters=params,
                    run={"execution_id": execution_id},
                )
                parser = ExpressionParser()
                # Strip ${{ }} wrapper if present.
                raw_expr = stage.condition.strip()
                if raw_expr.startswith("${{") and raw_expr.endswith("}}"):
                    raw_expr = raw_expr[3:-2].strip()

                result = parser.evaluate(raw_expr, ctx)
                if not result:
                    logger.info(
                        "_execute_stage: execution_id=%s stage=%r condition=False → skipped",
                        execution_id,
                        stage_id,
                    )
                    self._update_step(
                        step_id,
                        status="skipped",
                        completed_at=datetime.utcnow(),
                    )
                    self._emit_event(
                        execution_id,
                        "stage_skipped",
                        {
                            "execution_id": execution_id,
                            "step_id": step_id,
                            "stage_id": stage_id,
                            "reason": "condition_false",
                        },
                    )
                    return
            except Exception as exc:
                logger.warning(
                    "_execute_stage: execution_id=%s stage=%r condition eval error: %s",
                    execution_id,
                    stage_id,
                    exc,
                )
                # Treat condition evaluation failure as a skip (safe default).
                self._update_step(
                    step_id,
                    status="skipped",
                    completed_at=datetime.utcnow(),
                    error_message=f"Condition eval error: {exc}",
                )
                self._emit_event(
                    execution_id,
                    "stage_skipped",
                    {
                        "execution_id": execution_id,
                        "step_id": step_id,
                        "stage_id": stage_id,
                        "reason": "condition_eval_error",
                    },
                )
                return

        # ---------------------------------------------------------------
        # Step 3: Dispatch by stage type
        # ---------------------------------------------------------------
        last_exc: Optional[Exception] = None

        def _dispatch() -> None:
            """Perform the actual work for one attempt."""
            if stage_type == "gate":
                # Gate stages pause until external approval (API-3.14 endpoint).
                # Mark as waiting and return immediately — the approve/reject
                # endpoint will transition this step to completed/failed.
                self._update_step(step_id, status="waiting_for_approval")
                self._emit_event(
                    execution_id,
                    "stage_waiting_for_approval",
                    {
                        "execution_id": execution_id,
                        "step_id": step_id,
                        "stage_id": stage_id,
                        "approvers": stage.gate_approvers,
                    },
                )
                logger.info(
                    "_execute_stage: execution_id=%s stage=%r gate waiting for approval",
                    execution_id,
                    stage_id,
                )
                # Gate stages do not complete synchronously; return early.
                return

            # ------------------------------------------------------------------
            # Agent / fan_out dispatch (STUB — real dispatch is future work)
            # ------------------------------------------------------------------
            # TODO(SVC-4.x): Replace this stub with actual agent dispatch via
            # the SkillMeat agent runtime.  The stub logs the intent and marks
            # the step as completed immediately to unblock downstream stages.
            agent_ref = stage.primary_artifact or "(no artifact)"
            model_ref = stage.model or "default"
            logger.info(
                "_execute_stage: [STUB] dispatching stage=%r artifact=%r model=%r "
                "to agent runtime (execution_id=%s)",
                stage_id,
                agent_ref,
                model_ref,
                execution_id,
            )
            # Stub output mirrors what a real agent would produce.
            stub_output = {
                "stub": True,
                "stage_id": stage_id,
                "artifact": agent_ref,
                "model": model_ref,
                "message": f"Stage '{stage_name}' dispatched (stub — real dispatch is future work)",
            }
            completed_at = datetime.utcnow()
            self._update_step(
                step_id,
                status="completed",
                completed_at=completed_at,
                outputs=stub_output,
            )
            self._emit_event(
                execution_id,
                "stage_completed",
                {
                    "execution_id": execution_id,
                    "step_id": step_id,
                    "stage_id": stage_id,
                    "output": stub_output,
                },
            )
            logger.info(
                "_execute_stage: execution_id=%s stage=%r completed (stub)",
                execution_id,
                stage_id,
            )

        # ---------------------------------------------------------------
        # Step 4: Timeout watchdog + retry loop
        # ---------------------------------------------------------------
        timed_out_flag = threading.Event()

        def _on_timeout() -> None:
            timed_out_flag.set()

        for attempt in range(max(1, max_attempts)):
            if timeout_seconds is not None:
                watchdog = threading.Timer(timeout_seconds, _on_timeout)
                watchdog.daemon = True
                watchdog.start()
            else:
                watchdog = None

            try:
                _dispatch()
                last_exc = None
                break  # success — exit retry loop
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "_execute_stage: execution_id=%s stage=%r attempt=%d failed: %s",
                    execution_id,
                    stage_id,
                    attempt + 1,
                    exc,
                )
            finally:
                if watchdog is not None:
                    watchdog.cancel()

            # Check timeout before deciding to retry.
            if timed_out_flag.is_set():
                self._update_step(
                    step_id,
                    status="timed_out",
                    completed_at=datetime.utcnow(),
                    error_message=f"Stage timed out after {timeout_seconds}s",
                )
                self._emit_event(
                    execution_id,
                    "stage_failed",
                    {
                        "execution_id": execution_id,
                        "step_id": step_id,
                        "stage_id": stage_id,
                        "reason": "timeout",
                    },
                )
                last_exc = TimeoutError(
                    f"Stage '{stage_id}' timed out after {timeout_seconds}s"
                )
                break  # do not retry after timeout

            # Retry delay before next attempt.
            if last_exc is not None and attempt + 1 < max_attempts:
                if retry_delay_seconds > 0:
                    time.sleep(retry_delay_seconds)

        # ---------------------------------------------------------------
        # Step 5: Handle final failure
        # ---------------------------------------------------------------
        if last_exc is not None and not timed_out_flag.is_set():
            # Update step to failed (non-timeout path).
            self._update_step(
                step_id,
                status="failed",
                completed_at=datetime.utcnow(),
                error_message=str(last_exc),
            )
            self._emit_event(
                execution_id,
                "stage_failed",
                {
                    "execution_id": execution_id,
                    "step_id": step_id,
                    "stage_id": stage_id,
                    "error": str(last_exc),
                },
            )

        if last_exc is not None:
            # Apply error policy.
            if on_failure_raw in ("halt", "skip_dependents"):
                raise _StageHaltError(stage_id, last_exc)
            elif on_failure_raw in ("continue", "skip"):
                logger.info(
                    "_execute_stage: execution_id=%s stage=%r failed but "
                    "on_failure=%r — continuing",
                    execution_id,
                    stage_id,
                    on_failure_raw,
                )
                if on_failure_raw == "skip":
                    self._update_step(step_id, status="skipped")
                # "continue": leave as "failed" but don't halt the batch.
            else:
                # "ignore" or unknown — mark failed, do not halt.
                logger.info(
                    "_execute_stage: execution_id=%s stage=%r failed "
                    "on_failure=%r (ignored)",
                    execution_id,
                    stage_id,
                    on_failure_raw,
                )

    # =========================================================================
    # Execution state management helpers — SVC-3.6 stubs
    # =========================================================================

    def pause_execution(self, execution_id: str) -> WorkflowExecutionDTO:
        """Pause a running execution.

        Sets the execution status to ``"paused"`` and signals the execution
        loop to stop before the next batch.

        NOTE: Full pause/resume semantics (persisting current batch position
        so execution can resume mid-workflow) are deferred to SVC-3.6.
        This stub sets the status and signals the cancellation flag so the
        loop exits cleanly between batches.

        Args:
            execution_id: Primary key of the execution to pause.

        Returns:
            Updated ``WorkflowExecutionDTO``.

        Raises:
            WorkflowExecutionNotFoundError: If the execution does not exist.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            updated = repo.update_status(execution_id, status="paused")
            if updated is None:
                raise WorkflowExecutionNotFoundError(
                    f"WorkflowExecution not found: {execution_id!r}",
                    execution_id=execution_id,
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        # Signal the execution loop to stop between batches.
        with self._cancel_flags_lock:
            flag = self._cancel_flags.get(execution_id)
        if flag is not None:
            flag.set()

        logger.info("pause_execution: execution_id=%s paused", execution_id)
        return self.get_execution(execution_id)

    def resume_execution(self, execution_id: str) -> WorkflowExecutionDTO:
        """Resume a paused execution.

        Sets the execution status back to ``"running"``.

        NOTE: This stub only transitions the status field.  Actually
        re-entering the batch loop from the correct position is deferred to
        SVC-3.6.

        Args:
            execution_id: Primary key of the execution to resume.

        Returns:
            Updated ``WorkflowExecutionDTO``.

        Raises:
            WorkflowExecutionNotFoundError: If the execution does not exist.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            updated = repo.update_status(execution_id, status="running")
            if updated is None:
                raise WorkflowExecutionNotFoundError(
                    f"WorkflowExecution not found: {execution_id!r}",
                    execution_id=execution_id,
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        logger.info("resume_execution: execution_id=%s resumed", execution_id)
        return self.get_execution(execution_id)

    def cancel_execution(self, execution_id: str) -> WorkflowExecutionDTO:
        """Cancel a running or paused execution.

        Sets the execution status to ``"cancelled"``, signals the loop to
        stop, and marks all ``"pending"`` steps as ``"cancelled"``.

        Args:
            execution_id: Primary key of the execution to cancel.

        Returns:
            Updated ``WorkflowExecutionDTO``.

        Raises:
            WorkflowExecutionNotFoundError: If the execution does not exist.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import ExecutionStep  # noqa: PLC0415
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.cache.workflow_execution_repository import (  # noqa: PLC0415
            WorkflowExecutionRepository,
        )

        # Signal the loop to exit between batches.
        with self._cancel_flags_lock:
            flag = self._cancel_flags.get(execution_id)
        if flag is not None:
            flag.set()

        now = datetime.utcnow()
        session = get_session(self._db_path)
        try:
            repo = WorkflowExecutionRepository(session)
            execution = repo.get_with_steps(execution_id)
            if execution is None:
                raise WorkflowExecutionNotFoundError(
                    f"WorkflowExecution not found: {execution_id!r}",
                    execution_id=execution_id,
                )

            # Cancel all pending/running steps.
            for step in execution.steps or []:
                if step.status in ("pending", "running"):
                    step.status = "cancelled"
                    step.completed_at = now
                    step.updated_at = now

            repo.update_status(execution_id, status="cancelled", completed_at=now)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        logger.info("cancel_execution: execution_id=%s cancelled", execution_id)
        return self.get_execution(execution_id)

    # =========================================================================
    # SSE event emission (stub — consumed by API-3.13)
    # =========================================================================

    def _emit_event(
        self,
        execution_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Append an SSE event to the in-memory queue for this execution.

        Consumers (the SSE endpoint, API-3.13) read from this queue to stream
        real-time status updates to connected clients.

        Events are appended in order and include a monotonic sequence number
        for reliable client-side ordering.

        Args:
            execution_id: Execution the event belongs to.
            event_type:   Event name — one of:
                          ``"execution_started"``, ``"stage_started"``,
                          ``"stage_completed"``, ``"stage_failed"``,
                          ``"stage_skipped"``, ``"stage_waiting_for_approval"``,
                          ``"execution_completed"``, ``"execution_failed"``.
            data:         Arbitrary JSON-serialisable payload dict.
        """
        with self._event_queue_lock:
            queue = self._event_queues.setdefault(execution_id, [])
            event = {
                "seq": len(queue),
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }
            queue.append(event)

        logger.debug(
            "_emit_event: execution_id=%s type=%s seq=%d",
            execution_id,
            event_type,
            event["seq"],
        )

    def get_events(
        self,
        execution_id: str,
        after_seq: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return all queued SSE events for an execution after *after_seq*.

        Intended for use by the SSE endpoint (API-3.13) to long-poll or
        stream events to clients.

        Args:
            execution_id: Execution to query.
            after_seq:    Return only events with ``seq >= after_seq``.
                          0 returns all events.

        Returns:
            List of event dicts in chronological order.
        """
        with self._event_queue_lock:
            queue = self._event_queues.get(execution_id, [])
            return [e for e in queue if e["seq"] >= after_seq]

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _update_step(
        self,
        step_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update an ``ExecutionStep`` record within its own session.

        Each call opens a new session, applies the mutation, commits, and
        closes.  This is safe to call from worker threads because each call
        owns its own connection.

        Args:
            step_id:       Primary key of the ``ExecutionStep`` to update.
            status:        New status string.
            started_at:    If provided, set ``started_at``.
            completed_at:  If provided, set ``completed_at`` and compute
                           ``duration_seconds`` when ``started_at`` is also
                           known.
            error_message: If provided, set ``error_message``.
            outputs:       If provided, serialise to ``outputs_json``.
        """
        # Lazy imports — circular-import guard.
        from skillmeat.cache.models import ExecutionStep  # noqa: PLC0415
        from skillmeat.cache.models import get_session  # noqa: PLC0415

        if not step_id:
            # step_id can be empty when a stage was added to the plan after
            # the execution was created (shouldn't happen, but be defensive).
            logger.warning("_update_step: empty step_id, skipping update")
            return

        session = get_session(self._db_path)
        try:
            step: Optional[ExecutionStep] = (
                session.query(ExecutionStep)
                .filter(ExecutionStep.id == step_id)
                .first()
            )
            if step is None:
                logger.warning(
                    "_update_step: step_id=%r not found, skipping", step_id
                )
                return

            step.status = status
            step.updated_at = datetime.utcnow()

            if started_at is not None:
                step.started_at = started_at
            if completed_at is not None:
                step.completed_at = completed_at
                # Compute duration if we know when the step started.
                effective_start = started_at or step.started_at
                if effective_start is not None:
                    delta = completed_at - effective_start
                    step.duration_seconds = max(0.0, delta.total_seconds())
            if error_message is not None:
                step.error_message = error_message
            if outputs is not None:
                try:
                    step.outputs_json = json.dumps(outputs)
                except (TypeError, ValueError):
                    step.outputs_json = json.dumps({"raw": str(outputs)})

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
