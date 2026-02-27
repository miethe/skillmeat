"""Workflow execution API endpoints.

Provides REST API for starting and querying workflow execution records.
All business logic is delegated to ``WorkflowExecutionService``; this module
only handles HTTP concerns (routing, status codes, error translation).
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
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
