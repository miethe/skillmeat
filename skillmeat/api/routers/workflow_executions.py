"""Workflow execution API endpoints.

Provides REST API for starting and querying workflow execution records.
All business logic is delegated to ``WorkflowExecutionService``; this module
only handles HTTP concerns (routing, status codes, error translation).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from skillmeat.core.workflow.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.execution_service import WorkflowExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflow-executions",
    tags=["workflow-executions"],
)


# ---------------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------------


class WorkflowExecutionStartRequest(BaseModel):
    """Request body for starting a new workflow execution.

    Attributes:
        workflow_id:  DB primary key of the workflow to execute.
        parameters:   Optional caller-supplied parameter values merged with
                      workflow defaults.
        overrides:    Optional execution-level overrides dict (e.g. model
                      overrides).
    """

    workflow_id: str
    parameters: Optional[Dict[str, Any]] = None
    overrides: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dto_to_dict(dto: Any) -> Dict[str, Any]:
    """Convert a ``WorkflowExecutionDTO`` dataclass to a plain dict.

    ``datetime`` fields are serialised to ISO-8601 strings so the dict is
    JSON-serialisable without further processing by FastAPI.

    Args:
        dto: A ``WorkflowExecutionDTO`` or ``ExecutionStepDTO`` dataclass instance.

    Returns:
        Plain Python dict suitable for returning as a JSON response body.
    """
    raw = asdict(dto)

    # Convert datetime fields on the execution to ISO strings.
    for key in ("started_at", "completed_at"):
        if key in raw and raw[key] is not None:
            raw[key] = raw[key].isoformat()

    # Recurse into nested step dicts.
    if "steps" in raw and raw["steps"]:
        for step in raw["steps"]:
            for key in ("started_at", "completed_at"):
                if key in step and step[key] is not None:
                    step[key] = step[key].isoformat()

    return raw


def _get_service() -> WorkflowExecutionService:
    """Return a ``WorkflowExecutionService`` instance (uses default DB path).

    Returns:
        Fresh ``WorkflowExecutionService`` instance.
    """
    return WorkflowExecutionService()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    summary="Start workflow execution",
    description=(
        "Validate, plan, and start a new workflow execution. "
        "Returns the created execution record including all pending steps."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def start_execution(
    request: WorkflowExecutionStartRequest,
) -> Dict[str, Any]:
    """Start a new workflow execution.

    Validates the referenced workflow, resolves parameters, creates an
    execution record with status ``"running"``, and creates a pending step
    for each stage in the execution plan.

    Args:
        request: JSON body containing ``workflow_id`` and optional
                 ``parameters`` / ``overrides``.

    Returns:
        Created execution dict (HTTP 201).

    Raises:
        HTTPException 404: If no workflow with ``workflow_id`` exists.
        HTTPException 422: If the workflow definition has validation errors.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        dto = svc.start_execution(
            workflow_id=request.workflow_id,
            parameters=request.parameters,
            overrides=request.overrides,
        )
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except WorkflowValidationError as exc:
        logger.warning(
            "Workflow validation failed during execution start for %s: %s",
            request.workflow_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error starting execution for workflow %s",
            request.workflow_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start workflow execution.",
        ) from exc

    return _dto_to_dict(dto)


@router.get(
    "",
    summary="List workflow executions",
    description=(
        "Return a paginated list of workflow executions. "
        "Optionally filter by ``workflow_id`` and/or ``status``."
    ),
    status_code=status.HTTP_200_OK,
)
async def list_executions(
    workflow_id: Optional[str] = Query(
        None, description="Filter by parent workflow identifier."
    ),
    execution_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by execution status (e.g. 'running', 'completed').",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return."),
) -> List[Dict[str, Any]]:
    """List workflow executions with optional filters and offset pagination.

    Args:
        workflow_id:       Optional workflow identifier to filter by.
        execution_status:  Optional status to filter by (query param name: ``status``).
        skip:              Number of records to skip (0-based offset).
        limit:             Maximum number of records to return (1-200).

    Returns:
        List of execution dicts ordered by start time (descending).
    """
    svc = _get_service()
    try:
        dtos = svc.list_executions(
            workflow_id=workflow_id,
            status=execution_status,
            skip=skip,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Unexpected error listing workflow executions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflow executions.",
        ) from exc

    return [_dto_to_dict(dto) for dto in dtos]


@router.get(
    "/by-workflow/{workflow_id}",
    summary="List executions by workflow",
    description="Return all executions for a specific workflow, ordered by start time (descending).",
    status_code=status.HTTP_200_OK,
)
async def list_executions_by_workflow(
    workflow_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return."),
) -> List[Dict[str, Any]]:
    """List all workflow executions for a specific workflow.

    Args:
        workflow_id: UUID hex string identifying the parent workflow.
        skip:        Number of records to skip (0-based offset).
        limit:       Maximum number of records to return (1-200).

    Returns:
        List of execution dicts for the given workflow.
    """
    svc = _get_service()
    try:
        dtos = svc.list_executions(
            workflow_id=workflow_id,
            skip=skip,
            limit=limit,
        )
    except Exception as exc:
        logger.exception(
            "Unexpected error listing executions for workflow %s", workflow_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflow executions.",
        ) from exc

    return [_dto_to_dict(dto) for dto in dtos]


@router.get(
    "/{execution_id}",
    summary="Get workflow execution",
    description="Retrieve a single workflow execution by ID, including all step records.",
    status_code=status.HTTP_200_OK,
)
async def get_execution(execution_id: str) -> Dict[str, Any]:
    """Retrieve a workflow execution by its primary key.

    Args:
        execution_id: UUID hex string identifying the execution.

    Returns:
        Execution dict with nested steps (HTTP 200).

    Raises:
        HTTPException 404: If no execution with ``execution_id`` exists.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        dto = svc.get_execution(execution_id)
    except WorkflowExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error retrieving execution %s", execution_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow execution.",
        ) from exc

    return _dto_to_dict(dto)


@router.get(
    "/{execution_id}/stream",
    summary="Stream workflow execution events (SSE)",
    description=(
        "Stream real-time Server-Sent Events for a running workflow execution. "
        "The stream emits stage lifecycle events and closes with an "
        "``execution_completed`` event once the execution reaches a terminal state "
        "(completed, failed, or cancelled). "
        "Returns 404 immediately if the execution does not exist."
    ),
)
async def stream_execution_events(execution_id: str) -> StreamingResponse:
    """Stream SSE events for a workflow execution.

    Polls ``WorkflowExecutionService.get_events()`` on a 0.5-second interval,
    forwarding any new events to the client in SSE format.  The stream closes
    automatically when the execution reaches a terminal status.

    SSE event types emitted:

    - ``stage_started``        — ``{"stage_id": str, "stage_name": str}``
    - ``stage_completed``      — ``{"stage_id": str, "duration_seconds": float}``
    - ``stage_failed``         — ``{"stage_id": str, "error": str}``
    - ``stage_skipped``        — ``{"stage_id": str}``
    - ``log_line``             — ``{"stage_id": str, "message": str}``
    - ``execution_completed``  — ``{"status": str}`` (terminal, closes stream)

    Args:
        execution_id: UUID hex string identifying the execution to stream.

    Returns:
        ``StreamingResponse`` with ``text/event-stream`` content type.

    Raises:
        HTTPException 404: If no execution with ``execution_id`` exists.
    """
    # Validate that the execution exists before opening the stream.
    # This provides an immediate 404 rather than a silent empty stream.
    svc = _get_service()
    try:
        svc.get_execution(execution_id)
    except WorkflowExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error pre-validating execution %s for SSE stream",
            execution_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to open event stream.",
        ) from exc

    # Terminal statuses that close the stream.
    _TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

    async def event_generator():
        """Async generator that yields SSE-formatted event strings."""
        last_seq: int = 0
        loop = asyncio.get_event_loop()

        while True:
            # ---------------------------------------------------------------
            # Fetch new events since last_seq (sync call → thread executor)
            # ---------------------------------------------------------------
            try:
                events: List[Dict[str, Any]] = await loop.run_in_executor(
                    None,
                    lambda: _get_service().get_events(execution_id, after_seq=last_seq),
                )
            except Exception as exc:
                logger.warning(
                    "stream_execution_events: error fetching events for %s: %s",
                    execution_id,
                    exc,
                )
                events = []

            for event in events:
                last_seq = event["seq"] + 1
                event_type: str = event.get("type", "message")
                event_data: Dict[str, Any] = event.get("data", {})

                # Normalise event data to match the documented SSE payload shapes.
                # The execution service stores richer payloads; we surface the
                # keys that the SSE contract specifies.
                payload: Dict[str, Any]
                if event_type == "stage_started":
                    payload = {
                        "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
                        "stage_name": event_data.get("stage_name", event_data.get("stage_id", "")),
                    }
                elif event_type == "stage_completed":
                    payload = {
                        "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
                        "duration_seconds": event_data.get("duration_seconds", 0.0),
                    }
                elif event_type == "stage_failed":
                    payload = {
                        "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
                        "error": event_data.get("error", event_data.get("error_message", "")),
                    }
                elif event_type == "log_line":
                    payload = {
                        "stage_id": event_data.get("stage_id", ""),
                        "message": event_data.get("message", ""),
                    }
                elif event_type in ("execution_completed", "execution_failed"):
                    # Normalise both terminal types to "execution_completed" with
                    # the actual status so clients need only listen to one event.
                    event_type = "execution_completed"
                    payload = {
                        "status": event_data.get("status", "completed"),
                    }
                else:
                    # Pass through unknown event types unchanged.
                    payload = event_data

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(payload)}\n\n"

            # ---------------------------------------------------------------
            # Check whether the execution has reached a terminal state.
            # ---------------------------------------------------------------
            try:
                exec_dto = await loop.run_in_executor(
                    None,
                    lambda: _get_service().get_execution(execution_id),
                )
                current_status: str = exec_dto.status
            except WorkflowExecutionNotFoundError:
                # Execution disappeared — close stream.
                logger.warning(
                    "stream_execution_events: execution %s not found during poll — closing stream",
                    execution_id,
                )
                yield "event: execution_completed\n"
                yield f"data: {json.dumps({'status': 'unknown'})}\n\n"
                break
            except Exception as exc:
                logger.warning(
                    "stream_execution_events: error checking status for %s: %s — "
                    "will retry on next poll",
                    execution_id,
                    exc,
                )
                current_status = ""

            if current_status in _TERMINAL_STATUSES:
                # Emit terminal event and close the stream.
                yield "event: execution_completed\n"
                yield f"data: {json.dumps({'status': current_status})}\n\n"
                logger.info(
                    "stream_execution_events: execution %s reached terminal status=%s — closing stream",
                    execution_id,
                    current_status,
                )
                break

            # Poll interval — yield control back to the event loop.
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
