"""Pydantic v2 models for the SkillMeat Workflow Definition Language (SWDL).

This module defines the complete schema for workflow definitions that power
the SkillMeat Workflow Orchestration Engine. Workflows are declarative YAML
files describing multi-stage agent pipelines with typed I/O contracts,
dependency graphs, retry policies, and context bindings.

Design principles:
    - Declarative-first, YAML-native (models parse directly from YAML dicts)
    - Agent-centric (stages assign SkillMeat artifact roles, not generic nodes)
    - Contract-driven (every stage declares typed inputs and outputs)
    - Progressive complexity (minimal workflow is ~10 lines; advanced features
      layer on without breaking simple cases)
    - Round-trip fidelity (lossless YAML ↔ model ↔ Web UI visual composer)

See: docs/project_plans/design-specs/workflow-orchestration-schema-spec.md

Usage:
    >>> import yaml
    >>> from skillmeat.core.workflow.models import WorkflowDefinition
    >>>
    >>> with open("WORKFLOW.yaml") as f:
    ...     data = yaml.safe_load(f)
    >>>
    >>> workflow = WorkflowDefinition.model_validate(data)
    >>> print(workflow.workflow.name)
    "Ship a Feature (SDLC)"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Validation constants (mirrors pattern from memory_service.py)
# ---------------------------------------------------------------------------

VALID_ON_FAILURE_STAGE = {"halt", "continue", "skip_dependents"}
VALID_ON_STAGE_FAILURE_GLOBAL = {"halt", "continue", "rollback"}
VALID_HANDOFF_FORMATS = {"structured", "markdown", "raw"}
VALID_GATE_ON_TIMEOUT = {"halt", "auto_approve", "reject"}
VALID_STAGE_TYPES = {"agent", "gate", "fan_out"}
VALID_MEMORY_SCOPES = {"current"}  # Extensible: specific project IDs also allowed


# ---------------------------------------------------------------------------
# UI / Visual Composer Metadata
# ---------------------------------------------------------------------------


class UIMetadata(BaseModel):
    """Visual composer metadata for a single stage node.

    Used by the Web UI visual composer to position and style stage nodes.
    Ignored by the execution engine.

    Attributes:
        position: Canvas [x, y] coordinates for the node.
        color:    CSS hex color string (e.g. "#E8F5E9").
        icon:     Icon identifier string (e.g. "search", "rocket").
    """

    position: Optional[List[int]] = Field(
        default=None,
        description="Canvas [x, y] position for the visual composer node.",
    )
    color: Optional[str] = Field(
        default=None,
        description='CSS hex color for the node (e.g. "#E8F5E9").',
    )
    icon: Optional[str] = Field(
        default=None,
        description='Icon identifier string (e.g. "search", "rocket").',
    )


class WorkflowUIMetadata(BaseModel):
    """Visual composer metadata for the workflow canvas itself.

    Attributes:
        color: CSS hex color for the workflow card.
        icon:  Icon identifier for the workflow card.
    """

    color: Optional[str] = Field(
        default=None,
        description='CSS hex color for the workflow card (e.g. "#4A90D9").',
    )
    icon: Optional[str] = Field(
        default=None,
        description='Icon identifier for the workflow card (e.g. "rocket").',
    )


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


class RetryPolicy(BaseModel):
    """Per-stage or global retry configuration (Temporal-inspired).

    Controls how the engine retries a failed stage before giving up.

    Attributes:
        max_attempts:        Total attempts allowed (1 = no retry). Default: 2.
        initial_interval:    Duration string for the first retry delay. Default: "30s".
        backoff_multiplier:  Exponential backoff multiplier. Default: 2.0.
        max_interval:        Cap on retry delay regardless of backoff. Default: "5m".
        non_retryable_errors: Error type labels that should not be retried
                              (e.g. ["auth_failure", "rate_limit_exhausted"]).
    """

    max_attempts: int = Field(
        default=2,
        ge=1,
        description="Maximum number of execution attempts (1 = no retry).",
    )
    initial_interval: str = Field(
        default="30s",
        description='Initial retry delay as a duration string (e.g. "30s", "1m").',
    )
    backoff_multiplier: float = Field(
        default=2.0,
        gt=0,
        description="Exponential backoff multiplier applied between retries.",
    )
    max_interval: str = Field(
        default="5m",
        description='Maximum retry delay cap as a duration string (e.g. "5m", "1h").',
    )
    non_retryable_errors: List[str] = Field(
        default_factory=list,
        description="Error type labels that bypass retry (fail immediately).",
    )


class ErrorPolicy(BaseModel):
    """Stage-level error handling policy.

    Attributes:
        retry:      Optional retry configuration. Inherits global default when absent.
        on_failure: Behaviour when all retry attempts are exhausted.
                    "halt"            -- stop the workflow (default).
                    "continue"        -- mark stage failed, continue downstream.
                    "skip_dependents" -- mark stage and all dependents skipped.
        timeout:    Optional stage-level timeout as a duration string.
    """

    retry: Optional[RetryPolicy] = Field(
        default=None,
        description="Retry configuration. Inherits global default when absent.",
    )
    on_failure: str = Field(
        default="halt",
        description=(
            "Action when retries are exhausted: "
            '"halt" | "continue" | "skip_dependents".'
        ),
    )
    timeout: Optional[str] = Field(
        default=None,
        description='Stage execution timeout as a duration string (e.g. "30m", "2h").',
    )

    @field_validator("on_failure")
    @classmethod
    def validate_on_failure(cls, v: str) -> str:
        if v not in VALID_ON_FAILURE_STAGE:
            raise ValueError(
                f"on_failure must be one of {sorted(VALID_ON_FAILURE_STAGE)}, got {v!r}"
            )
        return v


class GlobalErrorPolicy(BaseModel):
    """Workflow-level default error handling policy.

    Provides default retry behaviour and the action to take when any stage
    fails (after its own error policy is exhausted).

    Attributes:
        default_retry:    Default RetryPolicy applied to all stages that do not
                          declare their own retry config.
        on_stage_failure: Global workflow action on stage failure.
                          "halt"     -- stop the workflow (default).
                          "continue" -- continue remaining independent stages.
                          "rollback" -- execute compensating actions (v2).
    """

    default_retry: Optional[RetryPolicy] = Field(
        default=None,
        description="Default retry policy applied to stages without explicit retry config.",
    )
    on_stage_failure: str = Field(
        default="halt",
        description=(
            "Global workflow action on stage failure: "
            '"halt" | "continue" | "rollback".'
        ),
    )

    @field_validator("on_stage_failure")
    @classmethod
    def validate_on_stage_failure(cls, v: str) -> str:
        if v not in VALID_ON_STAGE_FAILURE_GLOBAL:
            raise ValueError(
                f"on_stage_failure must be one of "
                f"{sorted(VALID_ON_STAGE_FAILURE_GLOBAL)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Role Assignment
# ---------------------------------------------------------------------------


class RoleAssignment(BaseModel):
    """Assignment of a SkillMeat artifact to a stage role.

    Attributes:
        artifact:     SkillMeat artifact reference in the form
                      "<type>:<name>" (e.g. "agent:researcher-v1").
        model:        Optional model preference override
                      (e.g. "opus", "sonnet").
        instructions: Optional stage-specific instructions appended to the
                      agent's base system prompt.
    """

    artifact: str = Field(
        description=(
            'SkillMeat artifact reference (e.g. "agent:researcher-v1", '
            '"skill:codebase-explorer").'
        ),
    )
    model: Optional[str] = Field(
        default=None,
        description='Model preference override (e.g. "opus", "sonnet", "haiku").',
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Stage-specific instructions appended to the agent's system prompt.",
    )


class StageRoles(BaseModel):
    """Role bindings for a stage.

    Attributes:
        primary: The main agent executing this stage.
        tools:   Supporting skill/MCP artifact references available to the
                 primary agent (e.g. ["skill:web-search", "mcp:github-api"]).
    """

    primary: RoleAssignment = Field(
        description="Primary agent executing this stage.",
    )
    tools: List[str] = Field(
        default_factory=list,
        description=(
            "Supporting artifact references available to the primary agent "
            '(e.g. "skill:web-search", "mcp:github-api").'
        ),
    )


# ---------------------------------------------------------------------------
# Input / Output Contracts
# ---------------------------------------------------------------------------


class InputContract(BaseModel):
    """Typed input declaration for a stage.

    Inputs are resolved from workflow parameters, prior stage outputs, or
    context bindings at plan time using the SWDL expression language.

    Attributes:
        type:        SWDL type string (e.g. "string", "boolean", "array<string>").
        source:      SWDL expression resolving the input value at runtime
                     (e.g. "${{ parameters.feature_name }}").
        required:    Whether the engine must resolve this input before execution.
        description: Human-readable description of the input.
    """

    type: str = Field(
        description='SWDL type string (e.g. "string", "boolean", "array<string>").',
    )
    source: Optional[str] = Field(
        default=None,
        description="SWDL expression resolving the value at runtime.",
    )
    required: bool = Field(
        default=True,
        description="Whether this input must be resolved before stage execution.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the input.",
    )


class OutputContract(BaseModel):
    """Typed output declaration for a stage.

    The engine validates that required outputs are present in stage results
    before allowing dependent stages to proceed.

    Attributes:
        type:        SWDL type string (e.g. "string", "array<string>").
        required:    Whether this output must be present after stage completion.
        description: Human-readable description of the output.
        default:     Fallback value used when the output is not produced and
                     required is False.
    """

    type: str = Field(
        description='SWDL type string (e.g. "string", "array<string>").',
    )
    required: bool = Field(
        default=True,
        description="Whether this output must be present after stage completion.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the output.",
    )
    default: Any = Field(
        default=None,
        description="Fallback value when the output is absent and required is False.",
    )


# ---------------------------------------------------------------------------
# Context Binding
# ---------------------------------------------------------------------------


class MemoryConfig(BaseModel):
    """Memory injection configuration for a stage or the workflow globally.

    Controls which memories from the SkillMeat Memory system are injected
    into the agent's context before execution.

    Attributes:
        project_scope:   Which project's memories to query. "current" targets
                         the active project; a specific project ID can also
                         be supplied.
        min_confidence:  Only inject memories at or above this confidence
                         threshold (0.0–1.0). Default: 0.7.
        categories:      Memory type filter (e.g. ["constraint", "decision"]).
                         Empty list means all categories.
        max_tokens:      Maximum token budget for injected memories. Default: 2000.
    """

    project_scope: str = Field(
        default="current",
        description=(
            'Project scope for memory queries: "current" or a specific project ID.'
        ),
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for injected memories (0.0–1.0).",
    )
    categories: List[str] = Field(
        default_factory=list,
        description=(
            'Memory category filter (e.g. ["constraint", "decision"]). '
            "Empty means all categories."
        ),
    )
    max_tokens: int = Field(
        default=2000,
        gt=0,
        description="Maximum token budget for memory injection.",
    )


class ContextBinding(BaseModel):
    """Stage-level context binding configuration.

    Specifies which SkillMeat Context Modules and memory items are injected
    into the stage's agent context before execution.

    Attributes:
        modules: List of Context Module references (e.g. "ctx:domain-knowledge").
        memory:  Optional memory injection config. When absent, no memory is injected.
    """

    modules: List[str] = Field(
        default_factory=list,
        description=(
            "Context Module references to inject "
            '(e.g. "ctx:domain-knowledge", "ctx:coding-standards").'
        ),
    )
    memory: Optional[MemoryConfig] = Field(
        default=None,
        description="Memory injection configuration. Absent means no memory injection.",
    )


class GlobalContextConfig(BaseModel):
    """Workflow-level global context configuration.

    Context bindings applied to all stages unless overridden at the stage level.

    Attributes:
        global_modules: Context Module references injected into every stage.
        memory:         Default memory injection config for all stages.
    """

    global_modules: List[str] = Field(
        default_factory=list,
        description="Context Module references injected into every stage globally.",
    )
    memory: Optional[MemoryConfig] = Field(
        default=None,
        description="Default memory injection configuration applied to all stages.",
    )


# ---------------------------------------------------------------------------
# Handoff Configuration
# ---------------------------------------------------------------------------


class HandoffConfig(BaseModel):
    """Configuration for how a stage's outputs are packaged for downstream stages.

    After a stage completes, its outputs are serialized according to this
    config and stored in the run state for dependent stages to consume.

    Attributes:
        format:          Serialization format for the stage outputs.
                         "structured" -- JSON-serialized dict (default).
                         "markdown"   -- rendered Markdown document.
                         "raw"        -- unprocessed agent output string.
        include_run_log: Whether to attach the stage execution log to the
                         handoff payload.
        summary_prompt:  Optional prompt that triggers a summarization pass,
                         condensing outputs for the next stage.
    """

    format: str = Field(
        default="structured",
        description=(
            'Output serialization format: "structured" | "markdown" | "raw".'
        ),
    )
    include_run_log: bool = Field(
        default=False,
        description="Whether to attach the stage execution log to the handoff.",
    )
    summary_prompt: Optional[str] = Field(
        default=None,
        description=(
            "Prompt that triggers a summarization pass condensing outputs "
            "for the downstream stage."
        ),
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in VALID_HANDOFF_FORMATS:
            raise ValueError(
                f"format must be one of {sorted(VALID_HANDOFF_FORMATS)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Approval Gate
# ---------------------------------------------------------------------------


class GateConfig(BaseModel):
    """Human-in-the-loop approval gate configuration.

    Used for stages with type "gate". The workflow pauses at the gate until
    a configured approver acts, or the timeout expires.

    Attributes:
        kind:       Gate kind. "manual_approval" is the only supported kind in v1.
        approvers:  List of approver identifiers (usernames).
        timeout:    How long to wait for approval before triggering on_timeout.
                    Default: "24h".
        on_timeout: Action when the gate times out without a response.
                    "halt"         -- fail the workflow (default).
                    "auto_approve" -- automatically approve and continue.
                    "reject"       -- automatically reject and halt.
        message:    Optional message displayed to approvers.
    """

    kind: str = Field(
        default="manual_approval",
        description='Gate kind. Currently supports "manual_approval".',
    )
    approvers: List[str] = Field(
        default_factory=list,
        description="List of approver usernames or identifiers.",
    )
    timeout: str = Field(
        default="24h",
        description='Approval timeout duration (e.g. "24h", "2h").',
    )
    on_timeout: str = Field(
        default="halt",
        description=(
            'Action when the gate times out: "halt" | "auto_approve" | "reject".'
        ),
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message displayed to approvers at the gate.",
    )

    @field_validator("on_timeout")
    @classmethod
    def validate_on_timeout(cls, v: str) -> str:
        if v not in VALID_GATE_ON_TIMEOUT:
            raise ValueError(
                f"on_timeout must be one of {sorted(VALID_GATE_ON_TIMEOUT)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Stage Definition
# ---------------------------------------------------------------------------


class StageDefinition(BaseModel):
    """A single stage in the workflow DAG.

    A stage is the atomic unit of work: it assigns an agent role, declares
    typed inputs/outputs, binds context, and specifies error handling.

    Stages without shared dependencies run in parallel (GitHub Actions pattern).
    The engine resolves execution batches via topological sort of ``depends_on``.

    Attributes:
        id:           Unique stage identifier within this workflow (kebab-case).
        name:         Human-readable display name.
        description:  Optional detailed description of the stage's purpose.
        depends_on:   IDs of stages that must complete before this stage runs.
                      Empty list means eligible for immediate / parallel execution.
        condition:    Optional SWDL expression; stage is skipped when it evaluates
                      to false (e.g. "${{ parameters.skip_review == false }}").
        type:         Stage execution type.
                      "agent"   -- executed by an agent role (default).
                      "gate"    -- human-in-the-loop approval pause.
                      "fan_out" -- dynamic parallel sub-stage spawning (v2).
        roles:        Agent role assignments. Required when type is "agent".
        inputs:       Named typed input declarations.
        outputs:      Named typed output declarations.
        context:      Stage-level context binding (merged with global context).
        error_policy: Stage-level error handling overriding global defaults.
        handoff:      Output packaging configuration for downstream stages.
        gate:         Gate configuration. Required when type is "gate".
        ui:           Visual composer metadata (ignored by execution engine).
    """

    id: str = Field(
        description="Unique stage identifier within this workflow (kebab-case recommended).",
    )
    name: str = Field(
        description="Human-readable stage display name.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of the stage's purpose.",
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description=(
            "IDs of stages that must complete before this stage can run. "
            "Empty means eligible for parallel execution."
        ),
    )
    condition: Optional[str] = Field(
        default=None,
        description=(
            "SWDL expression evaluated at runtime; stage is skipped when false. "
            'E.g. "${{ parameters.skip_review == false }}".'
        ),
    )
    type: str = Field(
        default="agent",
        description='Stage execution type: "agent" | "gate" | "fan_out".',
    )
    roles: Optional[StageRoles] = Field(
        default=None,
        description='Agent role assignments. Required when type is "agent".',
    )
    inputs: Dict[str, InputContract] = Field(
        default_factory=dict,
        description="Named typed input declarations for this stage.",
    )
    outputs: Dict[str, OutputContract] = Field(
        default_factory=dict,
        description="Named typed output declarations for this stage.",
    )
    context: Optional[ContextBinding] = Field(
        default=None,
        description="Stage-level context binding merged on top of global context.",
    )
    error_policy: Optional[ErrorPolicy] = Field(
        default=None,
        description="Stage-level error handling overriding global error_policy defaults.",
    )
    handoff: Optional[HandoffConfig] = Field(
        default=None,
        description="Output packaging configuration for downstream stages.",
    )
    gate: Optional[GateConfig] = Field(
        default=None,
        description='Gate configuration. Required when type is "gate".',
    )
    ui: Optional[UIMetadata] = Field(
        default=None,
        description="Visual composer metadata (ignored by the execution engine).",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_STAGE_TYPES:
            raise ValueError(
                f"type must be one of {sorted(VALID_STAGE_TYPES)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Workflow-Level Configuration
# ---------------------------------------------------------------------------


class WorkflowParameter(BaseModel):
    """A runtime parameter declaration for the workflow.

    Parameters are provided by the caller at execution time (via CLI flags or
    API request body) and referenced within the workflow via
    ``${{ parameters.<name> }}``.

    Attributes:
        type:        SWDL type string (e.g. "string", "boolean", "integer").
        required:    Whether the caller must supply this parameter. Default: False.
        default:     Default value used when the caller does not supply the parameter.
        description: Human-readable description shown in the execution plan.
    """

    type: str = Field(
        description='SWDL type string for this parameter (e.g. "string", "boolean").',
    )
    required: bool = Field(
        default=False,
        description="Whether the caller must supply this parameter at execution time.",
    )
    default: Any = Field(
        default=None,
        description="Default value when the parameter is not supplied by the caller.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description displayed in the execution plan.",
    )


class WorkflowConfig(BaseModel):
    """Global workflow execution configuration.

    Attributes:
        parameters: Named parameter declarations overridable at execution time.
        timeout:    Maximum wall-clock time for the entire workflow run.
                    Default: "2h".
        env:        Global environment variables available to all stages.
    """

    parameters: Dict[str, WorkflowParameter] = Field(
        default_factory=dict,
        description="Named runtime parameter declarations.",
    )
    timeout: str = Field(
        default="2h",
        description='Maximum wall-clock time for the entire workflow (e.g. "2h", "6h").',
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Global environment variables available to all stages.",
    )


# ---------------------------------------------------------------------------
# Lifecycle Hooks
# ---------------------------------------------------------------------------


class WorkflowHooks(BaseModel):
    """Lifecycle callback hooks for the workflow.

    Each hook is an arbitrary dict whose structure is interpreted by the
    execution engine (e.g. ``{"notify": "slack:#deployments"}`` or
    ``{"run": "skillmeat memory capture ..."}``).

    Attributes:
        on_start:    Hook executed when the workflow starts.
        on_complete: Hook executed when the workflow completes successfully.
        on_failure:  Hook executed when the workflow fails.
    """

    on_start: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Hook payload executed when the workflow starts.",
    )
    on_complete: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Hook payload executed when the workflow completes successfully.",
    )
    on_failure: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Hook payload executed when the workflow fails.",
    )


# ---------------------------------------------------------------------------
# Workflow Metadata
# ---------------------------------------------------------------------------


class WorkflowMetadata(BaseModel):
    """Top-level identifying metadata for a workflow definition.

    Attributes:
        id:          Unique workflow identifier (kebab-case, e.g. "sdlc-feature-ship").
        name:        Human-readable display name.
        version:     SemVer string (e.g. "1.0.0"). Default: "1.0.0".
        description: Optional multi-line description of the workflow's purpose.
        author:      Optional author identifier.
        tags:        Searchable tag list.
        ui:          Optional visual composer metadata for the workflow card.
    """

    id: str = Field(
        description="Unique workflow identifier (kebab-case, e.g. \"sdlc-feature-ship\").",
    )
    name: str = Field(
        description="Human-readable display name for the workflow.",
    )
    version: str = Field(
        default="1.0.0",
        description='SemVer version string (e.g. "1.0.0").',
    )
    description: Optional[str] = Field(
        default=None,
        description="Multi-line description of the workflow's purpose.",
    )
    author: Optional[str] = Field(
        default=None,
        description="Workflow author identifier.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description='Searchable tags (e.g. ["sdlc", "feature", "full-stack"]).',
    )
    ui: Optional[WorkflowUIMetadata] = Field(
        default=None,
        description="Visual composer metadata for the workflow card.",
    )


# ---------------------------------------------------------------------------
# Top-Level Workflow Definition
# ---------------------------------------------------------------------------


class WorkflowDefinition(BaseModel):
    """Top-level model for a SkillMeat Workflow Definition Language (SWDL) file.

    This is the root model that maps directly to the contents of a
    ``WORKFLOW.yaml`` file. Validate an entire workflow with::

        workflow = WorkflowDefinition.model_validate(yaml.safe_load(text))

    Attributes:
        workflow:     Identifying metadata (id, name, version, tags, ui).
        config:       Global execution config (parameters, timeout, env).
        context:      Workflow-wide context bindings (modules, memory).
        stages:       Ordered list of stage definitions forming the DAG.
        error_policy: Global error handling defaults.
        hooks:        Lifecycle callback hooks (on_start, on_complete, on_failure).

    Configuration:
        ``populate_by_name=True`` allows field population by field name in
        addition to aliases.
        ``extra="allow"`` permits forward-compatible unknown fields so that
        future SWDL versions can add top-level keys without breaking older
        parser versions.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    workflow: WorkflowMetadata = Field(
        description="Identifying metadata for this workflow definition.",
    )
    config: WorkflowConfig = Field(
        default_factory=WorkflowConfig,
        description="Global execution configuration (parameters, timeout, env).",
    )
    context: Optional[GlobalContextConfig] = Field(
        default=None,
        description="Workflow-wide context bindings injected into all stages.",
    )
    stages: List[StageDefinition] = Field(
        default_factory=list,
        description="Ordered list of stage definitions forming the execution DAG.",
    )
    error_policy: Optional[GlobalErrorPolicy] = Field(
        default=None,
        description="Global error handling defaults applied to all stages.",
    )
    hooks: Optional[WorkflowHooks] = Field(
        default=None,
        description="Lifecycle callback hooks executed at workflow milestones.",
    )
