"""Schema defaults application for SkillMeat Workflow Definition Language (SWDL).

This module provides :func:`apply_defaults`, which fills in cross-field and
conditional default values that Pydantic field defaults cannot express on their
own (e.g. "stage timeout depends on stage type", "inherit global retry when
stage has no error_policy").

All transformations are **pure** and **immutable**: every modification produces
a new model instance via ``model_copy(update={...})`` rather than mutating the
input. The function therefore satisfies the roundtrip guarantee::

    apply_defaults(parse_workflow(path))

serialised back to a dict and re-parsed must produce an identical model.

Design rules
------------
1. Never mutate input models — always use ``model_copy``.
2. Only fill in ``None`` / absent values — never overwrite explicit user values.
3. Produce models that pass ``WorkflowDefinition.model_validate`` unchanged.
"""

from __future__ import annotations

from typing import Dict

from skillmeat.core.workflow.models import (
    ErrorPolicy,
    GateConfig,
    GlobalErrorPolicy,
    HandoffConfig,
    RetryPolicy,
    StageDefinition,
    WorkflowDefinition,
)

# ---------------------------------------------------------------------------
# Module-level default constants
# ---------------------------------------------------------------------------

#: Default workflow-level timeout when none is specified.
DEFAULT_WORKFLOW_TIMEOUT = "2h"

#: Default stage timeout for agent-type stages.
DEFAULT_AGENT_STAGE_TIMEOUT = "30m"

#: Default stage timeout for gate-type stages.
DEFAULT_GATE_STAGE_TIMEOUT = "24h"

#: Default retry policy applied when a stage has an error_policy but no retry.
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    initial_interval="30s",
    backoff_multiplier=2.0,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_retry_defaults(retry: RetryPolicy) -> RetryPolicy:
    """Fill missing fields on an existing RetryPolicy.

    Currently only ``max_attempts`` can be absent in a user-supplied retry
    block (the SWDL schema requires it but older documents may omit it).
    All other fields already have Pydantic defaults that are always present
    after parsing.

    Args:
        retry: A parsed :class:`RetryPolicy` instance.

    Returns:
        A new :class:`RetryPolicy` with ``max_attempts`` guaranteed to be set.
    """
    if retry.max_attempts is None:
        return retry.model_copy(update={"max_attempts": DEFAULT_RETRY_POLICY.max_attempts})
    return retry


def _resolve_stage_retry(
    stage_error_policy: ErrorPolicy,
    global_error_policy: GlobalErrorPolicy | None,
) -> RetryPolicy | None:
    """Determine the effective retry policy for a stage's error_policy.

    Priority:
    1. Stage's own ``retry`` (user-explicit) — returned as-is after field
       defaults are applied.
    2. Global ``default_retry`` — copied into the stage.
    3. Module-level ``DEFAULT_RETRY_POLICY`` — when ``error_policy`` is
       present but neither the stage nor the global provides a retry config.

    Args:
        stage_error_policy: The stage's parsed :class:`ErrorPolicy`.
        global_error_policy: The workflow-level :class:`GlobalErrorPolicy`,
            or ``None`` when absent.

    Returns:
        The resolved :class:`RetryPolicy` to use.
    """
    if stage_error_policy.retry is not None:
        # Stage has explicit retry — apply field-level defaults only.
        return _apply_retry_defaults(stage_error_policy.retry)

    # Inherit from global default_retry when available.
    if global_error_policy is not None and global_error_policy.default_retry is not None:
        return _apply_retry_defaults(global_error_policy.default_retry)

    # Fall back to the module default retry.
    return DEFAULT_RETRY_POLICY


def _apply_error_policy_defaults(
    error_policy: ErrorPolicy,
    stage_type: str,
    global_error_policy: GlobalErrorPolicy | None,
) -> ErrorPolicy:
    """Fill cross-field defaults into an existing ErrorPolicy.

    Handles:
    - ``retry``: resolved from stage, global, or module default.
    - ``timeout``: set based on stage type when absent.
    - ``on_failure``: already defaulted by Pydantic to ``"halt"``; untouched.

    Args:
        error_policy:        The stage's existing :class:`ErrorPolicy`.
        stage_type:          The stage execution type (``"agent"`` or
                             ``"gate"``).
        global_error_policy: The workflow-level :class:`GlobalErrorPolicy`.

    Returns:
        A new :class:`ErrorPolicy` with defaults applied.
    """
    updates: Dict = {}

    # --- retry ---
    resolved_retry = _resolve_stage_retry(error_policy, global_error_policy)
    if resolved_retry is not error_policy.retry:
        updates["retry"] = resolved_retry

    # --- timeout ---
    if error_policy.timeout is None:
        updates["timeout"] = (
            DEFAULT_GATE_STAGE_TIMEOUT
            if stage_type == "gate"
            else DEFAULT_AGENT_STAGE_TIMEOUT
        )

    if updates:
        return error_policy.model_copy(update=updates)
    return error_policy


def _build_default_error_policy(
    stage_type: str,
    global_error_policy: GlobalErrorPolicy | None,
) -> ErrorPolicy:
    """Construct a default ErrorPolicy for a stage that has none.

    Inherits the global ``default_retry`` when available, otherwise uses the
    module-level :data:`DEFAULT_RETRY_POLICY`.  The timeout is set based on
    stage type.

    Args:
        stage_type:          The stage execution type (``"agent"`` or
                             ``"gate"``).
        global_error_policy: The workflow-level :class:`GlobalErrorPolicy`.

    Returns:
        A new :class:`ErrorPolicy` appropriate for the stage type.
    """
    if global_error_policy is not None and global_error_policy.default_retry is not None:
        inherited_retry: RetryPolicy = _apply_retry_defaults(global_error_policy.default_retry)
    else:
        inherited_retry = DEFAULT_RETRY_POLICY

    timeout = (
        DEFAULT_GATE_STAGE_TIMEOUT if stage_type == "gate" else DEFAULT_AGENT_STAGE_TIMEOUT
    )

    return ErrorPolicy(
        retry=inherited_retry,
        on_failure="halt",
        timeout=timeout,
    )


def _apply_stage_defaults(
    stage: StageDefinition,
    global_error_policy: GlobalErrorPolicy | None,
) -> StageDefinition:
    """Apply all conditional and cross-field defaults to a single stage.

    Handles in order:
    1. ``error_policy`` — create or augment with timeout + retry defaults.
    2. ``handoff``      — add :class:`HandoffConfig` with defaults when absent.
    3. ``gate``         — add :class:`GateConfig` with defaults for gate stages.

    Args:
        stage:               The parsed :class:`StageDefinition`.
        global_error_policy: The workflow-level :class:`GlobalErrorPolicy`.

    Returns:
        A new :class:`StageDefinition` with defaults applied.
    """
    updates: Dict = {}

    # --- error_policy ---
    if stage.error_policy is None:
        updates["error_policy"] = _build_default_error_policy(
            stage.type, global_error_policy
        )
    else:
        new_error_policy = _apply_error_policy_defaults(
            stage.error_policy, stage.type, global_error_policy
        )
        if new_error_policy is not stage.error_policy:
            updates["error_policy"] = new_error_policy

    # --- handoff ---
    if stage.handoff is None:
        updates["handoff"] = HandoffConfig(format="structured", include_run_log=False)

    # --- gate ---
    if stage.type == "gate" and stage.gate is None:
        updates["gate"] = GateConfig()

    if updates:
        return stage.model_copy(update=updates)
    return stage


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_defaults(workflow: WorkflowDefinition) -> WorkflowDefinition:
    """Apply cross-field and conditional schema defaults to a parsed workflow.

    Pydantic field defaults handle simple scalar defaults at parse time.  This
    function handles the remaining cases that require knowledge of sibling or
    parent field values:

    - **Workflow timeout**: Ensures ``config.timeout`` is set.  Because
      :class:`WorkflowConfig` already has ``default="2h"``, this is always
      present after parsing; the function documents and asserts the invariant
      without overwriting the field.

    - **Stage error policy**: When a stage has no ``error_policy``, one is
      synthesised that inherits the global ``default_retry`` (if any) and sets
      a type-appropriate timeout (``"30m"`` for agent stages, ``"24h"`` for
      gate stages).  When a stage *has* an error_policy but is missing
      ``retry``, a default retry is added.  Stage-level ``timeout`` is also
      filled based on stage type when absent.

    - **Stage handoff**: All stages receive a :class:`HandoffConfig` with
      ``format="structured"`` and ``include_run_log=False`` when absent.

    - **Gate config**: Stages with ``type="gate"`` receive a default
      :class:`GateConfig` when one is not explicitly provided.

    The function is **pure and immutable**: it never mutates the input and
    always returns a new :class:`WorkflowDefinition` instance.  Re-parsing the
    serialised output must produce an identical model (roundtrip guarantee).

    Args:
        workflow: A fully parsed :class:`WorkflowDefinition` instance.

    Returns:
        A new :class:`WorkflowDefinition` with all defaults applied.

    Example::

        import yaml
        from skillmeat.core.workflow import WorkflowDefinition, apply_defaults

        with open("WORKFLOW.yaml") as f:
            data = yaml.safe_load(f)

        raw_workflow = WorkflowDefinition.model_validate(data)
        workflow = apply_defaults(raw_workflow)
    """
    global_error_policy = workflow.error_policy

    # --- Apply defaults to each stage ---
    new_stages = [
        _apply_stage_defaults(stage, global_error_policy)
        for stage in workflow.stages
    ]

    # Only rebuild if at least one stage changed.
    stages_changed = any(
        new_stage is not orig_stage
        for new_stage, orig_stage in zip(new_stages, workflow.stages)
    )

    if stages_changed:
        return workflow.model_copy(update={"stages": new_stages})
    return workflow
