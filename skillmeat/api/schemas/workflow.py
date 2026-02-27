"""Pydantic schemas for workflow and workflow-execution API endpoints.

Defines request/response models for workflow CRUD, validation, planning,
and execution lifecycle endpoints.  All schemas use Pydantic v2 style.

Schema Groups:
    - Request schemas: WorkflowCreateRequest, WorkflowUpdateRequest, etc.
    - Response schemas: WorkflowResponse, ExecutionResponse, etc.
    - Nested sub-schemas: StageResponse, ExecutionStepResponse, etc.
    - Validation/planning: ValidationResultResponse, ExecutionPlanResponse, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Request schemas
# =============================================================================


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a new workflow definition.

    Attributes:
        yaml_content: Raw YAML text of the SWDL workflow definition.
        project_id:   Optional project identifier to scope the workflow.
    """

    yaml_content: str = Field(description="Raw YAML workflow definition string.")
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project identifier to scope the workflow.",
    )


class WorkflowUpdateRequest(BaseModel):
    """Request body for replacing a workflow definition.

    Attributes:
        yaml_content: New raw YAML text.  The entire definition is replaced.
    """

    yaml_content: str = Field(description="Replacement YAML workflow definition string.")


class WorkflowDuplicateRequest(BaseModel):
    """Optional request body for duplicating a workflow.

    Attributes:
        new_name: Optional name for the duplicate.  Defaults to
                  ``"<original name> (copy)"`` when not supplied.
    """

    new_name: Optional[str] = Field(
        default=None,
        description="Name for the duplicated workflow.  Defaults to '<original> (copy)'.",
    )


class WorkflowValidateRequest(BaseModel):
    """Optional request body for in-memory workflow validation.

    Attributes:
        parameters: Optional parameter values used during expression validation.
    """

    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameter values for expression validation.",
    )


class WorkflowPlanRequest(BaseModel):
    """Request body for generating a workflow execution plan.

    Attributes:
        parameters: Optional caller-supplied parameter values merged with
                    workflow defaults for planning purposes.
    """

    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameter values merged with workflow defaults.",
    )


class ExecutionStartRequest(BaseModel):
    """Request body for starting a new workflow execution.

    Attributes:
        workflow_id: DB primary key of the workflow to execute.
        parameters:  Optional caller-supplied parameter values merged with
                     workflow defaults.
        overrides:   Optional execution-level overrides (e.g. model overrides).
    """

    workflow_id: str = Field(description="DB primary key of the workflow to execute.")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameter values merged with workflow defaults.",
    )
    overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional execution-level overrides dict.",
    )


class GateRejectRequest(BaseModel):
    """Optional request body for rejecting a gate stage.

    Attributes:
        reason: Human-readable explanation for the rejection.
    """

    reason: Optional[str] = Field(
        default=None,
        description="Optional human-readable reason for the gate rejection.",
    )


# =============================================================================
# Response sub-schemas
# =============================================================================


class StageResponse(BaseModel):
    """Representation of a single workflow stage in a response.

    Attributes:
        id:           DB primary key (uuid hex).
        stage_id_ref: Stage identifier from the SWDL definition (kebab-case).
        name:         Human-readable stage name.
        description:  Optional stage description.
        order_index:  Positional index within the workflow (0-based).
        stage_type:   Stage execution type: "agent" | "gate" | "fan_out".
        condition:    Optional SWDL guard expression string.
        depends_on:   Stage identifier references this stage depends on.
    """

    id: str
    stage_id_ref: str
    name: str
    description: Optional[str] = None
    order_index: int
    stage_type: str
    condition: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ExecutionStepResponse(BaseModel):
    """Representation of a single workflow execution step in a response.

    Attributes:
        id:            DB primary key (uuid hex).
        stage_id:      Stage identifier (kebab-case) from the SWDL definition.
        stage_name:    Human-readable stage name.
        stage_type:    Stage execution type: "agent" | "gate" | "fan_out".
        batch_index:   Parallel batch index from the execution plan (0-based).
        status:        Step lifecycle status.
        started_at:    Timestamp when the step began executing, or ``None``.
        completed_at:  Timestamp when the step finished, or ``None``.
        error_message: Error description if the step failed, or ``None``.
    """

    id: str
    stage_id: str
    stage_name: str
    stage_type: str
    batch_index: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Workflow response schemas
# =============================================================================


class WorkflowResponse(BaseModel):
    """Full workflow definition response.

    Attributes:
        id:          DB primary key (uuid hex).
        name:        Workflow display name.
        description: Optional workflow description.
        version:     SemVer string (e.g. "1.0.0").
        status:      Lifecycle status: "draft" | "active" | "archived".
        definition:  Raw YAML definition string.
        tags:        Searchable tag list.
        stages:      Ordered list of stage sub-schemas.
        project_id:  Optional owning project identifier.
        created_at:  Record creation timestamp.
        updated_at:  Record last-update timestamp.
    """

    id: str
    name: str
    description: Optional[str] = None
    version: str
    status: str
    definition: str
    tags: List[str] = Field(default_factory=list)
    stages: List[StageResponse] = Field(default_factory=list)
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowListResponse(BaseModel):
    """Paginated list of workflow definitions.

    Attributes:
        items: List of workflow response objects.
        total: Total number of matching records (before pagination).
        skip:  Number of records skipped.
        limit: Maximum records returned.
    """

    items: List[WorkflowResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Execution response schemas
# =============================================================================


class ExecutionResponse(BaseModel):
    """Full workflow execution response.

    Attributes:
        id:                DB primary key (uuid hex).
        workflow_id:       Parent workflow primary key.
        status:            Execution lifecycle status.
        parameters:        Resolved parameter dict (merged caller + defaults).
        started_at:        Timestamp when execution began, or ``None``.
        completed_at:      Timestamp when execution finished, or ``None``.
        error_message:     Top-level error description if the execution failed.
        steps:             Ordered list of per-stage execution step responses.
    """

    id: str
    workflow_id: str
    status: str
    parameters: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    steps: List[ExecutionStepResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ExecutionListResponse(BaseModel):
    """Paginated list of workflow executions.

    Attributes:
        items: List of execution response objects.
        total: Total number of matching records (before pagination).
        skip:  Number of records skipped.
        limit: Maximum records returned.
    """

    items: List[ExecutionResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Validation response schemas
# =============================================================================


class ValidationIssueResponse(BaseModel):
    """A single validation error or warning.

    Attributes:
        category:  Validation category: "schema" | "dag" | "expression" | "artifact".
        message:   Human-readable description of the issue.
        stage_id:  Stage identifier where the issue was found, or ``None``.
        field:     Specific field path where the issue was found, or ``None``.
    """

    category: str
    message: str
    stage_id: Optional[str] = None
    field: Optional[str] = None


class ValidationResultResponse(BaseModel):
    """Result of a full multi-pass workflow validation.

    Attributes:
        is_valid:  ``True`` when no blocking errors were found.
        errors:    List of blocking validation issues.
        warnings:  List of non-blocking validation warnings.
    """

    is_valid: bool
    errors: List[ValidationIssueResponse]
    warnings: List[ValidationIssueResponse]


# =============================================================================
# Execution plan response schemas
# =============================================================================


class ExecutionPlanStageResponse(BaseModel):
    """A single stage entry in an execution plan batch.

    Attributes:
        stage_id:                  Stage identifier (kebab-case).
        stage_name:                Human-readable stage name.
        stage_type:                Stage execution type.
        agent:                     Primary agent artifact reference, or ``None``.
        estimated_duration_seconds: Estimated execution time in seconds, or ``None``.
    """

    stage_id: str
    stage_name: str
    stage_type: str
    agent: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None


class ExecutionPlanBatchResponse(BaseModel):
    """A parallel execution batch within an execution plan.

    Attributes:
        batch_index: 0-based index of this batch in the execution order.
        stages:      Stages that can execute concurrently within this batch.
    """

    batch_index: int
    stages: List[ExecutionPlanStageResponse]


class ExecutionPlanResponse(BaseModel):
    """Complete static execution plan for a workflow.

    Attributes:
        workflow_id:             DB primary key of the planned workflow.
        total_stages:            Total number of stages across all batches.
        total_batches:           Number of parallel execution batches.
        batches:                 Ordered list of execution batch responses.
        estimated_total_seconds: Rough sequential timeout estimate in seconds.
    """

    workflow_id: str
    total_stages: int
    total_batches: int
    batches: List[ExecutionPlanBatchResponse]
    estimated_total_seconds: Optional[int] = None
