/**
 * Workflow Orchestration Types for SkillMeat
 *
 * TypeScript types for the Workflow Orchestration feature, derived from
 * backend Pydantic schemas in:
 *   - skillmeat/api/schemas/workflow.py
 *   - skillmeat/core/workflow/models.py
 *
 * These types cover:
 *   - Workflow definitions (SWDL) and their stages
 *   - Execution lifecycle and per-step state
 *   - Validation results and execution plan previews
 *   - API request/response shapes
 *   - Filter/query parameter types for list endpoints
 *
 * @version 1.0.0
 */

// ============================================================================
// Enums
// ============================================================================

/**
 * Lifecycle status for a workflow definition.
 *
 * - draft:      Work-in-progress; not yet ready to execute.
 * - active:     Production-ready and eligible for execution.
 * - archived:   Retired; preserved for reference but not executable.
 * - deprecated: Superseded by another workflow; execution may still work
 *               but is discouraged.
 */
export type WorkflowStatus = 'draft' | 'active' | 'archived' | 'deprecated';

/**
 * Lifecycle status for a single workflow execution run.
 *
 * - pending:              Queued; not yet started.
 * - running:              Actively executing one or more stages.
 * - completed:            All stages finished successfully.
 * - failed:               One or more stages failed with no recovery.
 * - cancelled:            Execution was manually cancelled.
 * - paused:               Execution is temporarily suspended.
 * - waiting_for_approval: Paused at a gate stage awaiting human sign-off.
 */
export type ExecutionStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused'
  | 'waiting_for_approval';

/**
 * Parallelism mode for a workflow or stage group.
 *
 * - sequential: Stages run one after another in dependency order.
 * - parallel:   Independent stages (no shared depends_on) run concurrently.
 */
export type ExecutionMode = 'sequential' | 'parallel';

/**
 * Action taken when a stage exhausts all retry attempts.
 *
 * - halt:           Stop the entire workflow immediately (default).
 * - continue:       Mark the stage failed and continue downstream stages.
 * - retry_then_halt: Retry up to max_retries, then halt. Alias for the
 *                    most common retry-with-halt pattern.
 */
export type FailureAction = 'halt' | 'continue' | 'retry_then_halt';

/**
 * Execution type for a workflow stage.
 *
 * Maps to SWDL ``type`` field on StageDefinition.
 *
 * - standard:   Agent-driven stage (SWDL: "agent").
 * - gate:       Human-in-the-loop approval pause (SWDL: "gate").
 * - checkpoint: Fan-out or dynamic parallel sub-stage spawning (SWDL: "fan_out").
 *
 * Note: The backend uses "agent" | "gate" | "fan_out" as raw strings.
 * These frontend aliases provide more descriptive vocabulary for the UI.
 * Use `stageTypeToRaw` / `rawToStageType` helpers for conversions.
 */
export type StageType = 'standard' | 'gate' | 'checkpoint';

/**
 * Raw stage type strings as stored in the backend / SWDL.
 * Use when communicating with the API directly.
 */
export type RawStageType = 'agent' | 'gate' | 'fan_out';

/**
 * What initiated a workflow execution.
 *
 * - manual:   User triggered via the web UI or CLI.
 * - api:      Triggered programmatically via the REST API.
 * - schedule: Triggered by a time-based schedule (future v2 feature).
 */
export type TriggerType = 'manual' | 'api' | 'schedule';

/**
 * Serialization format used when packaging stage outputs for downstream stages.
 *
 * Mirrors SWDL HandoffConfig.format values.
 *
 * - structured: JSON-serialized dict (default).
 * - markdown:   Rendered Markdown document.
 * - raw:        Unprocessed agent output string.
 */
export type HandoffFormat = 'structured' | 'markdown' | 'raw';

/**
 * Action taken when a gate stage times out without a response.
 *
 * - halt:         Fail the workflow (default).
 * - auto_approve: Automatically approve and continue.
 * - reject:       Automatically reject and halt.
 */
export type GateTimeoutAction = 'halt' | 'auto_approve' | 'reject';

// ============================================================================
// Stage type conversion helpers
// ============================================================================

/** Map frontend StageType to SWDL raw string. */
export const STAGE_TYPE_TO_RAW: Record<StageType, RawStageType> = {
  standard: 'agent',
  gate: 'gate',
  checkpoint: 'fan_out',
};

/** Map SWDL raw string to frontend StageType. */
export const RAW_TO_STAGE_TYPE: Record<RawStageType, StageType> = {
  agent: 'standard',
  gate: 'gate',
  fan_out: 'checkpoint',
};

/** Convert a SWDL raw stage type to the frontend StageType. Defaults to 'standard' for unknowns. */
export function rawToStageType(raw: string): StageType {
  return RAW_TO_STAGE_TYPE[raw as RawStageType] ?? 'standard';
}

/** Convert a frontend StageType to the SWDL raw string. */
export function stageTypeToRaw(type: StageType): RawStageType {
  return STAGE_TYPE_TO_RAW[type];
}

// ============================================================================
// Retry / Error Policy
// ============================================================================

/**
 * Per-stage or global retry configuration.
 *
 * Mirrors the backend RetryPolicy Pydantic model (core/workflow/models.py).
 */
export interface RetryPolicy {
  /** Maximum number of execution attempts (1 = no retry). Default: 2. */
  maxAttempts: number;
  /** First retry delay as a duration string (e.g. "30s", "1m"). Default: "30s". */
  initialInterval: string;
  /** Exponential backoff multiplier between retries. Default: 2.0. */
  backoffMultiplier: number;
  /** Cap on retry delay regardless of backoff (e.g. "5m", "1h"). Default: "5m". */
  maxInterval: string;
  /** Error type labels that skip retry and fail immediately. */
  nonRetryableErrors: string[];
}

/**
 * Stage-level error handling policy.
 *
 * Mirrors the backend ErrorPolicy Pydantic model (core/workflow/models.py).
 */
export interface ErrorPolicy {
  /** Retry configuration; inherits global default when absent. */
  retry?: RetryPolicy;
  /** Action when retries are exhausted: "halt" | "continue" | "skip_dependents". */
  onFailure: 'halt' | 'continue' | 'skip_dependents';
  /** Stage execution timeout as a duration string (e.g. "30m", "2h"). */
  timeout?: string;
}

/**
 * Workflow-level default error handling policy.
 *
 * Mirrors the backend GlobalErrorPolicy Pydantic model (core/workflow/models.py).
 */
export interface GlobalErrorPolicy {
  /** Default retry policy for stages without explicit retry config. */
  defaultRetry?: RetryPolicy;
  /** Global workflow action on stage failure: "halt" | "continue" | "rollback". */
  onStageFailure: 'halt' | 'continue' | 'rollback';
}

// ============================================================================
// Role Assignment
// ============================================================================

/**
 * Assignment of a SkillMeat artifact to a stage role.
 *
 * Mirrors the backend RoleAssignment Pydantic model (core/workflow/models.py).
 */
export interface RoleAssignment {
  /**
   * SkillMeat artifact reference in "type:name" format.
   * E.g. "agent:researcher-v1", "skill:codebase-explorer".
   */
  artifact: string;
  /** Model preference override (e.g. "opus", "sonnet", "haiku"). */
  model?: string;
  /** Stage-specific instructions appended to the agent's base system prompt. */
  instructions?: string;
}

/**
 * Role bindings for a stage.
 *
 * Mirrors the backend StageRoles Pydantic model (core/workflow/models.py).
 */
export interface StageRoles {
  /** Primary agent executing this stage. */
  primary: RoleAssignment;
  /**
   * Supporting artifact references available to the primary agent.
   * E.g. ["skill:web-search", "mcp:github-api"].
   */
  tools: string[];
}

// ============================================================================
// Input / Output Contracts
// ============================================================================

/**
 * Typed input declaration for a stage.
 *
 * Mirrors the backend InputContract Pydantic model (core/workflow/models.py).
 */
export interface InputContract {
  /** SWDL type string (e.g. "string", "boolean", "array<string>"). */
  type: string;
  /** SWDL expression resolving the value at runtime (e.g. "${{ parameters.feature_name }}"). */
  source?: string;
  /** Whether this input must be resolved before stage execution. Default: true. */
  required: boolean;
  /** Human-readable description of the input. */
  description?: string;
}

/**
 * Typed output declaration for a stage.
 *
 * Mirrors the backend OutputContract Pydantic model (core/workflow/models.py).
 */
export interface OutputContract {
  /** SWDL type string (e.g. "string", "array<string>"). */
  type: string;
  /** Whether this output must be present after stage completion. Default: true. */
  required: boolean;
  /** Human-readable description of the output. */
  description?: string;
  /** Fallback value when the output is absent and required is false. */
  default?: unknown;
}

// ============================================================================
// Context Binding
// ============================================================================

/**
 * Memory injection configuration for a stage or the workflow globally.
 *
 * Mirrors the backend MemoryConfig Pydantic model (core/workflow/models.py).
 */
export interface MemoryConfig {
  /** Project scope for memory queries. "current" targets the active project. */
  projectScope: string;
  /** Only inject memories at or above this confidence threshold (0.0–1.0). Default: 0.7. */
  minConfidence: number;
  /** Memory type filter (e.g. ["constraint", "decision"]). Empty means all. */
  categories: string[];
  /** Maximum token budget for injected memories. Default: 2000. */
  maxTokens: number;
}

/**
 * Stage-level context binding configuration.
 *
 * Mirrors the backend ContextBinding Pydantic model (core/workflow/models.py).
 */
export interface ContextBinding {
  /**
   * Context Module references to inject into the stage's agent context.
   * E.g. "ctx:domain-knowledge", "ctx:coding-standards".
   */
  modules: string[];
  /** Memory injection configuration. Absent means no memory injection. */
  memory?: MemoryConfig;
}

/**
 * Workflow-level global context configuration.
 *
 * Mirrors the backend GlobalContextConfig Pydantic model (core/workflow/models.py).
 */
export interface GlobalContextConfig {
  /** Context Module references injected into every stage. */
  globalModules: string[];
  /** Default memory injection configuration applied to all stages. */
  memory?: MemoryConfig;
}

/**
 * Simplified context policy used in WorkflowStage for UI consumers that
 * do not need the full SWDL ContextBinding structure.
 */
export interface ContextPolicy {
  /** Module reference strings (e.g. "ctx:domain-knowledge"). */
  modules: string[];
  /** Whether to inherit the global workflow context config. */
  inheritGlobal: boolean;
}

// ============================================================================
// Handoff and Gate Config
// ============================================================================

/**
 * Configuration for packaging a stage's outputs for downstream stages.
 *
 * Mirrors the backend HandoffConfig Pydantic model (core/workflow/models.py).
 */
export interface HandoffConfig {
  /** Output serialization format. Default: "structured". */
  format: HandoffFormat;
  /** Whether to attach the stage execution log to the handoff. Default: false. */
  includeRunLog: boolean;
  /** Optional prompt that triggers a summarization pass for downstream. */
  summaryPrompt?: string;
}

/**
 * Human-in-the-loop approval gate configuration.
 *
 * Mirrors the backend GateConfig Pydantic model (core/workflow/models.py).
 */
export interface GateConfig {
  /** Gate kind. Currently "manual_approval" only. */
  kind: string;
  /** Approver usernames or identifiers. */
  approvers: string[];
  /** How long to wait for approval before triggering onTimeout. Default: "24h". */
  timeout: string;
  /** Action when the gate times out. */
  onTimeout: GateTimeoutAction;
  /** Optional message displayed to approvers at the gate. */
  message?: string;
}

// ============================================================================
// UI Metadata
// ============================================================================

/**
 * Visual composer metadata for a single stage node.
 *
 * Mirrors the backend UIMetadata Pydantic model (core/workflow/models.py).
 * Ignored by the execution engine — used only by the visual canvas.
 */
export interface StageUIMetadata {
  /** Canvas [x, y] position for the visual composer node. */
  position?: [number, number];
  /** CSS hex color for the node (e.g. "#E8F5E9"). */
  color?: string;
  /** Icon identifier string (e.g. "search", "rocket"). */
  icon?: string;
}

/**
 * Visual composer metadata for the workflow card itself.
 *
 * Mirrors the backend WorkflowUIMetadata Pydantic model (core/workflow/models.py).
 */
export interface WorkflowUIMetadata {
  /** CSS hex color for the workflow card (e.g. "#4A90D9"). */
  color?: string;
  /** Icon identifier for the workflow card (e.g. "rocket"). */
  icon?: string;
}

// ============================================================================
// Core Types — Stage
// ============================================================================

/**
 * A single stage within a workflow definition, as returned by the API.
 *
 * Derived from the backend StageResponse schema (api/schemas/workflow.py)
 * and the StageDefinition Pydantic model (core/workflow/models.py).
 *
 * This is the full, API-level stage representation. For lightweight list
 * display use WorkflowStage; for execution-time state use StageExecution.
 */
export interface WorkflowStage {
  /** DB primary key (uuid hex). */
  id: string;
  /** Stage identifier from the SWDL definition (kebab-case). Unique within the workflow. */
  stageIdRef: string;
  /** Human-readable stage display name. */
  name: string;
  /** Detailed description of the stage's purpose. */
  description?: string;
  /** Positional index within the workflow (0-based). */
  orderIndex: number;
  /**
   * Stage execution type.
   * Raw value from backend: "agent" | "gate" | "fan_out".
   * Use rawToStageType() to convert to the StageType alias.
   */
  stageType: RawStageType;
  /** SWDL expression; stage is skipped when it evaluates to false. */
  condition?: string;
  /** Stage IDs that must complete before this stage can run. */
  dependsOn: string[];
  /** Agent role assignments. Present when stageType is "agent". */
  roles?: StageRoles;
  /** Named typed input declarations. */
  inputs: Record<string, InputContract>;
  /** Named typed output declarations. */
  outputs: Record<string, OutputContract>;
  /** Stage-level context binding (merged with global context). */
  context?: ContextBinding;
  /** Stage-level error handling (overrides global defaults). */
  errorPolicy?: ErrorPolicy;
  /** Output packaging configuration for downstream stages. */
  handoff?: HandoffConfig;
  /** Gate configuration. Present when stageType is "gate". */
  gate?: GateConfig;
  /** Visual composer metadata (ignored by the execution engine). */
  ui?: StageUIMetadata;
}

// ============================================================================
// Core Types — Workflow Parameter
// ============================================================================

/**
 * A runtime parameter declaration for the workflow.
 *
 * Parameters are supplied by the caller at execution time and referenced
 * in the SWDL via ${{ parameters.<name> }}.
 *
 * Mirrors the backend WorkflowParameter Pydantic model (core/workflow/models.py).
 */
export interface WorkflowParameter {
  /** SWDL type string (e.g. "string", "boolean", "integer"). */
  type: string;
  /** Whether the caller must supply this parameter. Default: false. */
  required: boolean;
  /** Default value used when the caller does not supply the parameter. */
  defaultValue?: unknown;
  /** Human-readable description shown in the execution plan. */
  description?: string;
}

// ============================================================================
// Core Types — Workflow
// ============================================================================

/**
 * Full workflow definition as returned by GET /api/v1/workflows/{id}.
 *
 * Derives from the backend WorkflowResponse schema (api/schemas/workflow.py).
 */
export interface Workflow {
  /** DB primary key (uuid hex). */
  id: string;
  /** Unique workflow identifier from the SWDL definition (kebab-case). */
  uuid: string;
  /** Human-readable display name. */
  name: string;
  /** Multi-line description of the workflow's purpose. */
  description?: string;
  /** SemVer string (e.g. "1.0.0"). */
  version: string;
  /** Lifecycle status of the workflow definition. */
  status: WorkflowStatus;
  /** Raw YAML workflow definition string (SWDL). */
  definition: string;
  /** Searchable tag list. */
  tags: string[];
  /** Ordered list of stage definitions. */
  stages: WorkflowStage[];
  /**
   * Named parameter declarations.
   * Keys are parameter names; values are WorkflowParameter descriptors.
   */
  parameters: Record<string, WorkflowParameter>;
  /** Workflow-wide context configuration. */
  contextPolicy?: GlobalContextConfig;
  /** Global error handling defaults. */
  errorPolicy?: GlobalErrorPolicy;
  /** Visual composer metadata for the workflow card. */
  ui?: WorkflowUIMetadata;
  /** Optional project identifier scoping this workflow. */
  projectId?: string;
  /** ISO 8601 timestamp when the workflow was created. */
  createdAt: string;
  /** ISO 8601 timestamp of the last update. */
  updatedAt: string;
}

// ============================================================================
// Execution Types — Step (per-stage)
// ============================================================================

/**
 * Runtime state for a single stage within a workflow execution.
 *
 * Derives from the backend ExecutionStepResponse schema (api/schemas/workflow.py).
 */
export interface StageExecution {
  /** DB primary key (uuid hex). */
  id: string;
  /** Stage identifier (kebab-case) from the SWDL definition. */
  stageId: string;
  /** Human-readable stage name. */
  stageName: string;
  /**
   * Stage execution type.
   * Raw value from backend: "agent" | "gate" | "fan_out".
   */
  stageType: RawStageType;
  /** Parallel batch index from the execution plan (0-based). */
  batchIndex: number;
  /** Step lifecycle status. */
  status: ExecutionStatus;
  /** ISO 8601 timestamp when the step began executing. */
  startedAt?: string;
  /** ISO 8601 timestamp when the step finished. */
  completedAt?: string;
  /**
   * Duration in milliseconds.
   * Derived from startedAt/completedAt — not in the API response directly.
   * Compute client-side when both timestamps are present.
   */
  durationMs?: number;
  /** Agent artifact reference used for this step (e.g. "agent:researcher-v1"). */
  agentUsed?: string;
  /** Execution log lines for this step. */
  logs: string[];
  /** Structured outputs produced by this step. */
  outputs: Record<string, unknown>;
  /** Error description when the step failed. */
  errorMessage?: string;
}

// ============================================================================
// Execution Types — Workflow Execution
// ============================================================================

/**
 * Full workflow execution as returned by GET /api/v1/workflow-executions/{id}.
 *
 * Derives from the backend ExecutionResponse schema (api/schemas/workflow.py).
 */
export interface WorkflowExecution {
  /** DB primary key (uuid hex). */
  id: string;
  /** Parent workflow primary key (uuid hex). */
  workflowId: string;
  /** Human-readable workflow display name (denormalized for UI convenience). */
  workflowName?: string;
  /** Execution lifecycle status. */
  status: ExecutionStatus;
  /** What triggered this execution. */
  trigger: TriggerType;
  /** Resolved parameter dict (merged caller-supplied values + workflow defaults). */
  parameters?: Record<string, unknown>;
  /** ISO 8601 timestamp when execution began. */
  startedAt?: string;
  /** ISO 8601 timestamp when execution finished. */
  completedAt?: string;
  /** Duration in milliseconds (derived or provided by server). */
  durationMs?: number;
  /** Ordered list of per-stage execution step states. */
  stages: StageExecution[];
  /** Index of the currently active stage (0-based). -1 when none active. */
  currentStageIndex: number;
  /** Execution progress percentage (0–100). */
  progressPct: number;
  /** Top-level error description when the execution failed. */
  errorMessage?: string;
}

// ============================================================================
// Validation Types
// ============================================================================

/**
 * A single validation error or warning from the multi-pass validator.
 *
 * Derives from the backend ValidationIssueResponse schema (api/schemas/workflow.py).
 */
export interface ValidationIssue {
  /**
   * Validation category.
   * "schema" | "dag" | "expression" | "artifact"
   */
  category: 'schema' | 'dag' | 'expression' | 'artifact';
  /** Human-readable description of the issue. */
  message: string;
  /** Stage identifier where the issue was found. */
  stageId?: string;
  /** Specific field path where the issue was found. */
  field?: string;
}

/**
 * Result of a full multi-pass workflow validation.
 *
 * Derives from the backend ValidationResultResponse schema (api/schemas/workflow.py).
 */
export interface ValidationResult {
  /** True when no blocking errors were found. */
  isValid: boolean;
  /** Blocking validation issues that prevent execution. */
  errors: ValidationIssue[];
  /** Non-blocking warnings (execution can proceed). */
  warnings: ValidationIssue[];
}

// ============================================================================
// Execution Plan Types
// ============================================================================

/**
 * A single stage entry within an execution plan batch.
 *
 * Derives from the backend ExecutionPlanStageResponse schema (api/schemas/workflow.py).
 */
export interface ExecutionPlanStage {
  /** Stage identifier (kebab-case). */
  stageId: string;
  /** Human-readable stage name. */
  stageName: string;
  /** Stage execution type (raw SWDL value). */
  stageType: RawStageType;
  /** Primary agent artifact reference, or undefined if not an agent stage. */
  agent?: string;
  /** Estimated execution time in seconds. */
  estimatedDurationSeconds?: number;
}

/**
 * A parallel execution batch within an execution plan.
 *
 * Derives from the backend ExecutionPlanBatchResponse schema (api/schemas/workflow.py).
 * All stages within a batch can run concurrently.
 */
export interface ExecutionPlanBatch {
  /** 0-based index of this batch in the execution order. */
  batchIndex: number;
  /** Stages that can execute concurrently within this batch. */
  stages: ExecutionPlanStage[];
}

/**
 * Complete static execution plan for a workflow.
 *
 * Derives from the backend ExecutionPlanResponse schema (api/schemas/workflow.py).
 * Useful for pre-execution visualization and estimating total runtime.
 */
export interface ExecutionPlan {
  /** DB primary key of the planned workflow. */
  workflowId: string;
  /** Total number of stages across all batches. */
  totalStages: number;
  /** Number of parallel execution batches. */
  totalBatches: number;
  /** Ordered list of execution batches. */
  batches: ExecutionPlanBatch[];
  /** Rough sequential timeout estimate in seconds. */
  estimatedTotalSeconds?: number;
}

// ============================================================================
// Request Types
// ============================================================================

/**
 * Request body for creating a new workflow definition.
 *
 * POST /api/v1/workflows
 *
 * Derives from the backend WorkflowCreateRequest schema (api/schemas/workflow.py).
 */
export interface CreateWorkflowRequest {
  /** Raw YAML workflow definition string (SWDL). */
  yamlContent: string;
  /** Optional project identifier to scope the workflow. */
  projectId?: string;
}

/**
 * Request body for replacing an existing workflow definition.
 *
 * PUT /api/v1/workflows/{id}
 *
 * Derives from the backend WorkflowUpdateRequest schema (api/schemas/workflow.py).
 */
export type UpdateWorkflowRequest = Partial<CreateWorkflowRequest>;

/**
 * Request body for duplicating a workflow definition.
 *
 * POST /api/v1/workflows/{id}/duplicate
 *
 * Derives from the backend WorkflowDuplicateRequest schema (api/schemas/workflow.py).
 */
export interface DuplicateWorkflowRequest {
  /** Display name for the copy. Defaults to "<original name> (copy)" when absent. */
  newName?: string;
}

/**
 * Optional request body for in-memory workflow validation.
 *
 * POST /api/v1/workflows/{id}/validate
 *
 * Derives from the backend WorkflowValidateRequest schema (api/schemas/workflow.py).
 */
export interface ValidateWorkflowRequest {
  /** Optional parameter values used during expression validation. */
  parameters?: Record<string, unknown>;
}

/**
 * Request body for generating a workflow execution plan preview.
 *
 * POST /api/v1/workflows/{id}/plan
 *
 * Derives from the backend WorkflowPlanRequest schema (api/schemas/workflow.py).
 */
export interface PlanWorkflowRequest {
  /** Optional parameter values merged with workflow defaults for planning. */
  parameters?: Record<string, unknown>;
}

/**
 * Request body for starting a new workflow execution.
 *
 * POST /api/v1/workflow-executions
 *
 * Derives from the backend ExecutionStartRequest schema (api/schemas/workflow.py).
 */
export interface RunWorkflowRequest {
  /** DB primary key of the workflow to execute. */
  workflowId: string;
  /** Optional parameter values merged with workflow defaults at runtime. */
  parameters?: Record<string, unknown>;
  /** Optional execution-level overrides (e.g. model overrides). */
  overrides?: Record<string, unknown>;
}

/**
 * Optional request body for rejecting a gate stage.
 *
 * POST /api/v1/workflow-executions/{id}/stages/{stage_id}/reject
 *
 * Derives from the backend GateRejectRequest schema (api/schemas/workflow.py).
 */
export interface GateRejectRequest {
  /** Human-readable explanation for the rejection. */
  reason?: string;
}

// ============================================================================
// Response Types
// ============================================================================

/**
 * Paginated list of workflow definitions.
 *
 * GET /api/v1/workflows
 *
 * Derives from the backend WorkflowListResponse schema (api/schemas/workflow.py).
 */
export interface WorkflowListResponse {
  /** List of workflow objects for the current page. */
  items: Workflow[];
  /** Total number of matching records before pagination. */
  total: number;
  /** Number of records skipped (offset). */
  skip: number;
  /** Maximum records returned in this page. */
  limit: number;
  /**
   * Opaque pagination cursor for the next page.
   * Undefined when there are no more pages.
   */
  cursor?: string;
}

/**
 * Paginated list of workflow executions.
 *
 * GET /api/v1/workflow-executions
 *
 * Derives from the backend ExecutionListResponse schema (api/schemas/workflow.py).
 */
export interface ExecutionListResponse {
  /** List of execution objects for the current page. */
  items: WorkflowExecution[];
  /** Total number of matching records before pagination. */
  total: number;
  /** Number of records skipped (offset). */
  skip: number;
  /** Maximum records returned in this page. */
  limit: number;
  /**
   * Opaque pagination cursor for the next page.
   * Undefined when there are no more pages.
   */
  cursor?: string;
}

// ============================================================================
// Filter / Query Types
// ============================================================================

/**
 * Filter and pagination parameters for the workflow list endpoint.
 *
 * Maps to query parameters on GET /api/v1/workflows.
 */
export interface WorkflowFilters {
  /** Full-text search string matched against name, description, and tags. */
  search?: string;
  /** Filter by lifecycle status. */
  status?: WorkflowStatus;
  /** Filter by one or more tags (AND semantics when multiple provided). */
  tags?: string[];
  /** Field to sort results by. */
  sortBy?: 'name' | 'created_at' | 'updated_at' | 'status';
  /** Sort direction. */
  sortOrder?: 'asc' | 'desc';
  /** Opaque cursor from a previous WorkflowListResponse for keyset pagination. */
  cursor?: string;
  /** Maximum number of results to return. Default: 50, max: 100. */
  limit?: number;
  /** Number of results to skip (offset-based alternative to cursor). */
  skip?: number;
}

/**
 * Filter and pagination parameters for the workflow executions list endpoint.
 *
 * Maps to query parameters on GET /api/v1/workflow-executions.
 */
export interface ExecutionFilters {
  /** Filter by parent workflow ID. */
  workflowId?: string;
  /** Filter by execution lifecycle status. */
  status?: ExecutionStatus;
  /** Filter by trigger type. */
  trigger?: TriggerType;
  /** ISO 8601 start of date range filter (inclusive). */
  startedAfter?: string;
  /** ISO 8601 end of date range filter (inclusive). */
  startedBefore?: string;
  /** Field to sort results by. */
  sortBy?: 'started_at' | 'completed_at' | 'status';
  /** Sort direction. */
  sortOrder?: 'asc' | 'desc';
  /** Opaque cursor from a previous ExecutionListResponse for keyset pagination. */
  cursor?: string;
  /** Maximum number of results to return. Default: 50, max: 100. */
  limit?: number;
  /** Number of results to skip (offset-based alternative to cursor). */
  skip?: number;
}

// ============================================================================
// UI Convenience Types
// ============================================================================

/**
 * Lightweight workflow summary for list views.
 *
 * Omits the large `definition` YAML string and detailed stage/parameter data
 * to keep list renders fast. Derive from Workflow via Pick when needed.
 */
export type WorkflowSummary = Pick<
  Workflow,
  | 'id'
  | 'uuid'
  | 'name'
  | 'description'
  | 'version'
  | 'status'
  | 'tags'
  | 'projectId'
  | 'createdAt'
  | 'updatedAt'
> & {
  /** Stage count derived from stages.length — avoids loading full stage list. */
  stageCount: number;
};

/**
 * Lightweight execution summary for list views and activity feeds.
 *
 * Omits per-step log lines and full outputs to keep renders fast.
 */
export type ExecutionSummary = Omit<WorkflowExecution, 'stages'> & {
  /** Abbreviated stage summaries (no logs/outputs). */
  stages: Omit<StageExecution, 'logs' | 'outputs'>[];
};

/**
 * Status display metadata for WorkflowStatus values.
 * Maps each status to a label, description, and Tailwind color class.
 */
export const WORKFLOW_STATUS_META: Record<
  WorkflowStatus,
  { label: string; description: string; colorClass: string }
> = {
  draft: {
    label: 'Draft',
    description: 'Work-in-progress, not yet ready to execute',
    colorClass: 'text-yellow-500',
  },
  active: {
    label: 'Active',
    description: 'Production-ready and eligible for execution',
    colorClass: 'text-green-500',
  },
  archived: {
    label: 'Archived',
    description: 'Retired; preserved for reference',
    colorClass: 'text-gray-400',
  },
  deprecated: {
    label: 'Deprecated',
    description: 'Superseded by another workflow',
    colorClass: 'text-orange-400',
  },
};

/**
 * Status display metadata for ExecutionStatus values.
 * Maps each status to a label, description, and Tailwind color class.
 */
export const EXECUTION_STATUS_META: Record<
  ExecutionStatus,
  { label: string; description: string; colorClass: string }
> = {
  pending: {
    label: 'Pending',
    description: 'Queued; not yet started',
    colorClass: 'text-gray-400',
  },
  running: {
    label: 'Running',
    description: 'Actively executing',
    colorClass: 'text-blue-500',
  },
  completed: {
    label: 'Completed',
    description: 'All stages finished successfully',
    colorClass: 'text-green-500',
  },
  failed: {
    label: 'Failed',
    description: 'One or more stages failed',
    colorClass: 'text-red-500',
  },
  cancelled: {
    label: 'Cancelled',
    description: 'Execution was manually cancelled',
    colorClass: 'text-gray-500',
  },
  paused: {
    label: 'Paused',
    description: 'Temporarily suspended',
    colorClass: 'text-yellow-400',
  },
  waiting_for_approval: {
    label: 'Awaiting Approval',
    description: 'Paused at a gate stage',
    colorClass: 'text-purple-500',
  },
};

/**
 * Type guard: check if a value is a valid WorkflowStatus.
 */
export function isWorkflowStatus(value: unknown): value is WorkflowStatus {
  return (
    typeof value === 'string' &&
    ['draft', 'active', 'archived', 'deprecated'].includes(value)
  );
}

/**
 * Type guard: check if a value is a valid ExecutionStatus.
 */
export function isExecutionStatus(value: unknown): value is ExecutionStatus {
  return (
    typeof value === 'string' &&
    [
      'pending',
      'running',
      'completed',
      'failed',
      'cancelled',
      'paused',
      'waiting_for_approval',
    ].includes(value)
  );
}

/**
 * Returns true when the execution is in a terminal state (no further status changes).
 */
export function isTerminalExecutionStatus(status: ExecutionStatus): boolean {
  return ['completed', 'failed', 'cancelled'].includes(status);
}

/**
 * Returns true when the execution is actively progressing (not done, not waiting).
 */
export function isActiveExecutionStatus(status: ExecutionStatus): boolean {
  return ['pending', 'running'].includes(status);
}
