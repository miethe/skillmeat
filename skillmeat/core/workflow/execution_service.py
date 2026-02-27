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
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from skillmeat.core.workflow.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
)

logger = logging.getLogger(__name__)


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
