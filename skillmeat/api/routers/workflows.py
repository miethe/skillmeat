"""Workflow management API endpoints.

Provides REST API for CRUD operations on SkillMeat workflow definitions.
All business logic is delegated to ``WorkflowService``; this module only
handles HTTP concerns (routing, status codes, error translation).
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from skillmeat.core.workflow.exceptions import (
    WorkflowNotFoundError,
    WorkflowParseError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)


# ---------------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------------


class WorkflowCreateRequest(BaseModel):
    """Request body for creating or replacing a workflow definition.

    Attributes:
        yaml_content: Raw YAML string of the SWDL workflow definition.
        project_id:   Optional project identifier to scope the workflow.
    """

    yaml_content: str
    project_id: Optional[str] = None


class WorkflowUpdateRequest(BaseModel):
    """Request body for updating an existing workflow definition.

    Attributes:
        yaml_content: New raw YAML string.  Replaces the existing definition
                      and all associated stages atomically.
    """

    yaml_content: str


class WorkflowDuplicateRequest(BaseModel):
    """Optional request body for the duplicate endpoint.

    Attributes:
        new_name: Display name for the copy.  Defaults to
                  ``"<original name> (copy)"`` when omitted.
    """

    new_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dto_to_dict(dto: Any) -> Dict[str, Any]:
    """Convert a ``WorkflowDTO`` or ``StageDTO`` dataclass to a plain dict.

    ``datetime`` fields are serialised to ISO-8601 strings so the dict is
    JSON-serialisable without further processing by FastAPI.

    Args:
        dto: A dataclass instance (``WorkflowDTO`` or ``StageDTO``).

    Returns:
        Plain Python dict suitable for returning as a JSON response body.
    """
    raw = asdict(dto)

    # Convert datetime fields to ISO strings
    for key in ("created_at", "updated_at"):
        if key in raw and raw[key] is not None:
            raw[key] = raw[key].isoformat()

    # Recurse into nested stage dicts
    if "stages" in raw and raw["stages"]:
        for stage in raw["stages"]:
            for key in ("created_at", "updated_at"):
                if key in stage and stage[key] is not None:
                    stage[key] = stage[key].isoformat()

    return raw


def _get_service() -> WorkflowService:
    """Return a ``WorkflowService`` instance (uses default DB path).

    Returns:
        Fresh ``WorkflowService`` instance.
    """
    return WorkflowService()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="List workflows",
    description=(
        "Return a paginated list of workflow definitions. "
        "Optionally filter by ``project_id``."
    ),
    status_code=status.HTTP_200_OK,
)
async def list_workflows(
    project_id: Optional[str] = Query(
        None, description="Filter by owning project identifier."
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return."),
) -> List[Dict[str, Any]]:
    """List workflows with optional project filter and offset pagination.

    Args:
        project_id: Optional project identifier to filter by.
        skip:       Number of records to skip (0-based offset).
        limit:      Maximum number of records to return (1-200).

    Returns:
        List of workflow dicts ordered by creation date (descending).
    """
    svc = _get_service()
    try:
        dtos = svc.list(project_id=project_id, skip=skip, limit=limit)
    except Exception as exc:
        logger.exception("Unexpected error listing workflows")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflows.",
        ) from exc

    return [_dto_to_dict(dto) for dto in dtos]


@router.post(
    "",
    summary="Create workflow",
    description="Parse, validate, and persist a new workflow definition from YAML.",
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow(
    request: WorkflowCreateRequest,
) -> Dict[str, Any]:
    """Create a new workflow from a YAML definition string.

    Args:
        request: JSON body containing ``yaml_content`` and optional
                 ``project_id``.

    Returns:
        Created workflow dict (HTTP 201).

    Raises:
        HTTPException 422: On YAML parse or schema validation failure.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        dto = svc.create(
            yaml_content=request.yaml_content,
            project_id=request.project_id,
        )
    except (WorkflowParseError, WorkflowValidationError) as exc:
        logger.warning("Workflow parse/validation error on create: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error creating workflow")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow.",
        ) from exc

    return _dto_to_dict(dto)


@router.get(
    "/{workflow_id}",
    summary="Get workflow",
    description="Retrieve a single workflow definition by ID.",
    status_code=status.HTTP_200_OK,
)
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Retrieve a workflow by its primary key.

    Args:
        workflow_id: UUID hex string identifying the workflow.

    Returns:
        Workflow dict (HTTP 200).

    Raises:
        HTTPException 404: If no workflow with ``workflow_id`` exists.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        dto = svc.get(workflow_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error retrieving workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow.",
        ) from exc

    return _dto_to_dict(dto)


@router.put(
    "/{workflow_id}",
    summary="Update workflow",
    description=(
        "Re-parse and replace the YAML definition of an existing workflow. "
        "All stages are replaced atomically."
    ),
    status_code=status.HTTP_200_OK,
)
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
) -> Dict[str, Any]:
    """Update an existing workflow with a new YAML definition.

    Args:
        workflow_id: UUID hex string identifying the workflow to update.
        request:     JSON body containing the new ``yaml_content``.

    Returns:
        Updated workflow dict (HTTP 200).

    Raises:
        HTTPException 404: If no workflow with ``workflow_id`` exists.
        HTTPException 422: On YAML parse or schema validation failure.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        dto = svc.update(workflow_id, request.yaml_content)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (WorkflowParseError, WorkflowValidationError) as exc:
        logger.warning(
            "Workflow parse/validation error on update %s: %s", workflow_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error updating workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow.",
        ) from exc

    return _dto_to_dict(dto)


@router.delete(
    "/{workflow_id}",
    summary="Delete workflow",
    description="Delete a workflow and all its stages.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workflow(workflow_id: str) -> None:
    """Delete a workflow by ID.

    Args:
        workflow_id: UUID hex string identifying the workflow to delete.

    Returns:
        Empty body (HTTP 204).

    Raises:
        HTTPException 404: If no workflow with ``workflow_id`` exists.
        HTTPException 500: On unexpected errors.
    """
    svc = _get_service()
    try:
        svc.delete(workflow_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error deleting workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow.",
        ) from exc


@router.post(
    "/{workflow_id}/duplicate",
    summary="Duplicate workflow",
    description=(
        "Create a copy of an existing workflow with a new ID. "
        "The copy is created with ``status='draft'``."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_workflow(
    workflow_id: str,
    request: Optional[WorkflowDuplicateRequest] = None,
) -> Dict[str, Any]:
    """Duplicate an existing workflow.

    Args:
        workflow_id: UUID hex string of the source workflow.
        request:     Optional JSON body with a ``new_name`` for the copy.
                     When omitted, the copy is named
                     ``"<original name> (copy)"``.

    Returns:
        Newly created duplicate workflow dict (HTTP 201).

    Raises:
        HTTPException 404: If no workflow with ``workflow_id`` exists.
        HTTPException 500: On unexpected errors.
    """
    new_name: Optional[str] = None
    if request is not None:
        new_name = request.new_name

    svc = _get_service()
    try:
        dto = svc.duplicate(workflow_id, new_name=new_name)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error duplicating workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate workflow.",
        ) from exc

    return _dto_to_dict(dto)
