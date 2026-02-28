"""Execution plan generator for SkillMeat Workflow Definition Language (SWDL).

This module converts a parsed ``WorkflowDefinition`` into an ``ExecutionPlan``
that describes how the workflow will run: which stages execute in parallel,
what inputs each stage receives, and an estimated runtime.

The plan is generated at call time (before execution) and is purely descriptive.
Expression sources are passed through as-is — they are not evaluated at plan
time, only at execution time when stage outputs are available.

Typical usage::

    from skillmeat.core.workflow import parse_workflow
    from skillmeat.core.workflow.planner import generate_plan, format_plan_text

    workflow = parse_workflow(path)
    plan = generate_plan(workflow, {"feature": "auth-redesign"})
    print(format_plan_text(plan))
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from skillmeat.core.workflow.dag import Batch, build_dag, compute_execution_batches
from skillmeat.core.workflow.defaults import apply_defaults
from skillmeat.core.workflow.exceptions import WorkflowValidationError
from skillmeat.core.workflow.models import StageDefinition, WorkflowDefinition
from skillmeat.core.workflow.validator import ValidationResult, validate_expressions


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(
    r"^(?:(?P<days>\d+)d)?"
    r"(?:(?P<hours>\d+)h)?"
    r"(?:(?P<minutes>\d+)m)?"
    r"(?:(?P<seconds>\d+)s)?$"
)


def _parse_duration_seconds(duration: str) -> int:
    """Convert a duration string to total seconds.

    Supports days (``d``), hours (``h``), minutes (``m``), and seconds (``s``).
    Components may be combined (e.g. ``"1h30m"``).  Returns 0 for empty or
    unrecognised strings rather than raising so that the timeout estimate
    degrades gracefully.

    Args:
        duration: A duration string such as ``"30m"``, ``"2h"``, ``"1h30m"``,
                  ``"24h"``, or ``"1d"``.

    Returns:
        Total duration in seconds.  0 if the string is empty or does not match.
    """
    if not duration:
        return 0
    m = _DURATION_RE.match(duration.strip())
    if not m or not any(m.group(g) for g in ("days", "hours", "minutes", "seconds")):
        return 0
    days = int(m.group("days") or 0)
    hours = int(m.group("hours") or 0)
    minutes = int(m.group("minutes") or 0)
    seconds = int(m.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _format_seconds(total: int) -> str:
    """Format a total-seconds value as a human-readable duration string.

    Args:
        total: Total seconds (non-negative).

    Returns:
        A compact human-readable string such as ``"30m"``, ``"2h"``,
        ``"1h 30m"``, or ``"0m"`` for zero.
    """
    if total <= 0:
        return "0m"
    hours, remainder = divmod(total, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append("0m")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Plan dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ExecutionPlanStage:
    """Fully-resolved description of a single stage in the execution plan.

    All fields are derived from the ``StageDefinition`` and the DAG.  Input
    ``source`` expressions are kept as raw strings (not evaluated) because
    upstream stage outputs are not available at plan time.

    Attributes:
        stage_id:        Unique stage identifier.
        name:            Human-readable stage name.
        stage_type:      ``"agent"`` or ``"gate"``.
        primary_artifact: ``roles.primary.artifact`` or ``None`` for gate stages.
        model:           ``roles.primary.model`` or ``None``.
        tools:           Supporting artifact references from ``roles.tools``.
        inputs:          Mapping of input name to its raw ``source`` expression
                         string (or ``"(no source)"`` when absent).
        outputs:         List of declared output field names.
        context_modules: Stage-level context module references.
        timeout:         Effective stage timeout string or ``None``.
        condition:       Raw condition expression string or ``None``.
        depends_on:      Stage IDs this stage depends on.
        gate_approvers:  Approver identifiers for gate stages (empty otherwise).
        gate_timeout:    Gate timeout string or ``None`` for non-gate stages.
    """

    stage_id: str
    name: str
    stage_type: str
    primary_artifact: Optional[str]
    model: Optional[str]
    tools: List[str]
    inputs: Dict[str, str]
    outputs: List[str]
    context_modules: List[str]
    timeout: Optional[str]
    condition: Optional[str]
    depends_on: List[str]
    # Gate-specific
    gate_approvers: List[str] = field(default_factory=list)
    gate_timeout: Optional[str] = None


@dataclass
class ExecutionBatch:
    """A group of stages that can execute concurrently.

    Attributes:
        index:  0-based position within the ordered execution plan.
        stages: Stages belonging to this batch.
    """

    index: int
    stages: List[ExecutionPlanStage]


@dataclass
class ExecutionPlan:
    """Complete, human-inspectable execution plan for a workflow run.

    Generated by :func:`generate_plan` before execution begins.  Contains
    the resolved parameter set, an ordered list of parallel execution batches,
    a rough estimated total wall-clock time, and the result of the static
    expression validation pass.

    Attributes:
        workflow_id:               Workflow identifier.
        workflow_name:             Human-readable workflow name.
        workflow_version:          SemVer version string.
        parameters:                Fully merged parameters (defaults + caller values).
        batches:                   Ordered list of parallel execution batches.
        estimated_timeout_seconds: Rough sequential sum of per-batch max timeouts.
        validation:                Static expression validation result.
    """

    workflow_id: str
    workflow_name: str
    workflow_version: str
    parameters: Dict[str, Any]
    batches: List[ExecutionBatch]
    estimated_timeout_seconds: int
    validation: ValidationResult

    def format_text(self) -> str:
        """Return a human-readable representation of the execution plan.

        Matches the Schema Spec Section 4.2 format.

        Returns:
            Multi-line string describing the plan.
        """
        return format_plan_text(self)


# ---------------------------------------------------------------------------
# Stage extraction helpers
# ---------------------------------------------------------------------------


def _build_plan_stage(stage: StageDefinition) -> ExecutionPlanStage:
    """Convert a ``StageDefinition`` into an ``ExecutionPlanStage``.

    Inputs are kept as raw expression strings.  The effective timeout is read
    from ``error_policy.timeout`` (populated by ``apply_defaults``).

    Args:
        stage: A ``StageDefinition`` after defaults have been applied.

    Returns:
        A fully-populated ``ExecutionPlanStage``.
    """
    # --- Roles ---
    primary_artifact: Optional[str] = None
    model: Optional[str] = None
    tools: List[str] = []
    if stage.roles is not None:
        primary_artifact = stage.roles.primary.artifact
        model = stage.roles.primary.model
        tools = list(stage.roles.tools)

    # --- Inputs ---
    inputs: Dict[str, str] = {}
    for inp_name, inp_contract in stage.inputs.items():
        inputs[inp_name] = inp_contract.source if inp_contract.source else "(no source)"

    # --- Outputs ---
    outputs: List[str] = list(stage.outputs.keys())

    # --- Context modules ---
    context_modules: List[str] = []
    if stage.context is not None:
        context_modules = list(stage.context.modules)

    # --- Timeout ---
    # apply_defaults ensures error_policy is always set with a timeout.
    timeout: Optional[str] = None
    if stage.error_policy is not None:
        timeout = stage.error_policy.timeout

    # --- Gate details ---
    gate_approvers: List[str] = []
    gate_timeout: Optional[str] = None
    if stage.type == "gate" and stage.gate is not None:
        gate_approvers = list(stage.gate.approvers)
        gate_timeout = stage.gate.timeout

    return ExecutionPlanStage(
        stage_id=stage.id,
        name=stage.name,
        stage_type=stage.type,
        primary_artifact=primary_artifact,
        model=model,
        tools=tools,
        inputs=inputs,
        outputs=outputs,
        context_modules=context_modules,
        timeout=timeout,
        condition=stage.condition,
        depends_on=list(stage.depends_on),
        gate_approvers=gate_approvers,
        gate_timeout=gate_timeout,
    )


# ---------------------------------------------------------------------------
# Timeout estimation
# ---------------------------------------------------------------------------


def _estimate_timeout(
    batches: List[ExecutionBatch],
    raw_batches: List[Batch],
    stage_map: Dict[str, ExecutionPlanStage],
) -> int:
    """Estimate total wall-clock time for the workflow.

    Each batch contributes the maximum timeout of its stages (parallel
    execution).  Batches are summed sequentially to produce the estimate.

    Args:
        batches:    Populated ``ExecutionBatch`` instances.
        raw_batches: Original ``Batch`` objects from the DAG.
        stage_map:   Mapping of stage_id to ``ExecutionPlanStage``.

    Returns:
        Total estimated seconds.
    """
    total = 0
    for batch in batches:
        batch_max = 0
        for ps in batch.stages:
            stage_seconds = _parse_duration_seconds(ps.timeout or "")
            if stage_seconds > batch_max:
                batch_max = stage_seconds
        total += batch_max
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_plan(
    workflow: WorkflowDefinition,
    parameters: Dict[str, Any],
) -> ExecutionPlan:
    """Generate a complete ``ExecutionPlan`` for a workflow run.

    Steps performed:

    1. Apply cross-field schema defaults via :func:`apply_defaults`.
    2. Validate that all ``required=True`` parameters have been provided.
    3. Merge caller-supplied parameters with declared defaults.
    4. Build the dependency DAG via :func:`build_dag`.
    5. Run static expression validation via :func:`validate_expressions`.
    6. Compute parallel execution batches via :func:`compute_execution_batches`.
    7. Build ``ExecutionPlanStage`` for every stage in every batch.
    8. Estimate the total wall-clock timeout.

    Args:
        workflow:   A fully parsed ``WorkflowDefinition`` (Pydantic-validated).
        parameters: Caller-supplied parameter values.  May be a subset of the
                    declared parameters; missing non-required parameters receive
                    their declared defaults.

    Returns:
        A populated ``ExecutionPlan`` ready for display or execution.

    Raises:
        WorkflowValidationError: If any ``required=True`` parameter is absent
            from both *parameters* and the workflow's declared defaults.
        WorkflowValidationError: If ``build_dag`` detects an unknown
            ``depends_on`` reference.
        WorkflowCycleError:      If the dependency graph contains a cycle.
    """
    # Step 1: Apply cross-field defaults.
    workflow = apply_defaults(workflow)

    # Step 2 & 3: Validate required parameters and merge with defaults.
    declared = workflow.config.parameters
    merged_parameters: Dict[str, Any] = {}

    for param_name, param_def in declared.items():
        if param_name in parameters:
            merged_parameters[param_name] = parameters[param_name]
        elif param_def.default is not None:
            merged_parameters[param_name] = param_def.default
        elif param_def.required:
            raise WorkflowValidationError(
                f"Required parameter '{param_name}' was not provided and has no default."
            )
        # Non-required parameters without a default and not provided are omitted.

    # Also include any extra caller-supplied parameters not declared (pass through).
    for param_name, param_value in parameters.items():
        if param_name not in merged_parameters:
            merged_parameters[param_name] = param_value

    # Step 4: Build DAG (validates depends_on references and detects cycles).
    dag = build_dag(workflow)

    # Step 5: Static expression validation.
    validation = validate_expressions(workflow, dag)

    # Step 6: Compute execution batches.
    raw_batches: List[Batch] = compute_execution_batches(dag)

    # Build a quick lookup from stage_id to StageDefinition.
    stage_def_map: Dict[str, StageDefinition] = {
        stage.id: stage for stage in workflow.stages
    }

    # Step 7: Build ExecutionBatch / ExecutionPlanStage objects.
    plan_stage_map: Dict[str, ExecutionPlanStage] = {}
    execution_batches: List[ExecutionBatch] = []

    for raw_batch in raw_batches:
        plan_stages: List[ExecutionPlanStage] = []
        for stage_id in raw_batch.stage_ids:
            stage_def = stage_def_map[stage_id]
            plan_stage = _build_plan_stage(stage_def)
            plan_stage_map[stage_id] = plan_stage
            plan_stages.append(plan_stage)
        execution_batches.append(ExecutionBatch(index=raw_batch.index, stages=plan_stages))

    # Step 8: Estimate total timeout.
    estimated_seconds = _estimate_timeout(execution_batches, raw_batches, plan_stage_map)

    return ExecutionPlan(
        workflow_id=workflow.workflow.id,
        workflow_name=workflow.workflow.name,
        workflow_version=workflow.workflow.version,
        parameters=merged_parameters,
        batches=execution_batches,
        estimated_timeout_seconds=estimated_seconds,
        validation=validation,
    )


# ---------------------------------------------------------------------------
# Text formatter
# ---------------------------------------------------------------------------


def format_plan_text(plan: ExecutionPlan) -> str:
    """Render an ``ExecutionPlan`` as a human-readable string.

    Output format matches Schema Spec Section 4.2::

        Workflow: {name} v{version}
        Parameters: key=val, key=val

        Execution Plan:
          Batch 1 (parallel):
            [stage_id] Stage Name
              Agent: agent:researcher-v1 (opus)
              Tools: skill:web-search, skill:codebase-explorer
              Inputs: feature_name <- ${{ parameters.feature_name }}
              Outputs: research_summary, identified_risks
              Context: ctx:domain-knowledge
              Timeout: 30m

          Batch 2 (sequential after Batch 1):
            ...

        Estimated total time: Xh Ym

    Args:
        plan: A fully-populated ``ExecutionPlan``.

    Returns:
        Multi-line human-readable plan string.
    """
    lines: List[str] = []

    # --- Header ---
    lines.append(f"Workflow: {plan.workflow_name} v{plan.workflow_version}")

    if plan.parameters:
        param_parts = [f"{k}={v!r}" for k, v in sorted(plan.parameters.items())]
        lines.append(f"Parameters: {', '.join(param_parts)}")
    else:
        lines.append("Parameters: (none)")

    lines.append("")
    lines.append("Execution Plan:")

    # --- Batches ---
    total_batches = len(plan.batches)
    for batch in plan.batches:
        batch_num = batch.index + 1  # 1-based for display

        # Determine parallelism description.
        if len(batch.stages) > 1:
            parallel_label = "parallel"
        else:
            parallel_label = "sequential"

        if batch.index == 0:
            batch_header = f"  Batch {batch_num} ({parallel_label}):"
        else:
            prev_num = batch_num - 1
            batch_header = f"  Batch {batch_num} ({parallel_label} after Batch {prev_num}):"

        lines.append(batch_header)

        for ps in batch.stages:
            lines.append(f"    [{ps.stage_id}] {ps.name}")

            if ps.stage_type == "gate":
                lines.append(f"      Type: manual_approval")
                if ps.gate_approvers:
                    lines.append(f"      Approvers: {', '.join(ps.gate_approvers)}")
                if ps.gate_timeout:
                    lines.append(f"      Timeout: {ps.gate_timeout}")
            else:
                # Agent stage
                if ps.primary_artifact:
                    if ps.model:
                        lines.append(f"      Agent: {ps.primary_artifact} ({ps.model})")
                    else:
                        lines.append(f"      Agent: {ps.primary_artifact}")

                if ps.tools:
                    lines.append(f"      Tools: {', '.join(ps.tools)}")

                if ps.inputs:
                    input_parts = [
                        f"{name} <- {source}" for name, source in ps.inputs.items()
                    ]
                    lines.append(f"      Inputs: {', '.join(input_parts)}")

                if ps.outputs:
                    lines.append(f"      Outputs: {', '.join(ps.outputs)}")

                if ps.context_modules:
                    lines.append(f"      Context: {', '.join(ps.context_modules)}")

                if ps.condition:
                    lines.append(f"      Condition: {ps.condition}")

                if ps.timeout:
                    lines.append(f"      Timeout: {ps.timeout}")

        # Blank line between batches (except after the last).
        if batch.index < total_batches - 1:
            lines.append("")

    # --- Footer ---
    lines.append("")
    estimated_label = _format_seconds(plan.estimated_timeout_seconds)
    lines.append(f"Estimated total time: {estimated_label}")

    # --- Validation warnings / errors (if any) ---
    if plan.validation.errors or plan.validation.warnings:
        lines.append("")
        if plan.validation.errors:
            lines.append("Validation Errors:")
            for err in plan.validation.errors:
                lines.append(f"  [error] {err}")
        if plan.validation.warnings:
            lines.append("Validation Warnings:")
            for warn in plan.validation.warnings:
                lines.append(f"  [warn] {warn}")

    return "\n".join(lines)
