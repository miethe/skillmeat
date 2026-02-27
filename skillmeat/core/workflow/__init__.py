"""SkillMeat Workflow Definition Language (SWDL) models and parser.

This package provides the Pydantic v2 schema models for defining and
validating multi-stage agent workflow definitions in the SWDL format,
plus the ``parse_workflow`` function for loading definitions from disk
and the ``build_dag`` function for constructing the dependency graph.

Typical usage::

    from pathlib import Path
    from skillmeat.core.workflow import parse_workflow, WorkflowDefinition
    from skillmeat.core.workflow import WorkflowParseError, build_dag

    try:
        workflow = parse_workflow(Path("WORKFLOW.yaml"))
    except WorkflowParseError as exc:
        print(exc)

    dag = build_dag(workflow)
    roots = dag.get_roots()

All public models, exceptions, the parser, and DAG builder are exported
from this package for convenience.
"""

from skillmeat.core.workflow.dag import Batch, DAG, DAGNode, build_dag, compute_execution_batches
from skillmeat.core.workflow.planner import (
    ExecutionBatch,
    ExecutionPlan,
    ExecutionPlanStage,
    format_plan_text,
    generate_plan,
)
from skillmeat.core.workflow.expressions import (
    ExpressionContext,
    ExpressionError,
    ExpressionParser,
)
from skillmeat.core.workflow.defaults import apply_defaults
from skillmeat.core.workflow.exceptions import (
    WorkflowArtifactError,
    WorkflowCycleError,
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowParseError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.service import StageDTO, WorkflowDTO, WorkflowService
from skillmeat.core.workflow.models import (
    ContextBinding,
    ErrorPolicy,
    GateConfig,
    GlobalContextConfig,
    GlobalErrorPolicy,
    HandoffConfig,
    InputContract,
    MemoryConfig,
    OutputContract,
    RetryPolicy,
    RoleAssignment,
    StageDefinition,
    StageRoles,
    UIMetadata,
    WorkflowConfig,
    WorkflowDefinition,
    WorkflowHooks,
    WorkflowMetadata,
    WorkflowParameter,
    WorkflowUIMetadata,
)
from skillmeat.core.workflow.parser import parse_workflow
from skillmeat.core.workflow.validator import (
    ValidationIssue,
    ValidationResult,
    validate_expressions,
)

__all__ = [
    # Planner
    "ExecutionBatch",
    "ExecutionPlan",
    "ExecutionPlanStage",
    "format_plan_text",
    "generate_plan",
    # Expression engine
    "ExpressionContext",
    "ExpressionError",
    "ExpressionParser",
    # Expression validator
    "ValidationIssue",
    "ValidationResult",
    "validate_expressions",
    # DAG builder
    "Batch",
    "DAG",
    "DAGNode",
    "build_dag",
    "compute_execution_batches",
    # Exceptions
    "WorkflowError",
    "WorkflowParseError",
    "WorkflowValidationError",
    "WorkflowCycleError",
    "WorkflowArtifactError",
    "WorkflowNotFoundError",
    # Service + DTOs
    "WorkflowService",
    "WorkflowDTO",
    "StageDTO",
    # Parser
    "parse_workflow",
    # Defaults
    "apply_defaults",
    # Models
    "ContextBinding",
    "ErrorPolicy",
    "GateConfig",
    "GlobalContextConfig",
    "GlobalErrorPolicy",
    "HandoffConfig",
    "InputContract",
    "MemoryConfig",
    "OutputContract",
    "RetryPolicy",
    "RoleAssignment",
    "StageDefinition",
    "StageRoles",
    "UIMetadata",
    "WorkflowConfig",
    "WorkflowDefinition",
    "WorkflowHooks",
    "WorkflowMetadata",
    "WorkflowParameter",
    "WorkflowUIMetadata",
]
